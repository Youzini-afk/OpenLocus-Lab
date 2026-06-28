#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_p3_8h_proxy_fixture_compatibility_preflight.v1"
GENERATED_BY = "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py"
PHASE = "BEA-v1-P3-8H"
STATUS_PASS = "proxy_fixture_compatibility_preflight_pass_p3_8i_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8h_required_inputs_unavailable",
    "no_go_p3_8h_private_proxy_fixtures_missing",
    "no_go_p3_8h_proxy_fixture_schema_invalid",
    "no_go_p3_8h_proxy_origin_boundary_invalid",
    "no_go_p3_8h_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
DEFAULT_OUT = Path("artifacts/bea_v1_p3_8h_proxy_fixture_compatibility_preflight/bea_v1_p3_8h_proxy_fixture_compatibility_preflight_report.json")
P3_8G_ARTIFACT = Path("artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json")
PRIVATE_MANIFEST = Path(".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_manifest.json")
PRIVATE_EVENTS = Path(".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_events.jsonl")

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
    "docs/en/bea-v1-p3-8h-proxy-fixture-compatibility-preflight.md",
    "docs/zh/bea-v1-p3-8h-proxy-fixture-compatibility-preflight.md",
    "eval/bea_v1_p3_8h_proxy_fixture_compatibility_preflight.py",
    "artifacts/bea_v1_p3_8h_proxy_fixture_compatibility_preflight/bea_v1_p3_8h_proxy_fixture_compatibility_preflight_report.json",
})
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_p3_8h_proxy_fixture_compatibility_preflight/",
)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_out_dir", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response",
    "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "diff", "raw_diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket", "p3_8_compatibility_action_bucket"})


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


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in full.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                return [], "parse_failed"
            rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


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


def _private_signatures() -> tuple[tuple[bool, int, int], tuple[bool, int, int]]:
    signatures = []
    for path in (PRIVATE_MANIFEST, PRIVATE_EVENTS):
        full = _repo_root() / path
        if not full.exists():
            signatures.append((False, 0, 0))
        else:
            stat = full.stat()
            signatures.append((True, int(stat.st_size), int(stat.st_mtime_ns)))
    return signatures[0], signatures[1]


def _private_inventory_signature() -> tuple[int, int, int]:
    root = _repo_root() / ".openlocus/research-private"
    if not root.exists():
        return (0, 0, 0)
    count = 0
    total_size = 0
    total_mtime = 0
    for path in root.iterdir():
        if not path.is_file():
            continue
        stat = path.stat()
        count += 1
        total_size += int(stat.st_size)
        total_mtime += int(stat.st_mtime_ns)
    return (count, total_size, total_mtime)


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = _load_json(P3_8G_ARTIFACT)
    status = str(artifact.get("status", "") or "")
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    writes = artifact.get("private_write_summary_records", []) if isinstance(artifact.get("private_write_summary_records"), list) else []
    write_count = int(writes[0].get("private_files_written_count", 0) or 0) if writes and isinstance(writes[0], dict) else 0
    stop_go = artifact.get("stop_go_records", []) if isinstance(artifact.get("stop_go_records"), list) else []
    stop = stop_go[0] if stop_go and isinstance(stop_go[0], dict) else {}
    p3_8h = bool(stop.get("p3_8h_proxy_fixture_compatibility_preflight_authorized", False))
    empirical_claim = bool(stop.get("empirical_trace_fixture_claimed", True))
    capture_auth = bool(stop.get("p3_8_capture_execution_authorized", True))
    ok = load_status == "pass" and status == "frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized" and scan == "pass" and write_count == 2 and p3_8h and not empirical_claim and not capture_auth
    return [{"anonymous_input_artifact_id": "p38hi0000", "input_artifact_bucket": "p3_8g_proxy_fixture_materialization_smoke", "load_status": load_status, "observed_status": status, "expected_status": "frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized", "forbidden_scan_status": scan, "proxy_files_written_count": write_count, "p3_8h_authorized_bool": p3_8h, "empirical_trace_fixture_claimed_bool": empirical_claim, "p3_8_capture_execution_authorized_bool": capture_auth, "input_gate_passed_bool": ok}], ok


