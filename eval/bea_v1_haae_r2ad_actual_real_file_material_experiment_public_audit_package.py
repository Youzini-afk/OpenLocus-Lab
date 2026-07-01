#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AD actual real-file material experiment public audit package.

Public-only audit/package of the R2AC public aggregate artifact. This script
does not read private roots/material, recompute from private rows, generate
material/candidates, scan source, run retrieval/OpenLocus/runtime, or use
CI/network/provider/clone.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2ad_actual_real_file_material_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AC_CHECKPOINT = "6f189e4"
R2AC_STATUS = "haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_signal_present"
R2AB_CHECKPOINT = "52a23da"
R2AA_CHECKPOINT = "f325b65"
R2AC_SELF_TEST_TOTAL = 21
R2AC_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ac_actual_real_file_material_experiment/bea_v1_haae_r2ac_actual_real_file_material_experiment_report.json")

STATUS_PASS = "haae_r2ad_actual_real_file_material_experiment_public_audit_package_complete_r2ae_signal_robustness_scale_decision_authorized"
STATUS_FAIL_SOURCE = "haae_r2ad_fail_closed_source_lock_mismatch"
STATUS_FAIL_RESULT = "haae_r2ad_fail_closed_result_audit_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ad_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ad_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2ad_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 15
NEXT_PHASE = "BEA-v1-HAAE-R2AE Real-File Signal Robustness/Scale Decision"

RANK_SOURCES = ["query_identifier_overlap", "symbol_name_overlap", "lexical_bm25_like", "content_identifier_fusion", "control_baseline"]
HIGH_SOURCES = {"symbol_name_overlap", "content_identifier_fusion"}
MEDIUM_SOURCES = {"query_identifier_overlap", "lexical_bm25_like"}

