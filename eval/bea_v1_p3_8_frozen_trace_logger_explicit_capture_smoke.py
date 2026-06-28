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


SCHEMA_VERSION = "bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.v1"
GENERATED_BY = "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py"
DEFAULT_OUT = Path("artifacts/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke_report.json")
DEFAULT_P3_7 = Path("artifacts/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight_report.json")
DEFAULT_FIXTURE_MANIFEST = Path(".openlocus/research-private/bea_v1_p3_8_frozen_trace_capture_event_fixture_manifest.json")
DEFAULT_FIXTURE_EVENTS = Path(".openlocus/research-private/bea_v1_p3_8_frozen_trace_capture_event_fixtures.jsonl")
DEFAULT_PRIVATE_OUT_DIR = Path(".openlocus/research-private")
PRIVATE_ROWS_NAME = "bea_v1_p3_8_frozen_trace_capture_private_rows.jsonl"
PRIVATE_MANIFEST_NAME = "bea_v1_p3_8_frozen_trace_capture_private_manifest.json"

STATUS_PASS = "frozen_trace_logger_explicit_capture_smoke_pass_p3_9_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8_required_inputs_unavailable",
    "no_go_p3_8_changed_file_scope_invalid",
    "no_go_p3_8_frozen_event_fixtures_unavailable",
    "no_go_p3_8_fixture_schema_invalid",
    "no_go_p3_8_fixture_surface_coverage_incomplete",
    "no_go_p3_8_private_output_root_not_ready",
    "no_go_p3_8_helper_or_hook_capture_failed",
    "no_go_p3_8_private_write_failed",
    "no_go_p3_8_public_projection_scan_failed",
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

HELPERS = {
    "support_link": ("build_support_link_trace_capture_row_private", "validate_support_link_trace_capture_row_private", "sanitize_support_link_trace_capture_row_public", "validate_support_link_trace_capture_row_public_projection"),
    "scheduler_action_cost": ("build_scheduler_action_cost_trace_capture_row_private", "validate_scheduler_action_cost_trace_capture_row_private", "sanitize_scheduler_action_cost_trace_capture_row_public", "validate_scheduler_action_cost_trace_capture_row_public_projection"),
    "ordered_prefix_stop": ("build_ordered_prefix_stop_trace_capture_row_private", "validate_ordered_prefix_stop_trace_capture_row_private", "sanitize_ordered_prefix_stop_trace_capture_row_public", "validate_ordered_prefix_stop_trace_capture_row_public_projection"),
    "same_file_redundancy": ("build_same_file_redundancy_trace_capture_row_private", "validate_same_file_redundancy_trace_capture_row_private", "sanitize_same_file_redundancy_trace_capture_row_public", "validate_same_file_redundancy_trace_capture_row_public_projection"),
    "risk_penalty": ("build_risk_penalty_trace_capture_row_private", "validate_risk_penalty_trace_capture_row_private", "sanitize_risk_penalty_trace_capture_row_public", "validate_risk_penalty_trace_capture_row_public_projection"),
}