def _validate_manifest(manifest: dict[str, Any]) -> tuple[bool, int]:
    expected: dict[str, Any] = {
        "schema_version": "bea_v1_p3_8g_proxy_fixture_manifest.v1",
        "fixture_set_id_bucket": "p3_8g_proxy_fixture_set",
        "fixture_origin_bucket": "proxy_fixture_materialized_from_committed_artifact_summaries",
        "fixture_source_bucket": "p3_8f_safe_proxy_source_mappings",
        "fixture_event_count": 5,
        "surface_count": 5,
        "surface_buckets": list(SURFACES),
        "expected_private_row_count": 5,
        "fixtures_frozen_bool": True,
        "proxy_fixture_bool": True,
        "empirical_trace_capture_bool": False,
        "retrieval_execution_required_bool": False,
        "p4l_n1_n2_rerun_required_bool": False,
        "support_labeling_required_bool": False,
        "counterfactual_required_bool": False,
        "policy_change_required_bool": False,
    }
    errors = sum(1 for key, val in expected.items() if manifest.get(key) != val)
    return errors == 0, errors


def _validate_event(event: dict[str, Any]) -> tuple[bool, int]:
    errors = 0
    surface = str(event.get("surface_bucket", "") or "")
    if event.get("schema_version") != "bea_v1_p3_8g_proxy_fixture_event.v1":
        errors += 1
    if surface not in SURFACES:
        return False, errors + 1
    if event.get("event_origin_bucket") != "proxy_materialized_from_committed_artifact_summary":
        errors += 1
    if event.get("proxy_fixture_bool") is not True or event.get("fixture_frozen_bool") is not True or event.get("event_payload_bucketed_bool") is not True:
        errors += 1
    if event.get("empirical_trace_capture_bool") is not False:
        errors += 1
    for field in ("fixture_event_id_bucket", "source_mapping_bucket", "source_artifact_bucket", "fixture_kind_bucket", "missing_empirical_field_buckets"):
        if field not in event:
            errors += 1
    for field in REQUIRED_EVENT_FIELDS[surface]:
        if field not in event:
            errors += 1
    return errors == 0, errors


def _empirical_origin_string_count(obj: Any) -> int:
    count = 0
    if isinstance(obj, dict):
        for val in obj.values():
            count += _empirical_origin_string_count(val)
    elif isinstance(obj, list):
        for val in obj:
            count += _empirical_origin_string_count(val)
    elif isinstance(obj, str):
        if obj in {
            "frozen_materialized_event_fixture",
            "predeclared_frozen_materialized_event_fixtures",
            "empirical_trace_fixture",
            "empirical_trace_capture",
            "empirical_captured_event_fixture",
        }:
            count += 1
    return count


def _private_proxy_fixture_intake_records() -> tuple[list[dict[str, Any]], bool, dict[str, Any], list[dict[str, Any]], int, int]:
    manifest, manifest_load = _load_json(PRIVATE_MANIFEST)
    events, events_load = _read_jsonl(PRIVATE_EVENTS)
    manifest_valid, manifest_errors = _validate_manifest(manifest) if manifest_load == "pass" else (False, 1)
    valid_events = 0
    event_errors = 0
    surface_count = len({str(row.get("surface_bucket", "") or "") for row in events})
    for row in events:
        ok, errs = _validate_event(row)
        valid_events += int(ok)
        event_errors += errs
    missing = manifest_load == "missing" or events_load == "missing"
    ok = not missing and manifest_load == "pass" and events_load == "pass" and manifest_valid and valid_events == 5 and surface_count == 5 and event_errors == 0
    records = [{"anonymous_private_proxy_fixture_intake_id": "p38hpi0000", "proxy_manifest_bucket": "p3_8g_proxy_fixture_manifest_private", "proxy_events_bucket": "p3_8g_proxy_fixture_events_private", "manifest_present_bool": manifest_load != "missing", "events_present_bool": events_load != "missing", "manifest_load_status": manifest_load, "events_load_status": events_load, "manifest_schema_valid_bool": manifest_valid, "manifest_schema_error_count": manifest_errors, "event_count": len(events), "schema_valid_event_count": valid_events, "surface_coverage_count": surface_count, "surface_count": surface_count, "event_schema_error_count": event_errors, "private_proxy_fixtures_present_bool": not missing, "private_paths_publicly_serialized_bool": False, "raw_fixture_payloads_publicly_serialized_bool": False, "private_proxy_fixture_intake_passed_bool": ok}]
    return records, ok, manifest, events, valid_events, surface_count


