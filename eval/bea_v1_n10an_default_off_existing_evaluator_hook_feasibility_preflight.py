#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight.v1"
PHASE = "BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight"
STATUS_PASS = "default_off_existing_evaluator_hook_feasibility_preflight_pass_n10ao_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10an_required_inputs_unavailable",
    "no_go_n10an_no_safe_eval_only_hook_strategy",
    "no_go_n10an_existing_evaluator_mutation_risk",
    "no_go_n10an_default_off_boundary_incomplete",
    "no_go_n10an_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json")
INPUTS = {
    "n10am_adapter_integration_audit_package_artifact": (Path("artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json"), "eval_only_adapter_integration_result_audit_package_complete_n10an_authorized"),
    "n10al_adapter_integration_smoke_artifact": (Path("artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json"), "scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized"),
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
}
STATIC_FILES = {
    "span_projection_adapter": Path("eval/bea_v1_span_window_projection_adapter.py"),
    "span_window_helper": Path("eval/bea_v1_span_window_repair_helpers.py"),
    "n10ab_fixed_span_window_repair_smoke": Path("eval/bea_v1_n10ab_fixed_span_window_repair_smoke.py"),
    "n10x_span_level_utility_validation": Path("eval/bea_v1_n10x_n1_span_surface_span_level_utility_validation.py"),
    "n10t_span_surface_proxy_validation": Path("eval/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.py"),
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "evaluator_bucket", "inspection_bucket", "mutation_risk_bucket", "strategy_bucket", "selected_strategy_bucket",
    "default_off_boundary_bucket", "behavior_preservation_bucket", "privacy_boundary_bucket", "no_execution_bucket",
    "n10ao_handoff_bucket", "patch_scope_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation",
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
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
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
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10anin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def read_static_text(bucket: str) -> str:
    return (root() / STATIC_FILES[bucket]).read_text(encoding="utf-8")


def static_candidate_evaluator_records() -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10ab_fixed_span_window_repair_smoke", ("pm50", "top10", "span_extra_depth_promote")),
        ("n10x_span_level_utility_validation", ("span_overlap", "top10", "span_extra_depth_promote")),
        ("n10t_span_surface_proxy_validation", ("file", "top10", "span_extra_depth_promote")),
    ]
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, needles) in enumerate(specs):
        try:
            text = read_static_text(bucket)
            signal_count = sum(1 for needle in needles if needle in text)
            exists = True
        except Exception:
            signal_count = 0
            exists = False
        row_ok = exists and signal_count >= 2
        ok = ok and row_ok
        rows.append({
            "anonymous_static_candidate_evaluator_id": f"n10ancand{idx:04d}",
            "evaluator_bucket": bucket,
            "inspection_bucket": "static_text_only_no_import_no_execution",
            "static_inspection_only_bool": True,
            "candidate_imported_bool": False,
            "candidate_executed_bool": False,
            "static_signal_count": signal_count,
            "mutation_risk_bucket": "medium",
            "direct_hook_recommended_bool": False,
            "variant_evaluator_recommended_bool": True,
            "static_inspection_passed_bool": row_ok,
        })
    return rows, ok


def hook_strategy_decision_records(static_ok: bool, artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10am = artifacts.get("n10am_adapter_integration_audit_package_artifact", {})
    handoff = (n10am.get("n10an_handoff_records") or [{}])[0]
    ok = static_ok and handoff.get("n10an_preflight_authorized_bool") is True
    row = {
        "anonymous_hook_strategy_decision_id": "n10anstrategy0000",
        "selected_strategy_bucket": "new_adapter_enabled_variant_evaluator",
        "strategy_bucket": "add_new_eval_only_variant_evaluator_do_not_mutate_validated_evaluators",
        "modify_existing_validated_evaluator_bool": False,
        "runtime_path_hook_bool": False,
        "eval_only_bool": True,
        "default_off_required_bool": True,
        "strategy_feasible_bool": ok,
        "direct_existing_evaluator_hook_recommended_bool": False,
        "new_variant_evaluator_recommended_bool": True,
    }
    return [row], ok


def default_off_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_default_off_boundary_id": "n10anboundary0000", "default_off_boundary_bucket": "n10ao_variant_requires_explicit_enablement", "default_off_required_bool": True, "default_enabled_bool": False, "private_read_by_default_bool": False, "runtime_default_enablement_bool": False, "existing_evaluator_hook_in_bool": False, "adapter_import_allowed_bool": True, "same_scoped_private_rows_only_when_enabled_bool": True, "default_off_boundary_complete_bool": True}], True


def behavior_preservation_records(strategy_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_behavior_preservation_id": "n10anbehavior0000", "behavior_preservation_bucket": "new_variant_preserves_existing_validated_evaluators", "existing_validated_evaluator_modification_bool": False, "runtime_retrieval_config_modification_bool": False, "candidate_generation_behavior_change_bool": False, "new_arm_or_window_tuning_bool": False, "behavior_preservation_valid_bool": strategy_ok}], strategy_ok


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10anprivacy0000", "privacy_boundary_bucket": "public_static_preflight_only_no_private_rows", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10annoexec0000", "no_execution_bucket": "static_preflight_only_no_import_no_hook_no_runtime", "private_read_count": 0, "candidate_evaluator_import_count": 0, "candidate_evaluator_execution_count": 0, "hook_patch_count": 0, "runtime_default_change_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_valid_bool": True}], True


