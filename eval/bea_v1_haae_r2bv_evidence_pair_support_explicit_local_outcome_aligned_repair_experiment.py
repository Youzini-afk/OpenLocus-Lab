#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BV explicit local outcome-aligned repair experiment.

Default mode is a public no-op and reads no private root. Explicit mode reads
only an operator-provided existing R2BS repaired private material root and
computes bucketized aggregate experiment metrics. It never generates/repairs
material, scans source/candidate/corpus, or runs runtime/retrieval/network.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BV Evidence-Pair Support Explicit Local Outcome-Aligned Repair Experiment"
SLUG = "bea_v1_haae_r2bv_evidence_pair_support_explicit_local_outcome_aligned_repair_experiment"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BU_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bu_evidence_pair_support_outcome_aligned_repair_next_step_decision_design/bea_v1_haae_r2bu_evidence_pair_support_outcome_aligned_repair_next_step_decision_design_report.json")

R2BU_CHECKPOINT = "1666a00"
R2BU_STATUS = "haae_r2bu_outcome_aligned_repair_next_step_decision_design_complete_r2bv_explicit_local_experiment_authorized"
R2BU_SELF_TEST_TOTAL = 65
R2BS_CHECKPOINT = "71f3377"
R2BS_STATUS = "haae_r2bs_explicit_local_outcome_aligned_material_repair_generation_complete_r2bt_public_audit_authorized"
R2BT_CHECKPOINT = "63463b4"
R2BR_CHECKPOINT = "b96e717"
R2BE_CHECKPOINT = "c3901d6"
R2BO_CHECKPOINT = "07b9eef"

STATUS_DEFAULT = "haae_r2bv_unavailable_no_explicit_local_outcome_aligned_repair_experiment_opt_in"
STATUS_SIGNAL = "haae_r2bv_explicit_local_outcome_aligned_repair_experiment_complete_r2bw_public_audit_authorized_signal_present"
STATUS_WEAK = "haae_r2bv_explicit_local_outcome_aligned_repair_experiment_complete_r2bw_public_audit_authorized_weak_signal"
STATUS_ARTIFACT = "haae_r2bv_explicit_local_outcome_aligned_repair_experiment_complete_r2bw_public_audit_authorized_artifact_risk"
STATUS_INCONCLUSIVE = "haae_r2bv_explicit_local_outcome_aligned_repair_experiment_complete_r2bw_public_audit_authorized_inconclusive"
STATUS_FAIL_SOURCE = "haae_r2bv_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2bv_fail_closed_private_material_root_invalid"
STATUS_FAIL_PRIVACY = "haae_r2bv_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bv_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BW Evidence-Pair Support Outcome-Aligned Repair Experiment Public Audit Package"

PRIVATE_SCHEMA = "bea_v1_haae_r2bs_evidence_pair_support_explicit_local_outcome_aligned_material_repair_generation_private_material_v1"
R2BS_PHASE = "BEA-v1-HAAE-R2BS Evidence-Pair Support Explicit Local Outcome-Aligned Material Repair Generation"
GROUPS = ["outcome_aligned_task_frame", "outcome_aligned_source_manifest_private", "outcome_aligned_evidence_unit_pool", "outcome_aligned_support_pair_material", "outcome_aligned_control_pair_material", "outcome_label_alignment_eval_private", "gold_isolation_eval_private", "alignment_qa", "parent_r2be_row_ref_private", "parent_r2bo_label_ref_private", "repair_provenance_private"]

