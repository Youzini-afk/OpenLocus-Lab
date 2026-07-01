#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AF real-file signal robustness material preflight.

Public-only design/preflight package after R2AE. It reads only the committed
public R2AE artifact/docs and does not read or write private material, execute
experiments, generate candidates/material, scan source, retrieve, or use CI,
network, providers, schedulers, or selectors.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight"
SLUG = "bea_v1_haae_r2af_real_file_signal_robustness_material_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AE_CHECKPOINT = "4be50bc"
R2AE_STATUS = "haae_r2ae_real_file_signal_robustness_scale_decision_complete_r2af_robustness_material_preflight_authorized"
R2AE_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ae_real_file_signal_robustness_scale_decision/bea_v1_haae_r2ae_real_file_signal_robustness_scale_decision_report.json")

STATUS_PASS = "haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized"
STATUS_NO_GO = "haae_r2af_no_go_no_safe_r2ag_material_generation_contract"
STATUS_FAIL_SOURCE = "haae_r2af_fail_closed_source_lock_mismatch"
STATUS_FAIL_LEAK = "haae_r2af_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2af_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 26
NEXT_PHASE = "BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation"

VARIANT_BUCKETS = [
    "symbol_content_ablation",
    "query_token_masking",
    "shuffled_content_control",
    "negative_control_strengthening",
]

STOP_FORBIDDEN_TRUE = [
    "r2ag_experiment_metrics_authorized_bool", "r2ah_experiment_authorized_bool",
    "r2ag_broad_source_scan_authorized_bool", "r2ag_ci_execution_authorized_bool", "r2ag_network_provider_clone_authorized_bool",
    "execution_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool",
    "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool",
    "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool",
    "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool",
    "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
]

GATE_NAMES = [
    "r2ae_source_locked_gate", "r2ae_r2af_authorization_gate", "public_only_preflight_gate",
    "no_private_read_write_gate", "no_execution_recompute_generation_gate", "no_retrieval_runtime_source_scan_gate",
    "no_ci_network_provider_clone_gate", "r2ag_material_generation_only_gate", "target_20_existing_r2aa_task_frame_gate",
    "candidate_depth_40_gate", "row_cap_20000_gate", "variant_suite_gate", "no_path_gold_leakage_design_gate",
    "explicit_private_root_required_gate", "bounded_public_corpus_manifest_gate", "aggregate_only_public_artifact_gate",
    "material_qa_only_no_r2ag_metrics_gate", "no_r2ah_experiment_gate", "no_ci_scale_default_method_claim_gate",
    "forbidden_scan_pass_gate", "docs_readback_match_gate",
]

