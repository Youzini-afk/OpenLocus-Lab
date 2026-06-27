#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re
import time
from pathlib import Path
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_trace_gap_audit.v1"
GENERATED_BY = "eval/bea_v1_trace_gap_audit.py"
CLAIM_LEVEL = "bea_v1_trace_gap_audit_only"
MODE = "bea_v1_trace_gap_audit"
PHASE = "BEA-v1-P0-1"

DEFAULT_OUT = Path("artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json")
DEFAULT_FD1 = Path("artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json")
DEFAULT_P1 = Path("artifacts/bea_v1_p1_actionability_audit/bea_v1_p1_actionability_audit_report.json")
DEFAULT_FD2A1 = Path("artifacts/bea_fd2a1_failure_attribution/bea_fd2a1_failure_attribution_replay_report.json")
DEFAULT_P4L = Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json")
DEFAULT_N2 = Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json")
DEFAULT_N3 = Path("artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/bea_v1_n3_extra_depth_merge_order_design_simulation_report.json")

STATUSES = (
    "trace_gap_audit_pass",
    "no_go_trace_gap_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

TRACE_FIELD_SPECS: dict[str, dict[str, str]] = {
    "same_file_redundancy_trace": {
        "action_layer": "setwise_packer_redundancy",
        "required_for": "duplicate_waste_and_marginal_pack_utility",
        "risk_class": "mechanism_blind_spot",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus source_language_bucket plus duplicate_pressure_bucket plus action_arm plus topk_file_diversity_bucket",
    },
    "risk_penalty_trace": {
        "action_layer": "file_selector_or_risk_accounting",
        "required_for": "detect_gold_removed_by_risk_penalty_without_treating_risk_as_relevance",
        "risk_class": "mechanism_blind_spot",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus risk_class plus removed_gold_bucket plus replacement_bucket plus action_arm",
    },
    "support_link_trace": {
        "action_layer": "conditional_support_expansion",
        "required_for": "target_support_counterfactual_and_support_marginal_utility",
        "risk_class": "label_absent",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus support_relation_bucket plus target_hit_bucket plus support_hit_bucket plus conjunction_bucket",
    },
    "ordered_prefix_stop_trace": {
        "action_layer": "action_scheduler",
        "required_for": "stop_decision_counterfactual_and_early_stop_diagnosis",
        "risk_class": "trace_insufficient",
        "priority": "P1",
        "minimum_public_shape": "anonymous_record_id plus arm_name plus stop_reason plus prefix_cost_bucket plus marginal_gain_bucket",
    },
    "action_cost_trace": {
        "action_layer": "action_scheduler",
        "required_for": "scheduler_dataset_export_and_cost_aware_policy_comparison",
        "risk_class": "partially_private_only",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus state_bucket plus action_arm plus latency_bucket plus pool_delta_bucket plus hard_cap_bucket",
    },
    "rank_pack_trace": {
        "action_layer": "rank_pack_materialization",
        "required_for": "rank_blocker_and_pack_budget_actionability",
        "risk_class": "sanitized_available",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus rank_bucket plus blocker_bucket plus topk_recovery_bucket plus materializable_bucket",
    },
    "merge_order_sim_trace": {
        "action_layer": "rank_pack_materialization",
        "required_for": "extra_depth_merge_order_design_review",
        "risk_class": "sanitized_available",
        "priority": "P0",
        "minimum_public_shape": "anonymous_record_id plus sim_arm plus recovery_bucket plus retention_bucket plus duplicate_pressure_delta_bucket",
    },
}

FD1_CATEGORY_TRACE_FIELDS = {
    "redundant_same_file_candidates": "same_file_redundancy_trace",
    "risk_penalty_removed_gold": "risk_penalty_trace",
    "missing_support_candidate": "support_link_trace",
    "support_selected_without_target": "support_link_trace",
    "target_selected_without_support": "support_link_trace",
    "early_stop_too_early": "ordered_prefix_stop_trace",
    "budget_spent_on_low_marginal_gain": "action_cost_trace",
    "latency_without_quality_gain": "action_cost_trace",
    "correct_file_wrong_span": "rank_pack_trace",
    "gold_file_absent": "action_cost_trace",
    "gold_span_absent": "rank_pack_trace",
    "too_many_anchor_slots": "rank_pack_trace",
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "exact_path", "private_path", "private_dir", "trace_path",
    "start_line", "end_line", "line_range", "span", "spans", "exact_span",
    "gold", "gold_paths", "gold_lines", "gold_spans", "gold_labels",
    "candidate", "candidates", "candidate_list", "candidate_paths", "candidate_order",
    "rank", "score", "scores", "first_gold_rank", "candidate_rank",
    "raw", "raw_trace", "raw_prompt", "raw_response", "provider_payload",
    "snippet", "snippets", "content", "content_lines", "file_content_lines",
    "text", "raw_text", "content_sha", "task_id", "row_id", "repo_name",
    "repo_slug", "repo_url", "base_commit", "private_record_id", "record_ids",
})