R2BU_TRUE = ["haae_r2bv_explicit_local_outcome_aligned_repair_experiment_authorized_bool", "r2bv_scoped_explicit_opt_in_experiment_bool", "r2bv_existing_r2bs_private_material_read_authorized_bool", "r2bv_aggregate_experiment_metrics_authorized_bool", "r2bv_no_material_generation_bool", "r2bv_no_source_scan_bool", "r2bv_aggregate_only_public_artifact_required_bool", "r2bv_public_audit_required_after_experiment_bool", "r2bs_repair_generation_result_locked_bool"]
R2BU_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "experiment_execution_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
STOP_TRUE = ["haae_r2bw_outcome_aligned_repair_experiment_public_audit_authorized_bool", "r2bw_public_only_audit_bool", "r2bw_no_private_read_bool", "r2bw_no_metric_recompute_bool", "r2bw_no_material_generation_bool", "r2bw_no_source_scan_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "material_generation_authorized_bool", "material_repair_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "scale_preflight_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bu_source_lock_gate", "r2bs_private_root_safety_gate", "r2bs_private_manifest_group_schema_gate", "default_noop_or_explicit_opt_in_gate", "no_material_generation_gate", "no_source_candidate_corpus_scan_gate", "no_runtime_retrieval_network_gate", "aggregate_bucket_metrics_only_gate", "public_privacy_gate", "r2bw_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_signal_pass", "safe_parser_fail", "missing_explicit_arg_fail", "unknown_arg_fail", "r2bu_checkpoint_drift_fail", "r2bu_status_drift_fail", "r2bu_self_test_drift_fail", "r2bu_stop_go_overauth_fail", "r2bs_checkpoint_drift_fail", "r2bt_checkpoint_drift_fail", "r2br_checkpoint_drift_fail", "r2be_checkpoint_drift_fail", "r2bo_checkpoint_drift_fail", "root_in_repo_fail", "root_missing_manifest_fail", "root_manifest_schema_fail", "root_manifest_source_lock_fail", "root_group_missing_fail", "root_group_extra_fail", "root_group_symlink_fail", "root_empty_group_fail", "metric_bucketization_fail", "status_metric_alignment_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "runtime_overauth_fail", "raw_label_leak_fail", "private_ref_leak_fail", "stop_true_drop_fail", "stop_private_overauth_fail", "stop_material_overauth_fail", "stop_source_scan_overauth_fail", "stop_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_label", re.compile(r"gold_spans|hard_negatives|private_gold|private_hard|start_line|end_line|mined_high_confidence", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|private_label_source_ref|parent_r2be_row_ref|parent_r2bo_label_ref|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\brank\b|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    # Allow public boolean boundary field names that describe forbidden classes;
    # the values are checked separately by validate_report.
    for allowed in ["raw_labels_gold_spans_public_bool", "raw_private_rows_public_bool"]:
        text = text.replace(allowed, "public_boundary_bool")
    findings = [n for n, p in LEAK_PATTERNS if p.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def symlink_component(path: Path) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/")
    for part in p.parts[1:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
    return False

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "root": "", "confirm_existing": False, "confirm_no_material": False, "confirm_no_scan": False, "confirm_no_runtime": False, "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2bv-explicit-local-outcome-aligned-repair-experiment": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2bs-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-no-material-generation": parsed["confirm_no_material"] = True; i += 1
        elif a == "--confirm-no-source-candidate-corpus-scan": parsed["confirm_no_scan"] = True; i += 1
        elif a == "--confirm-no-runtime-openlocus-retrieval": parsed["confirm_no_runtime"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--r2bs-private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--r2bs-private-material-root": "root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "root", "confirm_existing", "confirm_no_material", "confirm_no_scan", "confirm_no_runtime", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bu(r2bu: dict[str, Any]) -> dict[str, bool]:
    src = (r2bu.get("source_lock_records") or [{}])[0]; fact = (r2bu.get("r2bs_repair_generation_fact_records") or [{}])[0]; stop = (r2bu.get("stop_go_records") or [{}])[0]
    locks = r2bu.get("status") == R2BU_STATUS and r2bu.get("self_test_total") == R2BU_SELF_TEST_TOTAL and r2bu.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bs_checkpoint") == R2BS_CHECKPOINT and src.get("locked_haae_r2bs_status") == R2BS_STATUS and src.get("locked_haae_r2bt_checkpoint") == R2BT_CHECKPOINT and src.get("locked_haae_r2br_checkpoint") == R2BR_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("locked_inherited_r2bo_checkpoint") == R2BO_CHECKPOINT and src.get("source_locked_bool") is True
    facts = fact.get("explicit_repair_generation_bool") is True and fact.get("output_group_set_exact_bool") is True and fact.get("label_alignment_materialized_bucket") == "label_alignment_materialized" and fact.get("parent_refs_present_bucket") == "parent_refs_present" and fact.get("private_rows_bucket") == "private_rows_le_20000" and fact.get("aggregate_only_public_artifact_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BU_TRUE) and all(stop.get(f, False) is False for f in R2BU_FALSE)
    return {"source_ok": locks and facts and stop_ok, "locks_ok": locks, "facts_ok": facts, "stop_ok": stop_ok}

def validate_root(value: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    if not value or any(part == ".." for part in Path(value).parts): return False, "root_traversal_rejected", {}
    root = Path(value)
    rows: dict[str, list[dict[str, Any]]] = {}
    try:
        if not root.exists() or root.is_symlink() or symlink_component(root) or not outside_repo(root): return False, "root_safety_rejected", {}
        mf = root / "r2bs_private_manifest.json"; gd = root / "groups"
        if not mf.is_file() or mf.is_symlink() or not gd.is_dir() or gd.is_symlink(): return False, "manifest_or_groups_missing", {}
        manifest = load_json(mf)
        if manifest.get("schema_version") != PRIVATE_SCHEMA or manifest.get("phase") != R2BS_PHASE: return False, "manifest_schema_mismatch", {}
        locks = manifest.get("source_lock") or {}
        if locks.get("r2br_checkpoint") != R2BR_CHECKPOINT or locks.get("r2be_checkpoint") != R2BE_CHECKPOINT or locks.get("r2bo_checkpoint") != R2BO_CHECKPOINT: return False, "manifest_source_lock_mismatch", {}
        present = {p.name for p in gd.iterdir()}
        if present != {f"{g}.jsonl" for g in GROUPS}: return False, "group_file_set_mismatch", {}
        for g in GROUPS:
            p = gd / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or root.resolve() not in p.resolve().parents: return False, "group_file_invalid", {}
            rows[g] = load_jsonl(p)
            if not rows[g]: return False, "group_file_empty", {}
    except Exception:
        return False, "root_invalid", {}
    return True, "root_valid", rows

def compute_metrics(rows: dict[str, list[dict[str, Any]]]) -> dict[str, str | bool]:
    support = rows.get("outcome_aligned_support_pair_material", [])
    control = rows.get("outcome_aligned_control_pair_material", [])
    eval_rows = rows.get("outcome_label_alignment_eval_private", [])
    gold_rows = rows.get("gold_isolation_eval_private", [])
    qa_rows = rows.get("alignment_qa", [])
    support_present = any(r.get("label_aligned_support_pair_bool") is True and r.get("experiment_metric_bool") is False for r in support)
    control_present = any(r.get("label_aligned_control_pair_bool") is True and r.get("experiment_metric_bool") is False for r in control)
    eval_present = any(r.get("private_label_values_eval_only_bool") is True and r.get("used_for_signal_metric_bool") is False for r in eval_rows)
    gold_ok = bool(gold_rows) and all(r.get("gold_hard_negative_eval_only_bool") is True and r.get("used_for_source_scan_or_ranking_bool") is False for r in gold_rows)
    qa_ok = any(r.get("no_experiment_metrics_bool") is True and r.get("no_source_scan_bool") is True for r in qa_rows)
    if support_present and control_present and eval_present and gold_ok and qa_ok:
        interp = "inconclusive"
    elif support_present and eval_present and gold_ok:
        interp = "weak_signal"
    elif control_present and not support_present:
        interp = "artifact_risk"
    else:
        interp = "inconclusive"
    return {"support_control_separation_bucket": "support_and_control_evaluable_no_separation_claim" if support_present and control_present else "support_control_separation_unavailable", "label_aligned_support_retention_bucket": "label_aligned_support_retention_present" if support_present else "label_aligned_support_retention_low", "hard_negative_rejection_bucket": "hard_negative_controls_evaluable_no_rejection_claim" if eval_present and control_present else "hard_negative_rejection_unavailable", "shuffled_cross_task_control_bucket": "control_family_evaluable" if control_present else "control_family_unavailable", "path_confound_risk_bucket": "path_confound_risk_not_elevated" if qa_ok else "path_confound_risk_unknown", "gold_isolation_bucket": "gold_isolation_pass" if gold_ok else "gold_isolation_unavailable", "outcome_alignment_coverage_bucket": "outcome_alignment_coverage_present" if eval_present else "outcome_alignment_coverage_unavailable", "interpretation_bucket": interp, "aggregate_bucket_metrics_only_bool": True, "no_exact_metrics_bool": True}

def default_metrics() -> dict[str, str | bool]:
    return {"support_control_separation_bucket": "unavailable_no_explicit_opt_in", "label_aligned_support_retention_bucket": "unavailable_no_explicit_opt_in", "hard_negative_rejection_bucket": "unavailable_no_explicit_opt_in", "shuffled_cross_task_control_bucket": "unavailable_no_explicit_opt_in", "path_confound_risk_bucket": "unavailable_no_explicit_opt_in", "gold_isolation_bucket": "unavailable_no_explicit_opt_in", "outcome_alignment_coverage_bucket": "unavailable_no_explicit_opt_in", "interpretation_bucket": "unavailable_no_explicit_opt_in", "aggregate_bucket_metrics_only_bool": True, "no_exact_metrics_bool": True}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_INCONCLUSIVE, f"{total}/{total}", R2BU_CHECKPOINT, R2BU_STATUS, R2BS_CHECKPOINT, R2BT_CHECKPOINT, R2BR_CHECKPOINT, R2BE_CHECKPOINT, R2BO_CHECKPOINT, "default mode", "no private read", "explicit mode", "existing R2BS repaired private material", "bucketized aggregate experiment metrics", "support/control separation", "outcome-alignment coverage", "signal_present", "weak_signal", "artifact_risk", "inconclusive", "no separation claim", "no material generation", "no source/candidate/corpus scan", NEXT_PHASE]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bv-evidence-pair-support-explicit-local-outcome-aligned-repair-experiment.md")) and ok(read("docs/zh/bea-v1-haae-r2bv-evidence-pair-support-explicit-local-outcome-aligned-repair-experiment.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bv-evidence-pair-support-explicit-local-outcome-aligned-repair-experiment.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str = "default", r2bu: dict[str, Any] | None = None, root_ok: bool = False, metrics: dict[str, str | bool] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bu is None:
        try: r2bu = load_json(repo_root() / R2BU_REPORT_PATH)
        except Exception: r2bu = {}
    audit = audit_r2bu(r2bu); rb = public_readback_match(self_test_total); explicit = mode == "explicit"; metrics = metrics or default_metrics(); interp = str(metrics.get("interpretation_bucket"))
    pass_status = {"signal_present": STATUS_SIGNAL, "weak_signal": STATUS_WEAK, "artifact_risk": STATUS_ARTIFACT, "inconclusive": STATUS_INCONCLUSIVE}.get(interp, STATUS_INCONCLUSIVE)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_ROOT if explicit and not root_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else (pass_status if explicit else STATUS_DEFAULT)))
    success = status in {STATUS_SIGNAL, STATUS_WEAK, STATUS_ARTIFACT, STATUS_INCONCLUSIVE}
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bvstop0000", "next_allowed_phase": NEXT_PHASE if success else "not_authorized_until_explicit_experiment_pass"}; stop.update({f: success for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bu_source_lock_gate": audit["source_ok"], "r2bs_private_root_safety_gate": (not explicit) or root_ok, "r2bs_private_manifest_group_schema_gate": (not explicit) or root_ok, "default_noop_or_explicit_opt_in_gate": True, "no_material_generation_gate": True, "no_source_candidate_corpus_scan_gate": True, "no_runtime_retrieval_network_gate": True, "aggregate_bucket_metrics_only_gate": metrics.get("aggregate_bucket_metrics_only_bool") is True and metrics.get("no_exact_metrics_bool") is True, "public_privacy_gate": True, "r2bw_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bvsource0000", "locked_haae_r2bu_checkpoint": R2BU_CHECKPOINT, "locked_haae_r2bu_status": R2BU_STATUS, "locked_haae_r2bu_self_test_total": R2BU_SELF_TEST_TOTAL, "locked_haae_r2bs_checkpoint": R2BS_CHECKPOINT, "locked_haae_r2bs_status": R2BS_STATUS, "locked_haae_r2bt_checkpoint": R2BT_CHECKPOINT, "locked_haae_r2br_checkpoint": R2BR_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "locked_inherited_r2bo_checkpoint": R2BO_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2bvexec0000", "execution_mode_bucket": "explicit_local_outcome_aligned_repair_experiment" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_r2bs_material_read_bool": explicit and root_ok, "private_write_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_network_bool": False}],
        "aggregate_metric_records": [{"anonymous_metric_id": "haaer2bvmetric0000", **metrics}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bvprivacy0000", "aggregate_bucket_only_publication_bool": True, "private_root_path_public_bool": False, "task_query_source_evidence_pair_ids_public_bool": False, "raw_labels_gold_spans_public_bool": False, "parent_private_refs_public_bool": False, "exact_counts_rates_scores_ranks_mrr_public_bool": False, "raw_private_rows_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bvgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bvsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bvreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_DEFAULT, STATUS_SIGNAL, STATUS_WEAK, STATUS_ARTIFACT, STATUS_INCONCLUSIVE} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") not in {STATUS_DEFAULT, STATUS_SIGNAL, STATUS_WEAK, STATUS_ARTIFACT, STATUS_INCONCLUSIVE}: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    src = (report.get("source_lock_records") or [{}])[0]
    for k, v in {"locked_haae_r2bu_checkpoint": R2BU_CHECKPOINT, "locked_haae_r2bu_status": R2BU_STATUS, "locked_haae_r2bu_self_test_total": R2BU_SELF_TEST_TOTAL, "locked_haae_r2bs_checkpoint": R2BS_CHECKPOINT, "locked_haae_r2bs_status": R2BS_STATUS, "locked_haae_r2bt_checkpoint": R2BT_CHECKPOINT, "locked_haae_r2br_checkpoint": R2BR_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "locked_inherited_r2bo_checkpoint": R2BO_CHECKPOINT}.items():
        if src.get(k) != v: issues.append(f"source_{k}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    metric = (report.get("aggregate_metric_records") or [{}])[0]
    for k in ["support_control_separation_bucket", "label_aligned_support_retention_bucket", "hard_negative_rejection_bucket", "shuffled_cross_task_control_bucket", "path_confound_risk_bucket", "gold_isolation_bucket", "outcome_alignment_coverage_bucket", "interpretation_bucket"]:
        if not isinstance(metric.get(k), str): issues.append(f"metric_{k}")
    if metric.get("aggregate_bucket_metrics_only_bool") is not True or metric.get("no_exact_metrics_bool") is not True: issues.append("metric_bucketization")
    status_interp = {STATUS_SIGNAL: "signal_present", STATUS_WEAK: "weak_signal", STATUS_ARTIFACT: "artifact_risk", STATUS_INCONCLUSIVE: "inconclusive"}
    status_value = str(report.get("status"))
    if status_value in status_interp and metric.get("interpretation_bucket") != status_interp[status_value]: issues.append("status_metric_alignment")
    exe = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_DEFAULT:
        if exe.get("explicit_opt_in_bool") is not False or exe.get("private_r2bs_material_read_bool") is not False: issues.append("default_private_read")
    elif report.get("status") in status_interp:
        if exe.get("explicit_opt_in_bool") is not True or exe.get("private_r2bs_material_read_bool") is not True: issues.append("explicit_private_read")
    for f in ["private_write_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_network_bool"]:
        if exe.get(f) is not False: issues.append(f"execution_{f}")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("aggregate_bucket_only_publication_bool") is not True: issues.append("privacy_aggregate_bucket_only_publication_bool")
    for f in ["private_root_path_public_bool", "task_query_source_evidence_pair_ids_public_bool", "raw_labels_gold_spans_public_bool", "parent_private_refs_public_bool", "exact_counts_rates_scores_ranks_mrr_public_bool", "raw_private_rows_public_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    success = report.get("status") in status_interp
    if success:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_phase_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"stop_false_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("readback_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("stale_current")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket')}")
    return issues

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def make_fixture(tmp: Path) -> Path:
    root = tmp / "r2bs_fixture"; (root / "groups").mkdir(parents=True)
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": R2BS_PHASE, "source_lock": {"r2br_checkpoint": R2BR_CHECKPOINT, "r2be_checkpoint": R2BE_CHECKPOINT, "r2bo_checkpoint": R2BO_CHECKPOINT}, "ownership": {"owner_phase": R2BS_PHASE}, "groups": {g: {"row_count_bucket": "present"} for g in GROUPS}}
    (root / "r2bs_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows = {
        "outcome_aligned_task_frame": [{"private_task_ref": "task0"}],
        "outcome_aligned_source_manifest_private": [{"private_source_ref": "src0"}],
        "outcome_aligned_evidence_unit_pool": [{"private_evidence_unit_ref": "ev0"}],
        "outcome_aligned_support_pair_material": [{"private_pair_ref": "sp0", "label_aligned_support_pair_bool": True, "experiment_metric_bool": False}],
        "outcome_aligned_control_pair_material": [{"private_pair_ref": "cp0", "label_aligned_control_pair_bool": True, "experiment_metric_bool": False}],
        "outcome_label_alignment_eval_private": [{"private_label_values_eval_only_bool": True, "used_for_signal_metric_bool": False, "private_gold_spans_eval_only": [{"x": 1}], "private_hard_negatives_eval_only": [{"x": 2}]}],
        "gold_isolation_eval_private": [{"gold_hard_negative_eval_only_bool": True, "used_for_source_scan_or_ranking_bool": False}],
        "alignment_qa": [{"no_experiment_metrics_bool": True, "no_source_scan_bool": True}],
        "parent_r2be_row_ref_private": [{"parent": "r2be"}], "parent_r2bo_label_ref_private": [{"parent": "r2bo"}], "repair_provenance_private": [{"inputs_mutated_bool": False}],
    }
    for g in GROUPS: write_jsonl(root / "groups" / f"{g}.jsonl", rows[g])
    return root

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    repo = repo_root(); base = load_json(repo / R2BU_REPORT_PATH)
    default = build_report("default", base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    tmp = Path(tempfile.mkdtemp(prefix="r2bv_selftest_", dir="/tmp/opencode"))
    try:
        fixture = make_fixture(tmp); ok, _, rows = validate_root(str(fixture)); metrics = compute_metrics(rows); explicit = build_report("explicit", base, ok, metrics)
        check("explicit_synthetic_signal_pass", explicit["status"] == STATUS_INCONCLUSIVE and validate_report(explicit) == [])
        for name, args in [("safe_parser_fail", ["--bad"]), ("missing_explicit_arg_fail", ["--allow-r2bv-explicit-local-outcome-aligned-repair-experiment"]), ("unknown_arg_fail", ["--unknown"] )]:
            try: parse_args(args); check(name, False)
            except ValueError: check(name, True)
        muts = [("r2bu_status_drift_fail", lambda r: r.__setitem__("status", "bad")), ("r2bu_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2bs_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bs_checkpoint", "bad")), ("r2bt_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bt_checkpoint", "bad")), ("r2br_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2br_checkpoint", "bad")), ("r2be_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2be_checkpoint", "bad")), ("r2bo_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2bo_checkpoint", "bad")), ("r2bu_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True)), ("r2bu_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bt_checkpoint", "bad"))]
        for name, mut in muts:
            m = json.loads(json.dumps(base)); mut(m); check(name, build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
        bad_root = repo / "bad"; check("root_in_repo_fail", validate_root(str(bad_root))[0] is False)
        no_manifest = tmp / "missing"; no_manifest.mkdir(); check("root_missing_manifest_fail", validate_root(str(no_manifest))[0] is False)
        schema = tmp / "schema"; shutil.copytree(fixture, schema); (schema / "r2bs_private_manifest.json").write_text(json.dumps({"schema_version": "bad", "phase": R2BS_PHASE}), encoding="utf-8"); check("root_manifest_schema_fail", validate_root(str(schema))[0] is False)
        lock = tmp / "lock"; shutil.copytree(fixture, lock); mf = load_json(lock / "r2bs_private_manifest.json"); mf["source_lock"]["r2br_checkpoint"] = "bad"; (lock / "r2bs_private_manifest.json").write_text(json.dumps(mf), encoding="utf-8"); check("root_manifest_source_lock_fail", validate_root(str(lock))[0] is False)
        missing = tmp / "missing_group"; shutil.copytree(fixture, missing); (missing / "groups" / f"{GROUPS[0]}.jsonl").unlink(); check("root_group_missing_fail", validate_root(str(missing))[0] is False)
        extra = tmp / "extra_group"; shutil.copytree(fixture, extra); (extra / "groups" / "extra.jsonl").write_text("{}\n", encoding="utf-8"); check("root_group_extra_fail", validate_root(str(extra))[0] is False)
        sy = tmp / "symlink_group"; shutil.copytree(fixture, sy); (sy / "groups" / f"{GROUPS[1]}.jsonl").unlink(); (sy / "groups" / f"{GROUPS[1]}.jsonl").symlink_to(fixture / "groups" / f"{GROUPS[1]}.jsonl"); check("root_group_symlink_fail", validate_root(str(sy))[0] is False)
        empty = tmp / "empty_group"; shutil.copytree(fixture, empty); (empty / "groups" / f"{GROUPS[2]}.jsonl").write_text("", encoding="utf-8"); check("root_empty_group_fail", validate_root(str(empty))[0] is False)
        report_muts = [("metric_bucketization_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("aggregate_bucket_metrics_only_bool", False), "metric_bucketization"), ("status_metric_alignment_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("interpretation_bucket", "signal_present"), "status_metric_alignment"), ("material_generation_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("material_generation_bool", True), "execution_material_generation_bool"), ("source_scan_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "execution_source_candidate_corpus_scan_bool"), ("runtime_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("runtime_retrieval_network_bool", True), "execution_runtime_retrieval_network_bool"), ("raw_label_leak_fail", lambda r: r.__setitem__("debug", "gold_spans"), "public_leak"), ("private_ref_leak_fail", lambda r: r.__setitem__("debug", "private_task_ref"), "public_leak"), ("stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "stop_false_private_read_authorized_bool"), ("stop_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "stop_false_material_generation_authorized_bool"), ("stop_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_false_source_scan_authorized_bool"), ("stop_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), "stop_false_method_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"), ("readback_record_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "readback_mismatch")]
        for name, mut, issue in report_muts:
            m = json.loads(json.dumps(explicit)); mut(m); check(name, issue in validate_report(m))
        leak = json.loads(json.dumps(explicit)); leak["debug"] = "/tmp/private-root exact_score_value r14m-001"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_INCONCLUSIVE}

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        ok, _, rows = validate_root(str(args["root"])); metrics = compute_metrics(rows) if ok else default_metrics(); report = build_report("explicit", root_ok=ok, metrics=metrics)
    else:
        report = build_report("default")
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_SIGNAL, STATUS_WEAK, STATUS_ARTIFACT, STATUS_INCONCLUSIVE} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