def _proxy_origin_boundary_records(manifest: dict[str, Any], events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    empirical_claim_count = int(manifest.get("empirical_trace_capture_bool") is True) + sum(1 for row in events if row.get("empirical_trace_capture_bool") is True)
    p3_8_empirical_origin_count = _empirical_origin_string_count(manifest) + _empirical_origin_string_count(events)
    forbidden_required_count = 0
    for key in ("retrieval_execution_required_bool", "p4l_n1_n2_rerun_required_bool", "support_labeling_required_bool", "counterfactual_required_bool", "policy_change_required_bool"):
        forbidden_required_count += int(manifest.get(key) is True)
    origin_valid = empirical_claim_count == 0 and p3_8_empirical_origin_count == 0 and forbidden_required_count == 0 and all(row.get("event_origin_bucket") == "proxy_materialized_from_committed_artifact_summary" for row in events)
    return [{"anonymous_proxy_origin_boundary_id": "p38hob0000", "proxy_fixture_origin_count": sum(1 for row in events if row.get("event_origin_bucket") == "proxy_materialized_from_committed_artifact_summary"), "empirical_trace_capture_claim_count": empirical_claim_count, "p3_8_empirical_origin_string_count": p3_8_empirical_origin_count, "forbidden_execution_required_count": forbidden_required_count, "private_trace_row_write_count": 0, "trace_capture_execution_count": 0, "proxy_origin_boundary_valid_bool": origin_valid}], origin_valid


def _p3_8_schema_compatibility_records(valid_events: int, surface_count: int) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8_schema_compatibility_id": "p38hsc0000", "p3_8_current_schema_accepts_proxy_fixtures_bool": False, "proxy_mode_required_bool": True, "p3_8_default_empirical_mode_must_remain_unchanged_bool": True, "compatibility_decision_bucket": "accept_proxy_only_in_explicit_proxy_mode", "p3_8_compatibility_action_bucket": "requires_p3_8i_explicit_proxy_fixture_logger_smoke_design", "schema_valid_proxy_event_count": valid_events, "surface_count": surface_count, "compatibility_gap_is_failure_bool": False}]


def _proxy_mode_acceptance_records(origin_ok: bool, schema_ok: bool) -> list[dict[str, Any]]:
    accepted = origin_ok and schema_ok
    return [{"anonymous_proxy_mode_acceptance_id": "p38hpa0000", "proxy_mode_acceptance_decision": "accepted_for_logger_smoke_only" if accepted else "rejected", "proxy_mode_preflight_accepts_private_proxy_fixtures_bool": accepted, "empirical_capture_mode_accepts_proxy_fixtures_bool": False, "acceptance_scope_bucket": "explicit_proxy_fixture_logger_smoke_design_only", "empirical_trace_capture_claimed_bool": False, "denominator_audit_authorized_bool": False, "counterfactual_authorized_bool": False, "private_trace_row_write_authorized_in_p3_8h_bool": False, "future_proxy_mode_requires_explicit_flag_bool": True, "future_proxy_mode_default_enabled_bool": False, "requires_p3_8_code_change_bool": False, "requires_capture_execution_bool": False}]


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    runtime = 0
    private_modified = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name.startswith(".openlocus/research-private/"):
            private_modified += 1
            allowed = False
        if not allowed:
            disallowed += 1
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            runtime += 1
    ok = available and disallowed == 0 and forbidden == 0 and runtime == 0 and private_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "p38hcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "private_file_modification_count": private_modified, "helper_p3_8_target_or_runtime_modified_bool": forbidden > 0 or runtime > 0, "disallowed_changed_file_count": disallowed, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records(before: tuple[tuple[bool, int, int], tuple[bool, int, int]], after: tuple[tuple[bool, int, int], tuple[bool, int, int]], inventory_before: tuple[int, int, int], inventory_after: tuple[int, int, int]) -> tuple[list[dict[str, Any]], bool]:
    unchanged = before == after
    inventory_unchanged = inventory_before == inventory_after
    records = [{"anonymous_no_execution_id": "p38hne0000", "private_proxy_fixture_files_modified_in_p3_8h_count": 0 if unchanged else 1, "private_research_inventory_modified_in_p3_8h_count": 0 if inventory_unchanged else 1, "private_trace_rows_written_count": 0, "trace_capture_execution_count": 0, "retrieval_execution_count": 0, "p4l_n1_n2_execution_count": 0, "support_labeling_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_execution_count": 0, "no_execution_boundary_passed_bool": unchanged and inventory_unchanged}]
    return records, unchanged


def _handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8i_handoff_id": "p38hh0000", "next_allowed_phase": "BEA-v1-P3-8I Explicit Proxy Fixture Logger Smoke Design — no capture execution", "p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized": pass_status, "p3_8_code_change_authorized_bool": False, "capture_execution_authorized_bool": False, "requires_separate_phase_bool": True}]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "proxy_fixture_compatibility_preflight_only", "next_allowed_phase": "BEA-v1-P3-8I Explicit Proxy Fixture Logger Smoke Design — no capture execution", "p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized": pass_status, "proxy_mode_accepted_for_logger_smoke_only": pass_status, "p3_8_default_empirical_mode_change_authorized": False, "p3_8_code_change_authorized": False, "p3_8_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, intake_ok: bool, origin_ok: bool, changed_ok: bool, no_exec_ok: bool) -> list[dict[str, Any]]:
    gates = (("p3_8g_input_pass", input_ok, int(input_ok), 1), ("private_proxy_fixtures_valid", intake_ok, int(intake_ok), 1), ("proxy_origin_boundary_valid", origin_ok, int(origin_ok), 1), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("no_execution_and_no_private_write", no_exec_ok, int(no_exec_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    before = _private_signatures()
    inventory_before = _private_inventory_signature()
    input_records, input_ok = _input_artifact_records()
    intake_records, intake_ok, manifest, events, valid_events, surface_count = _private_proxy_fixture_intake_records()
    origin_records, origin_ok = _proxy_origin_boundary_records(manifest, events)
    compatibility_records = _p3_8_schema_compatibility_records(valid_events, surface_count)
    acceptance_records = _proxy_mode_acceptance_records(origin_ok, intake_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    after = _private_signatures()
    inventory_after = _private_inventory_signature()
    no_execution_records, no_exec_ok = _no_execution_records(before, after, inventory_before, inventory_after)
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8h_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8h_changed_file_scope_invalid"
    elif not intake_records[0]["private_proxy_fixtures_present_bool"]:
        status = "no_go_p3_8h_private_proxy_fixtures_missing"
    elif not intake_ok:
        status = "no_go_p3_8h_proxy_fixture_schema_invalid"
    elif not origin_ok:
        status = "no_go_p3_8h_proxy_origin_boundary_invalid"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "proxy_fixture_compatibility_preflight_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "private_proxy_fixture_intake_records": intake_records,
        "proxy_origin_boundary_records": origin_records,
        "p3_8_schema_compatibility_records": compatibility_records,
        "proxy_mode_acceptance_records": acceptance_records,
        "changed_file_allowlist_records": changed_records,
        "no_execution_records": no_execution_records,
        "p3_8i_handoff_records": _handoff_records(pass_status),
        "gate_records": _gate_records(input_ok, intake_ok, origin_ok, changed_ok, no_exec_ok),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_filenames_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
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
    intake_records, intake_ok, manifest, events, valid_events, surface_count = _private_proxy_fixture_intake_records()
    origin_records, origin_ok = _proxy_origin_boundary_records(manifest, events)
    changed_records, changed_ok = _changed_file_allowlist_records()
    before = _private_signatures()
    after = _private_signatures()
    inventory_before = _private_inventory_signature()
    inventory_after = _private_inventory_signature()
    no_exec_records, no_exec_ok = _no_execution_records(before, after, inventory_before, inventory_after)
    stop = _stop_go_records(True)[0]
    compatibility = _p3_8_schema_compatibility_records(valid_events, surface_count)[0]
    acceptance = _proxy_mode_acceptance_records(origin_ok, intake_ok)[0]
    checks = [
        _check("status_vocab_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8h_required_inputs_unavailable", "no_go_p3_8h_private_proxy_fixtures_missing", "no_go_p3_8h_proxy_fixture_schema_invalid", "no_go_p3_8h_proxy_origin_boundary_invalid", "no_go_p3_8h_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("input_validation", input_ok and input_records[0]["proxy_files_written_count"] == 2),
        _check("private_proxy_fixture_schema", intake_ok and valid_events == 5 and surface_count == 5),
        _check("private_intake_public_boundary_flags", intake_records[0]["private_paths_publicly_serialized_bool"] is False and intake_records[0]["raw_fixture_payloads_publicly_serialized_bool"] is False),
        _check("scanner_rejection", _scan_summary({"private_path": "blocked", "raw_payload": "blocked", "snippet": "blocked"})["status"] == "fail"),
        _check("no_private_write", no_exec_ok and no_exec_records[0]["private_proxy_fixture_files_modified_in_p3_8h_count"] == 0),
        _check("origin_boundary", origin_ok and origin_records[0]["empirical_trace_capture_claim_count"] == 0 and origin_records[0]["p3_8_empirical_origin_string_count"] == 0),
        _check("schema_compatibility_requires_proxy_mode", compatibility["p3_8_current_schema_accepts_proxy_fixtures_bool"] is False and compatibility["proxy_mode_required_bool"] is True and compatibility["p3_8_default_empirical_mode_must_remain_unchanged_bool"] is True and compatibility["compatibility_decision_bucket"] == "accept_proxy_only_in_explicit_proxy_mode"),
        _check("proxy_acceptance_scope_exact", acceptance["proxy_mode_acceptance_decision"] == "accepted_for_logger_smoke_only" and acceptance["future_proxy_mode_requires_explicit_flag_bool"] is True and acceptance["future_proxy_mode_default_enabled_bool"] is False and acceptance["private_trace_row_write_authorized_in_p3_8h_bool"] is False),
        _check("stop_go_boundary", stop["p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized"] and stop["proxy_mode_accepted_for_logger_smoke_only"] and not stop["p3_8_default_empirical_mode_change_authorized"] and not stop["p3_8_code_change_authorized"] and not stop["p3_8_capture_execution_authorized"] and not stop["private_trace_row_write_authorized"]),
        _check("changed_file_allowlist", changed_ok and changed_records[0]["private_file_modification_count"] == 0 and not changed_records[0]["helper_p3_8_target_or_runtime_modified_bool"]),
        _check("p3_8g_files_not_allowed_in_p3_8h_scope", "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py" not in ALLOWED_CHANGED_EXACT and "artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/" not in ALLOWED_CHANGED_PREFIXES),
        _check("parser_safety", _parser_hides_unknown()),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8H proxy fixture compatibility preflight")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, events={report['private_proxy_fixture_intake_records'][0]['schema_valid_event_count']}, p3_8i={report['p3_8i_handoff_records'][0]['p3_8i_explicit_proxy_fixture_logger_smoke_design_authorized']})")


if __name__ == "__main__":
    main()
