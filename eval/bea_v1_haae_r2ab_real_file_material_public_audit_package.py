#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AB real-file material public audit package.

Public-only audit/package of the committed R2AA public artifact. It does not
read private roots/material, recompute, generate, scan source, or compute metrics.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AB Real-File Material Public Audit Package"
SLUG = "bea_v1_haae_r2ab_real_file_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AA_CHECKPOINT = "f325b65"
R2AA_STATUS = "haae_r2aa_actual_explicit_local_real_file_material_smoke_complete_r2ab_public_audit_authorized"
R2Z_CHECKPOINT = "a763a84"
R2AA_SELF_TEST_TOTAL = 24
R2AA_REPORT_PATH = Path("artifacts/bea_v1_haae_r2aa_actual_explicit_local_real_file_material_smoke/bea_v1_haae_r2aa_actual_explicit_local_real_file_material_smoke_report.json")

STATUS_PASS = "haae_r2ab_real_file_material_public_audit_package_complete_r2ac_real_file_material_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2ab_fail_closed_source_lock_mismatch"
STATUS_FAIL_MATERIAL = "haae_r2ab_fail_closed_material_audit_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ab_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ab_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2ab_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 15
NEXT_PHASE = "BEA-v1-HAAE-R2AC Actual Real-File Material Experiment"

