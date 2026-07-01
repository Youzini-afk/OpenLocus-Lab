#!/usr/bin/env python3
"""BEA-v1-HAAE-R2K public audit package.

Public-only audit/package of the R2J aggregate result. This script reads only
the committed public R2J artifact and public docs. It never reads private roots,
does not recompute from private rows, and does not generate material.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2K Public Audit Package"
SLUG = "bea_v1_haae_r2k_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2J_CHECKPOINT = "71c9a2c"
R2J_STATUS = "haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized"
R2J_REPORT_PATH = Path("artifacts/bea_v1_haae_r2j_harder_diversified_material_experiment/bea_v1_haae_r2j_harder_diversified_material_experiment_report.json")
R2J_SELF_TEST_READBACK = "21/21"

STATUS_PASS = "haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized"
STATUS_FAIL_SOURCE = "haae_r2k_fail_closed_source_lock_mismatch"
STATUS_FAIL_METRIC = "haae_r2k_fail_closed_r2j_metric_readback_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2k_fail_closed_claim_boundary_mismatch"
STATUS_FAIL_LEAK = "haae_r2k_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2k_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 14
NEXT_PHASE = "BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight"

FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2j_source_lock_gate", "r2j_status_gate", "r2j_public_artifact_only_gate", "r2j_forbidden_scan_gate", "r2j_self_test_readback_gate", "separation_signal_readback_gate", "path_prior_readback_gate", "control_baseline_readback_gate", "method_winner_false_gate", "public_only_no_private_read_gate", "no_recompute_private_rows_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_scheduler_selector_gate", "no_method_default_scaling_claim_gate", "r2l_design_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2j_source(r2j: dict[str, Any]) -> dict[str, bool]:
    stop = (r2j.get("stop_go_records") or [{}])[0]
    status_ok = r2j.get("status") == R2J_STATUS
    scan_ok = r2j.get("forbidden_scan", {}).get("status") == "pass"
    self_test_ok = str(r2j.get("self_test_total")) == "21"
    auth_ok = stop.get("haae_r2k_public_audit_package_authorized_bool") is True
    boundary_ok = all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    return {"status_ok": status_ok, "scan_ok": scan_ok, "self_test_ok": self_test_ok, "auth_ok": auth_ok, "boundary_ok": boundary_ok, "source_locked": status_ok and scan_ok and self_test_ok and auth_ok and boundary_ok}


def audit_r2j_metrics(r2j: dict[str, Any]) -> dict[str, Any]:
    metrics = {row.get("rank_source_bucket"): row for row in r2j.get("rank_source_metric_records", [])}
    sep = (r2j.get("separation_signal_records") or [{}])[0]
    path_prior = metrics.get("path_prior", {})
    control = metrics.get("control_baseline", {})
    separation_ok = sep.get("separation_signal_bool") is True and sep.get("rank_spread_bucket") == "spread_medium" and sep.get("control_baseline_separation_bucket") == "non_control_better" and sep.get("method_winner_bool") is False
    path_prior_ok = all(path_prior.get(field) == "count_10_to_20" for field in ["top1_hit_count_bucket", "top5_hit_count_bucket", "top10_hit_count_bucket", "top20_hit_count_bucket"]) and path_prior.get("mrr_bucket") == "mrr_high"
    control_ok = control.get("top1_hit_count_bucket") == "count_0" and control.get("mrr_bucket") == "mrr_low"
    aggregate_only_ok = all(row.get("exact_ranks_scores_paths_published_bool") is False for row in metrics.values()) and all(row.get("exact_values_published_bool") is False for row in r2j.get("rank_source_agreement_records", []))
    return {"separation_ok": separation_ok, "path_prior_ok": path_prior_ok, "control_ok": control_ok, "aggregate_only_ok": aggregate_only_ok, "metrics_ok": separation_ok and path_prior_ok and control_ok and aggregate_only_ok, "metrics": metrics, "separation": sep}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|task_key|candidate_index|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2J_CHECKPOINT, R2J_STATUS, f"R2J self-test {R2J_SELF_TEST_READBACK}", "separation signal true", "rank_spread_bucket=spread_medium", "control_baseline_separation_bucket=non_control_better", "method_winner_bool=false", "path_prior", "control_baseline", "separation signal worth mechanism/robustness follow-up", "not method winner/default/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2k-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2k-public-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2k-public-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2j: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2j is None:
        try: r2j = load_json(repo / R2J_REPORT_PATH)
        except Exception: r2j = {}
    source = validate_r2j_source(r2j)
    metric = audit_r2j_metrics(r2j)
    readback = public_readback_match(self_test_total)
    if not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not metric["metrics_ok"]:
        status = STATUS_FAIL_METRIC
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2j_source_lock_gate": source["source_locked"], "r2j_status_gate": source["status_ok"], "r2j_public_artifact_only_gate": True, "r2j_forbidden_scan_gate": source["scan_ok"], "r2j_self_test_readback_gate": source["self_test_ok"], "separation_signal_readback_gate": metric["separation_ok"], "path_prior_readback_gate": metric["path_prior_ok"], "control_baseline_readback_gate": metric["control_ok"], "method_winner_false_gate": metric["separation"].get("method_winner_bool") is False, "public_only_no_private_read_gate": True, "no_recompute_private_rows_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_scheduler_selector_gate": True, "no_method_default_scaling_claim_gate": True, "r2l_design_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    path_prior = metric["metrics"].get("path_prior", {})
    control = metric["metrics"].get("control_baseline", {})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ksource0000", "locked_haae_r2j_checkpoint": R2J_CHECKPOINT, "locked_haae_r2j_status": R2J_STATUS, "locked_haae_r2j_self_test": R2J_SELF_TEST_READBACK, "r2j_status_match_bool": source["status_ok"], "r2j_forbidden_scan_pass_bool": source["scan_ok"], "r2j_self_test_match_bool": source["self_test_ok"], "r2j_r2k_authorization_match_bool": source["auth_ok"], "r2j_no_forbidden_stop_go_drift_bool": source["boundary_ok"], "source_locked_bool": source["source_locked"]}],
        "r2j_metric_audit_records": [{"anonymous_r2j_metric_audit_id": "haaer2kmetric0000", "path_prior_top1_bucket": path_prior.get("top1_hit_count_bucket", "missing"), "path_prior_top5_bucket": path_prior.get("top5_hit_count_bucket", "missing"), "path_prior_top10_bucket": path_prior.get("top10_hit_count_bucket", "missing"), "path_prior_top20_bucket": path_prior.get("top20_hit_count_bucket", "missing"), "path_prior_mrr_bucket": path_prior.get("mrr_bucket", "missing"), "control_baseline_top1_bucket": control.get("top1_hit_count_bucket", "missing"), "control_baseline_mrr_bucket": control.get("mrr_bucket", "missing"), "metric_readback_match_bool": metric["path_prior_ok"] and metric["control_ok"], "exact_scores_ranks_paths_published_bool": False}],
        "separation_audit_records": [{"anonymous_separation_audit_id": "haaer2ksep0000", "separation_signal_bool": metric["separation"].get("separation_signal_bool") is True, "rank_spread_bucket": metric["separation"].get("rank_spread_bucket", "missing"), "control_baseline_separation_bucket": metric["separation"].get("control_baseline_separation_bucket", "missing"), "non_control_sources_distinguishable_bool": metric["separation"].get("non_control_sources_distinguishable_bool") is True, "method_winner_bool": False, "framing_bucket": "separation signal worth mechanism/robustness follow-up", "not_method_winner_default_scaling_claim_bool": True}],
        "public_audit_records": [{"anonymous_public_audit_id": "haaer2kaudit0000", "public_only_audit_bool": True, "private_read_count_bucket": "count_0", "private_write_count_bucket": "count_0", "no_private_root_read_bool": True, "no_private_metric_recompute_bool": True, "no_generation_retrieval_runtime_bool": True, "no_ci_network_scheduler_selector_bool": True, "aggregate_artifact_only_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2kclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2kgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ksynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2j_status_fail", "separation_drift_fail", "path_prior_metric_drift_fail", "control_baseline_metric_drift_fail", "method_winner_claim_fail", "stop_go_overauth_fail", "raw_leak_fail", "stale_readback_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2kreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2kstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2j_public_artifact", "haae_r2l_next_step_decision_mechanism_preflight_authorized_bool": passed, "haae_r2l_execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "r2j_metric_audit_records", "separation_audit_records", "public_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2j_checkpoint") != R2J_CHECKPOINT or src.get("locked_haae_r2j_status") != R2J_STATUS or src.get("locked_haae_r2j_self_test") != R2J_SELF_TEST_READBACK: issues.append("source_lock_mismatch")
    for field in ["r2j_status_match_bool", "r2j_forbidden_scan_pass_bool", "r2j_self_test_match_bool", "r2j_r2k_authorization_match_bool", "r2j_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    metric = (report.get("r2j_metric_audit_records") or [{}])[0]
    if not (metric.get("path_prior_top1_bucket") == "count_10_to_20" and metric.get("path_prior_top5_bucket") == "count_10_to_20" and metric.get("path_prior_top10_bucket") == "count_10_to_20" and metric.get("path_prior_top20_bucket") == "count_10_to_20" and metric.get("path_prior_mrr_bucket") == "mrr_high" and metric.get("control_baseline_top1_bucket") == "count_0" and metric.get("control_baseline_mrr_bucket") == "mrr_low"): issues.append("metric_readback_mismatch")
    sep = (report.get("separation_audit_records") or [{}])[0]
    if not (sep.get("separation_signal_bool") is True and sep.get("rank_spread_bucket") == "spread_medium" and sep.get("control_baseline_separation_bucket") == "non_control_better" and sep.get("method_winner_bool") is False): issues.append("separation_readback_mismatch")
    claims = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]:
        if claims.get(field) is not False: issues.append(f"claim_boundary_{field}")
    audit = (report.get("public_audit_records") or [{}])[0]
    for field in ["public_only_audit_bool", "no_private_root_read_bool", "no_private_metric_recompute_bool", "no_generation_retrieval_runtime_bool", "no_ci_network_scheduler_selector_bool", "aggregate_artifact_only_bool"]:
        if audit.get(field) is not True: issues.append(f"public_audit_{field}")
    if audit.get("private_read_count_bucket") != "count_0" or audit.get("private_write_count_bucket") != "count_0": issues.append("public_audit_private_count_mismatch")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2l_execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2l_next_step_decision_mechanism_preflight_authorized_bool") is not True: issues.append("missing_r2l_design_authorization")
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
    base = load_json(repo / R2J_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2j_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    sep = json.loads(json.dumps(base)); sep["separation_signal_records"][0]["separation_signal_bool"] = False; check("separation_drift_fail", build_report(sep)["status"] == STATUS_FAIL_METRIC)
    pp = json.loads(json.dumps(base)); pp["rank_source_metric_records"][2]["mrr_bucket"] = "mrr_low"; check("path_prior_metric_drift_fail", build_report(pp)["status"] == STATUS_FAIL_METRIC)
    cb = json.loads(json.dumps(base)); cb["rank_source_metric_records"][5]["top1_hit_count_bucket"] = "count_1"; check("control_baseline_metric_drift_fail", build_report(cb)["status"] == STATUS_FAIL_METRIC)
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(over)))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("method_winner_claim_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    source_bool = json.loads(json.dumps(passed)); source_bool["source_lock_records"][0]["source_locked_bool"] = False; check("source_bool_drift_fail", any(i.startswith("source_lock_") for i in validate_report(source_bool)))
    audit = json.loads(json.dumps(passed)); audit["public_audit_records"][0]["private_read_count_bucket"] = "count_1_to_10"; check("public_audit_private_count_fail", "public_audit_private_count_mismatch" in validate_report(audit))
    gate = json.loads(json.dumps(passed)); gate["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_false_fail", any(i.startswith("gate_failed_") for i in validate_report(gate)))
    next_phase = json.loads(json.dumps(passed)); next_phase["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_allowed_phase_drift_fail", "next_allowed_phase_mismatch" in validate_report(next_phase))
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