SAFE_VALUE_KEYS = frozenset({
    "schema_version", "generated_by", "generated_at", "claim_level", "status", "mode", "phase",
    "failure_reason_category", "artifact_key", "artifact_status", "artifact_schema", "trace_field",
    "trace_availability", "action_layer", "required_for", "risk_class", "priority", "source_phase",
    "source_status", "source_schema", "category", "category_availability", "minimum_public_shape",
    "publication_boundary", "next_step", "evidence_basis", "gate", "threshold_relation",
    "stop_go_decision", "stop_go_reason", "authorization", "input_artifact", "field_name",
})


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    hex_re = re.compile(r"\b[0-9a-f]{64}\b", re.I)

    def walk(o: Any, pth: str = "$") -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_s = str(key)
                sub = f"{pth}.{key_s}"
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "path": sub})
                walk(value, sub)
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                walk(value, f"{pth}[{idx}]")
        elif isinstance(o, str):
            last = pth.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if line_re.search(o):
                violations.append({"category": "line_range_value", "path": pth})
            if path_re.search(o):
                violations.append({"category": "path_like_value", "path": pth})
            if hex_re.search(o):
                violations.append({"category": "hex_digest_value", "path": pth})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": key, "count": value} for key, value in sorted(counts.items())],
    }


def _availability_by_category(fd1: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    totals: dict[str, int] = defaultdict(int)
    for row in fd1.get("availability_records", []):
        if not isinstance(row, dict):
            continue
        cat = str(row.get("category", "") or "")
        avail = str(row.get("category_availability", "") or "")
        count = int(row.get("record_count", 0) or 0)
        if cat and avail:
            grouped[cat][avail] += count
            totals[cat] += count
    out: dict[str, dict[str, Any]] = {}
    for cat, counter in grouped.items():
        dominant = counter.most_common(1)[0][0] if counter else "unknown"
        out[cat] = {"dominant": dominant, "availability_counts": dict(counter), "record_count": totals[cat]}
    return out


def _status_from_availability(availability: str, trace_field: str, supporting_artifacts: dict[str, dict[str, Any]]) -> str:
    if availability == "unavailable_missing_trace":
        return "missing_trace"
    if availability == "unavailable_no_support_label":
        return "missing_label"
    if trace_field == "rank_pack_trace" and supporting_artifacts.get("n2", {}).get("sanitized_records", 0) > 0:
        return "sanitized_available"
    if trace_field == "merge_order_sim_trace" and supporting_artifacts.get("n3", {}).get("sanitized_records", 0) > 0:
        return "sanitized_available"
    if trace_field == "action_cost_trace" and supporting_artifacts.get("p4l", {}).get("private_records", 0) > 0:
        return "private_only_needs_public_export"
    return "aggregate_only_insufficient_for_deep_research"


def _artifact_summary(key: str, art: dict[str, Any], status: str) -> dict[str, Any]:
    private_records = 0
    for row in art.get("private_manifest_records", []):
        if isinstance(row, dict):
            private_records += int(row.get("record_count", 0) or 0)
    sanitized_records = len(art.get("sanitized_analysis_records", [])) if isinstance(art.get("sanitized_analysis_records"), list) else 0
    return {
        "artifact_key": key,
        "artifact_status": status,
        "source_status": str(art.get("status", "") or ""),
        "source_schema": str(art.get("schema_version", "") or ""),
        "sanitized_analysis_record_count": sanitized_records,
        "private_manifest_record_count": private_records,
        "forbidden_scan_status": str(art.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(art.get("forbidden_scan"), dict) else "not_reported"),
    }


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    paths = {
        "fd1": args.fd1_artifact,
        "p1": args.p1_artifact,
        "fd2a1": args.fd2a1_artifact,
        "p4l": args.p4l_artifact,
        "n2": args.n2_artifact,
        "n3": args.n3_artifact,
    }
    loaded: dict[str, dict[str, Any]] = {}
    load_status: dict[str, str] = {}
    for key, path in paths.items():
        loaded[key], load_status[key] = _load_json(path)
    artifact_records = [_artifact_summary(key, loaded[key], load_status[key]) for key in paths]
    supporting = {
        key: {
            "sanitized_records": rec["sanitized_analysis_record_count"],
            "private_records": rec["private_manifest_record_count"],
        }
        for key, rec in zip(paths, artifact_records)
    }
    fd1_ok = load_status["fd1"] == "pass" and loaded["fd1"].get("status") == "bea_fd1_decomposition_pass"
    p1_ok = load_status["p1"] == "pass" and loaded["p1"].get("status") == "no_go_retrieval_availability_limit"
    n2_ok = load_status["n2"] == "pass" and loaded["n2"].get("status") == "n2_rank_pack_actionability_decomposition_pass"
    n3_ok = load_status["n3"] == "pass" and loaded["n3"].get("status") == "n3_merge_order_design_inconclusive"
    fd1_availability = _availability_by_category(loaded["fd1"])
    trace_rows: list[dict[str, Any]] = []
    sanitized_rows: list[dict[str, Any]] = []
    for idx, category in enumerate(sorted(FD1_CATEGORY_TRACE_FIELDS)):
        field = FD1_CATEGORY_TRACE_FIELDS[category]
        spec = TRACE_FIELD_SPECS[field]
        availability = str(fd1_availability.get(category, {}).get("dominant", "unknown"))
        trace_status = _status_from_availability(availability, field, supporting)
        record_count = int(fd1_availability.get(category, {}).get("record_count", 0) or 0)
        row = {
            "category": category,
            "trace_field": field,
            "trace_availability": trace_status,
            "action_layer": spec["action_layer"],
            "required_for": spec["required_for"],
            "risk_class": spec["risk_class"],
            "priority": spec["priority"],
            "record_count": record_count,
            "minimum_public_shape": spec["minimum_public_shape"],
            "publication_boundary": "scanner_validated_sanitized_rows_without_source_linkable_payloads",
            "next_step": "export_or_preserve_trace_before_new_policy_experiment" if trace_status != "sanitized_available" else "reuse_existing_sanitized_rows",
            "evidence_basis": availability,
        }
        trace_rows.append(row)
        sanitized_rows.append({
            "anonymous_local_id": f"tg{idx:05d}",
            "category": category,
            "trace_field": field,
            "trace_availability": trace_status,
            "action_layer": spec["action_layer"],
            "required_for": spec["required_for"],
            "risk_class": spec["risk_class"],
            "priority": spec["priority"],
            "publication_boundary": "sanitized_per_gap_record",
        })
    counts = Counter(row["trace_availability"] for row in trace_rows)
    priority_counts = Counter(row["priority"] for row in trace_rows if row["trace_availability"] != "sanitized_available")
    field_counts = Counter(row["trace_field"] for row in trace_rows if row["trace_availability"] != "sanitized_available")
    status = "trace_gap_audit_pass" if fd1_ok and p1_ok and n2_ok and n3_ok and checks and all(c["passed"] for c in checks) else "no_go_trace_gap_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "trace_gap_audit_pass" else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": bool(checks and all(c["passed"] for c in checks)),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": artifact_records,
        "trace_gap_records": trace_rows,
        "sanitized_analysis_records": sanitized_rows,
        "trace_availability_summary_records": [
            {"trace_availability": key, "count": value} for key, value in sorted(counts.items())
        ],
        "priority_gap_summary_records": [
            {"priority": key, "count": value} for key, value in sorted(priority_counts.items())
        ],
        "trace_field_gap_summary_records": [
            {"trace_field": key, "count": value} for key, value in sorted(field_counts.items())
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "trace_gaps_are_now_explicit_and_do_not_authorize_policy_implementation" if status == "trace_gap_audit_pass" else "required_inputs_unavailable",
            "authorization": "actionability_matrix_and_scheduler_dataset_export_only",
            "p5_authorized": False,
            "v1_a_authorized": False,
            "selector_or_reranker_authorized": False,
            "implementation_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "downstream_value_claimed": False,
        }],
        "gate_records": [
            {"gate": "fd1_pass_artifact_available", "passed": fd1_ok, "threshold_relation": "boolean", "value": int(fd1_ok), "threshold_value": 1},
            {"gate": "p1_actionability_audit_available", "passed": p1_ok, "threshold_relation": "boolean", "value": int(p1_ok), "threshold_value": 1},
            {"gate": "n2_rank_pack_sanitized_rows_available", "passed": n2_ok, "threshold_relation": "boolean", "value": int(n2_ok), "threshold_value": 1},
            {"gate": "n3_merge_order_sanitized_rows_available", "passed": n3_ok, "threshold_relation": "boolean", "value": int(n3_ok), "threshold_value": 1},
        ],
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
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("all_fd1_categories_have_trace_fields", len(FD1_CATEGORY_TRACE_FIELDS) == 12),
        _check("trace_specs_cover_category_map", all(v in TRACE_FIELD_SPECS for v in FD1_CATEGORY_TRACE_FIELDS.values())),
        _check("scanner_rejects_path_key", _scan_summary({"path": "x"})["status"] == "fail"),
        _check("scanner_accepts_sanitized_shape", _scan_summary({"trace_field": "support_link_trace", "priority": "P0"})["status"] == "pass"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 trace gap audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fd1-artifact", type=Path, default=DEFAULT_FD1)
    parser.add_argument("--p1-artifact", type=Path, default=DEFAULT_P1)
    parser.add_argument("--fd2a1-artifact", type=Path, default=DEFAULT_FD2A1)
    parser.add_argument("--p4l-artifact", type=Path, default=DEFAULT_P4L)
    parser.add_argument("--n2-artifact", type=Path, default=DEFAULT_N2)
    parser.add_argument("--n3-artifact", type=Path, default=DEFAULT_N3)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, trace_gaps={len(report['trace_gap_records'])})")


if __name__ == "__main__":
    main()
