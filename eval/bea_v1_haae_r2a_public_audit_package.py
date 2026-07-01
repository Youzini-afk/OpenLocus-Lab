#!/usr/bin/env python3
"""BEA-v1-HAAE-R2A public audit package.

Public-only audit of the R2 aggregate artifact. No private reads, no recompute,
no retrieval, no candidate generation, no scheduler/HAAE execution, no selector
or reranker, no runtime/default change, and no method-winner claim.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2a_small_local_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"

R2_CHECKPOINT = "0784be0"
R2_STATUS = "haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized"
R2_REPORT_PATH = Path("artifacts/bea_v1_haae_r2_small_local_lexical_material_experiment/bea_v1_haae_r2_small_local_lexical_material_experiment_report.json")

STATUS_PASS = "haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized"
STATUS_FAIL_SOURCE_LOCK = "haae_r2a_fail_closed_source_lock_mismatch"
STATUS_FAIL_METRIC_DRIFT = "haae_r2a_fail_closed_r2_metric_readback_drift"
STATUS_FAIL_OVERAUTH = "haae_r2a_fail_closed_stop_go_overauthorization"
STATUS_FAIL_RAW_LEAK = "haae_r2a_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2a_fail_closed_public_readback_mismatch"

SELF_TEST_EXPECTED = 10
RANK_SOURCES = ["bm25_like", "symbol_overlap", "rrf_like"]
AGREEMENT_PAIRS = {("bm25_like", "symbol_overlap"), ("bm25_like", "rrf_like"), ("symbol_overlap", "rrf_like")}
FORBIDDEN_R2_STOP_FIELDS = [
    "haae_r2_private_write_authorized_bool",
    "haae_r2_new_candidate_generation_authorized_bool",
    "haae_r2_rematerialization_authorized_bool",
    "haae_r2_broad_retrieval_authorized_bool",
    "haae_r2_scheduler_haae_layer_execution_authorized_bool",
    "haae_r2_selector_reranker_authorized_bool",
    "haae_r2_provider_model_network_authorized_bool",
    "haae_r2_runtime_default_change_authorized_bool",
    "haae_r2_bea_v1_a_authorized_bool",
    "haae_r2_p5_authorized_bool",
    "haae_r2_raw_publication_authorized_bool",
    "haae_r2_method_winner_claim_authorized_bool",
]
FORBIDDEN_R2A_STOP_FIELDS = [
    "haae_r2b_scale_execution_authorized_bool",
    "ci_execution_authorized_bool",
    "new_candidate_generation_authorized_bool",
    "candidate_generation_authorized_bool",
    "retrieval_authorized_bool",
    "scheduler_haae_execution_authorized_bool",
    "selector_reranker_authorized_bool",
    "runtime_default_change_authorized_bool",
    "bea_v1_a_authorized_bool",
    "p5_authorized_bool",
    "method_winner_claim_authorized_bool",
    "raw_publication_authorized_bool",
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "recompute_authorized_bool",
]
FORBIDDEN_CLAIM_FIELDS = [
    "method_winner_claim_bool",
    "runtime_default_change_bool",
    "bea_v1_a_bool",
    "p5_bool",
    "candidate_generation_bool",
    "retrieval_bool",
    "scheduler_haae_execution_bool",
    "selector_reranker_bool",
    "raw_publication_bool",
    "r2b_scale_execution_authorized_bool",
    "ci_execution_authorized_bool",
]
GATE_NAMES = [
    "haae_r2_source_locked_gate",
    "r2_status_match_gate",
    "r2_metric_readback_match_gate",
    "r2_stop_go_boundary_match_gate",
    "tiny_n_no_method_winner_claim_gate",
    "public_only_no_private_read_gate",
    "no_recompute_gate",
    "no_candidate_generation_gate",
    "no_retrieval_gate",
    "no_scheduler_haae_execution_gate",
    "no_selector_reranker_gate",
    "no_runtime_default_change_gate",
    "no_bea_v1_a_p5_gate",
    "r2b_design_only_handoff_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or ARTIFACT_DIR / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def is_exact_public_artifact_arg(value: str, expected: Path) -> bool:
    supplied = Path(value)
    if supplied.is_absolute() or ".." in supplied.parts:
        return False
    return supplied == expected


def audit_r2_report(r2: dict[str, Any]) -> dict[str, Any]:
    stop = (r2.get("stop_go_records") or [{}])[0]
    source = (r2.get("source_lock_records") or [{}])[0]
    summary = (r2.get("experiment_summary_records") or [{}])[0]
    metrics = {row.get("rank_source_bucket"): row for row in r2.get("rank_source_metric_records", [])}
    agreements = {(row.get("left_rank_source_bucket"), row.get("right_rank_source_bucket")): row for row in r2.get("rank_source_agreement_records", [])}
    status_ok = r2.get("status") == R2_STATUS
    source_ok = source.get("source_locked_bool") is True
    scan_ok = r2.get("forbidden_scan", {}).get("status") == "pass"
    r2a_auth_ok = stop.get("haae_r2a_public_audit_package_authorized_bool") is True
    no_r3_ok = stop.get("haae_r3_scale_preflight_authorized_bool") is False
    forbidden_ok = all(stop.get(field) is False for field in FORBIDDEN_R2_STOP_FIELDS)
    metric_ok = set(metrics) == set(RANK_SOURCES) and all(
        metrics[src].get("gold_file_hit_rate_bucket") == "rate_1"
        and metrics[src].get("task_count_bucket") == "count_2_to_5"
        and metrics[src].get("existing_trace_present_bool") is True
        for src in RANK_SOURCES
    )
    agreement_ok = set(agreements) == AGREEMENT_PAIRS and all(
        row.get("same_top_candidate_rate_bucket") == "rate_1" and row.get("comparable_task_count_bucket") == "count_2_to_5"
        for row in agreements.values()
    )
    tiny_n_ok = summary.get("task_count_bucket") == "count_2_to_5" and summary.get("method_winner_claim_bool") is False
    return {
        "status_ok": status_ok,
        "source_ok": source_ok,
        "scan_ok": scan_ok,
        "r2a_auth_ok": r2a_auth_ok,
        "no_r3_ok": no_r3_ok,
        "forbidden_ok": forbidden_ok,
        "metric_ok": metric_ok,
        "agreement_ok": agreement_ok,
        "tiny_n_ok": tiny_n_ok,
        "metrics": metrics,
        "summary": summary,
    }


PUBLIC_LEAK_PATTERNS = [
    ("path", re.compile(r"/workspace/|/tmp/|/var/tmp/|private[-_/ ]?root|crates/openlocus-|\.rs\b", re.I)),
    ("raw_task", re.compile(r"r14s-\d+|\"task_id\"|\"query\"")),
    ("raw_label", re.compile(r"gold_spans|hard_negatives|snippet|start_line|end_line|candidate_path")),
    ("score_hash", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in PUBLIC_LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(self_test_total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{self_test_total}/{self_test_total}", R2_CHECKPOINT, R2_STATUS, "tiny-N", "no method-winner", "BEA-v1-HAAE-R2B Scale Preflight Design"]
    spaced = [f"{self_test_total} / {self_test_total}" if f == f"{self_test_total}/{self_test_total}" else f for f in fragments]

    def text(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(s: str) -> bool:
        return all(f in s for f in fragments) or all(f in s for f in spaced)

    readme = has_all(text("README.md"))
    detail = has_all(text("docs/en/bea-v1-haae-r2a-small-local-experiment-public-audit-package.md")) and has_all(text("docs/zh/bea-v1-haae-r2a-small-local-experiment-public-audit-package.md"))
    current_root = text("docs/current-research-conclusions.md")
    current = has_all(text("docs/en/current-research-conclusions.md")) and has_all(text("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2a-small-local-experiment-public-audit-package.md" in current_root
    log = has_all(text("docs/en/research-log.md")) and has_all(text("docs/zh/research-log.md"))
    summary = has_all(text("docs/en/research-summary.md")) and has_all(text("docs/zh/research-summary.md"))
    return {
        "readme_readback_match_bool": readme,
        "detail_docs_readback_match_bool": detail,
        "current_conclusions_readback_match_bool": current,
        "research_log_readback_match_bool": log,
        "research_summary_readback_match_bool": summary,
        "all_public_readback_match_bool": readme and detail and current and log and summary,
    }


def build_report(r2: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2 is None:
        try:
            r2 = load_json(Path(__file__).resolve().parents[1] / R2_REPORT_PATH)
        except Exception:
            r2 = {}
    audit = audit_r2_report(r2)
    readback = public_readback_match(self_test_total)
    source_ok = audit["status_ok"] and audit["source_ok"] and audit["scan_ok"] and audit["r2a_auth_ok"]
    metric_ok = audit["metric_ok"] and audit["agreement_ok"] and audit["tiny_n_ok"]
    boundary_ok = audit["no_r3_ok"] and audit["forbidden_ok"]
    if not source_ok:
        status = STATUS_FAIL_SOURCE_LOCK
    elif not metric_ok:
        status = STATUS_FAIL_METRIC_DRIFT
    elif not boundary_ok:
        status = STATUS_FAIL_OVERAUTH
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "haae_r2_source_locked_gate": source_ok,
        "r2_status_match_gate": audit["status_ok"],
        "r2_metric_readback_match_gate": metric_ok,
        "r2_stop_go_boundary_match_gate": boundary_ok,
        "tiny_n_no_method_winner_claim_gate": audit["tiny_n_ok"],
        "public_only_no_private_read_gate": True,
        "no_recompute_gate": True,
        "no_candidate_generation_gate": True,
        "no_retrieval_gate": True,
        "no_scheduler_haae_execution_gate": True,
        "no_selector_reranker_gate": True,
        "no_runtime_default_change_gate": True,
        "no_bea_v1_a_p5_gate": True,
        "r2b_design_only_handoff_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2asource0000", "locked_haae_r2_checkpoint": R2_CHECKPOINT, "locked_haae_r2_status": R2_STATUS, "r2_artifact_status_match_bool": audit["status_ok"], "r2_artifact_forbidden_scan_pass_bool": audit["scan_ok"], "r2_source_lock_pass_bool": audit["source_ok"], "r2a_authorization_match_bool": audit["r2a_auth_ok"], "source_locked_bool": source_ok}],
        "r2_metric_readback_records": [{"anonymous_r2_metric_readback_id": f"haaer2ametric{idx:04d}", "rank_source_bucket": src, "gold_file_hit_rate_bucket": audit["metrics"].get(src, {}).get("gold_file_hit_rate_bucket", "missing"), "task_count_bucket": audit["metrics"].get(src, {}).get("task_count_bucket", "missing"), "existing_trace_present_bool": audit["metrics"].get(src, {}).get("existing_trace_present_bool") is True, "metric_readback_match_bool": src in audit["metrics"] and audit["metrics"][src].get("gold_file_hit_rate_bucket") == "rate_1", "raw_metric_values_published_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "r2_boundary_audit_records": [{"anonymous_r2_boundary_audit_id": "haaer2aboundary0000", "public_only_audit_bool": True, "private_read_count_bucket": "count_0", "private_write_count_bucket": "count_0", "r2_private_read_bucket_observed": "count_1_to_10", "r2_private_write_bucket_observed": "count_0", "no_recompute_bool": True, "no_candidate_generation_bool": True, "no_retrieval_bool": True, "no_scheduler_haae_execution_bool": True, "no_selector_reranker_bool": True, "no_runtime_default_change_bool": True, "no_bea_v1_a_p5_bool": True}],
        "public_audit_records": [{"anonymous_public_audit_id": "haaer2aaudit0000", "aggregate_metrics_confirmed_bool": metric_ok, "rank_sources_all_rate_1_bool": audit["metric_ok"], "same_top_agreement_rate_1_bool": audit["agreement_ok"], "sample_bucket": audit["summary"].get("task_count_bucket", "missing"), "tiny_n_caveat_bool": True, "no_method_winner_claim_bool": audit["tiny_n_ok"], "aggregate_only_publication_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2aclaim0000", "public_audit_package_bool": True, "method_winner_claim_bool": False, "runtime_default_change_bool": False, "bea_v1_a_bool": False, "p5_bool": False, "candidate_generation_bool": False, "retrieval_bool": False, "scheduler_haae_execution_bool": False, "selector_reranker_bool": False, "raw_publication_bool": False, "r2b_scale_preflight_design_authorized_bool": passed, "r2b_scale_execution_authorized_bool": False, "ci_execution_authorized_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2agate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(gates.get(name, False)), "gate_evaluated_on_public_artifact_bool": True, "gate_reads_private_material_bool": False} for idx, name in enumerate(GATE_NAMES)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2areadback0000", **readback}],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2asynth{idx:04d}", "validator_bucket": bucket, "expected_status_bucket": expected} for idx, (bucket, expected) in enumerate([("source_lock_pass_fixture", STATUS_PASS), ("stale_r2_status_fail_fixture", STATUS_FAIL_SOURCE_LOCK), ("metric_drift_fail_fixture", STATUS_FAIL_METRIC_DRIFT), ("stop_go_overauth_fail_fixture", STATUS_FAIL_OVERAUTH), ("raw_leak_scanner_fail_fixture", STATUS_FAIL_RAW_LEAK), ("docs_readback_stale_fail_fixture", STATUS_FAIL_READBACK)])],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2astop0000", "next_allowed_phase": "BEA-v1-HAAE-R2B Scale Preflight Design" if passed else "stop_or_reaudit_r2_public_artifact", "haae_r2b_scale_preflight_design_authorized_bool": passed, "haae_r2b_scale_execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_candidate_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "scheduler_haae_execution_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_change_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "method_winner_claim_authorized_bool": False, "raw_publication_authorized_bool": False, "private_read_authorized_bool": False, "private_write_authorized_bool": False, "recompute_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_RAW_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "r2_metric_readback_records", "r2_boundary_audit_records", "public_audit_records", "claim_boundary_records", "pass_fail_gate_records", "public_readback_records", "synthetic_validator_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2_checkpoint") != R2_CHECKPOINT or src.get("locked_haae_r2_status") != R2_STATUS:
        issues.append("source_lock_mismatch")
    if {row.get("rank_source_bucket") for row in report.get("r2_metric_readback_records", [])} != set(RANK_SOURCES):
        issues.append("rank_source_incomplete")
    for row in report.get("r2_metric_readback_records", []):
        if row.get("gold_file_hit_rate_bucket") != "rate_1" or row.get("metric_readback_match_bool") is not True:
            issues.append("metric_drift")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_R2A_STOP_FIELDS:
        if stop.get(field) is not False:
            issues.append(f"stop_go_overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        for key in [
            "source_locked_bool",
            "r2_artifact_status_match_bool",
            "r2_artifact_forbidden_scan_pass_bool",
            "r2_source_lock_pass_bool",
            "r2a_authorization_match_bool",
        ]:
            if src.get(key) is not True:
                issues.append(f"source_lock_field_not_true_{key}")
        claim = (report.get("claim_boundary_records") or [{}])[0]
        if claim.get("public_audit_package_bool") is not True:
            issues.append("claim_boundary_public_audit_not_true")
        if claim.get("r2b_scale_preflight_design_authorized_bool") is not True:
            issues.append("claim_boundary_missing_r2b_design_authorization")
        for field in FORBIDDEN_CLAIM_FIELDS:
            if claim.get(field) is not False:
                issues.append(f"claim_boundary_overauthorization_{field}")
        if stop.get("haae_r2b_scale_preflight_design_authorized_bool") is not True:
            issues.append("missing_r2b_design_authorization")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True:
                issues.append(f"gate_not_passed_{gate}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    base = load_json(Path(__file__).resolve().parents[1] / R2_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS)
    stale = json.loads(json.dumps(base)); stale["status"] = "stale"
    check("stale_r2_status_fail", build_report(stale)["status"] == STATUS_FAIL_SOURCE_LOCK)
    drift = json.loads(json.dumps(base)); drift["rank_source_metric_records"][0]["gold_file_hit_rate_bucket"] = "rate_0"
    check("metric_drift_fail", build_report(drift)["status"] == STATUS_FAIL_METRIC_DRIFT)
    over = json.loads(json.dumps(base)); over["stop_go_records"][0]["haae_r3_scale_preflight_authorized_bool"] = True
    check("stop_go_overauth_fail", build_report(over)["status"] == STATUS_FAIL_OVERAUTH)
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14s-001 query crates/openlocus-core/src/lib.rs"
    check("raw_leak_scanner_fail", scan_public_report(leak)["status"] == "fail")
    stale_doc = json.loads(json.dumps(passed)); stale_doc["self_test_total"] = 999
    check("docs_readback_stale_fail", "public_readback_stale" in validate_report(stale_doc))
    try:
        parse_args(["--unknown-private-path", "/tmp/secret"])
        parser_rejected = False
    except ValueError as exc:
        parser_rejected = str(exc) == "invalid arguments"
    check("safe_parser_rejects_unknown", parser_rejected)
    check("private_r2_report_arg_rejected", not is_exact_public_artifact_arg("/tmp/private.json", R2_REPORT_PATH))
    source_mutation = json.loads(json.dumps(passed)); source_mutation["source_lock_records"][0]["source_locked_bool"] = False
    check("source_lock_false_validate_fail", any(issue.startswith("source_lock_field_not_true") for issue in validate_report(source_mutation)))
    claim_mutation = json.loads(json.dumps(passed)); claim_mutation["claim_boundary_records"][0]["r2b_scale_execution_authorized_bool"] = True
    check("claim_boundary_overauth_validate_fail", any(issue.startswith("claim_boundary_overauthorization") for issue in validate_report(claim_mutation)))
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PHASE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report")
    parser.add_argument("--r2-report", default=str(R2_REPORT_PATH))
    parser.add_argument("--out")
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        raise ValueError("invalid arguments")
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.validate_report:
        report = load_json(Path(args.validate_report))
        issues = validate_report(report)
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    repo = Path(__file__).resolve().parents[1]
    if not is_exact_public_artifact_arg(args.r2_report, R2_REPORT_PATH):
        print("invalid arguments", file=sys.stderr)
        return 2
    r2_path = Path(args.r2_report)
    if not r2_path.is_absolute():
        r2_path = repo / r2_path
    report = build_report(load_json(r2_path))
    path = write_report(report, Path(args.out) if args.out else None)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
