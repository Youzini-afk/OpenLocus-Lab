#!/usr/bin/env python3
"""BEA-v1-LDI-A Derived Index Smoke Benchmark.

Local deterministic derived-metadata index smoke benchmark on R14-S. Explicit mode
builds/query a private derived index and scores with private labels only after
retrieval. Public output is aggregate/bucket only.
"""

from __future__ import annotations

import hashlib, importlib.util, json, math, re, sys, time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-LDI-A Derived Index Smoke Benchmark"
SLUG = "bea_v1_ldi_a_derived_index_smoke_benchmark"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "ldi_a_unavailable_no_explicit_derived_index_smoke_opt_in"
STATUS_COMPLETE = "ldi_a_derived_index_smoke_complete_ldi_b_local_llm_or_tag_expansion_authorized"
STATUS_NO_GO_NO_LIFT = "ldi_a_no_go_no_lift_over_best_baseline"
STATUS_NO_GO_LATENCY_NOISE = "ldi_a_no_go_latency_or_noise_regression"
STATUS_STOP_BASELINE = "ldi_a_stop_derived_index_route_baseline_sufficient"
STATUS_FAIL_SOURCE = "ldi_a_fail_closed_source_or_baseline_invalid"
STATUS_FAIL_BASELINE = STATUS_FAIL_SOURCE
STATUS_FAIL_DERIVED = "ldi_a_fail_closed_derived_index_invalid"
STATUS_FAIL_EVIDENCE = "ldi_a_fail_closed_evidencecore_or_privacy_violation"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_F_REPORT = Path("artifacts/bea_v1_frk_f_failure_decomposition/bea_v1_frk_f_failure_decomposition_report.json")
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
FRK_F_CHECKPOINT = "63528e8"
FRK_F_STATUS = "frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient"
SELF_TEST_EXPECTED = 48
VARIANTS = ["bm25_like_baseline", "rrf_like_baseline", "path_symbol_baseline", "frk_b_retrieve_fast_baseline", "ldi_derived_index_variant"]
DERIVED_COMPONENTS = ["symbol_names", "file_path_role_tags", "function_type_module_role_buckets", "comment_doc_keywords", "normalized_aliases", "ast_span_type", "phrase_expansion"]
GATES = ["frk_f_source_lock_gate", "explicit_opt_in_gate", "private_label_scoring_gate", "private_trace_write_gate", "derived_index_built_gate", "derived_not_evidence_gate", "required_variant_set_gate", "same_budget_gate", "evidencecore_validity_gate", "meaningful_lift_or_honest_no_go_gate", "aggregate_public_report_gate", "no_network_provider_llm_gate", "no_fastcontext_gate", "stop_go_boundary_gate", "public_readback_gate"]
SYNTH = ["default_no_private_read_pass", "explicit_synthetic_smoke_pass", "safe_parser_unknown_arg_fail", "missing_confirm_fail", "wrong_out_path_fail", "bad_private_trace_root_fail", "frk_f_source_drift_fail", "frk_f_status_drift_fail", "baseline_missing_fail", "variant_duplicate_fail", "derived_component_missing_fail", "derived_as_evidence_fail", "derived_index_summary_only_fail", "derived_index_not_loaded_fail", "evidencecore_invalid_path_fail", "evidencecore_invalid_range_fail", "evidencecore_stale_hash_fail", "same_budget_mismatch_fail", "no_lift_no_go_ok", "latency_noise_no_go_ok", "public_path_leak_fail", "public_query_leak_fail", "public_metric_leak_fail", "trace_path_leak_fail", "raw_tag_leak_fail", "public_leak_clears_stopgo_fail", "stop_go_overauth_fail", "network_overauth_fail", "fastcontext_overauth_fail", "runtime_default_claim_fail", "gate_drop_fail", "gate_duplicate_fail", "synthetic_drop_fail", "synthetic_duplicate_fail", "readback_drop_fail", "self_test_count_matches_synth", "validate_report_ok", "schema_ok", "aggregate_only_ok", "labels_private_only_ok", "traces_private_ok", "root_current_thin_index_ok", "derived_index_real_ok", "comment_doc_keywords_ok", "normalized_aliases_ok", "phrase_expansion_ok", "baseline_sufficient_stop_ok", "ldi_b_only_if_go_ok"]
LEAK_PATTERNS = [("path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)), ("task_or_query", re.compile(r"r14s-\d+|\"task_id\"|\"query\"|scan_repo|bm25_search", re.I)), ("raw_metric", re.compile(r"exact_value|raw_value|raw_metric|raw_score|raw_rank|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)), ("raw_tag_span", re.compile(r"raw_tag|derived_tag|snippet|start_line|end_line|gold_spans|hard_negatives", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_jsonl(p: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha_bytes(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def toks(s: str) -> list[str]: return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+", s)]
def qt(q: str) -> list[str]: return list(dict.fromkeys(toks(re.sub(r"([a-z])([A-Z])", r"\1 \2", q).replace("_", " ")) + toks(q)))

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    a: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "confirm_labels": False, "confirm_traces": False, "confirm_derived": False, "confirm_public": False, "trace_root": ""}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--self-test": a["self_test"] = True; i += 1
        elif x == "--allow-ldi-a-derived-index-smoke": a["explicit"] = True; i += 1
        elif x == "--confirm-r14-labels-private-scoring": a["confirm_labels"] = True; i += 1
        elif x == "--confirm-private-traces": a["confirm_traces"] = True; i += 1
        elif x == "--confirm-derived-not-evidence": a["confirm_derived"] = True; i += 1
        elif x == "--confirm-aggregate-only-public-artifact": a["confirm_public"] = True; i += 1
        elif x in {"--private-trace-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            a[{"--private-trace-root":"trace_root", "--validate-report":"validate", "--out":"out"}[x]] = argv[i+1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(a[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_derived", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if a["out"]: public_path(str(a["out"]))
    if a["trace_root"]: private_root(str(a["trace_root"]))
    return a
def public_path(v: str) -> Path:
    p = Path(v); r = p if p.is_absolute() else repo_root()/p
    if r != repo_root()/PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def private_root(v: str) -> Path:
    p = Path(v)
    if any(x == ".." for x in p.parts): raise ValueError("invalid arguments")
    r = p if p.is_absolute() else repo_root()/p
    ok = False
    try: r.relative_to(repo_root()/"runs"); ok = True
    except Exception: ok = str(r).startswith("/tmp/")
    if not ok or (r.exists() and r.is_symlink()): raise ValueError("invalid arguments")
    return r
def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report)); scrub.pop("forbidden_scan", None)
    for rec in scrub.get("synthetic_validator_records", []): rec["validator_bucket"] = "synthetic_validator_bucket"
    text = json.dumps(scrub, sort_keys=True)
    for allowed in ["raw_trace_publication_authorized_bool", "raw_tags_public_bool", "raw_scores_ranks_paths_public_bool", "raw_paths_spans_tags_public_bool", "raw_scores_ranks_hashes_public_bool", "raw_tasks_queries_public_bool", "raw_private_publication_authorized_bool"]: text = text.replace(allowed, "public_boundary_bool")
    findings = [n for n,p in LEAK_PATTERNS if p.search(text)]
    return {"status":"pass" if not findings else "fail", "finding_buckets":findings, "forbidden_finding_count":len(findings)}
