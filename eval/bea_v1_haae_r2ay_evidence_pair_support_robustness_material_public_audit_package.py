#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AY robustness material public audit package.

Public-only audit of the R2AX public artifact. R2AY does not read private
roots, /tmp, private material, diagnostics, source/candidate/corpus, runtime,
OpenLocus, retrieval, CI, network, provider, or clone paths.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AY Evidence-Pair Support Robustness Material Public Audit Package"
SLUG = "bea_v1_haae_r2ay_evidence_pair_support_robustness_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2AX_CHECKPOINT = "f3add65"
R2AX_STATUS = "haae_r2ax_explicit_local_robustness_material_generation_complete_r2ay_public_audit_authorized"
R2AX_SELF_TEST_TOTAL = 31
R2AX_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation/bea_v1_haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation_report.json")
R2AW_CHECKPOINT = "bc44454"
R2AW_STATUS = "haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_complete_r2ax_explicit_local_robustness_material_generation_authorized"
R2AN_CHECKPOINT = "93bba5f"

STATUS_PASS = "haae_r2ay_evidence_pair_support_robustness_material_public_audit_complete_r2az_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2ay_fail_closed_r2ax_source_or_artifact_mismatch"
STATUS_FAIL_AUDIT = "haae_r2ay_fail_closed_public_audit_boundary_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2ay_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2ay_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment"

