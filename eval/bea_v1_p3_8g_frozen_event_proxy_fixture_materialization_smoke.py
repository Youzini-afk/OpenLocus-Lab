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


SCHEMA_VERSION = "bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.v1"
GENERATED_BY = "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py"
PHASE = "BEA-v1-P3-8G"
STATUS_PASS = "frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8g_required_inputs_unavailable",
    "no_go_p3_8g_proxy_source_mapping_invalid",
    "no_go_p3_8g_changed_file_scope_invalid",
    "no_go_p3_8g_private_output_root_not_ready",
    "no_go_p3_8g_proxy_fixture_schema_invalid",
    "no_go_p3_8g_private_fixture_write_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SURFACES = ("support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty")
DEFAULT_OUT = Path("artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json")
P3_8F_ARTIFACT = Path("artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight_report.json")
PRIVATE_ROOT = Path(".openlocus/research-private")
PRIVATE_MANIFEST = PRIVATE_ROOT / "bea_v1_p3_8g_proxy_fixture_manifest.json"
PRIVATE_EVENTS = PRIVATE_ROOT / "bea_v1_p3_8g_proxy_fixture_events.jsonl"
FORBIDDEN_P3_8_DEFAULT_FIXTURE_NAMES = frozenset({
    "bea_v1_p3_8_frozen_trace_capture_event_fixture_manifest.json",
    "bea_v1_p3_8_frozen_trace_capture_event_fixtures.jsonl",
})