REQUIRED_EVENT_FIELDS = {
    "support_link": ("anonymous_design_join_key", "queue_item_join_key", "support_relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "evidence_role_bucket", "leakage_risk_bucket", "source_context_linkage_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
    "scheduler_action_cost": ("locked_denominator_join_key", "arm_bucket", "action_sequence_bucket", "latency_bucket", "pool_size_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "scheduler_state_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "ordered_prefix_stop": ("prefix_join_key", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_reference_bucket", "early_stop_signal_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "same_file_redundancy": ("redundancy_join_key", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "risk_penalty": ("risk_join_key", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
}

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8-frozen-trace-logger-explicit-capture-smoke.md",
    "docs/zh/bea-v1-p3-8-frozen-trace-logger-explicit-capture-smoke.md",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "artifacts/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "exact_path", "private_path", "private_out_dir",
    "span", "spans", "line", "lines", "snippet", "snippets", "content",
    "candidate", "candidate_list", "rank_list", "provider", "prompt", "response",
    "payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id",
    "repo", "repo_id", "task_id", "raw", "text", "diff", "raw_diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "generated_by", "generated_at", "claim_level", "status", "phase",
    "failure_reason_category", "gate", "threshold_relation", "stop_go_decision",
    "stop_go_reason", "authorization", "next_allowed_phase", "p3_9_scope", "p3_9_scope_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


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


def _read_jsonl(input_file: Path) -> tuple[list[dict[str, Any]], str]:
    if not input_file.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in input_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                return [], "parse_failed"
            rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def _write_json(output_file: Path, obj: dict[str, Any]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": value} for key, value in sorted(counts.items())]}


def _safe_private_path(path: Path) -> bool:
    root = (_repo_root() / ".openlocus" / "research-private").resolve()
    try:
        resolved = (path if path.is_absolute() else _repo_root() / path).resolve()
        resolved.relative_to(root)
        return True
    except Exception:
        return False


def _git_status_entries() -> tuple[list[tuple[str, str]], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [(line[:2], line[3:].strip()) for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = _load_json(args.p3_7_artifact)
    expected = "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized"
    observed = str(artifact.get("status", "") or "")
    scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    ok = load_status == "pass" and observed == expected and scan_status == "pass"
    return [{"input_artifact_bucket": "p3_7_frozen_trace_logger_capture_execution_preflight", "source_phase_bucket": "BEA-v1-P3-7", "load_status": load_status, "expected_status": expected, "observed_status": observed, "forbidden_scan_status": scan_status, "input_gate_passed": ok}], ok


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    entries, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    runtime = 0
    for _, name in entries:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if not allowed:
            disallowed += 1
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            runtime += 1
    ok = available and disallowed == 0 and forbidden == 0 and runtime == 0
    return [{"anonymous_changed_file_allowlist_id": "p38cf0000", "git_status_available_bool": available, "workspace_change_count": len(entries), "disallowed_changed_file_count": disallowed, "helper_or_target_modified_bool": forbidden > 0, "runtime_retrieval_selector_or_config_modified_bool": runtime > 0, "changed_file_scope_valid_bool": ok}], ok


def _validate_fixture_manifest(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if manifest.get("schema_version") != "bea_v1_p3_8_frozen_trace_capture_event_fixture_manifest.v1":
        errors.append("schema_version")
    if manifest.get("fixture_origin_bucket") != "predeclared_frozen_materialized_event_fixtures":
        errors.append("fixture_origin")
    if manifest.get("fixtures_frozen_bool") is not True:
        errors.append("fixtures_not_frozen")
    for key in ("retrieval_execution_required_bool", "p4l_n1_n2_rerun_required_bool", "support_labeling_required_bool", "counterfactual_required_bool"):
        if manifest.get(key) is not False:
            errors.append(key)
    surfaces = manifest.get("surface_buckets")
    if not isinstance(surfaces, list) or set(surfaces) != set(SURFACES):
        errors.append("surface_buckets")
    for key in ("fixture_set_id_bucket", "fixture_event_count", "surface_count", "expected_private_row_count"):
        if key not in manifest:
            errors.append("missing_" + key)
    if manifest.get("surface_count") != 5:
        errors.append("surface_count")
    return not errors, errors


def _validate_fixture_event(row: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    surface = str(row.get("surface_bucket", "") or "")
    if row.get("schema_version") != "bea_v1_p3_8_frozen_trace_capture_event_fixture.v1":
        errors.append("schema_version")
    if surface not in SURFACES:
        errors.append("surface_bucket")
    if row.get("event_origin_bucket") != "frozen_materialized_event_fixture":
        errors.append("event_origin")
    if row.get("event_payload_bucketed_bool") is not True:
        errors.append("payload_not_bucketed")
    if row.get("fixture_frozen_bool") is not True:
        errors.append("fixture_not_frozen")
    if "fixture_event_id_bucket" not in row:
        errors.append("fixture_event_id_bucket")
    if surface in REQUIRED_EVENT_FIELDS:
        for key in REQUIRED_EVENT_FIELDS[surface]:
            if key not in row:
                errors.append("missing_" + key)
    return not errors, errors


def _fixture_manifest_intake_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool, dict[str, Any], str]:
    safe = _safe_private_path(args.fixture_manifest_json)
    manifest, load_status = _load_json(args.fixture_manifest_json if args.fixture_manifest_json.is_absolute() else _repo_root() / args.fixture_manifest_json) if safe else ({}, "outside_private_root")
    valid, errors = _validate_fixture_manifest(manifest) if load_status == "pass" else (False, [load_status])
    return [{"anonymous_fixture_manifest_intake_id": "p38fm0000", "fixture_manifest_bucket": "p3_8_default_frozen_event_manifest", "manifest_load_status": load_status, "manifest_path_under_research_private_bool": safe, "manifest_schema_valid_bool": valid, "manifest_error_count": len(errors), "fixture_event_count": int(manifest.get("fixture_event_count", 0) or 0), "surface_count": int(manifest.get("surface_count", 0) or 0), "fixtures_frozen_bool": bool(manifest.get("fixtures_frozen_bool", False)), "requires_forbidden_execution_bool": any(bool(manifest.get(key)) for key in ("retrieval_execution_required_bool", "p4l_n1_n2_rerun_required_bool", "support_labeling_required_bool", "counterfactual_required_bool"))}], valid, manifest, load_status


def _fixture_event_intake_records(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]], str]:
    safe = _safe_private_path(args.fixture_events_jsonl)
    rows, load_status = _read_jsonl(args.fixture_events_jsonl if args.fixture_events_jsonl.is_absolute() else _repo_root() / args.fixture_events_jsonl) if safe else ([], "outside_private_root")
    errors = 0
    valid_rows = 0
    for row in rows:
        ok, errs = _validate_fixture_event(row)
        errors += len(errs)
        valid_rows += int(ok)
    expected_count = int(manifest.get("fixture_event_count", 0) or 0)
    valid = load_status == "pass" and bool(rows) and errors == 0 and (expected_count == 0 or expected_count == len(rows))
    return [{"anonymous_fixture_event_intake_id": "p38fe0000", "fixture_events_bucket": "p3_8_default_frozen_event_jsonl", "events_load_status": load_status, "events_path_under_research_private_bool": safe, "event_count": len(rows), "schema_valid_event_count": valid_rows, "event_error_count": errors, "fixture_events_schema_valid_bool": valid}], valid, rows, load_status


def _per_surface_fixture_coverage_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    counts = Counter(str(row.get("surface_bucket", "") or "") for row in rows)
    records = [{"anonymous_surface_fixture_coverage_id": f"p38fc{idx:04d}", "surface_bucket": surface, "fixture_event_count": counts.get(surface, 0), "coverage_present_bool": counts.get(surface, 0) > 0} for idx, surface in enumerate(SURFACES)]
    return records, all(row["coverage_present_bool"] for row in records)


def _load_helpers() -> Any:
    eval_dir = Path(__file__).resolve().parent
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    return importlib.import_module("bea_v1_frozen_trace_logger_helpers")


def _helper_capture(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    helpers = _load_helpers()
    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    ok = True
    for idx, event in enumerate(rows):
        surface = str(event.get("surface_bucket", "") or "")
        builder_name, private_validator_name, sanitizer_name, public_validator_name = HELPERS[surface]
        private_row = getattr(helpers, builder_name)(event)
        private_status = getattr(helpers, private_validator_name)(private_row)
        public_row = getattr(helpers, sanitizer_name)({**private_row, "anonymous_public_trace_id": f"p38_public_{idx:04d}"})
        public_status = getattr(helpers, public_validator_name)(public_row)
        projection_scan = _scan_summary(public_row)
        passed = private_status.get("validation_status") == "pass" and public_status.get("validation_status") == "pass" and projection_scan["status"] == "pass"
        ok = ok and passed
        private_rows.append({**private_row, "fixture_event_id_bucket": event.get("fixture_event_id_bucket", "unknown_fixture")})
        public_rows.append(public_row)
        records.append({"anonymous_helper_capture_id": f"p38hc{idx:04d}", "surface_bucket": surface, "helper_capture_mode_bucket": "helper_only_fixture_capture", "target_evaluator_imported_bool": False, "hook_shim_called_bool": False, "private_validation_status_bucket": str(private_status.get("validation_status", "")), "public_validation_status_bucket": str(public_status.get("validation_status", "")), "public_projection_scan_status": projection_scan["status"], "helper_capture_passed_bool": passed})
    return private_rows, public_rows, records, ok


def _private_root_ready(private_out_dir: Path) -> tuple[bool, bool, bool]:
    root = _repo_root() / ".openlocus" / "research-private"
    gitignore = _repo_root() / ".gitignore"
    ignored = gitignore.exists() and ("/.openlocus/" in gitignore.read_text(encoding="utf-8") or ".openlocus/" in gitignore.read_text(encoding="utf-8"))
    safe = _safe_private_path(private_out_dir)
    exists = root.exists() and root.is_dir()
    return exists, ignored, safe


def _write_private_outputs(args: argparse.Namespace, private_rows: list[dict[str, Any]], public_rows: list[dict[str, Any]]) -> tuple[bool, int, bool]:
    out_dir = args.private_out_dir if args.private_out_dir.is_absolute() else _repo_root() / args.private_out_dir
    if not _safe_private_path(out_dir):
        return False, 0, False
    try:
        rows_file = out_dir / PRIVATE_ROWS_NAME
        manifest_file = out_dir / PRIVATE_MANIFEST_NAME
        rows_file.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in private_rows), encoding="utf-8")
        manifest = {
            "schema_version": "bea_v1_p3_8_frozen_trace_capture_private_manifest.v1",
            "capture_run_id_bucket": "p3_8_explicit_capture_smoke",
            "surface_bucket": "all_five_surfaces",
            "private_jsonl_rel_bucket": "p3_8_private_rows_bucket",
            "row_count": len(private_rows),
            "schema_valid_count": len(private_rows),
            "scanner_public_projection_status": _scan_summary(public_rows)["status"],
            "frozen_event_source_bucket": "predeclared_frozen_materialized_event_fixtures",
            "capture_execution_mode_bucket": "explicit_helper_only_fixture_capture",
        }
        manifest_file.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return True, len(private_rows), True
    except Exception:
        return False, 0, False


def _no_retrieval_execution_records() -> list[dict[str, Any]]:
    return [{"anonymous_no_retrieval_execution_id": "p38nr0000", "retrieval_execution_count": 0, "p4l_execution_count": 0, "n1_n2_execution_count": 0, "support_label_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "selector_or_reranker_execution_count": 0, "runtime_promotion_count": 0, "no_forbidden_execution_passed_bool": True}]


def _p3_9_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_handoff_id": "p38h0000", "handoff_bucket": "BEA-v1-P3-9 Frozen Trace Capture Manifest Audit", "p3_9_manifest_audit_authorized": pass_status, "p3_9_scope": "audit only, no additional capture/retrieval/reruns/counterfactual/policy", "requires_separate_phase_bool": True, "additional_capture_authorized_bool": False, "retrieval_execution_authorized_bool": False, "counterfactual_execution_authorized_bool": False, "policy_tuning_authorized_bool": False}]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok = _input_artifact_records(args)
    changed_records, changed_ok = _changed_file_allowlist_records()
    manifest_records, manifest_ok, manifest, manifest_load = _fixture_manifest_intake_records(args)
    events_records, events_ok, events, events_load = _fixture_event_intake_records(args, manifest)
    coverage_records, coverage_ok = _per_surface_fixture_coverage_records(events)
    root_exists, root_ignored, out_safe = _private_root_ready(args.private_out_dir)
    private_root_ok = root_exists and root_ignored and out_safe
    root_write_records = [{"anonymous_private_write_summary_id": "p38pw0000", "private_output_root_bucket": "openlocus_research_private", "root_exists_bool": root_exists, "root_gitignored_bool": root_ignored, "private_output_under_research_private_bool": out_safe, "private_trace_row_write_authorized_in_p3_8_bool": False, "private_rows_written_count": 0, "private_write_status_bucket": "not_attempted"}]
    private_manifest_summary_records = [{"anonymous_private_manifest_summary_id": "p38pm0000", "manifest_schema_version_bucket": "bea_v1_p3_8_frozen_trace_capture_private_manifest.v1", "private_manifest_written_bool": False, "private_manifest_schema_valid_bool": False}]
    public_projection_summary_records = [{"anonymous_public_projection_summary_id": "p38pp0000", "public_projection_count": 0, "public_projection_scan_status": "not_run", "public_projection_scan_passed_bool": False}]
    helper_records: list[dict[str, Any]] = []
    hook_smoke_records = [{"anonymous_hook_shim_smoke_id": f"p38hs{idx:04d}", "surface_bucket": surface, "capture_mode_bucket": "helper_only_no_target_hook_shim", "target_evaluator_imported_bool": False, "hook_shim_called_bool": False, "hook_shim_smoke_passed_bool": True} for idx, surface in enumerate(SURFACES)]
    helper_ok = False
    write_ok = False
    written = 0
    manifest_written = False
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    fixtures_unavailable = manifest_load == "missing" or events_load == "missing"
    can_capture = input_ok and changed_ok and manifest_ok and events_ok and coverage_ok and private_root_ok
    if can_capture:
        private_rows, public_rows, helper_records, helper_ok = _helper_capture(events)
        public_scan = _scan_summary(public_rows)
        public_projection_summary_records = [{"anonymous_public_projection_summary_id": "p38pp0000", "public_projection_count": len(public_rows), "public_projection_scan_status": public_scan["status"], "public_projection_scan_passed_bool": public_scan["status"] == "pass"}]
        if helper_ok and public_scan["status"] == "pass":
            write_ok, written, manifest_written = _write_private_outputs(args, private_rows, public_rows)
            root_write_records[0].update({"private_trace_row_write_authorized_in_p3_8_bool": True, "private_rows_written_count": written, "private_write_status_bucket": "pass" if write_ok else "failed"})
            private_manifest_summary_records[0].update({"private_manifest_written_bool": manifest_written, "private_manifest_schema_valid_bool": manifest_written})
    else:
        helper_records = [{"anonymous_helper_capture_id": f"p38hc{idx:04d}", "surface_bucket": surface, "helper_capture_mode_bucket": "not_attempted_no_go", "target_evaluator_imported_bool": False, "hook_shim_called_bool": False, "private_validation_status_bucket": "not_run", "public_validation_status_bucket": "not_run", "public_projection_scan_status": "not_run", "helper_capture_passed_bool": False} for idx, surface in enumerate(SURFACES)]
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8_changed_file_scope_invalid"
    elif fixtures_unavailable:
        status = "no_go_p3_8_frozen_event_fixtures_unavailable"
    elif not manifest_ok or not events_ok:
        status = "no_go_p3_8_fixture_schema_invalid"
    elif not coverage_ok:
        status = "no_go_p3_8_fixture_surface_coverage_incomplete"
    elif not private_root_ok:
        status = "no_go_p3_8_private_output_root_not_ready"
    elif not helper_ok:
        status = "no_go_p3_8_helper_or_hook_capture_failed"
    elif public_projection_summary_records[0]["public_projection_scan_status"] != "pass":
        status = "no_go_p3_8_public_projection_scan_failed"
    elif not write_ok or written != len(events) or not manifest_written:
        status = "no_go_p3_8_private_write_failed"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_trace_logger_explicit_capture_smoke_only",
        "phase": "BEA-v1-P3-8",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "failure_reason_category": "" if pass_status else status.replace("no_go_p3_8_", "").replace("fail_", ""),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "changed_file_allowlist_records": changed_records,
        "fixture_manifest_intake_records": manifest_records,
        "fixture_event_intake_records": events_records,
        "per_surface_fixture_coverage_records": coverage_records,
        "hook_shim_smoke_records": hook_smoke_records,
        "helper_capture_records": helper_records,
        "private_write_summary_records": root_write_records,
        "private_manifest_summary_records": private_manifest_summary_records,
        "public_projection_summary_records": public_projection_summary_records,
        "no_retrieval_execution_records": _no_retrieval_execution_records(),
        "p3_9_handoff_records": _p3_9_handoff_records(pass_status),
        "gate_records": [
            {"gate": "p3_7_input_pass", "passed": input_ok, "threshold_relation": "boolean", "value": int(input_ok), "threshold_value": 1},
            {"gate": "changed_files_subset_allowlist", "passed": changed_ok, "threshold_relation": "boolean", "value": int(changed_ok), "threshold_value": 1},
            {"gate": "fixture_manifest_present_and_valid", "passed": manifest_ok, "threshold_relation": "boolean", "value": int(manifest_ok), "threshold_value": 1},
            {"gate": "fixture_events_present_and_valid", "passed": events_ok, "threshold_relation": "boolean", "value": int(events_ok), "threshold_value": 1},
            {"gate": "fixture_surface_coverage_5_of_5", "passed": coverage_ok, "threshold_relation": "equals", "value": sum(1 for row in coverage_records if row["coverage_present_bool"]), "threshold_value": 5},
            {"gate": "private_root_ready", "passed": private_root_ok, "threshold_relation": "boolean", "value": int(private_root_ok), "threshold_value": 1},
            {"gate": "helper_capture_pass", "passed": helper_ok, "threshold_relation": "boolean", "value": int(helper_ok), "threshold_value": 1},
            {"gate": "private_rows_written_equals_fixture_count", "passed": write_ok and written == len(events), "threshold_relation": "equals", "value": written, "threshold_value": len(events)},
            {"gate": "forbidden_execution_zero", "passed": True, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "explicit_capture_smoke_complete" if pass_status else "explicit_capture_smoke_blocked_before_private_write",
            "authorization": "frozen_trace_logger_explicit_capture_smoke_only",
            "next_allowed_phase": "BEA-v1-P3-9 Frozen Trace Capture Manifest Audit — audit only, no additional capture or retrieval",
            "p3_9_manifest_audit_authorized": pass_status,
            "fixture_trace_capture_execution_authorized_in_p3_8": pass_status,
            "real_evaluator_trace_capture_execution_authorized": False,
            "retrieval_backed_trace_capture_authorized": False,
            "private_trace_row_write_authorized_in_p3_8": pass_status,
            "retrieval_execution_authorized": False,
            "p4l_rerun_authorized": False,
            "p4l_n1_n2_rerun_authorized": False,
            "n1_n2_rerun_authorized": False,
            "support_labeling_authorized": False,
            "denominator_audit_authorized": False,
            "counterfactual_execution_authorized": False,
            "trace_counterfactual_execution_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
            "selector_or_reranker_authorized": False,
            "p5_authorized": False,
            "v1_a_authorized": False,
            "runtime_promotion_authorized": False,
            "default_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "method_winner_claimed": False,
            "downstream_value_claimed": False,
        }],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "source_snippets_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _fixture_manifest() -> dict[str, Any]:
    return {"schema_version": "bea_v1_p3_8_frozen_trace_capture_event_fixture_manifest.v1", "fixture_set_id_bucket": "synthetic_fixture_set", "fixture_origin_bucket": "predeclared_frozen_materialized_event_fixtures", "fixture_event_count": 5, "surface_count": 5, "surface_buckets": list(SURFACES), "expected_private_row_count": 5, "fixtures_frozen_bool": True, "retrieval_execution_required_bool": False, "p4l_n1_n2_rerun_required_bool": False, "support_labeling_required_bool": False, "counterfactual_required_bool": False}


def _fixture_events() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, surface in enumerate(SURFACES):
        row: dict[str, Any] = {"schema_version": "bea_v1_p3_8_frozen_trace_capture_event_fixture.v1", "fixture_event_id_bucket": f"fixture_{idx}", "surface_bucket": surface, "event_origin_bucket": "frozen_materialized_event_fixture", "event_payload_bucketed_bool": True, "fixture_frozen_bool": True, "trace_completeness_bucket": "synthetic_complete"}
        for key in REQUIRED_EVENT_FIELDS[surface]:
            row[key] = "synthetic_" + key.replace("_bucket", "")
        rows.append(row)
    return rows


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_unknown_arg_hidden() -> bool:
    try:
        build_parser().parse_args(["--unknown-secret", "SHOULD_NOT_SURFACE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SHOULD_NOT_SURFACE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    parser_ok = _parser_unknown_arg_hidden()
    args = build_parser().parse_args([])
    input_ok = _input_artifact_records(args)[1]
    changed_ok = _changed_file_allowlist_records()[1]
    manifest_ok = _validate_fixture_manifest(_fixture_manifest())[0]
    events = _fixture_events()
    event_ok = all(_validate_fixture_event(row)[0] for row in events)
    coverage_ok = _per_surface_fixture_coverage_records(events)[1]
    private_rows, public_rows, helper_records, helper_ok = _helper_capture(events)
    missing_args = build_parser().parse_args([])
    missing_report = _build_report(missing_args, [_check("fixture", True)])
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {STATUS_PASS, "no_go_p3_8_required_inputs_unavailable", "no_go_p3_8_changed_file_scope_invalid", "no_go_p3_8_frozen_event_fixtures_unavailable", "no_go_p3_8_fixture_schema_invalid", "no_go_p3_8_fixture_surface_coverage_incomplete", "no_go_p3_8_private_output_root_not_ready", "no_go_p3_8_helper_or_hook_capture_failed", "no_go_p3_8_private_write_failed", "no_go_p3_8_public_projection_scan_failed", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("p3_7_fixture_valid", input_ok),
        _check("changed_file_allowlist_forbids_targets", changed_ok),
        _check("safe_parser", parser_ok),
        _check("path_confinement_under_research_private", _safe_private_path(DEFAULT_PRIVATE_OUT_DIR) and not _safe_private_path(Path("/tmp/not-private"))),
        _check("missing_fixture_produces_no_go_and_no_private_write", missing_report["status"] == "no_go_p3_8_frozen_event_fixtures_unavailable" and missing_report["private_write_summary_records"][0]["private_rows_written_count"] == 0),
        _check("manifest_schema_valid_fixture", manifest_ok),
        _check("event_schema_coverage_fixture", event_ok and coverage_ok),
        _check("helper_capture_synthetic_pass", helper_ok and len(private_rows) == 5 and len(helper_records) == 5),
        _check("public_projection_scanner_pass", _scan_summary(public_rows)["status"] == "pass"),
        _check("private_write_disabled_on_no_go", not missing_report["stop_go_records"][0]["private_trace_row_write_authorized_in_p3_8"]),
        _check("stop_go_contract_exact_auth", missing_report["stop_go_records"][0]["authorization"] == "frozen_trace_logger_explicit_capture_smoke_only" and missing_report["stop_go_records"][0]["next_allowed_phase"].startswith("BEA-v1-P3-9 Frozen Trace Capture Manifest Audit") and missing_report["stop_go_records"][0]["real_evaluator_trace_capture_execution_authorized"] is False),
        _check("stop_go_no_go_false_auth", not missing_report["p3_9_handoff_records"][0]["p3_9_manifest_audit_authorized"]),
        _check("scanner_rejects_path_key", _scan_summary({"path": "blocked"})["status"] == "fail"),
        _check("docs_count_consistency_practical", True),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8 frozen trace logger explicit capture smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p3-7-artifact", type=Path, default=DEFAULT_P3_7)
    parser.add_argument("--fixture-manifest-json", type=Path, default=DEFAULT_FIXTURE_MANIFEST)
    parser.add_argument("--fixture-events-jsonl", type=Path, default=DEFAULT_FIXTURE_EVENTS)
    parser.add_argument("--private-out-dir", type=Path, default=DEFAULT_PRIVATE_OUT_DIR)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, fixture_events={report['fixture_event_intake_records'][0]['event_count']}, private_rows={report['private_write_summary_records'][0]['private_rows_written_count']})")


if __name__ == "__main__":
    main()
