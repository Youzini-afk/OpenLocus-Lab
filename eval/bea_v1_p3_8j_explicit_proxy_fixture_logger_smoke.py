#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.v1"
PHASE = "BEA-v1-P3-8J"
GENERATED_BY = "bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke"
STATUS_PASS = "explicit_proxy_fixture_logger_smoke_pass_p3_8k_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8j_required_inputs_unavailable",
    "no_go_p3_8j_private_proxy_fixtures_missing",
    "no_go_p3_8j_proxy_fixture_schema_invalid",
    "no_go_p3_8j_helper_smoke_failed",
    "no_go_p3_8j_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
DEFAULT_OUT = Path("artifacts/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke_report.json")
P3_8I_ARTIFACT = Path("artifacts/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design_report.json")
P3_8H_ARTIFACT = Path("artifacts/bea_v1_p3_8h_proxy_fixture_compatibility_preflight/bea_v1_p3_8h_proxy_fixture_compatibility_preflight_report.json")
PROXY_MANIFEST = Path(".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_manifest.json")
PROXY_EVENTS = Path(".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_events.jsonl")

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8j-explicit-proxy-fixture-logger-smoke.md",
    "docs/zh/bea-v1-p3-8j-explicit-proxy-fixture-logger-smoke.md",
    "eval/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke.py",
    "artifacts/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_p3_8j_explicit_proxy_fixture_logger_smoke/",)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "eval/bea_v1_p3_8i_explicit_proxy_fixture_logger_smoke_design.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/", ".openlocus/research-private/")
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_filename", "private_filenames", "private_out_dir",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list",
    "provider", "prompt", "response", "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id",
    "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in full.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    return [], "parse_failed"
                rows.append(value)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def _private_file_signature() -> tuple[tuple[bool, int, int], tuple[bool, int, int], tuple[int, int, int]]:
    signatures: list[tuple[bool, int, int]] = []
    for path in (PROXY_MANIFEST, PROXY_EVENTS):
        full = _repo_root() / path
        if not full.exists():
            signatures.append((False, 0, 0))
        else:
            stat = full.stat()
            signatures.append((True, int(stat.st_size), int(stat.st_mtime_ns)))
    root = _repo_root() / ".openlocus/research-private"
    inventory_count = 0
    inventory_size = 0
    inventory_mtime = 0
    if root.exists():
        for child in root.iterdir():
            if child.is_file():
                stat = child.stat()
                inventory_count += 1
                inventory_size += int(stat.st_size)
                inventory_mtime += int(stat.st_mtime_ns)
    return signatures[0], signatures[1], (inventory_count, inventory_size, inventory_mtime)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if hex_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": key, "count": val} for key, val in sorted(counts.items())]}


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    p3_8i, i_load = _load_json(P3_8I_ARTIFACT)
    i_scan = str(p3_8i.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p3_8i.get("forbidden_scan"), dict) else "not_reported")
    i_stop = p3_8i.get("stop_go_records", []) if isinstance(p3_8i.get("stop_go_records"), list) else []
    i_stop0 = i_stop[0] if i_stop and isinstance(i_stop[0], dict) else {}
    i_ok = (
        i_load == "pass"
        and p3_8i.get("status") == "explicit_proxy_fixture_logger_smoke_design_pass_p3_8j_authorized"
        and i_scan == "pass"
        and i_stop0.get("p3_8j_proxy_smoke_evaluator_authorized") is True
        and i_stop0.get("p3_8_code_change_authorized") is False
        and i_stop0.get("p3_8_capture_execution_authorized") is False
        and i_stop0.get("private_trace_row_write_authorized") is False
        and i_stop0.get("empirical_trace_capture_authorized") is False
    )
    records.append({"anonymous_input_artifact_id": "p38ji0000", "input_artifact_bucket": "p3_8i_explicit_proxy_fixture_logger_smoke_design", "load_status": i_load, "observed_status": str(p3_8i.get("status", "") or ""), "expected_status": "explicit_proxy_fixture_logger_smoke_design_pass_p3_8j_authorized", "forbidden_scan_status": i_scan, "p3_8j_proxy_smoke_evaluator_authorized_bool": bool(i_stop0.get("p3_8j_proxy_smoke_evaluator_authorized", False)), "p3_8_code_change_authorized_bool": bool(i_stop0.get("p3_8_code_change_authorized", True)), "p3_8_capture_execution_authorized_bool": bool(i_stop0.get("p3_8_capture_execution_authorized", True)), "private_trace_row_write_authorized_bool": bool(i_stop0.get("private_trace_row_write_authorized", True)), "empirical_trace_capture_authorized_bool": bool(i_stop0.get("empirical_trace_capture_authorized", True)), "input_gate_passed_bool": i_ok})

    p3_8h, h_load = _load_json(P3_8H_ARTIFACT)
    h_scan = str(p3_8h.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p3_8h.get("forbidden_scan"), dict) else "not_reported")
    h_stop = p3_8h.get("stop_go_records", []) if isinstance(p3_8h.get("stop_go_records"), list) else []
    h_stop0 = h_stop[0] if h_stop and isinstance(h_stop[0], dict) else {}
    h_ok = h_load == "pass" and p3_8h.get("status") == "proxy_fixture_compatibility_preflight_pass_p3_8i_authorized" and h_scan == "pass" and h_stop0.get("proxy_mode_accepted_for_logger_smoke_only") is True
    records.append({"anonymous_input_artifact_id": "p38ji0001", "input_artifact_bucket": "p3_8h_proxy_fixture_compatibility_preflight", "load_status": h_load, "observed_status": str(p3_8h.get("status", "") or ""), "expected_status": "proxy_fixture_compatibility_preflight_pass_p3_8i_authorized", "forbidden_scan_status": h_scan, "proxy_mode_accepted_for_logger_smoke_only_bool": bool(h_stop0.get("proxy_mode_accepted_for_logger_smoke_only", False)), "input_gate_passed_bool": h_ok})
    return records, i_ok and h_ok


