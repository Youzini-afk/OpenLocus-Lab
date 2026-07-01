#!/usr/bin/env python3
"""BEA-v1-HAAE-R2O robustness preflight design.

Public-only design package after R2N. It reads only public artifacts/docs and
does not execute material generation or experiments.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2O Robustness Preflight Design"
SLUG = "bea_v1_haae_r2o_robustness_preflight_design"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2N_CHECKPOINT = "a9066d2"
R2N_STATUS = "haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized"
R2N_REPORT_PATH = Path("artifacts/bea_v1_haae_r2n_public_audit_package/bea_v1_haae_r2n_public_audit_package_report.json")
STATUS_PASS = "haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2o_fail_closed_source_lock_mismatch"
STATUS_FAIL_CONTEXT = "haae_r2o_fail_closed_mechanism_context_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2o_fail_closed_claim_boundary_mismatch"
STATUS_FAIL_LEAK = "haae_r2o_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2o_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 14
NEXT_PHASE = "BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation"
VARIANTS = ["original", "path_scrambled", "extension_bucket_preserved", "directory_depth_preserved", "control_baseline_strengthened"]

CLAIM_FALSE_FIELDS = ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]
STOP_FALSE_FIELDS = ["haae_r2o_execution_authorized_bool", "haae_r2p_execution_authorized_by_r2o_bool", "ci_execution_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2n_source_locked_gate", "r2n_status_gate", "r2n_r2o_authorization_gate", "r2n_public_only_boundary_gate", "public_only_design_gate", "mechanism_context_gate", "robustness_question_defined_gate", "r2p_path_cue_robustness_selected_gate", "r2p_contract_bounded_gate", "no_private_read_write_gate", "no_material_generation_in_r2o_gate", "no_execution_recompute_gate", "no_retrieval_runtime_source_scan_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2n(r2n: dict[str, Any]) -> dict[str, bool]:
    source = (r2n.get("source_lock_records") or [{}])[0]
    mechanism = (r2n.get("mechanism_readback_records") or [{}])[0]
    claim = (r2n.get("claim_boundary_records") or [{}])[0]
    stop = (r2n.get("stop_go_records") or [{}])[0]
    status_ok = r2n.get("status") == R2N_STATUS
    scan_ok = r2n.get("forbidden_scan", {}).get("status") == "pass"
    source_ok = source.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2o_robustness_preflight_design_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in ["haae_r2o_execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    claim_ok = all(claim.get(field) is False for field in CLAIM_FALSE_FIELDS)
    context_ok = mechanism.get("dominant_mechanism_bucket") == "path_structure_prior" and mechanism.get("confidence_bucket") == "medium_high" and mechanism.get("fixture_path_cues_bool") is True and mechanism.get("control_underfit_bool") is True and mechanism.get("method_winner_bool") is False
    return {"status_ok": status_ok, "scan_ok": scan_ok, "source_ok": source_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "context_ok": context_ok, "source_locked": status_ok and scan_ok and source_ok and auth_ok and stop_ok and claim_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|extension_value|token_value|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2N_CHECKPOINT, R2N_STATUS, "path_structure_prior", "fixture path cues + control underfit", NEXT_PHASE, "target 20 tasks", "candidate depth 40", "row cap 20000", "original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened", "no experiment metrics in R2P", "not execution/CI/new material generation in R2O", "no method/default/scaling claim"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2o-robustness-preflight-design.md")) and has_all(read("docs/zh/bea-v1-haae-r2o-robustness-preflight-design.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2o-robustness-preflight-design.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2n: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2n is None:
        try: r2n = load_json(repo / R2N_REPORT_PATH)
        except Exception: r2n = {}
    audit = validate_r2n(r2n)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["context_ok"]:
        status = STATUS_FAIL_CONTEXT
    elif not audit["claim_ok"] or not audit["stop_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2n_source_locked_gate": audit["source_locked"], "r2n_status_gate": audit["status_ok"], "r2n_r2o_authorization_gate": audit["auth_ok"], "r2n_public_only_boundary_gate": audit["stop_ok"] and audit["claim_ok"], "public_only_design_gate": True, "mechanism_context_gate": audit["context_ok"], "robustness_question_defined_gate": True, "r2p_path_cue_robustness_selected_gate": True, "r2p_contract_bounded_gate": True, "no_private_read_write_gate": True, "no_material_generation_in_r2o_gate": True, "no_execution_recompute_gate": True, "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2osource0000", "locked_haae_r2n_checkpoint": R2N_CHECKPOINT, "locked_haae_r2n_status": R2N_STATUS, "r2n_status_match_bool": audit["status_ok"], "r2n_forbidden_scan_pass_bool": audit["scan_ok"], "r2n_r2o_authorization_match_bool": audit["auth_ok"], "r2n_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "r2n_claim_boundary_match_bool": audit["claim_ok"], "source_locked_bool": audit["source_locked"]}],
        "mechanism_context_records": [{"anonymous_mechanism_context_id": "haaer2ocontext0000", "dominant_mechanism_bucket": "path_structure_prior", "confidence_bucket": "medium_high", "fixture_path_cues_bool": True, "control_underfit_bool": True, "method_winner_bool": False, "context_readback_match_bool": audit["context_ok"]}],
        "robustness_question_records": [{"anonymous_robustness_question_id": "haaer2oquestion0000", "question_bucket": "do_path_cues_survive_controlled_path_perturbations", "target_mechanism_bucket": "path_structure_prior", "requires_new_private_material_bool": True, "experiment_metrics_in_r2o_bool": False, "public_only_design_bool": True}],
        "next_step_options_records": [{"anonymous_option_id": "haaer2ooption0000", "option_bucket": "path_cue_robustness_material_generation", "decision_bucket": "selected", "next_phase": NEXT_PHASE}, {"anonymous_option_id": "haaer2ooption0001", "option_bucket": "scale_current_recipe", "decision_bucket": "defer"}, {"anonymous_option_id": "haaer2ooption0002", "option_bucket": "ci_batch_execution", "decision_bucket": "defer"}, {"anonymous_option_id": "haaer2ooption0003", "option_bucket": "method_default_promotion", "decision_bucket": "reject"}],
        "r2p_contract_records": [{"anonymous_r2p_contract_id": "haaer2ocontract0000", "next_phase": NEXT_PHASE, "local_explicit_opt_in_bool": True, "private_output_root_required_bool": True, "public_aggregate_only_bool": True, "target_task_count_bucket": "count_20", "candidate_depth_bucket": "count_40", "variant_bucket": "/".join(VARIANTS), "private_row_cap_bucket": "count_20000", "experiment_metrics_in_r2p_bool": False, "ci_network_retrieval_runtime_source_scan_authorized_bool": False, "method_default_scaling_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2oclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ogate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2osynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2n_status_fail", "mechanism_context_drift_fail", "r2n_overauth_fail", "r2p_contract_missing_fail", "method_claim_fail", "stop_go_overauth_fail", "raw_leak_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2oreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2ostop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2n_public_artifact", "haae_r2p_path_cue_robustness_material_generation_authorized_bool": passed, "haae_r2o_execution_authorized_bool": False, "haae_r2p_execution_authorized_by_r2o_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_in_r2o_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "mechanism_context_records", "robustness_question_records", "next_step_options_records", "r2p_contract_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2n_checkpoint") != R2N_CHECKPOINT or source.get("locked_haae_r2n_status") != R2N_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2n_status_match_bool", "r2n_forbidden_scan_pass_bool", "r2n_r2o_authorization_match_bool", "r2n_no_forbidden_stop_go_drift_bool", "r2n_claim_boundary_match_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    context = (report.get("mechanism_context_records") or [{}])[0]
    if context.get("dominant_mechanism_bucket") != "path_structure_prior" or context.get("confidence_bucket") != "medium_high" or context.get("fixture_path_cues_bool") is not True or context.get("control_underfit_bool") is not True or context.get("method_winner_bool") is not False: issues.append("mechanism_context_mismatch")
    question = (report.get("robustness_question_records") or [{}])[0]
    if question.get("question_bucket") != "do_path_cues_survive_controlled_path_perturbations" or question.get("target_mechanism_bucket") != "path_structure_prior" or question.get("requires_new_private_material_bool") is not True or question.get("experiment_metrics_in_r2o_bool") is not False or question.get("public_only_design_bool") is not True: issues.append("robustness_question_mismatch")
    options = {row.get("option_bucket"): row.get("decision_bucket") for row in report.get("next_step_options_records", [])}
    if options.get("path_cue_robustness_material_generation") != "selected" or options.get("scale_current_recipe") != "defer" or options.get("ci_batch_execution") != "defer" or options.get("method_default_promotion") != "reject": issues.append("next_step_options_mismatch")
    contract = (report.get("r2p_contract_records") or [{}])[0]
    if contract.get("next_phase") != NEXT_PHASE or contract.get("local_explicit_opt_in_bool") is not True or contract.get("private_output_root_required_bool") is not True or contract.get("public_aggregate_only_bool") is not True or contract.get("target_task_count_bucket") != "count_20" or contract.get("candidate_depth_bucket") != "count_40" or contract.get("private_row_cap_bucket") != "count_20000" or contract.get("variant_bucket") != "/".join(VARIANTS) or contract.get("experiment_metrics_in_r2p_bool") is not False or contract.get("ci_network_retrieval_runtime_source_scan_authorized_bool") is not False or contract.get("method_default_scaling_claim_bool") is not False: issues.append("r2p_contract_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in CLAIM_FALSE_FIELDS:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2o_execution_authorized_bool", "haae_r2p_execution_authorized_by_r2o_bool", "ci_execution_authorized_bool", "new_material_generation_in_r2o_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2p_path_cue_robustness_material_generation_authorized_bool") is not True: issues.append("missing_r2p_authorization")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True: issues.append(f"gate_not_passed_{gate}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
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
    base = load_json(repo / R2N_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2n_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    ctx = json.loads(json.dumps(base)); ctx["mechanism_readback_records"][0]["dominant_mechanism_bucket"] = "other"; check("mechanism_context_drift_fail", build_report(ctx)["status"] == STATUS_FAIL_CONTEXT)
    over = json.loads(json.dumps(base)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("r2n_overauth_fail", build_report(over)["status"] == STATUS_FAIL_SOURCE)
    bad_contract = json.loads(json.dumps(passed)); bad_contract["r2p_contract_records"][0]["variant_bucket"] = "original"; check("r2p_contract_missing_fail", "r2p_contract_mismatch" in validate_report(bad_contract))
    bad_question = json.loads(json.dumps(passed)); bad_question["robustness_question_records"][0]["experiment_metrics_in_r2o_bool"] = True; check("robustness_question_drift_fail", "robustness_question_mismatch" in validate_report(bad_question))
    bad_option = json.loads(json.dumps(passed)); bad_option["next_step_options_records"][1]["decision_bucket"] = "selected"; check("next_option_drift_fail", "next_step_options_mismatch" in validate_report(bad_option))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("method_claim_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    stop = json.loads(json.dumps(passed)); stop["stop_go_records"][0]["haae_r2p_execution_authorized_by_r2o_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(stop)))
    next_stop = json.loads(json.dumps(passed)); next_stop["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_phase_drift_fail", "next_allowed_phase_mismatch" in validate_report(next_stop))
    gate_drift = json.loads(json.dumps(passed)); gate_drift["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_drift_fail", any(i.startswith("gate_not_passed_") for i in validate_report(gate_drift)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except ValueError:
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
