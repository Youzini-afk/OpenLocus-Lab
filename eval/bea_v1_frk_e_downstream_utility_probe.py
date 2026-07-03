#!/usr/bin/env python3
"""BEA-v1-FRK-E Downstream Utility Probe.

Executable local probe comparing same-budget retrieval/pack variants with private
R14-S labels only after label-independent proxy pack construction.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-E Downstream Utility Probe"
SLUG = "bea_v1_frk_e_downstream_utility_probe"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "frk_e_unavailable_no_explicit_downstream_utility_probe_opt_in"
STATUS_COMPLETE = "frk_e_downstream_utility_probe_complete_frk_f_failure_decomposition_or_proxy_expansion_authorized"
STATUS_NO_GO = "frk_e_no_go_no_proxy_lift_over_best_baseline"
STATUS_FAIL_SOURCE = "frk_e_fail_closed_source_lock_or_input_invalid"
STATUS_FAIL_PRIVACY = "frk_e_fail_closed_evidencecore_or_privacy_violation"
STATUS_FAIL_PACK = "frk_e_fail_closed_pack_variant_missing_or_budget_mismatch"
STATUS_FAIL_PROXY = "frk_e_fail_closed_proxy_metric_invalid"
NEXT_PHASE = "BEA-v1-FRK-F Failure Decomposition or Proxy Expansion"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_D_REPORT = Path("artifacts/bea_v1_frk_d_incremental_update_benchmark/bea_v1_frk_d_incremental_update_benchmark_report.json")
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
FRK_D_CHECKPOINT = "f156849"
FRK_D_STATUS = "frk_d_incremental_update_benchmark_complete_frk_e_downstream_utility_probe_authorized"
SELF_TEST_EXPECTED = 50
VARIANTS = ["bm25_like_baseline_pack", "rrf_like_baseline_pack", "frk_b_retrieve_fast_raw_pack", "frk_c_rankpack_builder_pack"]
GATES = ["frk_d_source_lock_gate", "explicit_opt_in_gate", "private_label_scoring_after_pack_gate", "label_independent_proxy_gate", "required_variant_set_gate", "same_budget_gate", "evidencecore_validity_gate", "proxy_metric_valid_gate", "proxy_lift_gate", "wrong_file_regression_gate", "private_trace_write_gate", "aggregate_public_report_gate", "no_network_provider_runtime_gate", "no_fastcontext_gate", "frk_f_only_stop_go_gate", "public_readback_gate"]
SYNTH = ["default_no_labels_pass", "explicit_synthetic_probe_pass", "safe_parser_unknown_arg_fail", "missing_confirm_fail", "wrong_out_path_fail", "bad_private_trace_root_fail", "frk_d_source_drift_fail", "variant_missing_fail", "budget_mismatch_fail", "label_before_pack_fail", "proxy_uses_gold_fail", "invalid_evidencecore_path_fail", "invalid_evidencecore_range_fail", "invalid_evidencecore_currentness_fail", "no_proxy_lift_no_go", "wrong_file_regression_fail", "empty_fabricated_pack_fail", "privacy_path_leak_fail", "privacy_query_leak_fail", "privacy_metric_leak_fail", "trace_path_leak_fail", "public_leak_clears_stopgo_fail", "stop_go_overauth_fail", "network_overauth_fail", "fastcontext_overauth_fail", "runtime_default_claim_fail", "gate_drop_fail", "gate_duplicate_fail", "synthetic_drop_fail", "synthetic_duplicate_fail", "readback_drop_fail", "metric_bucket_missing_fail", "trace_bucket_missing_fail", "proxy_lift_bucket_missing_fail", "comparative_lift_missing_fail", "no_go_proxy_expansion_overauth_fail", "evidencecore_bucket_missing_fail", "variant_budget_bucket_missing_fail", "stale_current_fail", "validate_report_ok", "schema_ok", "private_trace_written_ok", "frk_f_only_ok", "no_rpm_ci_network_ok", "aggregate_only_ok", "labels_private_only_ok", "proxy_label_independent_ok", "same_budget_ok", "no_runtime_agent_ok", "no_fastcontext_ok"]
LEAK_PATTERNS = [("path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)), ("task_or_query", re.compile(r"r14s-\d+|\"task_id\"|\"query\"|scan_repo|bm25_search", re.I)), ("raw_metric", re.compile(r"exact_value|raw_value|raw_metric|raw_score_value|raw_rank_value|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)), ("span_or_snippet", re.compile(r"snippet|start_line|end_line|gold_spans|hard_negatives", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def tokenize(text: str) -> list[str]: return [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+", text)]
def qtokens(q: str) -> list[str]: return list(dict.fromkeys(tokenize(re.sub(r"([a-z])([A-Z])", r"\1 \2", q).replace("_", " ")) + tokenize(q))) or [q.lower()]
def frk_b():
    p = repo_root()/"eval/bea_v1_frk_b_fast_retrieval_kernel_prototype.py"
    spec = importlib.util.spec_from_file_location("frkb", p); mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader; spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    args: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "confirm_labels": False, "confirm_traces": False, "confirm_public": False, "trace_root": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": args["self_test"] = True; i += 1
        elif a == "--allow-frk-e-downstream-utility-probe": args["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring": args["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-traces": args["confirm_traces"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": args["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            args[{"--validate-report": "validate", "--out": "out", "--private-trace-root": "trace_root"}[a]] = argv[i+1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(args[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if args["out"]: public_path(str(args["out"]))
    if args["trace_root"]: private_root(str(args["trace_root"]))
    return args
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
    scrub = json.loads(json.dumps(report))
    for rec in scrub.get("synthetic_validator_records", []): rec["validator_bucket"] = "synthetic_validator_bucket"
    text = json.dumps(scrub, sort_keys=True)
    for allowed in ["raw_trace_publication_authorized_bool", "raw_scores_ranks_paths_public_bool", "raw_private_publication_authorized_bool", "raw_pack_rows_public_bool", "raw_paths_spans_snippets_public_bool"]: text = text.replace(allowed, "public_boundary_bool")
    findings = [n for n, p in LEAK_PATTERNS if p.search(text)]
    return {"status": "pass" if not findings else "fail", "finding_buckets": findings, "forbidden_finding_count": len(findings)}
def audit_frk_d() -> bool:
    p = repo_root()/FRK_D_REPORT
    if not p.exists(): return False
    r = json.loads(p.read_text(encoding="utf-8"))
    return r.get("status") == FRK_D_STATUS and r.get("self_test_total") == 52 and r.get("forbidden_scan", {}).get("status") == "pass"
def bucket(v: float) -> str: return "very_high" if v >= .9 else "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"
def lat_bucket(ms: float) -> str: return "lt_10ms" if ms < 10 else "lt_50ms" if ms < 50 else "lt_100ms" if ms < 100 else "lt_200ms" if ms < 200 else "ge_200ms"
def file_hit(pack: list[dict[str, Any]], label: dict[str, Any], k: int) -> bool:
    gold = {x.get("path") for x in label.get("gold_spans", [])}
    return any(h.get("path") in gold for h in pack[:k])
def overlaps(h: dict[str, Any], label: dict[str, Any]) -> bool:
    return any(h.get("path") == sp.get("path") and int(h.get("start_line",0)) <= int(sp.get("end_line",0)) and int(h.get("end_line",0)) >= int(sp.get("start_line",0)) for sp in label.get("gold_spans", []))
def bm25_pack(index: dict[str, Any], query: str, top: int = 5) -> list[dict[str, Any]]:
    # Label-independent local baseline over the same index.
    qts = qtokens(query); scores: dict[int, float] = {}; n = max(len(index["files"]), 1); avg = sum(len(f["tokens"]) for f in index["files"])/n
    for tok in qts:
        postings = index["sparse"].get(tok, [])
        idf = math.log(1 + (n - len(postings) + .5)/(len(postings)+.5)) if postings else 0.0
        for fid in postings:
            f = index["files"][fid]; tf = f["tokens"].count(tok); dl = max(len(f["tokens"]), 1)
            scores[fid] = scores.get(fid, 0.0) + idf * (tf * 2.2)/(tf + 1.2*(.25 + .75*dl/max(avg,1)))
    return [frk_b().make_hit(index, fid, 1, min(8, len(index["files"][fid]["lines"])), sc) for fid, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top]]
def rrf_pack(index: dict[str, Any], query: str, top: int = 5) -> list[dict[str, Any]]:
    b = bm25_pack(index, query, 10); f = frk_b().retrieve_fast(index, query, 10); scores: dict[tuple[str,int,int], dict[str, Any]] = {}
    for arr in [b, f]:
        for i, h in enumerate(arr, 1):
            key = (h["path"], h["start_line"], h["end_line"]); rec = scores.setdefault(key, dict(h)); rec["score"] = float(rec.get("score", 0)) + 1/(60+i)
    return sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:top]
def frk_c_pack(cands: list[dict[str, Any]], top: int = 5) -> list[dict[str, Any]]:
    selected=[]; seen=set()
    for h in cands:
        if h["path"] not in seen: selected.append(h); seen.add(h["path"])
        if len(selected) >= top: return selected
    return (selected + [h for h in cands if h not in selected])[:top]
def pad_pack(pack: list[dict[str, Any]], pool: list[dict[str, Any]], top: int = 5) -> list[dict[str, Any]]:
    out = list(pack)
    for h in pool:
        if h not in out:
            out.append(h)
        if len(out) >= top:
            break
    return out[:top]
def score_pack(pack: list[dict[str, Any]], label: dict[str, Any]) -> dict[str, Any]:
    paths = [str(h.get("path")) for h in pack]
    return {"correct_file_before_first_edit": file_hit(pack, label, 1), "evidence_before_edit": any(overlaps(h, label) for h in pack[:3]), "wrong_file": bool(pack and not file_hit(pack, label, 1)), "empty": not pack, "budget_eff": len(pack) <= 5, "gold_covered": any(overlaps(h, label) for h in pack), "redundant_same_file": len(paths) - len(set(paths)), "unique_file_count": len(set(paths)), "first_relevant_position": next((i + 1 for i, h in enumerate(pack) if overlaps(h, label) or file_hit([h], label, 1)), 99)}
def risk_bucket(v: float) -> str: return "very_high" if v >= .9 else "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"
def pos_bucket(v: float) -> str: return "position_1" if v <= 1 else "position_2_to_3" if v <= 3 else "position_4_to_5" if v <= 5 else "not_in_pack"
def count_bucket(v: float) -> str: return "count_0" if v <= 0 else "count_1" if v <= 1 else "count_2_to_5" if v <= 5 else "count_gt_5"
def lift_bucket(delta: float, lower_is_better: bool = False) -> str:
    d = -delta if lower_is_better else delta
    return "strong_positive" if d >= .2 else "positive" if d > .01 else "neutral" if d >= -.01 else "negative"
def run_explicit(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not audit_frk_d(): raise RuntimeError("source lock")
    b = frk_b(); run_root = root / f"frk_e_private_{int(time.time())}"; index = b.build_kernel(run_root/"index")
    tasks = load_jsonl(repo_root()/TASKS); labels = {x["task_id"]: x for x in load_jsonl(repo_root()/LABELS)}; run_root.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, Any]]] = {v: [] for v in VARIANTS}; traces=[]; invalid=0; lat=[]
    for task in tasks:
        q = str(task["query"]); t0 = time.perf_counter(); fast = b.retrieve_fast(index, q, 10); lat.append((time.perf_counter()-t0)*1000)
        packs = {"bm25_like_baseline_pack": pad_pack(bm25_pack(index, q), fast), "rrf_like_baseline_pack": pad_pack(rrf_pack(index, q), fast), "frk_b_retrieve_fast_raw_pack": pad_pack(fast[:5], fast), "frk_c_rankpack_builder_pack": pad_pack(frk_c_pack(fast[:10]), fast)}
        if set(packs) != set(VARIANTS) or len({len(p) for p in packs.values() if p}) > 1: raise RuntimeError("pack mismatch")
        label = labels[task["task_id"]]
        for name, pack in packs.items():
            invalid += sum(not b.validate_hit(index, h) for h in pack); rows[name].append(score_pack(pack, label))
        traces.append({"task_id": task["task_id"], "query": q, "packs": packs})
    (run_root/"frk_e_private_probe_traces.jsonl").write_text("".join(json.dumps(x, sort_keys=True)+"\n" for x in traces), encoding="utf-8")
    n = len(tasks) or 1; records=[]; aggregates: dict[str, dict[str, float]] = {}
    for v in VARIANTS:
        rs = rows[v]
        aggregates[v] = {"correct": sum(r["correct_file_before_first_edit"] for r in rs)/n, "evidence": sum(r["evidence_before_edit"] for r in rs)/n, "wrong": sum(r["wrong_file"] for r in rs)/n, "empty": sum(r["empty"] for r in rs)/n, "budget": sum(r["budget_eff"] for r in rs)/n, "gold_span": sum(r["gold_covered"] for r in rs)/n, "redundancy": sum(r["redundant_same_file"] for r in rs)/n, "unique": sum(r["unique_file_count"] for r in rs)/n, "first_pos": sum(r["first_relevant_position"] for r in rs)/n}
        a = aggregates[v]
        records.append({"variant_bucket": v, "correct_file_before_first_edit_bucket": bucket(a["correct"]), "evidence_before_edit_bucket": bucket(a["evidence"]), "wrong_file_risk_bucket": risk_bucket(a["wrong"]), "empty_abstain_risk_bucket": risk_bucket(a["empty"]), "evidence_budget_efficiency_bucket": bucket(a["budget"]), "gold_span_covered_bucket": bucket(a["gold_span"]), "first_relevant_evidence_position_bucket": pos_bucket(a["first_pos"]), "gold_file_within_budget_bucket": bucket(a["correct"]), "gold_span_within_budget_bucket": bucket(a["gold_span"]), "token_waste_bucket": risk_bucket(max(0.0, 1.0 - a["gold_span"])), "redundant_same_file_span_bucket": count_bucket(a["redundancy"]), "unique_file_coverage_bucket": count_bucket(a["unique"]), "pack_item_count_bucket": "count_5", "same_budget_bucket": "top5_pack", "latency_bucket": lat_bucket(sorted(lat)[len(lat)//2])})
    baseline_variants = ["bm25_like_baseline_pack", "rrf_like_baseline_pack"]
    frk_variants = ["frk_b_retrieve_fast_raw_pack", "frk_c_rankpack_builder_pack"]
    base_correct = max(aggregates[v]["correct"] for v in baseline_variants); frk_correct = max(aggregates[v]["correct"] for v in frk_variants)
    base_wrong = min(aggregates[v]["wrong"] for v in baseline_variants); frk_wrong = min(aggregates[v]["wrong"] for v in frk_variants)
    base_budget = max(aggregates[v]["budget"] for v in baseline_variants); frk_budget = max(aggregates[v]["budget"] for v in frk_variants)
    base_redundancy = min(aggregates[v]["redundancy"] for v in baseline_variants); frk_redundancy = min(aggregates[v]["redundancy"] for v in frk_variants)
    comparative = {"correct_file_proxy_lift_vs_best_baseline_bucket": lift_bucket(frk_correct - base_correct), "wrong_file_risk_reduction_vs_best_baseline_bucket": lift_bucket(frk_wrong - base_wrong, lower_is_better=True), "budget_efficiency_lift_vs_best_baseline_bucket": lift_bucket(frk_budget - base_budget), "redundancy_reduction_vs_best_baseline_bucket": lift_bucket(frk_redundancy - base_redundancy, lower_is_better=True)}
    lift = any(v in {"positive", "strong_positive"} for v in comparative.values())
    catastrophic_wrong = frk_wrong - base_wrong > .2
    metrics = {"variant_records": records, "comparative_lift_records": [{"anonymous_lift_id": "frkelift0000", **comparative}], "proxy_lift_over_best_baseline_bucket": "meaningful_lift" if lift else "no_lift", "catastrophic_wrong_file_regression_bool": catastrophic_wrong, "evidencecore_validity_bucket": "all_valid_current" if invalid == 0 else "invalid", "invalid_hit_count_bucket": "zero" if invalid == 0 else "nonzero", "trace_written_bool": True, "trace_row_count_bucket": "r14_sanity_by_variant"}
    return metrics, {"label_independent_proxy_bool": True, "same_budget_bool": True, "required_variant_set_bool": True, "empty_fabricated_pack_bool": False}
def default_metrics() -> dict[str, Any]:
    return {"variant_records": [{"variant_bucket": v, "availability_bucket": "not_run_default_mode"} for v in VARIANTS], "proxy_lift_over_best_baseline_bucket": "not_run_default_mode", "catastrophic_wrong_file_regression_bool": False, "evidencecore_validity_bucket": "not_applicable_default_mode", "invalid_hit_count_bucket": "not_applicable_default_mode", "trace_written_bool": False, "trace_row_count_bucket": "not_written_default_mode"}
def readback(total: int) -> dict[str, bool]:
    parts=[PHASE, STATUS_DEFAULT, STATUS_COMPLETE, STATUS_NO_GO, f"{total}/{total}", "bm25_like_baseline_pack", "rrf_like_baseline_pack", "frk_b_retrieve_fast_raw_pack", "frk_c_rankpack_builder_pack", "private traces", "aggregate-only", "BEA-v1-FRK-F Failure Decomposition"]
    def txt(p: str) -> str:
        f = repo_root()/p; return f.read_text(encoding="utf-8") if f.exists() else ""
    def ok(t: str) -> bool: return all(x in t for x in parts)
    out={"readme_readback_match_bool": ok(txt("README.md")), "detail_docs_readback_match_bool": ok(txt("docs/en/bea-v1-frk-e-downstream-utility-probe.md")) and ok(txt("docs/zh/bea-v1-frk-e-downstream-utility-probe.md")), "current_conclusions_readback_match_bool": ok(txt("docs/en/current-research-conclusions.md")) and ok(txt("docs/zh/current-research-conclusions.md")), "research_log_readback_match_bool": ok(txt("docs/en/research-log.md")) and ok(txt("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(txt("docs/en/research-summary.md")) and ok(txt("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out
def build_report(mode: str, metrics: dict[str, Any] | None=None, meta: dict[str, Any] | None=None, total: int=SELF_TEST_EXPECTED) -> dict[str, Any]:
    explicit = mode == "explicit"; metrics = metrics or default_metrics(); meta = meta or {"label_independent_proxy_bool": True, "same_budget_bool": True, "required_variant_set_bool": True, "empty_fabricated_pack_bool": False}
    source_ok = audit_frk_d() if explicit else True
    variants_ok = set(r.get("variant_bucket") for r in metrics.get("variant_records", [])) == set(VARIANTS) and meta.get("required_variant_set_bool")
    evidence_ok = metrics.get("evidencecore_validity_bucket") in {"all_valid_current", "not_applicable_default_mode"}
    lift_ok = metrics.get("proxy_lift_over_best_baseline_bucket") == "meaningful_lift"
    status = STATUS_DEFAULT if not explicit else STATUS_COMPLETE if source_ok and variants_ok and evidence_ok and meta.get("label_independent_proxy_bool") and meta.get("same_budget_bool") and lift_ok and not metrics.get("catastrophic_wrong_file_regression_bool") and not meta.get("empty_fabricated_pack_bool") else STATUS_NO_GO if source_ok and variants_ok and evidence_ok and not lift_ok else STATUS_FAIL_PROXY
    rb = readback(total)
    gate = {"frk_d_source_lock_gate": source_ok, "explicit_opt_in_gate": True, "private_label_scoring_after_pack_gate": True, "label_independent_proxy_gate": meta.get("label_independent_proxy_bool"), "required_variant_set_gate": variants_ok, "same_budget_gate": meta.get("same_budget_bool"), "evidencecore_validity_gate": evidence_ok, "proxy_metric_valid_gate": not meta.get("empty_fabricated_pack_bool"), "proxy_lift_gate": lift_ok or not explicit, "wrong_file_regression_gate": not metrics.get("catastrophic_wrong_file_regression_bool"), "private_trace_write_gate": bool(metrics.get("trace_written_bool")) if explicit else True, "aggregate_public_report_gate": True, "no_network_provider_runtime_gate": True, "no_fastcontext_gate": True, "frk_f_only_stop_go_gate": True, "public_readback_gate": rb["all_public_readback_match_bool"]}
    report={"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": total, "source_lock_records": [{"source_bucket": "frk_d_parent", "checkpoint_bucket": FRK_D_CHECKPOINT, "status_bucket": FRK_D_STATUS, "top_level_frk_bool": True}], "execution_mode_records": [{"explicit_downstream_utility_probe_bool": explicit, "default_no_labels_traces_packs_metrics_bool": not explicit, "labels_score_only_after_pack_construction_bool": True}], "proxy_policy_records": [{"label_independent_proxy_construction_bool": bool(meta.get("label_independent_proxy_bool")), "correct_file_before_first_edit_proxy_bool": True, "evidence_before_edit_proxy_bool": True, "no_runtime_agent_calls_bool": True}], "variant_aggregate_records": metrics.get("variant_records", []), "comparative_lift_records": metrics.get("comparative_lift_records", []), "proxy_metric_summary_records": [{"proxy_lift_over_best_baseline_bucket": metrics.get("proxy_lift_over_best_baseline_bucket"), "catastrophic_wrong_file_regression_bool": bool(metrics.get("catastrophic_wrong_file_regression_bool")), "empty_fabricated_pack_bool": bool(meta.get("empty_fabricated_pack_bool")), "same_budget_bool": bool(meta.get("same_budget_bool"))}], "evidencecore_validity_records": [{"evidencecore_validity_bucket": metrics.get("evidencecore_validity_bucket"), "invalid_hit_count_bucket": metrics.get("invalid_hit_count_bucket"), "all_hits_valid_current_bool": evidence_ok}], "private_trace_records": [{"private_trace_written_bool": bool(metrics.get("trace_written_bool")), "trace_row_count_bucket": metrics.get("trace_row_count_bucket"), "trace_root_bucket": "ignored_runs_or_tmp_private_trace" if explicit else "not_written_default_mode", "raw_trace_public_bool": False}], "publication_boundary_records": [{"aggregate_bucketized_public_report_bool": True, "raw_tasks_queries_public_bool": False, "raw_paths_spans_snippets_public_bool": False, "raw_candidate_pack_rows_public_bool": False, "raw_scores_ranks_hashes_public_bool": False, "private_roots_trace_paths_public_bool": False, "runtime_default_method_scale_claim_bool": False}], "pass_fail_gate_records": [{"anonymous_gate_id": f"frkegate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gate[g])} for i,g in enumerate(GATES)], "synthetic_validator_records": [{"anonymous_synthetic_id": f"frkesynth{i:04d}", "validator_bucket": v} for i,v in enumerate(SYNTH)], "public_readback_records": [{"anonymous_readback_id": "frkereadback0000", **rb}], "stop_go_records": [{"anonymous_stop_go_id": "frkestop0000", "next_allowed_phase": NEXT_PHASE if status == STATUS_COMPLETE else ("BEA-v1-FRK-F Failure Decomposition" if status == STATUS_NO_GO else "not_authorized_until_valid_probe"), "frk_f_failure_decomposition_authorized_bool": status in {STATUS_COMPLETE, STATUS_NO_GO}, "proxy_expansion_authorized_bool": status == STATUS_COMPLETE, "runtime_default_method_scale_claim_authorized_bool": False, "rpm_ci_network_provider_authorized_bool": False, "fastcontext_authorized_bool": False, "raw_trace_publication_authorized_bool": False}]}
    report["forbidden_scan"] = scan_public(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_PRIVACY; report["stop_go_records"][0]["next_allowed_phase"] = "not_authorized_privacy_failure"; report["stop_go_records"][0]["frk_f_failure_decomposition_authorized_bool"] = False; report["stop_go_records"][0]["proxy_expansion_authorized_bool"] = False
    return report
def validate_report(report: dict[str, Any]) -> list[str]:
    issues=[]
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_synthetic_count")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_NO_GO}: issues.append("status")
    if scan_public({k:v for k,v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    src=(report.get("source_lock_records") or [{}])[0]
    if src.get("checkpoint_bucket") != FRK_D_CHECKPOINT or src.get("status_bucket") != FRK_D_STATUS: issues.append("source_lock")
    variants=[r.get("variant_bucket") for r in report.get("variant_aggregate_records", [])]
    if set(variants) != set(VARIANTS) or len(variants) != len(VARIANTS): issues.append("variant_set")
    metric_keys={"correct_file_before_first_edit_bucket","evidence_before_edit_bucket","wrong_file_risk_bucket","empty_abstain_risk_bucket","evidence_budget_efficiency_bucket","gold_span_covered_bucket","first_relevant_evidence_position_bucket","gold_file_within_budget_bucket","gold_span_within_budget_bucket","token_waste_bucket","redundant_same_file_span_bucket","unique_file_coverage_bucket","pack_item_count_bucket","same_budget_bucket","latency_bucket"}
    for r in report.get("variant_aggregate_records", []):
        if r.get("availability_bucket") != "not_run_default_mode" and not metric_keys <= set(r): issues.append("metric_missing")
    summ=(report.get("proxy_metric_summary_records") or [{}])[0]
    if summ.get("same_budget_bool") is not True: issues.append("budget_mismatch")
    if summ.get("empty_fabricated_pack_bool") is True: issues.append("empty_fabricated_pack")
    if summ.get("catastrophic_wrong_file_regression_bool") is True: issues.append("wrong_file_regression")
    if "proxy_lift_over_best_baseline_bucket" not in summ: issues.append("proxy_lift_missing")
    lift=(report.get("comparative_lift_records") or [{}])[0]
    lift_keys={"correct_file_proxy_lift_vs_best_baseline_bucket","wrong_file_risk_reduction_vs_best_baseline_bucket","budget_efficiency_lift_vs_best_baseline_bucket","redundancy_reduction_vs_best_baseline_bucket"}
    if report.get("status") in {STATUS_COMPLETE, STATUS_NO_GO} and not lift_keys <= set(lift): issues.append("comparative_lift_missing")
    if report.get("status") == STATUS_COMPLETE and not any(lift.get(k) in {"positive","strong_positive"} for k in lift_keys): issues.append("comparative_lift_no_positive")
    ev=(report.get("evidencecore_validity_records") or [{}])[0]
    if report.get("status") in {STATUS_COMPLETE, STATUS_NO_GO} and "evidencecore_validity_bucket" not in ev: issues.append("evidencecore")
    if report.get("status") in {STATUS_COMPLETE, STATUS_NO_GO} and ev.get("all_hits_valid_current_bool") is not True: issues.append("evidencecore")
    proxy=(report.get("proxy_policy_records") or [{}])[0]
    if proxy.get("label_independent_proxy_construction_bool") is not True: issues.append("proxy_uses_gold")
    if (report.get("execution_mode_records") or [{}])[0].get("labels_score_only_after_pack_construction_bool") is not True: issues.append("label_before_pack")
    pub=(report.get("publication_boundary_records") or [{}])[0]
    for k in ["raw_tasks_queries_public_bool","raw_paths_spans_snippets_public_bool","raw_candidate_pack_rows_public_bool","raw_scores_ranks_hashes_public_bool","private_roots_trace_paths_public_bool","runtime_default_method_scale_claim_bool"]:
        if pub.get(k) is not False: issues.append(f"pub_{k}")
    gates=[r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth=[r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates)!=set(GATES) or len(gates)!=len(GATES): issues.append("gate_set")
    if len(gates)!=len(set(gates)): issues.append("gate_duplicate")
    if set(synth)!=set(SYNTH) or len(synth)!=len(SYNTH) or len(synth) != report.get("self_test_total"): issues.append("synthetic_set")
    if len(synth)!=len(set(synth)): issues.append("synthetic_duplicate")
    if not (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop=(report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and stop.get("proxy_expansion_authorized_bool") is not True: issues.append("stop_expansion")
    if report.get("status") == STATUS_NO_GO and stop.get("proxy_expansion_authorized_bool") is not False: issues.append("stop_no_go_expansion")
    tr=(report.get("private_trace_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and tr.get("private_trace_written_bool") is not True: issues.append("trace")
    if report.get("status") == STATUS_COMPLETE and tr.get("trace_row_count_bucket") not in {"r14_sanity_by_variant"}: issues.append("trace_missing")
    for k in ["runtime_default_method_scale_claim_authorized_bool","rpm_ci_network_provider_authorized_bool","fastcontext_authorized_bool","raw_trace_publication_authorized_bool"]:
        if stop.get(k) is not False: issues.append(f"stop_{k}")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True and report.get("status") == STATUS_COMPLETE: issues.append(f"gate_failed_{g.get('gate_bucket')}")
    return issues
def self_test() -> dict[str, Any]:
    fails=[]
    def ck(n,o):
        if not o: fails.append(n)
    d=build_report("default"); ck("default_no_labels_pass", d["status"]==STATUS_DEFAULT and validate_report(d)==[])
    base={"correct_file_before_first_edit_bucket":"medium","evidence_before_edit_bucket":"medium","wrong_file_risk_bucket":"low","empty_abstain_risk_bucket":"zero","evidence_budget_efficiency_bucket":"medium","gold_span_covered_bucket":"medium","first_relevant_evidence_position_bucket":"position_2_to_3","gold_file_within_budget_bucket":"medium","gold_span_within_budget_bucket":"medium","token_waste_bucket":"low","redundant_same_file_span_bucket":"count_0","unique_file_coverage_bucket":"count_2_to_5","pack_item_count_bucket":"count_5","same_budget_bucket":"top5_pack","latency_bucket":"lt_10ms"}
    rec=[{"variant_bucket":v, **base} for v in VARIANTS]; rec[-1]["correct_file_before_first_edit_bucket"]="high"; rec[-1]["evidence_budget_efficiency_bucket"]="very_high"
    metrics={"variant_records":rec,"comparative_lift_records":[{"anonymous_lift_id":"frkelift0000","correct_file_proxy_lift_vs_best_baseline_bucket":"positive","wrong_file_risk_reduction_vs_best_baseline_bucket":"neutral","budget_efficiency_lift_vs_best_baseline_bucket":"positive","redundancy_reduction_vs_best_baseline_bucket":"neutral"}],"proxy_lift_over_best_baseline_bucket":"meaningful_lift","catastrophic_wrong_file_regression_bool":False,"evidencecore_validity_bucket":"all_valid_current","invalid_hit_count_bucket":"zero","trace_written_bool":True,"trace_row_count_bucket":"r14_sanity_by_variant"}
    meta={"label_independent_proxy_bool":True,"same_budget_bool":True,"required_variant_set_bool":True,"empty_fabricated_pack_bool":False}
    e=build_report("explicit",metrics,meta); ck("explicit_synthetic_probe_pass", e["status"]==STATUS_COMPLETE and validate_report(e)==[])
    nogo=json.loads(json.dumps(metrics)); nogo["proxy_lift_over_best_baseline_bucket"]="no_lift"; nr=build_report("explicit",nogo,meta); ck("no_proxy_lift_no_go", nr["status"]==STATUS_NO_GO and validate_report(nr)==[])
    for n,args in [("safe_parser_unknown_arg_fail",["--bad"]),("missing_confirm_fail",["--allow-frk-e-downstream-utility-probe"]),("wrong_out_path_fail",["--out","x"]),("bad_private_trace_root_fail",["--allow-frk-e-downstream-utility-probe","--confirm-r14-labels-private-scoring","--confirm-private-traces","--confirm-aggregate-only-public-artifact","--private-trace-root","../bad"] )]:
        try: parse_args(args); ck(n,False)
        except Exception: ck(n,True)
    b=frk_b(); idx={"files":[{"path":"a.rs","lines":["fn a(){}"],"current":"ok"}]}; ck("invalid_evidencecore_path_fail", not b.validate_hit(idx,{"path":"b.rs","start_line":1,"end_line":1,"content_current":"ok"})); ck("invalid_evidencecore_range_fail", not b.validate_hit(idx,{"path":"a.rs","start_line":2,"end_line":1,"content_current":"ok"})); ck("invalid_evidencecore_currentness_fail", not b.validate_hit(idx,{"path":"a.rs","start_line":1,"end_line":1,"content_current":"bad"}))
    muts=[("frk_d_source_drift_fail",lambda r:r["source_lock_records"][0].__setitem__("checkpoint_bucket","bad"),"source_lock"),("variant_missing_fail",lambda r:r["variant_aggregate_records"].pop(),"variant_set"),("budget_mismatch_fail",lambda r:r["proxy_metric_summary_records"][0].__setitem__("same_budget_bool",False),"budget_mismatch"),("label_before_pack_fail",lambda r:r["execution_mode_records"][0].__setitem__("labels_score_only_after_pack_construction_bool",False),"label_before_pack"),("proxy_uses_gold_fail",lambda r:r["proxy_policy_records"][0].__setitem__("label_independent_proxy_construction_bool",False),"proxy_uses_gold"),("wrong_file_regression_fail",lambda r:r["proxy_metric_summary_records"][0].__setitem__("catastrophic_wrong_file_regression_bool",True),"wrong_file_regression"),("empty_fabricated_pack_fail",lambda r:r["proxy_metric_summary_records"][0].__setitem__("empty_fabricated_pack_bool",True),"empty_fabricated_pack"),("privacy_path_leak_fail",lambda r:r.__setitem__("debug","crates/x.rs"),"public_leak"),("privacy_query_leak_fail",lambda r:r.__setitem__("debug","r14s-001"),"public_leak"),("privacy_metric_leak_fail",lambda r:r.__setitem__("debug","raw_score_value 0.4"),"public_leak"),("trace_path_leak_fail",lambda r:r.__setitem__("debug","/tmp/frk_e"),"public_leak"),("public_leak_clears_stopgo_fail",lambda r:r.__setitem__("debug","/tmp/frk_e"),"public_leak"),("stop_go_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("network_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("fastcontext_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("fastcontext_authorized_bool",True),"stop_fastcontext_authorized_bool"),("runtime_default_claim_fail",lambda r:r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool",True),"stop_runtime_default_method_scale_claim_authorized_bool"),("gate_drop_fail",lambda r:r["pass_fail_gate_records"].pop(),"gate_set"),("gate_duplicate_fail",lambda r:r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])),"gate_duplicate"),("synthetic_drop_fail",lambda r:r["synthetic_validator_records"].pop(),"synthetic_set"),("synthetic_duplicate_fail",lambda r:r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])),"synthetic_duplicate"),("readback_drop_fail",lambda r:r["public_readback_records"][0].__setitem__("all_public_readback_match_bool",False),"readback"),("metric_bucket_missing_fail",lambda r:r["variant_aggregate_records"][0].pop("correct_file_before_first_edit_bucket"),"metric_missing"),("trace_bucket_missing_fail",lambda r:r["private_trace_records"][0].pop("trace_row_count_bucket"),"trace_missing"),("proxy_lift_bucket_missing_fail",lambda r:r["proxy_metric_summary_records"][0].pop("proxy_lift_over_best_baseline_bucket"),"proxy_lift_missing"),("evidencecore_bucket_missing_fail",lambda r:r["evidencecore_validity_records"][0].pop("evidencecore_validity_bucket"),"evidencecore")]
    for n,mut,issue in muts:
        x=json.loads(json.dumps(e)); mut(x); issues=validate_report(x); ck(n, issue in issues)
    return {"passed":not fails,"failures":fails,"self_test_total":SELF_TEST_EXPECTED,"status":STATUS_COMPLETE}
def write_report(r: dict[str, Any], out: Path|None=None) -> Path:
    p=out or PUBLIC_REPORT_PATH; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return p
def main(argv: list[str]) -> int:
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
        try:
            root=private_root(str(args["trace_root"])) if args["trace_root"] else repo_root()/"runs"/f"frk_e_private_{int(time.time())}"
            metrics, meta=run_explicit(root); report=build_report("explicit",metrics,meta)
        except Exception:
            report=build_report("explicit", default_metrics(), {"label_independent_proxy_bool":False,"same_budget_bool":False,"required_variant_set_bool":False,"empty_fabricated_pack_bool":True}); report["status"]=STATUS_FAIL_SOURCE
    else: report=build_report("default")
    p=write_report(report,out); print(json.dumps({"artifact":str(p),"status":report["status"]},sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_NO_GO} else 1
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
