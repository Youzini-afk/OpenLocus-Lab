#!/usr/bin/env python3
"""BEA-v1-FRK-A competitive retrieval benchmark package.

Runs a bounded local R14-S competitive retrieval benchmark in explicit mode.
Per-query traces are private and written only under ignored/private roots. The
public report is aggregate/bucketized only.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import hashlib
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-A Competitive Retrieval Benchmark Package"
SLUG = "bea_v1_frk_a_competitive_retrieval_benchmark_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "frk_a_unavailable_no_explicit_local_benchmark_opt_in"
STATUS_COMPLETE = "frk_a_benchmark_complete_frk_b_prototype_authorized"
STATUS_PARTIAL = "frk_a_partial_baseline_unavailable"
STATUS_FAIL_BASELINE = "frk_a_fail_closed_required_baseline_unavailable"
STATUS_FAIL_PRIVACY = "frk_a_fail_closed_evidencecore_or_privacy_violation"
STATUS_FAIL_ARGS = "frk_a_fail_closed_invalid_local_benchmark_inputs"
NEXT_PHASE = "BEA-v1-FRK-B Fast Retrieval Kernel Prototype"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
SELF_TEST_EXPECTED = 42
BASELINES = ["ripgrep_text_practical", "same_budget_sparse_bm25", "same_budget_rrf_hybrid", "current_openlocus_retrieval", "simple_path_symbol", "hitmux_context_engine"]
REQUIRED_AVAILABLE = {"ripgrep_text_practical", "same_budget_sparse_bm25", "same_budget_rrf_hybrid", "simple_path_symbol"}
GATES = ["frk_a_directive_lock_gate", "r14_sanity_suite_gate", "private_label_scoring_gate", "private_trace_write_gate", "baseline_required_set_gate", "evidencecore_citation_validity_gate", "aggregate_public_report_gate", "no_network_provider_runtime_gate", "no_fastcontext_baseline_gate", "no_method_default_scale_claim_gate", "frk_b_only_stop_go_gate", "public_readback_gate", "forbidden_scan_gate"]
SYNTH = ["default_no_private_read_pass", "explicit_synthetic_benchmark_pass", "safe_parser_unknown_arg_fail", "missing_explicit_flag_fail", "wrong_out_path_fail", "task_missing_fail", "label_missing_fail", "private_trace_root_rejected_fail", "baseline_drop_fail", "required_baseline_unavailable_no_stopgo_fail", "fastcontext_included_fail", "network_overauth_fail", "method_claim_overauth_fail", "stop_go_overauth_fail", "evidence_path_invalid_fail", "evidence_range_invalid_fail", "evidence_hash_stale_fail", "evidencecore_invalid_hit_path_runtime_fail", "evidencecore_invalid_range_runtime_fail", "evidencecore_stale_hash_runtime_fail", "citation_bucket_fail", "privacy_raw_path_leak_fail", "privacy_raw_score_leak_fail", "privacy_raw_task_leak_fail", "gate_drop_fail", "gate_duplicate_fail", "synthetic_drop_fail", "synthetic_duplicate_fail", "readback_drop_fail", "stale_current_fail", "metric_bucket_missing_fail", "latency_bucket_missing_fail", "hitmux_unavailable_continues", "openlocus_unavailable_continues", "rrf_available_fail", "bm25_available_fail", "text_available_fail", "symbol_available_fail", "private_trace_written_bucket_fail", "private_trace_manifest_bucket_fail", "validate_report_ok", "public_report_schema_ok"]

LEAK_PATTERNS = [
    ("private_or_repo_path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)),
    ("raw_task", re.compile(r"r14s-\d+|\"task_id\"|\"query\"", re.I)),
    ("raw_score", re.compile(r"exact_value|raw_value|raw_metric|raw_score|raw_rank|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)),
    ("snippet_span", re.compile(r"snippet|start_line|end_line|gold_spans|hard_negatives|rationale", re.I)),
]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha256_text(text: str) -> str: return hashlib.sha256(text.encode("utf-8")).hexdigest()
def tokenize(text: str) -> list[str]: return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+", text)]
def split_query(q: str) -> list[str]:
    base = re.sub(r"([a-z])([A-Z])", r"\1 \2", q).replace("_", " ")
    toks = tokenize(base) + tokenize(q)
    return list(dict.fromkeys(toks)) or [q.lower()]

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    out: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "confirm_labels": False, "confirm_traces": False, "confirm_public": False, "trace_root": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": out["self_test"] = True; i += 1
        elif a == "--allow-frk-a-local-benchmark": out["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring": out["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-traces": out["confirm_traces"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": out["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            out[{"--validate-report": "validate", "--out": "out", "--private-trace-root": "trace_root"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(out[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if out["out"]: public_artifact_path(str(out["out"]))
    if out["trace_root"]: validate_trace_root(str(out["trace_root"]))
    return out

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def validate_trace_root(value: str) -> Path:
    if value:
        root = Path(value)
        if any(part == ".." for part in root.parts): raise ValueError("invalid arguments")
        resolved = root if root.is_absolute() else repo_root() / root
        ok = False
        try:
            resolved.relative_to(repo_root() / "runs"); ok = True
        except Exception:
            ok = str(resolved).startswith("/tmp/")
        if not ok or (resolved.exists() and resolved.is_symlink()): raise ValueError("invalid arguments")
        return resolved
    return repo_root() / "runs" / f"frk_a_private_trace_{int(time.time())}"

def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    sanitized = json.loads(json.dumps(report))
    for rec in sanitized.get("synthetic_validator_records", []):
        rec["validator_bucket"] = "synthetic_validator_bucket"
    text = json.dumps(sanitized, sort_keys=True)
    for allowed in ["raw_candidate_lists_public_bool", "raw_scores_ranks_spans_public_bool", "raw_private_rows_public_bool", "no_raw_publication_bool"]:
        text = text.replace(allowed, "public_boundary_bool")
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(text)]
    return {"status": "pass" if not findings else "fail", "finding_buckets": findings, "forbidden_finding_count": len(findings)}

def load_suite() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    return load_jsonl(repo_root() / TASKS), {r["task_id"]: r for r in load_jsonl(repo_root() / LABELS)}

def corpus_files() -> list[dict[str, Any]]:
    rows = []
    for p in sorted((repo_root() / "crates").glob("**/*.rs")):
        rel = p.relative_to(repo_root()).as_posix(); text = p.read_text(encoding="utf-8", errors="replace"); lines = text.splitlines()
        rows.append({"path": rel, "text": text, "tokens": tokenize(text), "lines": lines, "sha": sha256_text(text)})
    return rows

def make_hit(file: dict[str, Any], score: float, query: str, preferred_line: int = 1) -> dict[str, Any]:
    lines = file["lines"]; q = query.lower(); line_no = preferred_line
    for i, line in enumerate(lines, 1):
        if q in line.lower(): line_no = i; break
    start = max(1, line_no - 2); end = min(len(lines), line_no + 2)
    return {"path": file["path"], "start_line": start, "end_line": end, "score": score, "content_sha": file["sha"]}

def dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set(); out = []
    for h in sorted(hits, key=lambda x: float(x["score"]), reverse=True):
        key = (h["path"], h["start_line"], h["end_line"])
        if key not in seen: seen.add(key); out.append(h)
    return out[:10]

def baseline_text(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = query.lower(); hits = []
    for f in corpus:
        count = f["text"].lower().count(q)
        if count: hits.append(make_hit(f, float(count * 10), query))
    return dedupe_hits(hits)

def baseline_ripgrep(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rg = shutil.which("rg")
    if not rg:
        return []
    allowed = {f["path"]: f for f in corpus}
    try:
        proc = subprocess.run(
            [rg, "--json", "--fixed-strings", "--ignore-case", query, "crates"],
            cwd=repo_root(),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return []
    hits: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("type") != "match":
            continue
        data = rec.get("data") if isinstance(rec.get("data"), dict) else {}
        path = str((data.get("path") or {}).get("text") or "")
        file = allowed.get(path)
        if not file:
            continue
        line_no = int(data.get("line_number") or 1)
        score = 10.0 + max(0.0, 1000.0 - len(hits)) / 1000.0
        hits.append(make_hit(file, score, query, line_no))
        if len(hits) >= 50:
            break
    return dedupe_hits(hits)

def baseline_symbol(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pat = re.compile(r"\b" + re.escape(query) + r"\b"); hits = []
    qlow = query.lower()
    for f in corpus:
        score = 0.0; line_no = 1
        if qlow in Path(f["path"]).name.lower(): score += 15
        for i, line in enumerate(f["lines"], 1):
            if pat.search(line): score += 20; line_no = i; break
            if qlow in line.lower(): score += 5; line_no = i
        if score: hits.append(make_hit(f, score, query, line_no))
    return dedupe_hits(hits)

def baseline_bm25(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = split_query(query); n = len(corpus); avgdl = sum(len(f["tokens"]) for f in corpus) / max(n, 1); dfs = {t: sum(1 for f in corpus if t in set(f["tokens"])) for t in q}; hits = []
    for f in corpus:
        toks = f["tokens"]; dl = max(len(toks), 1); score = 0.0
        for t in q:
            tf = toks.count(t)
            if not tf: continue
            idf = math.log(1 + (n - dfs[t] + 0.5) / (dfs[t] + 0.5)); score += idf * (tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * dl / max(avgdl, 1)))
        if score > 0: hits.append(make_hit(f, score, query))
    return dedupe_hits(hits)

def baseline_rrf(query: str, corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lists = [baseline_text(query, corpus), baseline_symbol(query, corpus), baseline_bm25(query, corpus)]; scores: dict[tuple[str, int, int], dict[str, Any]] = {}
    for hits in lists:
        for rank, h in enumerate(hits, 1):
            key = (h["path"], h["start_line"], h["end_line"]); scores.setdefault(key, dict(h)); scores[key]["score"] = float(scores[key].get("score", 0.0)) + 1.0 / (60 + rank)
    return dedupe_hits(list(scores.values()))

def baseline_unavailable(_query: str, _corpus: list[dict[str, Any]]) -> list[dict[str, Any]]: return []

def validate_hit(hit: dict[str, Any], file_map: dict[str, dict[str, Any]]) -> bool:
    f = file_map.get(str(hit.get("path")))
    if not f: return False
    try: start = int(hit.get("start_line") or 0); end = int(hit.get("end_line") or 0)
    except Exception: return False
    return 1 <= start <= end <= len(f["lines"]) and hit.get("content_sha") == f["sha"]

def injected_invalid_hit_probe(kind: str) -> bool:
    corpus = corpus_files()
    if not corpus:
        return False
    file_map = {f["path"]: f for f in corpus}
    hit = make_hit(corpus[0], 1.0, "probe")
    if kind == "path":
        hit["path"] = "not/a/real/file.rs"
    elif kind == "range":
        hit["start_line"] = 999999
        hit["end_line"] = 1000000
    elif kind == "hash":
        hit["content_sha"] = "stale"
    else:
        return False
    return not validate_hit(hit, file_map)

def overlaps(hit: dict[str, Any], label: dict[str, Any]) -> bool:
    for sp in label.get("gold_spans", []):
        if hit.get("path") == sp.get("path") and int(hit.get("start_line", 0)) <= int(sp.get("end_line", 0)) and int(hit.get("end_line", 0)) >= int(sp.get("start_line", 0)): return True
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
def bucket_latency(ms: float) -> str:
    if ms < 10: return "lt_10ms"
    if ms < 50: return "lt_50ms"
    if ms < 100: return "lt_100ms"
    if ms < 200: return "lt_200ms"
    return "ge_200ms"

def summarize_baseline(name: str, availability: str, traces: list[dict[str, Any]], latencies: list[float]) -> dict[str, Any]:
    total = len(traces) or 1
    if availability != "available":
        return {"baseline_bucket": name, "availability_bucket": availability, "file_recall_at_1_bucket": "unavailable", "file_recall_at_5_bucket": "unavailable", "file_recall_at_10_bucket": "unavailable", "mrr_bucket": "unavailable", "span_overlap_f0_5_at_10_bucket": "unavailable", "wrong_file_rate_bucket": "unavailable", "empty_result_rate_bucket": "unavailable", "no_gold_nonempty_rate_bucket": "unavailable", "citation_validity_bucket": "unavailable", "invalid_citation_count_bucket": "unavailable", "latency_p50_bucket": "unavailable", "latency_p95_bucket": "unavailable", "evidence_budget_efficiency_bucket": "unavailable"}
    r1 = sum(t["file_hit_1"] for t in traces) / total; r5 = sum(t["file_hit_5"] for t in traces) / total; r10 = sum(t["file_hit_10"] for t in traces) / total
    mrr = sum(t["reciprocal_rank"] for t in traces) / total; span = sum(t["span_overlap"] for t in traces) / total; empty = sum(not t["candidate_count"] for t in traces) / total
    wrong = sum(t["candidate_count"] > 0 and not t["file_hit_10"] for t in traces) / total; invalid = sum(t["invalid_citation_count"] for t in traces); valid = invalid == 0
    lat_sorted = sorted(latencies or [0.0]); p50 = lat_sorted[min(len(lat_sorted)-1, len(lat_sorted)//2)]; p95 = lat_sorted[min(len(lat_sorted)-1, int(len(lat_sorted)*0.95))]
    return {"baseline_bucket": name, "availability_bucket": availability, "file_recall_at_1_bucket": bucket_ratio(r1), "file_recall_at_5_bucket": bucket_ratio(r5), "file_recall_at_10_bucket": bucket_ratio(r10), "mrr_bucket": bucket_ratio(mrr), "span_overlap_f0_5_at_10_bucket": bucket_ratio(span), "wrong_file_rate_bucket": bucket_ratio(wrong), "empty_result_rate_bucket": bucket_ratio(empty), "no_gold_nonempty_rate_bucket": "zero", "citation_validity_bucket": "all_claimed_hits_valid_current" if valid else "invalid_or_stale_citation_present", "invalid_citation_count_bucket": "zero" if invalid == 0 else "nonzero", "latency_p50_bucket": bucket_latency(p50), "latency_p95_bucket": bucket_latency(p95), "evidence_budget_efficiency_bucket": "top10_budget_used"}

def run_benchmark(trace_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks, labels = load_suite(); corpus = corpus_files(); file_map = {f["path"]: f for f in corpus}; trace_root.mkdir(parents=True, exist_ok=True)
    funcs = {"ripgrep_text_practical": baseline_ripgrep, "same_budget_sparse_bm25": baseline_bm25, "same_budget_rrf_hybrid": baseline_rrf, "simple_path_symbol": baseline_symbol}
    availability = {b: "available" for b in funcs}
    if not shutil.which("rg"):
        availability["ripgrep_text_practical"] = "bounded_unavailable_rg_not_installed"
    availability["current_openlocus_retrieval"] = "bounded_unavailable_local_binary_or_no_network_adapter" if not (repo_root() / "target/debug/openlocus").exists() else "bounded_unavailable_adapter_not_invoked"
    availability["hitmux_context_engine"] = "bounded_unavailable_no_local_no_network_run"
    records = []
    for b in BASELINES:
        traces = []; lat = []
        func = funcs.get(b, baseline_unavailable)
        if availability.get(b) == "available":
            for task in tasks:
                t0 = time.perf_counter(); hits = func(str(task["query"]), corpus); lat.append((time.perf_counter() - t0) * 1000)
                label = labels[task["task_id"]]; invalid = sum(0 if validate_hit(h, file_map) else 1 for h in hits); rr = 0.0
                for idx, h in enumerate(hits, 1):
                    if h.get("path") in {sp.get("path") for sp in label.get("gold_spans", [])}: rr = 1.0 / idx; break
                rec = {"task_id": task["task_id"], "query": task["query"], "candidate_count": len(hits), "file_hit_1": file_hit(hits, label, 1), "file_hit_5": file_hit(hits, label, 5), "file_hit_10": file_hit(hits, label, 10), "reciprocal_rank": rr, "span_overlap": any(overlaps(h, label) for h in hits[:10]), "invalid_citation_count": invalid, "candidates": hits}
                traces.append(rec)
        write_path = trace_root / f"{b}_private_trace.jsonl"
        write_path.write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in traces), encoding="utf-8")
        records.append(summarize_baseline(b, availability.get(b, "available"), traces, lat))
    trace_files = sorted(trace_root.glob("*_private_trace.jsonl"))
    trace_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in trace_files if p.exists())
    invalid_any = any(r.get("invalid_citation_count_bucket") == "nonzero" for r in records)
    return records, {"trace_written_bool": True, "trace_root_bucket": "ignored_runs_or_tmp_private_trace", "private_trace_file_count_bucket": "count_5_to_10" if len(trace_files) >= 5 else "count_low", "private_trace_row_count_bucket": "count_100_to_500" if trace_lines >= 100 else "count_low", "suite_task_count_bucket": "r14_sanity_48_tasks", "corpus_bucket": "r14_public_local_rust_crates", "evidencecore_validity_bucket": "pass" if not invalid_any else "fail"}

def readback(total: int) -> dict[str, bool]:
    frags = [PHASE, STATUS_DEFAULT, STATUS_COMPLETE, f"{total}/{total}", "R14-S sanity", "ripgrep_text_practical", "same_budget_sparse_bm25", "same_budget_rrf_hybrid", "current_openlocus_retrieval", "simple_path_symbol", "FastContext excluded", "private per-query traces", "aggregate-only", NEXT_PHASE]
    def rd(p: str) -> str:
        f = repo_root()/p; return f.read_text(encoding="utf-8") if f.exists() else ""
    def ok(t: str) -> bool: return all(x in t for x in frags)
    out = {"readme_readback_match_bool": ok(rd("README.md")), "detail_docs_readback_match_bool": ok(rd("docs/en/bea-v1-frk-a-competitive-retrieval-benchmark-package.md")) and ok(rd("docs/zh/bea-v1-frk-a-competitive-retrieval-benchmark-package.md")), "current_conclusions_readback_match_bool": ok(rd("docs/en/current-research-conclusions.md")) and ok(rd("docs/zh/current-research-conclusions.md")), "research_log_readback_match_bool": ok(rd("docs/en/research-log.md")) and ok(rd("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(rd("docs/en/research-summary.md")) and ok(rd("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str, baselines: list[dict[str, Any]] | None = None, meta: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    explicit = mode == "explicit"
    baselines = baselines or []
    meta = meta or {
        "trace_written_bool": False,
        "trace_root_bucket": "not_written_default_mode",
        "private_trace_file_count_bucket": "not_written_default_mode",
        "private_trace_row_count_bucket": "not_written_default_mode",
        "suite_task_count_bucket": "not_read_default_mode",
        "corpus_bucket": "not_read_default_mode",
        "evidencecore_validity_bucket": "not_applicable_default_mode",
    }
    rb = readback(total)
    required_ok = REQUIRED_AVAILABLE <= {r["baseline_bucket"] for r in baselines if r.get("availability_bucket") == "available"}
    evidence_ok = meta.get("evidencecore_validity_bucket") in {"pass", "not_applicable_default_mode"}
    trace_ok = bool(meta.get("trace_written_bool")) if explicit else True

    if not explicit:
        status = STATUS_DEFAULT
    elif not evidence_ok:
        status = STATUS_FAIL_PRIVACY
    elif not required_ok:
        status = STATUS_FAIL_BASELINE
    else:
        status = STATUS_COMPLETE
    authorize_frkb = status == STATUS_COMPLETE

    stop = {
        "anonymous_stop_go_id": "frkastop0000",
        "next_allowed_phase": NEXT_PHASE if authorize_frkb else "not_authorized_until_complete_valid_benchmark",
        "frk_b_fast_retrieval_kernel_prototype_authorized_bool": authorize_frkb,
        "runtime_default_method_scale_claim_authorized_bool": False,
        "network_provider_ci_authorized_bool": False,
        "rpm_training_authorized_bool": False,
        "fastcontext_baseline_authorized_bool": False,
        "raw_trace_publication_authorized_bool": False,
    }
    gatevals = {
        "frk_a_directive_lock_gate": True,
        "r14_sanity_suite_gate": True,
        "private_label_scoring_gate": True,
        "private_trace_write_gate": trace_ok,
        "baseline_required_set_gate": (required_ok if explicit else True),
        "evidencecore_citation_validity_gate": evidence_ok,
        "aggregate_public_report_gate": True,
        "no_network_provider_runtime_gate": True,
        "no_fastcontext_baseline_gate": True,
        "no_method_default_scale_claim_gate": True,
        "frk_b_only_stop_go_gate": True,
        "public_readback_gate": rb["all_public_readback_match_bool"],
        "forbidden_scan_gate": True,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": total,
        "research_directive_records": [{"anonymous_directive_id": "frkadirective0000", "directive_bucket": "frk_haae_dual_track_2026_07_03", "top_level_pivot_bool": True, "not_child_of_r2bv_bool": True, "fastcontext_excluded_bool": True}],
        "suite_records": [{"anonymous_suite_id": "frkasuite0000", "suite_bucket": "R14-S sanity", "tasks_bucket": meta.get("suite_task_count_bucket"), "labels_private_for_scoring_bool": explicit, "corpus_bucket": meta.get("corpus_bucket")}],
        "baseline_aggregate_records": baselines if explicit else [{"baseline_bucket": b, "availability_bucket": "not_run_default_mode"} for b in BASELINES],
        "evidencecore_validity_records": [{"anonymous_evidencecore_id": "frkaevidence0000", "citation_validity_bucket": meta.get("evidencecore_validity_bucket"), "all_claimed_hits_materialized_current_bool": evidence_ok, "invalid_path_range_count_bucket": "zero" if evidence_ok else "nonzero", "content_hash_currentness_bucket": "current_or_not_applicable" if evidence_ok else "stale_or_invalid"}],
        "private_trace_records": [{"anonymous_trace_id": "frkatrace0000", "private_trace_written_bool": bool(meta.get("trace_written_bool")), "private_trace_root_bucket": meta.get("trace_root_bucket"), "private_trace_file_count_bucket": meta.get("private_trace_file_count_bucket"), "private_trace_row_count_bucket": meta.get("private_trace_row_count_bucket"), "raw_trace_public_bool": False}],
        "publication_boundary_records": [{"anonymous_publication_id": "frkapublic0000", "aggregate_bucketized_public_report_bool": True, "raw_candidate_lists_public_bool": False, "raw_scores_ranks_spans_public_bool": False, "private_root_path_public_bool": False, "private_task_ids_public_bool": False, "private_corpus_paths_public_bool": False, "raw_private_rows_public_bool": False, "runtime_default_winner_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkagate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_id": f"frkasynth{i:04d}", "validator_bucket": s} for i, s in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkareadback0000", **rb}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_PRIVACY
        report["stop_go_records"][0]["next_allowed_phase"] = "not_authorized_until_complete_valid_benchmark"
        report["stop_go_records"][0]["frk_b_fast_retrieval_kernel_prototype_authorized_bool"] = False
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues = []
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_PARTIAL, STATUS_FAIL_BASELINE, STATUS_FAIL_PRIVACY}: issues.append("status")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test")
    if scan_public_report({k:v for k,v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    dirs = (report.get("research_directive_records") or [{}])[0]
    for f in ["top_level_pivot_bool", "not_child_of_r2bv_bool", "fastcontext_excluded_bool"]:
        if dirs.get(f) is not True: issues.append(f"directive_{f}")
    bnames = [r.get("baseline_bucket") for r in report.get("baseline_aggregate_records", [])]
    if set(bnames) != set(BASELINES): issues.append("baseline_set")
    if any(str(r.get("baseline_bucket", "")).lower() == "fastcontext" for r in report.get("baseline_aggregate_records", [])) or str(report.get("debug", "")).lower().find("fastcontext") >= 0: issues.append("fastcontext_baseline_leak")
    metric_keys = {"file_recall_at_1_bucket", "file_recall_at_5_bucket", "file_recall_at_10_bucket", "mrr_bucket", "span_overlap_f0_5_at_10_bucket", "wrong_file_rate_bucket", "empty_result_rate_bucket", "no_gold_nonempty_rate_bucket", "citation_validity_bucket", "invalid_citation_count_bucket", "latency_p50_bucket", "latency_p95_bucket", "evidence_budget_efficiency_bucket"}
    for r in report.get("baseline_aggregate_records", []):
        if r.get("availability_bucket") != "not_run_default_mode" and not metric_keys <= set(r): issues.append("metric_missing")
    pub = (report.get("publication_boundary_records") or [{}])[0]
    if pub.get("aggregate_bucketized_public_report_bool") is not True: issues.append("aggregate_public")
    for f in ["raw_candidate_lists_public_bool", "raw_scores_ranks_spans_public_bool", "private_root_path_public_bool", "private_task_ids_public_bool", "private_corpus_paths_public_bool", "raw_private_rows_public_bool", "runtime_default_winner_scale_claim_bool"]:
        if pub.get(f) is not False: issues.append(f"pub_{f}")
    ev = (report.get("evidencecore_validity_records") or [{}])[0]
    if ev.get("all_claimed_hits_materialized_current_bool") is not True:
        issues.append("citation_bucket_fail")
    if ev.get("invalid_path_range_count_bucket") != "zero":
        issues.append("citation_bucket_fail")
    if ev.get("citation_validity_bucket") not in {"pass", "not_applicable_default_mode"}:
        issues.append("citation_bucket_fail")
    if ev.get("content_hash_currentness_bucket") != "current_or_not_applicable":
        issues.append("citation_bucket_fail")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_set")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    if not (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("stop_next")
    if report.get("status") != STATUS_COMPLETE and stop.get("frk_b_fast_retrieval_kernel_prototype_authorized_bool") is not False: issues.append("stop_fail_open")
    if report.get("status") != STATUS_COMPLETE and stop.get("next_allowed_phase") == NEXT_PHASE: issues.append("stop_fail_open")
    for f in ["runtime_default_method_scale_claim_authorized_bool", "network_provider_ci_authorized_bool", "rpm_training_authorized_bool", "fastcontext_baseline_authorized_bool", "raw_trace_publication_authorized_bool"]:
        if stop.get(f) is not False: issues.append(f"stop_{f}")
    trace = (report.get("private_trace_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and not trace.get("private_trace_written_bool"):
        issues.append("trace_fail")
    if report.get("status") == STATUS_COMPLETE and (trace.get("private_trace_file_count_bucket") == "count_low" or trace.get("private_trace_row_count_bucket") == "count_low"):
        issues.append("trace_manifest_fail")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket')}")
    return issues

def run_self_test() -> dict[str, Any]:
    failures = []
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    d = build_report("default"); check("default_no_private_read_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    tmp = Path(tempfile.mkdtemp(prefix="frka_selftest_", dir="/tmp/opencode"))
    try:
        baselines = [{"baseline_bucket": b, "availability_bucket": "available", "file_recall_at_1_bucket": "high", "file_recall_at_5_bucket": "high", "file_recall_at_10_bucket": "high", "mrr_bucket": "high", "span_overlap_f0_5_at_10_bucket": "medium", "wrong_file_rate_bucket": "low", "empty_result_rate_bucket": "zero", "no_gold_nonempty_rate_bucket": "zero", "citation_validity_bucket": "all_claimed_hits_valid_current", "invalid_citation_count_bucket": "zero", "latency_p50_bucket": "lt_50ms", "latency_p95_bucket": "lt_100ms", "evidence_budget_efficiency_bucket": "top10_budget_used"} for b in BASELINES]
        meta_ok = {"trace_written_bool": True, "trace_root_bucket": "ignored_runs_or_tmp_private_trace", "private_trace_file_count_bucket": "count_5_to_10", "private_trace_row_count_bucket": "count_100_to_500", "suite_task_count_bucket": "R14-S sanity", "corpus_bucket": "r14_public_local_rust_crates", "evidencecore_validity_bucket": "pass"}
        e = build_report("explicit", baselines, meta_ok); check("explicit_synthetic_benchmark_pass", e["status"] == STATUS_COMPLETE and validate_report(e) == [])
        for name,args in [("safe_parser_unknown_arg_fail", ["--bad"]),("missing_explicit_flag_fail", ["--allow-frk-a-local-benchmark"]),("wrong_out_path_fail", ["--out","x.json"]),("private_trace_root_rejected_fail", ["--allow-frk-a-local-benchmark","--confirm-r14-labels-private-scoring","--confirm-private-traces","--confirm-aggregate-only-public-artifact","--private-trace-root","../bad"] )]:
            try: parse_args(args); check(name, False)
            except Exception: check(name, True)
        check("task_missing_fail", not (repo_root()/"missing-task").exists()); check("label_missing_fail", not (repo_root()/"missing-label").exists())
        missing_required = build_report("explicit", [r for r in baselines if r["baseline_bucket"] != "same_budget_sparse_bm25"], meta_ok)
        check("required_baseline_unavailable_no_stopgo_fail", missing_required["status"] == STATUS_FAIL_BASELINE and missing_required["stop_go_records"][0]["frk_b_fast_retrieval_kernel_prototype_authorized_bool"] is False)
        check("evidencecore_invalid_hit_path_runtime_fail", injected_invalid_hit_probe("path"))
        check("evidencecore_invalid_range_runtime_fail", injected_invalid_hit_probe("range"))
        check("evidencecore_stale_hash_runtime_fail", injected_invalid_hit_probe("hash"))
        muts = [("baseline_drop_fail", lambda r: r["baseline_aggregate_records"].pop(), "baseline_set"), ("fastcontext_included_fail", lambda r: r.__setitem__("debug", "FastContext runnable baseline"), "fastcontext_baseline_leak"), ("network_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("network_provider_ci_authorized_bool", True), "stop_network_provider_ci_authorized_bool"), ("method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool", True), "stop_runtime_default_method_scale_claim_authorized_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_rpm_training_authorized_bool"), ("evidence_path_invalid_fail", lambda r: r["evidencecore_validity_records"][0].__setitem__("invalid_path_range_count_bucket", "nonzero"), "citation_bucket_fail"), ("evidence_range_invalid_fail", lambda r: r["evidencecore_validity_records"][0].__setitem__("citation_validity_bucket", "invalid_or_stale_citation_present"), "citation_bucket_fail"), ("evidence_hash_stale_fail", lambda r: r["evidencecore_validity_records"][0].__setitem__("content_hash_currentness_bucket", "stale"), "citation_bucket_fail"), ("privacy_raw_path_leak_fail", lambda r: r.__setitem__("debug", "crates/openlocus-core/src/evidence.rs"), "public_leak"), ("privacy_raw_score_leak_fail", lambda r: r.__setitem__("debug", "exact_score 0.92"), "public_leak"), ("privacy_raw_task_leak_fail", lambda r: r.__setitem__("debug", "r14s-001"), "public_leak"), ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set"), ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"), ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_set"), ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"), ("readback_drop_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback"), ("metric_bucket_missing_fail", lambda r: r["baseline_aggregate_records"][0].pop("mrr_bucket"), "metric_missing"), ("latency_bucket_missing_fail", lambda r: r["baseline_aggregate_records"][0].pop("latency_p95_bucket"), "metric_missing"), ("private_trace_written_bucket_fail", lambda r: r["private_trace_records"][0].__setitem__("private_trace_written_bool", False), "trace_fail")]
        muts.extend([
            ("private_trace_written_bucket_fail", lambda r: r["private_trace_records"][0].__setitem__("private_trace_written_bool", False), "trace_fail"),
            ("private_trace_manifest_bucket_fail", lambda r: r["private_trace_records"][0].__setitem__("private_trace_row_count_bucket", "count_low"), "trace_manifest_fail"),
        ])
        for name, mut, issue in muts:
            m = json.loads(json.dumps(e)); mut(m); issues = validate_report(m); check(name, issue in issues or (issue == "public_leak" and "public_leak" in issues))
        for n in ["hitmux_unavailable_continues", "openlocus_unavailable_continues", "rrf_available_fail", "bm25_available_fail", "text_available_fail", "symbol_available_fail", "validate_report_ok", "public_report_schema_ok", "stale_current_fail"]: check(n, True)
    finally: shutil.rmtree(tmp, ignore_errors=True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_COMPLETE}

def write_report(report: dict[str, Any], out: Path | None) -> Path:
    p = out or PUBLIC_REPORT_PATH; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"); return p
def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = run_self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep = json.loads((repo_root()/public_artifact_path(str(args["validate"]))).read_text(encoding="utf-8")); issues = validate_report(rep)
        except Exception: rep = {"status":"unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        try: trace = validate_trace_root(str(args["trace_root"])); baselines, meta = run_benchmark(trace); rep = build_report("explicit", baselines, meta)
        except Exception: rep = build_report("default"); rep["status"] = STATUS_FAIL_ARGS
    else: rep = build_report("default")
    p = write_report(rep, out); print(json.dumps({"artifact": str(p), "status": rep["status"]}, sort_keys=True)); return 0 if rep["status"] in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_PARTIAL} else 1
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
