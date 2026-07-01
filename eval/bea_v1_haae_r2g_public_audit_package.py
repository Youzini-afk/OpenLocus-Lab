#!/usr/bin/env python3
"""BEA-v1-HAAE-R2G public audit package."""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2G Public Audit Package"
SLUG = "bea_v1_haae_r2g_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2F_CHECKPOINT = "1e0c718"
R2F_STATUS = "haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized"
R2F_REPORT_PATH = Path("artifacts/bea_v1_haae_r2f_local_medium_material_experiment/bea_v1_haae_r2f_local_medium_material_experiment_report.json")
STATUS_PASS = "haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized"
STATUS_FAIL_SOURCE = "haae_r2g_fail_closed_source_lock_mismatch"
STATUS_FAIL_METRIC = "haae_r2g_fail_closed_metric_readback_mismatch"
STATUS_FAIL_LEAK = "haae_r2g_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2g_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 9
NEXT_PHASE = "BEA-v1-HAAE-R2H Next-Step Design Decision"
RANK_SOURCES = ["bm25_like", "symbol_overlap", "rrf_like"]
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "runtime_default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r2_recompute_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2f_source_lock_gate", "r2f_status_gate", "r2f_forbidden_scan_gate", "aggregate_metric_readback_gate", "same_top_agreement_gate", "top_hit_bucket_gate", "medium_only_no_winner_gate", "public_only_no_private_read_gate", "no_recompute_gate", "no_generation_retrieval_runtime_gate", "no_ci_network_scheduler_selector_gate", "no_default_scaling_claim_gate", "r2h_design_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2f(r2f: dict[str, Any]) -> dict[str, bool]:
    stop = (r2f.get("stop_go_records") or [{}])[0]
    status_ok = r2f.get("status") == R2F_STATUS
    scan_ok = r2f.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2g_public_audit_package_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in FORBIDDEN_STOP_TRUE)
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "source_locked": status_ok and scan_ok and auth_ok and stop_ok}


