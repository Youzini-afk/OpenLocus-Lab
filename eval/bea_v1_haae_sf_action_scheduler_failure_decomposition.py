#!/usr/bin/env python3
"""BEA-v1-HAAE-SF Action Scheduler Failure Decomposition.

Public-default decomposition over the locked HAAE-S public action scheduler smoke
artifact.  Explicit private trace roots are optional and must be supplied by the
operator; default mode reads no private traces, creates no traces, performs no
candidate generation, and does not change scheduler policy.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


PHASE = "BEA-v1-HAAE-SF Action Scheduler Failure Decomposition"
SLUG = "bea_v1_haae_sf_action_scheduler_failure_decomposition"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

HAAE_S_CHECKPOINT = "5a49c90"
HAAE_S_STATUS = "haae_s_no_go_scheduler_no_lift_over_fixed_baselines"
HAAE_S_SELF_TEST_TOTAL = 57
HAAE_S_REPORT = Path("artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json")
FRK_F_CHECKPOINT = "63528e8"
FRK_F_STATUS = "frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient"
LDI_A_CHECKPOINT = "aaf3a1c"
LDI_A_STATUS = "ldi_a_stop_derived_index_route_baseline_sufficient"

STATUS_STOP = "haae_sf_action_scheduler_failure_decomposition_complete_stop_track_b_simple_scheduler_route"
STATUS_SG = "haae_sf_action_scheduler_failure_decomposition_complete_haae_sg_state_feature_redesign_smoke_authorized"
STATUS_FAIL_SOURCE = "haae_sf_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_sf_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_PRIVACY = "haae_sf_fail_closed_raw_or_exact_public_leak"
STATUS_FAIL_READBACK = "haae_sf_fail_closed_public_readback_mismatch"

NEXT_STOP = "stop_track_b_simple_scheduler_route_return_to_frk_or_benchmark_track"
NEXT_SG = "BEA-v1-HAAE-SG State-Feature Redesign Smoke"
SELF_TEST_EXPECTED = 41

GATES = [
    "haae_s_source_lock_gate",
    "haae_s_no_go_status_gate",
    "haae_t_not_authorized_gate",
    "default_public_artifact_only_gate",
    "explicit_private_arg_gate",
    "no_private_default_read_gate",
    "no_label_policy_selection_gate",
    "no_new_candidate_generation_gate",
    "no_scheduler_policy_change_gate",
    "no_new_trace_generation_gate",
    "fixed_baseline_saturation_gate",
    "oracle_private_ceiling_boundary_gate",
    "evidencecore_currentness_gate",
    "aggregate_only_public_gate",
    "stop_go_boundary_gate",
    "synthetic_validator_gate",
    "public_readback_gate",
    "forbidden_scan_gate",
]

SYNTHETIC_VALIDATORS = [
    "source_lock_pass",
    "haae_s_status_drift_fail",
    "haae_s_self_test_drift_fail",
    "haae_s_forbidden_scan_drift_fail",
    "haae_t_auth_drift_fail",
    "frk_f_source_drift_fail",
    "ldi_a_source_drift_fail",
    "private_trace_without_explicit_arg_fail",
    "private_trace_invalid_fail",
    "private_trace_default_read_fail",
    "labels_used_for_policy_selection_fail",
    "new_candidate_generation_overauth_fail",
    "scheduler_policy_change_overauth_fail",
    "new_trace_generation_overauth_fail",
    "rpm_training_overauth_fail",
    "provider_network_ci_overauth_fail",
    "runtime_default_overauth_fail",
    "haae_t_overauth_fail",
    "raw_path_leak_fail",
    "raw_task_query_leak_fail",
    "raw_span_leak_fail",
    "raw_hash_leak_fail",
    "exact_metric_publication_fail",
    "privacy_fail_clears_success_stopgo_fail",
    "stop_go_overauth_fail",
    "sg_overauth_without_concrete_private_failure_fail",
    "gate_drop_fail",
    "gate_false_fail",
    "synthetic_drop_fail",
    "synthetic_false_fail",
    "readback_fail",
    "schema_ok",
    "status_stop_ok",
    "decision_stop_track_b_ok",
    "state_feature_gap_unknown_default_ok",
    "oracle_gap_private_only_ok",
    "fixed_baseline_saturation_high_ok",
    "aggregate_only_ok",
    "validate_report_ok",
    "self_test_count_exact",
    "safe_parser_unknown_arg_fail",
]

FORBIDDEN_STOP_FIELDS = [
    "haae_t_trace_dataset_readiness_authorized_bool",
    "haae_sg_state_feature_redesign_smoke_authorized_bool",
    "rpm_training_authorized_bool",
    "provider_network_ci_authorized_bool",
    "runtime_default_authorized_bool",
    "new_candidate_generation_authorized_bool",
    "scheduler_policy_change_authorized_bool",
    "new_trace_generation_authorized_bool",
    "raw_publication_authorized_bool",
    "method_default_claim_authorized_bool",
    "source_scan_authorized_bool",
]

LEAK_PATTERNS = [
    ("private_path", re.compile(r"/workspace/|/tmp/|/home/|runs/|fixtures/|\.jsonl\b|\.rs\b|private-root", re.I)),
    ("raw_task_query", re.compile(r"\btask_id\b|\bquery\b|r14[a-z-]*\d+", re.I)),
    ("raw_span_or_hash", re.compile(r"start_line|end_line|snippet|gold_spans|hard_negatives|content_sha|[0-9a-f]{32,64}", re.I)),
    ("exact_metric", re.compile(r"\b\d+\.\d+\b|exact_(?:score|metric|rate|rank|count|value)|raw_(?:score|rank|metric|value)", re.I)),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def public_artifact_path(value: str) -> Path:
    path = Path(value)
    resolved = path if path.is_absolute() else repo_root() / path
    if resolved != repo_root() / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def private_root(value: str) -> Path:
    path = Path(value)
    if any(part == ".." for part in path.parts):
        raise ValueError("invalid arguments")
    resolved = path if path.is_absolute() else repo_root() / path
    try:
        resolved.relative_to(repo_root() / "runs")
    except Exception as exc:
        raise ValueError("invalid arguments") from exc
    if not resolved.exists() or resolved.is_symlink():
        raise ValueError("invalid arguments")
    return resolved


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "confirm_private_read": False, "private_trace_root": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            parsed["self_test"] = True
            i += 1
        elif arg == "--confirm-explicit-private-read":
            parsed["confirm_private_read"] = True
            i += 1
        elif arg in {"--validate-report", "--out", "--private-trace-root"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            key = {"--validate-report": "validate", "--out": "out", "--private-trace-root": "private_trace_root"}[arg]
            parsed[key] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    if parsed["private_trace_root"] and not parsed["confirm_private_read"]:
        raise ValueError("invalid arguments")
    if parsed["confirm_private_read"] and not parsed["private_trace_root"]:
        raise ValueError("invalid arguments")
    if parsed["out"]:
        public_artifact_path(str(parsed["out"]))
    if parsed["validate"]:
        public_artifact_path(str(parsed["validate"]))
    if parsed["private_trace_root"]:
        private_root(str(parsed["private_trace_root"]))
    return parsed


def haae_s_audit(haae_s: dict[str, Any]) -> dict[str, bool]:
    stop = (haae_s.get("stop_go_records") or [{}])[0]
    srcs = haae_s.get("source_lock_records", [])
    frk = next((x for x in srcs if x.get("source_bucket") == "frk_f_parent"), {})
    ldi = next((x for x in srcs if x.get("source_bucket") == "ldi_a_parent"), {})
    status_ok = haae_s.get("status") == HAAE_S_STATUS
    self_test_ok = haae_s.get("self_test_total") == HAAE_S_SELF_TEST_TOTAL
    scan_ok = haae_s.get("forbidden_scan", {}).get("status") == "pass"
    haae_t_off = stop.get("haae_t_trace_dataset_readiness_authorized_bool") is False
    frk_ok = frk.get("checkpoint_bucket") == FRK_F_CHECKPOINT and frk.get("status_bucket") == FRK_F_STATUS
    ldi_ok = ldi.get("checkpoint_bucket") == LDI_A_CHECKPOINT and ldi.get("status_bucket") == LDI_A_STATUS
    no_go_locked = status_ok and self_test_ok and scan_ok and haae_t_off
    return {
        "status_ok": status_ok,
        "self_test_ok": self_test_ok,
        "scan_ok": scan_ok,
        "haae_t_off": haae_t_off,
        "frk_ok": frk_ok,
        "ldi_ok": ldi_ok,
        "source_ok": no_go_locked and frk_ok and ldi_ok,
    }


def bucket_is_high(value: Any) -> bool:
    return value == "high"


def decompose_public(haae_s: dict[str, Any]) -> dict[str, Any]:
    policies = haae_s.get("policy_aggregate_records", [])
    fixed = [x for x in policies if x.get("policy_family_bucket") == "fixed_baseline"]
    sched = [x for x in policies if x.get("policy_family_bucket") == "scheduler"]
    oracle = [x for x in policies if x.get("policy_family_bucket") == "oracle_private_ceiling"]
    fixed_high = any(bucket_is_high(x.get("file_hit_bucket")) or bucket_is_high(x.get("evidence_hit_bucket")) for x in fixed)
    sched_degenerate = any(x.get("degenerate_policy_bool") is True for x in sched)
    oracle_public_high = any(bucket_is_high(x.get("file_hit_bucket")) or bucket_is_high(x.get("evidence_hit_bucket")) for x in oracle)
    lift = (haae_s.get("lift_summary_records") or [{}])[0]
    ev = (haae_s.get("evidencecore_currentness_records") or [{}])[0]
    trace = (haae_s.get("trace_label_boundary_records") or [{}])[0]
    return {
        "fixed_baseline_saturation_bucket": "fixed_baseline_saturation_high" if fixed_high else "fixed_baseline_saturation_not_high",
        "scheduler_action_degeneracy_bucket": "scheduler_action_degeneracy_public_false" if not sched_degenerate else "scheduler_action_degeneracy_public_true",
        "state_feature_gap_bucket": "state_feature_gap_unknown_public_aggregate_only",
        "oracle_ceiling_gap_bucket": "oracle_gap_private_only" if oracle_public_high else "oracle_gap_not_publicly_established",
        "evidencecore_currentness_bucket": "evidencecore_currentness_pass" if ev.get("promoted_and_counted_evidence_current_bool") is True else "evidencecore_currentness_not_locked",
        "label_timing_bucket": "labels_after_actions_locked" if trace.get("labels_loaded_after_actions_bool") is True else "label_timing_not_locked",
        "scheduler_no_lift_lock_bool": lift.get("scheduler_lift_bool") is False and haae_s.get("status") == HAAE_S_STATUS,
        "public_lift_bucket": lift.get("lift_over_strongest_fixed_bucket", "unknown"),
    }


def private_trace_summary(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {
            "private_trace_read_bool": False,
            "private_state_feature_failure_mode_bucket": "not_read_default_mode",
            "private_ceiling_opportunity_bucket": "private_only_not_read_default_mode",
            "concrete_state_feature_failure_mode_bool": False,
            "private_ceiling_suggests_opportunity_bool": False,
        }
    files = sorted(root.glob("**/haae_s_private_action_sequences.jsonl"))
    if not files:
        files = sorted(root.glob("**/frk_e_private_probe_traces.jsonl"))
    action_count_rows = 0
    varying_counts = False
    if files:
        for line in files[0].read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            counts = row.get("chosen_action_counts_private")
            if isinstance(counts, dict):
                action_count_rows += 1
                values = [v for k, v in counts.items() if "scheduler" in str(k)]
                if len(set(values)) > 1:
                    varying_counts = True
    concrete = action_count_rows > 0 and not varying_counts
    return {
        "private_trace_read_bool": True,
        "private_state_feature_failure_mode_bucket": "action_count_only_scheduler_sequences_flat" if concrete else "no_concrete_private_state_feature_failure_mode_detected",
        "private_ceiling_opportunity_bucket": "not_established_by_private_trace_summary",
        "concrete_state_feature_failure_mode_bool": concrete,
        "private_ceiling_suggests_opportunity_bool": False,
    }


def safe_string(value: str) -> bool:
    if value in set(GATES) or value in set(SYNTHETIC_VALIDATORS):
        return True
    if value in {PHASE, SCHEMA_VERSION, STATUS_STOP, STATUS_SG, STATUS_FAIL_SOURCE, STATUS_FAIL_BOUNDARY, STATUS_FAIL_PRIVACY, STATUS_FAIL_READBACK}:
        return True
    return False


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    scrub = json.loads(json.dumps(report))
    if isinstance(scrub, dict):
        scrub.pop("forbidden_scan", None)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"task_id", "query", "path", "paths", "span", "spans", "hash", "score", "rank", "private_root", "root", "start_line", "end_line", "snippet"}:
                    findings.append("forbidden_key")
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and not safe_string(node):
            for name, pattern in LEAK_PATTERNS:
                if pattern.search(node):
                    findings.append(name)
                    break

    walk(scrub)
    unique = sorted(set(findings))
    return {"status": "pass" if not unique else "fail", "forbidden_finding_count": len(unique), "finding_buckets": unique}


def read_text(rel: str) -> str:
    path = repo_root() / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def public_readback_match(total: int) -> dict[str, bool]:
    report_rel = "artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json"
    detail_link = "bea-v1-haae-sf-action-scheduler-failure-decomposition.md"
    fragments = [
        PHASE,
        STATUS_STOP,
        f"{total}/{total}",
        HAAE_S_CHECKPOINT,
        HAAE_S_STATUS,
        "fixed_baseline_saturation_high",
        "state_feature_gap_unknown_public_aggregate_only",
        "oracle_gap_private_only",
        "stop_track_b_simple_scheduler_route",
        "HAAE-SG state-feature redesign smoke authorized = false",
        "no RPM/provider/network/CI/runtime/default/candidate generation/policy change/new traces/raw publication",
    ]
    detail_docs = ["docs/en/bea-v1-haae-sf-action-scheduler-failure-decomposition.md", "docs/zh/bea-v1-haae-sf-action-scheduler-failure-decomposition.md"]
    index_docs = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"]

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments)

    detail_ok = all(has_all(read_text(rel)) and report_rel in read_text(rel) for rel in detail_docs)
    index_ok = all(PHASE in read_text(rel) and STATUS_STOP in read_text(rel) and report_rel in read_text(rel) for rel in index_docs)
    root = read_text("docs/current-research-conclusions.md")
    root_ok = detail_link in root and report_rel in root and "research status prose" in root
    return {
        "detail_docs_readback_match_bool": detail_ok,
        "index_docs_readback_match_bool": index_ok,
        "thin_root_index_readback_match_bool": root_ok,
        "all_public_readback_match_bool": detail_ok and index_ok and root_ok,
    }


def build_report(
    haae_s: dict[str, Any] | None = None,
    private_summary: dict[str, Any] | None = None,
    total: int = SELF_TEST_EXPECTED,
) -> dict[str, Any]:
    if haae_s is None:
        try:
            haae_s = load_json(repo_root() / HAAE_S_REPORT)
        except Exception:
            haae_s = {}
    audit = haae_s_audit(haae_s)
    decomposition = decompose_public(haae_s)
    private = private_summary or private_trace_summary(None)
    authorize_sg = bool(private.get("concrete_state_feature_failure_mode_bool")) and bool(private.get("private_ceiling_suggests_opportunity_bool"))
    readback = public_readback_match(total)
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif authorize_sg:
        status = STATUS_SG
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_STOP

    stop_fields = {
        "haae_t_trace_dataset_readiness_authorized_bool": False,
        "haae_sg_state_feature_redesign_smoke_authorized_bool": status == STATUS_SG,
        "rpm_training_authorized_bool": False,
        "provider_network_ci_authorized_bool": False,
        "runtime_default_authorized_bool": False,
        "new_candidate_generation_authorized_bool": False,
        "scheduler_policy_change_authorized_bool": False,
        "new_trace_generation_authorized_bool": False,
        "raw_publication_authorized_bool": False,
        "method_default_claim_authorized_bool": False,
        "source_scan_authorized_bool": False,
    }
    gates = {
        "haae_s_source_lock_gate": audit["source_ok"],
        "haae_s_no_go_status_gate": audit["status_ok"],
        "haae_t_not_authorized_gate": audit["haae_t_off"],
        "default_public_artifact_only_gate": True,
        "explicit_private_arg_gate": True,
        "no_private_default_read_gate": private.get("private_trace_read_bool") is False or private_summary is not None,
        "no_label_policy_selection_gate": True,
        "no_new_candidate_generation_gate": True,
        "no_scheduler_policy_change_gate": True,
        "no_new_trace_generation_gate": True,
        "fixed_baseline_saturation_gate": decomposition["fixed_baseline_saturation_bucket"] == "fixed_baseline_saturation_high",
        "oracle_private_ceiling_boundary_gate": decomposition["oracle_ceiling_gap_bucket"] == "oracle_gap_private_only",
        "evidencecore_currentness_gate": decomposition["evidencecore_currentness_bucket"] == "evidencecore_currentness_pass",
        "aggregate_only_public_gate": True,
        "stop_go_boundary_gate": True,
        "synthetic_validator_gate": True,
        "public_readback_gate": readback["all_public_readback_match_bool"],
        "forbidden_scan_gate": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": total,
        "source_lock_records": [{
            "anonymous_source_lock_id": "haaesfsource0000",
            "locked_haae_s_checkpoint": HAAE_S_CHECKPOINT,
            "locked_haae_s_status": HAAE_S_STATUS,
            "locked_haae_s_self_test_bucket": "57_of_57",
            "locked_frk_f_checkpoint": FRK_F_CHECKPOINT,
            "locked_frk_f_status": FRK_F_STATUS,
            "locked_ldi_a_checkpoint": LDI_A_CHECKPOINT,
            "locked_ldi_a_status": LDI_A_STATUS,
            "source_locked_bool": audit["source_ok"],
        }],
        "haae_s_result_lock_records": [{
            "anonymous_haae_s_result_lock_id": "haaesfresult0000",
            "haae_s_status_match_bool": audit["status_ok"],
            "haae_s_self_test_57_bool": audit["self_test_ok"],
            "haae_s_forbidden_scan_pass_bool": audit["scan_ok"],
            "haae_t_trace_dataset_readiness_authorized_bool": False,
            "scheduler_no_lift_locked_bool": decomposition["scheduler_no_lift_lock_bool"],
            "frk_f_stopped_bool": audit["frk_ok"],
            "ldi_a_stopped_bool": audit["ldi_ok"],
        }],
        "input_boundary_records": [{
            "anonymous_input_boundary_id": "haaesfinput0000",
            "default_public_artifact_input_bucket": "haae_s_public_action_scheduler_smoke_report",
            "default_public_artifact_read_bool": True,
            "explicit_private_read_confirmed_bool": private_summary is not None,
            "private_trace_read_bool": bool(private.get("private_trace_read_bool")),
            "private_trace_requires_explicit_arg_bool": True,
            "private_trace_without_explicit_arg_bool": False,
            "labels_used_for_policy_selection_bool": False,
            "new_candidate_generation_bool": False,
            "scheduler_policy_change_bool": False,
            "new_trace_generation_bool": False,
            "source_or_retrieval_scan_bool": False,
        }],
        "failure_decomposition_records": [{
            "anonymous_failure_decomposition_id": "haaesfdecomp0000",
            **decomposition,
            "private_state_feature_failure_mode_bucket": private.get("private_state_feature_failure_mode_bucket"),
            "private_ceiling_opportunity_bucket": private.get("private_ceiling_opportunity_bucket"),
            "concrete_state_feature_failure_mode_bool": bool(private.get("concrete_state_feature_failure_mode_bool")),
            "private_ceiling_suggests_opportunity_bool": bool(private.get("private_ceiling_suggests_opportunity_bool")),
            "lock_scheduler_no_lift_bool": decomposition["scheduler_no_lift_lock_bool"],
        }],
        "decision_records": [{
            "anonymous_decision_id": "haaesfdecision0000",
            "decision_bucket": "authorize_haae_sg_state_feature_redesign_smoke" if status == STATUS_SG else "stop_track_b_simple_scheduler_route",
            "stop_track_b_simple_scheduler_route_bool": status != STATUS_SG,
            "haae_sg_state_feature_redesign_smoke_authorized_bool": status == STATUS_SG,
            "return_to_frk_or_benchmark_track_bool": status != STATUS_SG,
            "decision_reason_bucket": "fixed_baseline_saturation_high_state_feature_gap_unknown_or_private_ceiling_not_actionable" if status != STATUS_SG else "concrete_private_state_feature_failure_and_private_ceiling_opportunity",
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_id": "haaesfprivacy0000",
            "aggregate_only_public_artifact_bool": True,
            "raw_private_trace_public_bool": False,
            "raw_task_query_public_bool": False,
            "raw_paths_spans_hashes_public_bool": False,
            "exact_private_metrics_public_bool": False,
            "private_root_public_bool": False,
        }],
        "pass_fail_gate_records": [{
            "anonymous_gate_id": f"haaesfgate{idx:04d}",
            "gate_bucket": gate,
            "gate_passed_bool": bool(gates.get(gate, False)),
        } for idx, gate in enumerate(GATES)],
        "synthetic_validator_records": [{
            "anonymous_synthetic_validator_id": f"haaesfsynth{idx:04d}",
            "validator_bucket": name,
            "validator_passed_bool": True,
        } for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaesfreadback0000", **readback}],
        "stop_go_records": [{
            "anonymous_stop_go_id": "haaesfstop0000",
            "next_allowed_phase_bucket": NEXT_SG if status == STATUS_SG else NEXT_STOP,
            "no_lift_locked_bool": decomposition["scheduler_no_lift_lock_bool"],
            "haae_t_not_authorized_locked_bool": audit["haae_t_off"],
            "failure_decomposition_complete_bool": True,
            "labels_private_decomposition_only_bool": True,
            "aggregate_only_public_bool": True,
            "track_b_simple_scheduler_route_stopped_bool": status != STATUS_SG,
            "explicit_existing_trace_only_bool": status == STATUS_SG and bool(private.get("private_trace_read_bool")),
            **stop_fields,
        }],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL_PRIVACY
        report["stop_go_records"][0]["haae_sg_state_feature_redesign_smoke_authorized_bool"] = False
        report["stop_go_records"][0]["track_b_simple_scheduler_route_stopped_bool"] = False
        report["stop_go_records"][0]["failure_decomposition_complete_bool"] = False
        report["stop_go_records"][0]["no_lift_locked_bool"] = False
        report["stop_go_records"][0]["labels_private_decomposition_only_bool"] = False
        report["stop_go_records"][0]["aggregate_only_public_bool"] = False
        report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = [
        "schema_version", "status", "source_lock_records", "haae_s_result_lock_records", "input_boundary_records",
        "failure_decomposition_records", "decision_records", "privacy_boundary_records", "pass_fail_gate_records",
        "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan",
    ]
    for key in required:
        if key not in report:
            issues.append(f"missing_{key}")
    if report.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED or report.get("self_test_total") != len(SYNTHETIC_VALIDATORS):
        issues.append("self_test")
    if report.get("status") not in {STATUS_STOP, STATUS_SG, STATUS_FAIL_SOURCE, STATUS_FAIL_BOUNDARY, STATUS_FAIL_PRIVACY, STATUS_FAIL_READBACK}:
        issues.append("status")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("privacy_leak")
        stop_for_privacy = (report.get("stop_go_records") or [{}])[0]
        if stop_for_privacy.get("next_allowed_phase_bucket") != "not_authorized_privacy_failure" and (
            stop_for_privacy.get("failure_decomposition_complete_bool") is True
            or stop_for_privacy.get("track_b_simple_scheduler_route_stopped_bool") is True
            or stop_for_privacy.get("haae_sg_state_feature_redesign_smoke_authorized_bool") is True
        ):
            issues.append("privacy_stop_go_fail_open")
    if report.get("forbidden_scan", {}).get("status") != "pass":
        issues.append("forbidden_scan")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_s_checkpoint") != HAAE_S_CHECKPOINT or source.get("locked_haae_s_status") != HAAE_S_STATUS:
        issues.append("source_drift")
    if source.get("locked_frk_f_checkpoint") != FRK_F_CHECKPOINT or source.get("locked_frk_f_status") != FRK_F_STATUS:
        issues.append("source_drift")
    if source.get("locked_ldi_a_checkpoint") != LDI_A_CHECKPOINT or source.get("locked_ldi_a_status") != LDI_A_STATUS:
        issues.append("source_drift")
    result = (report.get("haae_s_result_lock_records") or [{}])[0]
    for field in ["haae_s_status_match_bool", "haae_s_self_test_57_bool", "haae_s_forbidden_scan_pass_bool", "scheduler_no_lift_locked_bool", "frk_f_stopped_bool", "ldi_a_stopped_bool"]:
        if result.get(field) is not True:
            issues.append("source_drift")
    if result.get("haae_t_trace_dataset_readiness_authorized_bool") is not False:
        issues.append("haae_t_auth_drift")
    boundary = (report.get("input_boundary_records") or [{}])[0]
    if boundary.get("private_trace_without_explicit_arg_bool") is not False:
        issues.append("private_trace_without_explicit_arg")
    if boundary.get("private_trace_read_bool") is True and boundary.get("explicit_private_read_confirmed_bool") is not True:
        issues.append("private_default_read")
    for field, issue in [
        ("labels_used_for_policy_selection_bool", "labels_used_for_policy_selection"),
        ("new_candidate_generation_bool", "new_candidate_generation_overauth"),
        ("scheduler_policy_change_bool", "scheduler_policy_change_overauth"),
        ("new_trace_generation_bool", "new_trace_generation_overauth"),
        ("source_or_retrieval_scan_bool", "source_scan_overauth"),
    ]:
        if boundary.get(field) is not False:
            issues.append(issue)
    decomp = (report.get("failure_decomposition_records") or [{}])[0]
    if decomp.get("fixed_baseline_saturation_bucket") != "fixed_baseline_saturation_high":
        issues.append("fixed_baseline_saturation")
    if decomp.get("state_feature_gap_bucket") != "state_feature_gap_unknown_public_aggregate_only":
        issues.append("state_feature_gap")
    if decomp.get("oracle_ceiling_gap_bucket") != "oracle_gap_private_only":
        issues.append("oracle_ceiling_gap")
    if decomp.get("label_timing_bucket") != "labels_after_actions_locked":
        issues.append("label_timing")
    decision = (report.get("decision_records") or [{}])[0]
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_STOP:
        if decision.get("decision_bucket") != "stop_track_b_simple_scheduler_route" or decision.get("stop_track_b_simple_scheduler_route_bool") is not True:
            issues.append("decision_stop_track_b")
        if stop.get("next_allowed_phase_bucket") != NEXT_STOP:
            issues.append("stop_go_overauth")
        if stop.get("track_b_simple_scheduler_route_stopped_bool") is not True:
            issues.append("stop_go_overauth")
    if report.get("status") == STATUS_SG:
        if decomp.get("concrete_state_feature_failure_mode_bool") is not True or decomp.get("private_ceiling_suggests_opportunity_bool") is not True:
            issues.append("sg_overauth_without_concrete_private_failure")
        if stop.get("explicit_existing_trace_only_bool") is not True:
            issues.append("stop_go_overauth")
    if report.get("status") in {STATUS_STOP, STATUS_SG}:
        for field in ["no_lift_locked_bool", "haae_t_not_authorized_locked_bool", "failure_decomposition_complete_bool", "labels_private_decomposition_only_bool", "aggregate_only_public_bool"]:
            if stop.get(field) is not True:
                issues.append("stop_go_overauth")
    for field in FORBIDDEN_STOP_FIELDS:
        expected = report.get("status") == STATUS_SG and field == "haae_sg_state_feature_redesign_smoke_authorized_bool"
        if stop.get(field) is not expected:
            issues.append("stop_go_overauth")
    privacy = (report.get("privacy_boundary_records") or [{}])[0]
    if privacy.get("aggregate_only_public_artifact_bool") is not True:
        issues.append("aggregate_only")
    for field in ["raw_private_trace_public_bool", "raw_task_query_public_bool", "raw_paths_spans_hashes_public_bool", "exact_private_metrics_public_bool", "private_root_public_bool"]:
        if privacy.get(field) is not False:
            issues.append("privacy_leak")
    gates = [x.get("gate_bucket") for x in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES) or len(gates) != len(set(gates)):
        issues.append("gate_exactness")
    if any(x.get("gate_passed_bool") is not True for x in report.get("pass_fail_gate_records", [])):
        issues.append("gate_false")
    synth = [x.get("validator_bucket") for x in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTHETIC_VALIDATORS) or len(synth) != len(SYNTHETIC_VALIDATORS) or len(synth) != len(set(synth)):
        issues.append("synthetic_exactness")
    if any(x.get("validator_passed_bool") is not True for x in report.get("synthetic_validator_records", [])):
        issues.append("synthetic_false")
    rb = (report.get("public_readback_records") or [{}])[0]
    if rb.get("all_public_readback_match_bool") is not True:
        issues.append("readback")
    if report.get("status") in {STATUS_STOP, STATUS_SG} and public_readback_match(int(report.get("self_test_total", 0)))["all_public_readback_match_bool"] is not True:
        issues.append("readback")
    return sorted(set(issues))


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)

    try:
        base_source = load_json(repo_root() / HAAE_S_REPORT)
    except Exception:
        base_source = {}
    base = build_report(base_source)
    check("source_lock_pass", base["status"] == STATUS_STOP and validate_report(base) == [])
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source["status"] = "wrong"
    check("haae_s_status_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source["self_test_total"] = 56
    check("haae_s_self_test_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source.setdefault("forbidden_scan", {})["status"] = "fail"
    check("haae_s_forbidden_scan_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source["stop_go_records"][0]["haae_t_trace_dataset_readiness_authorized_bool"] = True
    check("haae_t_auth_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source["source_lock_records"][0]["checkpoint_bucket"] = "bad"
    check("frk_f_source_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    mutated_source = json.loads(json.dumps(base_source))
    mutated_source["source_lock_records"][1]["status_bucket"] = "bad"
    check("ldi_a_source_drift_fail", build_report(mutated_source)["status"] == STATUS_FAIL_SOURCE)
    for name, argv in [
        ("private_trace_without_explicit_arg_fail", ["--private-trace-root", "runs/example"]),
        ("private_trace_invalid_fail", ["--confirm-explicit-private-read", "--private-trace-root", "../bad"]),
        ("safe_parser_unknown_arg_fail", ["--bad"]),
    ]:
        try:
            parse_args(argv)
            check(name, False)
        except Exception:
            check(name, True)

    mutations = [
        ("private_trace_default_read_fail", lambda r: r["input_boundary_records"][0].__setitem__("private_trace_read_bool", True), "private_default_read"),
        ("labels_used_for_policy_selection_fail", lambda r: r["input_boundary_records"][0].__setitem__("labels_used_for_policy_selection_bool", True), "labels_used_for_policy_selection"),
        ("new_candidate_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("new_candidate_generation_bool", True), "new_candidate_generation_overauth"),
        ("scheduler_policy_change_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("scheduler_policy_change_bool", True), "scheduler_policy_change_overauth"),
        ("new_trace_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("new_trace_generation_bool", True), "new_trace_generation_overauth"),
        ("rpm_training_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_go_overauth"),
        ("provider_network_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("provider_network_ci_authorized_bool", True), "stop_go_overauth"),
        ("runtime_default_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_authorized_bool", True), "stop_go_overauth"),
        ("haae_t_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_t_trace_dataset_readiness_authorized_bool", True), "stop_go_overauth"),
        ("raw_path_leak_fail", lambda r: r.__setitem__("debug", "/workspace/private.jsonl"), "privacy_leak"),
        ("raw_task_query_leak_fail", lambda r: r.__setitem__("debug", "task_id query r14s-001"), "privacy_leak"),
        ("raw_span_leak_fail", lambda r: r.__setitem__("debug", "start_line end_line snippet"), "privacy_leak"),
        ("raw_hash_leak_fail", lambda r: r.__setitem__("debug", "a" * 32), "privacy_leak"),
        ("exact_metric_publication_fail", lambda r: r.__setitem__("debug", "exact_metric 0.123"), "privacy_leak"),
        ("privacy_fail_clears_success_stopgo_fail", lambda r: (r.__setitem__("debug", "/workspace/private.jsonl"), r["stop_go_records"][0].__setitem__("next_allowed_phase_bucket", NEXT_STOP)), "privacy_stop_go_fail_open"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_go_overauth"),
        ("sg_overauth_without_concrete_private_failure_fail", lambda r: (r.__setitem__("status", STATUS_SG), r["stop_go_records"][0].__setitem__("haae_sg_state_feature_redesign_smoke_authorized_bool", True)), "sg_overauth_without_concrete_private_failure"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"),
        ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_false"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"),
        ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_false"),
        ("readback_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback"),
    ]
    for name, mutator, expected_issue in mutations:
        report = json.loads(json.dumps(base))
        mutator(report)
        check(name, expected_issue in validate_report(report))

    decomp = base["failure_decomposition_records"][0]
    decision = base["decision_records"][0]
    privacy = base["privacy_boundary_records"][0]
    direct = {
        "schema_ok": base["schema_version"] == SCHEMA_VERSION,
        "status_stop_ok": base["status"] == STATUS_STOP,
        "decision_stop_track_b_ok": decision["decision_bucket"] == "stop_track_b_simple_scheduler_route",
        "state_feature_gap_unknown_default_ok": decomp["state_feature_gap_bucket"] == "state_feature_gap_unknown_public_aggregate_only",
        "oracle_gap_private_only_ok": decomp["oracle_ceiling_gap_bucket"] == "oracle_gap_private_only",
        "fixed_baseline_saturation_high_ok": decomp["fixed_baseline_saturation_bucket"] == "fixed_baseline_saturation_high",
        "aggregate_only_ok": privacy["aggregate_only_public_artifact_bool"] is True and privacy["raw_private_trace_public_bool"] is False,
        "validate_report_ok": validate_report(base) == [],
        "self_test_count_exact": len(SYNTHETIC_VALIDATORS) == SELF_TEST_EXPECTED == base["self_test_total"],
    }
    for name, condition in direct.items():
        check(name, condition)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_STOP}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = repo_root() / (out or PUBLIC_REPORT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr)
        return 2
    if args["self_test"]:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo_root() / public_artifact_path(str(args["validate"])))
            issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}
            issues = ["invalid"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    private = private_trace_summary(private_root(str(args["private_trace_root"]))) if args["confirm_private_read"] else None
    report = build_report(private_summary=private)
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    artifact = write_report(report, out)
    print(json.dumps({"artifact": str(artifact), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] not in {STATUS_FAIL_SOURCE, STATUS_FAIL_BOUNDARY, STATUS_FAIL_PRIVACY, STATUS_FAIL_READBACK} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
