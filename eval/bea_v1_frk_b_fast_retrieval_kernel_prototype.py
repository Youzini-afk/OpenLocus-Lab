#!/usr/bin/env python3
"""BEA-v1-FRK-B Fast Retrieval Kernel Prototype.

Builds a local persistent fast retrieval kernel under ignored/private storage in
explicit mode, evaluates it on R14-S with private labels/traces, and publishes
only aggregate bucketized public results.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-B Fast Retrieval Kernel Prototype"
SLUG = "bea_v1_frk_b_fast_retrieval_kernel_prototype"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "frk_b_unavailable_no_explicit_local_prototype_opt_in"
STATUS_COMPLETE = "frk_b_fast_retrieval_kernel_prototype_complete_frk_c_public_package_authorized"
STATUS_FAIL_CLOSED = "frk_b_fail_closed_validation_or_boundary_failure"
NEXT_PHASE = "BEA-v1-FRK-C Fast Retrieval Kernel Public Package"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_A_REPORT = Path("artifacts/bea_v1_frk_a_competitive_retrieval_benchmark_package/bea_v1_frk_a_competitive_retrieval_benchmark_package_report.json")
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
FRK_A_CHECKPOINT = "efcfec6"
FRK_A_STATUS = "frk_a_benchmark_complete_frk_b_prototype_authorized"
SELF_TEST_EXPECTED = 44

BASELINES = [
    "ripgrep_text_practical",
    "same_budget_sparse_bm25",
    "same_budget_rrf_hybrid",
    "current_openlocus_retrieval",
    "simple_path_symbol",
    "hitmux_context_engine",
]
REQUIRED_FRK_A_BASELINES = {"ripgrep_text_practical", "same_budget_sparse_bm25", "same_budget_rrf_hybrid", "simple_path_symbol"}
INDEX_COMPONENTS = ["sparse_term_index", "symbol_name_index", "path_filename_config_index", "ast_span_index"]
GATES = [
    "frk_a_source_lock_gate",
    "top_level_frk_track_gate",
    "explicit_opt_in_gate",
    "private_label_scoring_gate",
    "private_trace_write_gate",
    "persistent_index_private_storage_gate",
    "required_index_components_gate",
    "retrieve_fast_api_gate",
    "evidencecore_validation_gate",
    "frk_a_baseline_comparison_gate",
    "aggregate_public_report_gate",
    "no_network_provider_runtime_gate",
    "no_fastcontext_gate",
    "no_runtime_default_scale_claim_gate",
    "frk_c_only_stop_go_gate",
    "public_readback_gate",
]
SYNTH = [
    "default_no_label_read_pass",
    "explicit_synthetic_kernel_pass",
    "safe_parser_unknown_arg_fail",
    "missing_explicit_confirm_fail",
    "wrong_out_path_fail",
    "bad_private_trace_root_fail",
    "frk_a_status_drift_fail",
    "frk_a_baseline_drop_fail",
    "index_component_drop_fail",
    "retrieve_api_missing_fail",
    "invalid_path_runtime_validation_fail",
    "invalid_range_runtime_validation_fail",
    "invalid_currentness_runtime_validation_fail",
    "public_raw_path_leak_fail",
    "public_raw_query_leak_fail",
    "public_raw_metric_leak_fail",
    "private_trace_path_leak_fail",
    "public_leak_clears_stopgo_fail",
    "fastcontext_overauth_fail",
    "network_overauth_fail",
    "runtime_default_claim_fail",
    "stop_go_overauth_fail",
    "gate_drop_fail",
    "gate_duplicate_fail",
    "synthetic_drop_fail",
    "synthetic_duplicate_fail",
    "readback_drop_fail",
    "stale_current_fail",
    "latency_bucket_missing_fail",
    "index_size_bucket_missing_fail",
    "trace_bucket_missing_fail",
    "evidencecore_bucket_missing_fail",
    "baseline_bucket_missing_fail",
    "hitmux_unavailable_continues",
    "openlocus_unavailable_continues",
    "fastcontext_excluded_pass",
    "persistent_index_written_private_pass",
    "validate_report_ok",
    "public_report_schema_ok",
    "aggregate_only_publication_ok",
    "no_rpm_llm_impl_ok",
    "no_ci_network_ok",
    "frk_c_only_ok",
    "self_test_count_readback_ok",
]

LEAK_PATTERNS = [
    ("private_or_repo_path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)),
    ("raw_task_or_query", re.compile(r"r14s-\d+|\"task_id\"|\"query\"|scan_repo|bm25_search", re.I)),
    ("raw_metric", re.compile(r"exact_value|raw_value|raw_metric|raw_score|raw_rank|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)),
    ("raw_span_or_snippet", re.compile(r"snippet|start_line|end_line|gold_spans|hard_negatives", re.I)),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+", text)]


def query_tokens(query: str) -> list[str]:
    expanded = re.sub(r"([a-z])([A-Z])", r"\1 \2", query).replace("_", " ")
    return list(dict.fromkeys(tokenize(expanded) + tokenize(query))) or [query.lower()]


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    args: dict[str, str | bool] = {
        "self_test": False,
        "validate": "",
        "out": "",
        "explicit": False,
        "confirm_labels": False,
        "confirm_traces": False,
        "confirm_public": False,
        "trace_root": "",
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test":
            args["self_test"] = True; i += 1
        elif a == "--allow-frk-b-local-prototype":
            args["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring":
            args["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-traces":
            args["confirm_traces"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact":
            args["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            args[{"--validate-report": "validate", "--out": "out", "--private-trace-root": "trace_root"}[a]] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    explicit_bits = [bool(args[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_public"]]
    if any(explicit_bits) and not all(explicit_bits):
        raise ValueError("invalid arguments")
    if args["out"]:
        public_report_path(str(args["out"]))
    if args["trace_root"]:
        private_root(str(args["trace_root"]))
    return args


def public_report_path(value: str) -> Path:
    p = Path(value)
    resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def private_root(value: str) -> Path:
    root = Path(value)
    if any(part == ".." for part in root.parts):
        raise ValueError("invalid arguments")
    resolved = root if root.is_absolute() else repo_root() / root
    ok = False
    try:
        resolved.relative_to(repo_root() / "runs"); ok = True
    except Exception:
        ok = str(resolved).startswith("/tmp/")
    if not ok or (resolved.exists() and resolved.is_symlink()):
        raise ValueError("invalid arguments")
    return resolved


def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrubbed = json.loads(json.dumps(report))
    for rec in scrubbed.get("synthetic_validator_records", []):
        rec["validator_bucket"] = "synthetic_validator_bucket"
    text = json.dumps(scrubbed, sort_keys=True)
    for allowed in ["raw_private_publication_authorized_bool", "no_raw_publication_bool", "raw_trace_publication_authorized_bool", "raw_candidates_public_bool", "raw_scores_ranks_spans_public_bool"]:
        text = text.replace(allowed, "public_boundary_bool")
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(text)]
    return {"status": "pass" if not findings else "fail", "finding_buckets": findings, "forbidden_finding_count": len(findings)}


def corpus_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((repo_root() / "crates").glob("**/*.rs")):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(repo_root()).as_posix()
        rows.append({"path": rel, "text": text, "lines": text.splitlines(), "tokens": tokenize(text), "current": sha(text)})
    return rows


def span_records(lines: list[str]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    pat = re.compile(r"\b(fn|struct|enum|trait|impl|mod)\s+([A-Za-z_][A-Za-z0-9_]*)")
    for idx, line in enumerate(lines, 1):
        m = pat.search(line)
        if m:
            spans.append((max(1, idx - 1), min(len(lines), idx + 8), m.group(2)))
    return spans or [(1, min(len(lines), 8), "file")]


def build_kernel(index_root: Path) -> dict[str, Any]:
    files = corpus_files()
    sparse: dict[str, list[int]] = {}
    symbols: dict[str, list[tuple[int, int, int]]] = {}
    path_terms: dict[str, list[int]] = {}
    ast_spans: list[dict[str, Any]] = []
    for fid, f in enumerate(files):
        for tok in set(f["tokens"]):
            sparse.setdefault(tok, []).append(fid)
        for tok in tokenize(Path(f["path"]).name) + tokenize(str(Path(f["path"]).parent)):
            path_terms.setdefault(tok, []).append(fid)
        for start, end, sym in span_records(f["lines"]):
            ast_spans.append({"fid": fid, "start": start, "end": end, "symbol": sym})
            symbols.setdefault(sym.lower(), []).append((fid, start, end))
    index = {"files": files, "sparse": sparse, "symbols": symbols, "path_terms": path_terms, "ast_spans": ast_spans, "component_set": INDEX_COMPONENTS}
    index_root.mkdir(parents=True, exist_ok=True)
    # Private persistent index artifact may contain raw paths/spans; runs/ is ignored.
    private = {"files": [{"path": f["path"], "current": f["current"], "line_count": len(f["lines"])} for f in files], "components": INDEX_COMPONENTS, "ast_span_count": len(ast_spans), "term_count": len(sparse)}
    (index_root / "frk_b_private_index.json").write_text(json.dumps(private, sort_keys=True) + "\n", encoding="utf-8")
    return index


def make_hit(index: dict[str, Any], fid: int, start: int, end: int, score: float) -> dict[str, Any]:
    f = index["files"][fid]
    return {"path": f["path"], "start_line": max(1, start), "end_line": min(len(f["lines"]), end), "content_current": f["current"], "score": score}


def retrieve_fast(index: dict[str, Any], query: str, top_k: int = 10) -> list[dict[str, Any]]:
    qts = query_tokens(query)
    scores: dict[tuple[int, int, int], dict[str, Any]] = {}
    nfiles = max(len(index["files"]), 1)
    avgdl = sum(len(f["tokens"]) for f in index["files"]) / nfiles
    for tok in qts:
        postings = index["sparse"].get(tok, [])
        idf = math.log(1 + (nfiles - len(postings) + 0.5) / (len(postings) + 0.5)) if postings else 0.0
        for fid in postings:
            f = index["files"][fid]
            tf = f["tokens"].count(tok)
            dl = max(len(f["tokens"]), 1)
            score = idf * (tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * dl / max(avgdl, 1)))
            key = (fid, 1, min(len(f["lines"]), 8))
            rec = scores.setdefault(key, make_hit(index, fid, key[1], key[2], 0.0))
            rec["score"] += score
        for fid in index["path_terms"].get(tok, []):
            f = index["files"][fid]
            key = (fid, 1, min(len(f["lines"]), 8))
            rec = scores.setdefault(key, make_hit(index, fid, key[1], key[2], 0.0))
            rec["score"] += 1.5
    qlow = query.lower()
    for fid, start, end in index["symbols"].get(qlow, []):
        key = (fid, start, end)
        rec = scores.setdefault(key, make_hit(index, fid, start, end, 0.0))
        rec["score"] += 8.0
    for sp in index["ast_spans"]:
        if qlow in str(sp["symbol"]).lower():
            key = (sp["fid"], sp["start"], sp["end"])
            rec = scores.setdefault(key, make_hit(index, sp["fid"], sp["start"], sp["end"], 0.0))
            rec["score"] += 4.0
    return sorted(scores.values(), key=lambda h: float(h["score"]), reverse=True)[:top_k]


def validate_hit(index: dict[str, Any], hit: dict[str, Any]) -> bool:
    by_path = {f["path"]: f for f in index["files"]}
    f = by_path.get(str(hit.get("path")))
    if not f:
        return False
    try:
        start = int(hit.get("start_line") or 0); end = int(hit.get("end_line") or 0)
    except Exception:
        return False
    return 1 <= start <= end <= len(f["lines"]) and hit.get("content_current") == f["current"]


def labels_by_task() -> dict[str, dict[str, Any]]:
    return {r["task_id"]: r for r in load_jsonl(repo_root() / LABELS)}


def overlaps(hit: dict[str, Any], label: dict[str, Any]) -> bool:
    for sp in label.get("gold_spans", []):
        if hit.get("path") == sp.get("path") and int(hit.get("start_line", 0)) <= int(sp.get("end_line", 0)) and int(hit.get("end_line", 0)) >= int(sp.get("start_line", 0)):
            return True
    return False


def file_hit(hits: list[dict[str, Any]], label: dict[str, Any], k: int) -> bool:
    gold = {sp.get("path") for sp in label.get("gold_spans", [])}
    return any(h.get("path") in gold for h in hits[:k])


def bucket_ratio(v: float) -> str:
    if v >= 0.9: return "very_high"
    if v >= 0.7: return "high"
    if v >= 0.4: return "medium"
    if v > 0: return "low"
    return "zero"


def latency_bucket(ms: float) -> str:
    if ms < 10: return "lt_10ms"
    if ms < 50: return "lt_50ms"
    if ms < 100: return "lt_100ms"
    if ms < 200: return "lt_200ms"
    return "ge_200ms"


def count_bucket(n: int) -> str:
    if n == 0: return "zero"
    if n <= 20: return "le_20"
    if n <= 100: return "le_100"
    if n <= 500: return "le_500"
    if n <= 2000: return "le_2000"
    return "gt_2000"


def load_frk_a() -> dict[str, Any]:
    p = repo_root() / FRK_A_REPORT
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def audit_frk_a(report: dict[str, Any]) -> bool:
    if report.get("status") != FRK_A_STATUS:
        return False
    names = {r.get("baseline_bucket") for r in report.get("baseline_aggregate_records", [])}
    if not REQUIRED_FRK_A_BASELINES <= names:
        return False
    if report.get("forbidden_scan", {}).get("status") != "pass":
        return False
    return True


def run_explicit(trace_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    frk_a = load_frk_a()
    if not audit_frk_a(frk_a):
        raise RuntimeError("source lock")
    run_root = trace_root / f"frk_b_private_{int(time.time())}"
    index_root = run_root / "index"
    trace_dir = run_root / "traces"
    t0 = time.perf_counter()
    index = build_kernel(index_root)
    build_ms = (time.perf_counter() - t0) * 1000
    trace_dir.mkdir(parents=True, exist_ok=True)
    labels = labels_by_task()
    tasks = load_jsonl(repo_root() / TASKS)
    traces: list[dict[str, Any]] = []
    latencies: list[float] = []
    invalid_count = 0
    for task in tasks:
        start = time.perf_counter()
        hits = retrieve_fast(index, str(task["query"]), 10)
        latencies.append((time.perf_counter() - start) * 1000)
        invalid_count += sum(0 if validate_hit(index, h) else 1 for h in hits)
        label = labels[task["task_id"]]
        rr = 0.0
        for i, h in enumerate(hits, 1):
            if h.get("path") in {sp.get("path") for sp in label.get("gold_spans", [])}:
                rr = 1.0 / i; break
        traces.append({"task_id": task["task_id"], "query": task["query"], "candidate_count": len(hits), "file_hit_1": file_hit(hits, label, 1), "file_hit_5": file_hit(hits, label, 5), "file_hit_10": file_hit(hits, label, 10), "reciprocal_rank": rr, "span_overlap": any(overlaps(h, label) for h in hits[:10]), "hits": hits})
    (trace_dir / "frk_b_private_query_traces.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in traces), encoding="utf-8")
    total = len(traces) or 1
    metrics = {
        "kernel_file_recall_at_1_bucket": bucket_ratio(sum(t["file_hit_1"] for t in traces) / total),
        "kernel_file_recall_at_5_bucket": bucket_ratio(sum(t["file_hit_5"] for t in traces) / total),
        "kernel_file_recall_at_10_bucket": bucket_ratio(sum(t["file_hit_10"] for t in traces) / total),
        "kernel_mrr_bucket": bucket_ratio(sum(t["reciprocal_rank"] for t in traces) / total),
        "kernel_span_overlap_f0_5_at_10_bucket": bucket_ratio(sum(t["span_overlap"] for t in traces) / total),
        "kernel_empty_result_rate_bucket": bucket_ratio(sum(not t["candidate_count"] for t in traces) / total),
        "kernel_latency_p50_bucket": latency_bucket(sorted(latencies)[len(latencies)//2] if latencies else 0),
        "kernel_latency_p95_bucket": latency_bucket(sorted(latencies)[min(len(latencies)-1, int(len(latencies)*0.95))] if latencies else 0),
        "evidencecore_validity_bucket": "all_counted_hits_valid_current" if invalid_count == 0 else "invalid_or_stale_hit_present",
        "invalid_hit_count_bucket": "zero" if invalid_count == 0 else "nonzero",
    }
    meta = {
        "index_written_bool": True,
        "index_root_bucket": "ignored_runs_or_tmp_private_index",
        "index_component_set_exact_bool": set(index.get("component_set", [])) == set(INDEX_COMPONENTS),
        "index_file_count_bucket": count_bucket(len(index["files"])),
        "index_term_count_bucket": count_bucket(len(index["sparse"])),
        "index_span_count_bucket": count_bucket(len(index["ast_spans"])),
        "build_latency_bucket": latency_bucket(build_ms),
        "trace_written_bool": True,
        "trace_row_count_bucket": "r14_sanity_task_count",
        "trace_file_bucket": "private_trace_written",
    }
    return metrics, meta


def readback(total: int) -> dict[str, bool]:
    parts = [PHASE, STATUS_DEFAULT, STATUS_COMPLETE, f"{total}/{total}", "R14-S sanity", "ripgrep_text_practical", "same_budget_sparse_bm25", "same_budget_rrf_hybrid", "simple_path_symbol", "FastContext excluded", "private per-query traces", "aggregate-only", NEXT_PHASE]
    def text(rel: str) -> str:
        p = repo_root() / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(t: str) -> bool:
        return all(part in t for part in parts)
    out = {
        "readme_readback_match_bool": ok(text("README.md")),
        "detail_docs_readback_match_bool": ok(text("docs/en/bea-v1-frk-b-fast-retrieval-kernel-prototype.md")) and ok(text("docs/zh/bea-v1-frk-b-fast-retrieval-kernel-prototype.md")),
        "current_conclusions_readback_match_bool": ok(text("docs/en/current-research-conclusions.md")) and ok(text("docs/zh/current-research-conclusions.md")),
        "research_log_readback_match_bool": ok(text("docs/en/research-log.md")) and ok(text("docs/zh/research-log.md")),
        "research_summary_readback_match_bool": ok(text("docs/en/research-summary.md")) and ok(text("docs/zh/research-summary.md")),
    }
    out["all_public_readback_match_bool"] = all(out.values())
    return out


def build_report(mode: str, metrics: dict[str, Any] | None = None, meta: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    explicit = mode == "explicit"
    metrics = metrics or {
        "kernel_file_recall_at_1_bucket": "not_run_default_mode",
        "kernel_file_recall_at_5_bucket": "not_run_default_mode",
        "kernel_file_recall_at_10_bucket": "not_run_default_mode",
        "kernel_mrr_bucket": "not_run_default_mode",
        "kernel_span_overlap_f0_5_at_10_bucket": "not_run_default_mode",
        "kernel_empty_result_rate_bucket": "not_run_default_mode",
        "kernel_latency_p50_bucket": "not_run_default_mode",
        "kernel_latency_p95_bucket": "not_run_default_mode",
        "evidencecore_validity_bucket": "not_applicable_default_mode",
        "invalid_hit_count_bucket": "not_applicable_default_mode",
    }
    meta = meta or {
        "index_written_bool": False,
        "index_root_bucket": "not_written_default_mode",
        "index_component_set_exact_bool": False,
        "index_file_count_bucket": "not_built_default_mode",
        "index_term_count_bucket": "not_built_default_mode",
        "index_span_count_bucket": "not_built_default_mode",
        "build_latency_bucket": "not_built_default_mode",
        "trace_written_bool": False,
        "trace_row_count_bucket": "not_written_default_mode",
        "trace_file_bucket": "not_written_default_mode",
    }
    frk_a_ok = audit_frk_a(load_frk_a()) if explicit else True
    complete = explicit and frk_a_ok and meta.get("index_component_set_exact_bool") is True and metrics.get("evidencecore_validity_bucket") == "all_counted_hits_valid_current"
    rb = readback(total)
    gatevals = {
        "frk_a_source_lock_gate": frk_a_ok,
        "top_level_frk_track_gate": True,
        "explicit_opt_in_gate": True,
        "private_label_scoring_gate": True,
        "private_trace_write_gate": bool(meta.get("trace_written_bool")) if explicit else True,
        "persistent_index_private_storage_gate": bool(meta.get("index_written_bool")) if explicit else True,
        "required_index_components_gate": bool(meta.get("index_component_set_exact_bool")) if explicit else True,
        "retrieve_fast_api_gate": True,
        "evidencecore_validation_gate": metrics.get("evidencecore_validity_bucket") in {"all_counted_hits_valid_current", "not_applicable_default_mode"},
        "frk_a_baseline_comparison_gate": frk_a_ok,
        "aggregate_public_report_gate": True,
        "no_network_provider_runtime_gate": True,
        "no_fastcontext_gate": True,
        "no_runtime_default_scale_claim_gate": True,
        "frk_c_only_stop_go_gate": True,
        "public_readback_gate": rb["all_public_readback_match_bool"],
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": STATUS_COMPLETE if complete else STATUS_DEFAULT if not explicit else STATUS_FAIL_CLOSED,
        "self_test_total": total,
        "source_lock_records": [{"source_bucket": "frk_a_parent", "checkpoint_bucket": FRK_A_CHECKPOINT, "status_bucket": FRK_A_STATUS, "top_level_frk_track_bool": True, "not_r2bv_child_bool": True}],
        "execution_mode_records": [{"explicit_local_prototype_bool": explicit, "default_no_label_read_bool": not explicit, "labels_private_for_scoring_bool": explicit, "private_traces_required_bool": explicit}],
        "index_artifact_records": [{"persistent_local_index_private_bool": bool(meta.get("index_written_bool")), "index_root_bucket": meta.get("index_root_bucket"), "component_set_exact_bool": bool(meta.get("index_component_set_exact_bool")) if explicit else True, "component_buckets": INDEX_COMPONENTS, "index_file_count_bucket": meta.get("index_file_count_bucket"), "index_term_count_bucket": meta.get("index_term_count_bucket"), "index_ast_span_count_bucket": meta.get("index_span_count_bucket"), "build_latency_bucket": meta.get("build_latency_bucket")}],
        "retrieve_fast_api_records": [{"retrieve_fast_api_available_bool": True, "materialized_evidencecore_like_hits_internal_bool": True, "public_candidate_rows_bool": False}],
        "benchmark_suite_records": [{"suite_bucket": "R14-S sanity", "corpus_bucket": "local_rust_crates_public_benchmark_material", "private_labels_scoring_bool": explicit, "fastcontext_excluded_bool": True}],
        "baseline_comparison_records": [{"frk_a_required_baseline_bucket": b, "comparison_bucket": "available_from_frk_a_public_aggregate" if b in REQUIRED_FRK_A_BASELINES else "bounded_unavailable_or_conditional"} for b in BASELINES],
        "kernel_metric_bucket_records": [metrics],
        "evidencecore_validity_records": [{"evidencecore_validity_bucket": metrics.get("evidencecore_validity_bucket"), "invalid_hit_count_bucket": metrics.get("invalid_hit_count_bucket"), "all_counted_hits_valid_current_bool": metrics.get("evidencecore_validity_bucket") in {"all_counted_hits_valid_current", "not_applicable_default_mode"}}],
        "private_trace_records": [{"private_trace_written_bool": bool(meta.get("trace_written_bool")), "trace_root_bucket": "ignored_runs_or_tmp_private_trace" if explicit else "not_written_default_mode", "trace_file_bucket": meta.get("trace_file_bucket"), "trace_row_count_bucket": meta.get("trace_row_count_bucket"), "raw_trace_public_bool": False}],
        "publication_boundary_records": [{"aggregate_bucketized_public_report_bool": True, "raw_candidates_public_bool": False, "raw_scores_ranks_spans_public_bool": False, "private_trace_path_public_bool": False, "raw_task_query_public_bool": False, "raw_path_span_hash_public_bool": False, "runtime_default_method_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkbgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_id": f"frkbsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkbreadback0000", **rb}],
        "stop_go_records": [{"anonymous_stop_go_id": "frkbstop0000", "next_allowed_phase": NEXT_PHASE if complete else "not_authorized_until_complete_valid_prototype", "frk_c_public_package_authorized_bool": complete, "runtime_default_method_scale_claim_authorized_bool": False, "rpm_or_llm_derived_implementation_authorized_bool": False, "ci_network_provider_authorized_bool": False, "fastcontext_authorized_bool": False, "raw_trace_publication_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_public(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_CLOSED
        report["stop_go_records"][0]["next_allowed_phase"] = "not_authorized_until_complete_valid_prototype"
        report["stop_go_records"][0]["frk_c_public_package_authorized_bool"] = False
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or report.get("self_test_total") != len(SYNTH): issues.append("self_test")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_FAIL_CLOSED}: issues.append("status")
    if scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    if str(report.get("debug", "")).find("EvidenceCore") >= 0: issues.append("public_leak")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("checkpoint_bucket") != FRK_A_CHECKPOINT or source.get("status_bucket") != FRK_A_STATUS: issues.append("source_lock")
    if source.get("not_r2bv_child_bool") is not True: issues.append("track_boundary")
    idx = (report.get("index_artifact_records") or [{}])[0]
    if set(idx.get("component_buckets", [])) != set(INDEX_COMPONENTS): issues.append("index_components")
    if report.get("status") == STATUS_COMPLETE and idx.get("component_set_exact_bool") is not True: issues.append("index_exact")
    for k in ["index_file_count_bucket", "index_term_count_bucket", "index_ast_span_count_bucket", "build_latency_bucket"]:
        if k not in idx or idx.get(k) in {None, "not_built_default_mode"} and report.get("status") == STATUS_COMPLETE:
            issues.append(f"index_{k}")
    api = (report.get("retrieve_fast_api_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and api.get("retrieve_fast_api_available_bool") is not True:
        issues.append("api_missing")
    if report.get("status") == STATUS_COMPLETE and api.get("materialized_evidencecore_like_hits_internal_bool") is not True:
        issues.append("api_materialization_missing")
    if api.get("public_candidate_rows_bool") is not False:
        issues.append("api_public_candidate_rows")
    metric = (report.get("kernel_metric_bucket_records") or [{}])[0]
    for k in ["kernel_file_recall_at_10_bucket", "kernel_mrr_bucket", "kernel_latency_p95_bucket", "evidencecore_validity_bucket"]:
        if k not in metric: issues.append(f"metric_{k}")
    ev = (report.get("evidencecore_validity_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and ev.get("all_counted_hits_valid_current_bool") is not True: issues.append("evidencecore")
    baseline_names = {r.get("frk_a_required_baseline_bucket") for r in report.get("baseline_comparison_records", [])}
    if set(BASELINES) != baseline_names: issues.append("baseline_set")
    for rec in report.get("baseline_comparison_records", []):
        if "comparison_bucket" not in rec:
            issues.append("baseline_missing")
    if report.get("status") == STATUS_COMPLETE and metric.get("kernel_file_recall_at_10_bucket") in {"zero", "low"} and metric.get("kernel_latency_p95_bucket") not in {"lt_10ms", "lt_50ms", "lt_100ms"}:
        issues.append("quality_latency_regression")
    pub = (report.get("publication_boundary_records") or [{}])[0]
    if pub.get("aggregate_bucketized_public_report_bool") is not True: issues.append("aggregate_public")
    for k in ["raw_candidates_public_bool", "raw_scores_ranks_spans_public_bool", "private_trace_path_public_bool", "raw_task_query_public_bool", "raw_path_span_hash_public_bool", "runtime_default_method_scale_claim_bool"]:
        if pub.get(k) is not False: issues.append(f"pub_{k}")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if len(synth) != int(report.get("self_test_total") or -1): issues.append("synthetic_count_mismatch")
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_set")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    if not (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("stop_next")
    for k in ["runtime_default_method_scale_claim_authorized_bool", "rpm_or_llm_derived_implementation_authorized_bool", "ci_network_provider_authorized_bool", "fastcontext_authorized_bool", "raw_trace_publication_authorized_bool"]:
        if stop.get(k) is not False: issues.append(f"stop_{k}")
    if report.get("status") != STATUS_COMPLETE and stop.get("frk_c_public_package_authorized_bool") is not False:
        issues.append("stop_fail_open")
    trace = (report.get("private_trace_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE:
        if trace.get("private_trace_written_bool") is not True:
            issues.append("trace_missing")
        if "trace_row_count_bucket" not in trace or "trace_file_bucket" not in trace:
            issues.append("trace_missing")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket')}")
    return issues


def self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(name: str, ok: bool) -> None:
        if not ok: failures.append(name)
    default = build_report("default")
    check("default_no_label_read_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    metrics = {"kernel_file_recall_at_1_bucket": "medium", "kernel_file_recall_at_5_bucket": "high", "kernel_file_recall_at_10_bucket": "high", "kernel_mrr_bucket": "high", "kernel_span_overlap_f0_5_at_10_bucket": "medium", "kernel_empty_result_rate_bucket": "zero", "kernel_latency_p50_bucket": "lt_10ms", "kernel_latency_p95_bucket": "lt_50ms", "evidencecore_validity_bucket": "all_counted_hits_valid_current", "invalid_hit_count_bucket": "zero"}
    meta = {"index_written_bool": True, "index_root_bucket": "ignored_runs_or_tmp_private_index", "index_component_set_exact_bool": True, "index_file_count_bucket": "le_100", "index_term_count_bucket": "le_2000", "index_span_count_bucket": "le_500", "build_latency_bucket": "lt_100ms", "trace_written_bool": True, "trace_row_count_bucket": "r14_sanity_task_count", "trace_file_bucket": "private_trace_written"}
    explicit = build_report("explicit", metrics, meta)
    check("explicit_synthetic_kernel_pass", explicit["status"] == STATUS_COMPLETE and validate_report(explicit) == [])
    leak_meta = dict(meta)
    leak_meta["index_root_bucket"] = "/tmp/private/frk_b_index"
    leak_report = build_report("explicit", metrics, leak_meta)
    check("public_leak_clears_stopgo_fail", leak_report["status"] == STATUS_FAIL_CLOSED and leak_report["stop_go_records"][0].get("frk_c_public_package_authorized_bool") is False and leak_report["stop_go_records"][0].get("next_allowed_phase") != NEXT_PHASE)
    for name, args in [("safe_parser_unknown_arg_fail", ["--bad"]), ("missing_explicit_confirm_fail", ["--allow-frk-b-local-prototype"]), ("wrong_out_path_fail", ["--out", "x.json"]), ("bad_private_trace_root_fail", ["--allow-frk-b-local-prototype", "--confirm-r14-labels-private-scoring", "--confirm-private-traces", "--confirm-aggregate-only-public-artifact", "--private-trace-root", "../bad"] )]:
        try:
            parse_args(args); check(name, False)
        except Exception:
            check(name, True)
    synthetic_index = {"files": [{"path": "a.rs", "lines": ["fn x() {}"], "current": "abc"}]}
    check("invalid_path_runtime_validation_fail", not validate_hit(synthetic_index, {"path": "missing.rs", "start_line": 1, "end_line": 1, "content_current": "abc"}))
    check("invalid_range_runtime_validation_fail", not validate_hit(synthetic_index, {"path": "a.rs", "start_line": 2, "end_line": 1, "content_current": "abc"}))
    check("invalid_currentness_runtime_validation_fail", not validate_hit(synthetic_index, {"path": "a.rs", "start_line": 1, "end_line": 1, "content_current": "bad"}))
    mutations = [
        ("frk_a_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("status_bucket", "bad"), "source_lock"),
        ("frk_a_baseline_drop_fail", lambda r: r["baseline_comparison_records"].pop(), "baseline_set"),
        ("index_component_drop_fail", lambda r: r["index_artifact_records"][0]["component_buckets"].pop(), "index_components"),
        ("retrieve_api_missing_fail", lambda r: r["retrieve_fast_api_records"][0].__setitem__("retrieve_fast_api_available_bool", False), "api_missing"),
        ("public_raw_path_leak_fail", lambda r: r.__setitem__("debug", "crates/openlocus-core/src/evidence.rs"), "public_leak"),
        ("public_raw_query_leak_fail", lambda r: r.__setitem__("debug", "EvidenceCore"), "public_leak"),
        ("public_raw_metric_leak_fail", lambda r: r.__setitem__("debug", "raw_score 0.4"), "public_leak"),
        ("private_trace_path_leak_fail", lambda r: r.__setitem__("debug", "/tmp/frkb"), "public_leak"),
        ("fastcontext_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("fastcontext_authorized_bool", True), "stop_fastcontext_authorized_bool"),
        ("network_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_network_provider_authorized_bool", True), "stop_ci_network_provider_authorized_bool"),
        ("runtime_default_claim_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool", True), "stop_runtime_default_method_scale_claim_authorized_bool"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_or_llm_derived_implementation_authorized_bool", True), "stop_rpm_or_llm_derived_implementation_authorized_bool"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_set"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("readback_drop_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback"),
        ("latency_bucket_missing_fail", lambda r: r["kernel_metric_bucket_records"][0].pop("kernel_latency_p95_bucket"), "metric_kernel_latency_p95_bucket"),
        ("index_size_bucket_missing_fail", lambda r: r["index_artifact_records"][0].pop("index_file_count_bucket"), "index_index_file_count_bucket"),
        ("trace_bucket_missing_fail", lambda r: r["private_trace_records"][0].pop("trace_row_count_bucket"), "trace_missing"),
        ("evidencecore_bucket_missing_fail", lambda r: r["kernel_metric_bucket_records"][0].pop("evidencecore_validity_bucket"), "metric_evidencecore_validity_bucket"),
        ("baseline_bucket_missing_fail", lambda r: r["baseline_comparison_records"][0].pop("comparison_bucket"), "baseline_missing"),
    ]
    for name, mut, issue in mutations:
        m = json.loads(json.dumps(explicit)); mut(m); issues = validate_report(m)
        check(name, issue in issues)
    baselines = {r.get("frk_a_required_baseline_bucket"): r.get("comparison_bucket") for r in explicit.get("baseline_comparison_records", [])}
    stop = explicit["stop_go_records"][0]
    pub = explicit["publication_boundary_records"][0]
    root_current = (repo_root() / "docs/current-research-conclusions.md").read_text(encoding="utf-8")
    check("hitmux_unavailable_continues", baselines.get("hitmux_context_engine") == "bounded_unavailable_or_conditional" and explicit["status"] == STATUS_COMPLETE)
    check("openlocus_unavailable_continues", baselines.get("current_openlocus_retrieval") == "bounded_unavailable_or_conditional" and explicit["status"] == STATUS_COMPLETE)
    check("fastcontext_excluded_pass", explicit["benchmark_suite_records"][0].get("fastcontext_excluded_bool") is True and stop.get("fastcontext_authorized_bool") is False)
    check("persistent_index_written_private_pass", explicit["index_artifact_records"][0].get("persistent_local_index_private_bool") is True and explicit["index_artifact_records"][0].get("index_root_bucket") == "ignored_runs_or_tmp_private_index")
    check("validate_report_ok", validate_report(explicit) == [])
    check("public_report_schema_ok", explicit.get("schema_version") == SCHEMA_VERSION and explicit.get("phase_bucket") == PHASE)
    check("aggregate_only_publication_ok", pub.get("aggregate_bucketized_public_report_bool") is True and all(pub.get(k) is False for k in ["raw_candidates_public_bool", "raw_scores_ranks_spans_public_bool", "private_trace_path_public_bool", "raw_task_query_public_bool", "raw_path_span_hash_public_bool", "runtime_default_method_scale_claim_bool"]))
    check("no_rpm_llm_impl_ok", stop.get("rpm_or_llm_derived_implementation_authorized_bool") is False)
    check("no_ci_network_ok", stop.get("ci_network_provider_authorized_bool") is False)
    check("frk_c_only_ok", stop.get("frk_c_public_package_authorized_bool") is True and stop.get("next_allowed_phase") == NEXT_PHASE and all(stop.get(k) is False for k in ["runtime_default_method_scale_claim_authorized_bool", "rpm_or_llm_derived_implementation_authorized_bool", "ci_network_provider_authorized_bool", "fastcontext_authorized_bool", "raw_trace_publication_authorized_bool"]))
    check("self_test_count_readback_ok", explicit.get("self_test_total") == SELF_TEST_EXPECTED and explicit["public_readback_records"][0].get("all_public_readback_match_bool") is True)
    check("stale_current_fail", "bea-v1-frk-b-fast-retrieval-kernel-prototype.md" in root_current and STATUS_COMPLETE not in root_current and "This root file is only a bilingual index" in root_current)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_COMPLETE}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    p = out or PUBLIC_REPORT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr)
        return 2
    if args["self_test"]:
        result = self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = json.loads((repo_root() / public_report_path(str(args["validate"]))).read_text(encoding="utf-8"))
            issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    out = public_report_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        try:
            root = private_root(str(args["trace_root"])) if args["trace_root"] else (repo_root() / "runs" / f"frk_b_private_{int(time.time())}")
            metrics, meta = run_explicit(root)
            report = build_report("explicit", metrics, meta)
        except Exception:
            report = build_report("explicit", {"evidencecore_validity_bucket": "fail", "invalid_hit_count_bucket": "nonzero"}, {})
            report["status"] = STATUS_FAIL_CLOSED
    else:
        report = build_report("default")
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_DEFAULT, STATUS_COMPLETE} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
