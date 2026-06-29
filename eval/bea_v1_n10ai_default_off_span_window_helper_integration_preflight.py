#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ai_default_off_span_window_helper_integration_preflight.v1"
PHASE = "BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight"
STATUS_PASS = "default_off_span_window_helper_integration_preflight_pass_n10aj_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ai_required_inputs_unavailable",
    "no_go_n10ai_no_safe_eval_only_hook_point",
    "no_go_n10ai_default_off_boundary_incomplete",
    "no_go_n10ai_behavior_preservation_risk",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json")
INPUTS = {
    "n10ah_helper_smoke_artifact": (Path("artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json"), "default_off_span_window_helper_implementation_smoke_pass_n10ai_authorized"),
    "n10ag_claim_boundary_package_artifact": (Path("artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json"), "fixed_span_window_repair_claim_boundary_package_complete_n10ah_authorized"),
}
ALLOWED_CHANGED = {
    "eval/bea_v1_n10ai_default_off_span_window_helper_integration_preflight.py",
    "artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/",
    "artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json",
    "docs/en/bea-v1-n10ai-default-off-span-window-helper-integration-preflight.md",
    "docs/zh/bea-v1-n10ai-default-off-span-window-helper-integration-preflight.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "helper_function_bucket", "contract_bucket", "hook_candidate_bucket", "hook_target_bucket", "static_signal_bucket",
    "default_off_interface_bucket", "behavior_risk_bucket", "changed_file_bucket", "privacy_boundary_bucket",
    "no_execution_boundary_bucket", "n10aj_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10aiin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


def helper_contract_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ah = artifacts.get("n10ah_helper_smoke_artifact", {})
    helper_rows = n10ah.get("helper_contract_records", [])
    default = (n10ah.get("default_off_records") or [{}])[0]
    noio = (n10ah.get("no_io_private_records") or [{}])[0]
    ok = len(helper_rows) == 2 and all(isinstance(r, dict) and r.get("contract_valid_bool") is True for r in helper_rows) and default.get("hook_in_to_existing_evaluators_bool") is False and default.get("runtime_default_config_changed_bool") is False and noio.get("filesystem_io_in_helper_bool") is False
    records = []
    for idx, row in enumerate(helper_rows if isinstance(helper_rows, list) else []):
        if isinstance(row, dict):
            records.append({"anonymous_helper_contract_id": f"n10aicontract{idx:04d}", "helper_function_bucket": str(row.get("helper_function_bucket", "")), "contract_bucket": str(row.get("contract_bucket", "")), "contract_valid_bool": bool(row.get("contract_valid_bool", False)), "gold_input_required_bool": bool(row.get("gold_input_required_bool", True)), "filesystem_io_bool": bool(row.get("filesystem_io_bool", True))})
    return records, ok


def static_signal_count(file_name: str, needles: tuple[str, ...]) -> int:
    text = (root() / "eval" / file_name).read_text(encoding="utf-8")
    return sum(1 for needle in needles if needle in text)


def candidate_hook_point_records() -> tuple[list[dict[str, Any]], bool]:
    n10ab_signal = static_signal_count("bea_v1_n10ab_fixed_span_window_repair_smoke.py", ("span_hit_topk", "expanded_start", "expanded_end"))
    n10x_signal = static_signal_count("bea_v1_n10x_n1_span_surface_span_level_utility_validation.py", ("first_hit", "span_level", "order_for"))
    n10t_signal = static_signal_count("bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.py", ("order_for", "first_hit", "span_extra_depth_promote_before_primary_prefix_4"))
    records = [
        {"anonymous_candidate_hook_point_id": "n10aihook0000", "hook_candidate_bucket": "n10ab_smoke_evaluator_expansion_loop", "static_signal_bucket": "existing_eval_smoke_loop_detected", "eval_only_bool": True, "existing_runtime_path_bool": False, "default_off_possible_bool": True, "behavior_risk_bucket": "medium_existing_evaluator_modification_risk", "recommended_hook_target_bool": False, "static_signal_count": n10ab_signal},
        {"anonymous_candidate_hook_point_id": "n10aihook0001", "hook_candidate_bucket": "n10x_span_overlap_evaluation_loop", "static_signal_bucket": "existing_eval_validation_loop_detected", "eval_only_bool": True, "existing_runtime_path_bool": False, "default_off_possible_bool": True, "behavior_risk_bucket": "medium_existing_evaluator_modification_risk", "recommended_hook_target_bool": False, "static_signal_count": n10x_signal},
        {"anonymous_candidate_hook_point_id": "n10aihook0002", "hook_candidate_bucket": "future_eval_only_span_projection_adapter", "static_signal_bucket": "new_eval_only_adapter_target_no_existing_hook_patch", "eval_only_bool": True, "existing_runtime_path_bool": False, "default_off_possible_bool": True, "behavior_risk_bucket": "low", "recommended_hook_target_bool": True, "static_signal_count": n10t_signal},
    ]
    ok = any(r["eval_only_bool"] and r["default_off_possible_bool"] for r in records) and records[2]["recommended_hook_target_bool"] and records[2]["hook_candidate_bucket"] == "future_eval_only_span_projection_adapter" and records[2]["existing_runtime_path_bool"] is False
    return records, ok


def default_off_interface_records() -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_default_off_interface_id": "n10aiiface0000", "default_off_interface_bucket": "adapter_call_requires_explicit_eval_flag_and_fixed_window", "hook_target_bucket": "future_eval_only_span_projection_adapter", "default_off_interface_defined_bool": True, "default_enabled_bool": False, "existing_evaluator_hook_in_bool": False, "runtime_config_change_bool": False, "private_read_default_bool": False, "fixed_window_only_bool": True, "gold_policy_input_bool": False, "adaptive_tuning_bool": False}]
    return records, True


def behavior_preservation_records(hook_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    records = [{"anonymous_behavior_preservation_id": "n10aibehavior0000", "hook_target_bucket": "future_eval_only_span_projection_adapter", "behavior_risk_bucket": "low", "existing_evaluator_modification_bool": False, "runtime_path_modification_bool": False, "retrieval_behavior_change_bool": False, "candidate_generation_behavior_change_bool": False, "selector_reranker_behavior_change_bool": False, "behavior_preservation_valid_bool": hook_ok}]
    return records, hook_ok


def changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    files = []
    for line in result.stdout.splitlines():
        if line.strip():
            files.append(line[3:].strip())
    return files


def changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    files = changed_files()
    invalid = sorted(set(files) - ALLOWED_CHANGED)
    records = []
    for idx, file_name in enumerate(files):
        safe = re.sub(r"[^A-Za-z0-9]+", "_", file_name).strip("_") or "none"
        records.append({"anonymous_changed_file_allowlist_id": f"n10aichange{idx:04d}", "changed_file_bucket": safe, "allowed_bool": file_name in ALLOWED_CHANGED})
    if not records:
        records.append({"anonymous_changed_file_allowlist_id": "n10aichange0000", "changed_file_bucket": "none", "allowed_bool": True})
    return records, not invalid


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aiprivacy0000", "privacy_boundary_bucket": "public_static_preflight_no_private_data", "private_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10ainoexec0000", "no_execution_boundary_bucket": "static_integration_preflight_only_no_hook_patch", "private_read_count": 0, "hook_patch_count": 0, "runtime_config_change_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_execution_valid_bool": True}], True


def n10aj_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10aj_handoff_id": "n10aihandoff0000", "n10aj_handoff_bucket": "n10aj_default_off_eval_only_span_projection_adapter_patch_authorized" if complete else "n10aj_not_authorized", "n10aj_patch_authorized_bool": complete, "patch_scope_bucket": "new_eval_only_adapter_only" if complete else "none", "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "private_read_by_default_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, helper_ok: bool, hook_ok: bool, interface_ok: bool, behavior_ok: bool, touch_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("n10ah_status", input_ok, int(input_ok), 1), ("helper_pure", helper_ok, int(helper_ok), 1), ("eval_only_hook_point", hook_ok, int(hook_ok), 1), ("recommended_future_adapter", hook_ok, int(hook_ok), 1), ("default_off_interface", interface_ok, int(interface_ok), 1), ("behavior_risk_not_high", behavior_ok, int(behavior_ok), 1), ("changed_file_allowlist", touch_ok, int(touch_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10aj_default_off_eval_only_span_projection_adapter_patch_authorized" if complete else "n10aj_not_authorized", "next_allowed_phase": "BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch" if complete else "none_until_safe_eval_only_hook_point_exists", "next_allowed_scope_bucket": "new_eval_only_adapter_patch_no_runtime_default" if complete else "no_next_phase", "n10aj_patch_authorized": complete, "existing_evaluator_hook_in_authorized": False, "runtime_or_default_enablement_authorized": False, "private_read_by_default_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, helper_ok: bool, hook_ok: bool, interface_ok: bool, behavior_ok: bool, touch_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ai_required_inputs_unavailable"
    if not hook_ok:
        return "no_go_n10ai_no_safe_eval_only_hook_point"
    if not helper_ok or not interface_ok:
        return "no_go_n10ai_default_off_boundary_incomplete"
    if not behavior_ok:
        return "no_go_n10ai_behavior_preservation_risk"
    if not touch_ok:
        return "no_go_n10ai_behavior_preservation_risk"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    helper_records, helper_ok = helper_contract_records(artifacts)
    hook_records, hook_ok = candidate_hook_point_records()
    interface_records, interface_ok = default_off_interface_records()
    behavior_records, behavior_ok = behavior_preservation_records(hook_ok)
    change_records, touch_ok = changed_file_allowlist_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, helper_ok, hook_ok, interface_ok, behavior_ok, touch_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "static_integration_preflight_only", "generated_by": "bea_v1_n10ai_default_off_span_window_helper_integration_preflight", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "helper_contract_records": helper_records, "candidate_hook_point_records": hook_records, "default_off_interface_records": interface_records, "behavior_preservation_records": behavior_records, "changed_file_allowlist_records": change_records, "privacy_boundary_records": privacy_records, "no_execution_records": noexec_records, "n10aj_handoff_records": n10aj_handoff_records(complete), "gate_records": gate_records(input_ok, helper_ok, hook_ok, interface_ok, behavior_ok, touch_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, helper_ok, hook_ok, interface_ok, behavior_ok, touch_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10aj_handoff_records"] = n10aj_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, artifacts, input_ok = input_artifact_records()
    helper_records, helper_ok = helper_contract_records(artifacts)
    hook_records, hook_ok = candidate_hook_point_records()
    interface_records, interface_ok = default_off_interface_records()
    behavior_records, behavior_ok = behavior_preservation_records(hook_ok)
    change_records, touch_ok = changed_file_allowlist_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_execution_records()
    recommended = next(r for r in hook_records if r["recommended_hook_target_bool"])
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ai_required_inputs_unavailable", "no_go_n10ai_no_safe_eval_only_hook_point", "no_go_n10ai_default_off_boundary_incomplete", "no_go_n10ai_behavior_preservation_risk", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 2),
        check("helper_contract", helper_ok and len(helper_records) == 2),
        check("hook_points", hook_ok and len(hook_records) == 3),
        check("recommended_target", recommended["hook_candidate_bucket"] == "future_eval_only_span_projection_adapter" and recommended["existing_runtime_path_bool"] is False and recommended["behavior_risk_bucket"] == "low"),
        check("default_off_interface", interface_ok and interface_records[0]["default_enabled_bool"] is False and interface_records[0]["existing_evaluator_hook_in_bool"] is False),
        check("behavior_preservation", behavior_ok and behavior_records[0]["behavior_risk_bucket"] != "high" and behavior_records[0]["existing_evaluator_modification_bool"] is False),
        check("changed_files", touch_ok and all(r["allowed_bool"] for r in change_records)),
        check("privacy", privacy_ok and privacy_records[0]["private_read_count"] == 0),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec_records[0].items() if k.endswith("_count"))),
        check("handoff", n10aj_handoff_records(True)[0]["n10aj_patch_authorized_bool"] is True and stop_go_records(True)[0]["runtime_or_default_enablement_authorized"] is False),
        check("status_expected", status_for(True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AI default-off helper integration preflight")
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
    rec = next(r for r in report["candidate_hook_point_records"] if r["recommended_hook_target_bool"])
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, target={rec['hook_candidate_bucket']})")


if __name__ == "__main__":
    main()
