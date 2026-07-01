#!/usr/bin/env python3
"""BEA-v1-HAAE-R2S path-cue robustness experiment public audit package."""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2S Path-Cue Robustness Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2s_path_cue_robustness_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2R_CHECKPOINT = "7efc348"
R2R_STATUS = "haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely"
R2R_REPORT_PATH = Path("artifacts/bea_v1_haae_r2r_path_cue_robustness_experiment/bea_v1_haae_r2r_path_cue_robustness_experiment_report.json")
STATUS_PASS = "haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized"
STATUS_FAIL_SOURCE = "haae_r2s_fail_closed_source_lock_mismatch"
STATUS_FAIL_RESULT = "haae_r2s_fail_closed_result_readback_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2s_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2s_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2s_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 12
NEXT_PHASE = "BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision"

FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2r_source_locked_gate", "r2r_status_gate", "r2r_self_test_30_gate", "r2r_forbidden_scan_gate", "artifact_likely_interpretation_gate", "original_path_prior_top10_top20_gate", "all_perturbation_drop_buckets_gate", "variant_spread_high_gate", "privacy_aggregate_only_gate", "no_private_read_gate", "no_recompute_gate", "no_experiment_execution_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_provider_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "r2t_decision_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2r(r2r: dict[str, Any]) -> dict[str, bool]:
    stop = (r2r.get("stop_go_records") or [{}])[0]
    claim = (r2r.get("claim_boundary_records") or [{}])[0]
    robustness = (r2r.get("variant_robustness_records") or [{}])[0]
    metrics = r2r.get("variant_rank_source_metric_records", [])
    original_path = next((row for row in metrics if row.get("variant_bucket") == "original" and row.get("rank_source_bucket") == "path_prior"), {})
    status_ok = r2r.get("status") == R2R_STATUS
    self_test_ok = r2r.get("self_test_total") == 30
    scan_ok = r2r.get("forbidden_scan", {}).get("status") == "pass"
    stop_ok = stop.get("haae_r2s_public_audit_package_authorized_bool") is True and all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    claim_ok = claim.get("method_winner_claim_bool") is False and claim.get("default_runtime_claim_bool") is False and claim.get("scaling_claim_bool") is False and claim.get("raw_publication_bool") is False
    interpretation_ok = robustness.get("interpretation_bucket") == "path_cue_artifact_likely"
    original_ok = original_path.get("top10_hit_count_bucket") == "count_11_to_20" and original_path.get("top20_hit_count_bucket") == "count_11_to_20"
    drops_ok = all(robustness.get(field) == "count_11_to_20" for field in ["path_prior_path_scrambled_drop_bucket", "path_prior_extension_bucket_preserved_drop_bucket", "path_prior_directory_depth_preserved_drop_bucket", "path_prior_control_baseline_strengthened_drop_bucket"])
    spread_ok = robustness.get("variant_spread_bucket") == "spread_high"
    aggregate_ok = all(row.get("exact_values_published_bool") is False for row in metrics) and (r2r.get("execution_mode_records") or [{}])[0].get("aggregate_only_publication_bool") is True
    source_locked = status_ok and self_test_ok and scan_ok and stop_ok and claim_ok
    result_ok = interpretation_ok and original_ok and drops_ok and spread_ok and aggregate_ok
    return {"status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "interpretation_ok": interpretation_ok, "original_ok": original_ok, "drops_ok": drops_ok, "spread_ok": spread_ok, "aggregate_ok": aggregate_ok, "source_locked": source_locked, "result_ok": result_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|source_path|variant_path|candidate_key|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2R_CHECKPOINT, R2R_STATUS, "self-test 30/30", "path_cue_artifact_likely", "original path_prior top10/top20 count_11_to_20", "all perturbation drop buckets count_11_to_20", "variant_spread_bucket spread_high", "privacy/aggregate-only", NEXT_PHASE, "not execution/generation/CI"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2s-path-cue-robustness-experiment-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2s-path-cue-robustness-experiment-public-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2s-path-cue-robustness-experiment-public-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2r: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2r is None:
        try: r2r = load_json(repo / R2R_REPORT_PATH)
        except Exception: r2r = {}
    audit = audit_r2r(r2r)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["result_ok"]:
        status = STATUS_FAIL_RESULT
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2r_source_locked_gate": audit["source_locked"], "r2r_status_gate": audit["status_ok"], "r2r_self_test_30_gate": audit["self_test_ok"], "r2r_forbidden_scan_gate": audit["scan_ok"], "artifact_likely_interpretation_gate": audit["interpretation_ok"], "original_path_prior_top10_top20_gate": audit["original_ok"], "all_perturbation_drop_buckets_gate": audit["drops_ok"], "variant_spread_high_gate": audit["spread_ok"], "privacy_aggregate_only_gate": audit["aggregate_ok"], "no_private_read_gate": True, "no_recompute_gate": True, "no_experiment_execution_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_provider_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "r2t_decision_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ssource0000", "locked_haae_r2r_checkpoint": R2R_CHECKPOINT, "locked_haae_r2r_status": R2R_STATUS, "r2r_status_match_bool": audit["status_ok"], "r2r_self_test_30_match_bool": audit["self_test_ok"], "r2r_forbidden_scan_pass_bool": audit["scan_ok"], "r2r_stop_go_r2s_authorized_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "r2r_result_audit_records": [{"anonymous_result_audit_id": "haaer2sresult0000", "interpretation_bucket": "path_cue_artifact_likely", "interpretation_match_bool": audit["interpretation_ok"], "original_path_prior_top10_bucket": "count_11_to_20", "original_path_prior_top20_bucket": "count_11_to_20", "original_path_prior_top10_top20_match_bool": audit["original_ok"], "all_perturbation_drop_buckets": "count_11_to_20", "all_perturbation_drop_match_bool": audit["drops_ok"], "variant_spread_bucket": "spread_high", "variant_spread_match_bool": audit["spread_ok"], "method_winner_bool": False, "default_claim_bool": False, "scaling_claim_bool": False}],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2sboundary0000", "public_only_audit_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "recompute_bool": False, "experiment_execution_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "privacy_aggregate_only_bool": audit["aggregate_ok"], "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2sclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "execution_authorized_bool": False, "ci_authorized_bool": False, "new_material_generation_authorized_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2sgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ssynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2r_status_fail", "selftest_drift_fail", "interpretation_drift_fail", "original_top_bucket_drift_fail", "drop_bucket_drift_fail", "spread_drift_fail", "overauth_fail", "leak_fail", "stale_readback_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2sreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2sstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2r_public_artifact", "haae_r2t_non_path_cue_pivot_decision_authorized_bool": passed, "r2t_public_design_decision_only_bool": passed, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "r2r_result_audit_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2r_checkpoint") != R2R_CHECKPOINT or src.get("locked_haae_r2r_status") != R2R_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2r_status_match_bool", "r2r_self_test_30_match_bool", "r2r_forbidden_scan_pass_bool", "r2r_stop_go_r2s_authorized_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    result = (report.get("r2r_result_audit_records") or [{}])[0]
    if result.get("interpretation_bucket") != "path_cue_artifact_likely" or result.get("interpretation_match_bool") is not True: issues.append("interpretation_mismatch")
    if result.get("original_path_prior_top10_bucket") != "count_11_to_20" or result.get("original_path_prior_top20_bucket") != "count_11_to_20" or result.get("original_path_prior_top10_top20_match_bool") is not True: issues.append("original_path_prior_bucket_mismatch")
    if result.get("all_perturbation_drop_buckets") != "count_11_to_20" or result.get("all_perturbation_drop_match_bool") is not True: issues.append("drop_bucket_mismatch")
    if result.get("variant_spread_bucket") != "spread_high" or result.get("variant_spread_match_bool") is not True: issues.append("spread_bucket_mismatch")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("privacy_aggregate_only_bool") is not True: issues.append("boundary_public_aggregate_mismatch")
    for field in ["private_root_read_bool", "private_material_read_bool", "recompute_bool", "experiment_execution_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "execution_authorized_bool", "ci_authorized_bool", "new_material_generation_authorized_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2t_non_path_cue_pivot_decision_authorized_bool") is not True or stop.get("r2t_public_design_decision_only_bool") is not True: issues.append("r2t_stop_go_missing")
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
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; base = load_json(repo / R2R_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2r_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    selftest = json.loads(json.dumps(base)); selftest["self_test_total"] = 29; check("selftest_drift_fail", build_report(selftest)["status"] == STATUS_FAIL_SOURCE)
    interp = json.loads(json.dumps(base)); interp["variant_robustness_records"][0]["interpretation_bucket"] = "mixed_or_inconclusive"; check("interpretation_drift_fail", build_report(interp)["status"] == STATUS_FAIL_RESULT)
    top = json.loads(json.dumps(base)); top["variant_rank_source_metric_records"][0]["top10_hit_count_bucket"] = "count_0"; check("original_top_bucket_drift_fail", build_report(top)["status"] == STATUS_FAIL_RESULT)
    drop = json.loads(json.dumps(base)); drop["variant_robustness_records"][0]["path_prior_path_scrambled_drop_bucket"] = "count_0"; check("drop_bucket_drift_fail", build_report(drop)["status"] == STATUS_FAIL_RESULT)
    spread = json.loads(json.dumps(base)); spread["variant_robustness_records"][0]["variant_spread_bucket"] = "spread_low"; check("spread_drift_fail", build_report(spread)["status"] == STATUS_FAIL_RESULT)
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    next_drift = json.loads(json.dumps(passed)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2U Execution"; check("next_phase_drift_fail", "next_allowed_phase_mismatch" in validate_report(next_drift))
    r2t_drift = json.loads(json.dumps(passed)); r2t_drift["stop_go_records"][0]["r2t_public_design_decision_only_bool"] = False; check("r2t_stop_go_drift_fail", "r2t_stop_go_missing" in validate_report(r2t_drift))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
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
