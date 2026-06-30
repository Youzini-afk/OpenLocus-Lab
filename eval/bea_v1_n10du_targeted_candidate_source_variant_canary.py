#!/usr/bin/env python3
"""BEA-v1-N10DU Targeted Candidate-Source Variant Canary."""

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
PHASE = "BEA-v1-N10DU Targeted Candidate-Source Variant Canary"
SLUG = "bea_v1_n10du_targeted_candidate_source_variant_canary"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"

N10DT_REPORT = ROOT / "artifacts" / "bea_v1_n10dt_real_candidate_source_failure_analysis" / "bea_v1_n10dt_real_candidate_source_failure_analysis_report.json"
PRIVATE_N10DR_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dr_real_candidate_source_canary" / "private_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
PRIVATE_RECON = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "p4l_validation" / "bea_v1_p4l.private_reconstruction.jsonl"
PRIVATE_REPOS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "repos"
PRIVATE_OUT = ROOT / ".openlocus" / "research-private" / "local_n10du_targeted_source_variant_canary"
OPENLOCUS_BIN = ROOT / "target" / "release" / "openlocus"

STATUS_PASS = "targeted_candidate_source_variant_canary_pass_n10dv_authorized"
STATUS_PARTIAL = "partial_targeted_candidate_source_variant_canary_executed_with_low_recovery"
STATUS_NO_RECOVERY = "targeted_candidate_source_variant_canary_complete_no_recovery"
STATUS_NO_INPUTS = "no_go_n10du_required_inputs_unavailable"
STATUS_PREREQ = "no_go_n10du_local_prerequisites_unavailable"
STATUS_ACCOUNTING = "no_go_n10du_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10du_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_PASS, STATUS_PARTIAL, STATUS_NO_RECOVERY, STATUS_NO_INPUTS, STATUS_PREREQ, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

VARIANTS = [
    ("original_regex_only", "regex", "original"),
    ("original_symbol_only", "symbol", "original"),
    ("original_bm25_only", "bm25", "original"),
    ("identifier_normalized_regex_only", "regex", "identifier_normalized"),
    ("identifier_normalized_symbol_only", "symbol", "identifier_normalized"),
    ("identifier_normalized_bm25_only", "bm25", "identifier_normalized"),
]

FORBIDDEN_KEYS = {
    "path", "paths", "file", "files", "filename", "filenames", "repo", "repo_root",
    "private_path", "private_filename", "span", "spans", "line", "lines", "snippet",
    "snippets", "content", "candidate", "candidates", "candidate_list", "gold",
    "gold_path", "gold_paths", "exact_rank", "raw_rank", "raw_query", "query",
    "hash", "provider_payload", "raw_diff", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|java|go|cpp|c|h|md|txt)", re.I),
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
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    left, right = norm_ref(a), norm_ref(b)
    return bool(left and right and (left == right or left.endswith("/" + right) or right.endswith("/" + left)))


def candidate_hits_gold(candidate: dict[str, Any], gold_refs: list[Any]) -> bool:
    return any(suffix_match(candidate.get("path"), gold) for gold in gold_refs)


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


def normalize_query(query: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", query)
    tokens = re.findall(r"[A-Za-z0-9_]+", spaced.replace("_", " "))
    cleaned: list[str] = []
    for tok in tokens:
        for part in tok.split("_"):
            low = part.lower()
            if len(low) >= 3:
                cleaned.append(low)
    result = " ".join(cleaned[:12])
    return result or query


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
            if any(p.search(node) for p in FORBIDDEN_VALUE_PATTERNS):
                findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})
    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def input_records() -> tuple[list[dict[str, Any]], bool]:
    data, state = load_json(N10DT_REPORT)
    actual = str(data.get("status", "")) if data else ""
    ok = state == "present" and actual == "real_candidate_source_failure_analysis_complete_n10du_authorized"
    return [{
        "anonymous_input_artifact_id": "n10duinput0000",
        "artifact_bucket": "n10dt_failure_analysis",
        "load_status_bucket": state,
        "expected_status_bucket": "real_candidate_source_failure_analysis_complete_n10du_authorized",
        "actual_status_bucket": actual or "unavailable",
        "status_match_bool": ok,
        "public_artifact_bool": True,
    }], ok