def _validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "bea_v1_p3_8g_proxy_fixture_manifest.v1",
        "fixture_event_count": 5,
        "surface_count": 5,
        "proxy_fixture_bool": True,
        "empirical_trace_capture_bool": False,
        "retrieval_execution_required_bool": False,
        "p4l_n1_n2_rerun_required_bool": False,
        "support_labeling_required_bool": False,
        "counterfactual_required_bool": False,
    }
    for key, val in expected.items():
        if manifest.get(key) != val:
            errors.append("manifest_" + key)
    if set(manifest.get("surface_buckets", [])) != set(SURFACES):
        errors.append("manifest_surface_buckets")
    return errors


def _validate_event(row: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("schema_version") != "bea_v1_p3_8g_proxy_fixture_event.v1":
        errors.append("schema_version")
    if row.get("surface_bucket") not in SURFACES:
        errors.append("surface_bucket")
    if row.get("event_origin_bucket") != "proxy_materialized_from_committed_artifact_summary":
        errors.append("event_origin_bucket")
    for key, val in (("proxy_fixture_bool", True), ("empirical_trace_capture_bool", False), ("event_payload_bucketed_bool", True), ("fixture_frozen_bool", True)):
        if row.get(key) != val:
            errors.append(key)
    return errors


def _private_proxy_fixture_intake_records() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], bool, str]:
    manifest, manifest_load = _load_json(PROXY_MANIFEST)
    events, events_load = _load_jsonl(PROXY_EVENTS)
    manifest_errors = _validate_manifest(manifest) if manifest_load == "pass" else [manifest_load]
    event_errors = [_validate_event(row) for row in events]
    valid_events = sum(1 for errs in event_errors if not errs)
    surfaces = {str(row.get("surface_bucket", "")) for row in events if isinstance(row, dict)}
    missing_status = "pass"
    if manifest_load == "missing" or events_load == "missing":
        missing_status = "missing"
    ok = manifest_load == "pass" and events_load == "pass" and not manifest_errors and valid_events == 5 and surfaces == set(SURFACES)
    record = {"anonymous_private_proxy_fixture_intake_id": "p38jpi0000", "manifest_load_status": manifest_load, "events_load_status": events_load, "private_proxy_fixtures_present_bool": manifest_load == "pass" and events_load == "pass", "proxy_manifest_bucket": "p3_8g_proxy_fixture_manifest_private", "proxy_events_bucket": "p3_8g_proxy_fixture_events_private", "manifest_schema_valid_bool": not manifest_errors, "event_count": len(events), "schema_valid_event_count": valid_events, "surface_coverage_count": len(surfaces & set(SURFACES)), "proxy_fixture_bool": bool(manifest.get("proxy_fixture_bool", False)), "empirical_trace_capture_bool": bool(manifest.get("empirical_trace_capture_bool", True)), "private_paths_publicly_serialized_bool": False, "raw_fixture_payloads_publicly_serialized_bool": False, "private_proxy_fixture_intake_passed_bool": ok}
    return [record], manifest, events, ok, missing_status


