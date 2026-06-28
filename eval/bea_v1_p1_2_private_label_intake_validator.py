#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p0_5_support_link_labeling_harness as h  # noqa: E402
import bea_v1_p1_1_private_labeling_queue_preparation as q  # noqa: E402
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p1_2_private_label_intake_validator.v1"
GENERATED_BY = "eval/bea_v1_p1_2_private_label_intake_validator.py"
CLAIM_LEVEL = "bea_v1_p1_2_private_label_intake_validator_only"
MODE = "bea_v1_p1_2_private_label_intake_validator"
PHASE = "BEA-v1-P1-2"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_2_private_label_intake_validator/bea_v1_p1_2_private_label_intake_validator_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P1_1 = Path("artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json")
DEFAULT_QUEUE = Path(".openlocus/research-private/bea_v1_p1_1_support_labeling_queue.jsonl")

STATUSES = (
    "private_label_intake_validator_contract_pass",
    "private_label_intake_validator_real_labels_pass",
    "no_go_private_label_intake_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

QUEUE_STATUS = "ready_for_private_labeling"
OUTPUT_STATUS = "labeled"
BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED = False


def _bea_v1_support_label_intake_trace_hook(
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


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], "not_supplied"
    if not h._safe_private_path(path):
        return [], "outside_project_private_root"
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "parse_failed"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _queue_public_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("anonymous_queue_bucket_id", "") or "") for row in rows}


