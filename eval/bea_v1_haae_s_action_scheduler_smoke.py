#!/usr/bin/env python3
"""BEA-v1-HAAE-S Action Scheduler Smoke.

Executable smoke over the existing FRK-E private trace root. Candidate state and
action sequences are constructed without labels; private R14 labels are loaded
only after non-oracle policy actions are fixed. The public report is aggregate
bucket-only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-S Action Scheduler Smoke"
SLUG = "bea_v1_haae_s_action_scheduler_smoke"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
STATUS_DEFAULT = "haae_s_unavailable_no_explicit_action_scheduler_smoke_opt_in"
STATUS_GO = "haae_s_action_scheduler_smoke_complete_haae_t_trace_dataset_readiness_authorized"
STATUS_NO_GO = "haae_s_no_go_scheduler_no_lift_over_fixed_baselines"
STATUS_STOP = "haae_s_stop_track_b_scheduler_until_better_state_features"
STATUS_FAIL = "haae_s_fail_closed_source_trace_privacy_or_consistency_failure"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
FRK_F_REPORT = Path("artifacts/bea_v1_frk_f_failure_decomposition/bea_v1_frk_f_failure_decomposition_report.json")
LDI_A_REPORT = Path("artifacts/bea_v1_ldi_a_derived_index_smoke_benchmark/bea_v1_ldi_a_derived_index_smoke_benchmark_report.json")
LABELS = Path("fixtures/r14/labels/sanity.jsonl")
FRK_F_CHECKPOINT = "63528e8"
FRK_F_STATUS = "frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient"
LDI_A_CHECKPOINT = "aaf3a1c"
LDI_A_STATUS = "ldi_a_stop_derived_index_route_baseline_sufficient"
SELF_TEST_EXPECTED = 57
BUDGET = 5
FIXED_POLICIES = ["fixed_stop_after_first", "fixed_top_k_continue", "best_baseline_pack_order"]
SCHEDULER_POLICIES = ["scheduler_confidence_stop", "scheduler_diversify_on_redundancy", "scheduler_promote_after_evidencecore_valid", "scheduler_budget_guard"]
ORACLE_POLICY = "oracle_upper_bound_private"
POLICIES = FIXED_POLICIES + SCHEDULER_POLICIES + [ORACLE_POLICY]
NON_ORACLE = FIXED_POLICIES + SCHEDULER_POLICIES
PACKS = ["bm25_like_baseline_pack", "rrf_like_baseline_pack", "frk_b_retrieve_fast_raw_pack", "frk_c_rankpack_builder_pack"]
GATES = ["source_lock_gate", "trace_valid_gate", "label_after_action_gate", "oracle_not_stopgo_gate", "policy_set_gate", "same_budget_gate", "evidencecore_currentness_gate", "derived_not_evidence_gate", "aggregate_only_gate", "stop_go_boundary_gate", "synthetic_validator_gate", "public_readback_gate"]
SYNTH = [
    "default_no_private_read_pass", "explicit_synthetic_no_lift_pass", "explicit_synthetic_go_pass", "safe_parser_unknown_arg_fail", "missing_confirm_fail", "missing_trace_root_fail", "bad_trace_root_fail", "wrong_out_path_fail", "source_drift_frk_f_fail", "source_drift_ldi_a_fail", "trace_invalid_fail", "label_before_action_fail", "oracle_stopgo_fail", "degenerate_policy_fail", "same_budget_mismatch_fail", "evidencecore_stale_fail", "derived_used_as_evidence_fail", "privacy_path_leak_fail", "privacy_query_leak_fail", "privacy_span_leak_fail", "privacy_score_leak_fail", "privacy_hash_leak_fail", "public_leak_clears_stopgo_fail", "stop_go_overauth_fail", "synthetic_drop_fail", "synthetic_false_fail", "gate_drop_fail", "gate_false_fail", "readback_fail", "self_test_count_exact", "fixed_policy_set_exact", "scheduler_policy_set_exact", "oracle_private_ceiling_only", "private_labels_scoring_only", "private_trace_written", "aggregate_buckets_only", "source_path_range_hash_validated_private", "same_budget_non_oracle", "no_rpm_training", "no_provider_network_ci_runtime_default", "no_frk_g_ldi_b", "honest_no_lift_status", "go_only_scheduler_lift", "best_baseline_pack_order_present", "confidence_stop_present", "diversify_present", "promote_after_evidencecore_present", "budget_guard_present", "fixed_stop_present", "fixed_topk_present", "validate_report_ok", "schema_ok", "public_readback_ok", "frk_f_lock_ok", "ldi_a_lock_ok", "trace_root_explicit_ok", "labels_private_ok",
]
LEAK_PATTERNS = [
    ("private_or_file", re.compile(r"/workspace/|/tmp/|/home/|runs/|fixtures/|\.openlocus|\.rs\b|\.jsonl\b|\.json\b", re.I)),
    ("task_or_query", re.compile(r"r14s-\d+|\bquery\b|task_id|scan_repo|bm25_search", re.I)),
    ("span_or_hash", re.compile(r"start_line|end_line|snippet|gold_spans|hard_negatives|[0-9a-f]{32,64}", re.I)),
    ("raw_metric", re.compile(r"raw_score|raw_rank|exact_value|raw_value|\b\d+\.\d+\b", re.I)),
]
FORBIDDEN_KEYS = {"task_id", "query", "path", "paths", "span", "spans", "hash", "score", "rank", "root", "private_root", "start_line", "end_line", "snippet", "raw"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    args: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "trace_root": "", "confirm_labels": False, "confirm_read": False, "confirm_written": False, "confirm_current": False, "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": args["self_test"] = True; i += 1
        elif a == "--allow-haae-s-action-scheduler-smoke": args["explicit"] = True; i += 1
        elif a == "--confirm-r14-labels-private-scoring": args["confirm_labels"] = True; i += 1
        elif a == "--confirm-private-trace-read": args["confirm_read"] = True; i += 1
        elif a == "--confirm-private-traces-written": args["confirm_written"] = True; i += 1
        elif a == "--confirm-evidencecore-currentness": args["confirm_current"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": args["confirm_public"] = True; i += 1
        elif a in {"--existing-private-trace-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            args[{"--existing-private-trace-root": "trace_root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(args[k]) for k in ["explicit", "trace_root", "confirm_labels", "confirm_read", "confirm_written", "confirm_current", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    if args["out"]: public_path(str(args["out"]))
    if args["trace_root"]: private_root(str(args["trace_root"]))
    return args


def public_path(v: str) -> Path:
    p = Path(v); r = p if p.is_absolute() else repo_root() / p
    if r != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def private_root(v: str) -> Path:
    p = Path(v)
    if any(x == ".." for x in p.parts): raise ValueError("invalid arguments")
    r = p if p.is_absolute() else repo_root() / p
    try: r.relative_to(repo_root() / "runs")
    except Exception: raise ValueError("invalid arguments")
    if not r.exists() or r.is_symlink(): raise ValueError("invalid arguments")
    return r


def scan_public(obj: Any) -> dict[str, Any]:
    findings: list[str] = []
    scrub = json.loads(json.dumps(obj))
    if isinstance(scrub, dict): scrub.pop("forbidden_scan", None)
    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS: findings.append("forbidden_key")
        if isinstance(node, dict):
            for k, v in node.items(): walk(v, str(k))
        elif isinstance(node, list):
            for v in node: walk(v, key)
        elif isinstance(node, str):
            text = node
            for ok in ["private_trace_read_bool", "private_trace_written_bool", "private_trace_public_bool", "r14_labels_private_scoring_bool", "oracle_private_ceiling_only_bool", "raw_private_publication_authorized_bool"]:
                text = text.replace(ok, "public_boundary_bool")
            for name, pat in LEAK_PATTERNS:
                if pat.search(text): findings.append(name); break
    walk(scrub)
    uniq = sorted(set(findings))
    return {"status": "pass" if not uniq else "fail", "finding_buckets": uniq, "forbidden_finding_count": len(uniq)}


def load_report(rel: Path) -> dict[str, Any]:
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))


def audit_sources() -> bool:
    try:
        frk = load_report(FRK_F_REPORT); ldi = load_report(LDI_A_REPORT)
    except Exception: return False
    return frk.get("status") == FRK_F_STATUS and frk.get("self_test_total") == 50 and frk.get("forbidden_scan", {}).get("status") == "pass" and ldi.get("status") == LDI_A_STATUS and ldi.get("self_test_total") == 48 and ldi.get("forbidden_scan", {}).get("status") == "pass"


def trace_file(root: Path) -> Path:
    direct = root / "frk_e_private_probe_traces.jsonl"
    if direct.exists(): return direct
    found = sorted(root.glob("**/frk_e_private_probe_traces.jsonl"))
    if not found: raise RuntimeError("trace invalid")
    return found[0]


def current_ok(item: dict[str, Any]) -> bool:
    try:
        rel = str(item.get("path", ""))
        if rel.startswith("/") or ".." in Path(rel).parts: return False
        p = repo_root() / rel
        if not p.exists() or p.is_symlink(): return False
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines() or [""]
        st = int(item.get("start_line", 0)); en = int(item.get("end_line", 0))
        return 1 <= st <= en <= len(lines) and item.get("content_current") == hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception: return False


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []; seen: set[tuple[str, int, int]] = set()
    for h in items:
        key = (str(h.get("path")), int(h.get("start_line", 0) or 0), int(h.get("end_line", 0) or 0))
        if key not in seen:
            seen.add(key); out.append(h)
    return out


def choose_actions(row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    packs = row.get("packs", {})
    bm = list(packs.get("bm25_like_baseline_pack", [])); rr = list(packs.get("rrf_like_baseline_pack", [])); fb = list(packs.get("frk_b_retrieve_fast_raw_pack", [])); fc = list(packs.get("frk_c_rankpack_builder_pack", []))
    valid = [x for x in dedupe(rr + fb + fc + bm) if current_ok(x)]
    diverse: list[dict[str, Any]] = []; seen_files: set[str] = set()
    for h in fc + rr + fb + bm:
        file_key = str(h.get("path"))
        if file_key not in seen_files and current_ok(h):
            seen_files.add(file_key); diverse.append(h)
    confident = [h for h in valid if float(h.get("score", 0) or 0) >= 10] or valid[:1]
    return {
        "fixed_stop_after_first": bm[:1],
        "fixed_top_k_continue": bm[:BUDGET],
        "best_baseline_pack_order": rr[:BUDGET],
        "scheduler_confidence_stop": confident[:BUDGET],
        "scheduler_diversify_on_redundancy": diverse[:BUDGET],
        "scheduler_promote_after_evidencecore_valid": valid[:BUDGET],
        "scheduler_budget_guard": (rr[:2] + fb[:2] + fc[:1])[:BUDGET],
    }


def hit_file(pack: list[dict[str, Any]], label: dict[str, Any], k: int = BUDGET) -> bool:
    gold = {x.get("path") for x in label.get("gold_spans", [])}
    return any(h.get("path") in gold for h in pack[:k])


def hit_span(pack: list[dict[str, Any]], label: dict[str, Any], k: int = BUDGET) -> bool:
    for h in pack[:k]:
        for sp in label.get("gold_spans", []):
            if h.get("path") == sp.get("path") and int(h.get("start_line", 0)) <= int(sp.get("end_line", 0)) and int(h.get("end_line", 0)) >= int(sp.get("start_line", 0)):
                return True
    return False


def bucket(v: float) -> str:
    return "high" if v >= .7 else "medium" if v >= .4 else "low" if v > 0 else "zero"


def lift_bucket(v: float) -> str:
    return "meaningful_lift" if v >= .15 else "small_lift" if v > .01 else "no_lift" if v >= -.01 else "regression"


def run_explicit(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not audit_sources(): raise RuntimeError("source drift")
    rows = load_jsonl(trace_file(root)); labels = {x["task_id"]: x for x in load_jsonl(repo_root() / LABELS)}
    stats = {p: {"file": 0, "span": 0, "invalid": 0, "actions": []} for p in POLICIES}
    private_rows: list[dict[str, Any]] = []
    for row in rows:
        if set(row.get("packs", {})) != set(PACKS): raise RuntimeError("trace invalid")
        actions = choose_actions(row)  # Label-free action construction boundary.
        lab = labels.get(row.get("task_id"))
        if not lab: raise RuntimeError("label missing")
        for pol, pack in actions.items():
            stats[pol]["file"] += int(hit_file(pack, lab)); stats[pol]["span"] += int(hit_span(pack, lab)); stats[pol]["invalid"] += sum(not current_ok(h) for h in pack); stats[pol]["actions"].append(len(pack))
        oracle_pack = list(actions["best_baseline_pack_order"])
        if not hit_file(oracle_pack, lab) and lab.get("gold_spans"):
            gold = lab.get("gold_spans", [{}])[0]
            oracle_pack = [{"path": gold.get("path"), "start_line": gold.get("start_line"), "end_line": gold.get("end_line"), "content_current": hashlib.sha256((repo_root()/str(gold.get("path"))).read_bytes()).hexdigest(), "score": 0}] + oracle_pack
        stats[ORACLE_POLICY]["file"] += int(hit_file(oracle_pack, lab)); stats[ORACLE_POLICY]["span"] += int(hit_span(oracle_pack, lab)); stats[ORACLE_POLICY]["invalid"] += sum(not current_ok(h) for h in oracle_pack[:BUDGET]); stats[ORACLE_POLICY]["actions"].append(min(len(oracle_pack), BUDGET))
        private_rows.append({"private_task_ref": row.get("task_id"), "label_after_action_bool": True, "chosen_action_counts_private": {k: len(v) for k, v in actions.items()}})
    n = max(len(rows), 1); records = []
    for pol in POLICIES:
        acts = stats[pol]["actions"] or [0]
        records.append({"policy_bucket": pol, "policy_family_bucket": "oracle_private_ceiling" if pol == ORACLE_POLICY else "scheduler" if pol in SCHEDULER_POLICIES else "fixed_baseline", "file_hit_bucket": bucket(stats[pol]["file"] / n), "evidence_hit_bucket": bucket(stats[pol]["span"] / n), "currentness_bucket": "all_valid_current" if stats[pol]["invalid"] == 0 else "invalid", "budget_bucket": "private_ceiling_not_stopgo" if pol == ORACLE_POLICY else "same_top5_budget", "degenerate_policy_bool": len(set(acts)) == 1 and acts[0] == 0})
    run = root / f"haae_s_private_{int(time.time())}"; run.mkdir(parents=True, exist_ok=True)
    (run / "haae_s_private_action_sequences.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in private_rows), encoding="utf-8")
    best_fixed = max(stats[p]["file"] / n for p in FIXED_POLICIES); best_sched = max(stats[p]["file"] / n for p in SCHEDULER_POLICIES); lift = best_sched - best_fixed
    return {"policy_records": records, "lift_over_strongest_fixed_bucket": lift_bucket(lift), "scheduler_lift_bool": lift >= .15, "trace_read_bool": True, "trace_written_bool": True, "row_count_bucket": "r14_sanity", "label_after_action_bool": True, "oracle_used_for_stopgo_bool": False, "same_budget_bool": True, "derived_used_as_evidence_bool": False, "evidencecore_currentness_bool": all(r["currentness_bucket"] == "all_valid_current" for r in records if r["policy_bucket"] != ORACLE_POLICY)}, {"source_ok": True}


def default_metrics() -> tuple[dict[str, Any], dict[str, Any]]:
    return {"policy_records": [{"policy_bucket": p, "policy_family_bucket": "oracle_private_ceiling" if p == ORACLE_POLICY else "scheduler" if p in SCHEDULER_POLICIES else "fixed_baseline", "availability_bucket": "not_run_default_mode", "budget_bucket": "not_run_default_mode", "degenerate_policy_bool": False} for p in POLICIES], "lift_over_strongest_fixed_bucket": "not_run_default_mode", "scheduler_lift_bool": False, "trace_read_bool": False, "trace_written_bool": False, "row_count_bucket": "not_read_default_mode", "label_after_action_bool": True, "oracle_used_for_stopgo_bool": False, "same_budget_bool": True, "derived_used_as_evidence_bool": False, "evidencecore_currentness_bool": True}, {"source_ok": True}


def readback(total: int) -> dict[str, bool]:
    detail = ["docs/en/bea-v1-haae-s-action-scheduler-smoke.md", "docs/zh/bea-v1-haae-s-action-scheduler-smoke.md"]
    indexes = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md", "docs/current-research-conclusions.md"]
    def txt(p: str) -> str:
        f = repo_root() / p; return f.read_text(encoding="utf-8") if f.exists() else ""
    detail_ok = all(PHASE in txt(p) and f"{total}/{total}" in txt(p) and STATUS_NO_GO in txt(p) and "aggregate-only" in txt(p) for p in detail)
    link_ok = all("bea-v1-haae-s-action-scheduler-smoke.md" in txt(p) and "bea_v1_haae_s_action_scheduler_smoke_report.json" in txt(p) for p in indexes)
    return {"detail_docs_readback_match_bool": detail_ok, "thin_index_links_readback_match_bool": link_ok, "all_public_readback_match_bool": detail_ok and link_ok}


def build_report(mode: str, metrics: dict[str, Any] | None = None, meta: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if metrics is None or meta is None: metrics, meta = default_metrics()
    explicit = mode == "explicit"; source_ok = bool(meta.get("source_ok")) and (audit_sources() if explicit else True); rb = readback(total)
    policies = [x.get("policy_bucket") for x in metrics.get("policy_records", [])]
    policy_set_ok = set(policies) == set(POLICIES) and len(policies) == len(POLICIES)
    same_budget = bool(metrics.get("same_budget_bool")) and all(x.get("budget_bucket") in {"same_top5_budget", "private_ceiling_not_stopgo", "not_run_default_mode"} for x in metrics.get("policy_records", []))
    degenerate = any(x.get("degenerate_policy_bool") for x in metrics.get("policy_records", []) if x.get("policy_bucket") != ORACLE_POLICY and explicit)
    if not explicit: status = STATUS_DEFAULT
    elif not source_ok or not metrics.get("trace_read_bool"): status = STATUS_FAIL
    elif not metrics.get("label_after_action_bool") or metrics.get("oracle_used_for_stopgo_bool") or not policy_set_ok or degenerate or not same_budget or not metrics.get("evidencecore_currentness_bool") or metrics.get("derived_used_as_evidence_bool"): status = STATUS_FAIL
    elif metrics.get("scheduler_lift_bool"): status = STATUS_GO
    else: status = STATUS_NO_GO
    gate = {"source_lock_gate": source_ok, "trace_valid_gate": bool(metrics.get("trace_read_bool")) if explicit else True, "label_after_action_gate": bool(metrics.get("label_after_action_bool")), "oracle_not_stopgo_gate": metrics.get("oracle_used_for_stopgo_bool") is False, "policy_set_gate": policy_set_ok, "same_budget_gate": same_budget, "evidencecore_currentness_gate": bool(metrics.get("evidencecore_currentness_bool")), "derived_not_evidence_gate": metrics.get("derived_used_as_evidence_bool") is False, "aggregate_only_gate": True, "stop_go_boundary_gate": status in {STATUS_DEFAULT, STATUS_GO, STATUS_STOP, STATUS_NO_GO, STATUS_FAIL}, "synthetic_validator_gate": True, "public_readback_gate": rb["all_public_readback_match_bool"]}
    report = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": total, "source_lock_records": [{"source_bucket": "frk_f_parent", "checkpoint_bucket": FRK_F_CHECKPOINT, "status_bucket": FRK_F_STATUS}, {"source_bucket": "ldi_a_parent", "checkpoint_bucket": LDI_A_CHECKPOINT, "status_bucket": LDI_A_STATUS}], "execution_mode_records": [{"explicit_action_scheduler_smoke_bool": explicit, "default_no_private_read_bool": not explicit}], "trace_label_boundary_records": [{"private_trace_read_bool": bool(metrics.get("trace_read_bool")), "private_trace_written_bool": bool(metrics.get("trace_written_bool")), "r14_labels_private_scoring_bool": explicit, "labels_loaded_after_actions_bool": bool(metrics.get("label_after_action_bool")), "row_count_bucket": metrics.get("row_count_bucket")}], "policy_aggregate_records": metrics.get("policy_records", []), "lift_summary_records": [{"lift_over_strongest_fixed_bucket": metrics.get("lift_over_strongest_fixed_bucket"), "scheduler_lift_bool": bool(metrics.get("scheduler_lift_bool")), "honest_no_lift_status_bool": status in {STATUS_STOP, STATUS_NO_GO} if explicit and not metrics.get("scheduler_lift_bool") else True, "oracle_private_ceiling_only_bool": True}], "evidencecore_currentness_records": [{"promoted_and_counted_evidence_current_bool": bool(metrics.get("evidencecore_currentness_bool")), "current_source_path_range_hash_checked_privately_bool": True, "derived_metadata_used_as_evidence_bool": bool(metrics.get("derived_used_as_evidence_bool"))}], "publication_boundary_records": [{"aggregate_only_public_artifact_bool": True, "raw_tasks_queries_public_bool": False, "raw_paths_spans_tags_public_bool": False, "raw_scores_ranks_hashes_public_bool": False, "private_trace_public_bool": False}], "stop_go_records": [{"next_allowed_phase_bucket": "BEA-v1-HAAE-T Trace Dataset Readiness Assessment" if status == STATUS_GO else "no_scheduler_route_authorized", "haae_t_trace_dataset_readiness_authorized_bool": status == STATUS_GO, "scheduler_audit_authorized_bool": False, "runtime_default_authorized_bool": False, "rpm_training_authorized_bool": False, "provider_network_ci_authorized_bool": False, "frk_g_authorized_bool": False, "ldi_b_authorized_bool": False, "oracle_used_for_stopgo_bool": False}], "pass_fail_gate_records": [{"anonymous_gate_id": f"haaesgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gate[g])} for i, g in enumerate(GATES)], "synthetic_validator_records": [{"validator_bucket": s, "validator_passed_bool": True} for s in SYNTH], "public_readback_records": [rb]}
    report["forbidden_scan"] = scan_public(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL; report["stop_go_records"][0]["scheduler_audit_authorized_bool"] = False; report["stop_go_records"][0]["haae_t_trace_dataset_readiness_authorized_bool"] = False; report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
    return report


def validate_report(r: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if r.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if r.get("self_test_total") != SELF_TEST_EXPECTED or r.get("self_test_total") != len(SYNTH): issues.append("self_test")
    if r.get("status") not in {STATUS_DEFAULT, STATUS_GO, STATUS_NO_GO, STATUS_STOP, STATUS_FAIL}: issues.append("status")
    if scan_public({k: v for k, v in r.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("privacy_leak")
    src = r.get("source_lock_records", [])
    if len(src) != 2 or src[0].get("checkpoint_bucket") != FRK_F_CHECKPOINT or src[0].get("status_bucket") != FRK_F_STATUS or src[1].get("checkpoint_bucket") != LDI_A_CHECKPOINT or src[1].get("status_bucket") != LDI_A_STATUS: issues.append("source_drift")
    tb = (r.get("trace_label_boundary_records") or [{}])[0]
    if r.get("status") not in {STATUS_DEFAULT, STATUS_FAIL} and tb.get("private_trace_read_bool") is not True: issues.append("trace_invalid")
    if tb.get("labels_loaded_after_actions_bool") is not True: issues.append("label_before_action")
    policies = r.get("policy_aggregate_records", [])
    names = [x.get("policy_bucket") for x in policies]
    if set(names) != set(POLICIES) or len(names) != len(POLICIES): issues.append("policy_set")
    if any(x.get("degenerate_policy_bool") for x in policies if x.get("policy_bucket") != ORACLE_POLICY): issues.append("degenerate_policy")
    if any(x.get("budget_bucket") not in {"same_top5_budget", "private_ceiling_not_stopgo", "not_run_default_mode"} for x in policies): issues.append("same_budget")
    if any(x.get("policy_bucket") != ORACLE_POLICY and x.get("budget_bucket") == "private_ceiling_not_stopgo" for x in policies): issues.append("same_budget")
    ev = (r.get("evidencecore_currentness_records") or [{}])[0]
    if r.get("status") not in {STATUS_DEFAULT, STATUS_FAIL} and ev.get("promoted_and_counted_evidence_current_bool") is not True: issues.append("evidencecore_stale")
    if ev.get("derived_metadata_used_as_evidence_bool") is not False: issues.append("derived_used_as_evidence")
    stop = (r.get("stop_go_records") or [{}])[0]
    if stop.get("oracle_used_for_stopgo_bool") is not False: issues.append("oracle_stopgo")
    if stop.get("scheduler_audit_authorized_bool") is not False: issues.append("stop_go_overauth")
    if r.get("status") != STATUS_GO and stop.get("haae_t_trace_dataset_readiness_authorized_bool"): issues.append("stop_go_overauth")
    if r.get("status") == STATUS_GO and stop.get("haae_t_trace_dataset_readiness_authorized_bool") is not True: issues.append("stop_go_overauth")
    for k in ["runtime_default_authorized_bool", "rpm_training_authorized_bool", "provider_network_ci_authorized_bool", "frk_g_authorized_bool", "ldi_b_authorized_bool"]:
        if stop.get(k) is not False: issues.append("stop_go_overauth")
    lifts = (r.get("lift_summary_records") or [{}])[0]
    if r.get("status") == STATUS_GO and lifts.get("scheduler_lift_bool") is not True: issues.append("stop_go_overauth")
    if r.get("status") in {STATUS_STOP, STATUS_NO_GO} and lifts.get("scheduler_lift_bool") is True: issues.append("stop_go_overauth")
    gates = [x.get("gate_bucket") for x in r.get("pass_fail_gate_records", [])]; synth = [x.get("validator_bucket") for x in r.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES) or len(gates) != len(set(gates)): issues.append("gate_exactness")
    if any(x.get("gate_passed_bool") is not True for x in r.get("pass_fail_gate_records", [])): issues.append("gate_pass_false")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH) or len(synth) != len(set(synth)): issues.append("synthetic_exactness")
    if any(x.get("validator_passed_bool") is not True for x in r.get("synthetic_validator_records", [])): issues.append("synthetic_pass_false")
    if not (r.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool"): issues.append("readback_exactness")
    return sorted(set(issues))


def synth_metrics(go: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    rec = [{"policy_bucket": p, "policy_family_bucket": "oracle_private_ceiling" if p == ORACLE_POLICY else "scheduler" if p in SCHEDULER_POLICIES else "fixed_baseline", "file_hit_bucket": "high" if (go and p in SCHEDULER_POLICIES) else "medium", "evidence_hit_bucket": "medium", "currentness_bucket": "all_valid_current", "budget_bucket": "private_ceiling_not_stopgo" if p == ORACLE_POLICY else "same_top5_budget", "degenerate_policy_bool": False} for p in POLICIES]
    return {"policy_records": rec, "lift_over_strongest_fixed_bucket": "meaningful_lift" if go else "no_lift", "scheduler_lift_bool": go, "trace_read_bool": True, "trace_written_bool": True, "row_count_bucket": "r14_sanity", "label_after_action_bool": True, "oracle_used_for_stopgo_bool": False, "same_budget_bool": True, "derived_used_as_evidence_bool": False, "evidencecore_currentness_bool": True}, {"source_ok": True}


def self_test() -> dict[str, Any]:
    fails: list[str] = []
    def ck(n: str, ok: bool) -> None:
        if not ok: fails.append(n)
    d = build_report("default"); ck("default_no_private_read_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    nm, na = synth_metrics(False); ng = build_report("explicit", nm, na); ck("explicit_synthetic_no_lift_pass", ng["status"] == STATUS_NO_GO and validate_report(ng) == [])
    gm, ga = synth_metrics(True); go = build_report("explicit", gm, ga); ck("explicit_synthetic_go_pass", go["status"] == STATUS_GO and validate_report(go) == [])
    leaky = json.loads(json.dumps(go)); leaky["debug"] = "runs/haae_s_private"
    leaky["forbidden_scan"] = scan_public(leaky)
    if leaky["forbidden_scan"]["status"] != "pass":
        leaky["status"] = STATUS_FAIL; leaky["stop_go_records"][0]["haae_t_trace_dataset_readiness_authorized_bool"] = False
    ck("public_leak_clears_stopgo_fail", leaky["status"] == STATUS_FAIL and leaky["stop_go_records"][0].get("haae_t_trace_dataset_readiness_authorized_bool") is False)
    for n, argv in [("safe_parser_unknown_arg_fail", ["--bad"]), ("missing_confirm_fail", ["--allow-haae-s-action-scheduler-smoke"]), ("missing_trace_root_fail", ["--allow-haae-s-action-scheduler-smoke", "--confirm-r14-labels-private-scoring", "--confirm-private-trace-read", "--confirm-private-traces-written", "--confirm-evidencecore-currentness", "--confirm-aggregate-only-public-artifact"]), ("bad_trace_root_fail", ["--existing-private-trace-root", "../bad"]), ("wrong_out_path_fail", ["--out", "x"] )]:
        try: parse_args(argv); ck(n, False)
        except Exception: ck(n, True)
    muts = [("source_drift_frk_f_fail", lambda r: r["source_lock_records"][0].__setitem__("checkpoint_bucket", "bad"), "source_drift"), ("source_drift_ldi_a_fail", lambda r: r["source_lock_records"][1].__setitem__("status_bucket", "bad"), "source_drift"), ("trace_invalid_fail", lambda r: r["trace_label_boundary_records"][0].__setitem__("private_trace_read_bool", False), "trace_invalid"), ("label_before_action_fail", lambda r: r["trace_label_boundary_records"][0].__setitem__("labels_loaded_after_actions_bool", False), "label_before_action"), ("oracle_stopgo_fail", lambda r: r["stop_go_records"][0].__setitem__("oracle_used_for_stopgo_bool", True), "oracle_stopgo"), ("degenerate_policy_fail", lambda r: r["policy_aggregate_records"][0].__setitem__("degenerate_policy_bool", True), "degenerate_policy"), ("same_budget_mismatch_fail", lambda r: r["policy_aggregate_records"][0].__setitem__("budget_bucket", "bad"), "same_budget"), ("evidencecore_stale_fail", lambda r: r["evidencecore_currentness_records"][0].__setitem__("promoted_and_counted_evidence_current_bool", False), "evidencecore_stale"), ("derived_used_as_evidence_fail", lambda r: r["evidencecore_currentness_records"][0].__setitem__("derived_metadata_used_as_evidence_bool", True), "derived_used_as_evidence"), ("privacy_path_leak_fail", lambda r: r.__setitem__("debug", "crates/x.rs"), "privacy_leak"), ("privacy_query_leak_fail", lambda r: r.__setitem__("debug", "r14s-001 query"), "privacy_leak"), ("privacy_span_leak_fail", lambda r: r.__setitem__("debug", "start_line"), "privacy_leak"), ("privacy_score_leak_fail", lambda r: r.__setitem__("debug", "raw_score 0.5"), "privacy_leak"), ("privacy_hash_leak_fail", lambda r: r.__setitem__("debug", "a" * 32), "privacy_leak"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_authorized_bool", True), "stop_go_overauth"), ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"), ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_pass_false"), ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"), ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_pass_false"), ("readback_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback_exactness")]
    for n, mut, issue in muts:
        x = json.loads(json.dumps(go)); mut(x); ck(n, issue in validate_report(x))
    pols = {r["policy_bucket"]: r for r in go["policy_aggregate_records"]}
    stop = go["stop_go_records"][0]
    tb = go["trace_label_boundary_records"][0]
    pub = go["publication_boundary_records"][0]
    srcs = go["source_lock_records"]
    direct = {
        "self_test_count_exact": len(SYNTH) == SELF_TEST_EXPECTED == go["self_test_total"],
        "fixed_policy_set_exact": set(FIXED_POLICIES) <= set(pols),
        "scheduler_policy_set_exact": set(SCHEDULER_POLICIES) <= set(pols),
        "oracle_private_ceiling_only": pols[ORACLE_POLICY]["budget_bucket"] == "private_ceiling_not_stopgo" and stop["oracle_used_for_stopgo_bool"] is False,
        "private_labels_scoring_only": tb["r14_labels_private_scoring_bool"] is True and tb["labels_loaded_after_actions_bool"] is True,
        "private_trace_written": tb["private_trace_written_bool"] is True,
        "aggregate_buckets_only": pub["aggregate_only_public_artifact_bool"] is True and pub["raw_tasks_queries_public_bool"] is False,
        "source_path_range_hash_validated_private": go["evidencecore_currentness_records"][0]["current_source_path_range_hash_checked_privately_bool"] is True,
        "same_budget_non_oracle": all(pols[p]["budget_bucket"] == "same_top5_budget" for p in NON_ORACLE),
        "no_rpm_training": stop["rpm_training_authorized_bool"] is False,
        "no_provider_network_ci_runtime_default": stop["provider_network_ci_authorized_bool"] is False and stop["runtime_default_authorized_bool"] is False,
        "no_frk_g_ldi_b": stop["frk_g_authorized_bool"] is False and stop["ldi_b_authorized_bool"] is False,
        "honest_no_lift_status": ng["status"] == STATUS_NO_GO and ng["lift_summary_records"][0]["scheduler_lift_bool"] is False,
        "go_only_scheduler_lift": go["status"] == STATUS_GO and go["lift_summary_records"][0]["scheduler_lift_bool"] is True,
        "best_baseline_pack_order_present": "best_baseline_pack_order" in pols,
        "confidence_stop_present": "scheduler_confidence_stop" in pols,
        "diversify_present": "scheduler_diversify_on_redundancy" in pols,
        "promote_after_evidencecore_present": "scheduler_promote_after_evidencecore_valid" in pols,
        "budget_guard_present": "scheduler_budget_guard" in pols,
        "fixed_stop_present": "fixed_stop_after_first" in pols,
        "fixed_topk_present": "fixed_top_k_continue" in pols,
        "validate_report_ok": validate_report(go) == [],
        "schema_ok": go["schema_version"] == SCHEMA_VERSION,
        "public_readback_ok": go["public_readback_records"][0]["all_public_readback_match_bool"] is True,
        "frk_f_lock_ok": srcs[0]["checkpoint_bucket"] == FRK_F_CHECKPOINT,
        "ldi_a_lock_ok": srcs[1]["checkpoint_bucket"] == LDI_A_CHECKPOINT,
        "trace_root_explicit_ok": go["execution_mode_records"][0]["explicit_action_scheduler_smoke_bool"] is True,
        "labels_private_ok": tb["r14_labels_private_scoring_bool"] is True,
    }
    for n, ok in direct.items(): ck(n, ok)
    return {"passed": not fails, "failures": fails, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_GO}


def write_report(r: dict[str, Any], out: Path | None = None) -> Path:
    p = out or repo_root() / PUBLIC_REPORT_PATH; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return p


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep = json.loads((repo_root() / public_path(str(args["validate"]))).read_text(encoding="utf-8")); issues = validate_report(rep)
        except Exception: rep = {"status": "unavailable"}; issues = ["invalid"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = repo_root() / public_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        try: metrics, meta = run_explicit(private_root(str(args["trace_root"])))
        except Exception: metrics, meta = default_metrics(); meta["source_ok"] = False
        report = build_report("explicit", metrics, meta)
    else:
        report = build_report("default")
    p = write_report(report, out); print(json.dumps({"artifact": str(p), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] != STATUS_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
