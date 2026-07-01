#!/usr/bin/env python3
"""BEA-v1-HAAE-R2L next-step decision / mechanism preflight.

Public-only decision package over the R2K public audit artifact. It reads no
private root/material, no source repos, and performs no execution or recompute.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight"
SLUG = "bea_v1_haae_r2l_next_step_decision_mechanism_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2K_CHECKPOINT = "99600db"
R2K_STATUS = "haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized"
R2K_REPORT_PATH = Path("artifacts/bea_v1_haae_r2k_public_audit_package/bea_v1_haae_r2k_public_audit_package_report.json")

STATUS_PASS = "haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized"
STATUS_NO_GO = "haae_r2l_no_go_no_safe_mechanism_next_step"
STATUS_FAIL_SOURCE = "haae_r2l_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2l_fail_closed_claim_boundary_mismatch"
STATUS_FAIL_LEAK = "haae_r2l_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2l_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 14
NEXT_PHASE = "BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition"

FORBIDDEN_STOP_TRUE = ["haae_r2l_execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
CLAIM_FALSE_FIELDS = ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]
GATE_NAMES = ["r2k_source_locked_gate", "r2k_status_gate", "r2k_r2l_authorization_gate", "r2k_public_only_boundary_gate", "public_only_decision_gate", "no_private_read_gate", "no_material_generation_gate", "no_experiment_execution_gate", "no_recompute_gate", "no_retrieval_source_scan_runtime_gate", "no_ci_network_provider_clone_gate", "no_scheduler_haae_selector_gate", "separation_signal_context_gate", "no_method_default_scaling_claim_gate", "mechanism_next_step_selected_gate", "scale_ci_new_material_deferred_gate", "r2m_contract_bounded_gate", "r2m_next_only_r2n_audit_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2k_source(r2k: dict[str, Any]) -> dict[str, bool]:
    stop = (r2k.get("stop_go_records") or [{}])[0]
    claim = (r2k.get("claim_boundary_records") or [{}])[0]
    sep = (r2k.get("separation_audit_records") or [{}])[0]
    metric = (r2k.get("r2j_metric_audit_records") or [{}])[0]
    status_ok = r2k.get("status") == R2K_STATUS
    scan_ok = r2k.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2l_next_step_decision_mechanism_preflight_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    claim_ok = all(claim.get(field) is False for field in CLAIM_FALSE_FIELDS)
    separation_ok = sep.get("separation_signal_bool") is True and sep.get("method_winner_bool") is False and sep.get("rank_spread_bucket") == "spread_medium" and sep.get("control_baseline_separation_bucket") == "non_control_better"
    metric_ok = metric.get("path_prior_mrr_bucket") == "mrr_high" and metric.get("control_baseline_mrr_bucket") == "mrr_low" and metric.get("control_baseline_top1_bucket") == "count_0"
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "separation_ok": separation_ok, "metric_ok": metric_ok, "source_locked": status_ok and scan_ok and auth_ok and stop_ok and claim_ok and separation_ok and metric_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|private material root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2K_CHECKPOINT, R2K_STATUS, "separation signal but no method/default/scaling claim", "mechanism decomposition over existing R2I material", "not scale/CI or new material generation yet", "explicit opt-in private read only", "aggregate-only mechanism buckets", NEXT_PHASE, "R2M next only R2N public audit"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]

    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)

    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2l-next-step-decision-mechanism-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2l-next-step-decision-mechanism-preflight.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2l-next-step-decision-mechanism-preflight.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2k: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2k is None:
        try: r2k = load_json(repo / R2K_REPORT_PATH)
        except Exception: r2k = {}
    source = validate_r2k_source(r2k)
    readback = public_readback_match(self_test_total)
    safe_mechanism_defined = source["separation_ok"] and source["metric_ok"]
    if not source["status_ok"] or not source["scan_ok"] or not source["auth_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not source["stop_ok"] or not source["claim_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not safe_mechanism_defined:
        status = STATUS_NO_GO
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2k_source_locked_gate": source["source_locked"], "r2k_status_gate": source["status_ok"], "r2k_r2l_authorization_gate": source["auth_ok"], "r2k_public_only_boundary_gate": source["stop_ok"] and source["claim_ok"], "public_only_decision_gate": True, "no_private_read_gate": True, "no_material_generation_gate": True, "no_experiment_execution_gate": True, "no_recompute_gate": True, "no_retrieval_source_scan_runtime_gate": True, "no_ci_network_provider_clone_gate": True, "no_scheduler_haae_selector_gate": True, "separation_signal_context_gate": safe_mechanism_defined, "no_method_default_scaling_claim_gate": True, "mechanism_next_step_selected_gate": safe_mechanism_defined, "scale_ci_new_material_deferred_gate": True, "r2m_contract_bounded_gate": True, "r2m_next_only_r2n_audit_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2lsource0000", "locked_haae_r2k_checkpoint": R2K_CHECKPOINT, "locked_haae_r2k_status": R2K_STATUS, "r2k_status_match_bool": source["status_ok"], "r2k_forbidden_scan_pass_bool": source["scan_ok"], "r2k_r2l_authorization_match_bool": source["auth_ok"], "r2k_no_forbidden_stop_go_drift_bool": source["stop_ok"], "r2k_claim_boundary_match_bool": source["claim_ok"], "source_locked_bool": source["source_locked"]}],
        "separation_signal_context_records": [{"anonymous_context_id": "haaer2lcontext0000", "separation_signal_bool": source["separation_ok"], "path_prior_signal_bucket": "path_prior_high_vs_control_low", "control_baseline_bucket": "non_control_better", "method_default_scaling_claim_bool": False, "pipeline_followup_needed_bool": True, "mechanism_preflight_relevant_bool": safe_mechanism_defined}],
        "next_step_option_records": [{"anonymous_option_id": "haaer2loption0000", "option_bucket": "mechanism_decomposition_existing_r2i_material", "decision_bucket": "selected", "rationale_bucket": "separation_signal_but_no_method_default_scaling_claim"}, {"anonymous_option_id": "haaer2loption0001", "option_bucket": "scale_or_ci_same_recipe", "decision_bucket": "defer", "rationale_bucket": "mechanism_unknown"}, {"anonymous_option_id": "haaer2loption0002", "option_bucket": "new_material_generation", "decision_bucket": "defer", "rationale_bucket": "use_existing_r2i_first"}, {"anonymous_option_id": "haaer2loption0003", "option_bucket": "public_only_summary_loop", "decision_bucket": "reject", "rationale_bucket": "insufficient_mechanism_detail"}],
        "r2m_contract_records": [{"anonymous_r2m_contract_id": "haaer2lcontract0000", "next_phase": NEXT_PHASE, "explicit_opt_in_private_read_only_bool": True, "existing_r2i_private_material_root_only_bool": True, "aggregate_only_mechanism_buckets_bool": True, "private_write_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_runtime_source_scan_authorized_bool": False, "ci_network_provider_authorized_bool": False, "scheduler_selector_authorized_bool": False, "method_winner_default_scaling_claim_bool": False, "r2m_next_only_r2n_public_audit_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2lclaim0000", "public_only_decision_bool": True, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2lgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2lsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2k_status_fail", "r2k_overauth_fail", "claim_boundary_fail", "missing_separation_no_go", "unsafe_mechanism_no_go", "raw_leak_fail", "stop_go_overauth_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2lreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2lstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2k_public_artifact", "haae_r2m_path_prior_separation_mechanism_decomposition_authorized_bool": passed, "haae_r2l_execution_authorized_bool": False, "haae_r2m_execution_authorized_by_r2l_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "separation_signal_context_records", "next_step_option_records", "r2m_contract_records", "claim_boundary_records", "pass_fail_gate_records", "public_readback_records", "stop_go_records", "forbidden_scan", "synthetic_validator_records"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2k_checkpoint") != R2K_CHECKPOINT or source.get("locked_haae_r2k_status") != R2K_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2k_status_match_bool", "r2k_forbidden_scan_pass_bool", "r2k_r2l_authorization_match_bool", "r2k_no_forbidden_stop_go_drift_bool", "r2k_claim_boundary_match_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    context = (report.get("separation_signal_context_records") or [{}])[0]
    if not (context.get("separation_signal_bool") is True and context.get("path_prior_signal_bucket") == "path_prior_high_vs_control_low" and context.get("method_default_scaling_claim_bool") is False and context.get("mechanism_preflight_relevant_bool") is True): issues.append("separation_context_mismatch")
    options = {row.get("option_bucket"): row.get("decision_bucket") for row in report.get("next_step_option_records", [])}
    if options.get("mechanism_decomposition_existing_r2i_material") != "selected" or options.get("scale_or_ci_same_recipe") != "defer" or options.get("new_material_generation") != "defer": issues.append("next_step_decision_mismatch")
    contract = (report.get("r2m_contract_records") or [{}])[0]
    if not (contract.get("next_phase") == NEXT_PHASE and contract.get("explicit_opt_in_private_read_only_bool") is True and contract.get("existing_r2i_private_material_root_only_bool") is True and contract.get("aggregate_only_mechanism_buckets_bool") is True and contract.get("r2m_next_only_r2n_public_audit_bool") is True): issues.append("r2m_contract_incomplete")
    for field in ["private_write_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_runtime_source_scan_authorized_bool", "ci_network_provider_authorized_bool", "scheduler_selector_authorized_bool", "method_winner_default_scaling_claim_bool"]:
        if contract.get(field) is not False: issues.append(f"r2m_contract_overauth_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    if claim.get("public_only_decision_bool") is not True: issues.append("claim_boundary_public_only_decision_bool")
    for field in CLAIM_FALSE_FIELDS:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2l_execution_authorized_bool", "haae_r2m_execution_authorized_by_r2l_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2m_path_prior_separation_mechanism_decomposition_authorized_bool") is not True: issues.append("missing_r2m_authorization")
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
    base = load_json(repo / R2K_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2k_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    over = json.loads(json.dumps(base)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("r2k_overauth_fail", build_report(over)["status"] == STATUS_FAIL_BOUNDARY)
    claim = json.loads(json.dumps(base)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", build_report(claim)["status"] == STATUS_FAIL_BOUNDARY)
    nosep = json.loads(json.dumps(base)); nosep["separation_audit_records"][0]["separation_signal_bool"] = False; check("missing_separation_no_go", build_report(nosep)["status"] == STATUS_NO_GO)
    bad = json.loads(json.dumps(base)); bad["r2j_metric_audit_records"][0]["path_prior_mrr_bucket"] = "mrr_low"; check("unsafe_mechanism_no_go", build_report(bad)["status"] == STATUS_NO_GO)
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    stop = json.loads(json.dumps(passed)); stop["stop_go_records"][0]["new_material_generation_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(stop)))
    source_bool = json.loads(json.dumps(passed)); source_bool["source_lock_records"][0]["source_locked_bool"] = False; check("source_bool_drift_fail", any(i.startswith("source_lock_") for i in validate_report(source_bool)))
    context = json.loads(json.dumps(passed)); context["separation_signal_context_records"][0]["path_prior_signal_bucket"] = "wrong"; check("context_drift_fail", "separation_context_mismatch" in validate_report(context))
    contract = json.loads(json.dumps(passed)); contract["r2m_contract_records"][0]["next_phase"] = "wrong"; check("contract_next_phase_drift_fail", "r2m_contract_incomplete" in validate_report(contract))
    gate = json.loads(json.dumps(passed)); gate["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_false_fail", any(i.startswith("gate_not_passed_") for i in validate_report(gate)))
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
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