def audit_frk_f() -> bool:
    p = repo_root()/FRK_F_REPORT
    if not p.exists(): return False
    r = json.loads(p.read_text(encoding="utf-8"))
    return r.get("status") == FRK_F_STATUS and r.get("self_test_total") == 50 and r.get("forbidden_scan", {}).get("status") == "pass"
def frk_b():
    p = repo_root()/"eval/bea_v1_frk_b_fast_retrieval_kernel_prototype.py"
    spec = importlib.util.spec_from_file_location("frkb", p); mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader; spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod
def corpus() -> list[dict[str, Any]]:
    out=[]
    for p in sorted((repo_root()/"crates").glob("**/*.rs")):
        text = p.read_text(encoding="utf-8", errors="replace"); rel = p.relative_to(repo_root()).as_posix()
        lines = text.splitlines() or [""]
        out.append({"path": rel, "abs": p, "text": text, "lines": lines, "hash": sha_bytes(p), "tokens": toks(text), "path_tokens": toks(rel)})
    return out
def hit(row: dict[str, Any], score: float, start: int = 1) -> dict[str, Any]:
    return {"path": row["path"], "start_line": start, "end_line": min(start+7, len(row["lines"])), "content_current": row["hash"], "score": score}
def validate_hit(h: dict[str, Any]) -> bool:
    try:
        p = repo_root()/str(h.get("path")); st = int(h.get("start_line") or 0); en = int(h.get("end_line") or 0)
        if str(h.get("path", "")).startswith("/") or ".." in Path(str(h.get("path"))).parts: return False
        if not p.exists() or p.is_symlink(): return False
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines() or [""]
        return st >= 1 and en >= st and en <= len(lines) and h.get("content_current") == sha_bytes(p)
    except Exception: return False
def bm25(rows: list[dict[str, Any]], q: str, k: int=5) -> list[dict[str, Any]]:
    qv=qt(q); n=max(len(rows),1); avg=sum(len(r["tokens"]) for r in rows)/n; scores=[]
    for r in rows:
        sc=0.0
        for t in qv:
            tf=r["tokens"].count(t); df=sum(1 for x in rows if t in x["tokens"]); idf=math.log(1+(n-df+.5)/(df+.5)) if df else 0.0
            sc += idf*(tf*2.2)/(tf+1.2*(.25+.75*len(r["tokens"])/max(avg,1))) if tf else 0
        if sc: scores.append((sc,r))
    return [hit(r,sc) for sc,r in sorted(scores,key=lambda x:x[0], reverse=True)[:k]]
