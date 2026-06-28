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


SCHEMA_VERSION = "bea_v1_p1_5r_improved_automated_support_label_feasibility.v1"
GENERATED_BY = "eval/bea_v1_p1_5r_improved_automated_support_label_feasibility.py"
CLAIM_LEVEL = "improved_automated_support_label_feasibility_audit_only"
MODE = "bea_v1_p1_5r_improved_automated_support_label_feasibility"
PHASE = "BEA-v1-P1-5R"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_5r_improved_automated_support_label_feasibility/bea_v1_p1_5r_improved_automated_support_label_feasibility_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P1_1 = Path("artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json")
DEFAULT_P1_3 = Path("artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json")
DEFAULT_P1_4 = Path("artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json")
DEFAULT_QUEUE = Path(".openlocus/research-private/bea_v1_p1_1_support_labeling_queue.jsonl")
DEFAULT_PRIVATE_LABELS = Path(".openlocus/research-private/bea_v1_p1_3_agent_generated_support_labels.jsonl")

STATUSES = (
    "source_context_support_label_fill_pass",
    "no_go_p1_5r_private_context_unavailable",
    "no_go_p1_5r_label_generation_low_informative_yield",
    "no_go_p1_5r_p1_2_intake_failed",
    "no_go_p1_5r_p1_4_reliability_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

LINKAGE_CATEGORIES = (
    "source_location_reference",
    "source_span_reference",
    "gold_reference",
    "candidate_reference",
    "task_or_repo_reference",
    "trace_foreign_key_reference",
    "provider_or_private_payload_reference",
)

FIELD_CATEGORY_EXACT = {
    "path": "source_location_reference",
    "paths": "source_location_reference",
    "exact_path": "source_location_reference",
    "source_path": "source_location_reference",
    "file_path": "source_location_reference",
    "candidate_path": "source_location_reference",
    "candidate_paths": "source_location_reference",
    "gold_path": "source_location_reference",
    "gold_paths": "source_location_reference",
    "trace_path": "source_location_reference",
    "span": "source_span_reference",
    "spans": "source_span_reference",
    "exact_span": "source_span_reference",
    "start_line": "source_span_reference",
    "end_line": "source_span_reference",
    "line_range": "source_span_reference",
    "gold_lines": "source_span_reference",
    "gold_spans": "source_span_reference",
    "gold": "gold_reference",
    "gold_labels": "gold_reference",
    "candidate": "candidate_reference",
    "candidates": "candidate_reference",
    "candidate_list": "candidate_reference",
    "candidate_order": "candidate_reference",
    "task_id": "task_or_repo_reference",
    "repo_name": "task_or_repo_reference",
    "repo_slug": "task_or_repo_reference",
    "repo_url": "task_or_repo_reference",
    "base_commit": "task_or_repo_reference",
    "trace_id": "trace_foreign_key_reference",
    "trace_key": "trace_foreign_key_reference",
    "event_id": "trace_foreign_key_reference",
    "foreign_key": "trace_foreign_key_reference",
    "raw": "provider_or_private_payload_reference",
    "raw_trace": "provider_or_private_payload_reference",
    "raw_prompt": "provider_or_private_payload_reference",
    "raw_response": "provider_or_private_payload_reference",
    "provider_payload": "provider_or_private_payload_reference",
    "snippet": "provider_or_private_payload_reference",
    "snippets": "provider_or_private_payload_reference",
    "content": "provider_or_private_payload_reference",
    "content_lines": "provider_or_private_payload_reference",
    "content_sha": "provider_or_private_payload_reference",
}

FIELD_CATEGORY_SUFFIX = (
    ("_path", "source_location_reference"),
    ("_paths", "source_location_reference"),
    ("_span", "source_span_reference"),
    ("_spans", "source_span_reference"),
    ("_task_id", "task_or_repo_reference"),
    ("_repo_id", "task_or_repo_reference"),
    ("_trace_id", "trace_foreign_key_reference"),
    ("_event_id", "trace_foreign_key_reference"),
)


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


def _rows_from_artifact(artifact: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = artifact.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _field_category(field_name: str) -> str:
    lowered = field_name.lower()
    if lowered in FIELD_CATEGORY_EXACT:
        return FIELD_CATEGORY_EXACT[lowered]
    for suffix, category in FIELD_CATEGORY_SUFFIX:
        if lowered.endswith(suffix):
            return category
    return ""


def _walk_field_categories(obj: Any) -> Counter[str]:
    counts: Counter[str] = Counter()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                category = _field_category(str(key))
                if category:
                    counts[category] += 1
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return counts


def _field_count(rows: list[dict[str, Any]]) -> int:
    total = 0

    def walk(value: Any) -> None:
        nonlocal total
        if isinstance(value, dict):
            total += len(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for row in rows:
        walk(row)
    return total


def _inspect_surface(surface: str, rows: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    counts = _walk_field_categories(rows)
    reconstructable_count = sum(counts.values())
    return {
        "anonymous_presence_id": f"scp{idx:04d}",
        "source_surface_bucket": surface,
        "row_count": len(rows),
        "inspected_field_count": _field_count(rows),
        "reconstructable_context_field_count": reconstructable_count,
        "source_location_reference_count": counts["source_location_reference"],
        "source_span_reference_count": counts["source_span_reference"],
        "gold_reference_count": counts["gold_reference"],
        "candidate_reference_count": counts["candidate_reference"],
        "task_or_repo_reference_count": counts["task_or_repo_reference"],
        "trace_foreign_key_reference_count": counts["trace_foreign_key_reference"],
        "provider_or_private_payload_reference_count": counts["provider_or_private_payload_reference"],
        "context_linkage_bucket": "reconstructable_context_available" if reconstructable_count else "no_reconstructable_context_fields",
    }


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _p1_2_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    p1_2_args = argparse.Namespace(
        p0_4_artifact=args.p0_4_artifact,
        p1_1_artifact=args.p1_1_artifact,
        private_queue_jsonl=args.private_queue_jsonl,
        private_labels_jsonl=args.private_labels_jsonl,
    )
    return intake._build_report(p1_2_args, checks)


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]], p1_2_checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    p1_1, p1_1_status = _load_json(args.p1_1_artifact)
    p1_3, p1_3_status = _load_json(args.p1_3_artifact)
    p1_4, p1_4_status = _load_json(args.p1_4_artifact)
    private_queue_rows, private_queue_status = _read_jsonl(args.private_queue_jsonl)
    private_label_rows, private_label_status = _read_jsonl(args.private_labels_jsonl)
    p1_2 = _p1_2_report(args, p1_2_checks) if private_label_status == "pass" else {}
    p1_2_manifest = p1_2.get("private_label_intake_manifest_records", [{}])
    if not isinstance(p1_2_manifest, list) or not p1_2_manifest:
        p1_2_manifest = [{}]
    p1_2_valid_count = int(p1_2_manifest[0].get("valid_record_count", 0) or 0)
    p1_2_error_count = int(p1_2_manifest[0].get("error_count", 0) or 0)

    surfaces = [
        ("p0_4_support_link_input_design_rows", _rows_from_artifact(p0_4, "support_link_input_design_records")),
        ("p1_1_public_queue_rows", _rows_from_artifact(p1_1, "sanitized_labeling_queue_records")),
        ("p1_1_private_queue_rows", private_queue_rows),
        ("p1_3_public_label_rows", _rows_from_artifact(p1_3, "sanitized_agent_generated_label_records")),
        ("p1_3_private_label_rows", private_label_rows),
        ("p1_4_public_audit_rows", _rows_from_artifact(p1_4, "sanitized_automated_label_audit_records")),
    ]
    presence_rows = [_inspect_surface(surface, rows, i) for i, (surface, rows) in enumerate(surfaces)]
    total_reconstructable = sum(int(row.get("reconstructable_context_field_count", 0) or 0) for row in presence_rows)
    category_totals = Counter({category: 0 for category in LINKAGE_CATEGORIES})
    for row in presence_rows:
        for category in LINKAGE_CATEGORIES:
            category_totals[category] += int(row.get(f"{category}_count", 0) or 0)
    missing_rows = [
        {
            "linkage_category_bucket": category,
            "present_count": category_totals[category],
            "missing_bucket": "missing_from_all_inspected_surfaces" if category_totals[category] == 0 else "present_in_inspected_surface",
        }
        for category in LINKAGE_CATEGORIES
    ]

    p1_2_ok = p1_2.get("status") == "private_label_intake_validator_real_labels_pass" and p1_2_valid_count == 18 and p1_2_error_count == 0 and p1_2.get("forbidden_scan", {}).get("status") == "pass"
    p1_4_ok = p1_4_status == "pass" and p1_4.get("status") in {"no_go_p1_4_low_evidence_labels", "automated_label_reliability_audit_pass"} and p1_4.get("forbidden_scan", {}).get("status") == "pass"
    context_available = total_reconstructable > 0
    p1_4_low_yield = p1_4.get("status") == "no_go_p1_4_low_evidence_labels"
    self_tests_ok = all(c["passed"] for c in checks)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not p1_2_ok:
        status = "no_go_p1_5r_p1_2_intake_failed"
    elif not p1_4_ok:
        status = "no_go_p1_5r_p1_4_reliability_failed"
    elif not context_available:
        status = "no_go_p1_5r_private_context_unavailable"
    elif p1_4_low_yield:
        status = "no_go_p1_5r_label_generation_low_informative_yield"
    else:
        status = "source_context_support_label_fill_pass"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "private_context_unavailable" if status == "no_go_p1_5r_private_context_unavailable" else "low_informative_yield" if status == "no_go_p1_5r_label_generation_low_informative_yield" else "p1_2_intake_failed" if status == "no_go_p1_5r_p1_2_intake_failed" else "p1_4_reliability_failed" if status == "no_go_p1_5r_p1_4_reliability_failed" else "" if status == "source_context_support_label_fill_pass" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p0_4_support_link_input_design", "load_status": p0_4_status, "source_status": str(p0_4.get("status", "") or ""), "source_schema": str(p0_4.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_4.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(_rows_from_artifact(p0_4, "support_link_input_design_records"))},
            {"input_artifact": "p1_1_private_labeling_queue_preparation", "load_status": p1_1_status, "source_status": str(p1_1.get("status", "") or ""), "source_schema": str(p1_1.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_1.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_1.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(_rows_from_artifact(p1_1, "sanitized_labeling_queue_records"))},
            {"input_artifact": "p1_3_agent_generated_support_label_fill", "load_status": p1_3_status, "source_status": str(p1_3.get("status", "") or ""), "source_schema": str(p1_3.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_3.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_3.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(_rows_from_artifact(p1_3, "sanitized_agent_generated_label_records"))},
            {"input_artifact": "p1_4_automated_label_reliability_audit", "load_status": p1_4_status, "source_status": str(p1_4.get("status", "") or ""), "source_schema": str(p1_4.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_4.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(_rows_from_artifact(p1_4, "sanitized_automated_label_audit_records"))},
            {"input_artifact": "p1_2_direct_private_label_intake", "load_status": "pass" if p1_2 else "not_run", "source_status": str(p1_2.get("status", "") or ""), "source_schema": str(p1_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_2.get("forbidden_scan"), dict) else "not_reported"), "record_count": p1_2_valid_count},
        ],
        "private_input_manifest_records": [
            {"manifest_name": "bea_v1_p1_1_support_labeling_queue", "schema_version": q.QUEUE_SCHEMA_VERSION, "read_status": private_queue_status, "record_count": len(private_queue_rows), "path_publicly_serialized": False, "storage_class": "project_ignored_private_jsonl"},
            {"manifest_name": "bea_v1_p1_3_agent_generated_support_labels", "schema_version": h.PRIVATE_SCHEMA_VERSION, "read_status": private_label_status, "record_count": len(private_label_rows), "p1_2_valid_record_count": p1_2_valid_count, "p1_2_label_error_count": p1_2_error_count, "path_publicly_serialized": False, "storage_class": "project_ignored_private_jsonl"},
        ],
        "source_context_linkage_field_presence_records": presence_rows,
        "missing_context_linkage_summary_records": missing_rows,
        "context_linkage_summary_records": _summary(presence_rows, "context_linkage_bucket"),
        "feasibility_summary_records": [{
            "inspected_surface_count": len(presence_rows),
            "inspected_row_count": sum(int(row.get("row_count", 0) or 0) for row in presence_rows),
            "reconstructable_context_field_count": total_reconstructable,
            "all_required_linkage_categories_missing": all(row["present_count"] == 0 for row in missing_rows),
            "source_context_available_for_improved_labels": context_available,
            "improved_label_generation_attempted": False,
            "guessed_labels_generated": False,
        }],
        "gate_records": [
            {"gate": "direct_p1_2_intake_pass", "passed": p1_2_ok, "threshold_relation": "boolean", "value": int(p1_2_ok), "threshold_value": 1},
            {"gate": "p1_4_reliability_artifact_available", "passed": p1_4_ok, "threshold_relation": "boolean", "value": int(p1_4_ok), "threshold_value": 1},
            {"gate": "reconstructable_source_context_available", "passed": context_available, "threshold_relation": "greater_than", "value": total_reconstructable, "threshold_value": 0},
            {"gate": "improved_label_generation_not_guessed", "passed": True, "threshold_relation": "boolean", "value": 1, "threshold_value": 1},
            {"gate": "p1_5_denominator_audit_authorized", "passed": False, "threshold_relation": "boolean", "value": 0, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "private_context_linkage_absent_no_improved_labels_generated" if status == "no_go_p1_5r_private_context_unavailable" else "label_generation_low_informative_yield" if status == "no_go_p1_5r_label_generation_low_informative_yield" else "p1_2_intake_failed" if status == "no_go_p1_5r_p1_2_intake_failed" else "p1_4_reliability_failed" if status == "no_go_p1_5r_p1_4_reliability_failed" else "source_context_available_for_improved_fill",
            "authorization": "improved_automated_support_label_feasibility_audit_only",
            "p1_5_denominator_audit_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "support_counterfactual_executed": False,
            "support_marginal_utility_claimed": False,
            "mechanism_evidence_claimed": False,
            "human_calibrated": False,
            "human_labels_claimed": False,
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
    linked_row = {"source_path": "bucketed", "start_line": "bucketed", "task_id": "bucketed", "provider_payload": "bucketed"}
    unlinked_row = {"anonymous_design_id": "sl0000", "queue_item_id": "ql0000", "support_relation_bucket": "missing_support_candidate"}
    linked_presence = _inspect_surface("fixture_linked_rows", [linked_row], 0)
    unlinked_presence = _inspect_surface("fixture_unlinked_rows", [unlinked_row], 1)
    status_vocab_ok = set(STATUSES) == {
        "source_context_support_label_fill_pass",
        "no_go_p1_5r_private_context_unavailable",
        "no_go_p1_5r_label_generation_low_informative_yield",
        "no_go_p1_5r_p1_2_intake_failed",
        "no_go_p1_5r_p1_4_reliability_failed",
        "fail_forbidden_scan",
        "fail_schema_contract",
    }
    checks = [
        _check("status_vocab_complete", status_vocab_ok),
        _check("detects_linkage_fields", linked_presence["reconstructable_context_field_count"] == 4),
        _check("no_go_when_no_linkage", unlinked_presence["reconstructable_context_field_count"] == 0 and unlinked_presence["context_linkage_bucket"] == "no_reconstructable_context_fields"),
        _check("gate_math_totals", linked_presence["source_location_reference_count"] == 1 and linked_presence["source_span_reference_count"] == 1 and linked_presence["task_or_repo_reference_count"] == 1 and linked_presence["provider_or_private_payload_reference_count"] == 1),
        _check("private_root_safety", not h._safe_private_path(Path("artifacts/not_private.jsonl"))),
        _check("scanner_accepts_presence_records", tg._scan_summary({"source_context_linkage_field_presence_records": [unlinked_presence]})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("scanner_rejects_task_key", tg._scan_summary({"task_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-5R improved automated support-label feasibility audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--p1-1-artifact", type=Path, default=DEFAULT_P1_1)
    parser.add_argument("--p1-3-artifact", type=Path, default=DEFAULT_P1_3)
    parser.add_argument("--p1-4-artifact", type=Path, default=DEFAULT_P1_4)
    parser.add_argument("--private-queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--private-labels-jsonl", type=Path, default=DEFAULT_PRIVATE_LABELS)
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
    summary = report["feasibility_summary_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, inspected_rows={summary['inspected_row_count']}, context_fields={summary['reconstructable_context_field_count']})")


if __name__ == "__main__":
    main()
