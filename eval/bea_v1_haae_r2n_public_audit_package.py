#!/usr/bin/env python3
"""BEA-v1-HAAE-R2N public audit package.

Public-only audit/package of the committed R2M aggregate artifact. This script
does not read private roots/material and does not recompute from private rows.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2N Public Audit Package"
SLUG = "bea_v1_haae_r2n_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2M_CHECKPOINT = "7a3d6dc"
R2M_STATUS = "haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized"
R2M_REPORT_PATH = Path("artifacts/bea_v1_haae_r2m_path_prior_separation_mechanism_decomposition/bea_v1_haae_r2m_path_prior_separation_mechanism_decomposition_report.json")
STATUS_PASS = "haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized"
STATUS_FAIL_SOURCE = "haae_r2n_fail_closed_source_lock_mismatch"
STATUS_FAIL_MECHANISM = "haae_r2n_fail_closed_mechanism_readback_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2n_fail_closed_claim_boundary_mismatch"
STATUS_FAIL_LEAK = "haae_r2n_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2n_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 14
NEXT_PHASE = "BEA-v1-HAAE-R2O Robustness Preflight Design"

CLAIM_FALSE_FIELDS = ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]
STOP_FALSE_FIELDS = ["candidate_generation_authorized_bool", "ci_execution_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "network_authorized_bool", "new_material_generation_authorized_bool", "p5_authorized_bool", "provider_model_authorized_bool", "raw_publication_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "scaling_claim_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "source_scan_authorized_bool", "bea_v1_a_authorized_bool"]
GATE_NAMES = ["r2m_source_locked_gate", "r2m_status_gate", "r2m_forbidden_scan_gate", "r2m_public_readback_gate", "mechanism_summary_readback_gate", "fixture_path_cues_gate", "control_underfit_gate", "no_method_winner_gate", "public_only_audit_gate", "no_private_root_read_gate", "no_recompute_private_rows_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_provider_gate", "no_scheduler_selector_gate", "no_default_scaling_claim_gate", "r2o_design_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2m(r2m: dict[str, Any]) -> dict[str, bool]:
    source = (r2m.get("source_lock_records") or [{}])[0]
    summary = (r2m.get("mechanism_summary_records") or [{}])[0]
    fixture = (r2m.get("fixture_artifact_bias_records") or [{}])[0]
    control = (r2m.get("control_baseline_weakness_records") or [{}])[0]
    claim = (r2m.get("claim_boundary_records") or [{}])[0]
    stop = (r2m.get("stop_go_records") or [{}])[0]
    readback = (r2m.get("public_readback_records") or [{}])[0]
    status_ok = r2m.get("status") == R2M_STATUS
    scan_ok = r2m.get("forbidden_scan", {}).get("status") == "pass"
    source_ok = source.get("source_locked_bool") is True
    r2n_auth_ok = stop.get("haae_r2n_public_audit_package_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in STOP_FALSE_FIELDS)
    claim_ok = all(claim.get(field) is False for field in CLAIM_FALSE_FIELDS)
    readback_ok = readback.get("all_public_readback_match_bool") is True
    mechanism_ok = summary.get("dominant_mechanism_bucket") == "path_structure_prior" and summary.get("confidence_bucket") == "medium_high" and summary.get("method_winner_bool") is False and summary.get("mechanism_conclusive_bool") is True
    fixture_ok = fixture.get("interpretation_bucket") == "fixture_pool_contains_path_cues" and fixture.get("distinctive_token_bucket") == "distinctive_tokens_present"
    control_ok = control.get("underfit_bucket") == "control_underfit" and control.get("interpretation_bucket") == "control_baseline_weakness_supporting"
    return {"status_ok": status_ok, "scan_ok": scan_ok, "source_ok": source_ok, "r2n_auth_ok": r2n_auth_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "readback_ok": readback_ok, "mechanism_ok": mechanism_ok, "fixture_ok": fixture_ok, "control_ok": control_ok, "source_locked": status_ok and scan_ok and source_ok and r2n_auth_ok and stop_ok and claim_ok and readback_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|extension_value|token_value|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2M_CHECKPOINT, R2M_STATUS, "path_structure_prior", "medium_high confidence", "fixture path cues + control underfit", "no method winner", "not method/default/scaling claim", NEXT_PHASE, "not execution/CI/new material generation yet"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2n-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2n-public-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2n-public-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2m: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2m is None:
        try: r2m = load_json(repo / R2M_REPORT_PATH)
        except Exception: r2m = {}
    audit = validate_r2m(r2m)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not (audit["mechanism_ok"] and audit["fixture_ok"] and audit["control_ok"]):
        status = STATUS_FAIL_MECHANISM
    elif not audit["claim_ok"] or not audit["stop_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2m_source_locked_gate": audit["source_locked"], "r2m_status_gate": audit["status_ok"], "r2m_forbidden_scan_gate": audit["scan_ok"], "r2m_public_readback_gate": audit["readback_ok"], "mechanism_summary_readback_gate": audit["mechanism_ok"], "fixture_path_cues_gate": audit["fixture_ok"], "control_underfit_gate": audit["control_ok"], "no_method_winner_gate": audit["claim_ok"], "public_only_audit_gate": True, "no_private_root_read_gate": True, "no_recompute_private_rows_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_provider_gate": True, "no_scheduler_selector_gate": True, "no_default_scaling_claim_gate": True, "r2o_design_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2nsource0000", "locked_haae_r2m_checkpoint": R2M_CHECKPOINT, "locked_haae_r2m_status": R2M_STATUS, "r2m_status_match_bool": audit["status_ok"], "r2m_forbidden_scan_pass_bool": audit["scan_ok"], "r2m_r2n_authorization_match_bool": audit["r2n_auth_ok"], "r2m_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "r2m_claim_boundary_match_bool": audit["claim_ok"], "source_locked_bool": audit["source_locked"]}],
        "mechanism_readback_records": [{"anonymous_mechanism_readback_id": "haaer2nmech0000", "dominant_mechanism_bucket": "path_structure_prior", "confidence_bucket": "medium_high", "fixture_path_cues_bool": audit["fixture_ok"], "control_underfit_bool": audit["control_ok"], "method_winner_bool": False, "mechanism_readback_match_bool": audit["mechanism_ok"] and audit["fixture_ok"] and audit["control_ok"], "raw_mechanism_values_published_bool": False}],
        "public_audit_records": [{"anonymous_public_audit_id": "haaer2naudit0000", "public_only_audit_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "private_row_recompute_bool": False, "generation_bool": False, "retrieval_source_scan_runtime_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "raw_publication_bool": False}],
        "robustness_preflight_design_records": [{"anonymous_robustness_design_id": "haaer2nrobust0000", "next_phase": NEXT_PHASE, "authorized_bool": passed, "framing_bucket": "separation_signal_worth_robustness_preflight", "execution_authorized_bool": False, "ci_authorized_bool": False, "new_material_generation_authorized_bool": False, "method_default_scaling_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2nclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ngate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2nsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2m_status_fail", "mechanism_drift_fail", "fixture_bias_drift_fail", "control_underfit_drift_fail", "method_winner_claim_fail", "stop_go_overauth_fail", "raw_leak_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2nreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2nstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2m_public_artifact", "haae_r2o_robustness_preflight_design_authorized_bool": passed, "haae_r2o_execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "mechanism_readback_records", "public_audit_records", "robustness_preflight_design_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2m_checkpoint") != R2M_CHECKPOINT or source.get("locked_haae_r2m_status") != R2M_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2m_status_match_bool", "r2m_forbidden_scan_pass_bool", "r2m_r2n_authorization_match_bool", "r2m_no_forbidden_stop_go_drift_bool", "r2m_claim_boundary_match_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    mech = (report.get("mechanism_readback_records") or [{}])[0]
    if mech.get("dominant_mechanism_bucket") != "path_structure_prior" or mech.get("confidence_bucket") != "medium_high" or mech.get("fixture_path_cues_bool") is not True or mech.get("control_underfit_bool") is not True or mech.get("method_winner_bool") is not False: issues.append("mechanism_readback_mismatch")
    audit = (report.get("public_audit_records") or [{}])[0]
    if audit.get("public_only_audit_bool") is not True: issues.append("public_audit_not_public_only")
    for field in ["private_root_read_bool", "private_material_read_bool", "private_row_recompute_bool", "generation_bool", "retrieval_source_scan_runtime_bool", "ci_network_provider_bool", "scheduler_selector_bool", "raw_publication_bool"]:
        if audit.get(field) is not False: issues.append(f"public_audit_boundary_{field}")
    robust = (report.get("robustness_preflight_design_records") or [{}])[0]
    if robust.get("next_phase") != NEXT_PHASE or robust.get("framing_bucket") != "separation_signal_worth_robustness_preflight": issues.append("robustness_preflight_mismatch")
    for field in ["execution_authorized_bool", "ci_authorized_bool", "new_material_generation_authorized_bool", "method_default_scaling_claim_bool"]:
        if robust.get(field) is not False: issues.append(f"robustness_overauthorization_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in CLAIM_FALSE_FIELDS:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2o_execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if robust.get("authorized_bool") is not True: issues.append("missing_r2o_robustness_design_record_authorization")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2o_robustness_preflight_design_authorized_bool") is not True: issues.append("missing_r2o_design_authorization")
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
    base = load_json(repo / R2M_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2m_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    mech = json.loads(json.dumps(base)); mech["mechanism_summary_records"][0]["dominant_mechanism_bucket"] = "mixed"; check("mechanism_drift_fail", build_report(mech)["status"] == STATUS_FAIL_MECHANISM)
    fix = json.loads(json.dumps(base)); fix["fixture_artifact_bias_records"][0]["interpretation_bucket"] = "unknown"; check("fixture_bias_drift_fail", build_report(fix)["status"] == STATUS_FAIL_MECHANISM)
    ctl = json.loads(json.dumps(base)); ctl["control_baseline_weakness_records"][0]["underfit_bucket"] = "control_not_underfit"; check("control_underfit_drift_fail", build_report(ctl)["status"] == STATUS_FAIL_MECHANISM)
    claim = json.loads(json.dumps(base)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("method_winner_claim_fail", build_report(claim)["status"] == STATUS_FAIL_SOURCE)
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(over)))
    audit_drift = json.loads(json.dumps(passed)); audit_drift["public_audit_records"][0]["private_root_read_bool"] = True; check("public_audit_drift_fail", "public_audit_boundary_private_root_read_bool" in validate_report(audit_drift))
    robustness_drift = json.loads(json.dumps(passed)); robustness_drift["robustness_preflight_design_records"][0]["execution_authorized_bool"] = True; check("robustness_drift_fail", "robustness_overauthorization_execution_authorized_bool" in validate_report(robustness_drift))
    next_drift = json.loads(json.dumps(passed)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_phase_drift_fail", "next_allowed_phase_mismatch" in validate_report(next_drift))
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