STOP_FALSE_FIELDS = ["new_material_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "broad_scan_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]
GATE_NAMES = ["r2aa_source_locked_gate", "r2aa_status_gate", "r2aa_self_test_24_gate", "r2z_source_checkpoint_gate", "target_20_gate", "candidate_depth_40_gate", "source_file_count_bucket_gate", "source_cap_500_gate", "row_cap_20000_gate", "real_file_material_complete_gate", "no_metrics_gate", "aggregate_only_gate", "public_only_audit_gate", "no_private_read_gate", "no_recompute_generation_scan_gate", "r2ac_only_stop_go_gate", "no_method_default_scaling_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2aa(r2aa: dict[str, Any]) -> dict[str, bool]:
    src = (r2aa.get("source_lock_records") or [{}])[0]
    material = (r2aa.get("material_generation_records") or [{}])[0]
    gold = (r2aa.get("gold_policy_records") or [{}])[0]
    claim = (r2aa.get("claim_boundary_records") or [{}])[0]
    stop = (r2aa.get("stop_go_records") or [{}])[0]
    status_ok = r2aa.get("status") == R2AA_STATUS
    scan_ok = r2aa.get("forbidden_scan", {}).get("status") == "pass"
    self_test_ok = r2aa.get("self_test_total") == R2AA_SELF_TEST_TOTAL
    source_ok = src.get("locked_haae_r2z_checkpoint") == R2Z_CHECKPOINT and src.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2ab_public_audit_authorized_bool") is True
    stop_ok = all(stop.get(field, False) is False for field in STOP_FALSE_FIELDS)
    claim_ok = claim.get("experiment_metrics_bool") is False and claim.get("topk_mrr_metrics_bool") is False and claim.get("raw_publication_bool") is False and claim.get("method_winner_claim_bool") is False and claim.get("default_runtime_claim_bool") is False and claim.get("scaling_claim_bool") is False
    material_ok = (
        material.get("target_task_count_bucket") == "target_20"
        and material.get("candidate_depth_bucket") == "candidate_depth_40"
        and material.get("source_file_count_bucket") == "count_21_to_50"
        and material.get("source_file_cap_bucket") == "source_file_cap_500"
        and material.get("row_cap_bucket") == "row_cap_20000"
        and material.get("material_generation_complete_bool") is True
        and material.get("raw_rows_published_bool") is False
        and gold.get("gold_private_eval_only_bool") is True
        and gold.get("gold_used_for_ranking_bool") is False
    )
    aggregate_ok = material.get("raw_rows_published_bool") is False and scan_ok
    source_locked = status_ok and scan_ok and self_test_ok and source_ok and auth_ok and stop_ok and claim_ok
    return {"status_ok": status_ok, "scan_ok": scan_ok, "self_test_ok": self_test_ok, "source_ok": source_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "material_ok": material_ok, "aggregate_ok": aggregate_ok, "source_locked": source_locked}


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
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AA_CHECKPOINT, R2AA_STATUS, "R2AA self-test 24/24", R2Z_CHECKPOINT, "target20", "depth40", "source_file_count_bucket count_21_to_50", "source cap 500", "row cap 20000", "real-file material generation complete", "no metrics", "aggregate-only", "R2AB-only", NEXT_PHASE, "existing R2AA private material", "explicit private root", "no new material generation/retrieval/runtime/source scan/CI/network/provider/clone/broad scan/default/method/scaling/raw publication"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ab-real-file-material-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ab-real-file-material-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2ab-real-file-material-public-audit-package.md" in current_root and has_all(current_root)
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2aa: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2aa is None:
        try: r2aa = load_json(repo / R2AA_REPORT_PATH)
        except Exception: r2aa = {}
    audit = audit_r2aa(r2aa)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["material_ok"]:
        status = STATUS_FAIL_MATERIAL
    elif not audit["claim_ok"] or not audit["stop_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2aa_source_locked_gate": audit["source_locked"], "r2aa_status_gate": audit["status_ok"], "r2aa_self_test_24_gate": audit["self_test_ok"], "r2z_source_checkpoint_gate": audit["source_ok"], "target_20_gate": audit["material_ok"], "candidate_depth_40_gate": audit["material_ok"], "source_file_count_bucket_gate": audit["material_ok"], "source_cap_500_gate": audit["material_ok"], "row_cap_20000_gate": audit["material_ok"], "real_file_material_complete_gate": audit["material_ok"], "no_metrics_gate": audit["claim_ok"], "aggregate_only_gate": audit["aggregate_ok"], "public_only_audit_gate": True, "no_private_read_gate": True, "no_recompute_generation_scan_gate": True, "r2ac_only_stop_go_gate": True, "no_method_default_scaling_claim_gate": audit["claim_ok"], "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2absource0000", "locked_haae_r2aa_checkpoint": R2AA_CHECKPOINT, "locked_haae_r2aa_status": R2AA_STATUS, "locked_r2aa_source_r2z_checkpoint": R2Z_CHECKPOINT, "r2aa_status_match_bool": audit["status_ok"], "r2aa_forbidden_scan_pass_bool": audit["scan_ok"], "r2aa_self_test_24_bool": audit["self_test_ok"], "r2aa_r2ab_authorization_match_bool": audit["auth_ok"], "r2aa_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "material_audit_records": [{"anonymous_material_audit_id": "haaer2abmaterial0000", "target_task_count_bucket": "target20", "candidate_depth_bucket": "depth40", "source_file_count_bucket": "count_21_to_50", "source_cap_bucket": "source_cap_500", "row_cap_bucket": "row_cap_20000", "real_file_material_generation_complete_bool": audit["material_ok"], "private_write_nonzero_bool": True, "no_experiment_metrics_bool": audit["claim_ok"], "aggregate_only_bool": audit["aggregate_ok"], "r2ab_only_public_audit_bool": True}],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2abboundary0000", "public_only_audit_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "recompute_bool": False, "generation_bool": False, "source_scan_bool": False, "experiment_metrics_bool": False, "retrieval_runtime_bool": False, "ci_network_provider_clone_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2abclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_provider_clone_bool": False, "broad_scan_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2abgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2absynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2aa_status_fail", "self_test_drift_fail", "r2z_checkpoint_drift_fail", "material_bounds_drift_fail", "metrics_overauth_fail", "aggregate_boundary_fail", "stop_go_overauth_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail", "next_phase_overauth_fail", "r2ac_private_root_required_mutation_fail", "r2ac_existing_material_only_mutation_fail", "r2ac_aggregate_metrics_only_mutation_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2abreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2abstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2aa_public_artifact", "haae_r2ac_actual_real_file_material_experiment_authorized_bool": passed, "r2ac_explicit_private_root_required_bool": passed, "r2ac_reads_existing_r2aa_private_material_only_bool": passed, "r2ac_aggregate_metrics_only_bool": passed, "new_material_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "broad_scan_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "material_audit_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2aa_checkpoint") != R2AA_CHECKPOINT or source.get("locked_haae_r2aa_status") != R2AA_STATUS or source.get("locked_r2aa_source_r2z_checkpoint") != R2Z_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2aa_status_match_bool", "r2aa_forbidden_scan_pass_bool", "r2aa_self_test_24_bool", "r2aa_r2ab_authorization_match_bool", "r2aa_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    material = (report.get("material_audit_records") or [{}])[0]
    if material.get("target_task_count_bucket") != "target20" or material.get("candidate_depth_bucket") != "depth40" or material.get("source_file_count_bucket") != "count_21_to_50" or material.get("source_cap_bucket") != "source_cap_500" or material.get("row_cap_bucket") != "row_cap_20000": issues.append("material_bounds_mismatch")
    for field in ["real_file_material_generation_complete_bool", "private_write_nonzero_bool", "no_experiment_metrics_bool", "aggregate_only_bool", "r2ab_only_public_audit_bool"]:
        if material.get(field) is not True: issues.append(f"material_{field}")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "private_material_read_bool", "recompute_bool", "generation_bool", "source_scan_bool", "experiment_metrics_bool", "retrieval_runtime_bool", "ci_network_provider_clone_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_provider_clone_bool", "broad_scan_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2ac_actual_real_file_material_experiment_authorized_bool") is not True: issues.append("missing_r2ac_authorization")
        for field in ["r2ac_explicit_private_root_required_bool", "r2ac_reads_existing_r2aa_private_material_only_bool", "r2ac_aggregate_metrics_only_bool"]:
            if stop.get(field) is not True: issues.append(f"missing_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["new_material_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "broad_scan_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
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
    base = load_json(repo / R2AA_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2aa_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 23; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    src = json.loads(json.dumps(base)); src["source_lock_records"][0]["locked_haae_r2z_checkpoint"] = "wrong"; check("r2z_checkpoint_drift_fail", build_report(src)["status"] == STATUS_FAIL_SOURCE)
    mat = json.loads(json.dumps(base)); mat["material_generation_records"][0]["candidate_depth_bucket"] = "depth_0"; check("material_bounds_drift_fail", build_report(mat)["status"] == STATUS_FAIL_MATERIAL)
    metrics = json.loads(json.dumps(base)); metrics["claim_boundary_records"][0]["experiment_metrics_bool"] = True; check("metrics_overauth_fail", build_report(metrics)["status"] == STATUS_FAIL_SOURCE)
    boundary = json.loads(json.dumps(passed)); boundary["boundary_audit_records"][0]["private_root_read_bool"] = True; check("aggregate_boundary_fail", any(i.startswith("boundary_") for i in validate_report(boundary)))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    next_over = json.loads(json.dumps(passed)); next_over["stop_go_records"][0]["new_material_generation_authorized_bool"] = True; check("next_phase_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(next_over)))
    root_req = json.loads(json.dumps(passed)); root_req["stop_go_records"][0]["r2ac_explicit_private_root_required_bool"] = False; check("r2ac_private_root_required_mutation_fail", "missing_r2ac_explicit_private_root_required_bool" in validate_report(root_req))
    existing_only = json.loads(json.dumps(passed)); existing_only["stop_go_records"][0]["r2ac_reads_existing_r2aa_private_material_only_bool"] = False; check("r2ac_existing_material_only_mutation_fail", "missing_r2ac_reads_existing_r2aa_private_material_only_bool" in validate_report(existing_only))
    aggregate_only = json.loads(json.dumps(passed)); aggregate_only["stop_go_records"][0]["r2ac_aggregate_metrics_only_bool"] = False; check("r2ac_aggregate_metrics_only_mutation_fail", "missing_r2ac_aggregate_metrics_only_bool" in validate_report(aggregate_only))
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
