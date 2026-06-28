#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p0_5_support_link_labeling_harness as h  # noqa: E402
import bea_v1_p1_1_private_labeling_queue_preparation as q  # noqa: E402
import bea_v1_p1_2_private_label_intake_validator as intake  # noqa: E402
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p1_3_agent_generated_support_label_fill.v1"
GENERATED_BY = "eval/bea_v1_p1_3_agent_generated_support_label_fill.py"
CLAIM_LEVEL = "automated_private_support_label_fill_only"
MODE = "bea_v1_p1_3_agent_generated_support_label_fill"
PHASE = "BEA-v1-P1-3"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P1_1 = Path("artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json")
DEFAULT_QUEUE = Path(".openlocus/research-private/bea_v1_p1_1_support_labeling_queue.jsonl")
DEFAULT_PRIVATE_LABELS = Path(".openlocus/research-private/bea_v1_p1_3_agent_generated_support_labels.jsonl")

STATUSES = (
    "agent_generated_support_label_fill_pass",
    "no_go_agent_generated_support_label_fill_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

LABEL_ORIGIN = "agent_generated"
LABEL_METHOD_BUCKET = "deterministic_queue_field_heuristic"
ANNOTATION_STATUS = "labeled"
UNKNOWN_HIT = "unknown_not_labeled"

ROLE_BY_RELATION = {
    "missing_support_candidate": "ambiguous_or_unknown",
    "support_without_target": "ambiguous_or_unknown",
    "target_without_support": "constraint",
    "ambiguous_or_unknown": "ambiguous_or_unknown",
}

RISK_BY_RELATION = {
    "missing_support_candidate": "unknown_not_labeled",
    "support_without_target": "target_binding_leak_risk",
    "target_without_support": "support_overbroad_risk",
    "ambiguous_or_unknown": "unknown_not_labeled",
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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not h._safe_private_path(path):
        raise ValueError("agent-generated labels must stay under project private research storage")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _label_row_from_queue(row: dict[str, Any]) -> dict[str, Any]:
    relation = str(row.get("support_relation_bucket", "ambiguous_or_unknown") or "ambiguous_or_unknown")
    target_hit = UNKNOWN_HIT
    support_hit = UNKNOWN_HIT
    return {
        "schema_version": h.PRIVATE_SCHEMA_VERSION,
        "anonymous_design_id": str(row.get("anonymous_design_id", "") or ""),
        "queue_item_id": str(row.get("queue_item_id", "") or ""),
        "source_queue_schema_version": q.QUEUE_SCHEMA_VERSION,
        "failure_category": str(row.get("failure_category", "") or ""),
        "action_layer": str(row.get("action_layer", "") or ""),
        "support_relation_bucket": relation if relation in h.ALLOWED_RELATION else "ambiguous_or_unknown",
        "target_hit_bucket": target_hit,
        "support_hit_bucket": support_hit,
        "conjunction_bucket": h._derive_conjunction(target_hit, support_hit),
        "support_evidence_role_bucket": ROLE_BY_RELATION.get(relation, "ambiguous_or_unknown"),
        "leakage_risk_bucket": RISK_BY_RELATION.get(relation, "unknown_not_labeled"),
        "annotator_confidence_bucket": "unknown_not_labeled",
        "annotation_status": ANNOTATION_STATUS,
        "label_origin": LABEL_ORIGIN,
        "label_method_bucket": LABEL_METHOD_BUCKET,
        "human_calibrated": False,
    }


def _generated_label_rows(valid_queue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_label_row_from_queue(row) for row in valid_queue_rows]


def _sanitized_generated_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        out.append({
            "anonymous_generated_label_id": f"aglbl{i:04d}",
            "support_relation_bucket": str(row.get("support_relation_bucket", "") or ""),
            "target_hit_bucket": str(row.get("target_hit_bucket", "") or ""),
            "support_hit_bucket": str(row.get("support_hit_bucket", "") or ""),
            "conjunction_bucket": str(row.get("conjunction_bucket", "") or ""),
            "support_evidence_role_bucket": str(row.get("support_evidence_role_bucket", "") or ""),
            "leakage_risk_bucket": str(row.get("leakage_risk_bucket", "") or ""),
            "annotation_status_bucket": str(row.get("annotation_status", "") or ""),
            "label_origin_bucket": str(row.get("label_origin", "") or ""),
            "label_method_bucket": str(row.get("label_method_bucket", "") or ""),
            "human_calibrated": bool(row.get("human_calibrated", True)),
            "raw_source_used": False,
            "provider_call_used": False,
            "counterfactual_ready_after_fill": False,
        })
    return out


def _p1_2_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    p1_2_args = argparse.Namespace(
        p0_4_artifact=args.p0_4_artifact,
        p1_1_artifact=args.p1_1_artifact,
        private_queue_jsonl=args.private_queue_jsonl,
        private_labels_jsonl=args.private_labels_out,
    )
    return intake._build_report(p1_2_args, checks)


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]], p1_2_checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    p1_1, p1_1_status = _load_json(args.p1_1_artifact)
    design_rows = h._design_rows(p0_4)
    design_ids = {str(row.get("anonymous_design_id", "") or "") for row in design_rows}
    queue_rows, queue_read_status = _read_jsonl(args.private_queue_jsonl)
    valid_queue, queue_errors = intake._validate_queue(queue_rows, design_ids) if queue_read_status == "pass" else ([], [])
    generated_rows = _generated_label_rows(valid_queue)
    write_status = "not_requested"
    rows_written = False
    if args.emit_private_labels:
        try:
            _write_jsonl(args.private_labels_out, generated_rows)
            write_status = "written_project_private"
            rows_written = True
        except Exception:
            write_status = "write_failed"
    p0_5_valid, label_errors = h._validate_private_labels(generated_rows, design_ids)
    p1_2 = _p1_2_report(args, p1_2_checks) if rows_written else {}
    p1_2_manifest = p1_2.get("private_label_intake_manifest_records", [{}])
    if not isinstance(p1_2_manifest, list) or not p1_2_manifest:
        p1_2_manifest = [{}]
    p1_2_valid_count = int(p1_2_manifest[0].get("valid_record_count", 0) or 0)
    p1_2_error_count = int(p1_2_manifest[0].get("error_count", 0) or 0)
    sanitized = _sanitized_generated_records(p0_5_valid)
    p0_4_ok = p0_4_status == "pass" and p0_4.get("status") == "support_link_input_design_pass" and p0_4.get("forbidden_scan", {}).get("status") == "pass"
    p1_1_public_rows = p1_1.get("sanitized_labeling_queue_records", [])
    p1_1_ok = p1_1_status == "pass" and p1_1.get("status") == "private_labeling_queue_preparation_pass" and p1_1.get("forbidden_scan", {}).get("status") == "pass" and isinstance(p1_1_public_rows, list) and len(p1_1_public_rows) == 18
    queue_ok = queue_read_status == "pass" and len(queue_rows) == 18 and len(valid_queue) == 18 and not queue_errors
    generated_ok = len(generated_rows) == len(valid_queue) == 18
    p0_5_ok = len(p0_5_valid) == 18 and not label_errors
    p1_2_ok = p1_2.get("status") == "private_label_intake_validator_real_labels_pass" and p1_2_valid_count == 18 and p1_2_error_count == 0 and p1_2.get("forbidden_scan", {}).get("status") == "pass"
    no_counterfactual = True
    status = "agent_generated_support_label_fill_pass" if p0_4_ok and p1_1_ok and queue_ok and rows_written and generated_ok and p0_5_ok and p1_2_ok and no_counterfactual and all(c["passed"] for c in checks) else "no_go_agent_generated_support_label_fill_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "agent_generated_support_label_fill_pass" else "required_input_or_validation_gate_unavailable",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p0_4_support_link_input_design", "load_status": p0_4_status, "source_status": str(p0_4.get("status", "") or ""), "source_schema": str(p0_4.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_4.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(design_rows)},
            {"input_artifact": "p1_1_private_labeling_queue_preparation", "load_status": p1_1_status, "source_status": str(p1_1.get("status", "") or ""), "source_schema": str(p1_1.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_1.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_1.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(p1_1_public_rows) if isinstance(p1_1_public_rows, list) else 0},
            {"input_artifact": "p1_2_private_label_intake_validator", "load_status": "pass" if p1_2 else "not_run", "source_status": str(p1_2.get("status", "") or ""), "source_schema": str(p1_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_2.get("forbidden_scan"), dict) else "not_reported"), "record_count": p1_2_valid_count},
        ],
        "private_queue_read_manifest_records": [{
            "manifest_name": "bea_v1_p1_1_support_labeling_queue",
            "schema_version": q.QUEUE_SCHEMA_VERSION,
            "read_status": queue_read_status,
            "record_count": len(queue_rows),
            "valid_record_count": len(valid_queue),
            "error_count": len(queue_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "agent_generated_label_manifest_records": [{
            "manifest_name": "bea_v1_p1_3_agent_generated_support_labels",
            "schema_version": h.PRIVATE_SCHEMA_VERSION,
            "source_queue_schema_version": q.QUEUE_SCHEMA_VERSION,
            "label_origin_bucket": LABEL_ORIGIN,
            "label_method_bucket": LABEL_METHOD_BUCKET,
            "human_calibrated": False,
            "record_count": len(generated_rows),
            "records_written": rows_written,
            "write_status": write_status,
            "p0_5_compatible_record_count": len(p0_5_valid),
            "p1_2_intake_valid_record_count": p1_2_valid_count,
            "label_error_count": len(label_errors) + p1_2_error_count,
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "sanitized_agent_generated_label_records": sanitized,
        "label_relation_summary_records": _summary(sanitized, "support_relation_bucket"),
        "label_conjunction_summary_records": _summary(sanitized, "conjunction_bucket"),
        "label_role_summary_records": _summary(sanitized, "support_evidence_role_bucket"),
        "label_risk_summary_records": _summary(sanitized, "leakage_risk_bucket"),
        "label_origin_summary_records": _summary(sanitized, "label_origin_bucket"),
        "label_error_summary_records": _summary(label_errors, "error_bucket"),
        "gate_records": [
            {"gate": "p0_4_design_artifact_available", "passed": p0_4_ok, "threshold_relation": "boolean", "value": int(p0_4_ok), "threshold_value": 1},
            {"gate": "p1_1_queue_artifact_available", "passed": p1_1_ok, "threshold_relation": "boolean", "value": int(p1_1_ok), "threshold_value": 1},
            {"gate": "private_queue_rows_read", "passed": queue_read_status == "pass" and len(queue_rows) == 18, "threshold_relation": "equals", "value": len(queue_rows), "threshold_value": 18},
            {"gate": "private_queue_rows_valid", "passed": queue_ok, "threshold_relation": "equals", "value": len(valid_queue), "threshold_value": 18},
            {"gate": "agent_generated_label_rows_written", "passed": rows_written and generated_ok, "threshold_relation": "equals", "value": len(generated_rows), "threshold_value": 18},
            {"gate": "p0_5_compatible_rows", "passed": p0_5_ok, "threshold_relation": "equals", "value": len(p0_5_valid), "threshold_value": 18},
            {"gate": "p1_2_intake_valid_rows", "passed": p1_2_ok, "threshold_relation": "equals", "value": p1_2_valid_count, "threshold_value": 18},
            {"gate": "label_errors_zero", "passed": len(label_errors) + p1_2_error_count == 0, "threshold_relation": "equals", "value": len(label_errors) + p1_2_error_count, "threshold_value": 0},
            {"gate": "support_counterfactual_execution_not_run", "passed": no_counterfactual, "threshold_relation": "boolean", "value": int(no_counterfactual), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "agent_generated_private_labels_validated_without_counterfactual" if status == "agent_generated_support_label_fill_pass" else "required_inputs_or_validation_unavailable",
            "authorization": "automated_private_support_label_fill_only",
            "label_origin_claim": "agent_generated_only",
            "human_labels_claimed": False,
            "human_calibrated_e_s_claimed": False,
            "mechanism_evidence_claimed": False,
            "support_counterfactual_execution_authorized": False,
            "support_counterfactual_executed": False,
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
    design = [{"anonymous_design_id": "sl0000", "failure_category": "support_selected_without_target", "action_layer": "file_selector", "support_relation_bucket": "support_without_target"}]
    queue = q._queue_rows(design)
    label = _label_row_from_queue(queue[0])
    valid, errors = h._validate_private_labels([label], {"sl0000"})
    valid_queue, queue_errors = intake._validate_queue(queue, {"sl0000"})
    intake_valid, intake_errors = intake._validate_intake_labels([label], valid_queue)
    public = _sanitized_generated_records([label])
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("private_label_schema_set", label["schema_version"] == h.PRIVATE_SCHEMA_VERSION),
        _check("derived_conjunction_unknown_hits", label["conjunction_bucket"] == "ambiguous_unlabeled"),
        _check("private_root_safety_rejects_public_out", not h._safe_private_path(Path("artifacts/not_private.jsonl"))),
        _check("origin_metadata_set", label["label_origin"] == LABEL_ORIGIN and label["label_method_bucket"] == LABEL_METHOD_BUCKET and label["human_calibrated"] is False),
        _check("p0_5_compatible", len(valid) == 1 and not errors),
        _check("p1_2_intake_compatible", len(valid_queue) == 1 and not queue_errors and len(intake_valid) == 1 and not intake_errors),
        _check("public_records_hide_private_ids", "anonymous_design_id" not in public[0] and "queue_item_id" not in public[0]),
        _check("scanner_accepts_public_records", tg._scan_summary({"sanitized_agent_generated_label_records": public})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-3 agent-generated private support-label fill")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--p1-1-artifact", type=Path, default=DEFAULT_P1_1)
    parser.add_argument("--private-queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--private-labels-out", type=Path, default=DEFAULT_PRIVATE_LABELS)
    parser.add_argument("--no-emit-private-labels", dest="emit_private_labels", action="store_false")
    parser.set_defaults(emit_private_labels=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    p1_2_checks, p1_2_ok = intake.run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok and p1_2_ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks, p1_2_self_test={p1_2_ok})")
        raise SystemExit(0 if ok and p1_2_ok else 1)
    report = _build_report(args, checks, p1_2_checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    manifest = report["agent_generated_label_manifest_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, generated_labels={manifest['record_count']}, p1_2_valid={manifest['p1_2_intake_valid_record_count']})")


if __name__ == "__main__":
    main()