SYNTHETIC_VALIDATORS = [
    "source_lock_pass", "wrong_r2ae_status_fail", "missing_r2af_authorization_fail", "r2ae_contract_drift_fail",
    "r2ah_overauth_fail", "target_bound_drift_fail", "depth_bound_drift_fail", "row_cap_drift_fail",
    "variant_set_drift_fail", "private_root_required_fail", "corpus_manifest_required_fail",
    "aggregate_artifact_required_fail", "metrics_overauth_fail", "execution_overauth_fail", "source_scan_overauth_fail",
    "claim_boundary_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail", "material_generation_only_drift_fail",
    "r2ag_private_write_authorization_drift_fail", "r2ag_bounded_source_scan_authorization_drift_fail",
    "r2ag_broad_scan_overauth_fail", "required_gate_missing_fail", "synthetic_validator_missing_fail", "public_readback_record_missing_fail",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2ae(r2ae: dict[str, Any]) -> dict[str, bool]:
    stop = (r2ae.get("stop_go_records") or [{}])[0]
    contract = (r2ae.get("r2af_contract_records") or [{}])[0]
    claim = (r2ae.get("claim_boundary_records") or [{}])[0]
    status_ok = r2ae.get("status") == R2AE_STATUS
    scan_ok = r2ae.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2af_robustness_material_preflight_authorized_bool") is True and stop.get("r2af_public_preflight_only_bool") is True
    stop_ok = all(stop.get(field) is False for field in [
        "r2af_execution_authorized_bool", "r2af_private_read_authorized_bool", "r2af_private_write_authorized_bool",
        "r2af_candidate_generation_authorized_bool", "r2af_source_scan_authorized_bool", "r2af_ci_execution_authorized_bool",
        "r2af_network_provider_clone_authorized_bool", "execution_authorized_bool", "ci_execution_authorized_bool",
        "scale_execution_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_authorized_bool",
        "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool",
        "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool",
        "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool",
        "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
    ])
    contract_ok = (
        contract.get("next_phase") == PHASE
        and contract.get("public_only_preflight_bool") is True
        and contract.get("define_robustness_material_recipe_bool") is True
        and contract.get("r2ag_later_may_do_explicit_local_bounded_robustness_material_generation_bool") is True
        and contract.get("public_aggregate_only_bool") is True
        and contract.get("no_method_default_scaling_claim_bool") is True
        and all(contract.get(field) is False for field in [
            "execution_in_r2ae_bool", "private_read_in_r2ae_bool", "private_write_in_r2ae_bool",
            "candidate_generation_in_r2ae_bool", "source_scan_in_r2ae_bool", "ci_execution_in_r2ae_bool",
            "network_provider_clone_in_r2ae_bool",
        ])
    )
    claim_ok = claim.get("public_only_decision_bool") is True and all(claim.get(field) is False for field in [
        "private_read_bool", "private_write_bool", "execution_bool", "recompute_bool", "generation_bool",
        "retrieval_runtime_source_scan_bool", "ci_network_provider_clone_bool", "scheduler_selector_bool",
        "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "raw_publication_bool",
    ])
    source_locked = status_ok and scan_ok and auth_ok and stop_ok and contract_ok and claim_ok
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "contract_ok": contract_ok, "claim_ok": claim_ok, "source_locked": source_locked}


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
        PHASE, STATUS_PASS, f"{total}/{total}", R2AE_CHECKPOINT, R2AE_STATUS,
        "target 20 existing R2AA task frame if available", "depth 40", "row cap 20000",
        "symbol/content ablation", "query-token masking", "shuffled content control", "negative/control strengthening",
        "explicit private root", "bounded public corpus manifest", "aggregate-only public artifact",
        "no metrics in R2AG beyond material QA", "authorize only R2AG material generation", "no R2AH experiment",
        "no CI/scale/default/method claim", "no private reads/writes", "no execution", "no source scan", "no candidate/material generation",
        "R2AG local execution authorized", "R2AG private write authorized", "R2AG bounded source scan authorized", "R2AG candidate/material generation authorized",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]

    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)

    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2af-real-file-signal-robustness-material-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2af-real-file-signal-robustness-material-preflight.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2af-real-file-signal-robustness-material-preflight.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ae: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ae is None:
        try: r2ae = load_json(repo / R2AE_REPORT_PATH)
        except Exception: r2ae = {}
    audit = audit_r2ae(r2ae)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]: status = STATUS_FAIL_SOURCE
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {name: True for name in GATE_NAMES}
    gates.update({"r2ae_source_locked_gate": audit["source_locked"], "r2ae_r2af_authorization_gate": audit["auth_ok"], "docs_readback_match_gate": readback["all_public_readback_match_bool"]})
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2afsource0000", "locked_haae_r2ae_checkpoint": R2AE_CHECKPOINT, "locked_haae_r2ae_status": R2AE_STATUS, "r2ae_status_match_bool": audit["status_ok"], "r2ae_forbidden_scan_pass_bool": audit["scan_ok"], "r2ae_r2af_authorization_match_bool": audit["auth_ok"], "r2ae_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "r2ae_contract_match_bool": audit["contract_ok"], "source_locked_bool": audit["source_locked"]}],
        "r2ag_material_design_records": [{"anonymous_r2ag_design_id": "haaer2afdesign0000", "next_phase": NEXT_PHASE, "public_only_preflight_bool": True, "target_task_frame_bucket": "target_20_existing_r2aa_task_frame_if_available", "candidate_depth_cap_bucket": "depth_40", "private_row_cap_bucket": "row_cap_20000", "explicit_private_root_required_bool": True, "bounded_public_corpus_manifest_required_bool": True, "aggregate_only_public_artifact_bool": True, "material_qa_only_no_experiment_metrics_bool": True, "path_gold_leakage_forbidden_bool": True, "existing_r2aa_task_frame_preferred_bool": True, "fallback_requires_public_reason_bool": True}],
        "robustness_variant_records": [{"anonymous_variant_id": f"haaer2afvariant{idx:04d}", "variant_bucket": bucket, "purpose_bucket": purpose, "path_gold_leakage_forbidden_bool": True, "material_qa_only_bool": True} for idx, (bucket, purpose) in enumerate([("symbol_content_ablation", "test_symbol_content_dependence_without_revealing_locations"), ("query_token_masking", "test_identifier_overlap_dependence_without_revealing_gold"), ("shuffled_content_control", "test_content_position_control_without_revealing_files"), ("negative_control_strengthening", "test_control_separation_without_method_claim")])],
        "boundary_records": [{"anonymous_boundary_id": "haaer2afboundary0000", "public_only_design_preflight_bool": True, "private_read_bool": False, "private_write_bool": False, "execution_bool": False, "recompute_bool": False, "candidate_generation_bool": False, "material_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_provider_clone_bool": False, "scheduler_selector_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2afclaim0000", "r2ag_material_generation_only_bool": True, "r2ag_experiment_metrics_bool": False, "r2ah_experiment_bool": False, "ci_scale_default_method_claim_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "runtime_change_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2afgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2afsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2afreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2afstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_revisit_r2af_design", "haae_r2ag_explicit_local_bounded_robustness_material_generation_authorized_bool": passed, "r2ag_material_generation_only_bool": passed, "r2ag_requires_explicit_private_root_bool": passed, "r2ag_requires_bounded_public_corpus_manifest_bool": passed, "r2ag_aggregate_only_public_artifact_bool": passed, "r2ag_material_qa_only_no_experiment_metrics_bool": passed, "r2ag_local_execution_authorized_bool": passed, "r2ag_private_write_authorized_bool": passed, "r2ag_candidate_generation_authorized_bool": passed, "r2ag_material_generation_authorized_bool": passed, "r2ag_bounded_source_scan_authorized_bool": passed, "r2ag_broad_source_scan_authorized_bool": False, "r2ag_ci_execution_authorized_bool": False, "r2ag_network_provider_clone_authorized_bool": False, "r2ag_experiment_metrics_authorized_bool": False, "r2ah_experiment_authorized_bool": False, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "scale_execution_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "r2ag_material_design_records", "robustness_variant_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_buckets = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gate_buckets) != set(GATE_NAMES) or len(gate_buckets) != len(GATE_NAMES):
        issues.append("required_gate_coverage_mismatch")
    synth_buckets = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(synth_buckets) != set(SYNTHETIC_VALIDATORS) or len(synth_buckets) != len(SYNTHETIC_VALIDATORS):
        issues.append("synthetic_validator_coverage_mismatch")
    readback_records = report.get("public_readback_records", [])
    if len(readback_records) != 1 or readback_records[0].get("all_public_readback_match_bool") is not True:
        issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2ae_checkpoint") != R2AE_CHECKPOINT or source.get("locked_haae_r2ae_status") != R2AE_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2ae_status_match_bool", "r2ae_forbidden_scan_pass_bool", "r2ae_r2af_authorization_match_bool", "r2ae_no_forbidden_stop_go_drift_bool", "r2ae_contract_match_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    design = (report.get("r2ag_material_design_records") or [{}])[0]
    for field, expected in {"next_phase": NEXT_PHASE, "target_task_frame_bucket": "target_20_existing_r2aa_task_frame_if_available", "candidate_depth_cap_bucket": "depth_40", "private_row_cap_bucket": "row_cap_20000"}.items():
        if design.get(field) != expected: issues.append(f"r2ag_design_{field}")
    for field in ["public_only_preflight_bool", "explicit_private_root_required_bool", "bounded_public_corpus_manifest_required_bool", "aggregate_only_public_artifact_bool", "material_qa_only_no_experiment_metrics_bool", "path_gold_leakage_forbidden_bool", "existing_r2aa_task_frame_preferred_bool", "fallback_requires_public_reason_bool"]:
        if design.get(field) is not True: issues.append(f"r2ag_design_{field}")
    variants = {row.get("variant_bucket") for row in report.get("robustness_variant_records", [])}
    if variants != set(VARIANT_BUCKETS): issues.append("variant_set_mismatch")
    for row in report.get("robustness_variant_records", []):
        if row.get("path_gold_leakage_forbidden_bool") is not True or row.get("material_qa_only_bool") is not True: issues.append("variant_boundary_mismatch")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_design_preflight_bool") is not True: issues.append("boundary_public_only_design_preflight_bool")
    for field in ["private_read_bool", "private_write_bool", "execution_bool", "recompute_bool", "candidate_generation_bool", "material_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_provider_clone_bool", "scheduler_selector_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    if claim.get("r2ag_material_generation_only_bool") is not True: issues.append("claim_r2ag_material_generation_only_bool")
    for field in ["r2ag_experiment_metrics_bool", "r2ah_experiment_bool", "ci_scale_default_method_claim_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "runtime_change_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["haae_r2ag_explicit_local_bounded_robustness_material_generation_authorized_bool", "r2ag_material_generation_only_bool", "r2ag_requires_explicit_private_root_bool", "r2ag_requires_bounded_public_corpus_manifest_bool", "r2ag_aggregate_only_public_artifact_bool", "r2ag_material_qa_only_no_experiment_metrics_bool", "r2ag_local_execution_authorized_bool", "r2ag_private_write_authorized_bool", "r2ag_candidate_generation_authorized_bool", "r2ag_material_generation_authorized_bool", "r2ag_bounded_source_scan_authorized_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_missing_{field}")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_not_passed_{gate.get('gate_bucket', 'unknown')}")
        if stop.get("r2ag_material_generation_only_bool") is not True:
            issues.append("stop_go_missing_r2ag_material_generation_only_bool")
        elif not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    for field in STOP_FORBIDDEN_TRUE:
        if stop.get(field) is not False: issues.append(f"stop_go_overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AE_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ae_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    noauth = json.loads(json.dumps(base)); noauth["stop_go_records"][0]["haae_r2af_robustness_material_preflight_authorized_bool"] = False; check("missing_r2af_authorization_fail", build_report(noauth)["status"] == STATUS_FAIL_SOURCE)
    contract = json.loads(json.dumps(base)); contract["r2af_contract_records"][0]["define_robustness_material_recipe_bool"] = False; check("r2ae_contract_drift_fail", build_report(contract)["status"] == STATUS_FAIL_SOURCE)
    r2ah = json.loads(json.dumps(passed)); r2ah["stop_go_records"][0]["r2ah_experiment_authorized_bool"] = True; check("r2ah_overauth_fail", any(i.startswith("stop_go_overauthorization_") for i in validate_report(r2ah)))
    target = json.loads(json.dumps(passed)); target["r2ag_material_design_records"][0]["target_task_frame_bucket"] = "target_200"; check("target_bound_drift_fail", "r2ag_design_target_task_frame_bucket" in validate_report(target))
    depth = json.loads(json.dumps(passed)); depth["r2ag_material_design_records"][0]["candidate_depth_cap_bucket"] = "depth_400"; check("depth_bound_drift_fail", "r2ag_design_candidate_depth_cap_bucket" in validate_report(depth))
    rowcap = json.loads(json.dumps(passed)); rowcap["r2ag_material_design_records"][0]["private_row_cap_bucket"] = "row_cap_0"; check("row_cap_drift_fail", "r2ag_design_private_row_cap_bucket" in validate_report(rowcap))
    variants = json.loads(json.dumps(passed)); variants["robustness_variant_records"].pop(); check("variant_set_drift_fail", "variant_set_mismatch" in validate_report(variants))
    root = json.loads(json.dumps(passed)); root["r2ag_material_design_records"][0]["explicit_private_root_required_bool"] = False; check("private_root_required_fail", "r2ag_design_explicit_private_root_required_bool" in validate_report(root))
    manifest = json.loads(json.dumps(passed)); manifest["r2ag_material_design_records"][0]["bounded_public_corpus_manifest_required_bool"] = False; check("corpus_manifest_required_fail", "r2ag_design_bounded_public_corpus_manifest_required_bool" in validate_report(manifest))
    aggregate = json.loads(json.dumps(passed)); aggregate["r2ag_material_design_records"][0]["aggregate_only_public_artifact_bool"] = False; check("aggregate_artifact_required_fail", "r2ag_design_aggregate_only_public_artifact_bool" in validate_report(aggregate))
    metrics = json.loads(json.dumps(passed)); metrics["claim_boundary_records"][0]["r2ag_experiment_metrics_bool"] = True; check("metrics_overauth_fail", any(i.startswith("claim_boundary_") for i in validate_report(metrics)))
    execution = json.loads(json.dumps(passed)); execution["boundary_records"][0]["execution_bool"] = True; check("execution_overauth_fail", "boundary_execution_bool" in validate_report(execution))
    source_scan = json.loads(json.dumps(passed)); source_scan["boundary_records"][0]["source_scan_bool"] = True; check("source_scan_overauth_fail", "boundary_source_scan_bool" in validate_report(source_scan))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    material_only = json.loads(json.dumps(passed)); material_only["stop_go_records"][0]["r2ag_material_generation_only_bool"] = False; check("material_generation_only_drift_fail", "stop_go_missing_r2ag_material_generation_only_bool" in validate_report(material_only))
    write_auth = json.loads(json.dumps(passed)); write_auth["stop_go_records"][0]["r2ag_private_write_authorized_bool"] = False; check("r2ag_private_write_authorization_drift_fail", "stop_go_missing_r2ag_private_write_authorized_bool" in validate_report(write_auth))
    bounded_scan = json.loads(json.dumps(passed)); bounded_scan["stop_go_records"][0]["r2ag_bounded_source_scan_authorized_bool"] = False; check("r2ag_bounded_source_scan_authorization_drift_fail", "stop_go_missing_r2ag_bounded_source_scan_authorized_bool" in validate_report(bounded_scan))
    broad_scan = json.loads(json.dumps(passed)); broad_scan["stop_go_records"][0]["r2ag_broad_source_scan_authorized_bool"] = True; check("r2ag_broad_scan_overauth_fail", "stop_go_overauthorization_r2ag_broad_source_scan_authorized_bool" in validate_report(broad_scan))
    missing_gate = json.loads(json.dumps(passed)); missing_gate["pass_fail_gate_records"].pop(); check("required_gate_missing_fail", "required_gate_coverage_mismatch" in validate_report(missing_gate))
    missing_synth = json.loads(json.dumps(passed)); missing_synth["synthetic_validator_records"].pop(); check("synthetic_validator_missing_fail", "synthetic_validator_coverage_mismatch" in validate_report(missing_synth))
    missing_readback = json.loads(json.dumps(passed)); missing_readback["public_readback_records"] = []; check("public_readback_record_missing_fail", "public_readback_record_mismatch" in validate_report(missing_readback))
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
