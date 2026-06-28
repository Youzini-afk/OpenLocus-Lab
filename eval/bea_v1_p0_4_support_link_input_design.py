#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import time
from pathlib import Path
from typing import Any, Mapping, NoReturn

import sys

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p0_4_support_link_input_design.v1"
GENERATED_BY = "eval/bea_v1_p0_4_support_link_input_design.py"
CLAIM_LEVEL = "bea_v1_p0_4_support_link_input_design_only"
MODE = "bea_v1_p0_4_support_link_input_design"
PHASE = "BEA-v1-P0-4"

DEFAULT_OUT = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_TRACE_GAP = Path("artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")

STATUSES = (
    "support_link_input_design_pass",
    "no_go_support_link_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SUPPORT_CATEGORIES = (
    "missing_support_candidate",
    "support_selected_without_target",
    "target_selected_without_support",
)

RELATION_BY_CATEGORY = {
    "missing_support_candidate": "missing_support_candidate",
    "support_selected_without_target": "support_without_target",
    "target_selected_without_support": "target_without_support",
}

LABEL_CONTRACT = (
    ("support_relation_bucket", "enum", "missing_support_candidate|support_without_target|target_without_support|ambiguous_or_unknown", True, True, True, "classify_target_support_relation_without_exposing_paths"),
    ("target_hit_bucket", "enum", "hit|miss|unknown_not_labeled", True, True, True, "bucketize_target_presence_after_private_labeling"),
    ("support_hit_bucket", "enum", "hit|miss|unknown_not_labeled", True, True, True, "bucketize_support_presence_after_private_labeling"),
    ("conjunction_bucket", "enum", "target_and_support_hit|target_only|support_only|neither|ambiguous_unlabeled", True, True, True, "derive_only_from_target_and_support_buckets"),
    ("support_evidence_role_bucket", "enum", "precondition|constraint|cross_file_dependency|usage_example|ambiguous_or_unknown", True, True, True, "label_support_role_without_raw_snippet"),
    ("leakage_risk_bucket", "enum", "target_binding_leak_risk|support_overbroad_risk|safe_ambiguous_support|unknown_not_labeled", True, True, True, "guard_against_b16j_style_support_only_leakage"),
)

BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED = False