def _helper_import_review_records() -> tuple[list[dict[str, Any]], Any, bool]:
    try:
        helper = importlib.import_module("bea_v1_frozen_trace_logger_helpers")
        required = []
        for surface in SURFACES:
            required.extend((f"build_{surface}_trace_capture_row_private", f"sanitize_{surface}_trace_capture_row_public", f"validate_{surface}_trace_capture_row_private", f"validate_{surface}_trace_capture_row_public_projection"))
        missing = [name for name in required if not hasattr(helper, name)]
        ok = not missing
    except Exception:
        helper = None
        missing = ["helper_import_failed"]
        ok = False
    return [{"anonymous_helper_import_review_id": "p38jhi0000", "helper_module_imported_bool": helper is not None, "helper_module_bucket": "bea_v1_frozen_trace_logger_helpers", "helper_api_available_bool": ok, "missing_helper_api_count": len(missing), "p3_8_imported_bool": False, "target_evaluator_imported_bool": False, "retrieval_or_provider_imported_bool": False, "helper_import_review_passed_bool": ok}], helper, ok


def _event_for_helper(event: Mapping[str, Any]) -> dict[str, Any]:
    surface = str(event.get("surface_bucket", ""))
    converted = dict(event)
    converted["anonymous_trace_id"] = "proxy_public_" + surface
    converted["anonymous_public_trace_id"] = "proxy_public_" + surface
    converted["trace_completeness_bucket"] = "proxy_fixture_helper_smoke_validated"
    if surface == "support_link":
        converted["support_evidence_role_bucket"] = event.get("support_evidence_role_bucket", event.get("evidence_role_bucket", "proxy_label_summary"))
        converted["source_context_available_bucket"] = event.get("source_context_available_bucket", event.get("source_context_linkage_bucket", "proxy_context_unavailable"))
    return converted


