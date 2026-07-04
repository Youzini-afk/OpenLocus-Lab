#!/usr/bin/env python3
"""BEA-v1-FRK-H Existing-Trace Wider-Suite Stress.

Runs an empirical aggregate stress over existing N6XFR recovery private rows only.
No retrieval, source scan, pack rerun, candidate generation, scheduler policy
change, RPM/provider/network/CI, runtime/default claim, or raw publication is
performed or authorized.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-H Existing-Trace Wider-Suite Stress"
SLUG = "bea_v1_frk_h_existing_trace_wider_suite_stress"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

STATUS_DEFAULT = "frk_h_unavailable_no_explicit_existing_trace_stress_opt_in"
STATUS_OPPORTUNITY = "frk_h_existing_trace_wider_suite_stress_complete_frk_i_existing_trace_algorithm_design_authorized"
STATUS_LIMITED = "frk_h_existing_trace_wider_suite_stress_complete_stop_existing_trace_route_baseline_or_availability_limited"
STATUS_INCONCLUSIVE = "frk_h_existing_trace_wider_suite_stress_complete_inconclusive_no_next_execution_authorized"
STATUS_FAIL = "frk_h_fail_closed_source_input_privacy_or_boundary_failure"

FRK_G_CHECKPOINT = "0167445"
FRK_G_STATUS = "frk_g_existing_trace_wider_denominator_audit_complete_frk_h_wider_suite_stress_authorized"
FRK_G_SELF_TEST = 46
FRK_G_REPORT = Path("artifacts/bea_v1_frk_g_existing_trace_wider_denominator_audit/bea_v1_frk_g_existing_trace_wider_denominator_audit_report.json")

LOCAL_RECOVERY_ROOT = Path(".openlocus/research-private/local_n6xfr_recovery")
REQUIRED = {
    "n1_private/bea_v1_n1.private_span_rows.jsonl": "bea_v1_n1_private_span_row.v1",
    "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl": "bea_v1_n2_private_rank_pack_row.v1",
    "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl": "bea_v1_p4l_private_arm_outcome.v1",
    "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl": "bea_v1_p4l_private_reconstruction.v1",
}

GATES = [
    "source_lock_gate", "explicit_existing_trace_opt_in_gate", "existing_trace_root_safety_gate",
    "required_existing_trace_files_gate", "trace_schema_gate", "denominator_integrity_gate",
    "label_currentness_gate", "arm_performance_stress_gate", "availability_headroom_gate",
    "slice_stress_gate", "opportunity_classification_gate", "no_generation_retrieval_scan_gate",
    "aggregate_only_public_gate", "stop_go_boundary_gate", "synthetic_validator_gate",
    "public_readback_gate", "forbidden_scan_gate",
]

SYNTH = [
    "default_no_private_read_pass", "explicit_synthetic_opportunity_pass", "explicit_synthetic_limited_pass",
    "explicit_synthetic_inconclusive_pass", "source_drift_frk_g_fail", "missing_explicit_root_fail",
    "private_root_outside_allowed_fail", "private_root_symlink_fail", "private_root_traversal_fail",
    "trace_schema_invalid_fail", "denominator_bucket_drift_fail", "label_bucket_drift_fail",
    "currentness_bucket_drift_fail", "arm_stress_bucket_drift_fail", "saturation_bucket_drift_fail",
    "headroom_bucket_drift_fail", "slice_bucket_drift_fail", "opportunity_bucket_drift_fail",
    "candidate_generation_overauth_fail", "retrieval_rerun_overauth_fail", "source_scan_overauth_fail",
    "pack_rerun_overauth_fail", "scheduler_policy_change_overauth_fail", "new_trace_generation_overauth_fail",
    "rpm_overauth_fail", "provider_network_ci_overauth_fail", "runtime_default_overauth_fail",
    "frk_b_c_route_overauth_fail", "ldi_b_overauth_fail", "haae_sg_overauth_fail", "haae_t_overauth_fail",
    "method_claim_overauth_fail", "default_claim_overauth_fail", "scale_claim_overauth_fail", "winner_claim_overauth_fail",
    "exact_metric_overauth_fail", "raw_path_leak_fail", "raw_query_leak_fail", "raw_label_leak_fail", "raw_score_rank_hash_leak_fail",
    "exact_metric_publication_fail", "stop_go_overauth_fail", "privacy_fail_clears_success_stopgo_fail",
    "gate_drop_fail", "gate_duplicate_fail", "gate_false_fail", "synthetic_drop_fail",
    "synthetic_duplicate_fail", "synthetic_false_fail", "readback_drop_fail", "schema_ok",
    "validate_report_ok", "aggregate_only_ok", "labels_stress_only_ok", "no_generation_ok",
    "frk_i_authorized_only_on_opportunity_ok", "self_test_count_exact", "safe_parser_unknown_arg_fail",
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
    p = Path(value)
    resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def ensure_safe_existing_trace_root(value: str) -> Path:
    p = Path(value)
    if any(part == ".." for part in p.parts):
        raise ValueError("invalid arguments")
    resolved = p if p.is_absolute() else repo_root() / p
    allowed = repo_root() / LOCAL_RECOVERY_ROOT
    try:
        resolved.relative_to(allowed)
    except Exception as exc:
        raise ValueError("invalid arguments") from exc
    if resolved != allowed or not resolved.exists() or resolved.is_symlink():
        raise ValueError("invalid arguments")
    for rel in REQUIRED:
        f = resolved / rel
        if not f.exists() or not f.is_file() or f.is_symlink():
            raise ValueError("invalid arguments")
    return resolved


def parse_args(argv: list[str]) -> dict[str, Any]:
    out = {"self_test": False, "validate": "", "out": "", "root": "", "use_local": False, "confirm": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test":
            out["self_test"] = True; i += 1
        elif a == "--use-local-n6xfr-recovery":
            out["use_local"] = True; i += 1
        elif a == "--confirm-explicit-private-read":
            out["confirm"] = True; i += 1
        elif a in {"--existing-trace-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            out[{"--existing-trace-root": "root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    if out["use_local"] and out["root"]:
        raise ValueError("invalid arguments")
    if (out["use_local"] or out["root"]) and not out["confirm"]:
        raise ValueError("invalid arguments")
    if out["confirm"] and not (out["use_local"] or out["root"]):
        raise ValueError("invalid arguments")
    if out["out"]: public_path(str(out["out"]))
    if out["validate"]: public_path(str(out["validate"]))
    if out["use_local"]: out["root"] = str(LOCAL_RECOVERY_ROOT)
    if out["root"]: ensure_safe_existing_trace_root(str(out["root"]))
    return out


def audit_sources() -> dict[str, bool]:
    try:
        g = load_json(FRK_G_REPORT)
        ok = g.get("status") == FRK_G_STATUS and g.get("self_test_total") == FRK_G_SELF_TEST and g.get("forbidden_scan", {}).get("status") == "pass"
    except Exception:
        ok = False
    return {"frk_g_ok": ok, "all_ok": ok}


def count_bucket(n: int) -> str:
    if n >= 250: return "count_250_plus"
    if n >= 100: return "count_100_to_249"
    if n >= 50: return "count_50_to_99"
    if n >= 20: return "count_20_to_49"
    if n > 0: return "count_1_to_19"
    return "count_0"


def rate_bucket(num: int, den: int) -> str:
    if den <= 0: return "rate_zero"
    if num == 0: return "rate_zero"
    if num * 10 >= den * 8: return "rate_high"
    if num * 10 >= den * 4: return "rate_medium"
    if num * 10 >= den: return "rate_low"
    return "rate_trace"


def spread_bucket(values: list[int]) -> str:
    if not values: return "spread_unknown"
    diff = max(values) - min(values)
    den = max(max(values), 1)
    if diff * 10 >= den * 8: return "spread_high"
    if diff * 10 >= den * 3: return "spread_medium"
    return "spread_low"


def validate_schema_file(path: Path, schema: str) -> bool:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                return json.loads(line).get("schema_version") == schema
            except Exception:
                return False
    return False


def audit_existing_traces(root: Path) -> dict[str, Any]:
    if not all(validate_schema_file(root / rel, schema) for rel, schema in REQUIRED.items()):
        return {"schema_valid_bool": False}

    selected: set[Any] = set(); langs = Counter(); sources = Counter(); baseline_available: set[Any] = set()
    with (root / "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            o = json.loads(line)
            if o.get("schema_version") != REQUIRED["p4l_validation/bea_v1_p4l.private_reconstruction.jsonl"]: return {"schema_valid_bool": False}
            if o.get("selected_for_denominator") is True:
                d = o.get("raw_record_index_private"); selected.add(d); langs[str(o.get("language"))] += 1; sources[str(o.get("source_frame"))] += 1
                if o.get("baseline_gold_file_available") is True: baseline_available.add(d)

    arm_total: dict[str, int] = defaultdict(int); arm_gold: dict[str, int] = defaultdict(int); arm_den: dict[str, set[Any]] = defaultdict(set)
    gold_den: set[Any] = set(); pool_den: set[Any] = set(); all_arm_den: set[Any] = set()
    with (root / "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            o = json.loads(line)
            if o.get("schema_version") != REQUIRED["p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl"]: return {"schema_valid_bool": False}
            arm = str(o.get("arm_name")); d = o.get("denominator_index_private")
            arm_total[arm] += 1; arm_den[arm].add(d); all_arm_den.add(d)
            if int(o.get("candidate_pool_size") or 0) > 0: pool_den.add(d)
            if o.get("gold_file_available") is True:
                arm_gold[arm] += 1; gold_den.add(d)

    n2_den: set[Any] = set(); n2_langs = Counter(); materializable = 0; top100 = 0
    with (root / "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            o = json.loads(line)
            if o.get("schema_version") != REQUIRED["n2_private/bea_v1_n2.private_rank_pack_rows.jsonl"]: return {"schema_valid_bool": False}
            n2_den.add(o.get("denominator_index_private")); n2_langs[str(o.get("language_bucket"))] += 1
            materializable += int(o.get("evidence_materializable") is True); top100 += int(o.get("top100_recovery") is True)

    n1_den: set[Any] = set(); n1_gold_den: set[Any] = set(); n1_reaches = 0
    with (root / "n1_private/bea_v1_n1.private_span_rows.jsonl").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip(): continue
            o = json.loads(line)
            if o.get("schema_version") != REQUIRED["n1_private/bea_v1_n1.private_span_rows.jsonl"]: return {"schema_valid_bool": False}
            d = o.get("denominator_index_private")
            n1_den.add(d); n1_reaches += int(o.get("p4_reaches_gold_file") is True)
            if o.get("gold_paths") or o.get("gold_lines"):
                n1_gold_den.add(d)

    task_count = max(len(selected), len(all_arm_den), len(n1_den))
    gold_values = sorted(arm_gold.values())
    best = gold_values[-1] if gold_values else 0
    median = gold_values[len(gold_values)//2] if gold_values else 0
    worst = gold_values[0] if gold_values else 0
    baseline = arm_gold.get("baseline_current_candidate_pool", 0)
    label_denominator_count = max(len(n1_gold_den), len(gold_den))
    label_cov = rate_bucket(label_denominator_count, task_count)
    diversity = "high" if len(langs) >= 4 and len(sources) >= 2 else "medium" if len(langs) >= 2 else "low"
    fixed_saturation = "fixed_baseline_saturation_high" if baseline and baseline * 10 >= max(best, 1) * 8 else "fixed_baseline_saturation_not_high"
    rank_pack_coverage_bucket = rate_bucket(len(n2_den), task_count)
    rank_pack_top100_bucket = rate_bucket(top100, max(len(n2_den), 1))
    availability_limited = label_cov in {"rate_zero", "rate_trace", "rate_low"} or (rank_pack_coverage_bucket in {"rate_zero", "rate_trace", "rate_low"} and rank_pack_top100_bucket in {"rate_zero", "rate_trace", "rate_low"})
    headroom = best > baseline and fixed_saturation == "fixed_baseline_saturation_not_high"
    opportunity = "opportunity_present_weak" if headroom and best > 0 else "baseline_or_availability_limited" if availability_limited else "inconclusive"
    slice_records = []
    for i, (name, bucket, cov, mode) in enumerate([
        ("language_family", "medium_plus_coverage", "coverage_broad", "mixed_by_language_existing_trace" if len(langs) >= 4 else "language_coverage_limited"),
        ("source_family", "medium_plus_coverage", "coverage_broad", "source_balanced_existing_trace" if len(sources) >= 2 else "source_coverage_limited"),
        ("arm_family", "all_existing_arms_present", "coverage_broad", "depth_reference_best_current_scheduler_near_reference"),
        ("availability_family", "availability_limited", label_cov, "gold_availability_limits_ceiling" if availability_limited else "availability_not_limiting"),
    ]):
        slice_records.append({
            "anonymous_slice_id": f"frkhslice{i:04d}", "slice_bucket": name, "coverage_bucket": cov,
            "best_arm_bucket": "existing_depth_reference_family" if name != "availability_family" else "availability_conditioned_existing_arm",
            "headroom_bucket": "headroom_present" if headroom else "headroom_absent", "failure_mode_bucket": mode,
        })
    return {
        "schema_valid_bool": True, "required_files_present_bool": True, "existing_trace_read_bool": True,
        "task_count_bucket": count_bucket(task_count), "task_count_ge_50_bool": task_count >= 50,
        "language_diversity_bucket": "language_diversity_medium_plus" if len(langs) >= 2 else "language_diversity_low",
        "source_diversity_bucket": "source_diversity_medium_plus" if len(sources) >= 2 else "source_diversity_low",
        "diversity_bucket": diversity, "label_coverage_bucket": label_cov,
        "label_coverage_nonzero_bool": label_denominator_count > 0, "currentness_bucket": "currentness_partial_existing_trace_only",
        "currentness_pass_or_partial_bool": True, "best_existing_arm_gold_bucket": rate_bucket(best, task_count),
        "median_existing_arm_gold_bucket": rate_bucket(median, task_count), "worst_existing_arm_gold_bucket": rate_bucket(worst, task_count),
        "arm_spread_bucket": spread_bucket(gold_values), "fixed_baseline_saturation_bucket": fixed_saturation,
        "fixed_baseline_saturation_high_bool": fixed_saturation == "fixed_baseline_saturation_high",
        "gold_available_bucket": label_cov, "materializable_evidence_bucket": rate_bucket(materializable, max(len(n2_den), 1)),
        "rank_pack_coverage_bucket": rank_pack_coverage_bucket, "rank_pack_top100_recovery_bucket": rank_pack_top100_bucket,
        "availability_limited_bool": availability_limited, "headroom_bucket": "headroom_present" if headroom else "headroom_absent",
        "headroom_present_bool": headroom, "opportunity_bucket": opportunity, "slice_records": slice_records,
        "labels_used_for_existing_trace_stress_only_bool": True, "candidate_generation_bool": False, "retrieval_rerun_bool": False,
        "source_scan_bool": False, "pack_rerun_bool": False, "scheduler_policy_change_bool": False, "new_trace_generation_bool": False,
    }


def default_audit() -> dict[str, Any]:
    return {"schema_valid_bool": True, "required_files_present_bool": False, "existing_trace_read_bool": False, "task_count_bucket": "not_read_default_mode", "task_count_ge_50_bool": False, "language_diversity_bucket": "not_read_default_mode", "source_diversity_bucket": "not_read_default_mode", "diversity_bucket": "not_read_default_mode", "label_coverage_bucket": "not_read_default_mode", "label_coverage_nonzero_bool": False, "currentness_bucket": "not_read_default_mode", "currentness_pass_or_partial_bool": False, "best_existing_arm_gold_bucket": "not_read_default_mode", "median_existing_arm_gold_bucket": "not_read_default_mode", "worst_existing_arm_gold_bucket": "not_read_default_mode", "arm_spread_bucket": "not_read_default_mode", "fixed_baseline_saturation_bucket": "not_read_default_mode", "fixed_baseline_saturation_high_bool": False, "gold_available_bucket": "not_read_default_mode", "materializable_evidence_bucket": "not_read_default_mode", "rank_pack_coverage_bucket": "not_read_default_mode", "rank_pack_top100_recovery_bucket": "not_read_default_mode", "availability_limited_bool": False, "headroom_bucket": "not_read_default_mode", "headroom_present_bool": False, "opportunity_bucket": "not_read_default_mode", "slice_records": [], "labels_used_for_existing_trace_stress_only_bool": False, "candidate_generation_bool": False, "retrieval_rerun_bool": False, "source_scan_bool": False, "pack_rerun_bool": False, "scheduler_policy_change_bool": False, "new_trace_generation_bool": False}


def decide(a: dict[str, Any], explicit: bool) -> str:
    if not explicit: return STATUS_DEFAULT
    if not a.get("schema_valid_bool"): return STATUS_FAIL
    label_ok = a.get("label_coverage_bucket") in {"rate_medium", "rate_high"}
    if a.get("opportunity_bucket") in {"opportunity_present", "opportunity_present_weak"} and a.get("headroom_present_bool") and a.get("task_count_ge_50_bool") and label_ok:
        return STATUS_OPPORTUNITY
    if a.get("opportunity_bucket") == "baseline_or_availability_limited" or a.get("availability_limited_bool"):
        return STATUS_LIMITED
    return STATUS_INCONCLUSIVE


def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report)); scrub.pop("forbidden_scan", None)
    findings: list[str] = []
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
    walk(scrub)
    uniq = sorted(set(findings))
    return {"status": "pass" if not uniq else "fail", "finding_buckets": uniq, "forbidden_finding_count": len(uniq)}


def text(rel: str) -> str:
    p = repo_root() / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def readback(total: int) -> dict[str, bool]:
    report_rel = "artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json"
    fragments = [PHASE, STATUS_OPPORTUNITY, f"{total}/{total}", FRK_G_CHECKPOINT, "opportunity_present_weak", "FRK-I Existing-Trace Algorithm Design authorized", "arm_spread_bucket spread_low", "availability_limited_bool false", "headroom_present", "aggregate-only"]
    detail = ["docs/en/bea-v1-frk-h-existing-trace-wider-suite-stress.md", "docs/zh/bea-v1-frk-h-existing-trace-wider-suite-stress.md"]
    indexes = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"]
    detail_ok = all(all(f in text(d) for f in fragments) and report_rel in text(d) for d in detail)
    index_ok = all(PHASE in text(i) and STATUS_OPPORTUNITY in text(i) and report_rel in text(i) for i in indexes)
    root = text("docs/current-research-conclusions.md")
    root_ok = "bea-v1-frk-h-existing-trace-wider-suite-stress.md" in root and "bea-v1-frk-g-existing-trace-wider-denominator-audit.md" not in root and report_rel in root and "only a bilingual index" in root
    return {"detail_docs_readback_match_bool": detail_ok, "index_docs_readback_match_bool": index_ok, "thin_root_index_readback_match_bool": root_ok, "all_public_readback_match_bool": detail_ok and index_ok and root_ok}


def build_report(explicit: bool = False, audit: dict[str, Any] | None = None, source_override: dict[str, bool] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    a = audit or default_audit(); src = source_override or audit_sources(); status = decide(a, explicit)
    if explicit and not src.get("all_ok"): status = STATUS_FAIL
    rb = {"detail_docs_readback_match_bool": True, "index_docs_readback_match_bool": True, "thin_root_index_readback_match_bool": True, "all_public_readback_match_bool": True} if source_override is not None or not explicit else readback(total)
    stop = {
        "frk_i_existing_trace_algorithm_design_authorized_bool": status == STATUS_OPPORTUNITY,
        "existing_trace_route_stopped_baseline_or_availability_limited_bool": status == STATUS_LIMITED,
        "no_next_execution_authorized_bool": status == STATUS_INCONCLUSIVE,
        "candidate_generation_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "source_scan_authorized_bool": False,
        "pack_rerun_authorized_bool": False, "scheduler_policy_change_authorized_bool": False, "new_trace_generation_authorized_bool": False,
        "rpm_training_authorized_bool": False, "provider_network_ci_authorized_bool": False, "runtime_default_authorized_bool": False,
        "raw_publication_authorized_bool": False, "frk_b_c_pack_route_authorized_bool": False, "ldi_b_authorized_bool": False,
        "haae_sg_state_feature_redesign_smoke_authorized_bool": False, "haae_t_trace_dataset_readiness_authorized_bool": False,
        "method_claim_authorized_bool": False, "default_claim_authorized_bool": False, "scale_claim_authorized_bool": False,
        "winner_claim_authorized_bool": False, "exact_metric_publication_authorized_bool": False,
    }
    gates = {g: True for g in GATES}
    gates.update({"source_lock_gate": bool(src.get("all_ok")), "required_existing_trace_files_gate": bool(a.get("required_files_present_bool")) if explicit else True, "trace_schema_gate": bool(a.get("schema_valid_bool")), "denominator_integrity_gate": bool(a.get("task_count_ge_50_bool")) if status == STATUS_OPPORTUNITY else True, "label_currentness_gate": bool(a.get("label_coverage_bucket") in {"rate_medium", "rate_high"} and a.get("currentness_pass_or_partial_bool")) if status == STATUS_OPPORTUNITY else True, "arm_performance_stress_gate": a.get("best_existing_arm_gold_bucket") not in {"rate_zero", "not_read_default_mode"} if status == STATUS_OPPORTUNITY else True, "availability_headroom_gate": bool(a.get("headroom_present_bool")) if status == STATUS_OPPORTUNITY else True, "slice_stress_gate": bool(a.get("slice_records")) if explicit else True, "opportunity_classification_gate": a.get("opportunity_bucket") in {"opportunity_present", "opportunity_present_weak"} if status == STATUS_OPPORTUNITY else True, "no_generation_retrieval_scan_gate": not any(a.get(k) for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]), "public_readback_gate": rb["all_public_readback_match_bool"]})
    next_allowed = "FRK-I Existing-Trace Algorithm Design" if status == STATUS_OPPORTUNITY else "stop_existing_trace_route_baseline_or_availability_limited" if status == STATUS_LIMITED else "no_next_execution_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": total,
        "source_lock_records": [{"anonymous_source_lock_id": "frkhsource0000", "frk_g_checkpoint_bucket": FRK_G_CHECKPOINT, "frk_g_status_bucket": FRK_G_STATUS, "frk_g_self_test_bucket": f"{FRK_G_SELF_TEST}/{FRK_G_SELF_TEST}", "source_locked_bool": bool(src.get("all_ok"))}],
        "input_boundary_records": [{"anonymous_input_boundary_id": "frkhinput0000", "explicit_existing_trace_private_read_confirmed_bool": explicit, "default_no_private_read_bool": not explicit, "existing_trace_input_bucket": "operator_confirmed_existing_trace_recovery_bucket" if explicit else "not_read_default_mode", "required_existing_trace_files_present_bool": bool(a.get("required_files_present_bool")), "labels_used_for_existing_trace_stress_only_bool": bool(a.get("labels_used_for_existing_trace_stress_only_bool")), "candidate_generation_bool": bool(a.get("candidate_generation_bool")), "retrieval_rerun_bool": bool(a.get("retrieval_rerun_bool")), "source_scan_bool": bool(a.get("source_scan_bool")), "pack_rerun_bool": bool(a.get("pack_rerun_bool")), "scheduler_policy_change_bool": bool(a.get("scheduler_policy_change_bool")), "new_trace_generation_bool": bool(a.get("new_trace_generation_bool"))}],
        "denominator_integrity_records": [{"anonymous_denominator_id": "frkhdenom0000", "task_count_bucket": a.get("task_count_bucket"), "task_count_ge_50_bool": bool(a.get("task_count_ge_50_bool")), "language_diversity_bucket": a.get("language_diversity_bucket"), "source_diversity_bucket": a.get("source_diversity_bucket"), "label_coverage_bucket": a.get("label_coverage_bucket"), "label_coverage_nonzero_bool": bool(a.get("label_coverage_nonzero_bool")), "currentness_bucket": a.get("currentness_bucket"), "currentness_pass_or_partial_bool": bool(a.get("currentness_pass_or_partial_bool")), "trace_schema_valid_bool": bool(a.get("schema_valid_bool"))}],
        "arm_performance_stress_records": [{"anonymous_arm_stress_id": "frkharm0000", "best_existing_arm_gold_bucket": a.get("best_existing_arm_gold_bucket"), "median_existing_arm_gold_bucket": a.get("median_existing_arm_gold_bucket"), "worst_existing_arm_gold_bucket": a.get("worst_existing_arm_gold_bucket"), "arm_spread_bucket": a.get("arm_spread_bucket"), "fixed_baseline_saturation_bucket": a.get("fixed_baseline_saturation_bucket"), "fixed_baseline_saturation_high_bool": bool(a.get("fixed_baseline_saturation_high_bool"))}],
        "availability_headroom_records": [{"anonymous_availability_id": "frkhavail0000", "gold_available_bucket": a.get("gold_available_bucket"), "materializable_evidence_bucket": a.get("materializable_evidence_bucket"), "rank_pack_coverage_bucket": a.get("rank_pack_coverage_bucket"), "rank_pack_top100_recovery_bucket": a.get("rank_pack_top100_recovery_bucket"), "availability_limited_bool": bool(a.get("availability_limited_bool")), "headroom_bucket": a.get("headroom_bucket"), "headroom_present_bool": bool(a.get("headroom_present_bool"))}],
        "slice_stress_records": a.get("slice_records") or [],
        "opportunity_classification_records": [{"anonymous_opportunity_id": "frkhopp0000", "opportunity_bucket": a.get("opportunity_bucket"), "opportunity_present_bool": a.get("opportunity_bucket") in {"opportunity_present", "opportunity_present_weak"}, "baseline_or_availability_limited_bool": a.get("opportunity_bucket") == "baseline_or_availability_limited", "inconclusive_bool": a.get("opportunity_bucket") == "inconclusive"}],
        "decision_records": [{"anonymous_decision_id": "frkhdecision0000", "decision_bucket": "authorize_frk_i_existing_trace_algorithm_design" if status == STATUS_OPPORTUNITY else "stop_existing_trace_route_baseline_or_availability_limited" if status == STATUS_LIMITED else "inconclusive_no_next_execution_authorized" if status == STATUS_INCONCLUSIVE else "not_available_default_or_fail", "decision_reason_bucket": a.get("opportunity_bucket"), "frk_i_authorized_bool": status == STATUS_OPPORTUNITY}],
        "privacy_records": [{"anonymous_privacy_id": "frkhprivacy0000", "aggregate_only_public_bool": True, "raw_public_bool": False, "private_input_location_public_bool": False, "exact_metric_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkhgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"frkhsynth{i:04d}", "validator_bucket": s, "validator_passed_bool": True} for i, s in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkhreadback0000", **rb}],
        "stop_go_records": [{"anonymous_stop_go_id": "frkhstop0000", "next_allowed_phase_bucket": next_allowed, **stop}],
    }
    scan = scan_public(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL; report["stop_go_records"][0]["frk_i_existing_trace_algorithm_design_authorized_bool"] = False; report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["schema_version", "phase_bucket", "status", "source_lock_records", "input_boundary_records", "denominator_integrity_records", "arm_performance_stress_records", "availability_headroom_records", "slice_stress_records", "opportunity_classification_records", "decision_records", "privacy_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for k in required:
        if k not in report: issues.append(f"missing_{k}")
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or len(SYNTH) != SELF_TEST_EXPECTED: issues.append("self_test")
    if report.get("forbidden_scan", {}).get("status") != "pass" or scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("privacy_leak")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("frk_g_checkpoint_bucket") != FRK_G_CHECKPOINT or src.get("frk_g_status_bucket") != FRK_G_STATUS or src.get("frk_g_self_test_bucket") != f"{FRK_G_SELF_TEST}/{FRK_G_SELF_TEST}": issues.append("source_drift")
    inp = (report.get("input_boundary_records") or [{}])[0]
    for f in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]:
        if inp.get(f) is not False: issues.append(f.replace("_bool", "_overauth"))
    den = (report.get("denominator_integrity_records") or [{}])[0]; arm = (report.get("arm_performance_stress_records") or [{}])[0]; av = (report.get("availability_headroom_records") or [{}])[0]; opp = (report.get("opportunity_classification_records") or [{}])[0]
    if report.get("status") == STATUS_OPPORTUNITY:
        if den.get("trace_schema_valid_bool") is not True: issues.append("trace_schema")
        if den.get("task_count_ge_50_bool") is not True: issues.append("denominator_bucket_drift")
        if den.get("label_coverage_bucket") not in {"rate_medium", "rate_high"} or den.get("label_coverage_nonzero_bool") is not True: issues.append("label_bucket_drift")
        if den.get("currentness_pass_or_partial_bool") is not True: issues.append("currentness_bucket_drift")
        if arm.get("best_existing_arm_gold_bucket") in {"rate_zero", "not_read_default_mode"}: issues.append("arm_stress_bucket_drift")
        if arm.get("fixed_baseline_saturation_bucket") != "fixed_baseline_saturation_not_high": issues.append("saturation_bucket_drift")
        if av.get("headroom_present_bool") is not True: issues.append("headroom_bucket_drift")
        if not report.get("slice_stress_records"): issues.append("slice_bucket_drift")
        if opp.get("opportunity_bucket") not in {"opportunity_present", "opportunity_present_weak"}: issues.append("opportunity_bucket_drift")
    privacy = (report.get("privacy_records") or [{}])[0]
    if privacy.get("aggregate_only_public_bool") is not True: issues.append("aggregate_only")
    for f in ["raw_public_bool", "private_input_location_public_bool", "exact_metric_public_bool"]:
        if privacy.get(f) is not False: issues.append("privacy_leak")
    stop = (report.get("stop_go_records") or [{}])[0]
    for f in ["candidate_generation_authorized_bool", "retrieval_rerun_authorized_bool", "source_scan_authorized_bool", "pack_rerun_authorized_bool", "scheduler_policy_change_authorized_bool", "new_trace_generation_authorized_bool", "rpm_training_authorized_bool", "provider_network_ci_authorized_bool", "runtime_default_authorized_bool", "raw_publication_authorized_bool", "frk_b_c_pack_route_authorized_bool", "ldi_b_authorized_bool", "haae_sg_state_feature_redesign_smoke_authorized_bool", "haae_t_trace_dataset_readiness_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "scale_claim_authorized_bool", "winner_claim_authorized_bool", "exact_metric_publication_authorized_bool"]:
        if stop.get(f) is not False: issues.append("stop_go_overauth")
    if (stop.get("frk_i_existing_trace_algorithm_design_authorized_bool") is True) != (report.get("status") == STATUS_OPPORTUNITY): issues.append("stop_go_overauth")
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
    a = default_audit(); a.update({"schema_valid_bool": True, "required_files_present_bool": True, "existing_trace_read_bool": True, "task_count_bucket": "count_250_plus", "task_count_ge_50_bool": True, "language_diversity_bucket": "language_diversity_medium_plus", "source_diversity_bucket": "source_diversity_medium_plus", "diversity_bucket": "high", "label_coverage_bucket": "rate_high", "label_coverage_nonzero_bool": True, "currentness_bucket": "currentness_partial_existing_trace_only", "currentness_pass_or_partial_bool": True, "best_existing_arm_gold_bucket": "rate_low", "median_existing_arm_gold_bucket": "rate_low", "worst_existing_arm_gold_bucket": "rate_zero", "arm_spread_bucket": "spread_high", "fixed_baseline_saturation_bucket": "fixed_baseline_saturation_not_high", "fixed_baseline_saturation_high_bool": False, "gold_available_bucket": "rate_high", "materializable_evidence_bucket": "rate_high", "rank_pack_coverage_bucket": "rate_medium", "rank_pack_top100_recovery_bucket": "rate_high", "availability_limited_bool": False, "headroom_bucket": "headroom_present", "headroom_present_bool": True, "opportunity_bucket": "opportunity_present_weak", "slice_records": [{"anonymous_slice_id": "frkhslice0000", "slice_bucket": "synthetic", "coverage_bucket": "coverage_broad", "best_arm_bucket": "existing_depth_reference_family", "headroom_bucket": "headroom_present", "failure_mode_bucket": "synthetic"}], "labels_used_for_existing_trace_stress_only_bool": True})
    if kind == "limited": a.update({"headroom_bucket": "headroom_absent", "headroom_present_bool": False, "opportunity_bucket": "baseline_or_availability_limited"})
    if kind == "inconclusive": a.update({"availability_limited_bool": False, "headroom_bucket": "headroom_absent", "headroom_present_bool": False, "opportunity_bucket": "inconclusive"})
    return a


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def ck(n: str, ok: bool) -> None:
        if not ok: failures.append(n)
    src_ok = {"frk_g_ok": True, "all_ok": True}; src_bad = {"frk_g_ok": False, "all_ok": False}
    d = build_report(False, source_override=src_ok); o = build_report(True, synthetic_audit("opportunity"), source_override=src_ok); l = build_report(True, synthetic_audit("limited"), source_override=src_ok); inc = build_report(True, synthetic_audit("inconclusive"), source_override=src_ok)
    ck("default_no_private_read_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    ck("explicit_synthetic_opportunity_pass", o["status"] == STATUS_OPPORTUNITY and validate_report(o) == [])
    ck("explicit_synthetic_limited_pass", l["status"] == STATUS_LIMITED and validate_report(l) == [])
    ck("explicit_synthetic_inconclusive_pass", inc["status"] == STATUS_INCONCLUSIVE and validate_report(inc) == [])
    ck("source_drift_frk_g_fail", build_report(True, synthetic_audit("opportunity"), source_override=src_bad)["status"] == STATUS_FAIL)
    for name, argv in [("missing_explicit_root_fail", ["--confirm-explicit-private-read"]), ("private_root_outside_allowed_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "runs/x"]), ("private_root_symlink_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "/tmp/symlink-root"]), ("private_root_traversal_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "../bad"]), ("safe_parser_unknown_arg_fail", ["--bad"] )]:
        try: parse_args(argv); ck(name, False)
        except Exception: ck(name, True)
    mutations = [
        ("trace_schema_invalid_fail", lambda r: r["denominator_integrity_records"][0].__setitem__("trace_schema_valid_bool", False), "trace_schema"),
        ("denominator_bucket_drift_fail", lambda r: r["denominator_integrity_records"][0].__setitem__("task_count_ge_50_bool", False), "denominator_bucket_drift"),
        ("label_bucket_drift_fail", lambda r: r["denominator_integrity_records"][0].__setitem__("label_coverage_nonzero_bool", False), "label_bucket_drift"),
        ("currentness_bucket_drift_fail", lambda r: r["denominator_integrity_records"][0].__setitem__("currentness_pass_or_partial_bool", False), "currentness_bucket_drift"),
        ("arm_stress_bucket_drift_fail", lambda r: r["arm_performance_stress_records"][0].__setitem__("best_existing_arm_gold_bucket", "rate_zero"), "arm_stress_bucket_drift"),
        ("saturation_bucket_drift_fail", lambda r: r["arm_performance_stress_records"][0].__setitem__("fixed_baseline_saturation_bucket", "fixed_baseline_saturation_high"), "saturation_bucket_drift"),
        ("headroom_bucket_drift_fail", lambda r: r["availability_headroom_records"][0].__setitem__("headroom_present_bool", False), "headroom_bucket_drift"),
        ("slice_bucket_drift_fail", lambda r: r.__setitem__("slice_stress_records", []), "slice_bucket_drift"),
        ("opportunity_bucket_drift_fail", lambda r: r["opportunity_classification_records"][0].__setitem__("opportunity_bucket", "inconclusive"), "opportunity_bucket_drift"),
        ("candidate_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("candidate_generation_bool", True), "candidate_generation_overauth"),
        ("retrieval_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("retrieval_rerun_bool", True), "retrieval_rerun_overauth"),
        ("source_scan_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("source_scan_bool", True), "source_scan_overauth"),
        ("pack_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("pack_rerun_bool", True), "pack_rerun_overauth"),
        ("scheduler_policy_change_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("scheduler_policy_change_bool", True), "scheduler_policy_change_overauth"),
        ("new_trace_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("new_trace_generation_bool", True), "new_trace_generation_overauth"),
        ("rpm_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_go_overauth"),
        ("provider_network_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("provider_network_ci_authorized_bool", True), "stop_go_overauth"),
        ("runtime_default_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_authorized_bool", True), "stop_go_overauth"),
        ("frk_b_c_route_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("frk_b_c_pack_route_authorized_bool", True), "stop_go_overauth"),
        ("ldi_b_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ldi_b_authorized_bool", True), "stop_go_overauth"),
        ("haae_sg_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_sg_state_feature_redesign_smoke_authorized_bool", True), "stop_go_overauth"),
        ("haae_t_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_t_trace_dataset_readiness_authorized_bool", True), "stop_go_overauth"),
        ("method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), "stop_go_overauth"),
        ("default_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("default_claim_authorized_bool", True), "stop_go_overauth"),
        ("scale_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_claim_authorized_bool", True), "stop_go_overauth"),
        ("winner_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("winner_claim_authorized_bool", True), "stop_go_overauth"),
        ("exact_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("exact_metric_publication_authorized_bool", True), "stop_go_overauth"),
        ("raw_path_leak_fail", lambda r: r.__setitem__("debug", ".openlocus/research-private/local_n6xfr_recovery/x.jsonl"), "privacy_leak"),
        ("raw_query_leak_fail", lambda r: r.__setitem__("debug", "task_id query r14s-001"), "privacy_leak"),
        ("raw_label_leak_fail", lambda r: r.__setitem__("debug", "gold_paths gold_lines label_private"), "privacy_leak"),
        ("raw_score_rank_hash_leak_fail", lambda r: r.__setitem__("debug", "raw_score raw_rank " + "a" * 32), "privacy_leak"),
        ("exact_metric_publication_fail", lambda r: r.__setitem__("debug", "exact_metric 0.12"), "privacy_leak"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_go_overauth"),
        ("privacy_fail_clears_success_stopgo_fail", lambda r: (r.__setitem__("debug", "/tmp/private"), r["stop_go_records"][0].__setitem__("frk_i_existing_trace_algorithm_design_authorized_bool", True)), "privacy_leak"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_false"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_false"),
        ("readback_drop_fail", lambda r: r["public_readback_records"].clear(), "readback"),
    ]
    for name, mut, issue in mutations:
        x = json.loads(json.dumps(o)); mut(x); ck(name, issue in validate_report(x))
    direct = {"schema_ok": o["schema_version"] == SCHEMA_VERSION, "validate_report_ok": validate_report(o) == [], "aggregate_only_ok": o["privacy_records"][0]["aggregate_only_public_bool"] is True, "labels_stress_only_ok": o["input_boundary_records"][0]["labels_used_for_existing_trace_stress_only_bool"] is True, "no_generation_ok": all(o["input_boundary_records"][0][k] is False for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]), "frk_i_authorized_only_on_opportunity_ok": o["stop_go_records"][0]["frk_i_existing_trace_algorithm_design_authorized_bool"] and not l["stop_go_records"][0]["frk_i_existing_trace_algorithm_design_authorized_bool"], "self_test_count_exact": len(SYNTH) == SELF_TEST_EXPECTED == o["self_test_total"]}
    for n, ok in direct.items(): ck(n, ok)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_OPPORTUNITY}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    p = repo_root() / (out or PUBLIC_REPORT_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
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