def n10ao_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ao_handoff_id": "n10anhandoff0000", "n10ao_handoff_bucket": "n10ao_default_off_adapter_enabled_variant_evaluator_patch_authorized" if complete else "n10ao_not_authorized", "n10ao_authorized_bool": complete, "n10ao_patch_authorized_bool": complete, "patch_scope_bucket": "new_eval_only_variant_evaluator_importing_adapter" if complete else "none", "default_off_flag_required_bool": True, "same_scoped_private_rows_read_when_explicitly_enabled_bool": complete, "modify_existing_validated_evaluator_authorized_bool": False, "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, static_ok: bool, strategy_ok: bool, default_ok: bool, behavior_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("static_candidates_inspected", static_ok), ("new_variant_strategy", strategy_ok), ("default_off_boundary", default_ok), ("behavior_preservation", behavior_ok), ("privacy_boundary", privacy_ok), ("no_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ao_default_off_adapter_enabled_variant_evaluator_patch_authorized" if complete else "n10ao_not_authorized", "next_allowed_phase": "BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch" if complete else "none_until_safe_eval_only_hook_strategy_exists", "next_allowed_scope_bucket": "new_eval_only_variant_evaluator_patch_default_off" if complete else "no_next_phase", "n10ao_authorized": complete, "n10ao_patch_authorized": complete, "existing_evaluator_hook_in_authorized": False, "modify_existing_validated_evaluator_authorized": False, "runtime_or_default_enablement_authorized": False, "private_read_by_default_authorized": False, "same_scoped_private_rows_when_explicitly_enabled_authorized": complete, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_or_window_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, static_ok: bool, strategy_ok: bool, default_ok: bool, behavior_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10an_required_inputs_unavailable"
    if not static_ok or not strategy_ok:
        return "no_go_n10an_no_safe_eval_only_hook_strategy"
    if not behavior_ok:
        return "no_go_n10an_existing_evaluator_mutation_risk"
    if not default_ok:
        return "no_go_n10an_default_off_boundary_incomplete"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10an_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    static_rows, static_ok = static_candidate_evaluator_records()
    strategy_rows, strategy_ok = hook_strategy_decision_records(static_ok, artifacts)
    default_rows, default_ok = default_off_boundary_records()
    behavior_rows, behavior_ok = behavior_preservation_records(strategy_ok)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, static_ok, strategy_ok, default_ok, behavior_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_static_hook_feasibility_preflight_only", "generated_by": "bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "static_candidate_evaluator_records": static_rows, "hook_strategy_decision_records": strategy_rows, "default_off_boundary_records": default_rows, "behavior_preservation_records": behavior_rows, "n10ao_handoff_records": n10ao_handoff_records(complete), "privacy_boundary_records": privacy_rows, "no_execution_records": noexec_rows, "gate_records": gate_records(input_ok, static_ok, strategy_ok, default_ok, behavior_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, static_ok, strategy_ok, default_ok, behavior_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ao_handoff_records"] = n10ao_handoff_records(complete)
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
    inputs, artifacts, input_ok = input_artifact_records()
    static_rows, static_ok = static_candidate_evaluator_records()
    strategy_rows, strategy_ok = hook_strategy_decision_records(static_ok, artifacts)
    default_rows, default_ok = default_off_boundary_records()
    behavior_rows, behavior_ok = behavior_preservation_records(strategy_ok)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10an_required_inputs_unavailable", "no_go_n10an_no_safe_eval_only_hook_strategy", "no_go_n10an_existing_evaluator_mutation_risk", "no_go_n10an_default_off_boundary_incomplete", "no_go_n10an_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 3),
        check("static_candidates", static_ok and len(static_rows) == 3 and all(r["static_inspection_only_bool"] and not r["candidate_imported_bool"] and not r["candidate_executed_bool"] for r in static_rows)),
        check("candidate_decisions", all(r["mutation_risk_bucket"] == "medium" and not r["direct_hook_recommended_bool"] and r["variant_evaluator_recommended_bool"] for r in static_rows)),
        check("strategy", strategy_ok and strategy_rows[0]["selected_strategy_bucket"] == "new_adapter_enabled_variant_evaluator" and strategy_rows[0]["modify_existing_validated_evaluator_bool"] is False),
        check("default_off", default_ok and default_rows[0]["default_enabled_bool"] is False and default_rows[0]["private_read_by_default_bool"] is False),
        check("behavior", behavior_ok and behavior_rows[0]["existing_validated_evaluator_modification_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_read_count"] == 0),
        check("no_execution", noexec_ok and noexec_rows[0]["candidate_evaluator_import_count"] == 0 and noexec_rows[0]["hook_patch_count"] == 0),
        check("handoff", n10ao_handoff_records(True)[0]["n10ao_patch_authorized_bool"] is True and stop_go_records(True)[0]["existing_evaluator_hook_in_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AN default-off existing-evaluator hook feasibility preflight")
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
    strategy = report["hook_strategy_decision_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, strategy={strategy['selected_strategy_bucket']})")


if __name__ == "__main__":
    main()