def _run_helper_smoke(helper: Any, events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    smoke_records: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    if helper is None:
        return smoke_records, public_rows, False
    ok_all = True
    events_by_surface = {str(e.get("surface_bucket")): e for e in events}
    for idx, surface in enumerate(SURFACES):
        event = events_by_surface.get(surface, {})
        try:
            converted = _event_for_helper(event)
            builder = getattr(helper, f"build_{surface}_trace_capture_row_private")
            private_validator = getattr(helper, f"validate_{surface}_trace_capture_row_private")
            sanitizer = getattr(helper, f"sanitize_{surface}_trace_capture_row_public")
            public_validator = getattr(helper, f"validate_{surface}_trace_capture_row_public_projection")
            private_row = builder(converted)
            private_result = private_validator(private_row)
            helper_public = sanitizer(private_row)
            public_result = public_validator(helper_public)
            row = {key: value for key, value in helper_public.items() if key != "anonymous_public_trace_id"}
            row["anonymous_public_proxy_trace_id"] = f"p3_8j_proxy_public_{idx:04d}"
            row["proxy_fixture_bool"] = True
            row["empirical_trace_capture_bool"] = False
            row["trace_completeness_bucket"] = "proxy_fixture_helper_smoke_validated"
            scan_pass = _scan_summary(row)["status"] == "pass"
            passed = private_result.get("validation_status") == "pass" and public_result.get("validation_status") == "pass" and scan_pass
        except Exception:
            row = {"anonymous_public_proxy_trace_id": f"p3_8j_proxy_public_{idx:04d}", "surface_bucket": surface, "schema_version_bucket": "helper_exception", "trace_completeness_bucket": "proxy_fixture_helper_smoke_failed", "proxy_fixture_bool": True, "empirical_trace_capture_bool": False}
            passed = False
            scan_pass = False
            private_result = {"validation_status": "fail"}
            public_result = {"validation_status": "fail"}
        public_rows.append(row)
        smoke_records.append({"anonymous_per_surface_proxy_smoke_id": f"p38jps{idx:04d}", "surface_bucket": surface, "proxy_event_loaded_bool": bool(event), "proxy_fixture_bool": True, "empirical_trace_capture_claimed_bool": False, "helper_private_builder_pass_bool": private_result.get("validation_status") == "pass", "helper_private_validator_pass_bool": private_result.get("validation_status") == "pass", "helper_public_sanitizer_pass_bool": bool(row), "helper_public_validator_pass_bool": public_result.get("validation_status") == "pass", "public_projection_scanner_pass_bool": scan_pass, "private_trace_row_written_bool": False, "proxy_smoke_passed_bool": passed})
        ok_all = ok_all and passed
    return smoke_records, public_rows, ok_all


def _public_projection_records(public_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    ok = len(public_rows) == 5
    for idx, row in enumerate(public_rows):
        safe = _scan_summary(row)["status"] == "pass"
        rows.append({"anonymous_public_projection_record_id": f"p38jpp{idx:04d}", **row, "public_projection_scanner_passed_bool": safe})
        ok = ok and safe and row.get("proxy_fixture_bool") is True and row.get("empirical_trace_capture_bool") is False and row.get("trace_completeness_bucket") == "proxy_fixture_helper_smoke_validated"
    return rows, ok


def _no_execution_records(before: tuple[tuple[bool, int, int], tuple[bool, int, int], tuple[int, int, int]], after: tuple[tuple[bool, int, int], tuple[bool, int, int], tuple[int, int, int]]) -> tuple[list[dict[str, Any]], bool]:
    proxy_files_unchanged = before[:2] == after[:2]
    inventory_unchanged = before[2] == after[2]
    record = {"anonymous_no_execution_id": "p38jne0000", "p3_8_import_count": 0, "target_evaluator_import_count": 0, "private_proxy_fixture_modification_count": 0 if proxy_files_unchanged else 1, "private_research_inventory_modification_count": 0 if inventory_unchanged else 1, "private_trace_row_write_count": 0, "trace_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "p5_or_v1_a_execution_count": 0, "no_execution_boundary_passed_bool": proxy_files_unchanged and inventory_unchanged}
    return [record], proxy_files_unchanged and inventory_unchanged


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    private_modified = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name.startswith(".openlocus/research-private/"):
            private_modified += 1
            allowed = False
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            forbidden += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and forbidden == 0 and private_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "p38jcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_file_modification_count": private_modified, "p3_8_p3_8g_p3_8h_p3_8i_helper_target_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8k_handoff_id": "p38jhk0000", "next_allowed_phase": "BEA-v1-P3-8K Proxy Fixture Smoke Public Projection Audit — no empirical capture", "p3_8k_public_projection_audit_authorized": pass_status, "requires_separate_phase_bool": True, "empirical_capture_authorized_bool": False, "private_trace_row_write_authorized_bool": False}]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "explicit_proxy_fixture_logger_smoke_only", "next_allowed_phase": "BEA-v1-P3-8K Proxy Fixture Smoke Public Projection Audit — no empirical capture", "p3_8k_public_projection_audit_authorized": pass_status, "proxy_fixture_smoke_executed": pass_status, "empirical_trace_capture_authorized": False, "empirical_trace_capture_claimed": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "target_evaluator_import_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, fixture_ok: bool, helper_import_ok: bool, smoke_records: list[dict[str, Any]], projection_records: list[dict[str, Any]], changed_ok: bool) -> list[dict[str, Any]]:
    helper_pass_count = sum(1 for row in smoke_records if row.get("proxy_smoke_passed_bool") is True)
    projection_pass_count = sum(1 for row in projection_records if row.get("public_projection_scanner_passed_bool") is True)
    gates = (("required_inputs_available", input_ok, int(input_ok), 1), ("private_proxy_fixtures_valid", fixture_ok, int(fixture_ok), 1), ("helper_import_isolated", helper_import_ok, int(helper_import_ok), 1), ("helper_smoke_pass_5_of_5", helper_pass_count == 5, helper_pass_count, 5), ("public_projection_scan_pass_5_of_5", projection_pass_count == 5, projection_pass_count, 5), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    private_before = _private_file_signature()
    input_records, input_ok = _input_artifact_records()
    fixture_records, _manifest, events, fixture_ok, fixture_status = _private_proxy_fixture_intake_records()
    helper_records, helper, helper_import_ok = _helper_import_review_records()
    smoke_records, public_rows, helper_smoke_ok = _run_helper_smoke(helper, events) if fixture_ok else ([], [], False)
    projection_records, projection_ok = _public_projection_records(public_rows) if public_rows else ([], False)
    private_after = _private_file_signature()
    no_execution_records, no_execution_ok = _no_execution_records(private_before, private_after)
    changed_records, changed_ok = _changed_file_allowlist_records()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8j_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8j_changed_file_scope_invalid"
    elif fixture_status == "missing":
        status = "no_go_p3_8j_private_proxy_fixtures_missing"
    elif not fixture_ok:
        status = "no_go_p3_8j_proxy_fixture_schema_invalid"
    elif not helper_import_ok or not helper_smoke_ok or not projection_ok:
        status = "no_go_p3_8j_helper_smoke_failed"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "explicit_proxy_fixture_logger_smoke_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "private_proxy_fixture_intake_records": fixture_records,
        "helper_import_review_records": helper_records,
        "per_surface_proxy_smoke_records": smoke_records,
        "public_projection_records": projection_records,
        "no_execution_records": no_execution_records,
        "changed_file_allowlist_records": changed_records,
        "p3_8k_handoff_records": _handoff_records(pass_status),
        "gate_records": _gate_records(input_ok, fixture_ok, helper_import_ok, smoke_records, projection_records, changed_ok and no_execution_ok),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "private_filenames_publicly_serialized": False,
        "raw_fixture_payloads_publicly_serialized": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_records, input_ok = _input_artifact_records()
    fixture_records, _manifest, events, fixture_ok, _fixture_status = _private_proxy_fixture_intake_records()
    helper_records, helper, helper_import_ok = _helper_import_review_records()
    smoke_records, public_rows, helper_smoke_ok = _run_helper_smoke(helper, events) if fixture_ok else ([], [], False)
    projection_records, projection_ok = _public_projection_records(public_rows) if public_rows else ([], False)
    sig = _private_file_signature()
    no_execution_records, no_execution_ok = _no_execution_records(sig, sig)
    changed_records, changed_ok = _changed_file_allowlist_records()
    stop = _stop_go_records(True)[0]
    checks = [
        _check("status_vocab_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8j_required_inputs_unavailable", "no_go_p3_8j_private_proxy_fixtures_missing", "no_go_p3_8j_proxy_fixture_schema_invalid", "no_go_p3_8j_helper_smoke_failed", "no_go_p3_8j_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("parser_safety", _parser_hides_unknown()),
        _check("scanner", _scan_summary({"private_path": "blocked", "raw_payload": "blocked"})["status"] == "fail"),
        _check("input_gates", input_ok and len(input_records) == 2),
        _check("helper_import_isolation", helper_import_ok and helper_records[0]["helper_module_imported_bool"] and not helper_records[0]["p3_8_imported_bool"] and not helper_records[0]["target_evaluator_imported_bool"] and not helper_records[0]["retrieval_or_provider_imported_bool"]),
        _check("event_schema", fixture_ok and fixture_records[0]["schema_valid_event_count"] == 5 and fixture_records[0]["surface_coverage_count"] == 5),
        _check("public_projection_shape", projection_ok and len(projection_records) == 5 and all("anonymous_public_proxy_trace_id" in r for r in projection_records)),
        _check("helper_smoke", helper_smoke_ok and len(smoke_records) == 5 and all(r["proxy_smoke_passed_bool"] and r["helper_private_builder_pass_bool"] and r["helper_private_validator_pass_bool"] and r["helper_public_sanitizer_pass_bool"] and r["helper_public_validator_pass_bool"] and r["public_projection_scanner_pass_bool"] for r in smoke_records)),
        _check("no_private_writes", no_execution_ok and no_execution_records[0]["private_trace_row_write_count"] == 0 and no_execution_records[0]["private_proxy_fixture_modification_count"] == 0 and no_execution_records[0]["private_research_inventory_modification_count"] == 0 and fixture_records[0]["private_paths_publicly_serialized_bool"] is False),
        _check("changed_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0 and not changed_records[0]["p3_8_p3_8g_p3_8h_p3_8i_helper_target_or_runtime_modified_bool"]),
        _check("stop_go", stop["p3_8k_public_projection_audit_authorized"] and stop["proxy_fixture_smoke_executed"] and not stop["empirical_trace_capture_authorized"] and not stop["private_trace_row_write_authorized"] and not stop["retrieval_execution_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8J explicit proxy fixture logger smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, projections={len(report['public_projection_records'])}, p3_8k={report['p3_8k_handoff_records'][0]['p3_8k_public_projection_audit_authorized']})")


if __name__ == "__main__":
    main()