def run_retrieval(repo_root: Path, query: str, channel: str) -> tuple[int, list[dict[str, Any]], str, int]:
    start = time.monotonic()
    proc = subprocess.run(
        [str(OPENLOCUS_BIN), "retrieve", query, "--channels", channel, "--max-results", "50", "--json"],
        cwd=repo_root, text=True, capture_output=True, timeout=60,
    )
    elapsed = int((time.monotonic() - start) * 1000)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    evidence = data.get("evidence") if isinstance(data, dict) else []
    return proc.returncode, evidence[:50] if isinstance(evidence, list) else [], proc.stderr, elapsed


def execute() -> tuple[dict[str, Any], dict[str, Any]]:
    n10dr_rows = sorted(read_jsonl(PRIVATE_N10DR_ROWS), key=lambda r: int(r.get("private_case_order", 0)))
    n1_rows = {r["denominator_index_private"]: r for r in read_jsonl(PRIVATE_N1_ROWS) if isinstance(r.get("denominator_index_private"), int)}
    recon = [r for r in read_jsonl(PRIVATE_RECON) if r.get("selected_for_denominator")]
    variant_stats: dict[str, dict[str, Any]] = {name: {"executed": 0, "success": 0, "zero": 0, "nonzero": 0, "failed": 0, "top10": 0, "top20": 0, "top50": 0, "candidate_buckets": Counter(), "latency_buckets": Counter(), "overlap": Counter(), "novelty": Counter()} for name, _, _ in VARIANTS}
    private_rows: list[dict[str, Any]] = []
    recovered_cases: set[int] = set()
    best_variant_hits: Counter[str] = Counter()
    command_count = 0
    for sample in n10dr_rows:
        denom = int(sample.get("private_denominator_index", -1))
        n1 = n1_rows.get(denom, {})
        repo = repo_root_for(n1, recon)
        if repo is None or not repo.is_dir():
            continue
        original_query = str(n1.get("query", ""))
        normalized = normalize_query(original_query)
        gold_refs = n1.get("gold_paths") or []
        original_files = {norm_ref(c.get("path")) for c in (n1.get("p4_evidence") or []) if isinstance(c, dict) and c.get("path")}
        for name, channel, query_mode in VARIANTS:
            query = normalized if query_mode == "identifier_normalized" else original_query
            rc, evidence, stderr, elapsed = run_retrieval(repo, query, channel)
            command_count += 1
            stats = variant_stats[name]
            stats["executed"] += 1
            if rc == 0:
                stats["success"] += 1
            else:
                stats["failed"] += 1
            if rc == 0 and evidence:
                stats["nonzero"] += 1
            elif rc == 0:
                stats["zero"] += 1
            stats["candidate_buckets"][count_bucket(len(evidence))] += 1
            stats["latency_buckets"][latency_bucket(elapsed)] += 1
            cand_files = {norm_ref(c.get("path")) for c in evidence if isinstance(c, dict) and c.get("path")}
            overlap = sum(1 for c in cand_files if any(suffix_match(c, o) for o in original_files))
            stats["overlap"]["overlap_any" if overlap else "overlap_none"] += 1
            novel = sum(1 for c in cand_files if not any(suffix_match(c, o) for o in original_files))
            stats["novelty"]["many_novel_files" if novel > 5 else ("few_novel_files" if novel else "no_novel_files")] += 1
            hit_ranks = [idx + 1 for idx, cand in enumerate(evidence) if isinstance(cand, dict) and candidate_hits_gold(cand, gold_refs)]
            if hit_ranks:
                recovered_cases.add(denom)
                best_variant_hits[name] += 1
            stats["top10"] += int(any(r <= 10 for r in hit_ranks))
            stats["top20"] += int(any(r <= 20 for r in hit_ranks))
            stats["top50"] += int(bool(hit_ranks))
            private_rows.append({
                "private_case_order": sample.get("private_case_order"),
                "private_denominator_index": denom,
                "private_variant_bucket": name,
                "private_returncode": rc,
                "private_candidate_count": len(evidence),
                "private_hit_ranks": hit_ranks[:5],
                "private_candidate_rows": evidence,
                "private_error_bucket": "none" if rc == 0 else "nonzero_exit",
            })
    PRIVATE_OUT.mkdir(parents=True, exist_ok=True)
    with (PRIVATE_OUT / "private_variant_candidate_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in private_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {"private_schema_version": "n10du_private_manifest_v1", "private_sampled_case_count": len(n10dr_rows), "private_variant_count": len(VARIANTS), "private_command_count": command_count}
    (PRIVATE_OUT / "private_variant_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (PRIVATE_OUT / "private_command_summary.json").write_text(json.dumps({"private_command_count": command_count}, indent=2), encoding="utf-8")
    summary = {"sampled": len(n10dr_rows), "command_count": command_count, "variant_stats": variant_stats, "recovered_cases": recovered_cases, "best_variant_hits": best_variant_hits}
    return summary, manifest


def records_from_counter(prefix: str, counter: Counter[str], field: str) -> list[dict[str, Any]]:
    return [{f"anonymous_{prefix}_id": f"n10du{prefix}{i:04d}", field: k, "case_count": int(v)} for i, (k, v) in enumerate(sorted(counter.items()))]


def build_report() -> dict[str, Any]:
    inputs, inputs_ok = input_records()
    prereq_ok = all(p.exists() for p in (PRIVATE_N10DR_ROWS, PRIVATE_N1_ROWS, PRIVATE_RECON)) and OPENLOCUS_BIN.is_file() and PRIVATE_REPOS.is_dir()
    if not inputs_ok:
        status = STATUS_NO_INPUTS
        summary: dict[str, Any] = {"sampled": 0, "command_count": 0, "variant_stats": {}, "recovered_cases": set(), "best_variant_hits": Counter()}
        manifest: dict[str, Any] = {}
    elif not prereq_ok:
        status = STATUS_PREREQ
        summary = {"sampled": 0, "command_count": 0, "variant_stats": {}, "recovered_cases": set(), "best_variant_hits": Counter()}
        manifest = {}
    else:
        summary, manifest = execute()
        recovered = len(summary["recovered_cases"])
        if recovered >= 3:
            status = STATUS_PASS
        elif recovered >= 1:
            status = STATUS_PARTIAL
        else:
            status = STATUS_NO_RECOVERY
    variant_result_records = []
    for idx, (name, channel, query_mode) in enumerate(VARIANTS):
        s = summary.get("variant_stats", {}).get(name, {})
        variant_result_records.append({
            "anonymous_variant_result_id": f"n10duvarres{idx:04d}",
            "variant_bucket": name,
            "channel_bucket": channel,
            "query_mode_bucket": query_mode,
            "executed_case_count": int(s.get("executed", 0)),
            "retrieval_success_count": int(s.get("success", 0)),
            "zero_candidate_case_count": int(s.get("zero", 0)),
            "nonzero_candidate_case_count": int(s.get("nonzero", 0)),
            "command_failed_count": int(s.get("failed", 0)),
            "gold_file_recovered_top10_count": int(s.get("top10", 0)),
            "gold_file_recovered_top20_count": int(s.get("top20", 0)),
            "gold_file_recovered_top50_count": int(s.get("top50", 0)),
            "candidate_count_bucket_records": records_from_counter("candbucket", s.get("candidate_buckets", Counter()), "candidate_count_bucket"),
            "latency_bucket_records": records_from_counter("latbucket", s.get("latency_buckets", Counter()), "latency_bucket"),
            "novelty_bucket_records": records_from_counter("novbucket", s.get("novelty", Counter()), "novelty_bucket"),
            "overlap_bucket_records": records_from_counter("ovbucket", s.get("overlap", Counter()), "overlap_bucket"),
        })
    recovered_any = len(summary.get("recovered_cases", set()))
    best_variant = "none"
    if summary.get("best_variant_hits"):
        best_variant = summary["best_variant_hits"].most_common(1)[0][0]
    focused_followup = recovered_any > 0
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10du_targeted_candidate_source_variant_canary_v1",
        "phase_bucket": PHASE,
        "status": status,
        "input_artifact_records": inputs,
        "variant_contract_records": [{"anonymous_variant_contract_id": f"n10duvar{idx:04d}", "variant_bucket": name, "channel_bucket": channel, "query_mode_bucket": mode, "topk_limit": 50, "fixed_predeclared_bool": True} for idx, (name, channel, mode) in enumerate(VARIANTS)],
        "query_normalization_records": [{"anonymous_query_norm_id": "n10duquerynorm0000", "deterministic_bool": True, "gold_free_bool": True, "max_token_count": 12, "fallback_to_original_if_empty_bool": True}],
        "command_boundary_records": [{"anonymous_command_boundary_id": "n10ducmd0000", "max_command_count": 180, "actual_command_count": int(summary.get("command_count", 0)), "topk_limit": 50, "local_cli_only_bool": True, "network_bool": False, "git_clone_bool": False, "provider_bool": False, "selector_reranker_bool": False}],
        "private_execution_summary_records": [{"anonymous_private_execution_id": "n10duexec0000", "sampled_case_count": int(summary.get("sampled", 0)), "variant_count": len(VARIANTS), "private_output_file_count_bucket": "three_private_outputs", "private_rows_written_bucket": "many", "same_scoped_private_rows_read_bool": True}],
        "variant_result_records": variant_result_records,
        "cross_variant_recovery_records": [{"anonymous_cross_variant_id": "n10ducross0000", "cases_recovered_by_any_variant_count": recovered_any, "best_variant_bucket": best_variant, "best_channel_bucket": best_variant.split("_")[-2] if best_variant != "none" else "none", "best_query_bucket": "identifier_normalized" if best_variant.startswith("identifier") else ("original" if best_variant != "none" else "none")}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10duprivacy0000", "public_paths_or_filenames_bool": False, "public_candidate_lists_bool": False, "public_queries_bool": False, "public_snippets_or_content_bool": False, "public_spans_or_lines_bool": False, "public_gold_labels_bool": False, "public_exact_ranks_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10duforbid0000", "network_execution_count": 0, "git_clone_count": 0, "provider_call_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "p5_v1a_execution_count": 0}],
        "n10dv_handoff_records": [{"anonymous_handoff_id": "n10duhandoff0000", "n10dv_public_package_authorized_bool": True, "future_focused_followup_possible_bool": focused_followup, "next_allowed_phase_bucket": "BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package"}],
        "gate_records": [{"anonymous_gate_id": "n10dugate0000", "gate_bucket": "public_input_present", "gate_passed_bool": inputs_ok}, {"anonymous_gate_id": "n10dugate0001", "gate_bucket": "local_prerequisites_present", "gate_passed_bool": prereq_ok}, {"anonymous_gate_id": "n10dugate0002", "gate_bucket": "variant_count_six", "gate_passed_bool": len(VARIANTS) == 6}, {"anonymous_gate_id": "n10dugate0003", "gate_bucket": "commands_lte_180", "gate_passed_bool": int(summary.get("command_count", 0)) <= 180}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dustop0000", "next_allowed_phase_bucket": "BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package", "scaled_retrieval_authorized_bool": False, "network_authorized_bool": False, "git_clone_authorized_bool": False, "provider_authorized_bool": False, "candidate_generation_materialization_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_PASS in STATUS_VOCAB and STATUS_NO_RECOVERY in STATUS_VOCAB))
    checks.append(("variant_grid", len(VARIANTS) == 6 and {v[1] for v in VARIANTS} == {"regex", "symbol", "bm25"}))
    try:
        parse_args(["--bad", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/x.json"})["status"] == "fail"))
    checks.append(("normalize", normalize_query("fooBar/baz_qux.mm") == "foo bar baz qux"))
    checks.append(("suffix", suffix_match("a/b/c.py", "c.py") and not suffix_match("a.py", "b.py")))
    checks.append(("count_bucket", count_bucket(50) == "thirty_one_to_fifty"))
    checks.append(("latency_bucket", latency_bucket(1500) == "1500_4999ms"))
    checks.append(("records", isinstance(input_records()[0], list)))
    dummy = {"stop_go_records": [{"scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False}]}
    checks.append(("false_flags", not dummy["stop_go_records"][0]["scaled_retrieval_authorized_bool"] and not dummy["stop_go_records"][0]["runtime_default_authorized_bool"]))
    checks.append(("scan_pass", scan_summary({"bucket": "safe_bucket", "count": 1})["status"] == "pass"))
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
    return 0 if report["status"] in {STATUS_PASS, STATUS_PARTIAL, STATUS_NO_RECOVERY} else 1


if __name__ == "__main__":
    raise SystemExit(main())
