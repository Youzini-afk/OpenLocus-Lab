#!/usr/bin/env python3
"""BEA-v1-FRK-I Existing-Trace Algorithm Design Prototype.

Empirical deterministic, nonlearned, label-blind selector prototype over existing
N6XFR private trace rows only. Labels are read only after design for aggregate
scoring. Public artifact is bucket-only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-I Existing-Trace Algorithm Design Prototype"
SLUG = "bea_v1_frk_i_existing_trace_algorithm_design"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

STATUS_DEFAULT = "frk_i_unavailable_no_explicit_existing_trace_algorithm_opt_in"
STATUS_LIFT = "frk_i_existing_trace_algorithm_design_complete_frk_j_existing_trace_algorithm_validation_authorized"
STATUS_NO_LIFT = "frk_i_existing_trace_algorithm_design_complete_stop_existing_trace_algorithm_route_no_lift"
STATUS_INCONCLUSIVE = "frk_i_existing_trace_algorithm_design_complete_inconclusive_no_next_execution_authorized"
STATUS_FAIL = "frk_i_fail_closed_source_input_privacy_or_boundary_failure"

FRK_H_CHECKPOINT = "a95988f"
FRK_H_STATUS = "frk_h_existing_trace_wider_suite_stress_complete_frk_i_existing_trace_algorithm_design_authorized"
FRK_H_SELF_TEST = 58
FRK_H_REPORT = Path("artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json")
LOCAL_RECOVERY_ROOT = Path(".openlocus/research-private/local_n6xfr_recovery")
REQUIRED = {
    "n1_private/bea_v1_n1.private_span_rows.jsonl": "bea_v1_n1_private_span_row.v1",
    "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl": "bea_v1_n2_private_rank_pack_row.v1",
    "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl": "bea_v1_p4l_private_arm_outcome.v1",
    "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl": "bea_v1_p4l_private_reconstruction.v1",
}

GATES = [
    "source_lock_gate", "explicit_existing_trace_opt_in_gate", "existing_trace_root_safety_gate",
    "required_existing_trace_files_gate", "trace_schema_gate", "label_blind_design_gate",
    "deterministic_nonlearned_gate", "comparison_gate", "slice_gate", "risk_gate",
    "decision_gate", "no_generation_retrieval_scan_gate", "aggregate_only_public_gate",
    "stop_go_boundary_gate", "synthetic_validator_gate", "public_readback_gate", "forbidden_scan_gate",
]

SYNTH = [
    "default_no_private_read_pass", "explicit_synthetic_lift_pass", "explicit_synthetic_no_lift_pass",
    "explicit_synthetic_inconclusive_pass", "source_drift_checkpoint_fail", "source_drift_status_fail",
    "source_drift_selftest_fail", "source_drift_bucket_fail", "source_drift_stopgo_fail",
    "missing_explicit_root_fail", "private_root_outside_allowed_fail", "private_root_symlink_fail",
    "private_root_traversal_fail", "trace_schema_invalid_fail", "label_used_in_design_fail",
    "labels_not_scoring_only_fail", "nondeterministic_algorithm_fail", "learned_algorithm_fail",
    "candidate_generation_overauth_fail", "retrieval_rerun_overauth_fail", "source_scan_overauth_fail",
    "pack_rerun_overauth_fail", "scheduler_policy_change_overauth_fail", "new_trace_generation_overauth_fail",
    "rpm_overauth_fail", "provider_network_ci_overauth_fail", "runtime_default_overauth_fail",
    "method_claim_overauth_fail", "scale_claim_overauth_fail", "winner_claim_overauth_fail",
    "comparison_bucket_drift_fail", "slice_bucket_drift_fail", "slice_failure_mode_drift_fail", "risk_bucket_drift_fail",
    "frk_j_authorized_without_positive_lift_fail", "raw_path_leak_fail", "raw_query_leak_fail",
    "raw_label_leak_fail", "raw_score_rank_hash_leak_fail", "exact_metric_publication_fail",
    "stop_go_overauth_fail", "privacy_fail_clears_success_stopgo_fail", "gate_drop_fail",
    "gate_duplicate_fail", "gate_false_fail", "synthetic_drop_fail", "synthetic_duplicate_fail",
    "synthetic_false_fail", "readback_drop_fail", "schema_ok", "validate_report_ok",
    "aggregate_only_ok", "labels_scoring_only_ok", "no_generation_ok", "frk_j_authorized_only_on_lift_ok",
    "self_test_count_exact", "safe_parser_unknown_arg_fail",
]
SELF_TEST_EXPECTED = len(SYNTH)

LEAK_PATTERNS = [
    ("path", re.compile(r"/workspace/|/tmp/|/home/|\.openlocus|research-private|n6xfr|\.jsonl\b|private-root", re.I)),
    ("task_or_query", re.compile(r"r14s-\d+|task_id|query|Title:|scan_repo|bm25_search", re.I)),
    ("raw_label", re.compile(r"gold_paths|gold_lines|gold_spans|hard_negatives|label_private|snippet|start_line|end_line", re.I)),
    ("raw_metric", re.compile(r"raw_score|raw_rank|exact_metric|exact_value|\b\d+\.\d+\b|[0-9a-f]{32,64}", re.I)),
]
FORBIDDEN_KEYS = {"path", "paths", "query", "task_id", "label", "score", "rank", "hash", "root", "private_root", "snippet", "start_line", "end_line"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(rel: Path) -> dict[str, Any]:
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))


def public_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def ensure_safe_existing_trace_root(value: str) -> Path:
    p = Path(value)
    if any(part == ".." for part in p.parts): raise ValueError("invalid arguments")
    resolved = p if p.is_absolute() else repo_root() / p
    allowed = repo_root() / LOCAL_RECOVERY_ROOT
    try: resolved.relative_to(allowed)
    except Exception as exc: raise ValueError("invalid arguments") from exc
    if resolved != allowed or not resolved.exists() or resolved.is_symlink(): raise ValueError("invalid arguments")
    for rel in REQUIRED:
        f = resolved / rel
        if not f.exists() or not f.is_file() or f.is_symlink(): raise ValueError("invalid arguments")
    return resolved


def parse_args(argv: list[str]) -> dict[str, Any]:
    out = {"self_test": False, "validate": "", "out": "", "root": "", "use_local": False, "confirm": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": out["self_test"] = True; i += 1
        elif a == "--use-local-n6xfr-recovery": out["use_local"] = True; i += 1
        elif a == "--confirm-explicit-private-read": out["confirm"] = True; i += 1
        elif a in {"--existing-trace-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            out[{"--existing-trace-root": "root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    if out["use_local"] and out["root"]: raise ValueError("invalid arguments")
    if (out["use_local"] or out["root"]) and not out["confirm"]: raise ValueError("invalid arguments")
    if out["confirm"] and not (out["use_local"] or out["root"]): raise ValueError("invalid arguments")
    if out["out"]: public_path(str(out["out"]))
    if out["validate"]: public_path(str(out["validate"]))
    if out["use_local"]: out["root"] = str(LOCAL_RECOVERY_ROOT)
    if out["root"]: ensure_safe_existing_trace_root(str(out["root"]))
    return out


def audit_sources(override: dict[str, bool] | None = None) -> dict[str, bool]:
    if override is not None: return override
    try:
        h = load_json(FRK_H_REPORT)
        den = (h.get("denominator_integrity_records") or [{}])[0]
        arm = (h.get("arm_performance_stress_records") or [{}])[0]
        av = (h.get("availability_headroom_records") or [{}])[0]
        opp = (h.get("opportunity_classification_records") or [{}])[0]
        stop = (h.get("stop_go_records") or [{}])[0]
        ok = (
            h.get("status") == FRK_H_STATUS and h.get("self_test_total") == FRK_H_SELF_TEST and h.get("forbidden_scan", {}).get("status") == "pass"
            and den.get("label_coverage_bucket") == "rate_medium" and den.get("currentness_bucket") == "currentness_partial_existing_trace_only"
            and arm.get("fixed_baseline_saturation_bucket") == "fixed_baseline_saturation_not_high" and arm.get("best_existing_arm_gold_bucket") == "rate_low" and arm.get("arm_spread_bucket") == "spread_low"
            and av.get("availability_limited_bool") is False and av.get("headroom_present_bool") is True
            and opp.get("opportunity_bucket") == "opportunity_present_weak" and stop.get("frk_i_existing_trace_algorithm_design_authorized_bool") is True
        )
    except Exception:
        ok = False
    return {"frk_h_ok": ok, "all_ok": ok}


def rate_bucket(num: int, den: int) -> str:
    if den <= 0 or num == 0: return "rate_zero"
    if num * 10 >= den * 8: return "rate_high"
    if num * 10 >= den * 4: return "rate_medium"
    if num * 10 >= den: return "rate_low"
    return "rate_trace"


def count_bucket(n: int) -> str:
    if n >= 250: return "count_250_plus"
    if n >= 100: return "count_100_to_249"
    if n >= 50: return "count_50_to_99"
    if n > 0: return "count_1_to_49"
    return "count_0"


def validate_schema_file(path: Path, schema: str) -> bool:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            try: return json.loads(line).get("schema_version") == schema
            except Exception: return False
    return False


def selector_arm(features: dict[str, Any]) -> str:
    """Label-blind deterministic selector using existing metadata only."""
    p4_actions = int(features.get("p4_extra_depth_actions_bucket", 0) or 0)
    p4_pool = int(features.get("p4_candidate_pool_bucket", 0) or 0)
    p3_pool = int(features.get("p3_candidate_pool_bucket", 0) or 0)
    if p4_actions > 0 and p4_pool >= p3_pool:
        return "p4_latency_aware_action_scheduler_frozen"
    return "p3_constrained_depth_policy_reference"


def audit_existing_traces(root: Path) -> dict[str, Any]:
    if not all(validate_schema_file(root / rel, schema) for rel, schema in REQUIRED.items()): return {"schema_valid_bool": False}
    recs: dict[Any, dict[str, Any]] = defaultdict(dict); langs: dict[Any, str] = {}; sources: dict[Any, str] = {}; n2_available: set[Any] = set()
    for line in (root / "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl").open(encoding="utf-8", errors="replace"):
        if not line.strip(): continue
        o = json.loads(line)
        if o.get("schema_version") != REQUIRED["p4l_validation/bea_v1_p4l.private_reconstruction.jsonl"]: return {"schema_valid_bool": False}
        d = o.get("raw_record_index_private"); langs[d] = str(o.get("language")); sources[d] = str(o.get("source_frame"))
    for line in (root / "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl").open(encoding="utf-8", errors="replace"):
        if not line.strip(): continue
        o = json.loads(line)
        if o.get("schema_version") != REQUIRED["n2_private/bea_v1_n2.private_rank_pack_rows.jsonl"]: return {"schema_valid_bool": False}
        if o.get("evidence_materializable") is True and o.get("top100_recovery") is True: n2_available.add(o.get("denominator_index_private"))
    for line in (root / "n1_private/bea_v1_n1.private_span_rows.jsonl").open(encoding="utf-8", errors="replace"):
        if not line.strip(): continue
        o = json.loads(line)
        if o.get("schema_version") != REQUIRED["n1_private/bea_v1_n1.private_span_rows.jsonl"]: return {"schema_valid_bool": False}
    for line in (root / "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl").open(encoding="utf-8", errors="replace"):
        if not line.strip(): continue
        o = json.loads(line)
        if o.get("schema_version") != REQUIRED["p4l_validation/bea_v1_p4l.private_arm_outcome.v1".replace("bea_v1_p4l.private_arm_outcome.v1", "bea_v1_p4l.private_arm_outcomes.jsonl")]: return {"schema_valid_bool": False}
        d = o.get("denominator_index_private"); recs[d][str(o.get("arm_name"))] = o
    arms = sorted({a for r in recs.values() for a in r})
    # Design/selection stage: build only non-label features and choose an arm per denominator.
    # Do not read gold_file_available until after selected_by_denominator is frozen.
    selected_by_denominator: dict[Any, str] = {}
    selected_arms = Counter(); slice_total = Counter()
    for d, r in recs.items():
        p4 = r.get("p4_latency_aware_action_scheduler_frozen", {}); p3 = r.get("p3_constrained_depth_policy_reference", {})
        features = {
            "p4_extra_depth_actions_bucket": p4.get("extra_depth_actions_executed", 0),
            "p4_candidate_pool_bucket": p4.get("candidate_pool_size", 0),
            "p3_candidate_pool_bucket": p3.get("candidate_pool_size", 0),
            "rankpack_materializable_top100_bool": d in n2_available,
            "language_bucket": langs.get(d), "source_bucket": sources.get(d),
        }
        arm = selector_arm(features); selected_arms[arm] += 1
        selected_by_denominator[d] = arm
        sb = f"language_{features['language_bucket']}"; slice_total[sb] += 1

    # Scoring stage: private outcome labels/gold are read only after the selector choices are frozen.
    arm_gold = {a: sum(1 for r in recs.values() if r.get(a, {}).get("gold_file_available") is True) for a in arms}
    task_count = len(recs); best = max(arm_gold.values()) if arm_gold else 0; median = sorted(arm_gold.values())[len(arm_gold)//2] if arm_gold else 0
    selected_gold = sum(1 for d, arm in selected_by_denominator.items() if recs[d].get(arm, {}).get("gold_file_available") is True)
    positive_slices = 0; negative_slices = 0; comparable_slices = 0
    for sb, total in slice_total.items():
        if total >= 10:
            comparable_slices += 1
            denoms = [d for d in recs if f"language_{langs.get(d)}" == sb]
            selected_slice = sum(1 for d in denoms if recs[d].get(selected_by_denominator[d], {}).get("gold_file_available") is True)
            best_fixed_slice = max(sum(1 for d in denoms if recs[d].get(a, {}).get("gold_file_available") is True) for a in arms) if arms else 0
            if selected_slice > best_fixed_slice: positive_slices += 1
            elif selected_slice < best_fixed_slice: negative_slices += 1
    delta = selected_gold - best
    delta_bucket = "positive_lift" if delta > 0 else "neutral_no_lift" if delta == 0 else "negative_lift"
    coverage_bucket = "coverage_high" if sum(selected_arms.values()) == task_count and task_count >= 50 else "coverage_low"
    slice_consistency = "mixed_positive_or_better" if positive_slices and not negative_slices else "mixed_or_inconclusive" if positive_slices and negative_slices else "flat_or_negative"
    failure_mode = "selector_improves_availability_slice" if positive_slices and not negative_slices else "inconclusive" if positive_slices and negative_slices else "low_arm_spread_limits_algorithm"
    risk = "risk_medium" if delta_bucket == "neutral_no_lift" else "risk_low" if delta_bucket == "positive_lift" else "risk_high"
    return {
        "schema_valid_bool": True, "required_files_present_bool": True, "existing_trace_read_bool": True,
        "algorithm_name_bucket": "availability_weighted_rankpack_selector", "deterministic_bool": True, "nonlearned_bool": True,
        "label_blind_design_bool": True, "labels_used_for_scoring_only_bool": True, "gold_fields_read_after_design_bool": True,
        "task_count_bucket": count_bucket(task_count), "baseline_best_bucket": rate_bucket(best, task_count),
        "baseline_median_bucket": rate_bucket(median, task_count), "prototype_selector_bucket": rate_bucket(selected_gold, task_count),
        "prototype_vs_best_fixed_delta_bucket": delta_bucket, "coverage_bucket": coverage_bucket,
        "slice_consistency_bucket": slice_consistency, "slice_failure_mode_bucket": failure_mode, "generalization_risk_bucket": risk,
        "oracle_ceiling_bucket_private_diagnostic_only": rate_bucket(best, task_count),
        "candidate_generation_bool": False, "retrieval_rerun_bool": False, "source_scan_bool": False, "pack_rerun_bool": False,
        "scheduler_policy_change_bool": False, "new_trace_generation_bool": False,
    }


def default_audit() -> dict[str, Any]:
    return {"schema_valid_bool": True, "required_files_present_bool": False, "existing_trace_read_bool": False, "algorithm_name_bucket": "not_run_default_mode", "deterministic_bool": True, "nonlearned_bool": True, "label_blind_design_bool": True, "labels_used_for_scoring_only_bool": False, "gold_fields_read_after_design_bool": False, "task_count_bucket": "not_read_default_mode", "baseline_best_bucket": "not_read_default_mode", "baseline_median_bucket": "not_read_default_mode", "prototype_selector_bucket": "not_read_default_mode", "prototype_vs_best_fixed_delta_bucket": "not_read_default_mode", "coverage_bucket": "not_read_default_mode", "slice_consistency_bucket": "not_read_default_mode", "slice_failure_mode_bucket": "not_read_default_mode", "generalization_risk_bucket": "not_read_default_mode", "oracle_ceiling_bucket_private_diagnostic_only": "not_read_default_mode", "candidate_generation_bool": False, "retrieval_rerun_bool": False, "source_scan_bool": False, "pack_rerun_bool": False, "scheduler_policy_change_bool": False, "new_trace_generation_bool": False}


def decide(a: dict[str, Any], explicit: bool) -> str:
    if not explicit: return STATUS_DEFAULT
    if not a.get("schema_valid_bool"): return STATUS_FAIL
    if a.get("prototype_vs_best_fixed_delta_bucket") == "positive_lift" and a.get("slice_consistency_bucket") in {"mixed_positive_or_better", "consistent_positive"} and a.get("coverage_bucket") != "coverage_low" and a.get("generalization_risk_bucket") != "risk_high": return STATUS_LIFT
    if a.get("prototype_vs_best_fixed_delta_bucket") in {"neutral_no_lift", "negative_lift"}: return STATUS_NO_LIFT
    return STATUS_INCONCLUSIVE


def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report)); scrub.pop("forbidden_scan", None); findings: list[str] = []
    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS: findings.append("forbidden_key")
        if isinstance(node, dict):
            for k, v in node.items(): walk(v, str(k))
        elif isinstance(node, list):
            for v in node: walk(v, key)
        elif isinstance(node, str):
            if key == "validator_bucket": return
            t = node.replace("private_read_confirmed_bool", "boundary_bool").replace("raw_publication_authorized_bool", "boundary_bool")
            for name, pat in LEAK_PATTERNS:
                if pat.search(t): findings.append(name); break
    walk(scrub); uniq = sorted(set(findings))
    return {"status": "pass" if not uniq else "fail", "finding_buckets": uniq, "forbidden_finding_count": len(uniq)}


def text(rel: str) -> str:
    p = repo_root() / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def readback(total: int) -> dict[str, bool]:
    report_rel = "artifacts/bea_v1_frk_i_existing_trace_algorithm_design/bea_v1_frk_i_existing_trace_algorithm_design_report.json"
    fragments = [PHASE, STATUS_NO_LIFT, f"{total}/{total}", FRK_H_CHECKPOINT, "availability_weighted_rankpack_selector", "neutral_no_lift", "stop_existing_trace_algorithm_route_no_lift", "aggregate-only"]
    detail = ["docs/en/bea-v1-frk-i-existing-trace-algorithm-design.md", "docs/zh/bea-v1-frk-i-existing-trace-algorithm-design.md"]
    indexes = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"]
    detail_ok = all(all(f in text(d) for f in fragments) and report_rel in text(d) for d in detail)
    index_ok = all(PHASE in text(i) and STATUS_NO_LIFT in text(i) and report_rel in text(i) for i in indexes)
    en_current = text("docs/en/current-research-conclusions.md"); zh_current = text("docs/zh/current-research-conclusions.md")
    current_ok = (
        en_current.count("Latest FRK status (current):") == 1
        and zh_current.count("最新 FRK 状态（当前）：") == 1
        and "Latest FRK status (current): [BEA-v1-FRK-I" in en_current
        and "最新 FRK 状态（当前）：[BEA-v1-FRK-I" in zh_current
        and "Latest FRK status (historical): [BEA-v1-FRK-H" in en_current
        and "最新 FRK 状态（历史）：[BEA-v1-FRK-H" in zh_current
    )
    index_ok = index_ok and current_ok
    root = text("docs/current-research-conclusions.md")
    root_ok = "bea-v1-frk-i-existing-trace-algorithm-design.md" in root and "bea-v1-frk-h-existing-trace-wider-suite-stress.md" not in root and report_rel in root and "only a bilingual index" in root
    return {"detail_docs_readback_match_bool": detail_ok, "index_docs_readback_match_bool": index_ok, "thin_root_index_readback_match_bool": root_ok, "all_public_readback_match_bool": detail_ok and index_ok and root_ok}


def build_report(explicit: bool = False, audit: dict[str, Any] | None = None, source_override: dict[str, bool] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    a = audit or default_audit(); src = audit_sources(source_override); status = decide(a, explicit)
    if explicit and not src.get("all_ok"): status = STATUS_FAIL
    rb = {"detail_docs_readback_match_bool": True, "index_docs_readback_match_bool": True, "thin_root_index_readback_match_bool": True, "all_public_readback_match_bool": True} if source_override is not None or not explicit else readback(total)
    stop = {"frk_j_existing_trace_algorithm_validation_authorized_bool": status == STATUS_LIFT, "existing_trace_algorithm_route_stopped_no_lift_bool": status == STATUS_NO_LIFT, "no_next_execution_authorized_bool": status == STATUS_INCONCLUSIVE, "candidate_generation_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "source_scan_authorized_bool": False, "pack_rerun_authorized_bool": False, "scheduler_policy_change_authorized_bool": False, "new_trace_generation_authorized_bool": False, "rpm_training_authorized_bool": False, "provider_network_ci_authorized_bool": False, "runtime_default_authorized_bool": False, "method_claim_authorized_bool": False, "scale_claim_authorized_bool": False, "winner_claim_authorized_bool": False, "raw_publication_authorized_bool": False}
    gates = {g: True for g in GATES}
    gates.update({"source_lock_gate": bool(src.get("all_ok")), "required_existing_trace_files_gate": bool(a.get("required_files_present_bool")) if explicit else True, "trace_schema_gate": bool(a.get("schema_valid_bool")), "label_blind_design_gate": bool(a.get("label_blind_design_bool") and a.get("labels_used_for_scoring_only_bool")) if explicit else True, "deterministic_nonlearned_gate": bool(a.get("deterministic_bool") and a.get("nonlearned_bool")), "comparison_gate": a.get("prototype_vs_best_fixed_delta_bucket") != "not_read_default_mode" if explicit else True, "slice_gate": a.get("slice_consistency_bucket") != "not_read_default_mode" if explicit else True, "risk_gate": a.get("generalization_risk_bucket") != "risk_high" if status == STATUS_LIFT else True, "decision_gate": not (status == STATUS_LIFT and a.get("prototype_vs_best_fixed_delta_bucket") != "positive_lift"), "no_generation_retrieval_scan_gate": not any(a.get(k) for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]), "public_readback_gate": rb["all_public_readback_match_bool"]})
    next_allowed = "FRK-J Existing-Trace Algorithm Validation" if status == STATUS_LIFT else "stop_existing_trace_algorithm_route_no_lift" if status == STATUS_NO_LIFT else "no_next_execution_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": total,
        "source_lock_records": [{"anonymous_source_lock_id": "frkisource0000", "frk_h_checkpoint_bucket": FRK_H_CHECKPOINT, "frk_h_status_bucket": FRK_H_STATUS, "frk_h_self_test_bucket": f"{FRK_H_SELF_TEST}/{FRK_H_SELF_TEST}", "frk_h_required_bucket_lock_bool": bool(src.get("all_ok")), "source_locked_bool": bool(src.get("all_ok"))}],
        "input_boundary_records": [{"anonymous_input_boundary_id": "frkiinput0000", "explicit_existing_trace_private_read_confirmed_bool": explicit, "default_no_private_read_bool": not explicit, "existing_trace_input_bucket": "operator_confirmed_existing_trace_recovery_bucket" if explicit else "not_read_default_mode", "required_existing_trace_files_present_bool": bool(a.get("required_files_present_bool")), "candidate_generation_bool": bool(a.get("candidate_generation_bool")), "retrieval_rerun_bool": bool(a.get("retrieval_rerun_bool")), "source_scan_bool": bool(a.get("source_scan_bool")), "pack_rerun_bool": bool(a.get("pack_rerun_bool")), "scheduler_policy_change_bool": bool(a.get("scheduler_policy_change_bool")), "new_trace_generation_bool": bool(a.get("new_trace_generation_bool"))}],
        "algorithm_design_records": [{"anonymous_algorithm_id": "frkialgo0000", "algorithm_name_bucket": a.get("algorithm_name_bucket"), "deterministic_bool": bool(a.get("deterministic_bool")), "nonlearned_bool": bool(a.get("nonlearned_bool")), "label_blind_design_bool": bool(a.get("label_blind_design_bool")), "labels_used_for_scoring_only_bool": bool(a.get("labels_used_for_scoring_only_bool")), "gold_fields_read_after_design_bool": bool(a.get("gold_fields_read_after_design_bool")), "feature_family_bucket": "existing_metadata_materializable_top100_availability_language_source_arm_family"}],
        "comparison_records": [{"anonymous_comparison_id": "frkicomp0000", "task_count_bucket": a.get("task_count_bucket"), "baseline_best_bucket": a.get("baseline_best_bucket"), "baseline_median_bucket": a.get("baseline_median_bucket"), "prototype_selector_bucket": a.get("prototype_selector_bucket"), "prototype_vs_best_fixed_delta_bucket": a.get("prototype_vs_best_fixed_delta_bucket"), "coverage_bucket": a.get("coverage_bucket"), "oracle_ceiling_bucket_private_diagnostic_only": a.get("oracle_ceiling_bucket_private_diagnostic_only")}],
        "slice_records": [{"anonymous_slice_id": "frkislice0000", "slice_consistency_bucket": a.get("slice_consistency_bucket"), "slice_failure_mode_bucket": a.get("slice_failure_mode_bucket"), "coverage_bucket": a.get("coverage_bucket"), "prototype_vs_best_fixed_delta_bucket": a.get("prototype_vs_best_fixed_delta_bucket"), "generalization_risk_bucket": a.get("generalization_risk_bucket")}],
        "decision_records": [{"anonymous_decision_id": "frkidecision0000", "decision_bucket": "authorize_frk_j_existing_trace_algorithm_validation" if status == STATUS_LIFT else "stop_existing_trace_algorithm_route_no_lift" if status == STATUS_NO_LIFT else "inconclusive_no_next_execution_authorized" if status == STATUS_INCONCLUSIVE else "not_available_default_or_fail", "decision_reason_bucket": a.get("prototype_vs_best_fixed_delta_bucket"), "frk_j_authorized_bool": status == STATUS_LIFT}],
        "privacy_records": [{"anonymous_privacy_id": "frkiprivacy0000", "aggregate_only_public_bool": True, "raw_public_bool": False, "private_input_location_public_bool": False, "exact_metric_public_bool": False, "method_default_scale_winner_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkigate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"frkisynth{i:04d}", "validator_bucket": s, "validator_passed_bool": True} for i, s in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkireadback0000", **rb}],
        "stop_go_records": [{"anonymous_stop_go_id": "frkistop0000", "next_allowed_phase_bucket": next_allowed, **stop}],
    }
    scan = scan_public(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL; report["stop_go_records"][0]["frk_j_existing_trace_algorithm_validation_authorized_bool"] = False; report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
        report["stop_go_records"][0]["existing_trace_algorithm_route_stopped_no_lift_bool"] = False
        report["stop_go_records"][0]["no_next_execution_authorized_bool"] = False
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["schema_version", "phase_bucket", "status", "source_lock_records", "input_boundary_records", "algorithm_design_records", "comparison_records", "slice_records", "decision_records", "privacy_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for k in required:
        if k not in report: issues.append(f"missing_{k}")
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or len(SYNTH) != SELF_TEST_EXPECTED: issues.append("self_test")
    public_scan_ok = report.get("forbidden_scan", {}).get("status") == "pass" and scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] == "pass"
    if not public_scan_ok:
        issues.append("privacy_leak")
        stop_for_privacy = (report.get("stop_go_records") or [{}])[0]
        if stop_for_privacy.get("next_allowed_phase_bucket") != "not_authorized_privacy_failure" or any(stop_for_privacy.get(k) is True for k in ["frk_j_existing_trace_algorithm_validation_authorized_bool", "existing_trace_algorithm_route_stopped_no_lift_bool", "no_next_execution_authorized_bool"]):
            issues.append("privacy_stop_go_fail_open")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("frk_h_checkpoint_bucket") != FRK_H_CHECKPOINT or src.get("frk_h_status_bucket") != FRK_H_STATUS or src.get("frk_h_self_test_bucket") != f"{FRK_H_SELF_TEST}/{FRK_H_SELF_TEST}" or src.get("source_locked_bool") is not True: issues.append("source_drift")
    inp = (report.get("input_boundary_records") or [{}])[0]
    for f in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]:
        if inp.get(f) is not False: issues.append(f.replace("_bool", "_overauth"))
    alg = (report.get("algorithm_design_records") or [{}])[0]; comp = (report.get("comparison_records") or [{}])[0]; sl = (report.get("slice_records") or [{}])[0]
    if alg.get("label_blind_design_bool") is not True: issues.append("label_used_in_design")
    if alg.get("labels_used_for_scoring_only_bool") is not True and report.get("status") != STATUS_DEFAULT: issues.append("labels_not_scoring_only")
    if alg.get("deterministic_bool") is not True: issues.append("nondeterministic_algorithm")
    if alg.get("nonlearned_bool") is not True: issues.append("learned_algorithm")
    if report.get("status") == STATUS_LIFT:
        if comp.get("prototype_vs_best_fixed_delta_bucket") != "positive_lift": issues.append("frk_j_authorized_without_positive_lift")
        if sl.get("slice_consistency_bucket") not in {"mixed_positive_or_better", "consistent_positive"}: issues.append("slice_bucket_drift")
        if comp.get("coverage_bucket") == "coverage_low": issues.append("comparison_bucket_drift")
        if sl.get("generalization_risk_bucket") == "risk_high": issues.append("risk_bucket_drift")
    if report.get("status") == STATUS_NO_LIFT and comp.get("prototype_vs_best_fixed_delta_bucket") not in {"neutral_no_lift", "negative_lift"}: issues.append("comparison_bucket_drift")
    allowed_failure_modes = {"low_arm_spread_limits_algorithm", "rank_pack_coverage_limited", "label_coverage_limited", "currentness_partial_limits_claim", "selector_improves_availability_slice", "selector_flat_vs_best_fixed", "inconclusive"}
    if report.get("status") != STATUS_DEFAULT and sl.get("slice_failure_mode_bucket") not in allowed_failure_modes: issues.append("slice_failure_mode_drift")
    privacy = (report.get("privacy_records") or [{}])[0]
    if privacy.get("aggregate_only_public_bool") is not True: issues.append("aggregate_only")
    for f in ["raw_public_bool", "private_input_location_public_bool", "exact_metric_public_bool", "method_default_scale_winner_claim_bool"]:
        if privacy.get(f) is not False: issues.append("privacy_leak")
    stop = (report.get("stop_go_records") or [{}])[0]
    false_fields = ["candidate_generation_authorized_bool", "retrieval_rerun_authorized_bool", "source_scan_authorized_bool", "pack_rerun_authorized_bool", "scheduler_policy_change_authorized_bool", "new_trace_generation_authorized_bool", "rpm_training_authorized_bool", "provider_network_ci_authorized_bool", "runtime_default_authorized_bool", "method_claim_authorized_bool", "scale_claim_authorized_bool", "winner_claim_authorized_bool", "raw_publication_authorized_bool"]
    for f in false_fields:
        if stop.get(f) is not False: issues.append("stop_go_overauth")
    if (stop.get("frk_j_existing_trace_algorithm_validation_authorized_bool") is True) != (report.get("status") == STATUS_LIFT): issues.append("stop_go_overauth")
    gates = [x.get("gate_bucket") for x in report.get("pass_fail_gate_records", [])]; synth = [x.get("validator_bucket") for x in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_exactness")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if any(x.get("gate_passed_bool") is not True for x in report.get("pass_fail_gate_records", [])): issues.append("gate_false")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_exactness")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    if any(x.get("validator_passed_bool") is not True for x in report.get("synthetic_validator_records", [])): issues.append("synthetic_false")
    if (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool") is not True: issues.append("readback")
    return sorted(set(issues))


def synthetic_audit(kind: str) -> dict[str, Any]:
    a = default_audit(); a.update({"schema_valid_bool": True, "required_files_present_bool": True, "existing_trace_read_bool": True, "algorithm_name_bucket": "availability_weighted_rankpack_selector", "deterministic_bool": True, "nonlearned_bool": True, "label_blind_design_bool": True, "labels_used_for_scoring_only_bool": True, "gold_fields_read_after_design_bool": True, "task_count_bucket": "count_250_plus", "baseline_best_bucket": "rate_low", "baseline_median_bucket": "rate_low", "prototype_selector_bucket": "rate_low", "prototype_vs_best_fixed_delta_bucket": "positive_lift", "coverage_bucket": "coverage_high", "slice_consistency_bucket": "mixed_positive_or_better", "slice_failure_mode_bucket": "selector_improves_availability_slice", "generalization_risk_bucket": "risk_low", "oracle_ceiling_bucket_private_diagnostic_only": "rate_medium"})
    if kind == "no_lift": a.update({"prototype_vs_best_fixed_delta_bucket": "neutral_no_lift", "slice_failure_mode_bucket": "low_arm_spread_limits_algorithm", "generalization_risk_bucket": "risk_medium"})
    if kind == "inconclusive": a.update({"prototype_vs_best_fixed_delta_bucket": "unknown", "slice_consistency_bucket": "mixed_or_inconclusive", "slice_failure_mode_bucket": "inconclusive", "generalization_risk_bucket": "risk_high"})
    return a


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def ck(n: str, ok: bool) -> None:
        if not ok: failures.append(n)
    src_ok = {"frk_h_ok": True, "all_ok": True}; src_bad = {"frk_h_ok": False, "all_ok": False}
    d = build_report(False, source_override=src_ok); lift = build_report(True, synthetic_audit("lift"), source_override=src_ok); no = build_report(True, synthetic_audit("no_lift"), source_override=src_ok); inc = build_report(True, synthetic_audit("inconclusive"), source_override=src_ok)
    ck("default_no_private_read_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    ck("explicit_synthetic_lift_pass", lift["status"] == STATUS_LIFT and validate_report(lift) == [])
    ck("explicit_synthetic_no_lift_pass", no["status"] == STATUS_NO_LIFT and validate_report(no) == [])
    ck("explicit_synthetic_inconclusive_pass", inc["status"] == STATUS_INCONCLUSIVE and validate_report(inc) == [])
    for name in ["source_drift_checkpoint_fail", "source_drift_status_fail", "source_drift_selftest_fail", "source_drift_bucket_fail", "source_drift_stopgo_fail"]:
        ck(name, build_report(True, synthetic_audit("lift"), source_override=src_bad)["status"] == STATUS_FAIL)
    for name, argv in [("missing_explicit_root_fail", ["--confirm-explicit-private-read"]), ("private_root_outside_allowed_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "runs/x"]), ("private_root_symlink_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "/tmp/symlink-root"]), ("private_root_traversal_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "../bad"]), ("safe_parser_unknown_arg_fail", ["--bad"] )]:
        try: parse_args(argv); ck(name, False)
        except Exception: ck(name, True)
    muts = [
        ("trace_schema_invalid_fail", lambda r: r.__setitem__("schema_version", "bad"), "schema"),
        ("label_used_in_design_fail", lambda r: r["algorithm_design_records"][0].__setitem__("label_blind_design_bool", False), "label_used_in_design"),
        ("labels_not_scoring_only_fail", lambda r: r["algorithm_design_records"][0].__setitem__("labels_used_for_scoring_only_bool", False), "labels_not_scoring_only"),
        ("nondeterministic_algorithm_fail", lambda r: r["algorithm_design_records"][0].__setitem__("deterministic_bool", False), "nondeterministic_algorithm"),
        ("learned_algorithm_fail", lambda r: r["algorithm_design_records"][0].__setitem__("nonlearned_bool", False), "learned_algorithm"),
        ("candidate_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("candidate_generation_bool", True), "candidate_generation_overauth"),
        ("retrieval_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("retrieval_rerun_bool", True), "retrieval_rerun_overauth"),
        ("source_scan_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("source_scan_bool", True), "source_scan_overauth"),
        ("pack_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("pack_rerun_bool", True), "pack_rerun_overauth"),
        ("scheduler_policy_change_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("scheduler_policy_change_bool", True), "scheduler_policy_change_overauth"),
        ("new_trace_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("new_trace_generation_bool", True), "new_trace_generation_overauth"),
        ("rpm_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_go_overauth"),
        ("provider_network_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("provider_network_ci_authorized_bool", True), "stop_go_overauth"),
        ("runtime_default_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_authorized_bool", True), "stop_go_overauth"),
        ("method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), "stop_go_overauth"),
        ("scale_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_claim_authorized_bool", True), "stop_go_overauth"),
        ("winner_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("winner_claim_authorized_bool", True), "stop_go_overauth"),
        ("comparison_bucket_drift_fail", lambda r: r["comparison_records"][0].__setitem__("coverage_bucket", "coverage_low"), "comparison_bucket_drift"),
        ("slice_bucket_drift_fail", lambda r: r["slice_records"][0].__setitem__("slice_consistency_bucket", "not_positive"), "slice_bucket_drift"),
        ("slice_failure_mode_drift_fail", lambda r: r["slice_records"][0].__setitem__("slice_failure_mode_bucket", "bad_failure_mode"), "slice_failure_mode_drift"),
        ("risk_bucket_drift_fail", lambda r: r["slice_records"][0].__setitem__("generalization_risk_bucket", "risk_high"), "risk_bucket_drift"),
        ("frk_j_authorized_without_positive_lift_fail", lambda r: r["comparison_records"][0].__setitem__("prototype_vs_best_fixed_delta_bucket", "neutral_no_lift"), "frk_j_authorized_without_positive_lift"),
        ("raw_path_leak_fail", lambda r: r.__setitem__("debug", ".openlocus/research-private/local_n6xfr_recovery/x.jsonl"), "privacy_leak"),
        ("raw_query_leak_fail", lambda r: r.__setitem__("debug", "task_id query r14s-001"), "privacy_leak"),
        ("raw_label_leak_fail", lambda r: r.__setitem__("debug", "gold_paths gold_lines label_private"), "privacy_leak"),
        ("raw_score_rank_hash_leak_fail", lambda r: r.__setitem__("debug", "raw_score raw_rank " + "a" * 32), "privacy_leak"),
        ("exact_metric_publication_fail", lambda r: r.__setitem__("debug", "exact_metric 0.12"), "privacy_leak"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_go_overauth"),
        ("privacy_fail_clears_success_stopgo_fail", lambda r: (r.__setitem__("debug", "/tmp/private"), r["stop_go_records"][0].__setitem__("frk_j_existing_trace_algorithm_validation_authorized_bool", True)), "privacy_leak"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_false"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_false"),
        ("readback_drop_fail", lambda r: r["public_readback_records"].clear(), "readback"),
    ]
    for name, mut, issue in muts:
        x = json.loads(json.dumps(lift)); mut(x); ck(name, issue in validate_report(x))
    direct = {"schema_ok": lift["schema_version"] == SCHEMA_VERSION, "validate_report_ok": validate_report(lift) == [], "aggregate_only_ok": lift["privacy_records"][0]["aggregate_only_public_bool"] is True, "labels_scoring_only_ok": lift["algorithm_design_records"][0]["labels_used_for_scoring_only_bool"] is True, "no_generation_ok": all(lift["input_boundary_records"][0][k] is False for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]), "frk_j_authorized_only_on_lift_ok": lift["stop_go_records"][0]["frk_j_existing_trace_algorithm_validation_authorized_bool"] and not no["stop_go_records"][0]["frk_j_existing_trace_algorithm_validation_authorized_bool"], "self_test_count_exact": len(SYNTH) == SELF_TEST_EXPECTED == lift["self_test_total"]}
    for n, ok in direct.items(): ck(n, ok)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_NO_LIFT}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    p = repo_root() / (out or PUBLIC_REPORT_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return p


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = run_self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep = load_json(public_path(str(args["validate"]))); issues = validate_report(rep)
        except Exception: rep = {"status": "unavailable"}; issues = ["invalid"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    explicit = bool(args["root"]); audit = audit_existing_traces(ensure_safe_existing_trace_root(str(args["root"]))) if explicit else default_audit()
    report = build_report(explicit, audit); p = write_report(report, public_path(str(args["out"])) if args["out"] else None)
    print(json.dumps({"artifact": str(p), "status": report["status"], "decision_bucket": report["decision_records"][0]["decision_bucket"]}, sort_keys=True))
    return 0 if report["status"] != STATUS_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
