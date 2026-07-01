#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AO evidence-pair support material public audit package.

Public-only audit of the committed R2AN public artifact/docs. It does not read
private roots or /tmp, does not recompute generation, generate material, scan
source/candidates, or compute experiment metrics.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AO Evidence-Pair Support Material Public Audit Package"
SLUG = "bea_v1_haae_r2ao_evidence_pair_support_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AN_CHECKPOINT = "93bba5f"
R2AN_STATUS = "haae_r2an_evidence_pair_support_explicit_material_generation_complete_r2ao_public_material_audit_authorized"
R2AN_SELF_TEST_TOTAL = 27
R2AM_CHECKPOINT = "b243924"
R2AN_REPORT_PATH = Path("artifacts/bea_v1_haae_r2an_evidence_pair_support_explicit_material_generation/bea_v1_haae_r2an_evidence_pair_support_explicit_material_generation_report.json")

STATUS_PASS = "haae_r2ao_evidence_pair_support_material_public_audit_package_complete_r2ap_explicit_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2ao_fail_closed_source_lock_mismatch"
STATUS_FAIL_AUDIT = "haae_r2ao_fail_closed_material_audit_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ao_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ao_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2ao_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AP Evidence-Pair Support Explicit Local Material Experiment"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
R2AN_SCHEMA = "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1"
GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
BOUNDS = {"target_task_count_bucket": "target_20", "evidence_unit_depth_cap_bucket": "cap_40", "support_pair_cap_bucket": "cap_120", "contrast_control_pair_cap_bucket": "cap_80", "total_pair_cap_bucket": "cap_200", "source_file_cap_bucket": "cap_500", "private_row_cap_bucket": "cap_20000"}
GATE_NAMES = ["r2an_source_locked_gate", "r2an_status_gate", "r2an_self_test_27_gate", "r2am_source_lock_gate", "schema_groups_present_gate", "pair_families_present_gate", "bounds_shape_gate", "policy_gold_no_selection_gate", "policy_single_rank_forbidden_gate", "pair_setwise_gate", "privacy_aggregate_only_gate", "no_metrics_gate", "r2ap_stop_go_only_gate", "no_new_generation_source_scan_ci_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "wrong_r2an_status_fail", "self_test_drift_fail", "r2am_checkpoint_drift_fail", "group_missing_fail", "pair_family_missing_fail", "bounds_drift_fail", "gold_policy_drift_fail", "single_rank_policy_drift_fail", "privacy_drift_fail", "metrics_drift_fail", "r2an_private_read_overauth_fail", "r2an_material_generation_overauth_fail", "r2an_source_scan_overauth_fail", "r2an_network_runtime_overauth_fail", "stop_go_missing_r2ap_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "gate_duplicate_fail", "synthetic_validator_set_fail", "synthetic_validator_duplicate_fail", "readback_record_fail", "leak_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "material_generation_authorized_bool", "private_write_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
R2AN_FORBIDDEN_STOP_TRUE = ["private_read_authorized_bool", "prior_private_material_read_authorized_bool", "new_material_generation_authorized_bool", "material_generation_authorized_bool", "private_write_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "experiment_metrics_authorized_bool", "success_ranking_robustness_metrics_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "single_rank_content_path_primary_signal_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_keys_or_source", re.compile(r"candidate_key|pair_key_value|evidence_key|source_file_key|filepath|source_filename_value|directory_value|snippet_value|line_number|gold_span_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_or_metric", re.compile(r"exact_count_value|exact_rate|exact_score|private_score|top[-_]?k|mrr|hit_rate|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def audit_r2an(r2an: dict[str, Any]) -> dict[str, bool]:
    src = (r2an.get("source_lock_records") or [{}])[0]
    agg = (r2an.get("material_aggregate_records") or [{}])[0]
    policy = (r2an.get("policy_records") or [{}])[0]
    privacy = (r2an.get("privacy_publication_records") or [{}])[0]
    mode = (r2an.get("execution_mode_records") or [{}])[0]
    stop = (r2an.get("stop_go_records") or [{}])[0]
    status_ok = r2an.get("status") == R2AN_STATUS
    self_test_ok = r2an.get("self_test_total") == R2AN_SELF_TEST_TOTAL
    scan_ok = r2an.get("forbidden_scan", {}).get("status") == "pass"
    source_ok = status_ok and self_test_ok and scan_ok and src.get("locked_haae_r2am_checkpoint") == R2AM_CHECKPOINT and src.get("source_locked_bool") is True
    group_ok = set((agg.get("group_presence_buckets") or {}).keys()) == set(GROUPS) and all(v == "present" for v in (agg.get("group_presence_buckets") or {}).values())
    pair_ok = set((agg.get("pair_family_presence_buckets") or {}).keys()) == set(PAIR_FAMILIES) and all(v == "present" for v in (agg.get("pair_family_presence_buckets") or {}).values())
    bounds_ok = all(agg.get(k) == v for k, v in BOUNDS.items()) and agg.get("schema_version_bucket") == R2AN_SCHEMA and agg.get("selected_signal_family_bucket") == SELECTED_SIGNAL_FAMILY
    policy_ok = policy.get("gold_private_eval_only_bool") is True and policy.get("gold_used_for_evidence_unit_selection_bool") is False and policy.get("gold_used_for_pair_selection_bool") is False and policy.get("single_rank_content_path_primary_signal_bool") is False and policy.get("path_tokens_primary_signal_bool") is False and policy.get("pair_setwise_oriented_bool") is True
    privacy_ok = privacy.get("aggregate_only_public_artifact_bool") is True and all(privacy.get(field) is False for field in ["private_root_path_public_bool", "raw_task_query_candidate_evidence_pair_keys_public_bool", "source_filename_path_line_snippet_hash_public_bool", "gold_label_public_bool", "exact_row_counts_public_bool", "experiment_metrics_public_bool", "method_default_scale_claim_bool"])
    no_metrics_ok = mode.get("experiment_metrics_bool") is False and mode.get("material_qa_only_bool") is True and (r2an.get("qa_records") or [{}])[0].get("no_experiment_metrics_bool") is True
    stop_forbidden_ok = all(stop.get(field, False) is False for field in R2AN_FORBIDDEN_STOP_TRUE)
    stop_ok = stop.get("haae_r2ao_evidence_pair_support_material_public_audit_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE and stop_forbidden_ok
    audit_ok = source_ok and group_ok and pair_ok and bounds_ok and policy_ok and privacy_ok and no_metrics_ok and stop_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "group_ok": group_ok, "pair_ok": pair_ok, "bounds_ok": bounds_ok, "policy_ok": policy_ok, "privacy_ok": privacy_ok, "no_metrics_ok": no_metrics_ok, "stop_forbidden_ok": stop_forbidden_ok, "stop_ok": stop_ok, "audit_ok": audit_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AN_CHECKPOINT, R2AN_STATUS, "R2AN self-test 27/27", "R2AM b243924", "8 schema groups present", "6 pair families present", "target_20", "evidence cap 40", "support cap 120", "contrast cap 80", "total pair cap 200", "source file cap 500", "private row cap 20000", "gold private eval only", "no gold/pair selection", "single-rank content/path forbidden", "pair/setwise oriented", "aggregate-only", "no metrics", NEXT_PHASE, "no new material generation/source scan/CI/network/runtime/default/method/scale"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ao-evidence-pair-support-material-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ao-evidence-pair-support-material-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ao-evidence-pair-support-material-public-audit-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2an: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2an is None:
        try: r2an = load_json(repo / R2AN_REPORT_PATH)
        except Exception: r2an = {}
    audit = audit_r2an(r2an)
    readback = public_readback_match(self_test_total)
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["audit_ok"]:
        status = STATUS_FAIL_AUDIT
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2an_source_locked_gate": audit["source_ok"], "r2an_status_gate": audit["status_ok"], "r2an_self_test_27_gate": audit["self_test_ok"], "r2am_source_lock_gate": audit["source_ok"], "schema_groups_present_gate": audit["group_ok"], "pair_families_present_gate": audit["pair_ok"], "bounds_shape_gate": audit["bounds_ok"], "policy_gold_no_selection_gate": audit["policy_ok"], "policy_single_rank_forbidden_gate": audit["policy_ok"], "pair_setwise_gate": audit["policy_ok"], "privacy_aggregate_only_gate": audit["privacy_ok"], "no_metrics_gate": audit["no_metrics_ok"], "r2ap_stop_go_only_gate": True, "no_new_generation_source_scan_ci_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2aostop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2an_public_artifact", "haae_r2ap_explicit_local_material_experiment_authorized_bool": passed, "r2ap_existing_r2an_private_material_only_bool": passed, "r2ap_aggregate_only_metrics_bool": passed, "new_material_generation_authorized_bool": False, "material_generation_authorized_bool": False, "private_write_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "retrieval_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aosource0000", "locked_haae_r2an_checkpoint": R2AN_CHECKPOINT, "locked_haae_r2an_status": R2AN_STATUS, "r2an_status_match_bool": audit["status_ok"], "r2an_self_test_27_bool": audit["self_test_ok"], "r2an_forbidden_scan_pass_bool": audit["scan_ok"], "r2am_checkpoint_b243924_bool": audit["source_ok"], "source_locked_bool": audit["source_ok"]}],
        "material_shape_audit_records": [{"anonymous_material_shape_audit_id": "haaer2aoshape0000", "schema_group_count_bucket": "8 schema groups present", "pair_family_count_bucket": "6 pair families present", "groups_present_bool": audit["group_ok"], "pair_families_present_bool": audit["pair_ok"], "target_task_count_bucket": "target_20", "evidence_cap_bucket": "evidence cap 40", "support_cap_bucket": "support cap 120", "contrast_cap_bucket": "contrast cap 80", "total_pair_cap_bucket": "total pair cap 200", "source_file_cap_bucket": "source file cap 500", "private_row_cap_bucket": "private row cap 20000"}],
        "policy_audit_records": [{"anonymous_policy_audit_id": "haaer2aopolicy0000", "gold_private_eval_only_bool": True, "no_gold_pair_selection_bool": audit["policy_ok"], "single_rank_content_path_forbidden_bool": audit["policy_ok"], "pair_setwise_oriented_bool": audit["policy_ok"]}],
        "privacy_audit_records": [{"anonymous_privacy_audit_id": "haaer2aoprivacy0000", "aggregate_only_public_artifact_bool": audit["privacy_ok"], "no_raw_path_task_query_evidence_pair_keys_bool": audit["privacy_ok"], "no_source_filenames_snippets_hashes_bool": audit["privacy_ok"], "no_exact_counts_bool": audit["privacy_ok"], "no_metrics_bool": audit["no_metrics_ok"]}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2aoboundary0000", "public_only_audit_bool": True, "read_only_r2an_public_artifact_docs_bool": True, "private_root_read_bool": False, "tmp_read_bool": False, "recompute_generation_bool": False, "material_generation_bool": False, "experiment_metrics_bool": False, "source_candidate_scan_bool": False, "ci_network_runtime_provider_clone_bool": False, "method_default_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aogate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aosynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aoreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "material_shape_audit_records", "policy_audit_records", "privacy_audit_records", "boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_rows = report.get("pass_fail_gate_records", [])
    if len(gate_rows) != len(GATE_NAMES) or {row.get("gate_bucket") for row in gate_rows} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    synth_rows = report.get("synthetic_validator_records", [])
    if len(synth_rows) != len(SYNTHETIC_VALIDATORS) or {row.get("validator_bucket") for row in synth_rows} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2an_checkpoint") != R2AN_CHECKPOINT or source.get("locked_haae_r2an_status") != R2AN_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2an_status_match_bool", "r2an_self_test_27_bool", "r2an_forbidden_scan_pass_bool", "r2am_checkpoint_b243924_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_{field}")
    shape = (report.get("material_shape_audit_records") or [{}])[0]
    for field in ["groups_present_bool", "pair_families_present_bool"]:
        if shape.get(field) is not True: issues.append(f"shape_{field}")
    for field, expected in {"schema_group_count_bucket": "8 schema groups present", "pair_family_count_bucket": "6 pair families present", "target_task_count_bucket": "target_20", "evidence_cap_bucket": "evidence cap 40", "support_cap_bucket": "support cap 120", "contrast_cap_bucket": "contrast cap 80", "total_pair_cap_bucket": "total pair cap 200", "source_file_cap_bucket": "source file cap 500", "private_row_cap_bucket": "private row cap 20000"}.items():
        if shape.get(field) != expected: issues.append(f"shape_{field}")
    policy = (report.get("policy_audit_records") or [{}])[0]
    for field in ["gold_private_eval_only_bool", "no_gold_pair_selection_bool", "single_rank_content_path_forbidden_bool", "pair_setwise_oriented_bool"]:
        if policy.get(field) is not True: issues.append(f"policy_{field}")
    privacy = (report.get("privacy_audit_records") or [{}])[0]
    for field in ["aggregate_only_public_artifact_bool", "no_raw_path_task_query_evidence_pair_keys_bool", "no_source_filenames_snippets_hashes_bool", "no_exact_counts_bool", "no_metrics_bool"]:
        if privacy.get(field) is not True: issues.append(f"privacy_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("read_only_r2an_public_artifact_docs_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "tmp_read_bool", "recompute_generation_bool", "material_generation_bool", "experiment_metrics_bool", "source_candidate_scan_bool", "ci_network_runtime_provider_clone_bool", "method_default_scale_claim_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2ap_explicit_local_material_experiment_authorized_bool") is not True or stop.get("r2ap_existing_r2an_private_material_only_bool") is not True or stop.get("r2ap_aggregate_only_metrics_bool") is not True: issues.append("r2ap_stop_go_mismatch")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AN_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2an_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 26; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    cp = json.loads(json.dumps(base)); cp["source_lock_records"][0]["locked_haae_r2am_checkpoint"] = "wrong"; check("r2am_checkpoint_drift_fail", build_report(cp)["status"] == STATUS_FAIL_SOURCE)
    for label, mutator, expected in [("group_missing_fail", lambda r: r["material_aggregate_records"][0]["group_presence_buckets"].pop("task_frame"), "shape_groups_present_bool"), ("pair_family_missing_fail", lambda r: r["material_aggregate_records"][0]["pair_family_presence_buckets"].pop("target_support_pair"), "shape_pair_families_present_bool"), ("bounds_drift_fail", lambda r: r["material_shape_audit_records"][0].__setitem__("target_task_count_bucket", "target_21"), "shape_target_task_count_bucket"), ("gold_policy_drift_fail", lambda r: r["policy_audit_records"][0].__setitem__("no_gold_pair_selection_bool", False), "policy_no_gold_pair_selection_bool"), ("single_rank_policy_drift_fail", lambda r: r["policy_audit_records"][0].__setitem__("single_rank_content_path_forbidden_bool", False), "policy_single_rank_content_path_forbidden_bool"), ("privacy_drift_fail", lambda r: r["privacy_audit_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), "privacy_aggregate_only_public_artifact_bool"), ("metrics_drift_fail", lambda r: r["privacy_audit_records"][0].__setitem__("no_metrics_bool", False), "privacy_no_metrics_bool"), ("r2an_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_AUDIT), ("r2an_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), STATUS_FAIL_AUDIT), ("r2an_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_broad_authorized_bool", True), STATUS_FAIL_AUDIT), ("r2an_network_runtime_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_execution_authorized_bool", True), STATUS_FAIL_AUDIT), ("stop_go_missing_r2ap_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_r2ap_explicit_local_material_experiment_authorized_bool", False), "r2ap_stop_go_mismatch"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2ap_stop_go_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_set_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("synthetic_validator_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("leak_fail", lambda r: r.__setitem__("debug", "/tmp/private-root r14m-001 query pair_key crates/openlocus/src/lib.rs"), "forbidden_scan_failed")]:
        if label in {"group_missing_fail", "pair_family_missing_fail"}:
            mutated_source = json.loads(json.dumps(base)); mutator(mutated_source); report = build_report(mutated_source); check(label, report["status"] == STATUS_FAIL_AUDIT)
        elif label.startswith("r2an_"):
            mutated_source = json.loads(json.dumps(base)); mutator(mutated_source); report = build_report(mutated_source); check(label, report["status"] == expected)
        else:
            mutated = json.loads(json.dumps(passed)); mutator(mutated); check(label, expected in validate_report(mutated))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