def _validate_queue(rows: list[dict[str, Any]], design_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        row_errors: list[str] = []
        queue_id = str(row.get("queue_item_id", "") or "")
        design_id = str(row.get("anonymous_design_id", "") or "")
        if row.get("schema_version") != q.QUEUE_SCHEMA_VERSION:
            row_errors.append("queue_schema_version_mismatch")
        if row.get("base_private_label_schema_version") != h.PRIVATE_SCHEMA_VERSION:
            row_errors.append("base_private_label_schema_version_mismatch")
        if row.get("required_output_schema_version") != h.PRIVATE_SCHEMA_VERSION:
            row_errors.append("required_output_schema_version_mismatch")
        if row.get("queue_status") != QUEUE_STATUS:
            row_errors.append("queue_status_not_ready")
        if row.get("ready_for_counterfactual_after_label") is not False:
            row_errors.append("queue_counterfactual_flag_not_false")
        if not queue_id:
            row_errors.append("missing_queue_item_id")
        if queue_id in seen:
            row_errors.append("duplicate_queue_item_id")
        if design_id not in design_ids:
            row_errors.append("unknown_design_id")
        if row_errors:
            errors.append({"anonymous_error_id": f"qe{i:04d}", "error_bucket": "|".join(sorted(row_errors))})
        else:
            seen.add(queue_id)
            valid.append(row)
    return valid, errors


def _validate_intake_labels(rows: list[dict[str, Any]], queue_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue_by_design = {str(row.get("anonymous_design_id", "") or ""): row for row in queue_rows}
    valid, errors = h._validate_private_labels(rows, set(queue_by_design))
    error_ids = {str(error.get("anonymous_error_id", "") or "") for error in errors}
    seen_designs = {str(row.get("anonymous_design_id", "") or "") for row in valid}
    for i, row in enumerate(rows):
        error_id = f"le{i:04d}"
        if error_id in error_ids:
            continue
        row_errors: list[str] = []
        design_id = str(row.get("anonymous_design_id", "") or "")
        queue_row = queue_by_design.get(design_id, {})
        if row.get("queue_item_id") != queue_row.get("queue_item_id"):
            row_errors.append("queue_item_id_mismatch")
        if row.get("source_queue_schema_version") != q.QUEUE_SCHEMA_VERSION:
            row_errors.append("source_queue_schema_version_mismatch")
        if row.get("annotation_status") != OUTPUT_STATUS:
            row_errors.append("annotation_status_not_labeled")
        if row_errors:
            errors.append({"anonymous_error_id": error_id, "error_bucket": "|".join(sorted(row_errors))})
            seen_designs.discard(design_id)
    valid = [row for row in valid if str(row.get("anonymous_design_id", "") or "") in seen_designs]
    return valid, errors


def _sanitized_intake_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(h._sanitize_labels(rows)):
        out.append({
            **row,
            "anonymous_intake_label_id": f"ilbl{i:04d}",
            "label_is_real_private_data": True,
            "ready_for_counterfactual_after_intake": False,
        })
    return out


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    p1_1, p1_1_status = _load_json(args.p1_1_artifact)
    design_rows = h._design_rows(p0_4)
    queue_rows, queue_read_status = _read_jsonl(args.private_queue_jsonl)
    valid_queue, queue_errors = _validate_queue(queue_rows, {str(row.get("anonymous_design_id", "") or "") for row in design_rows}) if queue_read_status == "pass" else ([], [])
    label_rows, label_read_status = _read_jsonl(args.private_labels_jsonl)
    valid_labels, label_errors = _validate_intake_labels(label_rows, valid_queue) if label_read_status == "pass" else ([], [])
    sanitized = _sanitized_intake_records(valid_labels)
    p0_4_ok = p0_4_status == "pass" and p0_4.get("status") == "support_link_input_design_pass" and p0_4.get("forbidden_scan", {}).get("status") == "pass"
    p1_1_public_rows = p1_1.get("sanitized_labeling_queue_records", [])
    p1_1_ok = p1_1_status == "pass" and p1_1.get("status") == "private_labeling_queue_preparation_pass" and p1_1.get("forbidden_scan", {}).get("status") == "pass" and isinstance(p1_1_public_rows, list) and len(p1_1_public_rows) == 18
    queue_ok = queue_read_status == "pass" and len(valid_queue) == 18 and not queue_errors
    queue_public_shape_ok = p1_1_ok and len(_queue_public_ids(p1_1_public_rows)) == len(valid_queue)
    full_label_ok = label_read_status == "pass" and len(valid_labels) == 18 and not label_errors
    contract_ok = p0_4_ok and p1_1_ok and queue_ok and queue_public_shape_ok and all(c["passed"] for c in checks)
    if not contract_ok:
        status = "no_go_private_label_intake_inputs_unavailable"
    elif full_label_ok:
        status = "private_label_intake_validator_real_labels_pass"
    else:
        status = "private_label_intake_validator_contract_pass"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if contract_ok else "required_input_artifact_or_private_queue_unavailable",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p0_4_support_link_input_design", "load_status": p0_4_status, "source_status": str(p0_4.get("status", "") or ""), "source_schema": str(p0_4.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_4.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(design_rows)},
            {"input_artifact": "p1_1_private_labeling_queue_preparation", "load_status": p1_1_status, "source_status": str(p1_1.get("status", "") or ""), "source_schema": str(p1_1.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_1.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_1.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(p1_1_public_rows) if isinstance(p1_1_public_rows, list) else 0},
        ],
        "private_queue_intake_manifest_records": [{
            "manifest_name": "bea_v1_p1_1_support_labeling_queue",
            "schema_version": q.QUEUE_SCHEMA_VERSION,
            "required_output_schema_version": h.PRIVATE_SCHEMA_VERSION,
            "read_status": queue_read_status,
            "record_count": len(queue_rows),
            "valid_record_count": len(valid_queue),
            "error_count": len(queue_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "private_label_intake_manifest_records": [{
            "manifest_name": "bea_v1_p1_2_support_label_intake",
            "schema_version": h.PRIVATE_SCHEMA_VERSION,
            "source_queue_schema_version": q.QUEUE_SCHEMA_VERSION,
            "read_status": label_read_status,
            "record_count": len(label_rows),
            "valid_record_count": len(valid_labels),
            "error_count": len(label_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "queue_intake_error_summary_records": _summary(queue_errors, "error_bucket"),
        "label_intake_error_summary_records": _summary(label_errors, "error_bucket"),
        "sanitized_real_label_intake_records": sanitized,
        "label_relation_summary_records": _summary(sanitized, "support_relation_bucket"),
        "label_conjunction_summary_records": _summary(sanitized, "conjunction_bucket"),
        "label_risk_summary_records": _summary(sanitized, "leakage_risk_bucket"),
        "gate_records": [
            {"gate": "p0_4_design_artifact_available", "passed": p0_4_ok, "threshold_relation": "boolean", "value": int(p0_4_ok), "threshold_value": 1},
            {"gate": "p1_1_queue_artifact_available", "passed": p1_1_ok, "threshold_relation": "boolean", "value": int(p1_1_ok), "threshold_value": 1},
            {"gate": "private_queue_rows_valid", "passed": queue_ok, "threshold_relation": "equals", "value": len(valid_queue), "threshold_value": 18},
            {"gate": "public_private_queue_shapes_join", "passed": queue_public_shape_ok, "threshold_relation": "equals", "value": len(_queue_public_ids(p1_1_public_rows)) if isinstance(p1_1_public_rows, list) else 0, "threshold_value": len(valid_queue)},
            {"gate": "real_private_label_rows_full_valid", "passed": full_label_ok, "threshold_relation": "boolean_required_for_counterfactual", "value": int(full_label_ok), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "real_private_labels_validated_counterfactual_still_blocked" if full_label_ok else "intake_validator_ready_real_labels_still_required" if contract_ok else "required_inputs_unavailable",
            "authorization": "private_support_label_intake_validation_only",
            "real_private_labels_validated": full_label_ok,
            "support_counterfactual_execution_authorized": False,
            "support_marginal_utility_claimed": False,
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
    design = [{"anonymous_design_id": "sl0000", "failure_category": "missing_support_candidate", "action_layer": "file_selector", "support_relation_bucket": "missing_support_candidate"}]
    queue = q._queue_rows(design)
    label = {**h._template_rows(design)[0], "queue_item_id": queue[0]["queue_item_id"], "source_queue_schema_version": q.QUEUE_SCHEMA_VERSION, "target_hit_bucket": "hit", "support_hit_bucket": "hit", "conjunction_bucket": "target_and_support_hit", "support_evidence_role_bucket": "precondition", "leakage_risk_bucket": "safe_ambiguous_support", "annotation_status": "labeled"}
    valid_queue, queue_errors = _validate_queue(queue, {"sl0000"})
    valid_labels, label_errors = _validate_intake_labels([label], valid_queue)
    sanitized = _sanitized_intake_records(valid_labels)
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("queue_validates", len(valid_queue) == 1 and not queue_errors),
        _check("label_validates", len(valid_labels) == 1 and not label_errors),
        _check("label_queue_id_required", bool(_validate_intake_labels([{**label, "queue_item_id": "wrong"}], valid_queue)[1])),
        _check("sanitized_hides_private_ids", "anonymous_design_id" not in sanitized[0] and "queue_item_id" not in sanitized[0]),
        _check("intake_not_counterfactual_ready", sanitized[0]["ready_for_counterfactual_after_intake"] is False),
        _check("scanner_accepts_sanitized", tg._scan_summary({"sanitized_real_label_intake_records": sanitized})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-2 private label intake validator")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--p1-1-artifact", type=Path, default=DEFAULT_P1_1)
    parser.add_argument("--private-queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--private-labels-jsonl", type=Path, default=None)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, valid_labels={report['private_label_intake_manifest_records'][0]['valid_record_count']})")


if __name__ == "__main__":
    main()