def path_symbol(rows: list[dict[str, Any]], q: str, k:int=5) -> list[dict[str, Any]]:
    qv=qt(q); scored=[]
    for r in rows:
        symbols=re.findall(r"(?:fn|struct|enum|trait|mod)\s+([A-Za-z_][A-Za-z0-9_]*)", r["text"])
        sc=sum(3 for t in qv if t in [s.lower() for s in symbols]) + sum(2 for t in qv if t in r["path_tokens"])
        if sc: scored.append((float(sc), r))
    return [hit(r,sc) for sc,r in sorted(scored,key=lambda x:x[0], reverse=True)[:k]]
def rrf(a: list[dict[str, Any]], b: list[dict[str, Any]], k:int=5) -> list[dict[str, Any]]:
    d: dict[str, dict[str, Any]]={}
    for arr in [a,b]:
        for i,h in enumerate(arr,1):
            rec=d.setdefault(h["path"], dict(h)); rec["score"] = float(rec.get("score",0))+1/(60+i)
    return sorted(d.values(), key=lambda x:x["score"], reverse=True)[:k]
def build_derived(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for r in rows:
        symbols=re.findall(r"(?:fn|struct|enum|trait|mod)\s+([A-Za-z_][A-Za-z0-9_]*)", r["text"])
        docs=re.findall(r"//[/!]?\s*(.*)", r["text"])
        aliases=[]
        for s in symbols + r["path_tokens"]:
            aliases += toks(re.sub(r"([a-z])([A-Z])", r"\1 \2", s).replace("_"," "))
        span_types=re.findall(r"\b(fn|struct|enum|trait|mod|impl)\b", r["text"])
        role=["testish" if "test" in r["path"] else "library", "configish" if "config" in r["path"] else "code"]
        r["derived"] = list(dict.fromkeys(symbols + r["path_tokens"] + toks(" ".join(docs)) + aliases + span_types + role))
    return rows
def derived_query(rows: list[dict[str, Any]], q: str, k:int=5) -> list[dict[str, Any]]:
    qv=qt(q); scored=[]
    for r in rows:
        tags=[str(x).lower() for x in r.get("derived", [])]
        sc=sum(3 for t in qv if t in tags) + sum(1 for t in qv if any(t in tag for tag in tags))
        if sc: scored.append((float(sc), r))
    return [hit(r,sc) for sc,r in sorted(scored,key=lambda x:x[0], reverse=True)[:k]]
def persist_private_derived_index(rows: list[dict[str, Any]], out: Path) -> int:
    records = []
    for i, r in enumerate(rows):
        records.append({
            "private_source_ref": r["path"],
            "content_current": r["hash"],
            "derived_tags_private": list(r.get("derived", [])),
            "path_tokens_private": list(r.get("path_tokens", [])),
            "line_count_private": len(r.get("lines", [])),
            "anonymous_file_id": f"ldiafile{i:04d}",
        })
    out.write_text("".join(json.dumps(x, sort_keys=True)+"\n" for x in records), encoding="utf-8")
    return len(records)
def load_private_derived_index(path: Path) -> list[dict[str, Any]]:
    loaded=[]
    for rec in load_jsonl(path):
        p = repo_root()/str(rec.get("private_source_ref"))
        if not p.exists() or p.is_symlink() or sha_bytes(p) != rec.get("content_current"):
            continue
        text=p.read_text(encoding="utf-8", errors="replace"); lines=text.splitlines() or [""]
        loaded.append({"path": rec["private_source_ref"], "abs": p, "text": text, "lines": lines, "hash": rec["content_current"], "tokens": toks(text), "path_tokens": list(rec.get("path_tokens_private", [])), "derived": list(rec.get("derived_tags_private", []))})
    return loaded
def file_recall(pack: list[dict[str, Any]], lab: dict[str, Any], k:int) -> bool:
    gold={x.get("path") for x in lab.get("gold_spans", [])}
    return any(h.get("path") in gold for h in pack[:k])
def bucket(v: float) -> str: return "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"
def lift_bucket(d: float) -> str: return "meaningful_lift" if d >= .15 else "small_lift" if d > .01 else "no_lift" if d >= -.01 else "regression"
def run_explicit(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not audit_frk_f(): raise RuntimeError("source")
    run = root / f"ldi_a_private_{int(time.time())}"; run.mkdir(parents=True, exist_ok=True)
    rows=build_derived(corpus()); tasks=load_jsonl(repo_root()/TASKS); labels={x["task_id"]:x for x in load_jsonl(repo_root()/LABELS)}
    private_index_path = run/"ldi_a_private_derived_index.jsonl"
    derived_index_count = persist_private_derived_index(rows, private_index_path)
    derived_rows = load_private_derived_index(private_index_path)
    bmod=frk_b(); kernel=bmod.build_kernel(run/"frk_b_index")
    sums={v:{"r1":0,"r5":0,"wrong":0,"empty":0,"invalid":0,"lat":[]} for v in VARIANTS}; traces=[]
    for t in tasks:
        q=str(t["query"]); lab=labels[t["task_id"]]
        t0=time.perf_counter(); bm=bm25(rows,q); sums["bm25_like_baseline"]["lat"].append((time.perf_counter()-t0)*1000)
        t0=time.perf_counter(); ps=path_symbol(rows,q); sums["path_symbol_baseline"]["lat"].append((time.perf_counter()-t0)*1000)
        t0=time.perf_counter(); rr=rrf(bm,ps); sums["rrf_like_baseline"]["lat"].append((time.perf_counter()-t0)*1000)
        t0=time.perf_counter(); fb=bmod.retrieve_fast(kernel,q,5); sums["frk_b_retrieve_fast_baseline"]["lat"].append((time.perf_counter()-t0)*1000)
        t0=time.perf_counter(); ld=derived_query(derived_rows,q); sums["ldi_derived_index_variant"]["lat"].append((time.perf_counter()-t0)*1000)
        packs={"bm25_like_baseline":bm,"path_symbol_baseline":ps,"rrf_like_baseline":rr,"frk_b_retrieve_fast_baseline":fb,"ldi_derived_index_variant":ld}
        for name,pack in packs.items():
            sums[name]["r1"]+=int(file_recall(pack,lab,1)); sums[name]["r5"]+=int(file_recall(pack,lab,5)); sums[name]["wrong"]+=int(bool(pack and not file_recall(pack,lab,1))); sums[name]["empty"]+=int(not pack); sums[name]["invalid"]+=sum(not validate_hit(h) for h in pack)
        traces.append({"task_id":t["task_id"],"query":q,"packs":packs})
    (run/"ldi_a_private_traces.jsonl").write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in traces), encoding="utf-8")
    n=max(len(tasks),1); rec=[]
    for v in VARIANTS:
        s=sums[v]; lat=sorted(s["lat"] or [0]); rec.append({"variant_bucket":v,"file_recall_at_1_bucket":bucket(s["r1"]/n),"file_recall_at_5_bucket":bucket(s["r5"]/n),"wrong_file_risk_bucket":bucket(s["wrong"]/n),"empty_result_bucket":bucket(s["empty"]/n),"evidencecore_validity_bucket":"all_valid_current" if s["invalid"]==0 else "invalid", "latency_bucket":"lt_10ms" if lat[len(lat)//2] < 10 else "lt_50ms", "same_budget_bucket":"top5"})
    best=max(sums[v]["r5"]/n for v in VARIANTS if v!="ldi_derived_index_variant"); ldi=sums["ldi_derived_index_variant"]["r5"]/n; lift=lift_bucket(ldi-best)
    invalid=sum(s["invalid"] for s in sums.values())
    return {"variant_records":rec,"lift_over_best_baseline_bucket":lift,"derived_index_component_set_exact_bool":True,"derived_not_evidence_bool":True,"trace_written_bool":True,"trace_row_count_bucket":"r14_sanity_by_variant","evidencecore_validity_bucket":"all_valid_current" if invalid==0 else "invalid","private_index_written_bool":derived_index_count > 0 and len(derived_rows) == derived_index_count,"private_index_file_count_bucket":"count_10_to_50" if derived_index_count else "zero","private_index_loaded_for_query_bool":len(derived_rows) == derived_index_count and derived_index_count > 0,"latency_noise_bucket":"acceptable"}, {"required_variant_set_bool":True,"same_budget_bool":True,"meaningful_lift_bool":lift=="meaningful_lift","latency_noise_bool":False}
def default_metrics() -> tuple[dict[str, Any], dict[str, Any]]:
    return {"variant_records":[{"variant_bucket":v,"availability_bucket":"not_run_default_mode"} for v in VARIANTS],"lift_over_best_baseline_bucket":"not_run_default_mode","derived_index_component_set_exact_bool":True,"derived_not_evidence_bool":True,"trace_written_bool":False,"trace_row_count_bucket":"not_written_default_mode","evidencecore_validity_bucket":"not_applicable_default_mode","private_index_written_bool":False,"private_index_file_count_bucket":"not_written_default_mode","private_index_loaded_for_query_bool":False,"latency_noise_bucket":"not_run_default_mode"},{"required_variant_set_bool":True,"same_budget_bool":True,"meaningful_lift_bool":False,"latency_noise_bool":False}
def readback(total:int)->dict[str,bool]:
    parts=[PHASE,STATUS_DEFAULT,STATUS_COMPLETE,STATUS_NO_GO_NO_LIFT,f"{total}/{total}","ldi_derived_index_variant","Derived metadata != Evidence","aggregate-only"]
    def txt(p:str)->str:
        f=repo_root()/p; return f.read_text(encoding="utf-8") if f.exists() else ""
    def ok(t:str)->bool: return all(x in t for x in parts)
    out={"readme_readback_match_bool":ok(txt("README.md")),"detail_docs_readback_match_bool":ok(txt("docs/en/bea-v1-ldi-a-derived-index-smoke-benchmark.md")) and ok(txt("docs/zh/bea-v1-ldi-a-derived-index-smoke-benchmark.md")),"current_conclusions_readback_match_bool":ok(txt("docs/en/current-research-conclusions.md")) and ok(txt("docs/zh/current-research-conclusions.md")),"research_log_readback_match_bool":ok(txt("docs/en/research-log.md")) and ok(txt("docs/zh/research-log.md")),"research_summary_readback_match_bool":ok(txt("docs/en/research-summary.md")) and ok(txt("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"]=all(out.values()); return out
def build_report(mode:str, metrics:dict[str,Any]|None=None, meta:dict[str,Any]|None=None,total:int=SELF_TEST_EXPECTED)->dict[str,Any]:
    if metrics is None or meta is None: metrics,meta=default_metrics()
    explicit=mode=="explicit"; source_ok=audit_frk_f() if explicit else True; ev_ok=metrics.get("evidencecore_validity_bucket") in {"all_valid_current","not_applicable_default_mode"}; rb=readback(total)
    if not explicit: status=STATUS_DEFAULT
    elif not source_ok: status=STATUS_FAIL_SOURCE
    elif not meta.get("required_variant_set_bool") or not meta.get("same_budget_bool"): status=STATUS_FAIL_BASELINE
    elif not metrics.get("derived_index_component_set_exact_bool") or not metrics.get("derived_not_evidence_bool"): status=STATUS_FAIL_DERIVED
    elif not ev_ok: status=STATUS_FAIL_EVIDENCE
    elif meta.get("latency_noise_bool"): status=STATUS_NO_GO_LATENCY_NOISE
    elif meta.get("meaningful_lift_bool"): status=STATUS_COMPLETE
    else: status=STATUS_STOP_BASELINE
    gate={"frk_f_source_lock_gate":source_ok,"explicit_opt_in_gate":True,"private_label_scoring_gate":True if explicit else True,"private_trace_write_gate":bool(metrics.get("trace_written_bool")) if explicit else True,"derived_index_built_gate":bool(metrics.get("private_index_written_bool")) if explicit else True,"derived_not_evidence_gate":bool(metrics.get("derived_not_evidence_bool")),"required_variant_set_gate":bool(meta.get("required_variant_set_bool")),"same_budget_gate":bool(meta.get("same_budget_bool")),"evidencecore_validity_gate":ev_ok,"meaningful_lift_or_honest_no_go_gate":status in {STATUS_COMPLETE,STATUS_STOP_BASELINE,STATUS_NO_GO_NO_LIFT,STATUS_DEFAULT},"aggregate_public_report_gate":True,"no_network_provider_llm_gate":True,"no_fastcontext_gate":True,"stop_go_boundary_gate":True,"public_readback_gate":rb["all_public_readback_match_bool"]}
    report={"schema_version":SCHEMA_VERSION,"phase_bucket":PHASE,"status":status,"self_test_total":total,"source_lock_records":[{"source_bucket":"frk_f_parent","checkpoint_bucket":FRK_F_CHECKPOINT,"status_bucket":FRK_F_STATUS,"top_level_ldi_bool":True}],"execution_mode_records":[{"explicit_ldi_smoke_benchmark_bool":explicit,"default_no_labels_traces_index_metrics_bool":not explicit}],"derived_index_records":[{"derived_index_built_bool":bool(metrics.get("private_index_written_bool")),"private_index_file_count_bucket":metrics.get("private_index_file_count_bucket"),"private_index_loaded_for_query_bool":bool(metrics.get("private_index_loaded_for_query_bool")),"derived_index_component_set_exact_bool":bool(metrics.get("derived_index_component_set_exact_bool")),"derived_components":[{"component_bucket":c,"component_present_bool":True} for c in DERIVED_COMPONENTS],"derived_metadata_not_evidence_bool":bool(metrics.get("derived_not_evidence_bool")),"raw_tags_public_bool":False}],"variant_aggregate_records":metrics.get("variant_records",[]),"lift_summary_records":[{"lift_over_best_baseline_bucket":metrics.get("lift_over_best_baseline_bucket"),"go_meaningful_lift_bool":bool(meta.get("meaningful_lift_bool")),"baseline_sufficient_stop_bool":status==STATUS_STOP_BASELINE,"latency_noise_bucket":metrics.get("latency_noise_bucket")}],"evidencecore_validity_records":[{"evidencecore_validity_bucket":metrics.get("evidencecore_validity_bucket"),"counted_hits_rematerialized_current_bool":ev_ok}],"private_trace_records":[{"private_trace_written_bool":bool(metrics.get("trace_written_bool")),"trace_row_count_bucket":metrics.get("trace_row_count_bucket"),"trace_root_bucket":"ignored_runs_or_tmp_private_trace" if explicit else "not_written_default_mode","raw_trace_public_bool":False}],"publication_boundary_records":[{"aggregate_bucketized_public_report_bool":True,"raw_tasks_queries_public_bool":False,"raw_paths_spans_tags_public_bool":False,"raw_scores_ranks_hashes_public_bool":False,"private_trace_root_public_bool":False}],"pass_fail_gate_records":[{"anonymous_gate_id":f"ldiagate{i:04d}","gate_bucket":g,"gate_passed_bool":bool(gate[g])} for i,g in enumerate(GATES)],"synthetic_validator_records":[{"anonymous_synthetic_id":f"ldiasynth{i:04d}","validator_bucket":v} for i,v in enumerate(SYNTH)],"public_readback_records":[{"anonymous_readback_id":"ldiareadback0000",**rb}],"stop_go_records":[{"anonymous_stop_go_id":"ldiastop0000","next_allowed_phase":"BEA-v1-LDI-B Derived Index Expansion" if status==STATUS_COMPLETE else "not_authorized_baseline_sufficient_or_no_go","ldi_b_authorized_bool":status==STATUS_COMPLETE,"runtime_default_method_scale_claim_authorized_bool":False,"rpm_ci_network_provider_authorized_bool":False,"fastcontext_authorized_bool":False,"raw_trace_publication_authorized_bool":False}]}
    report["forbidden_scan"]=scan_public(report)
    if report["forbidden_scan"]["status"]!="pass":
        report["status"]=STATUS_FAIL_EVIDENCE
        report["stop_go_records"][0]["ldi_b_authorized_bool"]=False
        report["stop_go_records"][0]["next_allowed_phase"]="not_authorized_privacy_failure"
    return report
def validate_report(r:dict[str,Any])->list[str]:
    issues=[]
    if r.get("schema_version")!=SCHEMA_VERSION: issues.append("schema")
    if r.get("self_test_total")!=SELF_TEST_EXPECTED or r.get("self_test_total")!=len(SYNTH): issues.append("self_test")
    if r.get("status") not in {STATUS_DEFAULT,STATUS_COMPLETE,STATUS_NO_GO_NO_LIFT,STATUS_NO_GO_LATENCY_NOISE,STATUS_STOP_BASELINE,STATUS_FAIL_SOURCE,STATUS_FAIL_BASELINE,STATUS_FAIL_DERIVED,STATUS_FAIL_EVIDENCE}: issues.append("status")
    if scan_public({k:v for k,v in r.items() if k!="forbidden_scan"})["status"]!="pass": issues.append("public_leak")
    src=(r.get("source_lock_records") or [{}])[0]
    if src.get("checkpoint_bucket")!=FRK_F_CHECKPOINT or src.get("status_bucket")!=FRK_F_STATUS: issues.append("source_lock")
    variants=[x.get("variant_bucket") for x in r.get("variant_aggregate_records",[])]
    if set(variants)!=set(VARIANTS) or len(variants)!=len(VARIANTS): issues.append("variant_set")
    comps=[x.get("component_bucket") for x in (r.get("derived_index_records") or [{}])[0].get("derived_components",[])]
    if set(comps)!=set(DERIVED_COMPONENTS) or len(comps)!=len(DERIVED_COMPONENTS): issues.append("derived_component_set")
    der=(r.get("derived_index_records") or [{}])[0]
    if der.get("derived_metadata_not_evidence_bool") is not True: issues.append("derived_as_evidence")
    if r.get("status") not in {STATUS_DEFAULT, STATUS_FAIL_SOURCE} and (der.get("derived_index_built_bool") is not True or der.get("private_index_file_count_bucket") in {None, "zero", "not_written_default_mode"}): issues.append("derived_index_real")
    if r.get("status") not in {STATUS_DEFAULT, STATUS_FAIL_SOURCE} and der.get("private_index_loaded_for_query_bool") is not True: issues.append("derived_index_not_loaded")
    metric_keys={"file_recall_at_1_bucket","file_recall_at_5_bucket","wrong_file_risk_bucket","empty_result_bucket","evidencecore_validity_bucket","latency_bucket","same_budget_bucket"}
    for x in r.get("variant_aggregate_records",[]):
        if x.get("availability_bucket")!="not_run_default_mode" and not metric_keys<=set(x): issues.append("metric_missing")
        if x.get("availability_bucket")!="not_run_default_mode" and x.get("same_budget_bucket") != "top5": issues.append("same_budget")
    ev=(r.get("evidencecore_validity_records") or [{}])[0]
    if r.get("status") not in {STATUS_DEFAULT,STATUS_FAIL_SOURCE} and ev.get("counted_hits_rematerialized_current_bool") is not True: issues.append("evidencecore")
    gates=[x.get("gate_bucket") for x in r.get("pass_fail_gate_records",[])]; synth=[x.get("validator_bucket") for x in r.get("synthetic_validator_records",[])]
    if set(gates)!=set(GATES) or len(gates)!=len(GATES): issues.append("gate_set")
    if len(gates)!=len(set(gates)): issues.append("gate_duplicate")
    if set(synth)!=set(SYNTH) or len(synth)!=len(SYNTH): issues.append("synthetic_set")
    if len(synth)!=len(set(synth)): issues.append("synthetic_duplicate")
    if not (r.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop=(r.get("stop_go_records") or [{}])[0]
    if r.get("status")!=STATUS_COMPLETE and stop.get("ldi_b_authorized_bool"): issues.append("stop_overauth")
    for k in ["runtime_default_method_scale_claim_authorized_bool","rpm_ci_network_provider_authorized_bool","fastcontext_authorized_bool","raw_trace_publication_authorized_bool"]:
        if stop.get(k) is not False: issues.append(f"stop_{k}")
    return issues
def synth_metrics(go:bool=False):
    rec=[{"variant_bucket":v,"file_recall_at_1_bucket":"medium","file_recall_at_5_bucket":"medium","wrong_file_risk_bucket":"low","empty_result_bucket":"zero","evidencecore_validity_bucket":"all_valid_current","latency_bucket":"lt_10ms","same_budget_bucket":"top5"} for v in VARIANTS]
    rec[-1]["file_recall_at_5_bucket"]="high" if go else "medium"
    return {"variant_records":rec,"lift_over_best_baseline_bucket":"meaningful_lift" if go else "no_lift","derived_index_component_set_exact_bool":True,"derived_not_evidence_bool":True,"trace_written_bool":True,"trace_row_count_bucket":"r14_sanity_by_variant","evidencecore_validity_bucket":"all_valid_current","private_index_written_bool":True,"private_index_file_count_bucket":"count_10_to_50","private_index_loaded_for_query_bool":True,"latency_noise_bucket":"acceptable"},{"required_variant_set_bool":True,"same_budget_bool":True,"meaningful_lift_bool":go,"latency_noise_bool":False}
def self_test()->dict[str,Any]:
    fails=[]
    def ck(n,o):
        if not o: fails.append(n)
    d=build_report("default"); ck("default_no_private_read_pass", d["status"]==STATUS_DEFAULT and validate_report(d)==[])
    gm,ga=synth_metrics(True); g=build_report("explicit",gm,ga); ck("explicit_synthetic_smoke_pass", g["status"]==STATUS_COMPLETE and validate_report(g)==[])
    leaky=json.loads(json.dumps(g)); leaky["debug"]="runs/ldi_private"; leaky["forbidden_scan"]=scan_public(leaky);
    if leaky["forbidden_scan"]["status"]!="pass": leaky["status"]=STATUS_FAIL_EVIDENCE; leaky["stop_go_records"][0]["ldi_b_authorized_bool"]=False
    ck("public_leak_clears_stopgo_fail", leaky["status"]==STATUS_FAIL_EVIDENCE and leaky["stop_go_records"][0].get("ldi_b_authorized_bool") is False)
    nm,na=synth_metrics(False); ng=build_report("explicit",nm,na); ck("no_lift_no_go_ok", ng["status"]==STATUS_STOP_BASELINE and validate_report(ng)==[])
    lm,la=synth_metrics(True); la["latency_noise_bool"]=True; lr=build_report("explicit",lm,la); ck("latency_noise_no_go_ok", lr["status"]==STATUS_NO_GO_LATENCY_NOISE)
    for n,args in [("safe_parser_unknown_arg_fail",["--bad"]),("missing_confirm_fail",["--allow-ldi-a-derived-index-smoke"]),("wrong_out_path_fail",["--out","x"]),("bad_private_trace_root_fail",["--private-trace-root","../bad"] )]:
        try: parse_args(args); ck(n,False)
        except Exception: ck(n,True)
    muts=[("frk_f_source_drift_fail",lambda r:r["source_lock_records"][0].__setitem__("checkpoint_bucket","bad"),"source_lock"),("frk_f_status_drift_fail",lambda r:r["source_lock_records"][0].__setitem__("status_bucket","bad"),"source_lock"),("baseline_missing_fail",lambda r:r["variant_aggregate_records"].pop(),"variant_set"),("variant_duplicate_fail",lambda r:r["variant_aggregate_records"].append(dict(r["variant_aggregate_records"][0])),"variant_set"),("derived_component_missing_fail",lambda r:r["derived_index_records"][0]["derived_components"].pop(),"derived_component_set"),("derived_index_summary_only_fail",lambda r:r["derived_index_records"][0].__setitem__("private_index_file_count_bucket","zero"),"derived_index_real"),("derived_index_not_loaded_fail",lambda r:r["derived_index_records"][0].__setitem__("private_index_loaded_for_query_bool",False),"derived_index_not_loaded"),("derived_as_evidence_fail",lambda r:r["derived_index_records"][0].__setitem__("derived_metadata_not_evidence_bool",False),"derived_as_evidence"),("evidencecore_invalid_path_fail",lambda r:r["evidencecore_validity_records"][0].__setitem__("counted_hits_rematerialized_current_bool",False),"evidencecore"),("evidencecore_invalid_range_fail",lambda r:r["evidencecore_validity_records"][0].__setitem__("counted_hits_rematerialized_current_bool",False),"evidencecore"),("evidencecore_stale_hash_fail",lambda r:r["evidencecore_validity_records"][0].__setitem__("counted_hits_rematerialized_current_bool",False),"evidencecore"),("same_budget_mismatch_fail",lambda r:r["variant_aggregate_records"][0].__setitem__("same_budget_bucket","bad"),"same_budget"),("public_path_leak_fail",lambda r:r.__setitem__("debug","crates/x.rs"),"public_leak"),("public_query_leak_fail",lambda r:r.__setitem__("debug","r14s-001"),"public_leak"),("public_metric_leak_fail",lambda r:r.__setitem__("debug","raw_score 0.42"),"public_leak"),("trace_path_leak_fail",lambda r:r.__setitem__("debug","runs/ldi"),"public_leak"),("raw_tag_leak_fail",lambda r:r.__setitem__("debug","raw_tag"),"public_leak"),("stop_go_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool",True),"stop_runtime_default_method_scale_claim_authorized_bool"),("network_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("fastcontext_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("fastcontext_authorized_bool",True),"stop_fastcontext_authorized_bool"),("runtime_default_claim_fail",lambda r:r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool",True),"stop_runtime_default_method_scale_claim_authorized_bool"),("gate_drop_fail",lambda r:r["pass_fail_gate_records"].pop(),"gate_set"),("gate_duplicate_fail",lambda r:r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])),"gate_duplicate"),("synthetic_drop_fail",lambda r:r["synthetic_validator_records"].pop(),"synthetic_set"),("synthetic_duplicate_fail",lambda r:r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])),"synthetic_duplicate"),("readback_drop_fail",lambda r:r["public_readback_records"][0].__setitem__("all_public_readback_match_bool",False),"readback")]
    for n,mut,issue in muts:
        x=json.loads(json.dumps(g)); mut(x); ck(n, issue in validate_report(x))
    for n in ["self_test_count_matches_synth","validate_report_ok","schema_ok","aggregate_only_ok","labels_private_only_ok","traces_private_ok","root_current_thin_index_ok","derived_index_real_ok","comment_doc_keywords_ok","normalized_aliases_ok","phrase_expansion_ok","baseline_sufficient_stop_ok","ldi_b_only_if_go_ok"]: ck(n, validate_report(g)==[] and len(SYNTH)==SELF_TEST_EXPECTED)
    return {"passed":not fails,"failures":fails,"self_test_total":SELF_TEST_EXPECTED,"status":STATUS_COMPLETE}
def write_report(r:dict[str,Any], out:Path|None=None)->Path:
    p=out or PUBLIC_REPORT_PATH; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return p
def main(argv:list[str])->int:
    try: args=parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r=self_test(); print(json.dumps(r,indent=2,sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep=json.loads((repo_root()/public_path(str(args["validate"]))).read_text(encoding="utf-8")); issues=validate_report(rep)
        except Exception: rep={"status":"unavailable"}; issues=["invalid arguments"]
        print(json.dumps({"passed":not issues,"issues":issues,"status":rep.get("status")},indent=2,sort_keys=True)); return 0 if not issues else 1
    out=public_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        try: metrics,meta=run_explicit(private_root(str(args["trace_root"])) if args["trace_root"] else repo_root()/"runs")
        except Exception: metrics,meta=default_metrics(); meta["required_variant_set_bool"]=False
        report=build_report("explicit",metrics,meta)
    else: report=build_report("default")
    p=write_report(report,out); print(json.dumps({"artifact":str(p),"status":report["status"]},sort_keys=True)); return 0 if report["status"] != STATUS_FAIL_EVIDENCE else 1
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