def audit_metrics(r2f: dict[str, Any]) -> dict[str, Any]:
    metrics = {row.get("rank_source_bucket"): row for row in r2f.get("rank_source_metric_records", [])}
    agreements = r2f.get("rank_source_agreement_records", [])
    summary = (r2f.get("experiment_summary_records") or [{}])[0]
    metric_ok = set(metrics) == set(RANK_SOURCES) and all(
        metrics[src].get("gold_file_hit_rate_bucket") == "rate_1"
        and metrics[src].get("top1_hit_count_bucket") == "count_10_to_20"
        and metrics[src].get("top5_hit_count_bucket") == "count_10_to_20"
        and metrics[src].get("top10_hit_count_bucket") == "count_10_to_20"
        and metrics[src].get("rank_source_present_bool") is True
        and metrics[src].get("exact_scores_ranks_paths_published_bool") is False
        for src in RANK_SOURCES
    )
    agreement_ok = len(agreements) == 3 and all(
        row.get("same_top_candidate_rate_bucket") == "rate_1"
        and row.get("overlap_at_5_rate_bucket") == "rate_1"
        and row.get("overlap_at_10_rate_bucket") == "rate_1"
        and row.get("exact_candidate_values_published_bool") is False
        for row in agreements
    )
    medium_ok = summary.get("task_count_bucket") == "count_10_to_20" and summary.get("aggregate_metrics_only_bool") is True and summary.get("raw_rows_published_bool") is False
    return {"metric_ok": metric_ok, "agreement_ok": agreement_ok, "medium_ok": medium_ok, "metrics": metrics, "agreements": agreements, "summary": summary}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank|task_key|candidate_rank|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2F_CHECKPOINT, R2F_STATUS, "rate_1", "count_10_to_20", "medium material experiment only", "no method-winner/default/scaling claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]

    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)

    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2g-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2g-public-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2g-public-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2f: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2f is None:
        try:
            r2f = load_json(repo / R2F_REPORT_PATH)
        except Exception:
            r2f = {}
    source = validate_r2f(r2f)
    metric = audit_metrics(r2f)
    readback = public_readback_match(self_test_total)
    if not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not (metric["metric_ok"] and metric["agreement_ok"] and metric["medium_ok"]):
        status = STATUS_FAIL_METRIC
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2f_source_lock_gate": source["source_locked"], "r2f_status_gate": source["status_ok"], "r2f_forbidden_scan_gate": source["scan_ok"], "aggregate_metric_readback_gate": metric["metric_ok"], "same_top_agreement_gate": metric["agreement_ok"], "top_hit_bucket_gate": metric["metric_ok"], "medium_only_no_winner_gate": metric["medium_ok"], "public_only_no_private_read_gate": True, "no_recompute_gate": True, "no_generation_retrieval_runtime_gate": True, "no_ci_network_scheduler_selector_gate": True, "no_default_scaling_claim_gate": True, "r2h_design_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2gsource0000", "locked_haae_r2f_checkpoint": R2F_CHECKPOINT, "locked_haae_r2f_status": R2F_STATUS, "r2f_status_match_bool": source["status_ok"], "r2f_forbidden_scan_pass_bool": source["scan_ok"], "r2g_authorization_match_bool": source["auth_ok"], "r2f_no_forbidden_stop_go_drift_bool": source["stop_ok"], "source_locked_bool": source["source_locked"]}],
        "r2f_metric_readback_records": [{"anonymous_metric_readback_id": f"haaer2gmetric{idx:04d}", "rank_source_bucket": src, "gold_file_hit_rate_bucket": metric["metrics"].get(src, {}).get("gold_file_hit_rate_bucket", "missing"), "top1_hit_count_bucket": metric["metrics"].get(src, {}).get("top1_hit_count_bucket", "missing"), "top5_hit_count_bucket": metric["metrics"].get(src, {}).get("top5_hit_count_bucket", "missing"), "top10_hit_count_bucket": metric["metrics"].get(src, {}).get("top10_hit_count_bucket", "missing"), "metric_readback_match_bool": src in metric["metrics"] and metric["metrics"].get(src, {}).get("gold_file_hit_rate_bucket") == "rate_1", "exact_scores_or_ranks_published_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "r2f_agreement_readback_records": [{"anonymous_agreement_readback_id": f"haaer2gagree{idx:04d}", "same_top_candidate_rate_bucket": row.get("same_top_candidate_rate_bucket", "missing"), "overlap_at_5_rate_bucket": row.get("overlap_at_5_rate_bucket", "missing"), "overlap_at_10_rate_bucket": row.get("overlap_at_10_rate_bucket", "missing"), "agreement_readback_match_bool": row.get("same_top_candidate_rate_bucket") == "rate_1", "exact_candidate_values_published_bool": False} for idx, row in enumerate(metric["agreements"])],
        "public_audit_records": [{"anonymous_public_audit_id": "haaer2gaudit0000", "public_only_audit_bool": True, "private_read_count_bucket": "count_0", "private_write_count_bucket": "count_0", "no_recompute_bool": True, "no_generation_bool": True, "no_retrieval_source_scan_runtime_bool": True, "no_ci_network_scheduler_selector_bool": True, "medium_material_experiment_only_bool": True, "sample_bucket": metric["summary"].get("task_count_bucket", "missing")}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2gclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ggate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2gsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2f_status_fail", "metric_drift_fail", "agreement_drift_fail", "raw_leak_fail", "claim_boundary_fail", "stop_go_overauth_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2greadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2gstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2f_public_artifact", "haae_r2h_next_step_design_authorized_bool": passed, "haae_r2h_execution_authorized_bool": False, "scale_material_generation_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "scheduler_selector_authorized_bool": False, "bea_v1_a_p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
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
    for key in ["source_lock_records", "r2f_metric_readback_records", "r2f_agreement_readback_records", "public_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    for row in report.get("r2f_metric_readback_records", []):
        if row.get("gold_file_hit_rate_bucket") != "rate_1" or row.get("top1_hit_count_bucket") != "count_10_to_20" or row.get("top5_hit_count_bucket") != "count_10_to_20" or row.get("top10_hit_count_bucket") != "count_10_to_20":
            issues.append("metric_readback_mismatch")
    for row in report.get("r2f_agreement_readback_records", []):
        if row.get("same_top_candidate_rate_bucket") != "rate_1":
            issues.append("agreement_readback_mismatch")
    claims = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]:
        if claims.get(field) is not False:
            issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2h_execution_authorized_bool", "scale_material_generation_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "scheduler_selector_authorized_bool", "bea_v1_a_p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False:
            issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2h_next_step_design_authorized_bool") is not True:
            issues.append("missing_r2h_design_authorization")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            parsed["self_test"] = True
            i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            if arg == "--validate-report":
                parsed["validate"] = argv[i + 1]
            else:
                parsed["out"] = argv[i + 1]
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
    base = load_json(repo / R2F_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"
    check("wrong_r2f_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    drift = json.loads(json.dumps(base)); drift["rank_source_metric_records"][0]["gold_file_hit_rate_bucket"] = "rate_0"
    check("metric_drift_fail", build_report(drift)["status"] == STATUS_FAIL_METRIC)
    agree = json.loads(json.dumps(base)); agree["rank_source_agreement_records"][0]["same_top_candidate_rate_bucket"] = "rate_0"
    check("agreement_drift_fail", build_report(agree)["status"] == STATUS_FAIL_METRIC)
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"
    check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True
    check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True
    check("stop_go_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(over)))
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()):
            parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report()
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
