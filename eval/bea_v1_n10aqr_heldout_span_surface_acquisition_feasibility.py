#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility.v1"
PHASE = "BEA-v1-N10AQ-R Heldout Span-Surface Acquisition Feasibility"
STATUS_PASS = "heldout_acquisition_feasibility_pass_execution_authorized"
STATUS_NO_GO = "no_go_n10aqr_no_bounded_heldout_acquisition_path"
STATUSES = (
    STATUS_PASS,
    STATUS_NO_GO,
    "no_go_n10aqr_required_inputs_unavailable",
    "no_go_n10aqr_schema_or_privacy_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility_report.json")
PUBLIC_INPUTS = {
    "n10aq_source_discovery_artifact": (Path("artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json"), "no_go_n10aq_candidate_sources_not_heldout"),
    "n10ap_variant_audit_package_artifact": (Path("artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json"), "adapter_enabled_variant_evaluator_result_audit_package_complete_n10aq_authorized"),
    "n10r_targeted_generation_preflight_artifact": (Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json"), None),
}
CODE_SURFACES = {
    "n10aq_discovery_evaluator": Path("eval/bea_v1_n10aq_heldout_span_surface_source_discovery.py"),
    "n10r_targeted_builder_preflight": Path("eval/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight.py"),
    "n10ao_variant_evaluator": Path("eval/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.py"),
}
LOCAL_METADATA_TARGETS = {
    "release_binary_bucket": Path("target/release/openlocus"),
    "existing_n10_span_rows_bucket": Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl"),
    "p4l_private_outcomes_bucket": Path(".openlocus/research-private/local_n6xfr_recovery/p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl"),
    "n1_candidate_gold_trace_bucket": Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_candidate_gold_trace.jsonl"),
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff", "command",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "local_prerequisite_bucket", "availability_bucket", "candidate_acquisition_bucket", "acquisition_path_bucket",
    "denominator_bucket", "source_distinctness_bucket", "parameterization_bucket", "code_surface_bucket",
    "inspection_bucket", "decision_bucket", "blocker_bucket", "next_required_input_bucket", "privacy_boundary_bucket",
    "no_execution_bucket", "n10ar_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        expected_ok = True if expected is None else observed == expected
        passed = load_status == "pass" and expected_ok and forbidden == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10aqrin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected or "any_public_status", "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def count_lines_metadata_only(path: Path) -> int:
    full = root() / path
    if not full.exists() or not full.is_file():
        return 0
    count = 0
    with full.open("rb") as handle:
        for _ in handle:
            count += 1
    return count


def local_prerequisite_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    for idx, (bucket, path) in enumerate(LOCAL_METADATA_TARGETS.items()):
        exists = (root() / path).exists()
        line_count = count_lines_metadata_only(path) if bucket != "release_binary_bucket" else 0
        rows.append({"anonymous_local_prerequisite_id": f"n10aqrpre{idx:04d}", "local_prerequisite_bucket": bucket, "availability_bucket": "present" if exists else "missing", "metadata_only_bool": True, "content_read_bool": False, "record_count_bucket": "gt50" if line_count >= 50 else ("one_to_49" if line_count else "none"), "usable_as_distinct_heldout_bool": False})
    ok = True
    return rows, ok


def candidate_acquisition_path_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10aq = artifacts.get("n10aq_source_discovery_artifact", {})
    selection = (n10aq.get("source_selection_records") or [{}])[0]
    eligible = int(selection.get("eligible_heldout_source_count", 0) or 0)
    rows = [
        {"anonymous_candidate_acquisition_path_id": "n10aqrpath0000", "candidate_acquisition_bucket": "reuse_locally_discovered_span_source", "acquisition_path_bucket": "blocked_no_distinct_heldout_source", "denominator_bucket": "none_declared", "expected_row_count_ge_50_bool": False, "source_distinctness_bucket": "same_or_indistinguishable_from_existing_n10", "bounded_command_identified_bool": False, "privacy_plan_defined_bool": False, "eligible_for_execution_bool": False, "prior_eligible_source_count": eligible},
        {"anonymous_candidate_acquisition_path_id": "n10aqrpath0001", "candidate_acquisition_bucket": "parameterized_recovered_n1_p4l_pipeline", "acquisition_path_bucket": "blocked_no_disjoint_denominator_parameter", "denominator_bucket": "same_recovered_locked_surface", "expected_row_count_ge_50_bool": False, "source_distinctness_bucket": "not_proven_distinct", "bounded_command_identified_bool": False, "privacy_plan_defined_bool": True, "eligible_for_execution_bool": False, "requires_full_replay_or_existing_private_source_bool": True},
        {"anonymous_candidate_acquisition_path_id": "n10aqrpath0002", "candidate_acquisition_bucket": "full_frozen_replay_with_new_denominator", "acquisition_path_bucket": "out_of_scope_broad_replay_required", "denominator_bucket": "undeclared_external_or_benchmark_source", "expected_row_count_ge_50_bool": False, "source_distinctness_bucket": "not_proven_distinct", "bounded_command_identified_bool": False, "privacy_plan_defined_bool": False, "eligible_for_execution_bool": False, "requires_retrieval_or_openlocus_execution_bool": True},
    ]
    return rows, False


def inspect_code_surface(path: Path) -> str:
    full = root() / path
    if not full.exists():
        return ""
    return full.read_text(encoding="utf-8", errors="replace")


def pipeline_parameterization_records() -> tuple[list[dict[str, Any]], bool]:
    n10r_text = inspect_code_surface(CODE_SURFACES["n10r_targeted_builder_preflight"])
    n10aq_text = inspect_code_surface(CODE_SURFACES["n10aq_discovery_evaluator"])
    n10ao_text = inspect_code_surface(CODE_SURFACES["n10ao_variant_evaluator"])
    rows = [
        {"anonymous_pipeline_parameterization_id": "n10aqrpipe0000", "code_surface_bucket": "n10r_targeted_builder_preflight", "inspection_bucket": "static_text_only", "targeted_denominator_filter_available_bool": "targeted_denominator_filter_supported" in n10r_text, "can_produce_disjoint_heldout_span_rows_bool": False, "can_run_without_full_replay_bool": False, "bounded_command_identified_bool": False, "parameterization_bucket": "targeted_n2_not_heldout_span_acquisition"},
        {"anonymous_pipeline_parameterization_id": "n10aqrpipe0001", "code_surface_bucket": "n10aq_discovery_evaluator", "inspection_bucket": "static_text_only", "local_discovery_capable_bool": "MAX_CANDIDATE_FILES_SNIFFED" in n10aq_text, "can_produce_disjoint_heldout_span_rows_bool": False, "can_run_without_full_replay_bool": True, "bounded_command_identified_bool": False, "parameterization_bucket": "discovery_only_no_acquisition_builder"},
        {"anonymous_pipeline_parameterization_id": "n10aqrpipe0002", "code_surface_bucket": "n10ao_variant_evaluator", "inspection_bucket": "static_text_only", "adapter_validation_capable_bool": "enable_scoped_private_span_rows" in n10ao_text, "can_produce_disjoint_heldout_span_rows_bool": False, "can_run_without_full_replay_bool": True, "bounded_command_identified_bool": False, "parameterization_bucket": "validation_consumer_not_source_acquisition_builder"},
    ]
    return rows, False


def decision_records(path_ok: bool, pipeline_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    feasible = path_ok and pipeline_ok
    return [{"anonymous_decision_id": "n10aqrdecision0000", "decision_bucket": "bounded_heldout_acquisition_path_available" if feasible else "no_bounded_heldout_acquisition_path", "blocker_bucket": "no_distinct_heldout_source_or_parameterized_bounded_builder", "bounded_acquisition_command_identified_bool": feasible, "denominator_declared_bool": feasible, "not_same_as_n10_source_bool": feasible, "expected_rows_ge_50_bool": feasible, "privacy_plan_defined_bool": feasible, "n10ar_authorized_bool": feasible, "next_required_input_bucket": "heldout_span_surface_rows_or_exact_bounded_acquisition_command"}], feasible


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aqrprivacy0000", "privacy_boundary_bucket": "metadata_static_feasibility_only_no_private_content_public", "private_content_read_bool": False, "private_path_public_bool": False, "private_filename_public_bool": False, "raw_row_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "repo_or_task_id_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10aqrnoexec0000", "no_execution_bucket": "feasibility_only_no_acquisition_execution", "openlocus_binary_execution_count": 0, "retrieval_execution_count": 0, "benchmark_replay_count": 0, "git_clone_count": 0, "provider_call_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "p4l_n1_n2_n3_rerun_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_valid_bool": True}], True


def n10ar_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ar_handoff_id": "n10aqrhandoff0000", "n10ar_handoff_bucket": "n10ar_execution_authorized" if complete else "n10ar_not_authorized", "n10ar_authorized_bool": complete, "selected_source_read_authorized_bool": complete, "heldout_validation_execution_authorized_bool": complete, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, path_ok: bool, pipe_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok),
        ("bounded_acquisition_path_identified", path_ok),
        ("pipeline_parameterization_feasible", pipe_ok),
        ("decision_complete", True),
        ("n10ar_authorized", decision_ok),
        ("privacy_boundary", privacy_ok),
        ("no_execution", noexec_ok),
        ("forbidden_scan", scanner_ok),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ar_execution_authorized" if complete else "n10ar_not_authorized", "next_allowed_phase": "BEA-v1-N10AR Heldout Span-Surface Validation" if complete else "none_until_bounded_heldout_span_surface_acquisition_path_or_rows_exist", "next_allowed_scope_bucket": "declared_bounded_heldout_source_only" if complete else "no_next_phase", "n10ar_authorized": complete, "private_read_authorized": complete, "heldout_validation_execution_authorized": complete, "openlocus_execution_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_enablement_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10aqr_required_inputs_unavailable"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10aqr_schema_or_privacy_boundary_invalid"
    if not decision_ok:
        return STATUS_NO_GO
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    inputs, artifacts, input_ok = input_artifact_records()
    prereq_rows, _prereq_ok = local_prerequisite_records()
    path_rows, path_ok = candidate_acquisition_path_records(artifacts)
    pipe_rows, pipe_ok = pipeline_parameterization_records()
    decision_rows, decision_ok = decision_records(path_ok, pipe_ok)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, decision_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "heldout_acquisition_feasibility_only_no_execution", "generated_by": "bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "local_prerequisite_records": prereq_rows, "candidate_acquisition_path_records": path_rows, "pipeline_parameterization_records": pipe_rows, "decision_records": decision_rows, "privacy_boundary_records": privacy_rows, "no_execution_records": noexec_rows, "n10ar_handoff_records": n10ar_handoff_records(complete), "gate_records": gate_records(input_ok, path_ok, pipe_ok, decision_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10ar_handoff_records"] = n10ar_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, path_ok, pipe_ok, decision_ok, privacy_ok, noexec_ok, scanner_ok)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, _artifacts, input_ok = input_artifact_records()
    decision_pass, pass_ok = decision_records(True, True)
    decision_no, no_ok = decision_records(False, False)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_NO_GO, "no_go_n10aqr_required_inputs_unavailable", "no_go_n10aqr_schema_or_privacy_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload", "command"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 3),
        check("synthetic_pass_path", pass_ok and decision_pass[0]["bounded_acquisition_command_identified_bool"] is True),
        check("synthetic_no_go_path", not no_ok and decision_no[0]["bounded_acquisition_command_identified_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_content_read_bool"] is False and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_execution", noexec_ok and noexec_rows[0]["openlocus_binary_execution_count"] == 0 and noexec_rows[0]["retrieval_execution_count"] == 0),
        check("handoff_no_go", n10ar_handoff_records(False)[0]["n10ar_authorized_bool"] is False and stop_go_records(False)[0]["private_read_authorized"] is False),
        check("status_no_go", status_for(True, True, False, True, True) == STATUS_NO_GO),
        check("status_pass", status_for(True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AQ-R heldout span-surface acquisition feasibility")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    decision = report["decision_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, decision={decision['decision_bucket']})")


if __name__ == "__main__":
    main()
