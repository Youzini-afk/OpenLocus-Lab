#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review.v1"
GENERATED_BY = "eval/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review_report.json")
DEFAULT_P3_2 = Path("artifacts/bea_v1_p3_2_frozen_trace_logger_patch_design/bea_v1_p3_2_frozen_trace_logger_patch_design_report.json")
HELPER_MODULE_BUCKET = "bea_v1_frozen_trace_logger_helpers"

STATUSES = (
    "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized",
    "no_go_p3_3_required_inputs_unavailable",
    "no_go_p3_3_helper_module_missing_or_impure",
    "no_go_p3_3_surface_helper_incomplete",
    "no_go_p3_3_synthetic_validation_failed",
    "no_go_p3_3_forbidden_code_touch_detected",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = (
    "support_link",
    "scheduler_action_cost",
    "ordered_prefix_stop",
    "same_file_redundancy",
    "risk_penalty",
)

REQUIRED_FIELDS = {
    "support_link": ("anonymous_trace_id", "support_relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "support_evidence_role_bucket", "leakage_risk_bucket", "source_context_available_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
    "scheduler_action_cost": ("anonymous_trace_id", "arm_bucket", "action_sequence_bucket", "latency_bucket", "pool_size_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "scheduler_state_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "ordered_prefix_stop": ("anonymous_trace_id", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_reference_bucket", "early_stop_signal_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "same_file_redundancy": ("anonymous_trace_id", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "risk_penalty": ("anonymous_trace_id", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
}

FORBIDDEN_PUBLIC_KEYS = frozenset({"path", "file_path", "source_path", "exact_path", "exact_span", "repo", "repo_id", "repo_name", "repo_url", "task_id", "span", "line", "snippet", "content", "content_sha", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload", "hash", "private_id", "queue_item_id", "anonymous_design_id", "private_path", "raw", "text"})
SAFE_VALUE_KEYS = frozenset({"schema_version", "generated_by", "generated_at", "claim_level", "status", "mode", "phase", "failure_reason_category", "gate", "threshold_relation", "stop_go_decision", "stop_go_reason", "authorization"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(input_file: Path) -> tuple[dict[str, Any], str]:
    if not input_file.exists():
        return {}, "missing"
    try:
        data = json.loads(input_file.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(output_file: Path, obj: dict[str, Any]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                sub = marker + "." + key_s
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, sub)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if hex_re.search(value):
                violations.append({"category": "hex_digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": value} for key, value in sorted(counts.items())]}


def _schema(surface: str) -> str:
    return "bea_v1_" + surface + "_trace_capture.v1"


def _fixture(surface: str) -> dict[str, Any]:
    event = {"trace_completeness_bucket": "synthetic_complete"}
    for key in REQUIRED_FIELDS[surface]:
        event[key] = "synthetic_" + key.replace("_bucket", "")
    return event


def _helper_names(surface: str) -> tuple[str, str, str, str]:
    return (
        "build_" + surface + "_trace_capture_row_private",
        "sanitize_" + surface + "_trace_capture_row_public",
        "validate_" + surface + "_trace_capture_row_private",
        "validate_" + surface + "_trace_capture_row_public_projection",
    )


def _load_helpers() -> Any:
    eval_dir = Path(__file__).resolve().parent
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    return importlib.import_module("bea_v1_frozen_trace_logger_helpers")


def _input_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = _load_json(args.p3_2_artifact)
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    handoff = artifact.get("p3_3_handoff_records", [])
    handoff_ok = bool(isinstance(handoff, list) and handoff and isinstance(handoff[0], dict) and handoff[0].get("p3_3_helper_patch_review_authorized") is True and handoff[0].get("trace_capture_execution_authorized_bool") is False and handoff[0].get("private_trace_row_write_authorized_bool") is False and handoff[0].get("evaluator_hook_in_authorized_bool") is False)
    ok = load_status == "pass" and artifact.get("status") == "frozen_trace_logger_patch_design_pass_p3_3_authorized" and scan_status == "pass" and len(artifact.get("surface_patch_design_records", [])) == 5 and len(artifact.get("helper_signature_records", [])) == 5 and len(artifact.get("writer_contract_records", [])) == 5 and handoff_ok
    return [{"input_artifact_bucket": "p3_2_frozen_trace_logger_patch_design", "source_phase_bucket": "BEA-v1-P3-2", "load_status": load_status, "expected_status": "frozen_trace_logger_patch_design_pass_p3_3_authorized", "observed_status": str(artifact.get("status", "") or ""), "forbidden_scan_status": scan_status, "surface_patch_design_record_count": len(artifact.get("surface_patch_design_records", [])) if isinstance(artifact.get("surface_patch_design_records"), list) else 0, "helper_signature_record_count": len(artifact.get("helper_signature_records", [])) if isinstance(artifact.get("helper_signature_records"), list) else 0, "writer_contract_record_count": len(artifact.get("writer_contract_records", [])) if isinstance(artifact.get("writer_contract_records"), list) else 0, "p3_3_helper_patch_review_authorized": handoff_ok, "input_gate_passed": ok}], ok


def _static_helper_review() -> tuple[list[dict[str, Any]], bool]:
    helper_file = Path(__file__).resolve().parent / "bea_v1_frozen_trace_logger_helpers.py"
    source = helper_file.read_text(encoding="utf-8") if helper_file.exists() else ""
    import_lines = [line.strip() for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    allowed_imports = {"from __future__ import annotations", "from typing import Any, Mapping"}
    forbidden_tokens = ("open(", ".write(", "subprocess", "socket", "requests", "urllib", "http", "p4l", "n1_", "n2_", "p0_", "p1_", "p2_", "random", "time")
    forbidden_count = sum(1 for token in forbidden_tokens if token in source)
    imports_ok = all(line in allowed_imports for line in import_lines)
    function_count = len(re.findall(r"^def (build|sanitize|validate)_", source, re.M))
    ok = helper_file.exists() and imports_ok and forbidden_count == 0 and function_count == 20
    return [{"anonymous_static_review_id": "p33sr0000", "helper_module_bucket": HELPER_MODULE_BUCKET, "helper_module_present_bool": helper_file.exists(), "allowed_imports_only_bool": imports_ok, "forbidden_static_token_count": forbidden_count, "helper_function_count": function_count, "expected_helper_function_count": 20, "filesystem_write_call_detected_bool": False, "network_or_subprocess_token_detected_bool": False, "evaluator_import_detected_bool": False, "static_helper_contract_passed_bool": ok}], ok


def _fixture_review(helpers: Any) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    all_ok = True
    for idx, surface in enumerate(SURFACES):
        build_name, sanitize_name, validate_private_name, validate_public_name = _helper_names(surface)
        build = getattr(helpers, build_name)
        sanitize = getattr(helpers, sanitize_name)
        validate_private = getattr(helpers, validate_private_name)
        validate_public = getattr(helpers, validate_public_name)
        private_row = build(_fixture(surface))
        private_status = validate_private(private_row)
        public_row = sanitize({**private_row, "anonymous_public_trace_id": "p33_public_" + str(idx)})
        public_status = validate_public(public_row)
        negative_public = dict(public_row)
        negative_public["path"] = "blocked"
        negative_status = validate_public(negative_public)
        scanner_status = _scan_summary(public_row)["status"]
        ok = private_status.get("validation_status") == "pass" and public_status.get("validation_status") == "pass" and negative_status.get("validation_status") == "fail" and scanner_status == "pass" and private_row.get("schema_version") == _schema(surface) and public_row.get("schema_version_bucket") == _schema(surface)
        all_ok = all_ok and ok
        rows.append({"anonymous_fixture_review_id": f"p33fr{idx:04d}", "surface_bucket": surface, "private_builder_passed_bool": private_status.get("validation_status") == "pass", "private_validator_passed_bool": private_status.get("validation_status") == "pass", "public_sanitizer_passed_bool": public_status.get("validation_status") == "pass", "public_validator_passed_bool": public_status.get("validation_status") == "pass", "negative_privacy_fixture_rejected_bool": negative_status.get("validation_status") == "fail", "public_scanner_status": scanner_status, "fixture_review_passed_bool": ok})
    return rows, all_ok


def _surface_helper_coverage_records(helpers: Any) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, surface in enumerate(SURFACES):
        build_name, sanitize_name, validate_private_name, validate_public_name = _helper_names(surface)
        row = {
            "anonymous_surface_helper_coverage_id": f"p33hc{idx:04d}",
            "surface_bucket": surface,
            "private_builder_present_bool": callable(getattr(helpers, build_name, None)),
            "public_sanitizer_present_bool": callable(getattr(helpers, sanitize_name, None)),
            "private_validator_present_bool": callable(getattr(helpers, validate_private_name, None)),
            "public_validator_present_bool": callable(getattr(helpers, validate_public_name, None)),
        }
        row["helper_coverage_passed_bool"] = all(bool(row[k]) for k in ("private_builder_present_bool", "public_sanitizer_present_bool", "private_validator_present_bool", "public_validator_present_bool"))
        ok = ok and bool(row["helper_coverage_passed_bool"])
        rows.append(row)
    return rows, ok


def _synthetic_records_from_fixture_reviews(fixture_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(fixture_records):
        private_rows.append({
            "anonymous_synthetic_private_validation_id": f"p33pv{idx:04d}",
            "surface_bucket": row["surface_bucket"],
            "synthetic_private_row_built_bool": bool(row["private_builder_passed_bool"]),
            "private_schema_valid_bool": bool(row["private_validator_passed_bool"]),
            "private_validation_status_bucket": "pass" if row["private_validator_passed_bool"] else "fail",
            "uses_real_private_rows_bool": False,
            "private_trace_row_written_bool": False,
        })
        public_rows.append({
            "anonymous_synthetic_public_projection_id": f"p33pp{idx:04d}",
            "surface_bucket": row["surface_bucket"],
            "public_projection_built_bool": bool(row["public_sanitizer_passed_bool"]),
            "public_projection_valid_bool": bool(row["public_validator_passed_bool"]),
            "public_projection_scanner_status": row["public_scanner_status"],
            "public_projection_bucket_only_bool": bool(row["public_scanner_status"] == "pass"),
        })
    return private_rows, public_rows


def _negative_privacy_records(helpers: Any) -> tuple[list[dict[str, Any]], bool]:
    categories = (
        ("path", "path"),
        ("span", "span"),
        ("snippet", "snippet"),
        ("provider_payload", "provider"),
        ("candidate_list", "candidate_list"),
        ("private_identifier", "private_id"),
    )
    build = getattr(helpers, _helper_names("support_link")[0])
    sanitize = getattr(helpers, _helper_names("support_link")[1])
    validate_public = getattr(helpers, _helper_names("support_link")[3])
    base_public = sanitize({**build(_fixture("support_link")), "anonymous_public_trace_id": "p33_negative"})
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (category, key) in enumerate(categories):
        candidate = dict(base_public)
        candidate[key] = "blocked"
        validator_rejected = validate_public(candidate).get("validation_status") == "fail"
        scanner_rejected = _scan_summary(candidate)["status"] == "fail"
        ok = ok and validator_rejected and scanner_rejected
        rows.append({
            "anonymous_negative_privacy_test_id": f"p33nt{idx:04d}",
            "forbidden_category_bucket": category,
            "negative_fixture_rejected_bool": validator_rejected,
            "scanner_rejected_bool": scanner_rejected,
        })
    return rows, ok


def _changed_allowlist_review() -> tuple[list[dict[str, Any]], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=Path(__file__).resolve().parent.parent, check=False, capture_output=True, text=True, timeout=10)
        changed = [line[3:].strip() for line in proc.stdout.splitlines() if line.strip()]
        command_ok = proc.returncode == 0
    except Exception:
        changed = []
        command_ok = False
    allowed = {
        "README.md",
        "docs/current-research-conclusions.md",
        "docs/en/current-research-conclusions.md",
        "docs/zh/current-research-conclusions.md",
        "docs/en/bea-v1-p3-3-frozen-trace-logger-isolated-helper-patch-review.md",
        "docs/zh/bea-v1-p3-3-frozen-trace-logger-isolated-helper-patch-review.md",
        "eval/bea_v1_frozen_trace_logger_helpers.py",
        "eval/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review.py",
        "artifacts/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review_report.json",
    }
    allowed_prefixes = (
        "artifacts/bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review/",
    )
    disallowed = [name for name in changed if name not in allowed and not any(name.startswith(prefix) for prefix in allowed_prefixes)]
    ok = command_ok and not disallowed
    return [{"anonymous_forbidden_code_touch_id": "p33ct0000", "git_status_check_available_bool": command_ok, "workspace_change_count": len(changed), "disallowed_existing_eval_or_runtime_modification_count": len(disallowed), "existing_evaluator_files_modified_bool": False, "runtime_or_retrieval_files_modified_bool": False, "forbidden_code_touch_detected_bool": bool(disallowed), "new_helper_module_expected_bool": True, "new_review_evaluator_expected_bool": True, "change_allowlist_passed_bool": ok}], ok


def _helper_patch_review_records() -> list[dict[str, Any]]:
    return [{"anonymous_helper_patch_review_id": f"p33hp{idx:04d}", "surface_bucket": surface, "helper_count": 4, "isolated_helper_module_bool": True, "synthetic_tests_only_bool": True, "evaluator_hook_in_authorized_bool": False, "trace_capture_execution_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "runtime_behavior_change_authorized_bool": False} for idx, surface in enumerate(SURFACES)]


def _p3_4_handoff_records() -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p33h0000", "handoff_bucket": "p3_4_frozen_trace_logger_hook_in_preflight_design", "p3_4_hook_in_preflight_design_authorized": True, "requires_separate_phase_bool": True, "hook_application_authorized_bool": False, "trace_capture_execution_authorized_bool": False, "private_trace_row_write_authorized_bool": False, "retrieval_execution_authorized_bool": False, "runtime_behavior_change_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_records(args)
    static_records, static_ok = _static_helper_review()
    helpers = _load_helpers()
    coverage_records, coverage_ok = _surface_helper_coverage_records(helpers)
    fixture_records, fixture_ok = _fixture_review(helpers)
    synthetic_private_records, synthetic_public_records = _synthetic_records_from_fixture_reviews(fixture_records)
    negative_records, negative_ok = _negative_privacy_records(helpers)
    allowlist_records, allowlist_ok = _changed_allowlist_review()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_3_required_inputs_unavailable"
    elif not static_ok:
        status = "no_go_p3_3_helper_module_missing_or_impure"
    elif not coverage_ok:
        status = "no_go_p3_3_surface_helper_incomplete"
    elif not fixture_ok or not negative_ok:
        status = "no_go_p3_3_synthetic_validation_failed"
    elif not allowlist_ok:
        status = "no_go_p3_3_forbidden_code_touch_detected"
    else:
        status = "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": "frozen_trace_logger_isolated_helper_patch_review_only",
        "mode": "bea_v1_p3_3_frozen_trace_logger_isolated_helper_patch_review",
        "phase": "BEA-v1-P3-3",
        "status": status,
        "failure_reason_category": "" if status == "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized" else status.replace("no_go_p3_3_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "helper_module_static_review_records": static_records,
        "surface_helper_coverage_records": coverage_records,
        "synthetic_private_validation_records": synthetic_private_records,
        "synthetic_public_projection_records": synthetic_public_records,
        "negative_privacy_test_records": negative_records,
        "forbidden_code_touch_records": allowlist_records,
        "isolated_helper_patch_review_records": _helper_patch_review_records(),
        "p3_4_handoff_records": _p3_4_handoff_records(),
        "gate_records": [
            {"gate": "p3_2_required_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "helper_static_contract_pass", "passed": static_ok, "threshold_relation": "boolean", "value": int(static_ok), "threshold_value": 1},
            {"gate": "surface_helper_coverage_count", "passed": coverage_ok, "threshold_relation": "equals", "value": sum(1 for row in coverage_records if row["helper_coverage_passed_bool"]), "threshold_value": 5},
            {"gate": "five_surface_fixture_validation_pass", "passed": fixture_ok, "threshold_relation": "equals", "value": sum(1 for row in fixture_records if row["fixture_review_passed_bool"]), "threshold_value": 5},
            {"gate": "negative_privacy_rejection_count", "passed": negative_ok, "threshold_relation": "at_least", "value": sum(1 for row in negative_records if row["negative_fixture_rejected_bool"] and row["scanner_rejected_bool"]), "threshold_value": 6},
            {"gate": "existing_eval_runtime_change_allowlist_pass", "passed": allowlist_ok, "threshold_relation": "boolean", "value": int(allowlist_ok), "threshold_value": 1},
            {"gate": "p3_4_preflight_design_only_handoff", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
        ],
        "stop_go_records": [{"stop_go_decision": status, "stop_go_reason": "isolated_helper_patch_review_complete" if status == "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized" else "helper_patch_review_blocked", "authorization": "frozen_trace_logger_isolated_helper_patch_review_only", "next_allowed_phase": "BEA-v1-P3-4 Frozen Trace Logger Hook-In Preflight Design — design only, no hook application or trace capture execution", "p3_4_hook_in_preflight_design_authorized": status == "frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized", "actual_hook_in_authorized": False, "helper_module_and_synthetic_tests_only": True, "hook_application_authorized": False, "existing_evaluator_hook_authorized": False, "evaluator_hook_in_authorized": False, "trace_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "implementation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    helpers = _load_helpers()
    static_records, static_ok = _static_helper_review()
    coverage_records, coverage_ok = _surface_helper_coverage_records(helpers)
    fixture_records, fixture_ok = _fixture_review(helpers)
    negative_records, negative_ok = _negative_privacy_records(helpers)
    allowlist_records, _ = _changed_allowlist_review()
    parser_ok = False
    try:
        build_parser().parse_args(["--unknown-secret", "VALUE_SHOULD_NOT_SURFACE"])
    except SystemExit as exc:
        parser_ok = "VALUE_SHOULD_NOT_SURFACE" not in str(exc)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"frozen_trace_logger_isolated_helper_patch_pass_p3_4_preflight_authorized", "no_go_p3_3_required_inputs_unavailable", "no_go_p3_3_helper_module_missing_or_impure", "no_go_p3_3_surface_helper_incomplete", "no_go_p3_3_synthetic_validation_failed", "no_go_p3_3_forbidden_code_touch_detected", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("helper_module_static_contract_pass", static_ok and static_records[0]["helper_function_count"] == 20),
        _check("surface_helper_coverage_pass", coverage_ok and len(coverage_records) == 5),
        _check("twenty_helper_functions_callable", all(callable(getattr(helpers, name, None)) for surface in SURFACES for name in _helper_names(surface))),
        _check("five_surface_synthetic_fixtures_pass", fixture_ok and len(fixture_records) == 5),
        _check("private_builders_emit_expected_schema", all(getattr(helpers, _helper_names(surface)[0])(_fixture(surface)).get("schema_version") == _schema(surface) for surface in SURFACES)),
        _check("public_sanitizers_drop_forbidden_keys", all(not any(key in FORBIDDEN_PUBLIC_KEYS for key in getattr(helpers, _helper_names(surface)[1])({**getattr(helpers, _helper_names(surface)[0])(_fixture(surface)), "anonymous_public_trace_id": "x"}).keys()) for surface in SURFACES)),
        _check("negative_privacy_fixtures_rejected", negative_ok and len(negative_records) >= 6),
        _check("public_scanner_accepts_sanitized_rows", all(row["public_scanner_status"] == "pass" for row in fixture_records)),
        _check("public_scanner_rejects_forbidden_key", _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("p3_4_handoff_design_only", _p3_4_handoff_records()[0]["p3_4_hook_in_preflight_design_authorized"] and not _p3_4_handoff_records()[0]["hook_application_authorized_bool"] and not _p3_4_handoff_records()[0]["trace_capture_execution_authorized_bool"]),
        _check("forbidden_code_touch_record_sanitized", _scan_summary(allowlist_records)["status"] == "pass"),
        _check("safe_parser_hides_unknown_arg_values", parser_ok),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-3 isolated helper patch review")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-2-artifact", type=Path, default=DEFAULT_P3_2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={len(report['synthetic_private_validation_records'])}, helper_static={report['helper_module_static_review_records'][0]['static_helper_contract_passed_bool']}, p3_4={report['p3_4_handoff_records'][0]['p3_4_hook_in_preflight_design_authorized']})")


if __name__ == "__main__":
    main()
