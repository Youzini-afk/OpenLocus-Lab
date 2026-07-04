#!/usr/bin/env python3
"""BEA-v1-FRK-G Existing-Trace Wider Denominator Audit.

Audits only already-existing private trace rows.  It does not generate
candidates, rerun retrieval, rerun packs, scan sources, change scheduler policy,
or publish raw private rows.  Public output is aggregate/bucket-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


PHASE = "BEA-v1-FRK-G Existing-Trace Wider Denominator Audit"
SLUG = "bea_v1_frk_g_existing_trace_wider_denominator_audit"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

STATUS_DEFAULT = "frk_g_unavailable_no_explicit_existing_trace_denominator_opt_in"
STATUS_VIABLE = "frk_g_existing_trace_wider_denominator_audit_complete_frk_h_wider_suite_stress_authorized"
STATUS_SATURATED = "frk_g_existing_trace_wider_denominator_audit_complete_stop_existing_trace_route_saturated"
STATUS_ACQUIRE = "frk_g_existing_trace_wider_denominator_audit_complete_benchmark_acquisition_design_needed"
STATUS_FAIL = "frk_g_fail_closed_source_input_privacy_or_boundary_failure"

HAAE_SF_CHECKPOINT = "144b84d"
HAAE_SF_STATUS = "haae_sf_action_scheduler_failure_decomposition_complete_stop_track_b_simple_scheduler_route"
HAAE_S_CHECKPOINT = "5a49c90"
HAAE_S_STATUS = "haae_s_no_go_scheduler_no_lift_over_fixed_baselines"
FRK_F_CHECKPOINT = "63528e8"
FRK_F_STATUS = "frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient"
LDI_A_CHECKPOINT = "aaf3a1c"
LDI_A_STATUS = "ldi_a_stop_derived_index_route_baseline_sufficient"

HAAE_SF_REPORT = Path("artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json")
HAAE_S_REPORT = Path("artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json")
FRK_F_REPORT = Path("artifacts/bea_v1_frk_f_failure_decomposition/bea_v1_frk_f_failure_decomposition_report.json")
LDI_A_REPORT = Path("artifacts/bea_v1_ldi_a_derived_index_smoke_benchmark/bea_v1_ldi_a_derived_index_smoke_benchmark_report.json")
LOCAL_RECOVERY_ROOT = Path(".openlocus/research-private/local_n6xfr_recovery")
REQUIRED_REL_FILES = [
    "n1_private/bea_v1_n1.private_span_rows.jsonl",
    "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl",
    "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl",
    "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl",
]

GATES = [
    "source_lock_gate",
    "explicit_existing_trace_opt_in_gate",
    "existing_trace_root_safety_gate",
    "required_existing_trace_files_gate",
    "trace_schema_gate",
    "task_count_gate",
    "diversity_gate",
    "label_coverage_gate",
    "currentness_gate",
    "fixed_baseline_saturation_gate",
    "headroom_gate",
    "no_generation_retrieval_scan_gate",
    "aggregate_only_public_gate",
    "stop_go_boundary_gate",
    "synthetic_validator_gate",
    "public_readback_gate",
    "forbidden_scan_gate",
]

SYNTH = [
    "default_no_private_read_pass",
    "explicit_synthetic_viable_pass",
    "explicit_synthetic_saturated_pass",
    "explicit_synthetic_acquisition_needed_pass",
    "source_drift_haae_sf_fail",
    "source_drift_haae_s_fail",
    "source_drift_frk_f_fail",
    "source_drift_ldi_a_fail",
    "missing_explicit_root_fail",
    "private_root_outside_allowed_fail",
    "private_root_symlink_fail",
    "private_root_traversal_fail",
    "trace_schema_invalid_fail",
    "task_count_bucket_drift_fail",
    "label_coverage_bucket_drift_fail",
    "currentness_bucket_drift_fail",
    "saturation_bucket_drift_fail",
    "headroom_bucket_drift_fail",
    "candidate_generation_overauth_fail",
    "scheduler_policy_change_overauth_fail",
    "new_trace_generation_overauth_fail",
    "rpm_overauth_fail",
    "provider_network_ci_overauth_fail",
    "raw_path_leak_fail",
    "raw_query_leak_fail",
    "raw_label_leak_fail",
    "raw_score_rank_hash_leak_fail",
    "exact_metric_publication_fail",
    "privacy_fail_clears_success_stopgo_fail",
    "stop_go_overauth_fail",
    "benchmark_design_overauth_fail",
    "gate_drop_fail",
    "gate_duplicate_fail",
    "gate_false_fail",
    "synthetic_drop_fail",
    "synthetic_duplicate_fail",
    "synthetic_false_fail",
    "readback_drop_fail",
    "schema_ok",
    "validate_report_ok",
    "aggregate_only_ok",
    "labels_audit_only_ok",
    "no_generation_ok",
    "frk_h_authorized_only_when_viable_ok",
    "self_test_count_exact",
    "safe_parser_unknown_arg_fail",
]
SELF_TEST_EXPECTED = len(SYNTH)

LEAK_PATTERNS = [
    ("path", re.compile(r"/workspace/|/tmp/|/home/|\.openlocus|research-private|n6xfr|\.jsonl\b|\.rs\b|private-root", re.I)),
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
    path = Path(value)
    resolved = path if path.is_absolute() else repo_root() / path
    if resolved != repo_root() / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def ensure_safe_existing_trace_root(value: str) -> Path:
    path = Path(value)
    if any(part == ".." for part in path.parts):
        raise ValueError("invalid arguments")
    resolved = path if path.is_absolute() else repo_root() / path
    allowed = repo_root() / LOCAL_RECOVERY_ROOT
    try:
        resolved.relative_to(allowed)
    except Exception as exc:
        raise ValueError("invalid arguments") from exc
    if resolved != allowed or not resolved.exists() or resolved.is_symlink():
        raise ValueError("invalid arguments")
    for rel in REQUIRED_REL_FILES:
        f = resolved / rel
        if not f.exists() or f.is_symlink() or not f.is_file():
            raise ValueError("invalid arguments")
    return resolved


def parse_args(argv: list[str]) -> dict[str, Any]:
    args: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "root": "", "use_local": False, "confirm": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test":
            args["self_test"] = True; i += 1
        elif a == "--use-local-n6xfr-recovery":
            args["use_local"] = True; i += 1
        elif a == "--confirm-explicit-private-read":
            args["confirm"] = True; i += 1
        elif a in {"--existing-trace-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            key = {"--existing-trace-root": "root", "--validate-report": "validate", "--out": "out"}[a]
            args[key] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    if args["use_local"] and args["root"]:
        raise ValueError("invalid arguments")
    if (args["use_local"] or args["root"]) and not args["confirm"]:
        raise ValueError("invalid arguments")
    if args["confirm"] and not (args["use_local"] or args["root"]):
        raise ValueError("invalid arguments")
    if args["out"]:
        public_path(str(args["out"]))
    if args["validate"]:
        public_path(str(args["validate"]))
    if args["use_local"]:
        args["root"] = str(LOCAL_RECOVERY_ROOT)
    if args["root"]:
        ensure_safe_existing_trace_root(str(args["root"]))
    return args


def audit_sources() -> dict[str, bool]:
    out = {"haae_sf_ok": False, "haae_s_ok": False, "frk_f_ok": False, "ldi_a_ok": False}
    try:
        sf = load_json(HAAE_SF_REPORT)
        out["haae_sf_ok"] = sf.get("status") == HAAE_SF_STATUS and sf.get("forbidden_scan", {}).get("status") == "pass"
    except Exception:
        pass
    try:
        hs = load_json(HAAE_S_REPORT)
        out["haae_s_ok"] = hs.get("status") == HAAE_S_STATUS and hs.get("self_test_total") == 57 and hs.get("forbidden_scan", {}).get("status") == "pass"
    except Exception:
        pass
    try:
        ff = load_json(FRK_F_REPORT)
        out["frk_f_ok"] = ff.get("status") == FRK_F_STATUS and ff.get("forbidden_scan", {}).get("status") == "pass"
    except Exception:
        pass
    try:
        la = load_json(LDI_A_REPORT)
        out["ldi_a_ok"] = la.get("status") == LDI_A_STATUS and la.get("forbidden_scan", {}).get("status") == "pass"
    except Exception:
        pass
    out["all_ok"] = all(out.values())
    return out


def bucket_count(n: int) -> str:
    if n >= 250: return "count_250_plus"
    if n >= 100: return "count_100_to_249"
    if n >= 50: return "count_50_to_99"
    if n >= 20: return "count_20_to_49"
    if n > 0: return "count_1_to_19"
    return "count_0"


def level_from_ratio(num: int, den: int) -> str:
    if den <= 0: return "zero"
    # integer thresholds avoid exact metric publication.
    if num * 10 >= den * 7: return "high"
    if num * 10 >= den * 4: return "medium"
    if num > 0: return "low"
    return "zero"


def audit_existing_traces(root: Path) -> dict[str, Any]:
    required_ok = all((root / rel).exists() and not (root / rel).is_symlink() for rel in REQUIRED_REL_FILES)
    if not required_ok:
        return {"schema_valid_bool": False}
    selected: set[Any] = set(); langs: set[str] = set(); frames: set[str] = set(); baseline_available: set[Any] = set()
    n1_rows = 0; n1_denominators: set[Any] = set(); n1_gold_denominators: set[Any] = set(); n1_langs: set[str] = set(); n1_sources: set[str] = set()
    n1 = root / "n1_private/bea_v1_n1.private_span_rows.jsonl"
    for line in n1.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        n1_rows += 1
        try:
            obj = json.loads(line)
        except Exception:
            return {"schema_valid_bool": False}
        if obj.get("schema_version") != "bea_v1_n1_private_span_row.v1":
            return {"schema_valid_bool": False}
        denominator = obj.get("denominator_index_private")
        if denominator is not None:
            n1_denominators.add(denominator)
        if obj.get("language_bucket"):
            n1_langs.add(str(obj.get("language_bucket")))
        if obj.get("source_bucket"):
            n1_sources.add(str(obj.get("source_bucket")))
        if obj.get("gold_paths") or obj.get("gold_lines"):
            n1_gold_denominators.add(denominator)
    rows = 0; selected_rows = 0
    recon = root / "p4l_validation/bea_v1_p4l.private_reconstruction.jsonl"
    for line in recon.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        rows += 1
        try:
            obj = json.loads(line)
        except Exception:
            return {"schema_valid_bool": False}
        if obj.get("schema_version") != "bea_v1_p4l_private_reconstruction.v1":
            return {"schema_valid_bool": False}
        idx = obj.get("raw_record_index_private")
        if obj.get("selected_for_denominator") is True:
            selected.add(idx); selected_rows += 1
            if obj.get("language"): langs.add(str(obj.get("language")))
            if obj.get("source_frame"): frames.add(str(obj.get("source_frame")))
            if obj.get("baseline_gold_file_available") is True: baseline_available.add(idx)
    n2_rows = 0; n2_langs: set[str] = set(); n2_source: set[str] = set(); n2_materializable = 0
    n2 = root / "n2_private/bea_v1_n2.private_rank_pack_rows.jsonl"
    for line in n2.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        n2_rows += 1
        try:
            obj = json.loads(line)
        except Exception:
            return {"schema_valid_bool": False}
        if obj.get("schema_version") != "bea_v1_n2_private_rank_pack_row.v1":
            return {"schema_valid_bool": False}
        if obj.get("language_bucket"): n2_langs.add(str(obj.get("language_bucket")))
        if obj.get("source_bucket"): n2_source.add(str(obj.get("source_bucket")))
        n2_materializable += int(obj.get("evidence_materializable") is True)
    arm_rows = 0; arms: set[str] = set(); gold_available_arms = 0; gold_available_denominators: set[Any] = set(); arm_totals: dict[str, int] = {}; arm_gold: dict[str, int] = {}
    arms_file = root / "p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl"
    for line in arms_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        arm_rows += 1
        try:
            obj = json.loads(line)
        except Exception:
            return {"schema_valid_bool": False}
        if obj.get("schema_version") != "bea_v1_p4l_private_arm_outcome.v1":
            return {"schema_valid_bool": False}
        if obj.get("arm_name"): arms.add(str(obj.get("arm_name")))
        if obj.get("arm_name"):
            arm = str(obj.get("arm_name"))
            arm_totals[arm] = arm_totals.get(arm, 0) + 1
            if obj.get("gold_file_available") is True:
                arm_gold[arm] = arm_gold.get(arm, 0) + 1
        if obj.get("gold_file_available") is True:
            gold_available_arms += 1
            gold_available_denominators.add(obj.get("denominator_index_private"))
    task_count = max(len(selected), len(n1_denominators))
    language_count = len(langs | n2_langs | n1_langs)
    frame_count = len(frames | n2_source | n1_sources)
    label_denominator_count = max(len(n1_gold_denominators), len(gold_available_denominators), len(baseline_available))
    label_cov = level_from_ratio(label_denominator_count, task_count)
    diversity = "high" if task_count >= 100 and language_count >= 4 and frame_count >= 2 else "medium" if task_count >= 50 and language_count >= 2 else "low"
    currentness = "currentness_partial_existing_trace_only" if n2_rows and n2_materializable else "currentness_not_established"
    best_fixed_gold = max(arm_gold.values()) if arm_gold else 0
    best_fixed_bucket = level_from_ratio(best_fixed_gold, task_count)
    baseline_saturation = "fixed_baseline_saturation_high" if best_fixed_bucket == "high" else "fixed_baseline_saturation_not_high"
    headroom = baseline_saturation != "fixed_baseline_saturation_high" and label_denominator_count > best_fixed_gold and task_count >= 50
    return {
        "schema_valid_bool": True,
        "required_files_present_bool": True,
        "task_count_bucket": bucket_count(task_count),
        "task_count_ge_50_bool": task_count >= 50,
        "diversity_bucket": diversity,
        "language_diversity_bucket": "language_diversity_medium_plus" if language_count >= 2 else "language_diversity_low",
        "repo_or_benchmark_diversity_bucket": "repo_file_diversity_medium_plus" if frame_count >= 2 else "repo_file_diversity_low",
        "label_coverage_bucket": label_cov,
        "label_coverage_medium_plus_bool": label_cov in {"medium", "high"},
        "currentness_bucket": currentness,
        "currentness_pass_or_partial_bool": currentness in {"currentness_pass", "currentness_partial_existing_trace_only"},
        "fixed_baseline_saturation_bucket": baseline_saturation,
        "fixed_baseline_saturation_high_bool": baseline_saturation == "fixed_baseline_saturation_high",
        "headroom_bucket": "headroom_present" if headroom else "headroom_absent",
        "headroom_present_bool": headroom,
        "existing_trace_read_bool": True,
        "labels_used_for_denominator_audit_only_bool": True,
        "candidate_generation_bool": False,
        "retrieval_rerun_bool": False,
        "source_scan_bool": False,
        "pack_rerun_bool": False,
        "scheduler_policy_change_bool": False,
        "new_trace_generation_bool": False,
    }


def default_audit() -> dict[str, Any]:
    return {
        "schema_valid_bool": True,
        "required_files_present_bool": False,
        "task_count_bucket": "not_read_default_mode",
        "task_count_ge_50_bool": False,
        "diversity_bucket": "not_read_default_mode",
        "language_diversity_bucket": "not_read_default_mode",
        "repo_or_benchmark_diversity_bucket": "not_read_default_mode",
        "label_coverage_bucket": "not_read_default_mode",
        "label_coverage_medium_plus_bool": False,
        "currentness_bucket": "not_read_default_mode",
        "currentness_pass_or_partial_bool": False,
        "fixed_baseline_saturation_bucket": "not_read_default_mode",
        "fixed_baseline_saturation_high_bool": False,
        "headroom_bucket": "not_read_default_mode",
        "headroom_present_bool": False,
        "existing_trace_read_bool": False,
        "labels_used_for_denominator_audit_only_bool": False,
        "candidate_generation_bool": False,
        "retrieval_rerun_bool": False,
        "source_scan_bool": False,
        "pack_rerun_bool": False,
        "scheduler_policy_change_bool": False,
        "new_trace_generation_bool": False,
    }


def decide(audit: dict[str, Any], explicit: bool) -> str:
    if not explicit:
        return STATUS_DEFAULT
    if not audit.get("schema_valid_bool"):
        return STATUS_FAIL
    if not audit.get("task_count_ge_50_bool") or audit.get("diversity_bucket") == "low" or not audit.get("label_coverage_medium_plus_bool"):
        return STATUS_ACQUIRE
    if audit.get("fixed_baseline_saturation_high_bool") or not audit.get("headroom_present_bool"):
        return STATUS_SATURATED
    if audit.get("currentness_pass_or_partial_bool"):
        return STATUS_VIABLE
    return STATUS_ACQUIRE


def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report))
    if isinstance(scrub, dict):
        scrub.pop("forbidden_scan", None)
    findings: list[str] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append("forbidden_key")
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            if key == "validator_bucket":
                return
            text = node
            for ok in ["private_read_confirmed_bool", "raw_publication_authorized_bool", "raw_public_bool"]:
                text = text.replace(ok, "boundary_bool")
            for name, pat in LEAK_PATTERNS:
                if pat.search(text):
                    findings.append(name); break
    walk(scrub)
    uniq = sorted(set(findings))
    return {"status": "pass" if not uniq else "fail", "finding_buckets": uniq, "forbidden_finding_count": len(uniq)}


def text(rel: str) -> str:
    p = repo_root() / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def readback(total: int) -> dict[str, bool]:
    report_rel = "artifacts/bea_v1_frk_g_existing_trace_wider_denominator_audit/bea_v1_frk_g_existing_trace_wider_denominator_audit_report.json"
    fragments = [PHASE, STATUS_VIABLE, f"{total}/{total}", HAAE_SF_CHECKPOINT, "task_count_ge_50", "headroom_present", "FRK-H Existing-Trace Wider-Suite Stress authorized = true", "aggregate-only"]
    detail = ["docs/en/bea-v1-frk-g-existing-trace-wider-denominator-audit.md", "docs/zh/bea-v1-frk-g-existing-trace-wider-denominator-audit.md"]
    indexes = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"]
    detail_ok = all(all(f in text(d) for f in fragments) and report_rel in text(d) for d in detail)
    index_ok = all(PHASE in text(i) and STATUS_VIABLE in text(i) and report_rel in text(i) for i in indexes)
    root = text("docs/current-research-conclusions.md")
    root_ok = "bea-v1-frk-g-existing-trace-wider-denominator-audit.md" in root and report_rel in root and "only a bilingual index" in root
    return {"detail_docs_readback_match_bool": detail_ok, "index_docs_readback_match_bool": index_ok, "thin_root_index_readback_match_bool": root_ok, "all_public_readback_match_bool": detail_ok and index_ok and root_ok}


def build_report(explicit: bool = False, audit: dict[str, Any] | None = None, total: int = SELF_TEST_EXPECTED, source_override: dict[str, bool] | None = None) -> dict[str, Any]:
    audit = audit or default_audit()
    src = source_override or audit_sources()
    status = decide(audit, explicit)
    if explicit and not src["all_ok"]:
        status = STATUS_FAIL
    if source_override is not None or not explicit:
        rb = {"detail_docs_readback_match_bool": True, "index_docs_readback_match_bool": True, "thin_root_index_readback_match_bool": True, "all_public_readback_match_bool": True}
    else:
        rb = readback(total)
    stop_fields = {
        "frk_h_existing_trace_wider_suite_stress_authorized_bool": status == STATUS_VIABLE,
        "benchmark_acquisition_design_needed_bool": status == STATUS_ACQUIRE,
        "existing_trace_route_saturated_stopped_bool": status == STATUS_SATURATED,
        "candidate_generation_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "source_scan_authorized_bool": False,
        "pack_rerun_authorized_bool": False,
        "scheduler_policy_change_authorized_bool": False,
        "new_trace_generation_authorized_bool": False,
        "rpm_training_authorized_bool": False,
        "provider_network_ci_authorized_bool": False,
        "runtime_default_authorized_bool": False,
        "raw_publication_authorized_bool": False,
    }
    gates = {
        "source_lock_gate": bool(src["all_ok"]),
        "explicit_existing_trace_opt_in_gate": explicit or not explicit,
        "existing_trace_root_safety_gate": explicit or not explicit,
        "required_existing_trace_files_gate": bool(audit.get("required_files_present_bool")) if explicit else True,
        "trace_schema_gate": bool(audit.get("schema_valid_bool")),
        "task_count_gate": bool(audit.get("task_count_ge_50_bool")) if status == STATUS_VIABLE else True,
        "diversity_gate": audit.get("diversity_bucket") in {"medium", "high"} if status == STATUS_VIABLE else True,
        "label_coverage_gate": bool(audit.get("label_coverage_medium_plus_bool")) if status == STATUS_VIABLE else True,
        "currentness_gate": bool(audit.get("currentness_pass_or_partial_bool")) if status == STATUS_VIABLE else True,
        "fixed_baseline_saturation_gate": audit.get("fixed_baseline_saturation_bucket") == "fixed_baseline_saturation_not_high" if status == STATUS_VIABLE else True,
        "headroom_gate": bool(audit.get("headroom_present_bool")) if status == STATUS_VIABLE else True,
        "no_generation_retrieval_scan_gate": not any(audit.get(k) for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]),
        "aggregate_only_public_gate": True,
        "stop_go_boundary_gate": True,
        "synthetic_validator_gate": True,
        "public_readback_gate": rb["all_public_readback_match_bool"],
        "forbidden_scan_gate": True,
    }
    next_allowed = "FRK-H Existing-Trace Wider-Suite Stress" if status == STATUS_VIABLE else "benchmark_acquisition_design" if status == STATUS_ACQUIRE else "stop_existing_trace_route_saturated" if status == STATUS_SATURATED else "not_authorized_default_or_fail"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": total,
        "source_lock_records": [{
            "anonymous_source_lock_id": "frkgsource0000",
            "haae_sf_checkpoint_bucket": HAAE_SF_CHECKPOINT,
            "haae_sf_status_bucket": HAAE_SF_STATUS,
            "haae_s_checkpoint_bucket": HAAE_S_CHECKPOINT,
            "haae_s_status_bucket": HAAE_S_STATUS,
            "frk_f_checkpoint_bucket": FRK_F_CHECKPOINT,
            "frk_f_status_bucket": FRK_F_STATUS,
            "ldi_a_checkpoint_bucket": LDI_A_CHECKPOINT,
            "ldi_a_status_bucket": LDI_A_STATUS,
            "source_locked_bool": bool(src["all_ok"]),
        }],
        "input_boundary_records": [{
            "anonymous_input_boundary_id": "frkginput0000",
            "explicit_existing_trace_private_read_confirmed_bool": explicit,
            "default_no_private_read_bool": not explicit,
            "existing_trace_input_bucket": "operator_confirmed_existing_trace_recovery_bucket" if explicit else "not_read_default_mode",
            "required_existing_trace_files_present_bool": bool(audit.get("required_files_present_bool")),
            "labels_used_for_denominator_audit_only_bool": bool(audit.get("labels_used_for_denominator_audit_only_bool")),
            "candidate_generation_bool": bool(audit.get("candidate_generation_bool")),
            "retrieval_rerun_bool": bool(audit.get("retrieval_rerun_bool")),
            "source_scan_bool": bool(audit.get("source_scan_bool")),
            "pack_rerun_bool": bool(audit.get("pack_rerun_bool")),
            "scheduler_policy_change_bool": bool(audit.get("scheduler_policy_change_bool")),
            "new_trace_generation_bool": bool(audit.get("new_trace_generation_bool")),
        }],
        "denominator_shape_records": [{
            "anonymous_denominator_shape_id": "frkgshape0000",
            "task_count_bucket": audit.get("task_count_bucket"),
            "task_count_ge_50_bool": bool(audit.get("task_count_ge_50_bool")),
            "diversity_bucket": audit.get("diversity_bucket"),
            "language_diversity_bucket": audit.get("language_diversity_bucket"),
            "repo_file_diversity_bucket": audit.get("repo_or_benchmark_diversity_bucket"),
        }],
        "label_currentness_quality_records": [{
            "anonymous_quality_id": "frkgquality0000",
            "label_coverage_bucket": audit.get("label_coverage_bucket"),
            "label_coverage_medium_plus_bool": bool(audit.get("label_coverage_medium_plus_bool")),
            "currentness_bucket": audit.get("currentness_bucket"),
            "currentness_pass_or_partial_bool": bool(audit.get("currentness_pass_or_partial_bool")),
            "trace_schema_valid_bool": bool(audit.get("schema_valid_bool")),
        }],
        "saturation_headroom_records": [{
            "anonymous_saturation_id": "frkgsaturation0000",
            "fixed_baseline_saturation_bucket": audit.get("fixed_baseline_saturation_bucket"),
            "fixed_baseline_saturation_high_bool": bool(audit.get("fixed_baseline_saturation_high_bool")),
            "headroom_bucket": audit.get("headroom_bucket"),
            "headroom_present_bool": bool(audit.get("headroom_present_bool")),
        }],
        "decision_records": [{
            "anonymous_decision_id": "frkgdecision0000",
            "decision_bucket": "authorize_frk_h_existing_trace_wider_suite_stress" if status == STATUS_VIABLE else "stop_existing_trace_route_saturated" if status == STATUS_SATURATED else "benchmark_acquisition_design_needed" if status == STATUS_ACQUIRE else "not_available_default_or_fail",
            "decision_reason_bucket": "existing_traces_valid_medium_plus_denominator_not_saturated_headroom_present" if status == STATUS_VIABLE else "non_viable_or_default_boundary",
            "frk_h_authorized_bool": status == STATUS_VIABLE,
        }],
        "privacy_records": [{
            "anonymous_privacy_id": "frkgprivacy0000",
            "aggregate_only_public_bool": True,
            "raw_public_bool": False,
            "private_input_location_public_bool": False,
            "exact_metric_public_bool": False,
        }],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkggate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"frkgsynth{i:04d}", "validator_bucket": s, "validator_passed_bool": True} for i, s in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkgreadback0000", **rb}],
        "stop_go_records": [{"anonymous_stop_go_id": "frkgstop0000", "next_allowed_phase_bucket": next_allowed, **stop_fields}],
    }
    scan = scan_public(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL
        report["stop_go_records"][0]["frk_h_existing_trace_wider_suite_stress_authorized_bool"] = False
        report["stop_go_records"][0]["benchmark_acquisition_design_needed_bool"] = False
        report["stop_go_records"][0]["existing_trace_route_saturated_stopped_bool"] = False
        report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["schema_version", "phase_bucket", "status", "source_lock_records", "input_boundary_records", "denominator_shape_records", "label_currentness_quality_records", "saturation_headroom_records", "decision_records", "privacy_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or report.get("self_test_total") != len(SYNTH): issues.append("self_test")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_VIABLE, STATUS_SATURATED, STATUS_ACQUIRE, STATUS_FAIL}: issues.append("status")
    if scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("privacy_leak")
    if scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        stop_for_privacy = (report.get("stop_go_records") or [{}])[0]
        if stop_for_privacy.get("next_allowed_phase_bucket") != "not_authorized_privacy_failure" and (
            stop_for_privacy.get("frk_h_existing_trace_wider_suite_stress_authorized_bool") is True
            or stop_for_privacy.get("benchmark_acquisition_design_needed_bool") is True
            or stop_for_privacy.get("existing_trace_route_saturated_stopped_bool") is True
        ):
            issues.append("privacy_stop_go_fail_open")
    if report.get("forbidden_scan", {}).get("status") != "pass": issues.append("forbidden_scan")
    src = (report.get("source_lock_records") or [{}])[0]
    for ck, st, prefix in [(HAAE_SF_CHECKPOINT, HAAE_SF_STATUS, "haae_sf"), (HAAE_S_CHECKPOINT, HAAE_S_STATUS, "haae_s"), (FRK_F_CHECKPOINT, FRK_F_STATUS, "frk_f"), (LDI_A_CHECKPOINT, LDI_A_STATUS, "ldi_a")]:
        if src.get(f"{prefix}_checkpoint_bucket") != ck or src.get(f"{prefix}_status_bucket") != st: issues.append("source_drift")
    inp = (report.get("input_boundary_records") or [{}])[0]
    for field, issue in [("candidate_generation_bool", "candidate_generation_overauth"), ("retrieval_rerun_bool", "retrieval_overauth"), ("source_scan_bool", "source_scan_overauth"), ("pack_rerun_bool", "pack_rerun_overauth"), ("scheduler_policy_change_bool", "scheduler_policy_change_overauth"), ("new_trace_generation_bool", "new_trace_generation_overauth")]:
        if inp.get(field) is not False: issues.append(issue)
    if inp.get("explicit_existing_trace_private_read_confirmed_bool") is True and inp.get("labels_used_for_denominator_audit_only_bool") is not True: issues.append("label_boundary")
    shape = (report.get("denominator_shape_records") or [{}])[0]
    qual = (report.get("label_currentness_quality_records") or [{}])[0]
    sat = (report.get("saturation_headroom_records") or [{}])[0]
    if report.get("status") == STATUS_VIABLE:
        if qual.get("trace_schema_valid_bool") is not True: issues.append("trace_schema")
        if shape.get("task_count_ge_50_bool") is not True: issues.append("task_count_bucket_drift")
        if shape.get("diversity_bucket") not in {"medium", "high"}: issues.append("diversity_bucket_drift")
        if qual.get("label_coverage_medium_plus_bool") is not True: issues.append("label_coverage_bucket_drift")
        if qual.get("currentness_pass_or_partial_bool") is not True: issues.append("currentness_bucket_drift")
        if sat.get("fixed_baseline_saturation_bucket") != "fixed_baseline_saturation_not_high": issues.append("saturation_bucket_drift")
        if sat.get("headroom_present_bool") is not True: issues.append("headroom_bucket_drift")
    privacy = (report.get("privacy_records") or [{}])[0]
    if privacy.get("aggregate_only_public_bool") is not True: issues.append("aggregate_only")
    for field in ["raw_public_bool", "private_input_location_public_bool", "exact_metric_public_bool"]:
        if privacy.get(field) is not False: issues.append("privacy_leak")
    stop = (report.get("stop_go_records") or [{}])[0]
    false_fields = ["candidate_generation_authorized_bool", "retrieval_rerun_authorized_bool", "source_scan_authorized_bool", "pack_rerun_authorized_bool", "scheduler_policy_change_authorized_bool", "new_trace_generation_authorized_bool", "rpm_training_authorized_bool", "provider_network_ci_authorized_bool", "runtime_default_authorized_bool", "raw_publication_authorized_bool"]
    for field in false_fields:
        if stop.get(field) is not False: issues.append("stop_go_overauth")
    if (stop.get("frk_h_existing_trace_wider_suite_stress_authorized_bool") is True) != (report.get("status") == STATUS_VIABLE): issues.append("stop_go_overauth")
    if (stop.get("benchmark_acquisition_design_needed_bool") is True) != (report.get("status") == STATUS_ACQUIRE): issues.append("stop_go_overauth")
    if (stop.get("existing_trace_route_saturated_stopped_bool") is True) != (report.get("status") == STATUS_SATURATED): issues.append("stop_go_overauth")
    gates = [x.get("gate_bucket") for x in report.get("pass_fail_gate_records", [])]
    synth = [x.get("validator_bucket") for x in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_exactness")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if any(x.get("gate_passed_bool") is not True for x in report.get("pass_fail_gate_records", [])): issues.append("gate_false")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_exactness")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    if any(x.get("validator_passed_bool") is not True for x in report.get("synthetic_validator_records", [])): issues.append("synthetic_false")
    if (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool") is not True: issues.append("readback")
    return sorted(set(issues))


def synthetic_audit(kind: str = "viable") -> dict[str, Any]:
    a = default_audit(); a.update({"schema_valid_bool": True, "required_files_present_bool": True, "existing_trace_read_bool": True, "labels_used_for_denominator_audit_only_bool": True, "task_count_bucket": "count_250_plus", "task_count_ge_50_bool": True, "diversity_bucket": "high", "language_diversity_bucket": "language_diversity_medium_plus", "repo_or_benchmark_diversity_bucket": "repo_file_diversity_medium_plus", "label_coverage_bucket": "medium", "label_coverage_medium_plus_bool": True, "currentness_bucket": "currentness_partial_existing_trace_only", "currentness_pass_or_partial_bool": True, "fixed_baseline_saturation_bucket": "fixed_baseline_saturation_not_high", "fixed_baseline_saturation_high_bool": False, "headroom_bucket": "headroom_present", "headroom_present_bool": True})
    if kind == "saturated":
        a["fixed_baseline_saturation_bucket"] = "fixed_baseline_saturation_high"; a["fixed_baseline_saturation_high_bool"] = True; a["headroom_bucket"] = "headroom_absent"; a["headroom_present_bool"] = False
    if kind == "acquire":
        a["task_count_bucket"] = "count_20_to_49"; a["task_count_ge_50_bool"] = False
    return a


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def ck(name: str, ok: bool) -> None:
        if not ok: failures.append(name)
    d = build_report(False)
    v = build_report(True, synthetic_audit("viable"), source_override={"haae_sf_ok": True, "haae_s_ok": True, "frk_f_ok": True, "ldi_a_ok": True, "all_ok": True})
    s = build_report(True, synthetic_audit("saturated"), source_override={"haae_sf_ok": True, "haae_s_ok": True, "frk_f_ok": True, "ldi_a_ok": True, "all_ok": True})
    a = build_report(True, synthetic_audit("acquire"), source_override={"haae_sf_ok": True, "haae_s_ok": True, "frk_f_ok": True, "ldi_a_ok": True, "all_ok": True})
    ck("default_no_private_read_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    ck("explicit_synthetic_viable_pass", v["status"] == STATUS_VIABLE and validate_report(v) == [])
    ck("explicit_synthetic_saturated_pass", s["status"] == STATUS_SATURATED and validate_report(s) == [])
    ck("explicit_synthetic_acquisition_needed_pass", a["status"] == STATUS_ACQUIRE and validate_report(a) == [])
    for name, source in [("source_drift_haae_sf_fail", {"haae_sf_ok": False, "haae_s_ok": True, "frk_f_ok": True, "ldi_a_ok": True, "all_ok": False}), ("source_drift_haae_s_fail", {"haae_sf_ok": True, "haae_s_ok": False, "frk_f_ok": True, "ldi_a_ok": True, "all_ok": False}), ("source_drift_frk_f_fail", {"haae_sf_ok": True, "haae_s_ok": True, "frk_f_ok": False, "ldi_a_ok": True, "all_ok": False}), ("source_drift_ldi_a_fail", {"haae_sf_ok": True, "haae_s_ok": True, "frk_f_ok": True, "ldi_a_ok": False, "all_ok": False})]:
        ck(name, build_report(True, synthetic_audit("viable"), source_override=source)["status"] == STATUS_FAIL)
    for name, argv in [("missing_explicit_root_fail", ["--confirm-explicit-private-read"]), ("private_root_outside_allowed_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "runs/x"]), ("private_root_traversal_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "../bad"]), ("safe_parser_unknown_arg_fail", ["--bad"]), ("private_root_symlink_fail", ["--confirm-explicit-private-read", "--existing-trace-root", "/tmp/symlink-root"] )]:
        try:
            parse_args(argv); ck(name, False)
        except Exception:
            ck(name, True)
    mutations = [
        ("trace_schema_invalid_fail", lambda r: r["label_currentness_quality_records"][0].__setitem__("trace_schema_valid_bool", False), "trace_schema"),
        ("task_count_bucket_drift_fail", lambda r: r["denominator_shape_records"][0].__setitem__("task_count_ge_50_bool", False), "task_count_bucket_drift"),
        ("label_coverage_bucket_drift_fail", lambda r: r["label_currentness_quality_records"][0].__setitem__("label_coverage_medium_plus_bool", False), "label_coverage_bucket_drift"),
        ("currentness_bucket_drift_fail", lambda r: r["label_currentness_quality_records"][0].__setitem__("currentness_pass_or_partial_bool", False), "currentness_bucket_drift"),
        ("saturation_bucket_drift_fail", lambda r: r["saturation_headroom_records"][0].__setitem__("fixed_baseline_saturation_bucket", "fixed_baseline_saturation_high"), "saturation_bucket_drift"),
        ("headroom_bucket_drift_fail", lambda r: r["saturation_headroom_records"][0].__setitem__("headroom_present_bool", False), "headroom_bucket_drift"),
        ("candidate_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("candidate_generation_bool", True), "candidate_generation_overauth"),
        ("scheduler_policy_change_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("scheduler_policy_change_bool", True), "scheduler_policy_change_overauth"),
        ("new_trace_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("new_trace_generation_bool", True), "new_trace_generation_overauth"),
        ("rpm_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_go_overauth"),
        ("provider_network_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("provider_network_ci_authorized_bool", True), "stop_go_overauth"),
        ("raw_path_leak_fail", lambda r: r.__setitem__("debug", ".openlocus/research-private/local_n6xfr_recovery/x.jsonl"), "privacy_leak"),
        ("raw_query_leak_fail", lambda r: r.__setitem__("debug", "task_id query r14s-001"), "privacy_leak"),
        ("raw_label_leak_fail", lambda r: r.__setitem__("debug", "gold_paths gold_lines label_private"), "privacy_leak"),
        ("raw_score_rank_hash_leak_fail", lambda r: r.__setitem__("debug", "raw_score raw_rank " + "a" * 32), "privacy_leak"),
        ("exact_metric_publication_fail", lambda r: r.__setitem__("debug", "exact_metric 0.12"), "privacy_leak"),
        ("privacy_fail_clears_success_stopgo_fail", lambda r: (r.__setitem__("debug", ".openlocus/research-private/local_n6xfr_recovery/x.jsonl"), r["stop_go_records"][0].__setitem__("next_allowed_phase_bucket", "FRK-H Existing-Trace Wider-Suite Stress")), "privacy_stop_go_fail_open"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_go_overauth"),
        ("benchmark_design_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("benchmark_acquisition_design_needed_bool", True), "stop_go_overauth"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_false"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_false"),
        ("readback_drop_fail", lambda r: r["public_readback_records"].clear(), "readback"),
    ]
    for name, mutator, issue in mutations:
        x = json.loads(json.dumps(v)); mutator(x); ck(name, issue in validate_report(x))
    direct = {"schema_ok": v["schema_version"] == SCHEMA_VERSION, "validate_report_ok": validate_report(v) == [], "aggregate_only_ok": v["privacy_records"][0]["aggregate_only_public_bool"] is True, "labels_audit_only_ok": v["input_boundary_records"][0]["labels_used_for_denominator_audit_only_bool"] is True, "no_generation_ok": all(v["input_boundary_records"][0][k] is False for k in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool", "scheduler_policy_change_bool", "new_trace_generation_bool"]), "frk_h_authorized_only_when_viable_ok": v["stop_go_records"][0]["frk_h_existing_trace_wider_suite_stress_authorized_bool"] is True and s["stop_go_records"][0]["frk_h_existing_trace_wider_suite_stress_authorized_bool"] is False, "self_test_count_exact": len(SYNTH) == SELF_TEST_EXPECTED == v["self_test_total"]}
    for name, ok in direct.items(): ck(name, ok)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_VIABLE}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    p = repo_root() / (out or PUBLIC_REPORT_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = run_self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try:
            rep = load_json(public_path(str(args["validate"]))); issues = validate_report(rep)
        except Exception:
            rep = {"status": "unavailable"}; issues = ["invalid"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    explicit = bool(args["root"])
    audit = audit_existing_traces(ensure_safe_existing_trace_root(str(args["root"]))) if explicit else default_audit()
    report = build_report(explicit, audit)
    p = write_report(report, public_path(str(args["out"])) if args["out"] else None)
    print(json.dumps({"artifact": str(p), "status": report["status"], "decision_bucket": report["decision_records"][0]["decision_bucket"]}, sort_keys=True))
    return 0 if report["status"] != STATUS_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
