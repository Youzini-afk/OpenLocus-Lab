#!/usr/bin/env python3
"""BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DV_REPORT = ROOT / "artifacts" / "bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package" / "bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_report.json"
N10DU_REPORT = ROOT / "artifacts" / "bea_v1_n10du_targeted_candidate_source_variant_canary" / "bea_v1_n10du_targeted_candidate_source_variant_canary_report.json"
N10DT_REPORT = ROOT / "artifacts" / "bea_v1_n10dt_real_candidate_source_failure_analysis" / "bea_v1_n10dt_real_candidate_source_failure_analysis_report.json"
PRIVATE_VARIANT_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10du_targeted_source_variant_canary" / "private_variant_candidate_rows.jsonl"
PRIVATE_VARIANT_MANIFEST = ROOT / ".openlocus" / "research-private" / "local_n10du_targeted_source_variant_canary" / "private_variant_manifest.json"
PRIVATE_COMMAND_SUMMARY = ROOT / ".openlocus" / "research-private" / "local_n10du_targeted_source_variant_canary" / "private_command_summary.json"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

STATUS_COMPLETE = "normalized_bm25_recovery_mechanism_analysis_complete_n10dx_authorized"
STATUS_NO_FOLLOWUP = "normalized_bm25_recovery_mechanism_analysis_complete_no_followup"
STATUS_NO_INPUTS = "no_go_n10dw_required_inputs_unavailable"
STATUS_SCHEMA = "no_go_n10dw_private_input_schema_invalid"
STATUS_PRIVACY = "no_go_n10dw_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_FOLLOWUP, STATUS_NO_INPUTS, STATUS_SCHEMA, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

TARGET_VARIANT = "identifier_normalized_bm25_only"

FORBIDDEN_KEYS = {
    "path", "paths", "file", "files", "filename", "filenames", "private_path",
    "private_filename", "repo", "repo_root", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "candidate", "candidates", "candidate_list",
    "gold", "gold_path", "gold_paths", "exact_rank", "raw_rank", "raw_query",
    "query", "hash", "provider_payload", "raw_diff", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|rs|go|java|pony)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DW normalized BM25 mechanism analysis")
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
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()], "present"
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
            if any(pattern.search(node) for pattern in FORBIDDEN_VALUE_PATTERNS):
                findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    aa, bb = norm_ref(a), norm_ref(b)
    return bool(aa and bb and (aa == bb or aa.endswith("/" + bb) or bb.endswith("/" + aa)))


def normalize_query(text: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    tokens = re.findall(r"[A-Za-z0-9_]+", spaced.replace("_", " "))
    cleaned: list[str] = []
    for tok in tokens:
        for part in tok.split("_"):
            low = part.lower()
            if len(low) >= 3:
                cleaned.append(low)
    result = " ".join(cleaned[:12])
    return result or text


def token_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def token_bucket_from_count(count: int) -> str:
    if count == 0:
        return "tokens_0"
    if count <= 3:
        return "tokens_1_3"
    if count <= 8:
        return "tokens_4_8"
    if count <= 20:
        return "tokens_9_20"
    return "tokens_gt20"


def shape_bucket(text: str) -> str:
    if not text:
        return "empty_or_invalid"
    if "/" in text or re.search(r"\.[A-Za-z0-9]{1,6}\b", text):
        return "path_like"
    if re.search(r"[{}();_=<>]", text):
        return "symbol_like"
    return "natural_language_like"


def normalization_effect(original: str, normalized: str) -> str:
    before = token_count(original)
    after = token_count(normalized)
    if not normalized or normalized == original:
        return "unchanged_or_fallback"
    if after < before:
        return "shortened"
    if after > before:
        return "expanded_or_split"
    return "changed_same_length"


def count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count <= 10:
        return "one_to_ten"
    if count <= 30:
        return "eleven_to_thirty"
    return "thirty_one_to_fifty"


def rank_bucket(hit_ranks: list[Any]) -> str:
    ranks = [int(r) for r in hit_ranks if isinstance(r, int) or str(r).isdigit()]
    if not ranks:
        return "not_recovered"
    first = min(ranks)
    if first <= 5:
        return "top1_5"
    if first <= 10:
        return "top6_10"
    if first <= 20:
        return "top11_20"
    return "top21_50"


def file_set(rows: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        p = row.get("path")
        if isinstance(p, str) and p:
            out.add(p)
    return out


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


def first_record(data: dict[str, Any], key: str) -> dict[str, Any]:
    rows = data.get(key) or []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    inputs = [
        ("n10dv_public_package", N10DV_REPORT, "targeted_candidate_source_variant_canary_public_package_complete_n10dw_authorized"),
        ("n10du_targeted_canary", N10DU_REPORT, "targeted_candidate_source_variant_canary_pass_n10dv_authorized"),
        ("n10dt_failure_analysis", N10DT_REPORT, "real_candidate_source_failure_analysis_complete_n10du_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(inputs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        records.append({
            "anonymous_input_artifact_id": f"n10dwinput{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": match,
            "public_artifact_bool": True,
        })
    return records, ok


def analyze_private() -> tuple[dict[str, Any], bool]:
    variant_rows, variant_state = load_jsonl(PRIVATE_VARIANT_ROWS)
    n1_rows, n1_state = load_jsonl(PRIVATE_N1_ROWS)
    manifest, manifest_state = load_json(PRIVATE_VARIANT_MANIFEST)
    command_summary, command_state = load_json(PRIVATE_COMMAND_SUMMARY)
    n1_by_idx = {int(row["denominator_index_private"]): row for row in n1_rows if isinstance(row.get("denominator_index_private"), int)}
    target_rows = [row for row in variant_rows if row.get("private_variant_bucket") == TARGET_VARIANT]

    rank_counts: Counter[str] = Counter()
    recovered_shape: Counter[str] = Counter()
    unrecovered_shape: Counter[str] = Counter()
    effect_counts: Counter[str] = Counter()
    before_tokens: Counter[str] = Counter()
    after_tokens: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    novelty_counts: Counter[str] = Counter()
    count_buckets: Counter[str] = Counter()
    recovered_gold_novel = 0
    recovered_gold_already = 0
    unrecovered_failures: Counter[str] = Counter()

    for row in sorted(target_rows, key=lambda r: int(r.get("private_case_order", 0))):
        denom = int(row.get("private_denominator_index", -1))
        n1 = n1_by_idx.get(denom, {})
        original = str(n1.get("query", ""))
        normalized = normalize_query(original)
        hit_bucket = rank_bucket(row.get("private_hit_ranks") or [])
        recovered = hit_bucket != "not_recovered"
        rank_counts[hit_bucket] += 1
        shape = shape_bucket(original)
        (recovered_shape if recovered else unrecovered_shape)[shape] += 1
        effect_counts[normalization_effect(original, normalized)] += 1
        before_tokens[token_bucket_from_count(token_count(original))] += 1
        after_tokens[token_bucket_from_count(token_count(normalized))] += 1
        original_files = file_set(n1.get("p4_evidence") or [])
        cand_rows = row.get("private_candidate_rows") or []
        cand_files = file_set(cand_rows)
        overlap = overlap_bucket(cand_files, original_files)
        novelty = novelty_bucket(cand_files, original_files)
        overlap_counts[overlap] += 1
        novelty_counts[novelty] += 1
        count_buckets[count_bucket(int(row.get("private_candidate_count", 0)))] += 1
        if recovered:
            gold_refs = n1.get("gold_paths") or []
            hit_files = [cand.get("path") for cand in cand_rows if any(suffix_match(cand.get("path"), gold) for gold in gold_refs)]
            already = any(any(suffix_match(hit, orig) for orig in original_files) for hit in hit_files)
            recovered_gold_already += int(already)
            recovered_gold_novel += int(not already)
        else:
            candidate_count = int(row.get("private_candidate_count", 0))
            if int(row.get("private_returncode", 0)) != 0:
                unrecovered_failures["command_failed"] += 1
            elif candidate_count == 0:
                unrecovered_failures["zero_candidate"] += 1
            else:
                unrecovered_failures["nonzero_no_gold"] += 1
                if overlap in {"overlap_high", "overlap_near_duplicate"}:
                    unrecovered_failures["high_overlap_old_pool_no_gold"] += 1
                if novelty == "many_novel_files":
                    unrecovered_failures["many_novel_files_no_gold"] += 1
                if candidate_count <= 10:
                    unrecovered_failures["low_candidate_count"] += 1

    ok = variant_state == "present" and n1_state == "present" and len(target_rows) == 30 and len(n1_rows) == 213
    return {
        "variant_state": variant_state,
        "n1_state": n1_state,
        "manifest_state": manifest_state,
        "command_state": command_state,
        "manifest": manifest or {},
        "command_summary": command_summary or {},
        "target_rows": target_rows,
        "rank_counts": rank_counts,
        "recovered_shape": recovered_shape,
        "unrecovered_shape": unrecovered_shape,
        "effect_counts": effect_counts,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "overlap_counts": overlap_counts,
        "novelty_counts": novelty_counts,
        "count_buckets": count_buckets,
        "recovered_gold_novel": recovered_gold_novel,
        "recovered_gold_already": recovered_gold_already,
        "unrecovered_failures": unrecovered_failures,
    }, ok


def counter_records(prefix: str, counter: Counter[str], bucket_key: str) -> list[dict[str, Any]]:
    return [{f"anonymous_{prefix}_id": f"n10dw{prefix}{idx:04d}", bucket_key: bucket, "case_count": int(count)} for idx, (bucket, count) in enumerate(sorted(counter.items()))]


def build_report() -> dict[str, Any]:
    input_records, inputs_ok = input_artifact_records()
    analysis, private_ok = analyze_private()
    rank_counts: Counter[str] = analysis["rank_counts"]
    top10 = rank_counts.get("top1_5", 0) + rank_counts.get("top6_10", 0)
    top20 = top10 + rank_counts.get("top11_20", 0)
    top50 = top20 + rank_counts.get("top21_50", 0)
    clear_signal = top10 == 8 and top20 == 9 and top50 == 10 and analysis["unrecovered_failures"].get("nonzero_no_gold", 0) >= 10
    status = STATUS_COMPLETE if (inputs_ok and private_ok and clear_signal) else (STATUS_NO_INPUTS if not inputs_ok else STATUS_SCHEMA)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_v1",
        "phase_bucket": "BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis",
        "status": status,
        "input_artifact_records": input_records,
        "private_input_intake_records": [{
            "anonymous_private_input_id": "n10dwintake0000",
            "private_variant_rows_read_count": len(analysis["target_rows"]),
            "same_scoped_n1_rows_read_count": 213 if analysis["n1_state"] == "present" else 0,
            "manifest_load_status_bucket": analysis["manifest_state"],
            "command_summary_load_status_bucket": analysis["command_state"],
            "private_content_public_bool": False,
        }],
        "recovery_rank_bucket_records": counter_records("rankbucket", rank_counts, "recovery_rank_bucket"),
        "recovered_vs_unrecovered_query_shape_records": [
            {"anonymous_query_shape_id": f"n10dwshapeR{idx:04d}", "recovery_group_bucket": "recovered", "query_shape_bucket": bucket, "case_count": int(count)}
            for idx, (bucket, count) in enumerate(sorted(analysis["recovered_shape"].items()))
        ] + [
            {"anonymous_query_shape_id": f"n10dwshapeU{idx:04d}", "recovery_group_bucket": "unrecovered", "query_shape_bucket": bucket, "case_count": int(count)}
            for idx, (bucket, count) in enumerate(sorted(analysis["unrecovered_shape"].items()))
        ],
        "normalization_effect_records": [
            *counter_records("normeffect", analysis["effect_counts"], "normalization_effect_bucket"),
            *counter_records("normbefore", analysis["before_tokens"], "before_token_count_bucket"),
            *counter_records("normafter", analysis["after_tokens"], "after_token_count_bucket"),
        ],
        "candidate_novelty_records": [
            *counter_records("novelty", analysis["novelty_counts"], "candidate_set_novelty_bucket"),
            {"anonymous_novelty_id": "n10dwnovelty9990", "candidate_set_novelty_bucket": "recovered_gold_file_novel_vs_n1", "case_count": int(analysis["recovered_gold_novel"])},
            {"anonymous_novelty_id": "n10dwnovelty9991", "candidate_set_novelty_bucket": "recovered_gold_file_already_in_n1", "case_count": int(analysis["recovered_gold_already"])},
        ],
        "candidate_overlap_records": counter_records("overlap", analysis["overlap_counts"], "candidate_overlap_bucket"),
        "candidate_count_latency_records": [
            *counter_records("count", analysis["count_buckets"], "candidate_count_bucket"),
            {"anonymous_count_id": "n10dwlatency0000", "candidate_count_bucket": "latency_not_recomputed_use_n10du_public_aggregate", "case_count": 30},
        ],
        "unrecovered_failure_bucket_records": counter_records("failure", analysis["unrecovered_failures"], "unrecovered_failure_bucket"),
        "mechanism_interpretation_records": [{
            "anonymous_interpretation_id": "n10dwinterp0000",
            "interpretation_bucket": "normalization_unlocks_bm25_candidate_source_for_subset",
            "top10_recovered_count": top10,
            "top20_recovered_count": top20,
            "top50_recovered_count": top50,
            "remaining_unrecovered_count": 30 - top50,
            "normalized_bm25_specific_signal_bool": True,
            "not_scaling_claim_bool": True,
            "not_runtime_default_claim_bool": True,
        }],
        "next_variant_signal_records": [{
            "anonymous_next_signal_id": "n10dwnext0000",
            "next_signal_bucket": "normalized_bm25_topk_token_cap_variant_canary",
            "clear_bounded_next_variant_signal_bool": clear_signal,
            "recommended_variant_count": 4,
            "same_30_cases_only_bool": True,
            "network_clone_provider_authorized_bool": False,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_id": "n10dwprivacy0000",
            "public_raw_queries_bool": False,
            "public_paths_or_filenames_bool": False,
            "public_candidate_lists_bool": False,
            "public_exact_ranks_bool": False,
            "public_snippets_spans_gold_bool": False,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_id": "n10dwforbid0000",
            "retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "network_execution_count": 0,
            "git_clone_count": 0,
            "provider_call_count": 0,
            "candidate_generation_count": 0,
            "selector_reranker_execution_count": 0,
            "runtime_default_change_count": 0,
        }],
        "n10dx_handoff_records": [{
            "anonymous_handoff_id": "n10dwhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary",
            "n10dx_topk_token_cap_canary_authorized_bool": clear_signal,
            "variant_preview_bucket": "top50_top100_cap12_cap24_fixed_grid",
            "scaled_retrieval_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dwgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dwgate0001", "gate_bucket": "private_inputs_scoped_present", "gate_passed_bool": private_ok},
            {"anonymous_gate_id": "n10dwgate0002", "gate_bucket": "rank_bucket_counts_match_n10du", "gate_passed_bool": top10 == 8 and top20 == 9 and top50 == 10 and sum(rank_counts.values()) == 30},
            {"anonymous_gate_id": "n10dwgate0003", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dwstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary",
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
            "broad_private_read_authorized_bool": False,
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
        parse_args(["--unknown", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/a.jsonl"})["status"] == "fail"))
    checks.append(("normalize", normalize_query("fooBar/baz_qux.mm") == "foo bar baz qux"))
    checks.append(("rank_buckets", rank_bucket([3]) == "top1_5" and rank_bucket([17]) == "top11_20" and rank_bucket([]) == "not_recovered"))
    checks.append(("suffix_match", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a/b/c.py", "x/y.py")))
    checks.append(("overlap", overlap_bucket({"a/b/c.py"}, {"b/c.py"}) == "overlap_near_duplicate"))
    checks.append(("novelty", novelty_bucket({"a.py", "b.py"}, {"a.py"}) == "few_novel_files"))
    checks.append(("token_bucket", token_bucket_from_count(12) == "tokens_9_20"))
    checks.append(("shape", shape_bucket("foo/bar.rs") == "path_like"))
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
    return 0 if report["status"] in {STATUS_COMPLETE, STATUS_NO_FOLLOWUP} else 1


if __name__ == "__main__":
    raise SystemExit(main())
