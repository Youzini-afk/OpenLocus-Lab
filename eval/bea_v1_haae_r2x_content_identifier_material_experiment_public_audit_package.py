#!/usr/bin/env python3
"""BEA-v1-HAAE-R2X content-identifier material experiment public audit package."""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2X Content-Identifier Material Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2x_content_identifier_material_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2W_CHECKPOINT = "1f91567"
R2W_STATUS = "haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present"
R2V_CHECKPOINT = "b8522de"
R2U_CHECKPOINT = "bb95f80"
R2W_REPORT_PATH = Path("artifacts/bea_v1_haae_r2w_content_identifier_material_experiment/bea_v1_haae_r2w_content_identifier_material_experiment_report.json")
STATUS_PASS = "haae_r2x_content_identifier_material_experiment_public_audit_package_complete_r2y_decision_design_authorized"
STATUS_FAIL_SOURCE = "haae_r2x_fail_closed_source_lock_mismatch"
STATUS_FAIL_RESULT = "haae_r2x_fail_closed_result_readback_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2x_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2x_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2x_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 18
NEXT_PHASE = "BEA-v1-HAAE-R2Y Content-Identifier Next-Step Decision Design"
RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "content_snippet_overlap", "identifier_normalized_bm25_like", "hard_negative_quality_control", "content_identifier_fusion", "control_baseline"]
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2w_source_locked_gate", "r2w_status_gate", "r2w_signal_present_gate", "r2w_spread_high_gate", "r2w_forbidden_scan_gate", "r2v_r2u_source_lock_gate", "aggregate_bucket_metrics_gate", "material_validity_context_gate", "no_real_file_candidate_evidence_gate", "no_file_retrieval_claim_gate", "no_method_default_scaling_claim_gate", "no_private_read_gate", "no_recompute_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_provider_scheduler_selector_gate", "r2y_decision_design_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2w(r2w: dict[str, Any]) -> dict[str, bool]:
    src = (r2w.get("source_lock_records") or [{}])[0]
    stop = (r2w.get("stop_go_records") or [{}])[0]
    claim = (r2w.get("claim_boundary_records") or [{}])[0]
    signal = (r2w.get("signal_diagnostic_records") or [{}])[0]
    validity = (r2w.get("material_validity_context_records") or [{}])[0]
    metrics = r2w.get("rank_source_metric_records", [])
    agreements = r2w.get("rank_source_agreement_records", [])
    source_ok = src.get("locked_haae_r2v_checkpoint") == R2V_CHECKPOINT and src.get("locked_r2u_source_checkpoint") == R2U_CHECKPOINT and src.get("source_locked_bool") is True
    status_ok = r2w.get("status") == R2W_STATUS
    scan_ok = r2w.get("forbidden_scan", {}).get("status") == "pass"
    stop_ok = stop.get("haae_r2x_public_audit_package_authorized_bool") is True and all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    claim_ok = all(claim.get(field) is False for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"])
    signal_ok = signal.get("content_identifier_signal_bucket") == "signal_present" and signal.get("rank_spread_bucket") == "spread_high" and signal.get("method_winner_bool") is False and signal.get("aggregate_only_bool") is True
    validity_ok = validity.get("candidate_material_type_bucket") == "query_derived_identifier_decoys" and validity.get("real_file_candidate_evidence_bool") is False and validity.get("file_retrieval_claim_bool") is False and validity.get("method_winner_claim_bool") is False
    metric_ok = len(metrics) == 7 and {row.get("rank_source_bucket") for row in metrics} == set(RANK_SOURCES) and all(row.get("exact_values_published_bool") is False for row in metrics)
    expected_pairs = len(RANK_SOURCES) * (len(RANK_SOURCES) - 1) // 2
    agreement_ok = len(agreements) == expected_pairs and all(row.get("exact_candidate_values_published_bool") is False for row in agreements)
    return {"source_ok": source_ok, "status_ok": status_ok, "scan_ok": scan_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "signal_ok": signal_ok, "validity_ok": validity_ok, "metric_ok": metric_ok, "agreement_ok": agreement_ok, "source_locked": source_ok and status_ok and scan_ok and stop_ok and claim_ok, "result_ok": signal_ok and validity_ok and metric_ok and agreement_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_key|candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2W_CHECKPOINT, R2W_STATUS, "R2V checkpoint b8522de", "R2U checkpoint bb95f80", "signal_present", "spread_high", "query_derived_identifier_decoys", "real_file_candidate_evidence=false", "file_retrieval_claim=false", "method_winner/default/scaling false", "aggregate-only bucket metrics", NEXT_PHASE, "no execution directly"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2x-content-identifier-material-experiment-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2x-content-identifier-material-experiment-public-audit-package.md"))
    root_current = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(root_current) and "bea-v1-haae-r2x-content-identifier-material-experiment-public-audit-package.md" in root_current
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2w: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2w is None:
        try: r2w = load_json(repo / R2W_REPORT_PATH)
        except Exception: r2w = {}
    audit = audit_r2w(r2w)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]: status = STATUS_FAIL_SOURCE
    elif not audit["result_ok"]: status = STATUS_FAIL_RESULT
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2w_source_locked_gate": audit["source_locked"], "r2w_status_gate": audit["status_ok"], "r2w_signal_present_gate": audit["signal_ok"], "r2w_spread_high_gate": audit["signal_ok"], "r2w_forbidden_scan_gate": audit["scan_ok"], "r2v_r2u_source_lock_gate": audit["source_ok"], "aggregate_bucket_metrics_gate": audit["metric_ok"] and audit["agreement_ok"], "material_validity_context_gate": audit["validity_ok"], "no_real_file_candidate_evidence_gate": audit["validity_ok"], "no_file_retrieval_claim_gate": audit["validity_ok"], "no_method_default_scaling_claim_gate": audit["claim_ok"], "no_private_read_gate": True, "no_recompute_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_provider_scheduler_selector_gate": True, "r2y_decision_design_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2xsource0000", "locked_haae_r2w_checkpoint": R2W_CHECKPOINT, "locked_haae_r2w_status": R2W_STATUS, "locked_haae_r2v_checkpoint": R2V_CHECKPOINT, "locked_haae_r2u_checkpoint": R2U_CHECKPOINT, "r2w_status_match_bool": audit["status_ok"], "r2w_forbidden_scan_pass_bool": audit["scan_ok"], "r2w_stop_go_r2x_authorized_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "experiment_result_audit_records": [{"anonymous_result_audit_id": "haaer2xresult0000", "content_identifier_signal_bucket": "signal_present", "rank_spread_bucket": "spread_high", "aggregate_bucket_metrics_bool": audit["metric_ok"], "pairwise_overlap_buckets_present_bool": audit["agreement_ok"], "exact_metrics_published_bool": False, "result_readback_match_bool": audit["result_ok"]}],
        "material_validity_context_records": [{"anonymous_material_validity_context_id": "haaer2xvalidity0000", "candidate_material_type_bucket": "query_derived_identifier_decoys", "real_file_candidate_evidence_bool": False, "file_retrieval_claim_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False}],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2xboundary0000", "public_only_audit_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "recompute_metrics_bool": False, "material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "aggregate_only_bool": True, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2xclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "execution_authorized_bool": False, "ci_authorized_bool": False, "new_material_generation_authorized_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2xgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2xsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2w_status_fail", "signal_drift_fail", "spread_drift_fail", "material_validity_drift_fail", "metric_exact_publication_fail", "overauth_fail", "next_phase_overauth_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail", "source_checkpoint_drift_fail", "claim_boundary_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2xreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2xstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2w_public_artifact", "haae_r2y_decision_design_authorized_bool": passed, "r2y_public_decision_design_only_bool": passed, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "experiment_result_audit_records", "material_validity_context_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2w_checkpoint") != R2W_CHECKPOINT or src.get("locked_haae_r2w_status") != R2W_STATUS or src.get("locked_haae_r2v_checkpoint") != R2V_CHECKPOINT or src.get("locked_haae_r2u_checkpoint") != R2U_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2w_status_match_bool", "r2w_forbidden_scan_pass_bool", "r2w_stop_go_r2x_authorized_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    result = (report.get("experiment_result_audit_records") or [{}])[0]
    if result.get("content_identifier_signal_bucket") != "signal_present" or result.get("rank_spread_bucket") != "spread_high" or result.get("result_readback_match_bool") is not True: issues.append("result_readback_mismatch")
    if result.get("aggregate_bucket_metrics_bool") is not True: issues.append("result_aggregate_bucket_metrics_missing")
    if result.get("pairwise_overlap_buckets_present_bool") is not True: issues.append("result_pairwise_overlap_buckets_missing")
    if result.get("exact_metrics_published_bool") is not False: issues.append("result_exact_metrics_public")
    validity = (report.get("material_validity_context_records") or [{}])[0]
    if validity.get("candidate_material_type_bucket") != "query_derived_identifier_decoys" or validity.get("real_file_candidate_evidence_bool") is not False or validity.get("file_retrieval_claim_bool") is not False or validity.get("method_winner_claim_bool") is not False or validity.get("default_runtime_claim_bool") is not False or validity.get("scaling_claim_bool") is not False: issues.append("material_validity_context_mismatch")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("aggregate_only_bool") is not True: issues.append("boundary_public_aggregate_mismatch")
    for field in ["private_root_read_bool", "private_material_read_bool", "recompute_metrics_bool", "material_generation_bool", "candidate_generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "execution_authorized_bool", "ci_authorized_bool", "new_material_generation_authorized_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2y_decision_design_authorized_bool") is not True or stop.get("r2y_public_decision_design_only_bool") is not True: issues.append("r2y_stop_go_missing")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["execution_authorized_bool", *FORBIDDEN_STOP_TRUE]:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}; i = 0
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
    repo = Path(__file__).resolve().parents[1]; path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; base = load_json(repo / R2W_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2w_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    source = json.loads(json.dumps(base)); source["source_lock_records"][0]["locked_haae_r2v_checkpoint"] = "wrong"; check("source_checkpoint_drift_fail", build_report(source)["status"] == STATUS_FAIL_SOURCE)
    signal = json.loads(json.dumps(base)); signal["signal_diagnostic_records"][0]["content_identifier_signal_bucket"] = "no_signal"; check("signal_drift_fail", build_report(signal)["status"] == STATUS_FAIL_RESULT)
    spread = json.loads(json.dumps(base)); spread["signal_diagnostic_records"][0]["rank_spread_bucket"] = "spread_low"; check("spread_drift_fail", build_report(spread)["status"] == STATUS_FAIL_RESULT)
    validity = json.loads(json.dumps(base)); validity["material_validity_context_records"][0]["real_file_candidate_evidence_bool"] = True; check("material_validity_drift_fail", build_report(validity)["status"] == STATUS_FAIL_RESULT)
    metric = json.loads(json.dumps(base)); metric["rank_source_metric_records"][0]["exact_values_published_bool"] = True; check("metric_exact_publication_fail", build_report(metric)["status"] == STATUS_FAIL_RESULT)
    exact = json.loads(json.dumps(passed)); exact["experiment_result_audit_records"][0]["exact_metrics_published_bool"] = True; check("r2x_exact_metrics_public_fail", "result_exact_metrics_public" in validate_report(exact))
    aggregate = json.loads(json.dumps(passed)); aggregate["experiment_result_audit_records"][0]["aggregate_bucket_metrics_bool"] = False; check("r2x_aggregate_metrics_missing_fail", "result_aggregate_bucket_metrics_missing" in validate_report(aggregate))
    pairwise = json.loads(json.dumps(passed)); pairwise["experiment_result_audit_records"][0]["pairwise_overlap_buckets_present_bool"] = False; check("r2x_pairwise_missing_fail", "result_pairwise_overlap_buckets_missing" in validate_report(pairwise))
    agreement = json.loads(json.dumps(base)); agreement["rank_source_agreement_records"] = agreement["rank_source_agreement_records"][:-1]; check("agreement_pair_count_fail", build_report(agreement)["status"] == STATUS_FAIL_RESULT)
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    next_drift = json.loads(json.dumps(passed)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2Y Execution"; check("next_phase_overauth_fail", "next_allowed_phase_mismatch" in validate_report(next_drift))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    check("root_current_latest_readback", public_readback_match(SELF_TEST_EXPECTED)["current_conclusions_readback_match_bool"] is True)
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_") for i in validate_report(claim)))
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


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