R2AX_GROUPS = ["task_frame", "source_manifest_private", "base_evidence_unit_pool", "base_evidence_pair_material", "robustness_variant_material", "ablation_control_material", "hard_negative_control_material", "shuffled_mismatch_control_material", "outcome_eval_private", "material_qa", "source_material_manifest", "parent_r2an_row_ref_private"]
VARIANTS = ["single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control"]
R2AX_GATES = ["r2aw_source_lock_gate", "r2aw_stop_go_exact_gate", "default_noop_or_explicit_opt_in_gate", "root_safety_gate", "r2an_input_schema_group_gate", "r2an_pair_family_gate", "gold_eval_only_no_path_primary_gate", "generated_group_set_gate", "variant_set_gate", "bounds_gate", "material_generation_only_no_metrics_gate", "aggregate_only_public_gate", "r2ay_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2AX_SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "safe_parser_fail", "bad_r2aw_status_fail", "bad_r2aw_checkpoint_fail", "r2aw_stop_go_overauth_fail", "r2aw_stop_private_read_overauth_fail", "r2aw_synthetic_exact_set_fail", "missing_input_group_fail", "group_symlink_fail", "manifest_schema_fail", "missing_pair_family_fail", "gold_selection_fail", "path_primary_fail", "output_root_in_repo_fail", "nested_roots_fail", "nonempty_unowned_output_fail", "output_groups_symlink_fail", "missing_variant_fail", "missing_generated_group_fail", "bounds_drift_fail", "explicit_mode_drift_fail", "root_path_public_fail", "metrics_public_leak_fail", "stop_go_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail"]
R2AX_STOP_TRUE = ["haae_r2ay_evidence_pair_support_robustness_material_public_audit_authorized_bool", "r2ay_public_only_audit_bool", "r2ay_no_private_read_bool", "r2ay_no_metric_computation_bool"]
R2AX_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "private_diagnostics_read_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "new_candidate_generation_authorized_bool", "new_base_material_generation_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "scale_claim_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "method_winner_claim_authorized_bool", "winner_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2ax_source_lock_gate", "r2ax_explicit_generation_gate", "r2ax_generated_group_set_gate", "r2ax_variant_set_gate", "r2ax_bounds_gate", "r2ax_no_experiment_metrics_gate", "r2ax_privacy_boundary_gate", "r2ax_gate_synthetic_readback_exact_gate", "r2ax_stop_go_exact_gate", "r2ay_public_only_gate", "r2az_scoped_stop_go_gate", "no_broad_private_material_scan_runtime_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["audit_pass", "r2ax_checkpoint_drift_fail", "r2ax_status_drift_fail", "r2ax_self_test_drift_fail", "generated_group_drop_fail", "variant_drop_fail", "bounds_drift_fail", "metric_publication_drift_fail", "privacy_boundary_drift_fail", "r2ax_gate_drop_fail", "r2ax_gate_duplicate_fail", "r2ax_synthetic_drop_fail", "r2ax_synthetic_duplicate_fail", "r2ax_readback_drop_fail", "r2ax_readback_duplicate_fail", "r2ax_stop_private_read_overauth_fail", "r2ax_stop_material_generation_overauth_fail", "r2ax_stop_metric_overauth_fail", "r2ax_stop_mechanism_recompute_overauth_fail", "r2ax_stop_private_diagnostics_read_overauth_fail", "r2ax_stop_source_scan_overauth_fail", "r2ax_stop_scale_preflight_overauth_fail", "r2ax_stop_runtime_overauth_fail", "r2az_scoped_authorization_drift_fail", "r2az_broad_private_read_overauth_fail", "r2az_broad_experiment_metrics_overauth_fail", "r2az_private_write_overauth_fail", "r2az_material_generation_overauth_fail", "r2az_default_claim_overauth_fail", "r2az_raw_publication_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

R2AZ_TRUE = ["haae_r2az_evidence_pair_support_explicit_local_robustness_experiment_authorized_bool", "r2az_explicit_opt_in_required_bool", "r2az_existing_r2ax_private_material_read_authorized_bool", "r2az_aggregate_metrics_only_bool", "r2az_public_audit_required_bool"]
R2AZ_FALSE = ["r2ay_private_read_bool", "r2ay_private_write_bool", "r2ay_material_generation_bool", "r2ay_metric_computation_bool", "private_read_authorized_bool", "private_write_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "private_diagnostics_read_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "new_base_material_generation_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "candidate_scan_authorized_bool", "new_candidate_generation_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "method_winner_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "scale_preflight_authorized_bool", "raw_publication_authorized_bool"]

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|task_ref_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": ""}; i = 0
    while i < len(argv):
        if argv[i] == "--self-test": parsed["self_test"] = True; i += 1
        elif argv[i] in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed["validate" if argv[i] == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    return parsed
def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]; p = Path(value); resolved = p if p.is_absolute() else repo / p
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2ax(r2ax: dict[str, Any]) -> dict[str, bool]:
    src = (r2ax.get("source_lock_records") or [{}])[0]; mode = (r2ax.get("execution_mode_records") or [{}])[0]; mat = (r2ax.get("generated_material_records") or [{}])[0]; priv = (r2ax.get("privacy_boundary_records") or [{}])[0]; stop = (r2ax.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2ax.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2ax.get("synthetic_validator_records", [])]; read = r2ax.get("public_readback_records", [])
    source_ok = r2ax.get("status") == R2AX_STATUS and r2ax.get("self_test_total") == R2AX_SELF_TEST_TOTAL and r2ax.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2aw_checkpoint") == R2AW_CHECKPOINT and src.get("locked_haae_r2aw_status") == R2AW_STATUS and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("source_locked_bool") is True
    explicit_ok = mode.get("explicit_mode_executed_bool") is True and mode.get("private_output_write_bool") is True and mode.get("experiment_metrics_bool") is False and mode.get("source_candidate_corpus_scan_bool") is False and mode.get("runtime_openlocus_retrieval_bool") is False
    group_ok = set((mat.get("generated_group_presence_buckets") or {}).keys()) == set(R2AX_GROUPS) and all(v == "present" for v in (mat.get("generated_group_presence_buckets") or {}).values())
    variant_ok = set((mat.get("variant_presence_buckets") or {}).keys()) == set(VARIANTS) and all(v == "present" for v in (mat.get("variant_presence_buckets") or {}).values())
    bounds_ok = mat.get("bounds_bucket") == "bounds_satisfied" and mat.get("private_row_cap_bucket") == "under_private_row_cap" and mat.get("material_generation_only_no_experiment_metrics_bool") is True
    privacy_ok = priv.get("aggregate_only_public_artifact_bool") is True and priv.get("no_private_root_path_public_bool") is True and priv.get("no_raw_private_publication_bool") is True and priv.get("no_exact_metric_publication_bool") is True and priv.get("no_scores_rates_mrr_bool") is True
    integrity_ok = set(gates) == set(R2AX_GATES) and len(gates) == len(R2AX_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2AX_SYNTH) and len(synth) == len(R2AX_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2AX_STOP_TRUE) and all(stop.get(f, False) is False for f in R2AX_STOP_FALSE)
    return {"audit_ok": source_ok and explicit_ok and group_ok and variant_ok and bounds_ok and privacy_ok and integrity_ok and stop_ok, "source_ok": source_ok, "explicit_ok": explicit_ok, "group_ok": group_ok, "variant_ok": variant_ok, "bounds_ok": bounds_ok, "privacy_ok": privacy_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AX_CHECKPOINT, R2AX_STATUS, R2AW_CHECKPOINT, R2AN_CHECKPOINT, "public-only audit", "read only R2AX public artifact", "no private root", "no experiment metrics", "exact generated group set", "exact 8 variant set", "bounds satisfied", "aggregate-only", NEXT_PHASE, "R2AZ explicit local robustness experiment", "aggregate metrics only", "no material generation", "no source scan", "no runtime"]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    public_texts = [
        read("README.md"), root, read("docs/en/current-research-conclusions.md"), read("docs/zh/current-research-conclusions.md"),
        read("docs/en/research-log.md"), read("docs/zh/research-log.md"), read("docs/en/research-summary.md"), read("docs/zh/research-summary.md"),
        read("docs/en/bea-v1-haae-r2ax-evidence-pair-support-explicit-local-robustness-material-generation.md"),
        read("docs/zh/bea-v1-haae-r2ax-evidence-pair-support-explicit-local-robustness-material-generation.md"),
    ]
    def is_main_r2ax_line(line: str) -> bool:
        stripped = line.lstrip()
        return (
            stripped.startswith("BEA-v1-HAAE-R2AX")
            or stripped.startswith("Latest HAAE status: BEA-v1-HAAE-R2AX")
            or stripped.startswith("最新 HAAE 状态：BEA-v1-HAAE-R2AX")
            or stripped.startswith("`eval/bea_v1_haae_r2ax")
            or stripped.startswith("- **BEA-v1-HAAE-R2AX")
        )
    r2ax_count_lines = [line for text in public_texts for line in text.splitlines() if is_main_r2ax_line(line) and "self-test" in line]
    r2ax_count_guard = bool(r2ax_count_lines) and all("31/31" in line and "36/36" not in line for line in r2ax_count_lines)
    return {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2ay-evidence-pair-support-robustness-material-public-audit-package.md")) and ok(read("docs/zh/bea-v1-haae-r2ay-evidence-pair-support-robustness-material-public-audit-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2ay-evidence-pair-support-robustness-material-public-audit-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md")), "r2ax_prior_self_test_count_guard_bool": r2ax_count_guard}

def build_report(r2ax: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ax is None:
        try: r2ax = load_json(repo / R2AX_REPORT_PATH)
        except Exception: r2ax = {}
    audit = audit_r2ax(r2ax); rb = public_readback_match(self_test_total); rb["all_public_readback_match_bool"] = all(rb.values())
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_AUDIT if not all(audit[k] for k in ["explicit_ok", "group_ok", "variant_ok", "bounds_ok", "privacy_ok", "integrity_ok", "stop_ok"]) else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2aystop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass"}; stop.update({f: passed for f in R2AZ_TRUE}); stop.update({f: False for f in R2AZ_FALSE})
    gatevals = {"r2ax_source_lock_gate": audit["source_ok"], "r2ax_explicit_generation_gate": audit["explicit_ok"], "r2ax_generated_group_set_gate": audit["group_ok"], "r2ax_variant_set_gate": audit["variant_ok"], "r2ax_bounds_gate": audit["bounds_ok"], "r2ax_no_experiment_metrics_gate": audit["explicit_ok"] and audit["bounds_ok"], "r2ax_privacy_boundary_gate": audit["privacy_ok"], "r2ax_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2ax_stop_go_exact_gate": audit["stop_ok"], "r2ay_public_only_gate": True, "r2az_scoped_stop_go_gate": True, "no_broad_private_material_scan_runtime_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aysource0000", "locked_haae_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_haae_r2ax_status": R2AX_STATUS, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2ax_status_match_bool": audit["source_ok"], "r2ax_self_test_31_bool": audit["source_ok"], "r2ax_forbidden_scan_pass_bool": audit["source_ok"], "source_locked_bool": audit["source_ok"]}],
        "robustness_material_audit_records": [{"anonymous_material_audit_id": "haaer2ayaudit0000", "explicit_mode_true_bool": audit["explicit_ok"], "private_output_write_true_bool": audit["explicit_ok"], "no_experiment_metrics_bool": audit["explicit_ok"], "generated_group_set_exact_bool": audit["group_ok"], "variant_set_exact_bool": audit["variant_ok"], "bounds_satisfied_bool": audit["bounds_ok"], "aggregate_only_public_bool": audit["privacy_ok"]}],
        "public_only_boundary_records": [{"anonymous_boundary_id": "haaer2ayboundary0000", "public_only_audit_bool": True, "read_only_r2ax_public_artifact_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "material_recompute_bool": False, "experiment_metric_computation_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_openlocus_retrieval_ci_network_provider_clone_bool": False, "method_default_scale_raw_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aygate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aysynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2ayreadback0000", **rb}],
        "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for k in ["source_lock_records", "robustness_material_audit_records", "public_only_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if k not in report: issues.append(f"missing_{k}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_haae_r2ax_status": R2AX_STATUS, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    for f in ["r2ax_status_match_bool", "r2ax_self_test_31_bool", "r2ax_forbidden_scan_pass_bool", "source_locked_bool"]:
        if src.get(f) is not True: issues.append(f"source_{f}")
    aud = (report.get("robustness_material_audit_records") or [{}])[0]
    for f in ["explicit_mode_true_bool", "private_output_write_true_bool", "no_experiment_metrics_bool", "generated_group_set_exact_bool", "variant_set_exact_bool", "bounds_satisfied_bool", "aggregate_only_public_bool"]:
        if aud.get(f) is not True: issues.append(f"audit_{f}")
    boundary = (report.get("public_only_boundary_records") or [{}])[0]
    for f in ["public_only_audit_bool", "read_only_r2ax_public_artifact_bool"]:
        if boundary.get(f) is not True: issues.append(f"boundary_{f}")
    for f in ["private_root_read_bool", "private_material_read_bool", "material_recompute_bool", "experiment_metric_computation_bool", "source_candidate_corpus_scan_bool", "runtime_openlocus_retrieval_ci_network_provider_clone_bool", "method_default_scale_raw_claim_bool"]:
        if boundary.get(f) is not False: issues.append(f"boundary_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2az_stop_go_mismatch")
    for f in R2AZ_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in R2AZ_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not all(public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED))).values()): issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AX_REPORT_PATH)

    def check(n: str, c: bool) -> None:
        if not c:
            failures.append(n)

    passed = build_report(base)
    check("audit_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])

    source_mut = [
        ("r2ax_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2aw_checkpoint", "bad"), STATUS_FAIL_SOURCE),
        ("r2ax_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE),
        ("r2ax_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE),
        ("generated_group_drop_fail", lambda r: r["generated_material_records"][0]["generated_group_presence_buckets"].pop(R2AX_GROUPS[0]), STATUS_FAIL_AUDIT),
        ("variant_drop_fail", lambda r: r["generated_material_records"][0]["variant_presence_buckets"].pop(VARIANTS[0]), STATUS_FAIL_AUDIT),
        ("bounds_drift_fail", lambda r: r["generated_material_records"][0].__setitem__("bounds_bucket", "bad"), STATUS_FAIL_AUDIT),
        ("metric_publication_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("experiment_metrics_bool", True), STATUS_FAIL_AUDIT),
        ("privacy_boundary_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("no_raw_private_publication_bool", False), STATUS_FAIL_AUDIT),
        ("r2ax_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_AUDIT),
        ("r2ax_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_AUDIT),
        ("r2ax_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_AUDIT),
        ("r2ax_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_AUDIT),
        ("r2ax_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_AUDIT),
        ("r2ax_readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), STATUS_FAIL_AUDIT),
        ("r2ax_stop_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("experiment_metrics_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_mechanism_recompute_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("mechanism_recompute_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_private_diagnostics_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_diagnostics_read_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_broad_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_scale_preflight_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), STATUS_FAIL_AUDIT),
        ("r2ax_stop_runtime_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_execution_authorized_bool", True), STATUS_FAIL_AUDIT),
    ]
    for name, mut, status in source_mut:
        m = json.loads(json.dumps(base))
        mut(m)
        check(name, build_report(m)["status"] == status)

    report_mut = [
        ("r2az_scoped_authorization_drift_fail", lambda r: r["stop_go_records"][0].__setitem__(R2AZ_TRUE[0], False), f"stop_true_{R2AZ_TRUE[0]}"),
        ("r2az_broad_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"),
        ("r2az_broad_experiment_metrics_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("experiment_metrics_authorized_bool", True), "overauthorization_experiment_metrics_authorized_bool"),
        ("r2az_private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"),
        ("r2az_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"),
        ("r2az_default_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("default_claim_authorized_bool", True), "overauthorization_default_claim_authorized_bool"),
        ("r2az_raw_publication_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("raw_publication_authorized_bool", True), "overauthorization_raw_publication_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"),
        ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
    ]
    for name, mut, issue in report_mut:
        m = json.loads(json.dumps(passed))
        mut(m)
        check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed))
    leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"
    check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    try:
        with redirect_stderr(io.StringIO()):
            parse_args(["--private-root", "x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        res = run_self_test(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
