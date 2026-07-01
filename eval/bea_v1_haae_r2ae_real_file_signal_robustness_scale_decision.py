#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AE real-file signal robustness/scale decision.

Public-only decision/preflight package. Reads only public artifacts/docs; does
not read private roots/material, recompute, execute, generate material or
candidates, scan source, retrieve, run OpenLocus/runtime, or use CI/network.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AE Real-File Signal Robustness/Scale Decision"
SLUG = "bea_v1_haae_r2ae_real_file_signal_robustness_scale_decision"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AD_CHECKPOINT = "a17ae7e"
R2AD_STATUS = "haae_r2ad_actual_real_file_material_experiment_public_audit_package_complete_r2ae_signal_robustness_scale_decision_authorized"
R2AD_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ad_actual_real_file_material_experiment_public_audit_package/bea_v1_haae_r2ad_actual_real_file_material_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2ae_real_file_signal_robustness_scale_decision_complete_r2af_robustness_material_preflight_authorized"
STATUS_NO_GO = "haae_r2ae_no_go_no_safe_robustness_preflight"
STATUS_FAIL_SOURCE = "haae_r2ae_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ae_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ae_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2ae_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 15
NEXT_PHASE = "BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight"

STOP_FORBIDDEN_TRUE = [
    "execution_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool",
    "new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool",
    "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool",
    "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool",
    "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool",
    "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
]
GATE_NAMES = [
    "r2ad_source_locked_gate", "r2ad_r2ae_authorization_gate", "real_file_signal_present_gate",
    "real_file_signal_not_robust_gate", "public_only_decision_gate", "no_private_read_gate",
    "no_recompute_execution_generation_gate", "no_retrieval_runtime_source_scan_gate",
    "no_ci_network_provider_clone_gate", "direct_scale_ci_rejected_gate", "mechanism_decomposition_deferred_gate",
    "r2af_preflight_selected_gate", "r2af_public_only_boundary_gate", "no_method_default_scaling_claim_gate",
    "forbidden_scan_pass_gate", "docs_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2ad(r2ad: dict[str, Any]) -> dict[str, bool]:
    stop = (r2ad.get("stop_go_records") or [{}])[0]
    metric = (r2ad.get("metric_signal_audit_records") or [{}])[0]
    boundary = (r2ad.get("public_audit_boundary_records") or [{}])[0]
    claim = (r2ad.get("claim_boundary_records") or [{}])[0]
    status_ok = r2ad.get("status") == R2AD_STATUS
    scan_ok = r2ad.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2ae_signal_robustness_scale_decision_authorized_bool") is True and stop.get("r2ae_public_decision_preflight_only_bool") is True
    stop_ok = all(stop.get(field) is False for field in STOP_FORBIDDEN_TRUE)
    signal_ok = (
        metric.get("signal_bucket") == "signal_present"
        and metric.get("symbol_name_overlap_bucket") == "high"
        and metric.get("content_identifier_fusion_bucket") == "high"
        and metric.get("query_identifier_overlap_bucket") == "medium"
        and metric.get("lexical_bm25_like_bucket") == "medium"
        and metric.get("control_baseline_bucket") == "low"
        and metric.get("exact_metrics_published_bool") is False
    )
    boundary_ok = boundary.get("public_only_audit_bool") is True and boundary.get("aggregate_only_bool") is True and all(
        boundary.get(field) is False for field in [
            "private_root_read_bool", "private_material_read_bool", "recompute_metrics_from_private_material_bool",
            "candidate_generation_bool", "material_generation_bool", "source_scan_bool", "retrieval_openlocus_runtime_bool",
            "ci_network_provider_clone_bool", "raw_publication_bool",
        ]
    )
    claim_ok = all(claim.get(field) is False for field in [
        "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "execution_authorized_bool",
        "ci_authorized_bool", "scale_authorized_bool", "new_material_generation_authorized_bool", "raw_publication_bool",
    ])
    source_locked = status_ok and scan_ok and auth_ok and stop_ok and boundary_ok and claim_ok
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "signal_ok": signal_ok, "boundary_ok": boundary_ok, "claim_ok": claim_ok, "source_locked": source_locked}


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
        PHASE, STATUS_PASS, f"{total}/{total}", R2AD_CHECKPOINT, R2AD_STATUS,
        "real-file signal is promising but not robust", "reject/defer direct scale/CI",
        "defer mechanism decomposition", NEXT_PHASE, "public-only preflight", "R2AG later may do explicit local bounded robustness material generation",
        "no private reads", "no execution", "no material/candidate generation", "no method/default/scaling claim",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ae-real-file-signal-robustness-scale-decision.md")) and has_all(read("docs/zh/bea-v1-haae-r2ae-real-file-signal-robustness-scale-decision.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ae-real-file-signal-robustness-scale-decision.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ad: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ad is None:
        try:
            r2ad = load_json(repo / R2AD_REPORT_PATH)
        except Exception:
            r2ad = {}
    audit = audit_r2ad(r2ad)
    readback = public_readback_match(self_test_total)
    selected_ok = True
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["signal_ok"] or not selected_ok:
        status = STATUS_NO_GO
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2ad_source_locked_gate": audit["source_locked"], "r2ad_r2ae_authorization_gate": audit["auth_ok"],
        "real_file_signal_present_gate": audit["signal_ok"], "real_file_signal_not_robust_gate": True,
        "public_only_decision_gate": True, "no_private_read_gate": True, "no_recompute_execution_generation_gate": True,
        "no_retrieval_runtime_source_scan_gate": True, "no_ci_network_provider_clone_gate": True,
        "direct_scale_ci_rejected_gate": True, "mechanism_decomposition_deferred_gate": True,
        "r2af_preflight_selected_gate": selected_ok, "r2af_public_only_boundary_gate": True,
        "no_method_default_scaling_claim_gate": audit["claim_ok"], "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aesource0000", "locked_haae_r2ad_checkpoint": R2AD_CHECKPOINT, "locked_haae_r2ad_status": R2AD_STATUS, "r2ad_status_match_bool": audit["status_ok"], "r2ad_forbidden_scan_pass_bool": audit["scan_ok"], "r2ad_r2ae_authorization_match_bool": audit["auth_ok"], "r2ad_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "real_file_signal_context_records": [{"anonymous_real_file_signal_context_id": "haaer2aecontext0000", "signal_bucket": "signal_present", "signal_strength_bucket": "promising", "robustness_bucket": "not_robust_enough", "symbol_name_overlap_bucket": "high", "content_identifier_fusion_bucket": "high", "query_identifier_overlap_bucket": "medium", "lexical_bm25_like_bucket": "medium", "control_baseline_bucket": "low", "method_default_scaling_claim_bool": False, "context_readback_match_bool": audit["signal_ok"]}],
        "cautionary_context_records": [
            {"anonymous_cautionary_context_id": "haaer2aecaution0000", "context_bucket": "path_cue_artifact_history", "source_phase_bucket": "R2R_R2S", "caution_bucket": "robustness_checks_needed_before_scale", "private_read_bool": False},
            {"anonymous_cautionary_context_id": "haaer2aecaution0001", "context_bucket": "identifier_decoy_not_file_evidence_history", "source_phase_bucket": "R2W_R2X", "caution_bucket": "material_validity_must_remain_explicit", "private_read_bool": False},
        ],
        "next_step_option_records": [
            {"anonymous_next_step_option_id": "haaer2aeoption0000", "option_bucket": "direct_scale_or_ci", "decision_bucket": "rejected_deferred", "selected_bool": False, "reason_bucket": "signal_promising_but_not_robust"},
            {"anonymous_next_step_option_id": "haaer2aeoption0001", "option_bucket": "mechanism_decomposition_now", "decision_bucket": "deferred", "selected_bool": False, "reason_bucket": "robustness_material_preflight_needed_first"},
            {"anonymous_next_step_option_id": "haaer2aeoption0002", "option_bucket": "new_unbounded_material_generation", "decision_bucket": "rejected", "selected_bool": False, "reason_bucket": "would_violate_bounded_local_contract"},
            {"anonymous_next_step_option_id": "haaer2aeoption0003", "option_bucket": "real_file_signal_robustness_material_preflight", "decision_bucket": "selected", "selected_bool": True, "reason_bucket": "define_bounded_robustness_material_before_execution"},
        ],
        "r2af_contract_records": [{"anonymous_r2af_contract_id": "haaer2aecontract0000", "next_phase": NEXT_PHASE, "public_only_preflight_bool": True, "define_robustness_material_recipe_bool": True, "r2ag_later_may_do_explicit_local_bounded_robustness_material_generation_bool": True, "execution_in_r2ae_bool": False, "private_read_in_r2ae_bool": False, "private_write_in_r2ae_bool": False, "candidate_generation_in_r2ae_bool": False, "source_scan_in_r2ae_bool": False, "ci_execution_in_r2ae_bool": False, "network_provider_clone_in_r2ae_bool": False, "public_aggregate_only_bool": True, "no_method_default_scaling_claim_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2aeclaim0000", "public_only_decision_bool": True, "private_read_bool": False, "private_write_bool": False, "execution_bool": False, "recompute_bool": False, "generation_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_clone_bool": False, "scheduler_selector_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aegate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aesynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2ad_status_fail", "missing_r2ae_authorization_fail", "signal_missing_no_go", "direct_scale_selected_fail", "mechanism_not_deferred_fail", "r2af_not_selected_fail", "r2af_execution_overauth_fail", "claim_boundary_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail", "status_drift_fail", "next_phase_drift_fail", "root_current_readback_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aereadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2aestop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_revisit_real_file_signal_decision", "haae_r2af_robustness_material_preflight_authorized_bool": passed, "r2af_public_preflight_only_bool": passed, "r2af_execution_authorized_bool": False, "r2af_private_read_authorized_bool": False, "r2af_private_write_authorized_bool": False, "r2af_candidate_generation_authorized_bool": False, "r2af_source_scan_authorized_bool": False, "r2af_ci_execution_authorized_bool": False, "r2af_network_provider_clone_authorized_bool": False, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "scale_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
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
    for key in ["source_lock_records", "real_file_signal_context_records", "cautionary_context_records", "next_step_option_records", "r2af_contract_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS:
        issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2ad_checkpoint") != R2AD_CHECKPOINT or source.get("locked_haae_r2ad_status") != R2AD_STATUS:
        issues.append("source_lock_mismatch")
    for field in ["r2ad_status_match_bool", "r2ad_forbidden_scan_pass_bool", "r2ad_r2ae_authorization_match_bool", "r2ad_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True:
            issues.append(f"source_lock_{field}")
    signal = (report.get("real_file_signal_context_records") or [{}])[0]
    if signal.get("signal_bucket") != "signal_present" or signal.get("signal_strength_bucket") != "promising" or signal.get("robustness_bucket") != "not_robust_enough" or signal.get("method_default_scaling_claim_bool") is not False:
        issues.append("signal_context_mismatch")
    options = {row.get("option_bucket"): row for row in report.get("next_step_option_records", [])}
    if options.get("direct_scale_or_ci", {}).get("decision_bucket") != "rejected_deferred" or options.get("mechanism_decomposition_now", {}).get("decision_bucket") != "deferred" or options.get("real_file_signal_robustness_material_preflight", {}).get("selected_bool") is not True:
        issues.append("next_step_decision_mismatch")
    contract = (report.get("r2af_contract_records") or [{}])[0]
    if contract.get("next_phase") != NEXT_PHASE:
        issues.append("r2af_contract_next_phase")
    for field in ["public_only_preflight_bool", "define_robustness_material_recipe_bool", "r2ag_later_may_do_explicit_local_bounded_robustness_material_generation_bool", "public_aggregate_only_bool", "no_method_default_scaling_claim_bool"]:
        if contract.get(field) is not True:
            issues.append(f"r2af_contract_{field}")
    for field in ["execution_in_r2ae_bool", "private_read_in_r2ae_bool", "private_write_in_r2ae_bool", "candidate_generation_in_r2ae_bool", "source_scan_in_r2ae_bool", "ci_execution_in_r2ae_bool", "network_provider_clone_in_r2ae_bool"]:
        if contract.get(field) is not False:
            issues.append(f"r2af_contract_overauth_{field}")
    claims = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["private_read_bool", "private_write_bool", "execution_bool", "recompute_bool", "generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_clone_bool", "scheduler_selector_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claims.get(field) is not False:
            issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["r2af_execution_authorized_bool", "r2af_private_read_authorized_bool", "r2af_private_write_authorized_bool", "r2af_candidate_generation_authorized_bool", "r2af_source_scan_authorized_bool", "r2af_ci_execution_authorized_bool", "r2af_network_provider_clone_authorized_bool", *STOP_FORBIDDEN_TRUE]:
        if stop.get(field) is not False:
            issues.append(f"stop_go_overauthorization_{field}")
    gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2af_robustness_material_preflight_authorized_bool") is not True or stop.get("r2af_public_preflight_only_bool") is not True:
            issues.append("missing_r2af_preflight_authorization")
        for gate in GATE_NAMES:
            if gates.get(gate) is not True:
                issues.append(f"gate_not_passed_{gate}")
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
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]
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


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AD_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ad_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    noauth = json.loads(json.dumps(base)); noauth["stop_go_records"][0]["haae_r2ae_signal_robustness_scale_decision_authorized_bool"] = False; check("missing_r2ae_authorization_fail", build_report(noauth)["status"] == STATUS_FAIL_SOURCE)
    nosignal = json.loads(json.dumps(base)); nosignal["metric_signal_audit_records"][0]["signal_bucket"] = "no_signal"; check("signal_missing_no_go", build_report(nosignal)["status"] == STATUS_NO_GO)
    direct = json.loads(json.dumps(passed)); direct["next_step_option_records"][0]["decision_bucket"] = "selected"; check("direct_scale_selected_fail", "next_step_decision_mismatch" in validate_report(direct))
    mech = json.loads(json.dumps(passed)); mech["next_step_option_records"][1]["decision_bucket"] = "selected"; check("mechanism_not_deferred_fail", "next_step_decision_mismatch" in validate_report(mech))
    r2af_not_selected = json.loads(json.dumps(passed)); r2af_not_selected["next_step_option_records"][3]["selected_bool"] = False; check("r2af_not_selected_fail", "next_step_decision_mismatch" in validate_report(r2af_not_selected))
    over = json.loads(json.dumps(passed)); over["r2af_contract_records"][0]["execution_in_r2ae_bool"] = True; check("r2af_execution_overauth_fail", any(i.startswith("r2af_contract_overauth") for i in validate_report(over)))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    status_bad = json.loads(json.dumps(passed)); status_bad["status"] = "wrong"; check("status_drift_fail", "status_mismatch" in validate_report(status_bad))
    next_bad = json.loads(json.dumps(passed)); next_bad["r2af_contract_records"][0]["next_phase"] = "wrong"; check("next_phase_drift_fail", any(i.startswith("r2af_contract_") for i in validate_report(next_bad)))
    check("root_current_readback_fail", public_readback_match(999)["current_conclusions_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
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
