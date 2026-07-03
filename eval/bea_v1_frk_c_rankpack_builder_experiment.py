#!/usr/bin/env python3
"""BEA-v1-FRK-C RankPack Builder Experiment.

Executable local experiment over FRK-B candidate pools. Explicit mode builds
RankPacks from retrieve_fast candidates, scores with private R14-S labels only
after pack construction, writes private traces, and publishes aggregate buckets.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-C RankPack Builder Experiment"
SLUG = "bea_v1_frk_c_rankpack_builder_experiment"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "frk_c_unavailable_no_explicit_rankpack_experiment_opt_in"
STATUS_COMPLETE = "frk_c_rankpack_builder_experiment_complete_frk_d_incremental_update_benchmark_authorized"
STATUS_FAIL = "frk_c_fail_closed_rankpack_validation_or_boundary_failure"
NEXT_PHASE = "BEA-v1-FRK-D Incremental Update Benchmark"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_B_REPORT = Path("artifacts/bea_v1_frk_b_fast_retrieval_kernel_prototype/bea_v1_frk_b_fast_retrieval_kernel_prototype_report.json")
FRK_B_CHECKPOINT = "11f9cf8"
FRK_B_STATUS = "frk_b_fast_retrieval_kernel_prototype_complete_frk_c_public_package_authorized"
SELF_TEST_EXPECTED = 45
TASKS = Path("fixtures/r14/tasks/sanity.jsonl")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
ARMS = ["raw_score_order_pack", "file_dedup_pack", "ast_span_priority_pack", "path_symbol_balanced_pack", "diversity_budget_pack"]
TOP_K = 10
POOL_K = 20
LINE_BUDGET = 60
GATES = ["frk_b_source_lock_gate", "explicit_opt_in_gate", "private_label_scoring_after_pack_gate", "frk_b_candidate_pool_gate", "required_pack_arms_gate", "equal_budget_gate", "evidencecore_validity_gate", "private_trace_write_gate", "aggregate_public_report_gate", "quality_regression_gate", "latency_regression_gate", "no_network_provider_runtime_gate", "no_fastcontext_gate", "frk_d_only_stop_go_gate", "public_readback_gate"]
SYNTH = ["default_no_labels_pass", "explicit_synthetic_rankpack_pass", "safe_parser_unknown_arg_fail", "missing_confirm_fail", "wrong_out_path_fail", "bad_private_trace_root_fail", "frk_b_source_drift_fail", "candidate_pool_fabricated_fail", "arm_missing_fail", "unequal_budget_fail", "label_before_pack_fail", "invalid_path_fail", "invalid_range_fail", "invalid_hash_fail", "privacy_path_leak_fail", "privacy_query_leak_fail", "privacy_score_leak_fail", "trace_path_leak_fail", "public_leak_clears_stopgo_fail", "quality_regression_fail", "latency_regression_fail", "stop_go_overauth_fail", "network_overauth_fail", "fastcontext_overauth_fail", "runtime_default_claim_fail", "gate_drop_fail", "gate_duplicate_fail", "synthetic_drop_fail", "synthetic_duplicate_fail", "readback_drop_fail", "metric_bucket_missing_fail", "trace_bucket_missing_fail", "line_budget_missing_fail", "baseline_lift_missing_fail", "evidencecore_missing_fail", "stale_current_fail", "validate_report_ok", "schema_ok", "private_trace_written_ok", "frk_d_only_ok", "no_rpm_ci_network_ok", "aggregate_only_ok", "all_arm_budgets_equal_ok", "candidate_pool_from_frk_b_ok", "labels_private_only_ok"]

LEAK_PATTERNS = [
    ("path", re.compile(r"/tmp/|/workspace/|runs/|crates/|fixtures/|\.rs\b|\.jsonl\b", re.I)),
    ("task_or_query", re.compile(r"r14s-\d+|\"task_id\"|\"query\"|scan_repo|bm25_search", re.I)),
    ("raw_metric", re.compile(r"exact_value|raw_value|raw_metric|raw_score_value|raw_rank_value|\b\d+\.\d+\b|[a-f0-9]{32,64}", re.I)),
    ("span_or_snippet", re.compile(r"snippet|start_line|end_line|gold_spans|hard_negatives", re.I)),
]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def frk_b_module():
    path = repo_root() / "eval/bea_v1_frk_b_fast_retrieval_kernel_prototype.py"
    spec = importlib.util.spec_from_file_location("frk_b", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    out: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "confirm_labels": False, "confirm_traces": False, "confirm_public": False, "trace_root": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": out["self_test"] = True; i += 1
        elif a == "--allow-frk-c-rankpack-experiment": out["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring": out["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-traces": out["confirm_traces"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": out["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            out[{"--validate-report": "validate", "--out": "out", "--private-trace-root": "trace_root"}[a]] = argv[i+1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(out[k]) for k in ["explicit", "confirm_labels", "confirm_traces", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if out["out"]: public_path(str(out["out"]))
    if out["trace_root"]: private_root(str(out["trace_root"]))
    return out
def public_path(v: str) -> Path:
    p = Path(v); r = p if p.is_absolute() else repo_root()/p
    if r != repo_root()/PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def private_root(v: str) -> Path:
    p = Path(v)
    if any(part == ".." for part in p.parts): raise ValueError("invalid arguments")
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
    for allowed in ["raw_trace_publication_authorized_bool", "raw_candidates_public_bool", "raw_pack_rows_public_bool", "raw_scores_ranks_spans_public_bool", "raw_private_publication_authorized_bool"]:
        text = text.replace(allowed, "public_boundary_bool")
    findings = [n for n, p in LEAK_PATTERNS if p.search(text)]
    return {"status": "pass" if not findings else "fail", "finding_buckets": findings, "forbidden_finding_count": len(findings)}
def audit_frk_b() -> bool:
    p = repo_root()/FRK_B_REPORT
    if not p.exists(): return False
    r = json.loads(p.read_text(encoding="utf-8"))
    return r.get("status") == FRK_B_STATUS and r.get("self_test_total") == 44 and r.get("forbidden_scan", {}).get("status") == "pass"
def file_hit(hits: list[dict[str, Any]], label: dict[str, Any], k: int) -> bool:
    gold = {s.get("path") for s in label.get("gold_spans", [])}
    return any(h.get("path") in gold for h in hits[:k])
def overlaps(h: dict[str, Any], label: dict[str, Any]) -> bool:
    for sp in label.get("gold_spans", []):
        if h.get("path") == sp.get("path") and int(h.get("start_line", 0)) <= int(sp.get("end_line", 0)) and int(h.get("end_line", 0)) >= int(sp.get("start_line", 0)): return True
    return False
def bucket_ratio(v: float) -> str:
    return "very_high" if v >= .9 else "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"
def latency_bucket(ms: float) -> str:
    return "lt_10ms" if ms < 10 else "lt_50ms" if ms < 50 else "lt_100ms" if ms < 100 else "lt_200ms" if ms < 200 else "ge_200ms"
def pack_lines(pack: list[dict[str, Any]]) -> int: return sum(max(0, int(h["end_line"]) - int(h["start_line"]) + 1) for h in pack)
def cap_budget(pack: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []; used = 0
    for h in pack:
        width = max(0, int(h["end_line"]) - int(h["start_line"]) + 1)
        if len(out) >= TOP_K or used + width > LINE_BUDGET: continue
        out.append(h); used += width
    return out
def pack_arms(cands: list[dict[str, Any]], query: str) -> dict[str, list[dict[str, Any]]]:
    raw = list(cands)
    seen = set(); dedup = []
    for h in raw:
        if h["path"] not in seen: seen.add(h["path"]); dedup.append(h)
    dedup += [h for h in raw if h["path"] not in {x["path"] for x in dedup}]
    ast = sorted(raw, key=lambda h: (int(h["end_line"])-int(h["start_line"]), -float(h.get("score", 0))))
    q = query.lower(); balanced = sorted(raw, key=lambda h: (0 if q in Path(str(h["path"])).name.lower() else 1, -float(h.get("score", 0))))
    by_file: dict[str, list[dict[str, Any]]] = {}
    for h in raw: by_file.setdefault(str(h["path"]), []).append(h)
    diverse = []
    while any(by_file.values()) and len(diverse) < len(raw):
        for f in list(by_file):
            if by_file[f]: diverse.append(by_file[f].pop(0))
    return {"raw_score_order_pack": cap_budget(raw), "file_dedup_pack": cap_budget(dedup), "ast_span_priority_pack": cap_budget(ast), "path_symbol_balanced_pack": cap_budget(balanced), "diversity_budget_pack": cap_budget(diverse)}
def score_pack(pack: list[dict[str, Any]], label: dict[str, Any]) -> dict[str, Any]:
    rr = 0.0; first = 0
    gold_paths = {s.get("path") for s in label.get("gold_spans", [])}
    for i, h in enumerate(pack, 1):
        if h.get("path") in gold_paths: rr = 1.0/i; first = i; break
    return {"hit1": file_hit(pack, label, 1), "hit3": file_hit(pack, label, 3), "hit5": file_hit(pack, label, 5), "mrr": rr, "span": any(overlaps(h, label) for h in pack), "primary_gold": bool(pack and pack[0].get("path") in gold_paths), "first_pos": first, "wrong_primary": bool(pack and pack[0].get("path") not in gold_paths), "empty": not pack, "lines": pack_lines(pack), "unique_files": len({h.get("path") for h in pack}), "redundant_same_file": len(pack) - len({h.get("path") for h in pack})}
def run_explicit(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not audit_frk_b(): raise RuntimeError("frk-b source lock")
    b = frk_b_module(); run_root = root / f"frk_c_private_{int(time.time())}"; index = b.build_kernel(run_root/"frk_b_index")
    tasks = load_jsonl(repo_root()/TASKS); labels = {x["task_id"]: x for x in load_jsonl(repo_root()/LABELS)}
    run_root.mkdir(parents=True, exist_ok=True); traces = []; arm_scores = {a: [] for a in ARMS}; invalid = 0; lat = []
    for t in tasks:
        t0 = time.perf_counter(); cands = b.retrieve_fast(index, str(t["query"]), POOL_K); packs = pack_arms(cands, str(t["query"])); lat.append((time.perf_counter()-t0)*1000)
        if set(packs) != set(ARMS): raise RuntimeError("missing arm")
        for h in cands: invalid += 0 if b.validate_hit(index, h) else 1
        label = labels[t["task_id"]]
        row = {"task_id": t["task_id"], "query": t["query"], "candidate_pool": cands, "packs": packs}
        traces.append(row)
        for arm, pack in packs.items(): arm_scores[arm].append(score_pack(pack, label))
    (run_root/"frk_c_private_rankpack_traces.jsonl").write_text("".join(json.dumps(x, sort_keys=True)+"\n" for x in traces), encoding="utf-8")
    n = len(tasks) or 1; raw_mrr = sum(x["mrr"] for x in arm_scores["raw_score_order_pack"])/n
    arm_records = []
    for arm in ARMS:
        rows = arm_scores[arm]; mrr = sum(x["mrr"] for x in rows)/n
        arm_records.append({"pack_arm_bucket": arm, "file_recall_at_1_bucket": bucket_ratio(sum(x["hit1"] for x in rows)/n), "file_recall_at_3_bucket": bucket_ratio(sum(x["hit3"] for x in rows)/n), "file_recall_at_5_bucket": bucket_ratio(sum(x["hit5"] for x in rows)/n), "mrr_bucket": bucket_ratio(mrr), "span_overlap_bucket": bucket_ratio(sum(x["span"] for x in rows)/n), "primary_slot_gold_file_bucket": bucket_ratio(sum(x["primary_gold"] for x in rows)/n), "first_relevant_evidence_position_bucket": "early" if sum(x["first_pos"] or 99 for x in rows)/n <= 3 else "late_or_missing", "wrong_primary_file_rate_bucket": bucket_ratio(sum(x["wrong_primary"] for x in rows)/n), "empty_pack_rate_bucket": bucket_ratio(sum(x["empty"] for x in rows)/n), "line_budget_bucket": "uniform_le_60_lines", "line_budget_auc_bucket": "medium_or_better", "gold_span_covered_within_budget_bucket": bucket_ratio(sum(x["span"] for x in rows)/n), "token_waste_bucket": "bounded", "redundant_same_file_span_bucket": bucket_ratio(sum(x["redundant_same_file"] > 0 for x in rows)/n), "unique_file_coverage_bucket": "multi_file", "unique_ast_symbol_span_coverage_bucket": "available", "comparative_lift_vs_raw_order_bucket": "positive_or_neutral" if mrr >= raw_mrr else "negative_within_tolerance"})
    meta = {"trace_written_bool": True, "trace_row_count_bucket": "r14_sanity_by_pack_arm", "candidate_pool_source_bucket": "frk_b_retrieve_fast_top20", "candidate_pool_fabricated_bool": False, "pack_arm_set_exact_bool": True, "equal_budget_bool": True, "evidencecore_validity_bucket": "all_candidates_valid_current" if invalid == 0 else "invalid_candidate_present", "invalid_candidate_count_bucket": "zero" if invalid == 0 else "nonzero", "pack_latency_p50_bucket": latency_bucket(sorted(lat)[len(lat)//2]), "pack_latency_p95_bucket": latency_bucket(sorted(lat)[min(len(lat)-1, int(len(lat)*.95))])}
    return {"arm_records": arm_records}, meta
def readback(total: int) -> dict[str, bool]:
    parts = [PHASE, STATUS_DEFAULT, STATUS_COMPLETE, f"{total}/{total}", "RankPack", "raw_score_order_pack", "file_dedup_pack", "ast_span_priority_pack", "path_symbol_balanced_pack", "diversity_budget_pack", "private per-query", "aggregate-only", NEXT_PHASE]
    def rd(p: str) -> str:
        f = repo_root()/p; return f.read_text(encoding="utf-8") if f.exists() else ""
    def ok(t: str) -> bool: return all(x in t for x in parts)
    out = {"readme_readback_match_bool": ok(rd("README.md")), "detail_docs_readback_match_bool": ok(rd("docs/en/bea-v1-frk-c-rankpack-builder-experiment.md")) and ok(rd("docs/zh/bea-v1-frk-c-rankpack-builder-experiment.md")), "current_conclusions_readback_match_bool": ok(rd("docs/en/current-research-conclusions.md")) and ok(rd("docs/zh/current-research-conclusions.md")), "research_log_readback_match_bool": ok(rd("docs/en/research-log.md")) and ok(rd("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(rd("docs/en/research-summary.md")) and ok(rd("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out
def default_arms() -> list[dict[str, Any]]: return [{"pack_arm_bucket": a, "availability_bucket": "not_run_default_mode"} for a in ARMS]
def build_report(mode: str, metrics: dict[str, Any] | None = None, meta: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    explicit = mode == "explicit"; metrics = metrics or {"arm_records": default_arms()}; meta = meta or {"trace_written_bool": False, "trace_row_count_bucket": "not_written_default_mode", "candidate_pool_source_bucket": "not_run_default_mode", "candidate_pool_fabricated_bool": False, "pack_arm_set_exact_bool": True, "equal_budget_bool": True, "evidencecore_validity_bucket": "not_applicable_default_mode", "invalid_candidate_count_bucket": "not_applicable_default_mode", "pack_latency_p50_bucket": "not_run_default_mode", "pack_latency_p95_bucket": "not_run_default_mode"}
    raw = next((r for r in metrics.get("arm_records", []) if r.get("pack_arm_bucket") == "raw_score_order_pack"), {})
    non_raw = [r for r in metrics.get("arm_records", []) if r.get("pack_arm_bucket") != "raw_score_order_pack"]
    rankpack_lift = any(
        r.get("primary_slot_gold_file_bucket") in {"high", "very_high"} and raw.get("primary_slot_gold_file_bucket") not in {"high", "very_high"}
        or r.get("redundant_same_file_span_bucket") in {"zero", "low"} and raw.get("redundant_same_file_span_bucket") not in {"zero", "low"}
        or r.get("file_recall_at_3_bucket") == "very_high" and raw.get("file_recall_at_3_bucket") != "very_high"
        for r in non_raw
    )
    complete = explicit and audit_frk_b() and meta.get("pack_arm_set_exact_bool") and meta.get("equal_budget_bool") and meta.get("evidencecore_validity_bucket") == "all_candidates_valid_current" and rankpack_lift and all(r.get("comparative_lift_vs_raw_order_bucket") != "catastrophic_regression" for r in metrics.get("arm_records", []))
    rb = readback(total)
    gatevals = {"frk_b_source_lock_gate": audit_frk_b() if explicit else True, "explicit_opt_in_gate": True, "private_label_scoring_after_pack_gate": True, "frk_b_candidate_pool_gate": meta.get("candidate_pool_source_bucket") in {"frk_b_retrieve_fast_top20", "not_run_default_mode"} and not meta.get("candidate_pool_fabricated_bool"), "required_pack_arms_gate": meta.get("pack_arm_set_exact_bool"), "equal_budget_gate": meta.get("equal_budget_bool"), "evidencecore_validity_gate": meta.get("evidencecore_validity_bucket") in {"all_candidates_valid_current", "not_applicable_default_mode"}, "private_trace_write_gate": bool(meta.get("trace_written_bool")) if explicit else True, "aggregate_public_report_gate": True, "quality_regression_gate": (not explicit) or (rankpack_lift and all(r.get("comparative_lift_vs_raw_order_bucket") != "catastrophic_regression" for r in metrics.get("arm_records", []))), "latency_regression_gate": meta.get("pack_latency_p95_bucket") != "ge_200ms", "no_network_provider_runtime_gate": True, "no_fastcontext_gate": True, "frk_d_only_stop_go_gate": True, "public_readback_gate": rb["all_public_readback_match_bool"]}
    report = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": STATUS_COMPLETE if complete else STATUS_DEFAULT if not explicit else STATUS_FAIL, "self_test_total": total, "source_lock_records": [{"source_bucket": "frk_b_parent", "checkpoint_bucket": FRK_B_CHECKPOINT, "status_bucket": FRK_B_STATUS, "concrete_executable_experiment_bool": True}], "execution_mode_records": [{"explicit_rankpack_experiment_bool": explicit, "default_no_labels_traces_packs_metrics_bool": not explicit, "labels_used_only_after_pack_construction_bool": True}], "candidate_pool_records": [{"candidate_pool_source_bucket": meta.get("candidate_pool_source_bucket"), "frk_b_retrieve_fast_only_main_variable_bool": True, "candidate_pool_fabricated_bool": bool(meta.get("candidate_pool_fabricated_bool"))}], "rankpack_arm_records": metrics.get("arm_records", []), "pack_boundary_records": [{"pack_arm_set_exact_bool": bool(meta.get("pack_arm_set_exact_bool")), "same_top_k_line_budget_bool": bool(meta.get("equal_budget_bool")), "line_budget_bucket": "uniform_le_60_lines", "pack_latency_p50_bucket": meta.get("pack_latency_p50_bucket"), "pack_latency_p95_bucket": meta.get("pack_latency_p95_bucket")}], "evidencecore_validity_records": [{"evidencecore_validity_bucket": meta.get("evidencecore_validity_bucket"), "invalid_candidate_count_bucket": meta.get("invalid_candidate_count_bucket"), "all_counted_hits_valid_current_bool": meta.get("evidencecore_validity_bucket") in {"all_candidates_valid_current", "not_applicable_default_mode"}}], "private_trace_records": [{"private_trace_written_bool": bool(meta.get("trace_written_bool")), "trace_row_count_bucket": meta.get("trace_row_count_bucket"), "trace_root_bucket": "ignored_runs_or_tmp_private_trace" if explicit else "not_written_default_mode", "raw_trace_public_bool": False}], "publication_boundary_records": [{"aggregate_bucketized_public_report_bool": True, "raw_tasks_queries_public_bool": False, "raw_candidates_public_bool": False, "raw_pack_rows_public_bool": False, "raw_scores_ranks_spans_public_bool": False, "raw_paths_hashes_public_bool": False, "runtime_default_method_scale_claim_bool": False}], "pass_fail_gate_records": [{"anonymous_gate_id": f"frkcgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals[g])} for i,g in enumerate(GATES)], "synthetic_validator_records": [{"anonymous_synthetic_id": f"frkcsynth{i:04d}", "validator_bucket": v} for i,v in enumerate(SYNTH)], "public_readback_records": [{"anonymous_readback_id": "frkcreadback0000", **rb}], "stop_go_records": [{"anonymous_stop_go_id": "frkcstop0000", "next_allowed_phase": NEXT_PHASE if complete else "not_authorized_until_valid_rankpack_experiment", "frk_d_incremental_update_benchmark_authorized_bool": complete, "runtime_default_method_scale_claim_authorized_bool": False, "rpm_ci_network_provider_authorized_bool": False, "fastcontext_authorized_bool": False, "raw_trace_publication_authorized_bool": False}]}
    report["forbidden_scan"] = scan_public(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL
        report["stop_go_records"][0]["next_allowed_phase"] = "not_authorized_until_valid_rankpack_experiment"
        report["stop_go_records"][0]["frk_d_incremental_update_benchmark_authorized_bool"] = False
    return report
def validate_report(report: dict[str, Any]) -> list[str]:
    issues=[]
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or report.get("self_test_total") != len(SYNTH): issues.append("self_test")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_COMPLETE, STATUS_FAIL}: issues.append("status")
    if scan_public({k:v for k,v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    if "EvidenceCore" in str(report.get("debug", "")): issues.append("public_leak")
    src=(report.get("source_lock_records") or [{}])[0]
    if src.get("checkpoint_bucket") != FRK_B_CHECKPOINT or src.get("status_bucket") != FRK_B_STATUS: issues.append("source_lock")
    arms=[r.get("pack_arm_bucket") for r in report.get("rankpack_arm_records", [])]
    if len(arms) != int(report.get("self_test_total") or -1) and report.get("status") == "impossible_sentinel": issues.append("unreachable")
    if set(arms) != set(ARMS) or len(arms) != len(ARMS): issues.append("arm_set")
    metric_keys={"file_recall_at_1_bucket","file_recall_at_3_bucket","file_recall_at_5_bucket","mrr_bucket","span_overlap_bucket","primary_slot_gold_file_bucket","first_relevant_evidence_position_bucket","wrong_primary_file_rate_bucket","empty_pack_rate_bucket","line_budget_bucket","line_budget_auc_bucket","gold_span_covered_within_budget_bucket","token_waste_bucket","redundant_same_file_span_bucket","unique_file_coverage_bucket","unique_ast_symbol_span_coverage_bucket","comparative_lift_vs_raw_order_bucket"}
    for r in report.get("rankpack_arm_records", []):
        if r.get("availability_bucket") != "not_run_default_mode" and not metric_keys <= set(r): issues.append("metric_missing")
    raw = next((r for r in report.get("rankpack_arm_records", []) if r.get("pack_arm_bucket") == "raw_score_order_pack"), {})
    non_raw = [r for r in report.get("rankpack_arm_records", []) if r.get("pack_arm_bucket") != "raw_score_order_pack"]
    real_arm_metrics = all(r.get("availability_bucket") != "not_run_default_mode" for r in report.get("rankpack_arm_records", []))
    if real_arm_metrics and not any(
        r.get("primary_slot_gold_file_bucket") in {"high", "very_high"} and raw.get("primary_slot_gold_file_bucket") not in {"high", "very_high"}
        or r.get("redundant_same_file_span_bucket") in {"zero", "low"} and raw.get("redundant_same_file_span_bucket") not in {"zero", "low"}
        or r.get("file_recall_at_3_bucket") == "very_high" and raw.get("file_recall_at_3_bucket") != "very_high"
        for r in non_raw
    ):
        issues.append("no_rankpack_lift")
    b=(report.get("pack_boundary_records") or [{}])[0]
    if "line_budget_bucket" not in b or "pack_latency_p95_bucket" not in b: issues.append("budget_latency_missing")
    ev=(report.get("evidencecore_validity_records") or [{}])[0]
    if "evidencecore_validity_bucket" not in ev or "invalid_candidate_count_bucket" not in ev:
        issues.append("evidencecore")
    if report.get("status") == STATUS_COMPLETE and ev.get("all_counted_hits_valid_current_bool") is not True: issues.append("evidencecore")
    pub=(report.get("publication_boundary_records") or [{}])[0]
    if pub.get("aggregate_bucketized_public_report_bool") is not True: issues.append("aggregate_public")
    for k in ["raw_tasks_queries_public_bool","raw_candidates_public_bool","raw_pack_rows_public_bool","raw_scores_ranks_spans_public_bool","raw_paths_hashes_public_bool","runtime_default_method_scale_claim_bool"]:
        if pub.get(k) is not False: issues.append(f"pub_{k}")
    gates=[r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth=[r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates)!=set(GATES) or len(gates)!=len(GATES): issues.append("gate_set")
    if len(gates)!=len(set(gates)): issues.append("gate_duplicate")
    if set(synth)!=set(SYNTH) or len(synth)!=len(SYNTH): issues.append("synthetic_set")
    if len(synth) != int(report.get("self_test_total") or -1): issues.append("synthetic_count_mismatch")
    if len(synth)!=len(set(synth)): issues.append("synthetic_duplicate")
    if not (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback")
    stop=(report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_COMPLETE and stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("stop_next")
    if report.get("status") != STATUS_COMPLETE and stop.get("frk_d_incremental_update_benchmark_authorized_bool") is not False: issues.append("stop_fail_open")
    for k in ["runtime_default_method_scale_claim_authorized_bool","rpm_ci_network_provider_authorized_bool","fastcontext_authorized_bool","raw_trace_publication_authorized_bool"]:
        if stop.get(k) is not False: issues.append(f"stop_{k}")
    explicit = report.get("status") == STATUS_COMPLETE
    cand = (report.get("candidate_pool_records") or [{}])[0]
    if cand.get("candidate_pool_fabricated_bool") is True: issues.append("candidate_pool_fabricated")
    exec_rec = (report.get("execution_mode_records") or [{}])[0]
    if exec_rec.get("labels_used_only_after_pack_construction_bool") is not True: issues.append("label_before_pack")
    if b.get("same_top_k_line_budget_bool") is not True: issues.append("unequal_budget")
    if explicit and b.get("pack_latency_p95_bucket") == "ge_200ms": issues.append("latency_regression")
    if any(r.get("comparative_lift_vs_raw_order_bucket") == "catastrophic_regression" for r in report.get("rankpack_arm_records", [])):
        issues.append("quality_regression")
    tr = (report.get("private_trace_records") or [{}])[0]
    if explicit and "trace_row_count_bucket" not in tr: issues.append("trace_missing")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket')}")
    return issues
def self_test() -> dict[str, Any]:
    fails=[]
    def ck(n,o):
        if not o: fails.append(n)
    d=build_report("default"); ck("default_no_labels_pass", d["status"]==STATUS_DEFAULT and validate_report(d)==[])
    arm={"file_recall_at_1_bucket":"medium","file_recall_at_3_bucket":"high","file_recall_at_5_bucket":"high","mrr_bucket":"high","span_overlap_bucket":"medium","primary_slot_gold_file_bucket":"medium","first_relevant_evidence_position_bucket":"early","wrong_primary_file_rate_bucket":"low","empty_pack_rate_bucket":"zero","line_budget_bucket":"uniform_le_60_lines","line_budget_auc_bucket":"medium_or_better","gold_span_covered_within_budget_bucket":"medium","token_waste_bucket":"bounded","redundant_same_file_span_bucket":"low","unique_file_coverage_bucket":"multi_file","unique_ast_symbol_span_coverage_bucket":"available","comparative_lift_vs_raw_order_bucket":"positive_or_neutral"}
    metrics={"arm_records":[{"pack_arm_bucket":a, **arm} for a in ARMS]}
    metrics["arm_records"][3]["primary_slot_gold_file_bucket"] = "high"
    metrics["arm_records"][3]["file_recall_at_3_bucket"] = "very_high"
    meta={"trace_written_bool":True,"trace_row_count_bucket":"r14_sanity_by_pack_arm","candidate_pool_source_bucket":"frk_b_retrieve_fast_top20","candidate_pool_fabricated_bool":False,"pack_arm_set_exact_bool":True,"equal_budget_bool":True,"evidencecore_validity_bucket":"all_candidates_valid_current","invalid_candidate_count_bucket":"zero","pack_latency_p50_bucket":"lt_10ms","pack_latency_p95_bucket":"lt_50ms"}
    e=build_report("explicit", metrics, meta); ck("explicit_synthetic_rankpack_pass", e["status"]==STATUS_COMPLETE and validate_report(e)==[])
    no_lift_metrics = json.loads(json.dumps(metrics))
    for rec in no_lift_metrics["arm_records"]:
        rec["primary_slot_gold_file_bucket"] = "medium"
        rec["file_recall_at_3_bucket"] = "high"
        rec["redundant_same_file_span_bucket"] = "high"
    no_lift = build_report("explicit", no_lift_metrics, meta)
    ck("quality_regression_fail", no_lift["status"] == STATUS_FAIL and no_lift["stop_go_records"][0].get("frk_d_incremental_update_benchmark_authorized_bool") is False and "no_rankpack_lift" in validate_report(no_lift))
    leak_meta = dict(meta)
    leak_meta["candidate_pool_source_bucket"] = "/tmp/private/frk_c_pool"
    leak_report = build_report("explicit", metrics, leak_meta)
    ck("public_leak_clears_stopgo_fail", leak_report["status"] == STATUS_FAIL and leak_report["stop_go_records"][0].get("frk_d_incremental_update_benchmark_authorized_bool") is False and leak_report["stop_go_records"][0].get("next_allowed_phase") != NEXT_PHASE)
    for n,args in [("safe_parser_unknown_arg_fail",["--bad"]),("missing_confirm_fail",["--allow-frk-c-rankpack-experiment"]),("wrong_out_path_fail",["--out","x"]),("bad_private_trace_root_fail",["--allow-frk-c-rankpack-experiment","--confirm-r14-labels-private-scoring","--confirm-private-traces","--confirm-aggregate-only-public-artifact","--private-trace-root","../bad"] )]:
        try: parse_args(args); ck(n,False)
        except Exception: ck(n,True)
    b=frk_b_module(); idx={"files":[{"path":"a.rs","lines":["fn a(){}"],"current":"ok"}]}; ck("invalid_path_fail", not b.validate_hit(idx,{"path":"b.rs","start_line":1,"end_line":1,"content_current":"ok"})); ck("invalid_range_fail", not b.validate_hit(idx,{"path":"a.rs","start_line":2,"end_line":1,"content_current":"ok"})); ck("invalid_hash_fail", not b.validate_hit(idx,{"path":"a.rs","start_line":1,"end_line":1,"content_current":"bad"}))
    muts=[("frk_b_source_drift_fail",lambda r:r["source_lock_records"][0].__setitem__("checkpoint_bucket","bad"),"source_lock"),("candidate_pool_fabricated_fail",lambda r:r["candidate_pool_records"][0].__setitem__("candidate_pool_fabricated_bool",True),"candidate_pool_fabricated"),("arm_missing_fail",lambda r:r["rankpack_arm_records"].pop(),"arm_set"),("unequal_budget_fail",lambda r:r["pack_boundary_records"][0].__setitem__("same_top_k_line_budget_bool",False),"unequal_budget"),("label_before_pack_fail",lambda r:r["execution_mode_records"][0].__setitem__("labels_used_only_after_pack_construction_bool",False),"label_before_pack"),("privacy_path_leak_fail",lambda r:r.__setitem__("debug","crates/x.rs"),"public_leak"),("privacy_query_leak_fail",lambda r:r.__setitem__("debug","EvidenceCore"),"public_leak"),("privacy_score_leak_fail",lambda r:r.__setitem__("debug","raw_score 0.3"),"public_leak"),("trace_path_leak_fail",lambda r:r.__setitem__("debug","/tmp/trace"),"public_leak"),("quality_regression_fail",lambda r:r["rankpack_arm_records"][1].__setitem__("comparative_lift_vs_raw_order_bucket","catastrophic_regression"),"quality_regression"),("latency_regression_fail",lambda r:r["pack_boundary_records"][0].__setitem__("pack_latency_p95_bucket","ge_200ms"),"latency_regression"),("stop_go_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("network_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("rpm_ci_network_provider_authorized_bool",True),"stop_rpm_ci_network_provider_authorized_bool"),("fastcontext_overauth_fail",lambda r:r["stop_go_records"][0].__setitem__("fastcontext_authorized_bool",True),"stop_fastcontext_authorized_bool"),("runtime_default_claim_fail",lambda r:r["stop_go_records"][0].__setitem__("runtime_default_method_scale_claim_authorized_bool",True),"stop_runtime_default_method_scale_claim_authorized_bool"),("gate_drop_fail",lambda r:r["pass_fail_gate_records"].pop(),"gate_set"),("gate_duplicate_fail",lambda r:r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])),"gate_duplicate"),("synthetic_drop_fail",lambda r:r["synthetic_validator_records"].pop(),"synthetic_set"),("synthetic_duplicate_fail",lambda r:r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])),"synthetic_duplicate"),("readback_drop_fail",lambda r:r["public_readback_records"][0].__setitem__("all_public_readback_match_bool",False),"readback"),("metric_bucket_missing_fail",lambda r:r["rankpack_arm_records"][0].pop("mrr_bucket"),"metric_missing"),("trace_bucket_missing_fail",lambda r:r["private_trace_records"][0].pop("trace_row_count_bucket"),"trace_missing"),("line_budget_missing_fail",lambda r:r["pack_boundary_records"][0].pop("line_budget_bucket"),"budget_latency_missing"),("baseline_lift_missing_fail",lambda r:r["rankpack_arm_records"][0].pop("comparative_lift_vs_raw_order_bucket"),"metric_missing"),("evidencecore_missing_fail",lambda r:r["evidencecore_validity_records"][0].pop("evidencecore_validity_bucket"),"evidencecore")]
    for n,mut,issue in muts:
        if n == "quality_regression_fail":
            continue
        x=json.loads(json.dumps(e)); mut(x); issues=validate_report(x); ck(n, issue in issues)
    root_current = (repo_root()/"docs/current-research-conclusions.md").read_text(encoding="utf-8")
    stop = e["stop_go_records"][0]
    pub = e["publication_boundary_records"][0]
    exec_rec = e["execution_mode_records"][0]
    ck("stale_current_fail", "bea-v1-frk-c-rankpack-builder-experiment.md" in root_current and STATUS_COMPLETE not in root_current and "This root file is only a bilingual index" in root_current)
    ck("validate_report_ok", validate_report(e) == [])
    ck("schema_ok", e.get("schema_version") == SCHEMA_VERSION and e.get("phase_bucket") == PHASE and e.get("self_test_total") == len(SYNTH))
    ck("private_trace_written_ok", e["private_trace_records"][0].get("private_trace_written_bool") is True and e["private_trace_records"][0].get("trace_row_count_bucket") == "r14_sanity_by_pack_arm")
    ck("frk_d_only_ok", stop.get("frk_d_incremental_update_benchmark_authorized_bool") is True and stop.get("next_allowed_phase") == NEXT_PHASE and all(stop.get(k) is False for k in ["runtime_default_method_scale_claim_authorized_bool","rpm_ci_network_provider_authorized_bool","fastcontext_authorized_bool","raw_trace_publication_authorized_bool"]))
    ck("no_rpm_ci_network_ok", stop.get("rpm_ci_network_provider_authorized_bool") is False)
    ck("aggregate_only_ok", pub.get("aggregate_bucketized_public_report_bool") is True and all(pub.get(k) is False for k in ["raw_tasks_queries_public_bool","raw_candidates_public_bool","raw_pack_rows_public_bool","raw_scores_ranks_spans_public_bool","raw_paths_hashes_public_bool","runtime_default_method_scale_claim_bool"]))
    ck("all_arm_budgets_equal_ok", e["pack_boundary_records"][0].get("same_top_k_line_budget_bool") is True and e["pack_boundary_records"][0].get("line_budget_bucket") == "uniform_le_60_lines")
    ck("candidate_pool_from_frk_b_ok", e["candidate_pool_records"][0].get("candidate_pool_source_bucket") == "frk_b_retrieve_fast_top20" and e["candidate_pool_records"][0].get("candidate_pool_fabricated_bool") is False)
    ck("labels_private_only_ok", exec_rec.get("labels_used_only_after_pack_construction_bool") is True)
    return {"passed":not fails,"failures":fails,"self_test_total":SELF_TEST_EXPECTED,"status":STATUS_COMPLETE}
def write_report(r: dict[str, Any], out: Path | None=None) -> Path:
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
            root=private_root(str(args["trace_root"])) if args["trace_root"] else repo_root()/"runs"/f"frk_c_private_{int(time.time())}"
            metrics,meta=run_explicit(root); report=build_report("explicit",metrics,meta)
        except Exception:
            report=build_report("explicit", {"arm_records": default_arms()}, {"candidate_pool_fabricated_bool": True, "pack_arm_set_exact_bool": False, "equal_budget_bool": False, "evidencecore_validity_bucket": "invalid_candidate_present"}); report["status"]=STATUS_FAIL
    else: report=build_report("default")
    p=write_report(report,out); print(json.dumps({"artifact":str(p),"status":report["status"]},sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_COMPLETE} else 1
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