FORBIDDEN_STOP_TRUE = [
    "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool",
    "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool",
    "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool",
    "broad_scan_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool",
    "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool",
    "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
]
GATE_NAMES = [
    "r2ac_source_locked_gate", "r2ac_status_signal_present_gate", "r2ac_self_test_21_gate",
    "r2ab_r2aa_source_lock_gate", "r2ac_forbidden_scan_gate", "aggregate_bucket_metrics_gate",
    "symbol_content_high_bucket_gate", "query_lexical_medium_bucket_gate", "control_low_bucket_gate",
    "signal_present_gate", "public_only_audit_gate", "no_private_read_gate", "no_recompute_gate",
    "no_generation_source_scan_runtime_gate", "no_ci_network_provider_clone_gate",
    "no_method_default_scaling_claim_gate", "r2ae_decision_only_stop_go_gate", "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_by_source(r2ac: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row.get("rank_source_bucket"): row for row in r2ac.get("rank_source_metric_records", [])}


def audit_r2ac(r2ac: dict[str, Any]) -> dict[str, bool]:
    src = (r2ac.get("source_lock_records") or [{}])[0]
    stop = (r2ac.get("stop_go_records") or [{}])[0]
    claim = (r2ac.get("claim_boundary_records") or [{}])[0]
    signal = (r2ac.get("signal_summary_records") or [{}])[0]
    metrics = metric_by_source(r2ac)
    agreements = r2ac.get("rank_source_agreement_records", [])
    gates = r2ac.get("pass_fail_gate_records", [])

    status_ok = r2ac.get("status") == R2AC_STATUS
    scan_ok = r2ac.get("forbidden_scan", {}).get("status") == "pass"
    self_test_ok = r2ac.get("self_test_total") == R2AC_SELF_TEST_TOTAL
    source_ok = (
        src.get("locked_haae_r2ab_checkpoint") == R2AB_CHECKPOINT
        and src.get("locked_r2aa_checkpoint") == R2AA_CHECKPOINT
        and src.get("source_locked_bool") is True
    )
    stop_ok = stop.get("haae_r2ad_public_audit_package_authorized_bool") is True and all(
        stop.get(field, False) is False for field in FORBIDDEN_STOP_TRUE
    )
    claim_ok = all(claim.get(field) is False for field in [
        "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool",
        "candidate_generation_bool", "private_write_bool", "retrieval_openlocus_runtime_bool", "source_scan_bool",
        "ci_network_provider_clone_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool",
    ])
    metric_set_ok = set(metrics) == set(RANK_SOURCES) and all(
        row.get("exact_values_published_bool") is False and row.get("rank_source_present_bool") is True
        for row in metrics.values()
    )
    high_ok = all(
        metrics.get(src_name, {}).get("mrr_bucket") == "mrr_high"
        and metrics.get(src_name, {}).get("top1_hit_count_bucket") == "count_11_to_20"
        and metrics.get(src_name, {}).get("top20_hit_count_bucket") == "count_11_to_20"
        for src_name in HIGH_SOURCES
    )
    medium_ok = all(metrics.get(src_name, {}).get("mrr_bucket") == "mrr_medium" for src_name in MEDIUM_SOURCES)
    control_ok = (
        metrics.get("control_baseline", {}).get("mrr_bucket") == "mrr_low"
        and metrics.get("control_baseline", {}).get("top1_hit_count_bucket") == "count_0"
    )
    agreement_ok = len(agreements) == 10 and all(row.get("exact_candidate_values_published_bool") is False for row in agreements)
    signal_ok = (
        signal.get("real_file_material_signal_bucket") == "signal_present"
        and signal.get("rank_source_spread_bucket") in {"spread_medium", "spread_high"}
        and signal.get("method_winner_bool") is False
        and signal.get("aggregate_only_bool") is True
    )
    gates_ok = bool(gates) and all(row.get("gate_passed_bool") is True for row in gates)
    source_locked = status_ok and scan_ok and self_test_ok and source_ok and stop_ok and claim_ok
    result_ok = metric_set_ok and high_ok and medium_ok and control_ok and agreement_ok and signal_ok and gates_ok
    return {
        "status_ok": status_ok, "scan_ok": scan_ok, "self_test_ok": self_test_ok, "source_ok": source_ok,
        "stop_ok": stop_ok, "claim_ok": claim_ok, "metric_set_ok": metric_set_ok, "high_ok": high_ok,
        "medium_ok": medium_ok, "control_ok": control_ok, "agreement_ok": agreement_ok, "signal_ok": signal_ok,
        "gates_ok": gates_ok, "source_locked": source_locked, "result_ok": result_ok,
    }


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_path", re.compile(r"candidate_path|source_path|filepath|filename|directory|snippet|start_line|end_line|\.rs\b|crates/openlocus-")),
    ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|candidate_key|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE, STATUS_PASS, f"{total}/{total}", R2AC_CHECKPOINT, R2AC_STATUS, "R2AC self-test 21/21",
        R2AB_CHECKPOINT, R2AA_CHECKPOINT, "signal_present", "aggregate-only bucket metrics", "no raw leak",
        "symbol_name_overlap/content_identifier_fusion high bucket", "query/lexical medium", "control low",
        "method/default/scaling false", NEXT_PHASE, "public decision/preflight only",
        "not direct CI/scale/execution",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ad-actual-real-file-material-experiment-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ad-actual-real-file-material-experiment-public-audit-package.md"))
    root_current = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(root_current) and "bea-v1-haae-r2ad-actual-real-file-material-experiment-public-audit-package.md" in root_current
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ac: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ac is None:
        try:
            r2ac = load_json(repo / R2AC_REPORT_PATH)
        except Exception:
            r2ac = {}
    audit = audit_r2ac(r2ac)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["result_ok"]:
        status = STATUS_FAIL_RESULT
    elif not audit["claim_ok"] or not audit["stop_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2ac_source_locked_gate": audit["source_locked"], "r2ac_status_signal_present_gate": audit["status_ok"],
        "r2ac_self_test_21_gate": audit["self_test_ok"], "r2ab_r2aa_source_lock_gate": audit["source_ok"],
        "r2ac_forbidden_scan_gate": audit["scan_ok"], "aggregate_bucket_metrics_gate": audit["metric_set_ok"] and audit["agreement_ok"],
        "symbol_content_high_bucket_gate": audit["high_ok"], "query_lexical_medium_bucket_gate": audit["medium_ok"],
        "control_low_bucket_gate": audit["control_ok"], "signal_present_gate": audit["signal_ok"],
        "public_only_audit_gate": True, "no_private_read_gate": True, "no_recompute_gate": True,
        "no_generation_source_scan_runtime_gate": True, "no_ci_network_provider_clone_gate": True,
        "no_method_default_scaling_claim_gate": audit["claim_ok"], "r2ae_decision_only_stop_go_gate": True,
        "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{
            "anonymous_source_lock_id": "haaer2adsource0000",
            "locked_haae_r2ac_checkpoint": R2AC_CHECKPOINT,
            "locked_haae_r2ac_status": R2AC_STATUS,
            "locked_haae_r2ab_checkpoint": R2AB_CHECKPOINT,
            "locked_haae_r2aa_checkpoint": R2AA_CHECKPOINT,
            "r2ac_status_match_bool": audit["status_ok"],
            "r2ac_forbidden_scan_pass_bool": audit["scan_ok"],
            "r2ac_self_test_21_bool": audit["self_test_ok"],
            "r2ac_stop_go_r2ad_authorized_bool": audit["stop_ok"],
            "source_locked_bool": audit["source_locked"],
        }],
        "metric_signal_audit_records": [{
            "anonymous_metric_signal_audit_id": "haaer2admetric0000",
            "signal_bucket": "signal_present",
            "rank_spread_bucket": "spread_medium",
            "aggregate_bucket_metrics_bool": audit["metric_set_ok"],
            "symbol_name_overlap_bucket": "high",
            "content_identifier_fusion_bucket": "high",
            "query_identifier_overlap_bucket": "medium",
            "lexical_bm25_like_bucket": "medium",
            "control_baseline_bucket": "low",
            "exact_metrics_published_bool": False,
            "result_readback_match_bool": audit["result_ok"],
        }],
        "public_audit_boundary_records": [{
            "anonymous_public_audit_boundary_id": "haaer2adboundary0000",
            "public_only_audit_bool": True,
            "private_root_read_bool": False,
            "private_material_read_bool": False,
            "recompute_metrics_from_private_material_bool": False,
            "candidate_generation_bool": False,
            "material_generation_bool": False,
            "source_scan_bool": False,
            "retrieval_openlocus_runtime_bool": False,
            "ci_network_provider_clone_bool": False,
            "raw_publication_bool": False,
            "aggregate_only_bool": True,
        }],
        "claim_boundary_records": [{
            "anonymous_claim_boundary_id": "haaer2adclaim0000",
            "method_winner_claim_bool": False,
            "default_runtime_claim_bool": False,
            "scaling_claim_bool": False,
            "execution_authorized_bool": False,
            "ci_authorized_bool": False,
            "scale_authorized_bool": False,
            "new_material_generation_authorized_bool": False,
            "raw_publication_bool": False,
        }],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2adgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2adsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate([
            "source_lock_pass", "wrong_r2ac_status_fail", "self_test_drift_fail", "source_checkpoint_drift_fail",
            "symbol_content_high_drift_fail", "query_lexical_medium_drift_fail", "control_low_drift_fail",
            "signal_drift_fail", "exact_metric_publication_fail", "claim_boundary_fail", "stop_go_overauth_fail",
            "leak_fail", "stale_readback_fail", "status_drift_fail", "next_phase_drift_fail",
        ])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2adreadback0000", **readback}],
        "stop_go_records": [{
            "anonymous_stop_go_id": "haaer2adstop0000",
            "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2ac_public_artifact",
            "haae_r2ae_signal_robustness_scale_decision_authorized_bool": passed,
            "r2ae_public_decision_preflight_only_bool": passed,
            "execution_authorized_bool": False,
            "ci_execution_authorized_bool": False,
            "scale_execution_authorized_bool": False,
            "new_material_generation_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "retrieval_authorized_bool": False,
            "runtime_execution_authorized_bool": False,
            "openlocus_runtime_authorized_bool": False,
            "source_scan_authorized_bool": False,
            "network_authorized_bool": False,
            "provider_model_authorized_bool": False,
            "clone_authorized_bool": False,
            "broad_scan_authorized_bool": False,
            "scheduler_haae_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "bea_v1_a_authorized_bool": False,
            "p5_authorized_bool": False,
            "default_change_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
            "scaling_claim_authorized_bool": False,
            "raw_publication_authorized_bool": False,
        }],
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
    required = ["source_lock_records", "metric_signal_audit_records", "public_audit_boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report:
            issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS:
        issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2ac_checkpoint") != R2AC_CHECKPOINT or source.get("locked_haae_r2ac_status") != R2AC_STATUS or source.get("locked_haae_r2ab_checkpoint") != R2AB_CHECKPOINT or source.get("locked_haae_r2aa_checkpoint") != R2AA_CHECKPOINT:
        issues.append("source_lock_mismatch")
    for field in ["r2ac_status_match_bool", "r2ac_forbidden_scan_pass_bool", "r2ac_self_test_21_bool", "r2ac_stop_go_r2ad_authorized_bool", "source_locked_bool"]:
        if source.get(field) is not True:
            issues.append(f"source_lock_{field}")
    result = (report.get("metric_signal_audit_records") or [{}])[0]
    if result.get("signal_bucket") != "signal_present" or result.get("result_readback_match_bool") is not True:
        issues.append("signal_readback_mismatch")
    if result.get("aggregate_bucket_metrics_bool") is not True:
        issues.append("aggregate_bucket_metrics_missing")
    if result.get("symbol_name_overlap_bucket") != "high" or result.get("content_identifier_fusion_bucket") != "high":
        issues.append("high_bucket_readback_mismatch")
    if result.get("query_identifier_overlap_bucket") != "medium" or result.get("lexical_bm25_like_bucket") != "medium":
        issues.append("medium_bucket_readback_mismatch")
    if result.get("control_baseline_bucket") != "low":
        issues.append("control_low_readback_mismatch")
    if result.get("exact_metrics_published_bool") is not False:
        issues.append("exact_metrics_public")
    boundary = (report.get("public_audit_boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("aggregate_only_bool") is not True:
        issues.append("boundary_public_aggregate_mismatch")
    for field in ["private_root_read_bool", "private_material_read_bool", "recompute_metrics_from_private_material_bool", "candidate_generation_bool", "material_generation_bool", "source_scan_bool", "retrieval_openlocus_runtime_bool", "ci_network_provider_clone_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False:
            issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "execution_authorized_bool", "ci_authorized_bool", "scale_authorized_bool", "new_material_generation_authorized_bool", "raw_publication_bool"]:
        if claim.get(field) is not False:
            issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2ae_signal_robustness_scale_decision_authorized_bool") is not True or stop.get("r2ae_public_decision_preflight_only_bool") is not True:
            issues.append("r2ae_stop_go_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True:
                issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["execution_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool", *FORBIDDEN_STOP_TRUE]:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
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
    base = load_json(repo / R2AC_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ac_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 20; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    src = json.loads(json.dumps(base)); src["source_lock_records"][0]["locked_haae_r2ab_checkpoint"] = "wrong"; check("source_checkpoint_drift_fail", build_report(src)["status"] == STATUS_FAIL_SOURCE)
    high = json.loads(json.dumps(base)); high["rank_source_metric_records"][1]["mrr_bucket"] = "mrr_low"; check("symbol_content_high_drift_fail", build_report(high)["status"] == STATUS_FAIL_RESULT)
    med = json.loads(json.dumps(base)); med["rank_source_metric_records"][0]["mrr_bucket"] = "mrr_low"; check("query_lexical_medium_drift_fail", build_report(med)["status"] == STATUS_FAIL_RESULT)
    ctl = json.loads(json.dumps(base)); ctl["rank_source_metric_records"][4]["top1_hit_count_bucket"] = "count_11_to_20"; check("control_low_drift_fail", build_report(ctl)["status"] == STATUS_FAIL_RESULT)
    sig = json.loads(json.dumps(base)); sig["signal_summary_records"][0]["real_file_material_signal_bucket"] = "no_signal"; check("signal_drift_fail", build_report(sig)["status"] == STATUS_FAIL_RESULT)
    exact = json.loads(json.dumps(passed)); exact["metric_signal_audit_records"][0]["exact_metrics_published_bool"] = True; check("exact_metric_publication_fail", "exact_metrics_public" in validate_report(exact))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_") for i in validate_report(claim)))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    status_bad = json.loads(json.dumps(passed)); status_bad["status"] = "wrong"; check("status_drift_fail", "status_mismatch" in validate_report(status_bad))
    next_bad = json.loads(json.dumps(passed)); next_bad["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_phase_drift_fail", "r2ae_stop_go_mismatch" in validate_report(next_bad))
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
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
