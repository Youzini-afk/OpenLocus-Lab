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
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p1_1_private_labeling_queue_preparation.v1"
QUEUE_SCHEMA_VERSION = "bea_v1_p1_1_support_labeling_queue.v1"
GENERATED_BY = "eval/bea_v1_p1_1_private_labeling_queue_preparation.py"
CLAIM_LEVEL = "bea_v1_p1_1_private_labeling_queue_preparation_only"
MODE = "bea_v1_p1_1_private_labeling_queue_preparation"
PHASE = "BEA-v1-P1-1"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P1_0 = Path("artifacts/bea_v1_p1_0_support_label_validator_dry_run/bea_v1_p1_0_support_label_validator_dry_run_report.json")
DEFAULT_QUEUE = Path(".openlocus/research-private/bea_v1_p1_1_support_labeling_queue.jsonl")

STATUSES = (
    "private_labeling_queue_preparation_pass",
    "no_go_private_labeling_queue_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIORITY_BY_RELATION = {
    "missing_support_candidate": "p0_high_missing_support",
    "support_without_target": "p1_medium_support_only_risk",
    "target_without_support": "p1_medium_target_only_gap",
    "ambiguous_or_unknown": "p2_low_ambiguous",
}

ROLE_HINT_BY_RELATION = {
    "missing_support_candidate": "look_for_support_evidence_role_before_counterfactual",
    "support_without_target": "guard_against_support_only_target_binding_leak",
    "target_without_support": "check_whether_support_is_required_or_optional",
    "ambiguous_or_unknown": "label_relation_only_if_private_context_is_sufficient",
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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not h._safe_private_path(path):
        raise ValueError("private labeling queue must stay under .openlocus/research-private")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _queue_rows(design_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates = h._template_rows(design_rows)
    out: list[dict[str, Any]] = []
    for i, row in enumerate(templates):
        relation = str(row.get("support_relation_bucket", "ambiguous_or_unknown") or "ambiguous_or_unknown")
        out.append({
            **row,
            "schema_version": QUEUE_SCHEMA_VERSION,
            "base_private_label_schema_version": h.PRIVATE_SCHEMA_VERSION,
            "queue_item_id": f"ql{i:04d}",
            "queue_status": "ready_for_private_labeling",
            "queue_priority_bucket": PRIORITY_BY_RELATION.get(relation, "p2_low_ambiguous"),
            "annotation_guidance_bucket": ROLE_HINT_BY_RELATION.get(relation, "label_relation_only_if_private_context_is_sufficient"),
            "required_output_schema_version": h.PRIVATE_SCHEMA_VERSION,
            "ready_for_counterfactual_after_label": False,
        })
    return out


def _public_queue_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        out.append({
            "anonymous_queue_bucket_id": f"qpub{i:04d}",
            "failure_category": str(row.get("failure_category", "") or ""),
            "action_layer": str(row.get("action_layer", "") or ""),
            "support_relation_bucket": str(row.get("support_relation_bucket", "") or ""),
            "queue_priority_bucket": str(row.get("queue_priority_bucket", "") or ""),
            "queue_status_bucket": str(row.get("queue_status", "") or ""),
            "annotation_guidance_bucket": str(row.get("annotation_guidance_bucket", "") or ""),
            "ready_for_counterfactual_after_label": False,
        })
    return out


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    p1_0, p1_0_status = _load_json(args.p1_0_artifact)
    design_rows = h._design_rows(p0_4)
    queue_rows = _queue_rows(design_rows)
    queue_written = False
    queue_status = "not_requested"
    if args.emit_private_queue:
        try:
            _write_jsonl(args.private_queue_out, queue_rows)
            queue_written = True
            queue_status = "written_project_private"
        except Exception:
            queue_status = "write_failed"
    public_rows = _public_queue_records(queue_rows)
    p0_4_ok = p0_4_status == "pass" and p0_4.get("status") == "support_link_input_design_pass" and p0_4.get("forbidden_scan", {}).get("status") == "pass"
    p1_0_ok = p1_0_status == "pass" and p1_0.get("status") == "support_label_validator_dry_run_pass" and p1_0.get("forbidden_scan", {}).get("status") == "pass"
    queue_ok = len(queue_rows) == 18 and len({row["queue_item_id"] for row in queue_rows}) == 18 and all(row.get("required_output_schema_version") == h.PRIVATE_SCHEMA_VERSION for row in queue_rows)
    status = "private_labeling_queue_preparation_pass" if p0_4_ok and p1_0_ok and queue_ok and all(c["passed"] for c in checks) else "no_go_private_labeling_queue_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "private_labeling_queue_preparation_pass" else "required_input_artifact_unavailable_or_queue_build_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p0_4_support_link_input_design", "load_status": p0_4_status, "source_status": str(p0_4.get("status", "") or ""), "source_schema": str(p0_4.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_4.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(design_rows)},
            {"input_artifact": "p1_0_support_label_validator_dry_run", "load_status": p1_0_status, "source_status": str(p1_0.get("status", "") or ""), "source_schema": str(p1_0.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_0.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_0.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(p1_0.get("sanitized_synthetic_label_records", [])) if isinstance(p1_0.get("sanitized_synthetic_label_records"), list) else 0},
        ],
        "private_queue_manifest_records": [{
            "manifest_name": "bea_v1_p1_1_support_labeling_queue",
            "schema_version": QUEUE_SCHEMA_VERSION,
            "required_output_schema_version": h.PRIVATE_SCHEMA_VERSION,
            "record_count": len(queue_rows),
            "records_written": queue_written,
            "write_status": queue_status,
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "sanitized_labeling_queue_records": public_rows,
        "queue_priority_summary_records": _summary(public_rows, "queue_priority_bucket"),
        "queue_relation_summary_records": _summary(public_rows, "support_relation_bucket"),
        "queue_action_layer_summary_records": _summary(public_rows, "action_layer"),
        "gate_records": [
            {"gate": "p0_4_design_artifact_available", "passed": p0_4_ok, "threshold_relation": "boolean", "value": int(p0_4_ok), "threshold_value": 1},
            {"gate": "p1_0_validator_dry_run_available", "passed": p1_0_ok, "threshold_relation": "boolean", "value": int(p1_0_ok), "threshold_value": 1},
            {"gate": "private_queue_rows_buildable", "passed": queue_ok, "threshold_relation": "equals", "value": len(queue_rows), "threshold_value": 18},
            {"gate": "real_private_labels_available", "passed": False, "threshold_relation": "boolean_required_for_counterfactual", "value": 0, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "private_labeling_queue_ready_real_labels_still_required" if status == "private_labeling_queue_preparation_pass" else "required_inputs_unavailable",
            "authorization": "real_private_support_labeling_queue_only",
            "real_private_labeling_authorized": status == "private_labeling_queue_preparation_pass",
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
    queue = _queue_rows(design)
    public = _public_queue_records(queue)
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("queue_schema_set", queue[0]["schema_version"] == QUEUE_SCHEMA_VERSION),
        _check("queue_requires_p0_5_schema", queue[0]["required_output_schema_version"] == h.PRIVATE_SCHEMA_VERSION),
        _check("queue_not_counterfactual_ready", queue[0]["ready_for_counterfactual_after_label"] is False),
        _check("public_queue_hides_design_id", "anonymous_design_id" not in public[0] and "queue_item_id" not in public[0]),
        _check("scanner_accepts_public_queue", tg._scan_summary({"sanitized_labeling_queue_records": public})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-1 private labeling queue preparation")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--p1-0-artifact", type=Path, default=DEFAULT_P1_0)
    parser.add_argument("--emit-private-queue", action="store_true")
    parser.add_argument("--private-queue-out", type=Path, default=DEFAULT_QUEUE)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, queue_records={len(report['sanitized_labeling_queue_records'])})")


if __name__ == "__main__":
    main()