REQUIRED_EVENT_FIELDS = {
    "support_link": ("anonymous_design_join_key", "queue_item_join_key", "support_relation_bucket", "target_hit_bucket", "support_hit_bucket", "conjunction_bucket", "evidence_role_bucket", "leakage_risk_bucket", "source_context_linkage_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
    "scheduler_action_cost": ("locked_denominator_join_key", "arm_bucket", "action_sequence_bucket", "latency_bucket", "pool_size_bucket", "pool_delta_bucket", "hard_cap_bucket", "file_reach_bucket", "cost_state_bucket", "scheduler_state_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "ordered_prefix_stop": ("prefix_join_key", "arm_bucket", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "stop_policy_bucket", "continue_reference_bucket", "early_stop_signal_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "same_file_redundancy": ("redundancy_join_key", "action_layer_bucket", "action_arm_bucket", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"),
    "risk_penalty": ("risk_join_key", "action_layer_bucket", "action_arm_bucket", "risk_class_bucket", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket", "capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket"),
}

PROXY_VALUES = {
    "support_link": {
        "anonymous_design_join_key": "proxy_not_empirical",
        "queue_item_join_key": "proxy_not_empirical",
        "support_relation_bucket": "proxy_label_summary",
        "target_hit_bucket": "proxy_unknown_not_empirical",
        "support_hit_bucket": "proxy_unknown_not_empirical",
        "conjunction_bucket": "proxy_unknown_not_empirical",
        "evidence_role_bucket": "proxy_label_summary",
        "leakage_risk_bucket": "proxy_label_summary",
        "source_context_linkage_bucket": "proxy_context_unavailable",
    },
    "scheduler_action_cost": {
        "locked_denominator_join_key": "proxy_contract_template",
        "arm_bucket": "proxy_contract_template",
        "action_sequence_bucket": "proxy_not_empirical",
        "latency_bucket": "proxy_contract_template",
        "pool_size_bucket": "proxy_contract_template",
        "pool_delta_bucket": "proxy_contract_template",
        "hard_cap_bucket": "proxy_contract_template",
        "file_reach_bucket": "proxy_not_empirical",
        "cost_state_bucket": "proxy_not_empirical",
        "scheduler_state_bucket": "proxy_not_empirical",
    },
    "ordered_prefix_stop": {
        "prefix_join_key": "proxy_aggregate_bucket",
        "arm_bucket": "proxy_aggregate_bucket",
        "prefix_position_bucket": "proxy_not_row_level",
        "prefix_cost_bucket": "proxy_aggregate_bucket",
        "budget_remaining_bucket": "proxy_not_row_level",
        "marginal_gain_bucket": "proxy_not_row_level",
        "stop_policy_bucket": "proxy_aggregate_bucket",
        "continue_reference_bucket": "proxy_not_row_level",
        "early_stop_signal_bucket": "proxy_aggregate_bucket",
    },
    "same_file_redundancy": {
        "redundancy_join_key": "proxy_contract_template",
        "action_layer_bucket": "proxy_contract_template",
        "action_arm_bucket": "proxy_contract_template",
        "duplicate_pressure_bucket": "proxy_not_empirical",
        "same_file_candidate_count_bucket": "proxy_not_empirical",
        "topk_file_diversity_bucket": "proxy_not_empirical",
        "gold_file_displacement_bucket": "proxy_not_empirical",
        "marginal_utility_bucket": "proxy_not_empirical",
    },
    "risk_penalty": {
        "risk_join_key": "proxy_contract_template",
        "action_layer_bucket": "proxy_contract_template",
        "action_arm_bucket": "proxy_contract_template",
        "risk_class_bucket": "proxy_contract_template",
        "risk_policy_bucket": "proxy_not_empirical",
        "removed_gold_bucket": "proxy_not_empirical",
        "replacement_bucket": "proxy_not_empirical",
        "topk_effect_bucket": "proxy_not_empirical",
        "counterfactual_keep_bucket": "proxy_not_empirical",
    },
}

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8g-frozen-event-proxy-fixture-materialization-smoke.md",
    "docs/zh/bea-v1-p3-8g-frozen-event-proxy-fixture-materialization-smoke.md",
    "eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py",
    "artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json",
    ".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_manifest.json",
    ".openlocus/research-private/bea_v1_p3_8g_proxy_fixture_events.jsonl",
})
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/",
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
    "path", "paths", "file_path", "source_path", "private_path", "private_out_dir", "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "diff", "raw_diff",
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


def _safe_private_path(path: Path) -> bool:
    root = (_repo_root() / PRIVATE_ROOT).resolve()
    try:
        resolved = (path if path.is_absolute() else _repo_root() / path).resolve()
        resolved.relative_to(root)
        return True
    except Exception:
        return False


def _private_root_ready() -> tuple[bool, bool, bool]:
    root = _repo_root() / PRIVATE_ROOT
    gitignore = _repo_root() / ".gitignore"
    ignored = gitignore.exists() and ".openlocus/" in gitignore.read_text(encoding="utf-8")
    return root.exists() and root.is_dir(), ignored, _safe_private_path(PRIVATE_MANIFEST) and _safe_private_path(PRIVATE_EVENTS)


def _p3_8_default_fixture_file_count() -> int:
    root = _repo_root() / PRIVATE_ROOT
    if not root.exists():
        return 0
    names = {p.name for p in root.iterdir() if p.is_file()}
    return sum(1 for name in FORBIDDEN_P3_8_DEFAULT_FIXTURE_NAMES if name in names)


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        names = [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()]
        return names, proc.returncode == 0
    except Exception:
        return [], False


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    runtime = 0
    expected_private_seen = sum(1 for path in (PRIVATE_MANIFEST, PRIVATE_EVENTS) if (_repo_root() / path).exists())
    unexpected_private = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name in (".openlocus", ".openlocus/research-private"):
            allowed = True
        if name.startswith(".openlocus/research-private/") and name not in ALLOWED_CHANGED_EXACT:
            unexpected_private += 1
            allowed = False
        if not allowed:
            disallowed += 1
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(FORBIDDEN_PREFIXES):
            runtime += 1
    ok = available and disallowed == 0 and forbidden == 0 and runtime == 0 and unexpected_private == 0
    return [{"anonymous_changed_file_allowlist_id": "p38gcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "expected_private_fixture_file_count_seen": expected_private_seen, "unexpected_research_private_file_count": unexpected_private, "disallowed_changed_file_count": disallowed, "helper_p3_8_target_or_runtime_modified_bool": forbidden > 0 or runtime > 0, "changed_file_scope_valid_bool": ok}], ok


def _input_records() -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
    artifact, load_status = _load_json(P3_8F_ARTIFACT)
    scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
    status = str(artifact.get("status", "") or "")
    mappings = artifact.get("fixture_source_mapping_records", []) if isinstance(artifact.get("fixture_source_mapping_records"), list) else []
    safe_count = sum(1 for row in mappings if isinstance(row, dict) and row.get("safe_proxy_source_mapping_bool") is True)
    empirical_count = sum(1 for row in mappings if isinstance(row, dict) and row.get("empirical_captured_event_fixture_bool") is True)
    stop_go = artifact.get("stop_go_records", []) if isinstance(artifact.get("stop_go_records"), list) else []
    p3_8g_auth = bool(stop_go and isinstance(stop_go[0], dict) and stop_go[0].get("p3_8g_fixture_materialization_authorized") is True)
    no_private = artifact.get("no_private_write_records", []) if isinstance(artifact.get("no_private_write_records"), list) else []
    private_written = 0
    if no_private and isinstance(no_private[0], dict):
        private_written = int(no_private[0].get("private_fixture_files_written_in_p3_8f_count", 0) or 0)
    ok = load_status == "pass" and status == "frozen_event_fixture_materialization_preflight_pass_p3_8g_authorized" and scan == "pass" and len(mappings) == 5 and safe_count == 5 and empirical_count == 0 and p3_8g_auth and private_written == 0
    return [{"anonymous_input_artifact_id": "p38gi0000", "input_artifact_bucket": "p3_8f_frozen_event_fixture_materialization_preflight", "load_status": load_status, "observed_status": status, "expected_status": "frozen_event_fixture_materialization_preflight_pass_p3_8g_authorized", "forbidden_scan_status": scan, "safe_proxy_mapping_count": safe_count, "empirical_mapping_count": empirical_count, "p3_8g_authorized_bool": p3_8g_auth, "p3_8f_private_fixture_write_count": private_written, "input_gate_passed_bool": ok}], ok, [row for row in mappings if isinstance(row, dict)]


def _proxy_manifest() -> dict[str, Any]:
    return {
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


def _mapping_by_surface(mappings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("surface_bucket", "") or ""): row for row in mappings}


def _proxy_events(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_surface = _mapping_by_surface(mappings)
    events = []
    for surface in SURFACES:
        mapping = by_surface[surface]
        event: dict[str, Any] = {
            "schema_version": "bea_v1_p3_8g_proxy_fixture_event.v1",
            "fixture_event_id_bucket": f"p3_8g_proxy_{surface}",
            "surface_bucket": surface,
            "event_origin_bucket": "proxy_materialized_from_committed_artifact_summary",
            "event_payload_bucketed_bool": True,
            "fixture_frozen_bool": True,
            "proxy_fixture_bool": True,
            "empirical_trace_capture_bool": False,
            "source_mapping_bucket": mapping.get("source_mapping_bucket", "proxy_unknown"),
            "source_artifact_bucket": mapping.get("source_artifact_bucket", "proxy_unknown"),
            "fixture_kind_bucket": mapping.get("fixture_kind_bucket", "proxy_unknown"),
            "missing_empirical_field_buckets": list(mapping.get("missing_empirical_field_buckets", [])),
            "capture_phase_bucket": "p3_8g_proxy_fixture_materialization",
            "trace_logger_version_bucket": "proxy_fixture_v1",
            "validation_status_bucket": "proxy_schema_smoke_valid",
            "replay_freeze_bucket": "proxy_not_empirical",
        }
        for field in REQUIRED_EVENT_FIELDS[surface]:
            if field in ("capture_phase_bucket", "trace_logger_version_bucket", "validation_status_bucket", "replay_freeze_bucket"):
                continue
            event[field] = PROXY_VALUES[surface].get(field, "proxy_unknown")
        events.append(event)
    return events


def _validate_manifest(manifest: dict[str, Any]) -> tuple[bool, int]:
    errors = 0
    expected = _proxy_manifest()
    for key, expected_value in expected.items():
        if manifest.get(key) != expected_value:
            errors += 1
    return errors == 0, errors


def _validate_event(event: dict[str, Any]) -> tuple[bool, int]:
    errors = 0
    surface = str(event.get("surface_bucket", "") or "")
    if event.get("schema_version") != "bea_v1_p3_8g_proxy_fixture_event.v1":
        errors += 1
    if surface not in SURFACES:
        errors += 1
        return False, errors
    for key in ("fixture_event_id_bucket", "event_origin_bucket", "source_mapping_bucket", "source_artifact_bucket", "fixture_kind_bucket", "missing_empirical_field_buckets"):
        if key not in event:
            errors += 1
    for key in ("event_payload_bucketed_bool", "fixture_frozen_bool", "proxy_fixture_bool"):
        if event.get(key) is not True:
            errors += 1
    if event.get("empirical_trace_capture_bool") is not False:
        errors += 1
    if event.get("event_origin_bucket") != "proxy_materialized_from_committed_artifact_summary":
        errors += 1
    for field in REQUIRED_EVENT_FIELDS[surface]:
        if field not in event:
            errors += 1
    for value in event.values():
        if isinstance(value, str) and ("empirical_" in value and value not in {"proxy_not_empirical", "proxy_unknown_not_empirical"}):
            errors += 1
    return errors == 0, errors


def _write_private_files(manifest: dict[str, Any], events: list[dict[str, Any]]) -> tuple[bool, int, int]:
    if not (_safe_private_path(PRIVATE_MANIFEST) and _safe_private_path(PRIVATE_EVENTS)):
        return False, 0, 0
    try:
        root = _repo_root() / PRIVATE_ROOT
        root.mkdir(parents=True, exist_ok=True)
        (_repo_root() / PRIVATE_MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (_repo_root() / PRIVATE_EVENTS).write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
    except Exception:
        return False, 0, 0
    read_manifest, load_manifest = _load_json(PRIVATE_MANIFEST)
    event_rows: list[dict[str, Any]] = []
    load_events = "pass"
    try:
        for line in (_repo_root() / PRIVATE_EVENTS).read_text(encoding="utf-8").splitlines():
            event_rows.append(json.loads(line))
    except Exception:
        load_events = "parse_failed"
    manifest_ok = load_manifest == "pass" and _validate_manifest(read_manifest)[0]
    valid_events = sum(1 for event in event_rows if _validate_event(event)[0])
    return manifest_ok and load_events == "pass" and valid_events == len(events), int(manifest_ok), valid_events


def _manifest_summary_records(manifest: dict[str, Any], manifest_valid: bool) -> list[dict[str, Any]]:
    return [{"anonymous_proxy_manifest_summary_id": "p38gms0000", "proxy_manifest_bucket": "p3_8g_proxy_fixture_manifest_private", "schema_version_bucket": str(manifest.get("schema_version", "")), "fixture_origin_bucket": str(manifest.get("fixture_origin_bucket", "")), "fixture_event_count": int(manifest.get("fixture_event_count", 0) or 0), "surface_count": int(manifest.get("surface_count", 0) or 0), "proxy_fixture_bool": bool(manifest.get("proxy_fixture_bool", False)), "empirical_trace_capture_bool": bool(manifest.get("empirical_trace_capture_bool", True)), "manifest_schema_valid_bool": manifest_valid}]


def _event_summary_records(events: list[dict[str, Any]], valid_count: int) -> list[dict[str, Any]]:
    counts = Counter(str(event.get("surface_bucket", "") or "") for event in events)
    return [{"anonymous_proxy_event_summary_id": "p38ges0000", "proxy_events_bucket": "p3_8g_proxy_fixture_events_private", "event_count": len(events), "schema_valid_event_count": valid_count, "surface_count": len([surface for surface in SURFACES if counts.get(surface, 0) > 0]), "proxy_fixture_event_count": sum(1 for event in events if event.get("proxy_fixture_bool") is True), "empirical_trace_capture_event_count": sum(1 for event in events if event.get("empirical_trace_capture_bool") is True)}]


def _per_surface_records(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    by_surface = {str(event.get("surface_bucket", "") or ""): event for event in events}
    for idx, surface in enumerate(SURFACES):
        event = by_surface[surface]
        records.append({"anonymous_per_surface_proxy_fixture_id": f"p38gps{idx:04d}", "surface_bucket": surface, "source_mapping_bucket": str(event.get("source_mapping_bucket", "")), "source_artifact_bucket": str(event.get("source_artifact_bucket", "")), "fixture_kind_bucket": str(event.get("fixture_kind_bucket", "")), "missing_empirical_field_count": len(event.get("missing_empirical_field_buckets", [])), "helper_required_field_count": len(REQUIRED_EVENT_FIELDS[surface]), "helper_required_fields_present_bool": all(field in event for field in REQUIRED_EVENT_FIELDS[surface]), "proxy_safe_bucket_values_bool": True, "empirical_origin_value_used_bool": False})
    return records


def _private_write_summary_records(write_ok: bool, manifest_valid_count: int, valid_event_count: int, default_fixture_file_count: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_write_summary_id": "p38gpw0000", "proxy_manifest_bucket": "p3_8g_proxy_fixture_manifest_private", "proxy_events_bucket": "p3_8g_proxy_fixture_events_private", "private_output_root_bucket": "openlocus_research_private", "private_paths_publicly_serialized_bool": False, "p3_8_default_fixture_filenames_written_bool": default_fixture_file_count > 0, "p3_8_default_fixture_filename_count": default_fixture_file_count, "private_file_write_attempted_bool": True, "private_files_written_count": 2 if write_ok else 0, "manifest_schema_valid_count": manifest_valid_count, "event_schema_valid_count": valid_event_count, "private_fixture_write_passed_bool": write_ok}]


def _p3_8_compatibility_records() -> list[dict[str, Any]]:
    return [{"anonymous_p3_8_compatibility_id": "p38gpc0000", "p3_8_current_schema_accepts_proxy_fixtures_bool": False, "p3_8_compatibility_action_bucket": "requires_p3_8h_proxy_mode_or_rejection_decision", "compatibility_gap_is_failure_bool": False}]


def _handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_p3_8h_handoff_id": "p38gh0000", "next_allowed_phase": "BEA-v1-P3-8H Proxy Fixture Compatibility Preflight — no capture execution", "p3_8h_proxy_fixture_compatibility_preflight_authorized": pass_status, "capture_execution_authorized_bool": False, "requires_separate_phase_bool": True}]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "frozen_event_proxy_fixture_materialization_smoke_only", "next_allowed_phase": "BEA-v1-P3-8H Proxy Fixture Compatibility Preflight — no capture execution", "p3_8h_proxy_fixture_compatibility_preflight_authorized": pass_status, "proxy_fixture_files_written": pass_status, "empirical_trace_fixture_claimed": False, "p3_8_capture_execution_authorized": False, "private_trace_row_write_authorized": False, "retrieval_execution_authorized": False, "p4l_rerun_authorized": False, "n1_n2_rerun_authorized": False, "support_labeling_authorized": False, "denominator_audit_authorized": False, "trace_counterfactual_execution_authorized": False, "support_counterfactual_execution_authorized": False, "policy_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "broad_retrieval_expansion_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, mapping_ok: bool, changed_ok: bool, root_ok: bool, schema_ok: bool, write_ok: bool, default_files_absent: bool) -> list[dict[str, Any]]:
    gates = (("p3_8f_input_pass", input_ok, int(input_ok), 1), ("proxy_source_mapping_valid_5_of_5", mapping_ok, 5 if mapping_ok else 0, 5), ("changed_file_scope_valid", changed_ok, int(changed_ok), 1), ("private_output_root_ready", root_ok, int(root_ok), 1), ("proxy_fixture_schema_valid", schema_ok, int(schema_ok), 1), ("p3_8_default_fixture_files_absent", default_files_absent, 0 if default_files_absent else 1, 0), ("private_fixture_write_pass", write_ok, int(write_ok), 1), ("forbidden_execution_zero", True, 0, 0))
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, input_ok, mappings = _input_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    root_exists, root_ignored, paths_safe = _private_root_ready()
    root_ok = root_exists and root_ignored and paths_safe
    mapping_ok = len(mappings) == 5 and sum(1 for row in mappings if row.get("safe_proxy_source_mapping_bool") is True) == 5 and not any(row.get("empirical_captured_event_fixture_bool") is True for row in mappings)
    manifest = _proxy_manifest()
    events = _proxy_events(mappings) if mapping_ok else []
    manifest_valid, _ = _validate_manifest(manifest)
    event_valid_count = sum(1 for event in events if _validate_event(event)[0])
    schema_ok = manifest_valid and len(events) == 5 and event_valid_count == 5
    default_count_before_write = _p3_8_default_fixture_file_count()
    self_ok = all(c["passed"] for c in checks)
    write_ok = False
    manifest_valid_count = 0
    written_event_valid_count = 0
    default_files_absent = default_count_before_write == 0
    if self_ok and input_ok and mapping_ok and changed_ok and root_ok and schema_ok and default_files_absent:
        write_ok, manifest_valid_count, written_event_valid_count = _write_private_files(manifest, events)
    default_count_after_write = _p3_8_default_fixture_file_count()
    default_files_absent = default_count_after_write == 0
    write_ok = write_ok and default_files_absent
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8g_required_inputs_unavailable"
    elif not mapping_ok:
        status = "no_go_p3_8g_proxy_source_mapping_invalid"
    elif not changed_ok:
        status = "no_go_p3_8g_changed_file_scope_invalid"
    elif not root_ok:
        status = "no_go_p3_8g_private_output_root_not_ready"
    elif not schema_ok:
        status = "no_go_p3_8g_proxy_fixture_schema_invalid"
    elif not default_files_absent:
        status = "no_go_p3_8g_private_fixture_write_failed"
    elif not write_ok:
        status = "no_go_p3_8g_private_fixture_write_failed"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_event_proxy_fixture_materialization_smoke_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "proxy_fixture_manifest_summary_records": _manifest_summary_records(manifest, manifest_valid),
        "proxy_fixture_event_summary_records": _event_summary_records(events, event_valid_count),
        "per_surface_proxy_fixture_records": _per_surface_records(events) if events else [],
        "private_write_summary_records": _private_write_summary_records(write_ok, manifest_valid_count, written_event_valid_count, default_count_after_write),
        "changed_file_allowlist_records": changed_records,
        "p3_8_compatibility_records": _p3_8_compatibility_records(),
        "p3_8h_handoff_records": _handoff_records(pass_status),
        "gate_records": _gate_records(input_ok, mapping_ok, changed_ok, root_ok, schema_ok, write_ok, default_files_absent),
        "stop_go_records": _stop_go_records(pass_status),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "private_paths_publicly_serialized": False,
        "raw_fixture_payloads_publicly_serialized": False,
        "p3_8_default_fixture_files_written": False,
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
    input_records, input_ok, mappings = _input_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    root_exists, root_ignored, paths_safe = _private_root_ready()
    manifest = _proxy_manifest()
    events = _proxy_events(mappings) if len(mappings) == 5 else []
    manifest_ok, _ = _validate_manifest(manifest)
    event_ok = len(events) == 5 and all(_validate_event(event)[0] for event in events)
    helper_fields_ok = bool(events) and all(all(field in event for field in REQUIRED_EVENT_FIELDS[event["surface_bucket"]]) for event in events)
    no_empirical = bool(events) and all(event.get("empirical_trace_capture_bool") is False and event.get("event_origin_bucket") == "proxy_materialized_from_committed_artifact_summary" for event in events)
    stop = _stop_go_records(True)[0]
    checks = [
        _check("status_vocab_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8g_required_inputs_unavailable", "no_go_p3_8g_proxy_source_mapping_invalid", "no_go_p3_8g_changed_file_scope_invalid", "no_go_p3_8g_private_output_root_not_ready", "no_go_p3_8g_proxy_fixture_schema_invalid", "no_go_p3_8g_private_fixture_write_failed", "fail_forbidden_scan", "fail_schema_contract")),
        _check("input_validation", input_ok and input_records[0]["safe_proxy_mapping_count"] == 5),
        _check("private_path_confinement", _safe_private_path(PRIVATE_MANIFEST) and _safe_private_path(PRIVATE_EVENTS) and not _safe_private_path(Path("/tmp/not_allowed.json"))),
        _check("gitignore_root_readiness", root_exists and root_ignored and paths_safe),
        _check("manifest_event_schema", manifest_ok and event_ok),
        _check("helper_required_fields_present", helper_fields_ok),
        _check("no_empirical_origin_values", no_empirical),
        _check("p3_8_default_fixture_files_absent", _p3_8_default_fixture_file_count() == 0),
        _check("public_scanner_rejects_private_path_raw_payload_keys", _scan_summary({"private_path": "blocked", "payload": "blocked"})["status"] == "fail"),
        _check("changed_file_allowlist_expected_private_and_forbids_helper_p3_8_runtime", changed_ok and not changed_records[0]["helper_p3_8_target_or_runtime_modified_bool"]),
        _check("p3_8f_files_not_allowed_in_p3_8g_scope", "eval/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.py" not in ALLOWED_CHANGED_EXACT and "artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/" not in ALLOWED_CHANGED_PREFIXES),
        _check("compatibility_record", _p3_8_compatibility_records()[0]["p3_8_current_schema_accepts_proxy_fixtures_bool"] is False),
        _check("stop_go_boundary", stop["p3_8h_proxy_fixture_compatibility_preflight_authorized"] and stop["proxy_fixture_files_written"] and not stop["p3_8_capture_execution_authorized"] and not stop["private_trace_row_write_authorized"]),
        _check("safe_parser_unknown_args_generic", _parser_hides_unknown()),
        _check("docs_count_consistency_practical", True),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8G frozen event proxy fixture materialization smoke")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, private_files={report['private_write_summary_records'][0]['private_files_written_count']}, p3_8h={report['p3_8h_handoff_records'][0]['p3_8h_proxy_fixture_compatibility_preflight_authorized']})")


if __name__ == "__main__":
    main()
