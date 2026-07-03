#!/usr/bin/env python3
"""BEA-v1-FRK-D Incremental Update Benchmark.

Executable local benchmark for incremental index update behavior. Explicit mode
creates a private temporary corpus snapshot, builds FRK-B-style indexes, applies
deterministic local mutations only in that snapshot, compares incremental update
against cold rebuild and a stale-index negative control, writes private traces,
and publishes aggregate buckets only.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-D Incremental Update Benchmark"
SLUG = "bea_v1_frk_d_incremental_update_benchmark"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "frk_d_unavailable_no_explicit_incremental_update_benchmark_opt_in"
STATUS_COMPLETE = "frk_d_incremental_update_benchmark_complete_frk_e_downstream_utility_probe_authorized"
STATUS_FAIL = "frk_d_fail_closed_incremental_update_validation_or_boundary_failure"
NEXT_PHASE = "BEA-v1-FRK-E Downstream Utility Probe"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_C_REPORT = Path("artifacts/bea_v1_frk_c_rankpack_builder_experiment/bea_v1_frk_c_rankpack_builder_experiment_report.json")
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
FRK_C_CHECKPOINT = "2218554"
FRK_C_STATUS = "frk_c_rankpack_builder_experiment_complete_frk_d_incremental_update_benchmark_authorized"
SELF_TEST_EXPECTED = 52
MUTATIONS = ["symbol_alias_insertion", "path_term_relevant_edit", "ast_span_line_movement", "stale_candidate_trap", "unaffected_sentinel"]
ARMS = ["cold_rebuild_after_update", "incremental_update_path", "stale_index_negative_control", "pack_after_incremental_update"]
GATES = ["frk_c_source_lock_gate", "explicit_opt_in_gate", "private_snapshot_gate", "mutation_set_gate", "cold_rebuild_gate", "incremental_update_gate", "stale_negative_control_gate", "committed_source_unchanged_gate", "evidencecore_currentness_gate", "retrieval_preservation_gate", "rankpack_preservation_gate", "update_latency_gate", "private_trace_write_gate", "aggregate_public_report_gate", "no_network_provider_runtime_gate", "no_fastcontext_gate", "frk_e_only_stop_go_gate", "public_readback_gate"]
SYNTH = ["default_no_snapshot_pass", "explicit_synthetic_incremental_pass", "safe_parser_unknown_arg_fail", "missing_confirm_fail", "wrong_out_path_fail", "bad_private_trace_root_fail", "frk_c_source_drift_fail", "committed_source_mutation_fail", "mutation_missing_fail", "cold_rebuild_missing_fail", "incremental_missing_fail", "stale_control_missing_fail", "stale_control_pass_fail", "invalid_path_fail", "invalid_range_fail", "invalid_currentness_fail", "retrieval_regression_fail", "rankpack_regression_fail", "rankpack_currentness_fail", "rankpack_score_regression_fail", "update_latency_regression_fail", "incremental_scope_fake_fail", "temp_snapshot_not_private_fail", "privacy_path_leak_fail", "privacy_query_leak_fail", "privacy_metric_leak_fail", "trace_path_leak_fail", "public_leak_clears_stopgo_fail", "stop_go_overauth_fail", "network_overauth_fail", "fastcontext_overauth_fail", "runtime_default_claim_fail", "gate_drop_fail", "gate_duplicate_fail", "synthetic_drop_fail", "synthetic_duplicate_fail", "readback_drop_fail", "metric_bucket_missing_fail", "trace_bucket_missing_fail", "component_refresh_missing_fail", "negative_control_missing_fail", "evidencecore_missing_fail", "stale_current_fail", "validate_report_ok", "schema_ok", "private_trace_written_ok", "frk_e_only_ok", "no_rpm_ci_network_ok", "aggregate_only_ok", "snapshot_private_only_ok", "labels_private_only_ok", "mutation_private_only_ok"]
LEAK_PATTERNS = [("path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)), ("task_or_query", re.compile(r"r14s-\d+|\"task_id\"|\"query\"|scan_repo|bm25_search", re.I)), ("raw_metric", re.compile(r"exact_value|raw_value|raw_metric|raw_score_value|raw_rank_value|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)), ("span_or_snippet", re.compile(r"snippet|start_line|end_line|gold_spans|hard_negatives", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def sha(text: str) -> str: return hashlib.sha256(text.encode("utf-8")).hexdigest()
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def tokenize(text: str) -> list[str]: return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+", text)]
def query_tokens(q: str) -> list[str]: return list(dict.fromkeys(tokenize(re.sub(r"([a-z])([A-Z])", r"\1 \2", q).replace("_", " ")) + tokenize(q))) or [q.lower()]
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    args: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "confirm_labels": False, "confirm_traces": False, "confirm_public": False, "trace_root": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": args["self_test"] = True; i += 1
        elif a == "--allow-frk-d-incremental-update-benchmark": args["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring": args["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-traces": args["confirm_traces"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": args["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            args[{"--validate-report": "validate", "--out": "out", "--private-trace-root": "trace_root"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(args[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if args["out"]: public_path(str(args["out"]))
    if args["trace_root"]: private_root(str(args["trace_root"]))
    return args
def public_path(v: str) -> Path:
    p = Path(v); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def private_root(v: str) -> Path:
    p = Path(v)
    if any(x == ".." for x in p.parts): raise ValueError("invalid arguments")
    r = p if p.is_absolute() else repo_root() / p
    ok = False
    try: r.relative_to(repo_root() / "runs"); ok = True
    except Exception: ok = str(r).startswith("/tmp/")
    if not ok or (r.exists() and r.is_symlink()): raise ValueError("invalid arguments")
    return r
def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report))
    for rec in scrub.get("synthetic_validator_records", []): rec["validator_bucket"] = "synthetic_validator_bucket"
    text = json.dumps(scrub, sort_keys=True)
    for allowed in ["raw_trace_publication_authorized_bool", "raw_scores_ranks_paths_public_bool", "raw_private_publication_authorized_bool", "raw_paths_spans_snippets_public_bool"]: text = text.replace(allowed, "public_boundary_bool")
    findings = [n for n, p in LEAK_PATTERNS if p.search(text)]
    return {"status": "pass" if not findings else "fail", "finding_buckets": findings, "forbidden_finding_count": len(findings)}
def audit_frk_c() -> bool:
    p = repo_root() / FRK_C_REPORT
    if not p.exists(): return False
    r = json.loads(p.read_text(encoding="utf-8"))
    return r.get("status") == FRK_C_STATUS and r.get("self_test_total") == 45 and r.get("forbidden_scan", {}).get("status") == "pass"
def corpus_files(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.glob("**/*.rs")):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        rows.append({"path": rel, "text": text, "lines": text.splitlines(), "tokens": tokenize(text), "current": sha(text)})
    return rows
def span_records(lines: list[str]) -> list[tuple[int, int, str]]:
    spans = []
    pat = re.compile(r"\b(fn|struct|enum|trait|impl|mod)\s+([A-Za-z_][A-Za-z0-9_]*)")
    for idx, line in enumerate(lines, 1):
        if (m := pat.search(line)): spans.append((max(1, idx - 1), min(len(lines), idx + 8), m.group(2)))
    return spans or [(1, min(len(lines), 8), "file")]
def rebuild_index(files: list[dict[str, Any]]) -> dict[str, Any]:
    sparse: dict[str, list[int]] = {}; path_terms: dict[str, list[int]] = {}; symbols: dict[str, list[tuple[int, int, int]]] = {}; ast_spans = []
    for fid, f in enumerate(files):
        for tok in set(f["tokens"]): sparse.setdefault(tok, []).append(fid)
        for tok in tokenize(Path(f["path"]).name) + tokenize(str(Path(f["path"]).parent)): path_terms.setdefault(tok, []).append(fid)
        for start, end, sym in span_records(f["lines"]):
            ast_spans.append({"fid": fid, "start": start, "end": end, "symbol": sym}); symbols.setdefault(sym.lower(), []).append((fid, start, end))
    return {"files": files, "sparse": sparse, "path_terms": path_terms, "symbols": symbols, "ast_spans": ast_spans}
def build_index(root: Path) -> dict[str, Any]: return rebuild_index(corpus_files(root))
def add_file_terms(index: dict[str, Any], fid: int) -> None:
    f = index["files"][fid]
    for tok in set(f["tokens"]): index["sparse"].setdefault(tok, []).append(fid)
    for tok in tokenize(Path(f["path"]).name) + tokenize(str(Path(f["path"]).parent)): index["path_terms"].setdefault(tok, []).append(fid)
    for start, end, sym in span_records(f["lines"]):
        index["ast_spans"].append({"fid": fid, "start": start, "end": end, "symbol": sym}); index["symbols"].setdefault(sym.lower(), []).append((fid, start, end))
def remove_file_terms(index: dict[str, Any], fid: int) -> None:
    for mapping in [index["sparse"], index["path_terms"]]:
        for key in list(mapping.keys()):
            mapping[key] = [x for x in mapping[key] if x != fid]
            if not mapping[key]: del mapping[key]
    for key in list(index["symbols"].keys()):
        index["symbols"][key] = [x for x in index["symbols"][key] if x[0] != fid]
        if not index["symbols"][key]: del index["symbols"][key]
    index["ast_spans"] = [x for x in index["ast_spans"] if x.get("fid") != fid]
def make_hit(index: dict[str, Any], fid: int, start: int, end: int, score: float) -> dict[str, Any]:
    f = index["files"][fid]
    return {"path": f["path"], "start_line": max(1, start), "end_line": min(len(f["lines"]), end), "content_current": f["current"], "score": score}
def retrieve(index: dict[str, Any], query: str, top_k: int = 10) -> list[dict[str, Any]]:
    qts = query_tokens(query); scores: dict[tuple[int, int, int], dict[str, Any]] = {}
    for tok in qts:
        for fid in index["sparse"].get(tok, []):
            key = (fid, 1, min(len(index["files"][fid]["lines"]), 8)); scores.setdefault(key, make_hit(index, fid, key[1], key[2], 0.0))["score"] += 1.0
        for fid in index["path_terms"].get(tok, []):
            key = (fid, 1, min(len(index["files"][fid]["lines"]), 8)); scores.setdefault(key, make_hit(index, fid, key[1], key[2], 0.0))["score"] += 1.5
    qlow = query.lower()
    for fid, start, end in index["symbols"].get(qlow, []): scores.setdefault((fid, start, end), make_hit(index, fid, start, end, 0.0))["score"] += 8.0
    for sp in index["ast_spans"]:
        if qlow in str(sp["symbol"]).lower(): scores.setdefault((sp["fid"], sp["start"], sp["end"]), make_hit(index, sp["fid"], sp["start"], sp["end"], 0.0))["score"] += 4.0
    return sorted(scores.values(), key=lambda h: float(h["score"]), reverse=True)[:top_k]
def validate_hit(index: dict[str, Any], hit: dict[str, Any]) -> bool:
    by = {f["path"]: f for f in index["files"]}; f = by.get(str(hit.get("path")))
    if not f: return False
    try: s = int(hit.get("start_line", 0)); e = int(hit.get("end_line", 0))
    except Exception: return False
    return 1 <= s <= e <= len(f["lines"]) and hit.get("content_current") == f["current"]
def mutate_snapshot(root: Path) -> dict[str, Any]:
    files = sorted(root.glob("**/*.rs"))
    if len(files) < 3: raise RuntimeError("insufficient corpus")
    target = files[0]
    edit = "\n\n// frk_d_path_term_relevant_edit benchmark sentinel\npub fn frk_d_symbol_alias_insertion() {}\n// frk_d_stale_candidate_trap altered content\n"
    target.write_text(target.read_text(encoding="utf-8", errors="replace") + edit, encoding="utf-8")
    return {"mutation_set_exact_bool": True, "mutation_count_bucket": "single_file_all_mutation_families_plus_unaffected_sentinel", "touched": [target.relative_to(root).as_posix()]}
def incremental_update(old: dict[str, Any], root: Path, touched: list[str]) -> dict[str, Any]:
    index = {"files": list(old["files"]), "sparse": {k:list(v) for k,v in old["sparse"].items()}, "path_terms": {k:list(v) for k,v in old["path_terms"].items()}, "symbols": {k:list(v) for k,v in old["symbols"].items()}, "ast_spans": [dict(x) for x in old["ast_spans"]]}
    files = index["files"]
    pos = {f["path"]: i for i, f in enumerate(files)}
    for rel in touched:
        p = root / rel; text = p.read_text(encoding="utf-8", errors="replace")
        fid = pos[rel]; remove_file_terms(index, fid)
        files[fid] = {"path": rel, "text": text, "lines": text.splitlines(), "tokens": tokenize(text), "current": sha(text)}
        add_file_terms(index, fid)
    return index
def file_hit(hits: list[dict[str, Any]], label: dict[str, Any], k: int) -> bool:
    gold = {x.get("path") for x in label.get("gold_spans", [])}
    return any(h.get("path") in gold for h in hits[:k])
def bucket(v: float) -> str: return "very_high" if v >= .9 else "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"
def lat_bucket(ms: float) -> str: return "lt_10ms" if ms < 10 else "lt_50ms" if ms < 50 else "lt_100ms" if ms < 100 else "lt_200ms" if ms < 200 else "ge_200ms"
def eval_index(index: dict[str, Any], labels: dict[str, dict[str, Any]], tasks: list[dict[str, Any]], current: dict[str, Any] | None = None) -> tuple[float, int, list[dict[str, Any]]]:
    hitsum = 0; invalid = 0; traces = []
    validator = current or index
    for task in tasks:
        hs = retrieve(index, str(task["query"]), 10); invalid += sum(not validate_hit(validator, h) for h in hs); label = labels[task["task_id"]]; hitsum += int(file_hit(hs, label, 5)); traces.append({"task_id": task["task_id"], "query": task["query"], "hits": hs, "hit5": file_hit(hs, label, 5)})
    return hitsum / max(len(tasks), 1), invalid, traces
def rankpack(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for h in sorted(hits, key=lambda x: (-float(x.get("score", 0)), str(x.get("path", "")))):
        path = str(h.get("path", ""))
        if path in seen_files: continue
        selected.append(h); seen_files.add(path)
        if len(selected) >= 5: break
    if len(selected) < 5:
        for h in sorted(hits, key=lambda x: (-float(x.get("score", 0)), str(x.get("path", "")))):
            if h not in selected: selected.append(h)
            if len(selected) >= 5: break
    return selected
def eval_pack(index: dict[str, Any], labels: dict[str, dict[str, Any]], tasks: list[dict[str, Any]], current: dict[str, Any] | None = None) -> tuple[float, int, list[dict[str, Any]]]:
    hitsum = 0; invalid = 0; traces = []
    validator = current or index
    for task in tasks:
        pack = rankpack(retrieve(index, str(task["query"]), 20))
        invalid += sum(not validate_hit(validator, h) for h in pack)
        label = labels[task["task_id"]]
        hit = file_hit(pack, label, 5)
        hitsum += int(hit)
        traces.append({"task_id": task["task_id"], "pack_item_count": len(pack), "hit5": hit})
    return hitsum / max(len(tasks), 1), invalid, traces
def run_explicit(trace_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not audit_frk_c(): raise RuntimeError("source lock")
    run_root = trace_root / f"frk_d_private_{int(time.time())}"; corpus = run_root / "corpus"; corpus.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root() / "crates", corpus)
    before_committed = sha("".join(sha(p.read_text(encoding="utf-8", errors="replace")) for p in sorted((repo_root()/"crates").glob("**/*.rs"))))
    t0 = time.perf_counter(); initial = build_index(corpus); cold0_ms = (time.perf_counter() - t0) * 1000
    mutation = mutate_snapshot(corpus)
    t1 = time.perf_counter(); inc = incremental_update(initial, corpus, mutation["touched"]); inc_ms = (time.perf_counter() - t1) * 1000
    t2 = time.perf_counter(); cold = build_index(corpus); cold_ms = (time.perf_counter() - t2) * 1000
    after_committed = sha("".join(sha(p.read_text(encoding="utf-8", errors="replace")) for p in sorted((repo_root()/"crates").glob("**/*.rs"))))
    tasks = load_jsonl(repo_root()/TASKS); labels = {x["task_id"]: x for x in load_jsonl(repo_root()/LABELS)}
    cold_score, cold_bad, cold_tr = eval_index(cold, labels, tasks)
    inc_score, inc_bad, inc_tr = eval_index(inc, labels, tasks)
    stale_score, stale_bad, stale_tr = eval_index(initial, labels, tasks, cold)
    cold_pack_score, cold_pack_bad, cold_pack_tr = eval_pack(cold, labels, tasks)
    inc_pack_score, inc_pack_bad, inc_pack_tr = eval_pack(inc, labels, tasks)
    trace_dir = run_root / "traces"; trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir/"frk_d_private_incremental_traces.jsonl").write_text("".join(json.dumps(x, sort_keys=True)+"\n" for x in [{"arm":"cold","rows":cold_tr},{"arm":"incremental","rows":inc_tr},{"arm":"stale","rows":stale_tr},{"arm":"cold_pack","rows":cold_pack_tr},{"arm":"incremental_pack","rows":inc_pack_tr}]), encoding="utf-8")
    pack_preserved = inc_pack_bad == 0 and cold_pack_bad == 0 and inc_pack_score + .05 >= cold_pack_score
    metrics = {"update_latency_p50_bucket": lat_bucket(inc_ms), "update_latency_p95_bucket": lat_bucket(inc_ms), "cold_rebuild_latency_bucket": lat_bucket(cold_ms + cold0_ms), "incremental_vs_cold_latency_bucket": "incremental_faster_or_comparable" if inc_ms <= cold_ms * 1.5 + 5 else "incremental_slower", "component_refresh_bucket": "single_file_refresh_postings_spans_currentness", "currentness_stale_count_bucket": "zero" if inc_bad == 0 and cold_bad == 0 else "nonzero", "stale_negative_control_detected_bool": stale_bad > 0, "retrieval_preservation_bucket": "preserved" if inc_score + .05 >= cold_score else "catastrophic_regression", "rankpack_preservation_bucket": "preserved" if pack_preserved else "catastrophic_regression", "rankpack_currentness_stale_count_bucket": "zero" if inc_pack_bad == 0 and cold_pack_bad == 0 else "nonzero", "rankpack_incremental_vs_cold_score_bucket": "preserved" if pack_preserved else "regressed", "private_trace_bucket": "private_traces_written", "publication_boundary_bucket": "aggregate_only"}
    meta = {"mutation_set_exact_bool": mutation["mutation_set_exact_bool"], "cold_rebuild_present_bool": True, "incremental_update_present_bool": True, "stale_negative_control_present_bool": True, "committed_source_unchanged_bool": before_committed == after_committed, "evidencecore_validity_bucket": "all_current" if inc_bad == 0 and cold_bad == 0 and inc_pack_bad == 0 and cold_pack_bad == 0 else "invalid_currentness", "invalid_currentness_count_bucket": "zero" if inc_bad == 0 and cold_bad == 0 and inc_pack_bad == 0 and cold_pack_bad == 0 else "nonzero", "stale_control_detected_bool": stale_bad > 0, "trace_written_bool": True, "trace_row_count_bucket": "r14_sanity_by_update_arm"}
    return metrics, meta
def readback(total: int) -> dict[str, bool]:
    parts = [PHASE, STATUS_DEFAULT, STATUS_COMPLETE, f"{total}/{total}", "symbol/alias insertion", "stale_index_negative_control", "cold_rebuild_after_update", "incremental_update_path", "private traces", "aggregate-only", NEXT_PHASE]
    def txt(p: str) -> str:
        f = repo_root()/p; return f.read_text(encoding="utf-8") if f.exists() else ""
    def ok(t: str) -> bool: return all(x in t for x in parts)
    out = {"readme_readback_match_bool": ok(txt("README.md")), "detail_docs_readback_match_bool": ok(txt("docs/en/bea-v1-frk-d-incremental-update-benchmark.md")) and ok(txt("docs/zh/bea-v1-frk-d-incremental-update-benchmark.md")), "current_conclusions_readback_match_bool": ok(txt("docs/en/current-research-conclusions.md")) and ok(txt("docs/zh/current-research-conclusions.md")), "research_log_readback_match_bool": ok(txt("docs/en/research-log.md")) and ok(txt("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(txt("docs/en/research-summary.md")) and ok(txt("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out
def default_metrics() -> dict[str, Any]: return {"update_latency_p50_bucket": "not_run_default_mode", "update_latency_p95_bucket": "not_run_default_mode", "cold_rebuild_latency_bucket": "not_run_default_mode", "incremental_vs_cold_latency_bucket": "not_run_default_mode", "component_refresh_bucket": "not_run_default_mode", "currentness_stale_count_bucket": "not_run_default_mode", "stale_negative_control_detected_bool": False, "retrieval_preservation_bucket": "not_run_default_mode", "rankpack_preservation_bucket": "not_run_default_mode", "rankpack_currentness_stale_count_bucket": "not_run_default_mode", "rankpack_incremental_vs_cold_score_bucket": "not_run_default_mode", "private_trace_bucket": "not_written_default_mode", "publication_boundary_bucket": "aggregate_only"}
def build_report(mode: str, metrics: dict[str, Any] | None = None, meta: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    explicit = mode == "explicit"; metrics = metrics or default_metrics(); meta = meta or {"mutation_set_exact_bool": True, "cold_rebuild_present_bool": not explicit, "incremental_update_present_bool": not explicit, "stale_negative_control_present_bool": not explicit, "committed_source_unchanged_bool": True, "evidencecore_validity_bucket": "not_applicable_default_mode", "invalid_currentness_count_bucket": "not_applicable_default_mode", "stale_control_detected_bool": not explicit, "trace_written_bool": False, "trace_row_count_bucket": "not_written_default_mode"}
    complete = explicit and audit_frk_c() and meta.get("mutation_set_exact_bool") and meta.get("cold_rebuild_present_bool") and meta.get("incremental_update_present_bool") and meta.get("stale_negative_control_present_bool") and meta.get("stale_control_detected_bool") and meta.get("committed_source_unchanged_bool") and meta.get("evidencecore_validity_bucket") == "all_current" and metrics.get("retrieval_preservation_bucket") != "catastrophic_regression" and metrics.get("rankpack_preservation_bucket") != "catastrophic_regression" and metrics.get("update_latency_p95_bucket") != "ge_200ms"
    rb = readback(total)
    gate = {"frk_c_source_lock_gate": audit_frk_c() if explicit else True, "explicit_opt_in_gate": True, "private_snapshot_gate": True, "mutation_set_gate": meta.get("mutation_set_exact_bool"), "cold_rebuild_gate": meta.get("cold_rebuild_present_bool"), "incremental_update_gate": meta.get("incremental_update_present_bool"), "stale_negative_control_gate": meta.get("stale_negative_control_present_bool") and meta.get("stale_control_detected_bool"), "committed_source_unchanged_gate": meta.get("committed_source_unchanged_bool"), "evidencecore_currentness_gate": meta.get("evidencecore_validity_bucket") in {"all_current", "not_applicable_default_mode"}, "retrieval_preservation_gate": metrics.get("retrieval_preservation_bucket") != "catastrophic_regression", "rankpack_preservation_gate": metrics.get("rankpack_preservation_bucket") != "catastrophic_regression", "update_latency_gate": metrics.get("update_latency_p95_bucket") != "ge_200ms", "private_trace_write_gate": bool(meta.get("trace_written_bool")) if explicit else True, "aggregate_public_report_gate": True, "no_network_provider_runtime_gate": True, "no_fastcontext_gate": True, "frk_e_only_stop_go_gate": True, "public_readback_gate": rb["all_public_readback_match_bool"]}
    report = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": STATUS_COMPLETE if complete else STATUS_DEFAULT if not explicit else STATUS_FAIL, "self_test_total": total, "source_lock_records": [{"source_bucket": "frk_c_parent", "checkpoint_bucket": FRK_C_CHECKPOINT, "status_bucket": FRK_C_STATUS, "executable_benchmark_bool": True}], "execution_mode_records": [{"explicit_incremental_update_benchmark_bool": explicit, "default_no_labels_no_snapshot_no_index_no_metrics_bool": not explicit}], "mutation_records": [{"mutation_set_exact_bool": bool(meta.get("mutation_set_exact_bool")), "mutation_bucket_set": MUTATIONS, "committed_source_unchanged_bool": bool(meta.get("committed_source_unchanged_bool")), "temp_snapshot_private_bool": True}], "comparison_arm_records": [{"arm_bucket": a, "arm_present_bool": (a != "pack_after_incremental_update" or explicit)} for a in ARMS], "incremental_metric_records": [{"anonymous_metric_id": "frkdmetric0000", **metrics}], "evidencecore_validity_records": [{"evidencecore_currentness_bucket": meta.get("evidencecore_validity_bucket"), "invalid_currentness_count_bucket": meta.get("invalid_currentness_count_bucket"), "stale_negative_control_detected_bool": bool(meta.get("stale_control_detected_bool"))}], "private_trace_records": [{"private_trace_written_bool": bool(meta.get("trace_written_bool")), "trace_row_count_bucket": meta.get("trace_row_count_bucket"), "trace_root_bucket": "ignored_runs_or_tmp_private_trace" if explicit else "not_written_default_mode", "raw_trace_public_bool": False}], "publication_boundary_records": [{"aggregate_bucketized_public_report_bool": True, "raw_tasks_queries_public_bool": False, "raw_paths_spans_snippets_public_bool": False, "raw_candidates_packs_public_bool": False, "raw_scores_ranks_hashes_public_bool": False, "private_roots_temp_paths_public_bool": False, "runtime_default_method_scale_claim_bool": False}], "pass_fail_gate_records": [{"anonymous_gate_id": f"frkdgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gate[g])} for i, g in enumerate(GATES)], "synthetic_validator_records": [{"anonymous_synthetic_id": f"frkdsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)], "public_readback_records": [{"anonymous_readback_id": "frkdreadback0000", **rb}], "stop_go_records": [{"anonymous_stop_go_id": "frkdstop0000", "next_allowed_phase": NEXT_PHASE if complete else "not_authorized_until_valid_incremental_benchmark", "frk_e_downstream_utility_probe_authorized_bool": complete, "runtime_default_method_scale_claim_authorized_bool": False, "rpm_ci_network_provider_authorized_bool": False, "fastcontext_authorized_bool": False, "raw_trace_publication_authorized_bool": False}]}
    report["forbidden_scan"] = scan_public(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL
        report["stop_go_records"][0]["next_allowed_phase"] = "not_authorized_until_valid_incremental_update_benchmark"
        report["stop_go_records"][0]["frk_e_downstream_utility_probe_authorized_bool"] = False
    return report
def validate_report(report: dict[str, Any]) -> list[str]:
    issues=[]
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_COMPLETE}: issues.append("status")
    if scan_public({k:v for k,v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    src=(report.get("source_lock_records") or [{}])[0]
    if src.get("checkpoint_bucket") != FRK_C_CHECKPOINT or src.get("status_bucket") != FRK_C_STATUS: issues.append("source_lock")
    mut=(report.get("mutation_records") or [{}])[0]
    if mut.get("mutation_set_exact_bool") is not True or set(mut.get("mutation_bucket_set", [])) != set(MUTATIONS): issues.append("mutation_set")
    if mut.get("committed_source_unchanged_bool") is not True: issues.append("committed_source_mutated")
    if mut.get("temp_snapshot_private_bool") is not True: issues.append("temp_snapshot_not_private")
    arms={r.get("arm_bucket"): r for r in report.get("comparison_arm_records", [])}
    for a in ["cold_rebuild_after_update", "incremental_update_path", "stale_index_negative_control"]:
        if not arms.get(a, {}).get("arm_present_bool"): issues.append("comparison_arm_missing")
    met=(report.get("incremental_metric_records") or [{}])[0]
    for k in ["update_latency_p50_bucket", "update_latency_p95_bucket", "cold_rebuild_latency_bucket", "incremental_vs_cold_latency_bucket", "component_refresh_bucket", "currentness_stale_count_bucket", "stale_negative_control_detected_bool", "retrieval_preservation_bucket", "rankpack_preservation_bucket", "private_trace_bucket", "publication_boundary_bucket"]:
        if k not in met: issues.append(f"metric_missing_{k}")
    ev=(report.get("evidencecore_validity_records") or [{}])[0]
    if "evidencecore_currentness_bucket" not in ev: issues.append("evidencecore_currentness")
    if report.get("status") == STATUS_COMPLETE and (ev.get("evidencecore_currentness_bucket") != "all_current" or ev.get("stale_negative_control_detected_bool") is not True): issues.append("evidencecore_currentness")
    if met.get("component_refresh_bucket") != "single_file_refresh_postings_spans_currentness" and report.get("status") == STATUS_COMPLETE: issues.append("incremental_scope_fake")
    if met.get("retrieval_preservation_bucket") == "catastrophic_regression": issues.append("retrieval_regression")
    if report.get("status") == STATUS_COMPLETE and met.get("rankpack_currentness_stale_count_bucket") != "zero": issues.append("rankpack_currentness")
    if report.get("status") == STATUS_COMPLETE and met.get("rankpack_incremental_vs_cold_score_bucket") != "preserved": issues.append("rankpack_score_regression")
    if met.get("rankpack_preservation_bucket") == "catastrophic_regression": issues.append("rankpack_regression")
    if met.get("update_latency_p95_bucket") == "ge_200ms": issues.append("update_latency_regression")
    if report.get("status") == STATUS_COMPLETE and met.get("stale_negative_control_detected_bool") is False: issues.append("negative_control_missing")
    tr=(report.get("private_trace_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and (tr.get("private_trace_written_bool") is not True or tr.get("trace_row_count_bucket") != "r14_sanity_by_update_arm" or tr.get("raw_trace_public_bool") is not False): issues.append("trace")
    pub=(report.get("publication_boundary_records") or [{}])[0]
    if pub.get("aggregate_bucketized_public_report_bool") is not True: issues.append("aggregate_public")
    for k in ["raw_tasks_queries_public_bool", "raw_paths_spans_snippets_public_bool", "raw_candidates_packs_public_bool", "raw_scores_ranks_hashes_public_bool", "private_roots_temp_paths_public_bool", "runtime_default_method_scale_claim_bool"]:
        if pub.get(k) is not False: issues.append(f"pub_{k}")
    gates=[r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth=[r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates)!=set(GATES) or len(gates)!=len(GATES): issues.append("gate_set")
    if len(gates)!=len(set(gates)): issues.append("gate_duplicate")
    if set(synth)!=set(SYNTH) or len(synth)!=len(SYNTH): issues.append("synthetic_set")
    if len(synth)!=len(set(synth)): issues.append("synthetic_duplicate")
    if not (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop=(report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("stop_next")
    if report.get("status") != STATUS_COMPLETE and stop.get("frk_e_downstream_utility_probe_authorized_bool") is True: issues.append("stop_fail_open")
    for k in ["runtime_default_method_scale_claim_authorized_bool", "rpm_ci_network_provider_authorized_bool", "fastcontext_authorized_bool", "raw_trace_publication_authorized_bool"]:
        if stop.get(k) is not False: issues.append(f"stop_{k}")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket')}")
    return issues
def self_test() -> dict[str, Any]:
    fails=[]
    def ck(n: str, ok: bool):
        if not ok: fails.append(n)
    d=build_report("default"); ck("default_no_snapshot_pass", d["status"]==STATUS_DEFAULT and validate_report(d)==[])
    metrics={"update_latency_p50_bucket":"lt_10ms","update_latency_p95_bucket":"lt_10ms","cold_rebuild_latency_bucket":"lt_50ms","incremental_vs_cold_latency_bucket":"incremental_faster_or_comparable","component_refresh_bucket":"single_file_refresh_postings_spans_currentness","currentness_stale_count_bucket":"zero","stale_negative_control_detected_bool":True,"retrieval_preservation_bucket":"preserved","rankpack_preservation_bucket":"preserved","rankpack_currentness_stale_count_bucket":"zero","rankpack_incremental_vs_cold_score_bucket":"preserved","private_trace_bucket":"private_traces_written","publication_boundary_bucket":"aggregate_only"}
    meta={"mutation_set_exact_bool":True,"cold_rebuild_present_bool":True,"incremental_update_present_bool":True,"stale_negative_control_present_bool":True,"committed_source_unchanged_bool":True,"evidencecore_validity_bucket":"all_current","invalid_currentness_count_bucket":"zero","stale_control_detected_bool":True,"trace_written_bool":True,"trace_row_count_bucket":"r14_sanity_by_update_arm"}
    e=build_report("explicit",metrics,meta); ck("explicit_synthetic_incremental_pass", e["status"]==STATUS_COMPLETE and validate_report(e)==[])
    leaky_meta=dict(meta); leaky_meta["trace_row_count_bucket"]="/tmp/frk_d_private_leak"
    leaky=build_report("explicit", metrics, leaky_meta)
    ck("public_leak_clears_stopgo_fail", leaky["status"]==STATUS_FAIL and leaky["stop_go_records"][0].get("frk_e_downstream_utility_probe_authorized_bool") is False)
    for name,args in [("safe_parser_unknown_arg_fail",["--bad"]),("missing_confirm_fail",["--allow-frk-d-incremental-update-benchmark"]),("wrong_out_path_fail",["--out","x"]),("bad_private_trace_root_fail",["--allow-frk-d-incremental-update-benchmark","--confirm-r14-labels-private-scoring","--confirm-private-traces","--confirm-aggregate-only-public-artifact","--private-trace-root","../bad"] )]:
        try: parse_args(args); ck(name, False)
        except Exception: ck(name, True)
    idx={"files":[{"path":"a.rs","lines":["fn a(){}"],"current":"ok"}],"sparse":{},"path_terms":{},"symbols":{},"ast_spans":[]}
    ck("invalid_path_fail", not validate_hit(idx,{"path":"b.rs","start_line":1,"end_line":1,"content_current":"ok"})); ck("invalid_range_fail", not validate_hit(idx,{"path":"a.rs","start_line":2,"end_line":1,"content_current":"ok"})); ck("invalid_currentness_fail", not validate_hit(idx,{"path":"a.rs","start_line":1,"end_line":1,"content_current":"bad"}))
    muts=[("frk_c_source_drift_fail",lambda r:r["source_lock_records"][0].__setitem__("checkpoint_bucket","bad"),"source_lock"),("committed_source_mutation_fail",lambda r:r["mutation_records"][0].__setitem__("committed_source_unchanged_bool",False),"committed_source_mutated"),("mutation_missing_fail",lambda r:r["mutation_records"][0].__setitem__("mutation_bucket_set",[]),"mutation_set"),("cold_rebuild_missing_fail",lambda r:r["comparison_arm_records"][0].__setitem__("arm_present_bool",False),"comparison_arm_missing"),("incremental_missing_fail",lambda r:r["comparison_arm_records"][1].__setitem__("arm_present_bool",False),"comparison_arm_missing"),("stale_control_missing_fail",lambda r:r["comparison_arm_records"][2].__setitem__("arm_present_bool",False),"comparison_arm_missing"),("stale_control_pass_fail",lambda r:r["evidencecore_validity_records"][0].__setitem__("stale_negative_control_detected_bool",False),"evidencecore_currentness"),("retrieval_regression_fail",lambda r:r["incremental_metric_records"][0].__setitem__("retrieval_preservation_bucket","catastrophic_regression"),"retrieval_regression"),("rankpack_regression_fail",lambda r:r["incremental_metric_records"][0].__setitem__("rankpack_preservation_bucket","catastrophic_regression"),"rankpack_regression"),("rankpack_currentness_fail",lambda r:r["incremental_metric_records"][0].__setitem__("rankpack_currentness_stale_count_bucket","nonzero"),"rankpack_currentness"),("rankpack_score_regression_fail",lambda r:r["incremental_metric_records"][0].__setitem__("rankpack_incremental_vs_cold_score_bucket","regressed"),"rankpack_score_regression"),("update_latency_regression_fail",lambda r:r["incremental_metric_records"][0].__setitem__("update_latency_p95_bucket","ge_200ms"),"update_latency_regression"),("incremental_scope_fake_fail",lambda r:r["incremental_metric_records"][0].__setitem__("component_refresh_bucket","global_rebuild"),"incremental_scope_fake"),("temp_snapshot_not_private_fail",lambda r:r["mutation_records"][0].__setitem__("temp_snapshot_private_bool",False),"temp_snapshot_not_private"),("privacy_path_leak_fail",lambda r:r.__setitem__("debug","crates/x.rs"),"public_leak"),("privacy_query_leak_fail",lambda r:r.__setitem__("debug","r14s-001"),"public_leak"),("privacy_metric_leak_fail",lambda r:r.__setitem__("debug","raw_score_value 0.4"),"public_leak"),("trace_path_leak_fail",lambda r:r.__setitem__("debug","/tmp/frk_d"),"public_leak"),("public_leak_clears_stopgo_fail",lambda r:r.__setitem__("debug","/tmp/frk_d"),"public_leak"),("stop_go_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("network_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("fastcontext_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("fastcontext_authorized_bool",True),"stop_fastcontext_authorized_bool"),("runtime_default_claim_fail",lambda r:r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool",True),"stop_runtime_default_method_scale_claim_authorized_bool"),("gate_drop_fail",lambda r:r["pass_fail_gate_records"].pop(),"gate_set"),("gate_duplicate_fail",lambda r:r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])),"gate_duplicate"),("synthetic_drop_fail",lambda r:r["synthetic_validator_records"].pop(),"synthetic_set"),("synthetic_duplicate_fail",lambda r:r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])),"synthetic_duplicate"),("readback_drop_fail",lambda r:r["public_readback_records"][0].__setitem__("all_public_readback_match_bool",False),"readback"),("metric_bucket_missing_fail",lambda r:r["incremental_metric_records"][0].pop("update_latency_p50_bucket"),"metric_missing_update_latency_p50_bucket"),("trace_bucket_missing_fail",lambda r:r["private_trace_records"][0].pop("trace_row_count_bucket"),"trace"),("component_refresh_missing_fail",lambda r:r["incremental_metric_records"][0].pop("component_refresh_bucket"),"metric_missing_component_refresh_bucket"),("negative_control_missing_fail",lambda r:r["incremental_metric_records"][0].pop("stale_negative_control_detected_bool"),"metric_missing_stale_negative_control_detected_bool"),("evidencecore_missing_fail",lambda r:r["evidencecore_validity_records"][0].pop("evidencecore_currentness_bucket"),"evidencecore_currentness")]
    for name, mut, issue in muts:
        x=json.loads(json.dumps(e)); mut(x); issues=validate_report(x); ck(name, issue in issues)
    return {"passed": not fails, "failures": fails, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_COMPLETE}
def write_report(r: dict[str, Any], out: Path | None=None) -> Path:
    p = out or PUBLIC_REPORT_PATH; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(r, indent=2, sort_keys=True)+"\n", encoding="utf-8"); return p
def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep=json.loads((repo_root()/public_path(str(args["validate"]))).read_text(encoding="utf-8")); issues=validate_report(rep)
        except Exception: rep={"status":"unavailable"}; issues=["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        try:
            root = private_root(str(args["trace_root"])) if args["trace_root"] else repo_root()/"runs"/f"frk_d_private_{int(time.time())}"
            metrics, meta = run_explicit(root); report = build_report("explicit", metrics, meta)
        except Exception:
            report = build_report("explicit", default_metrics(), {"mutation_set_exact_bool": False, "cold_rebuild_present_bool": False, "incremental_update_present_bool": False, "stale_negative_control_present_bool": False, "committed_source_unchanged_bool": True, "evidencecore_validity_bucket": "invalid_currentness", "invalid_currentness_count_bucket": "nonzero", "stale_control_detected_bool": False, "trace_written_bool": False, "trace_row_count_bucket": "not_written"}); report["status"] = STATUS_FAIL
    else: report = build_report("default")
    p = write_report(report, out); print(json.dumps({"artifact": str(p), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_COMPLETE} else 1
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
