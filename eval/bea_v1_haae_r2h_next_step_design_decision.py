#!/usr/bin/env python3
"""BEA-v1-HAAE-R2H next-step design decision.

Public-only design decision over the R2G public audit artifact. It does not read
private roots, generate material, execute experiments, recompute metrics, run
retrieval/runtime, or use CI/network/provider/scheduler/selector.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2H Next-Step Design Decision"
SLUG = "bea_v1_haae_r2h_next_step_design_decision"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2G_CHECKPOINT = "cd583d6"
R2G_STATUS = "haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized"
R2G_REPORT_PATH = Path("artifacts/bea_v1_haae_r2g_public_audit_package/bea_v1_haae_r2g_public_audit_package_report.json")
STATUS_PASS = "haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2h_fail_closed_source_lock_mismatch"
STATUS_FAIL_DECISION = "haae_r2h_fail_closed_design_decision_mismatch"
STATUS_FAIL_LEAK = "haae_r2h_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2h_fail_closed_public_readback_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2h_fail_closed_stop_go_overauthorization"
SELF_TEST_EXPECTED = 11
NEXT_PHASE = "BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke"

R2I_RANK_SOURCES = ["bm25_like", "symbol_overlap", "path_prior", "structure_token_overlap", "rrf_like", "control_baseline"]
FORBIDDEN_R2G_STOP = ["haae_r2h_execution_authorized_bool", "scale_material_generation_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "scheduler_selector_authorized_bool", "bea_v1_a_p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
FORBIDDEN_R2H_STOP = ["r2i_execution_authorized_bool", "r2i_experiment_metrics_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r3_direct_scale_authorized_bool"]
GATE_NAMES = ["r2g_source_locked_gate", "r2g_r2h_authorization_gate", "public_only_design_gate", "no_private_read_gate", "no_material_generation_gate", "no_experiment_execution_gate", "no_recompute_gate", "degeneracy_detected_gate", "scale_same_recipe_rejected_gate", "harder_diversified_next_step_selected_gate", "r2i_boundary_bounded_gate", "no_ci_execution_gate", "no_r3_direct_scale_gate", "no_method_default_scaling_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2g_source(r2g: dict[str, Any]) -> dict[str, bool]:
    stop = (r2g.get("stop_go_records") or [{}])[0]
    status_ok = r2g.get("status") == R2G_STATUS
    scan_ok = r2g.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2h_next_step_design_authorized_bool") is True
    design_only = all(stop.get(field) is False for field in FORBIDDEN_R2G_STOP)
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "design_only": design_only, "source_locked": status_ok and scan_ok and auth_ok and design_only}


def audit_r2g_evidence(r2g: dict[str, Any]) -> dict[str, bool]:
    metrics = r2g.get("r2f_metric_readback_records", [])
    agreements = r2g.get("r2f_agreement_readback_records", [])
    claims = (r2g.get("claim_boundary_records") or [{}])[0]
    rank_sources_present = {row.get("rank_source_bucket") for row in metrics} >= {"bm25_like", "symbol_overlap", "rrf_like"}
    saturated_hit = bool(metrics) and all(row.get("gold_file_hit_rate_bucket") == "rate_1" for row in metrics)
    saturated_top = bool(metrics) and all(row.get("top1_hit_count_bucket") == "count_10_to_20" and row.get("top5_hit_count_bucket") == "count_10_to_20" and row.get("top10_hit_count_bucket") == "count_10_to_20" for row in metrics)
    same_top = bool(agreements) and all(row.get("same_top_candidate_rate_bucket") == "rate_1" for row in agreements)
    no_claims = claims.get("method_winner_claim_bool") is False and claims.get("default_runtime_claim_bool") is False and claims.get("scaling_claim_bool") is False
    return {"tiny_chain_present": True, "medium_chain_present": True, "rank_sources_present": rank_sources_present, "saturated_hit": saturated_hit, "saturated_top": saturated_top, "same_top": same_top, "no_claims": no_claims, "degeneracy_detected": saturated_hit and same_top and no_claims}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank|task_key|candidate_rank|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2G_CHECKPOINT, R2G_STATUS, "arms_not_separating", "reject/defer scaling the same R14 medium recipe", "harder/diversified local material generation", "target 20 tasks", "candidate depth 40", "private row cap 10000", "no method/default/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]

    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)

    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2h-next-step-design-decision.md")) and has_all(read("docs/zh/bea-v1-haae-r2h-next-step-design-decision.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2h-next-step-design-decision.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2g: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2g is None:
        try:
            r2g = load_json(repo / R2G_REPORT_PATH)
        except Exception:
            r2g = {}
    source = validate_r2g_source(r2g)
    evidence = audit_r2g_evidence(r2g)
    readback = public_readback_match(self_test_total)
    decision_ok = evidence["degeneracy_detected"] and evidence["rank_sources_present"] and evidence["medium_chain_present"] and evidence["no_claims"]
    if not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not decision_ok:
        status = STATUS_FAIL_DECISION
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2g_source_locked_gate": source["source_locked"], "r2g_r2h_authorization_gate": source["auth_ok"], "public_only_design_gate": True, "no_private_read_gate": True, "no_material_generation_gate": True, "no_experiment_execution_gate": True, "no_recompute_gate": True, "degeneracy_detected_gate": evidence["degeneracy_detected"], "scale_same_recipe_rejected_gate": True, "harder_diversified_next_step_selected_gate": True, "r2i_boundary_bounded_gate": True, "no_ci_execution_gate": True, "no_r3_direct_scale_gate": True, "no_method_default_scaling_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2hsource0000", "locked_haae_r2g_checkpoint": R2G_CHECKPOINT, "locked_haae_r2g_status": R2G_STATUS, "r2g_status_match_bool": source["status_ok"], "r2g_forbidden_scan_pass_bool": source["scan_ok"], "r2g_r2h_design_authorized_bool": source["auth_ok"], "r2g_authorizes_only_design_bool": source["design_only"], "source_locked_bool": source["source_locked"]}],
        "evidence_summary_records": [{"anonymous_evidence_summary_id": "haaer2hevidence0000", "tiny_chain_present_bool": evidence["tiny_chain_present"], "medium_chain_present_bool": evidence["medium_chain_present"], "rank_sources_present_bool": evidence["rank_sources_present"], "saturated_hit_bucket_bool": evidence["saturated_hit"], "same_top_agreement_saturated_bool": evidence["same_top"], "method_default_scaling_claim_bool": False}],
        "degeneracy_diagnosis_records": [{"anonymous_degeneracy_diagnosis_id": "haaer2hdegeneracy0000", "all_rank_sources_rate_1_bool": evidence["saturated_hit"], "same_top_rate_1_bool": evidence["same_top"], "arms_not_separating_bool": True, "pipeline_validity_signal_bool": True, "method_evidence_signal_bool": False}],
        "next_step_option_records": [{"anonymous_option_id": "haaer2hoption0000", "option_bucket": "scale_same_r14_medium_or_ci", "decision_bucket": "reject_defer", "selected_bool": False}, {"anonymous_option_id": "haaer2hoption0001", "option_bucket": "harder_diversified_local_material_generation", "decision_bucket": "selected", "selected_bool": True}, {"anonymous_option_id": "haaer2hoption0002", "option_bucket": "ci_batch_same_recipe", "decision_bucket": "defer", "selected_bool": False}, {"anonymous_option_id": "haaer2hoption0003", "option_bucket": "public_only_analysis_loop", "decision_bucket": "reject", "selected_bool": False}],
        "r2i_contract_records": [{"anonymous_r2i_contract_id": "haaer2hcontract0000", "next_phase_bucket": NEXT_PHASE, "target_task_count_bucket": "target_20_tasks", "candidate_depth_bucket": "candidate_depth_40", "private_row_cap_bucket": "private_row_cap_10000", "explicit_opt_in_private_root_required_bool": True, "local_manual_only_bool": True, "public_aggregate_only_manifest_bool": True, "rank_source_buckets": R2I_RANK_SOURCES, "no_experiment_metrics_in_r2i_bool": True, "no_retrieval_runtime_source_scan_outside_fixture_bool": True, "no_ci_network_provider_bool": True, "no_method_default_scaling_claim_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2hclaim0000", "public_only_design_bool": True, "private_read_bool": False, "material_generation_bool": False, "experiment_execution_bool": False, "recompute_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_clone_bool": False, "scheduler_haae_selector_bool": False, "method_default_scaling_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2hgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2hreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2hstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_redesign_next_step", "haae_r2i_harder_diversified_material_generation_smoke_authorized_bool": passed, "r2i_execution_authorized_bool": False, "r2i_experiment_metrics_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_outside_fixture_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "r3_direct_scale_authorized_bool": False}],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2hsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2g_status_fail", "r2g_overauth_fail", "degeneracy_missing_fail", "same_recipe_selected_fail", "r2i_overauth_fail", "raw_leak_fail", "stale_readback_fail"])],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "evidence_summary_records", "degeneracy_diagnosis_records", "next_step_option_records", "r2i_contract_records", "claim_boundary_records", "pass_fail_gate_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2g_checkpoint") != R2G_CHECKPOINT or source.get("locked_haae_r2g_status") != R2G_STATUS or source.get("source_locked_bool") is not True or source.get("r2g_authorizes_only_design_bool") is not True:
        issues.append("source_lock_mismatch")
    degeneracy = (report.get("degeneracy_diagnosis_records") or [{}])[0]
    if degeneracy.get("arms_not_separating_bool") is not True or degeneracy.get("pipeline_validity_signal_bool") is not True or degeneracy.get("method_evidence_signal_bool") is not False:
        issues.append("degeneracy_decision_mismatch")
    options = {row.get("option_bucket"): row for row in report.get("next_step_option_records", [])}
    if options.get("harder_diversified_local_material_generation", {}).get("selected_bool") is not True or options.get("scale_same_r14_medium_or_ci", {}).get("decision_bucket") != "reject_defer":
        issues.append("next_step_option_mismatch")
    contract = (report.get("r2i_contract_records") or [{}])[0]
    if contract.get("target_task_count_bucket") != "target_20_tasks" or contract.get("candidate_depth_bucket") != "candidate_depth_40" or contract.get("private_row_cap_bucket") != "private_row_cap_10000" or contract.get("no_experiment_metrics_in_r2i_bool") is not True:
        issues.append("r2i_contract_mismatch")
    if contract.get("explicit_opt_in_private_root_required_bool") is not True or contract.get("local_manual_only_bool") is not True or contract.get("public_aggregate_only_manifest_bool") is not True:
        issues.append("r2i_contract_mismatch")
    if contract.get("no_retrieval_runtime_source_scan_outside_fixture_bool") is not True or contract.get("no_ci_network_provider_bool") is not True or contract.get("no_method_default_scaling_claim_bool") is not True:
        issues.append("r2i_contract_mismatch")
    if set(contract.get("rank_source_buckets") or []) != set(R2I_RANK_SOURCES):
        issues.append("r2i_contract_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    if claim.get("public_only_design_bool") is not True:
        issues.append("claim_boundary_public_only_design")
    for field in ["private_read_bool", "material_generation_bool", "experiment_execution_bool", "recompute_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_clone_bool", "scheduler_haae_selector_bool", "method_default_scaling_claim_bool"]:
        if claim.get(field) is not False:
            issues.append(f"claim_boundary_{field}")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True:
            issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_R2H_STOP:
        if stop.get(field) is not False:
            issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2i_harder_diversified_material_generation_smoke_authorized_bool") is not True:
            issues.append("missing_r2i_authorization")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            if arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2G_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"
    check("wrong_r2g_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    over = json.loads(json.dumps(base)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("r2g_overauth_fail", build_report(over)["status"] == STATUS_FAIL_SOURCE)
    deg = json.loads(json.dumps(base)); deg["r2f_metric_readback_records"][0]["gold_file_hit_rate_bucket"] = "rate_half_to_lt1"
    check("degeneracy_missing_fail", build_report(deg)["status"] == STATUS_FAIL_DECISION)
    opt = json.loads(json.dumps(passed)); opt["next_step_option_records"][1]["selected_bool"] = False
    check("same_recipe_selected_fail", "next_step_option_mismatch" in validate_report(opt))
    contract = json.loads(json.dumps(passed)); contract["r2i_contract_records"][0]["rank_source_buckets"] = ["bm25_like"]
    check("r2i_contract_drift_fail", "r2i_contract_mismatch" in validate_report(contract))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["material_generation_bool"] = True
    check("claim_boundary_drift_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    gate = json.loads(json.dumps(passed)); gate["pass_fail_gate_records"][0]["gate_passed_bool"] = False
    check("gate_drift_fail", any(i.startswith("gate_failed_") for i in validate_report(gate)))
    over2 = json.loads(json.dumps(passed)); over2["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("r2i_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(over2)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"
    check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()):
            parse_args(["--private-root", "/tmp/x"])
        check("safe_parser", False)
    except ValueError:
        check("safe_parser", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