def _bea_v1_support_link_trace_hook(
    event: Mapping[str, Any], *, enabled: bool = BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED
) -> dict[str, Any]:
    if not enabled:
        return {"trace_logger_enabled": False, "trace_capture_attempted": False, "private_trace_row_written": False}
    from bea_v1_frozen_trace_logger_helpers import (  # noqa: WPS433
        build_support_link_trace_capture_row_private,
        sanitize_support_link_trace_capture_row_public,
        validate_support_link_trace_capture_row_private,
        validate_support_link_trace_capture_row_public_projection,
    )

    private_row = build_support_link_trace_capture_row_private(event)
    private_validation = validate_support_link_trace_capture_row_private(private_row)
    public_row = sanitize_support_link_trace_capture_row_public(private_row)
    public_validation = validate_support_link_trace_capture_row_public_projection(public_row)
    return {
        "trace_logger_enabled": True,
        "trace_capture_attempted": False,
        "private_trace_row_written": False,
        "surface_bucket": "support_link",
        "private_validation_status": private_validation.get("validation_status"),
        "public_validation_status": public_validation.get("validation_status"),
        "public_projection": public_row,
    }


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


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _support_trace_rows(trace_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows = trace_artifact.get("trace_gap_records", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("trace_field") == "support_link_trace"]


def _support_matrix_rows(p0_2: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p0_2.get("refreshed_actionability_matrix_records", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("trace_field") == "support_link_trace"]


def _input_design_records(matrix_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(sorted(matrix_rows, key=lambda r: (str(r.get("failure_category", "")), str(r.get("action_layer", ""))))):
        category = str(row.get("failure_category", "") or "")
        relation = RELATION_BY_CATEGORY.get(category, "ambiguous_or_unknown")
        out.append({
            "anonymous_design_id": f"sl{i:04d}",
            "failure_category": category,
            "action_layer": str(row.get("action_layer", "") or ""),
            "trace_field": "support_link_trace",
            "support_relation_bucket": relation,
            "target_hit_bucket": "unknown_not_labeled",
            "support_hit_bucket": "unknown_not_labeled",
            "conjunction_bucket": "ambiguous_unlabeled",
            "support_evidence_role_bucket": "ambiguous_or_unknown",
            "leakage_risk_bucket": "unknown_not_labeled",
            "label_question_bucket": "does_this_failure_require_target_support_relation_labeling",
            "label_required": True,
            "counterfactual_ready_after_label": False,
            "publication_boundary": "sanitized_labeling_input_contract_only",
            "authorized_next_step": "label_support_relation_before_counterfactual",
        })
    return out


def _labeling_contract_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, (name, field_type, allowed, required, public_safe, private_required, guidance) in enumerate(LABEL_CONTRACT):
        out.append({
            "anonymous_contract_id": f"lc{i:03d}",
            "input_field_name": name,
            "field_type": field_type,
            "allowed_values": allowed,
            "required": required,
            "public_safe": public_safe,
            "private_source_required": private_required,
            "annotation_guidance_bucket": guidance,
        })
    return out


def _source_record(key: str, artifact: dict[str, Any], load_status: str, field: str) -> dict[str, Any]:
    rows = artifact.get(field, [])
    return {
        "input_artifact": key,
        "load_status": load_status,
        "source_status": str(artifact.get("status", "") or ""),
        "source_schema": str(artifact.get("schema_version", "") or ""),
        "forbidden_scan_status": str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"),
        "record_count": len(rows) if isinstance(rows, list) else 0,
    }


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    trace_artifact, trace_status = _load_json(args.trace_gap_artifact)
    p0_2, p0_2_status = _load_json(args.p0_2_artifact)
    trace_rows = _support_trace_rows(trace_artifact)
    matrix_rows = _support_matrix_rows(p0_2)
    design_rows = _input_design_records(matrix_rows)
    contract_rows = _labeling_contract_records()
    trace_ok = trace_status == "pass" and trace_artifact.get("status") == "trace_gap_audit_pass" and trace_artifact.get("forbidden_scan", {}).get("status") == "pass"
    p0_2_ok = p0_2_status == "pass" and p0_2.get("status") == "actionability_matrix_refresh_pass" and p0_2.get("forbidden_scan", {}).get("status") == "pass"
    category_ok = {str(row.get("category", "") or "") for row in trace_rows} == set(SUPPORT_CATEGORIES)
    matrix_ok = len(matrix_rows) == 18 and {str(row.get("failure_category", "") or "") for row in matrix_rows} == set(SUPPORT_CATEGORIES)
    design_ok = len(design_rows) == 18 and all(row.get("label_required") is True for row in design_rows)
    status = "support_link_input_design_pass" if trace_ok and p0_2_ok and category_ok and matrix_ok and design_ok and all(c["passed"] for c in checks) else "no_go_support_link_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "support_link_input_design_pass" else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            _source_record("p0_1_trace_gap_audit", trace_artifact, trace_status, "trace_gap_records"),
            _source_record("p0_2_actionability_matrix_refresh", p0_2, p0_2_status, "refreshed_actionability_matrix_records"),
        ],
        "support_link_input_design_records": design_rows,
        "labeling_input_contract_records": contract_rows,
        "support_link_gap_summary_records": _summary(design_rows, "failure_category"),
        "support_link_cell_summary_records": _summary(design_rows, "action_layer"),
        "support_relation_summary_records": _summary(design_rows, "support_relation_bucket"),
        "conjunction_summary_records": _summary(design_rows, "conjunction_bucket"),
        "gate_records": [
            {"gate": "p0_1_trace_gap_artifact_available", "passed": trace_ok, "threshold_relation": "boolean", "value": int(trace_ok), "threshold_value": 1},
            {"gate": "p0_2_matrix_artifact_available", "passed": p0_2_ok, "threshold_relation": "boolean", "value": int(p0_2_ok), "threshold_value": 1},
            {"gate": "support_link_categories_complete", "passed": category_ok, "threshold_relation": "boolean", "value": int(category_ok), "threshold_value": 1},
            {"gate": "support_link_cells_complete", "passed": matrix_ok, "threshold_relation": "equals", "value": len(matrix_rows), "threshold_value": 18},
            {"gate": "input_design_records_complete", "passed": design_ok, "threshold_relation": "equals", "value": len(design_rows), "threshold_value": 18},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "support_link_labeling_input_contract_ready_without_counterfactual_claim" if status == "support_link_input_design_pass" else "required_inputs_unavailable",
            "authorization": "support_link_labeling_input_only",
            "counterfactual_execution_authorized": False,
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "v1_a_authorized": False,
            "p5_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "downstream_value_claimed": False,
        }],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = tg._scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = tg._scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    sample = _input_design_records([{"failure_category": "missing_support_candidate", "action_layer": "conditional_support_expansion", "trace_field": "support_link_trace"}])[0]
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("support_categories_exact", len(SUPPORT_CATEGORIES) == 3),
        _check("label_contract_nonempty", len(LABEL_CONTRACT) == 6),
        _check("sample_relation_bucket", sample["support_relation_bucket"] == "missing_support_candidate"),
        _check("sample_not_counterfactual_ready", sample["counterfactual_ready_after_label"] is False),
        _check("sample_hides_raw_payload", all(k not in sample for k in ("path", "candidate", "rank", "score", "snippet", "private_record_id"))),
        _check("scanner_accepts_sample", tg._scan_summary({"support_link_input_design_records": [sample]})["status"] == "pass"),
        _check("scanner_rejects_forbidden_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-4 support-link input design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--trace-gap-artifact", type=Path, default=DEFAULT_TRACE_GAP)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, design_records={len(report['support_link_input_design_records'])})")


if __name__ == "__main__":
    main()
