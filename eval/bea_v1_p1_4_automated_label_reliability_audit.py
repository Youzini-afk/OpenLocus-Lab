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
import bea_v1_p1_3_agent_generated_support_label_fill as p1_3  # noqa: E402
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p1_4_automated_label_reliability_audit.v1"
GENERATED_BY = "eval/bea_v1_p1_4_automated_label_reliability_audit.py"
CLAIM_LEVEL = "automated_label_reliability_audit_only"
MODE = "bea_v1_p1_4_automated_label_reliability_audit"
PHASE = "BEA-v1-P1-4"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json")
DEFAULT_P1_3 = Path("artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P1_1 = Path("artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json")
DEFAULT_QUEUE = Path(".openlocus/research-private/bea_v1_p1_1_support_labeling_queue.jsonl")
DEFAULT_PRIVATE_LABELS = Path(".openlocus/research-private/bea_v1_p1_3_agent_generated_support_labels.jsonl")

STATUSES = (
    "automated_label_reliability_audit_pass",
    "no_go_p1_4_low_evidence_labels",
    "no_go_p1_4_intake_or_origin_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

LABEL_ORIGIN = "agent_generated"
LABEL_METHOD_BUCKET = "deterministic_queue_field_heuristic"
UNKNOWN_HIT = "unknown_not_labeled"
UNKNOWN_CONJUNCTION = "ambiguous_unlabeled"
P1_5_INFORMATIVE_RATE_MIN = 0.50
P1_5_KNOWN_CONJUNCTION_RATE_MIN = 0.25
P1_5_UNKNOWN_BOTH_HIT_RATE_MAX = 0.50


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


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _label_informativeness(row: dict[str, Any]) -> dict[str, bool]:
    target_known = str(row.get("target_hit_bucket", "") or "") != UNKNOWN_HIT
    support_known = str(row.get("support_hit_bucket", "") or "") != UNKNOWN_HIT
    conjunction_known = str(row.get("conjunction_bucket", "") or "") != UNKNOWN_CONJUNCTION
    return {
        "known_target_or_support_hit": target_known or support_known,
        "known_conjunction": conjunction_known,
        "informative_label": target_known or support_known or conjunction_known,
        "unknown_both_hit": not target_known and not support_known,
    }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    flags = [_label_informativeness(row) for row in rows]
    known_target_or_support_hit_count = sum(1 for f in flags if f["known_target_or_support_hit"])
    known_conjunction_count = sum(1 for f in flags if f["known_conjunction"])
    informative_label_count = sum(1 for f in flags if f["informative_label"])
    unknown_both_hit_count = sum(1 for f in flags if f["unknown_both_hit"])
    return {
        "label_count": total,
        "known_target_or_support_hit_count": known_target_or_support_hit_count,
        "known_target_or_support_hit_rate": _rate(known_target_or_support_hit_count, total),
        "known_conjunction_count": known_conjunction_count,
        "known_conjunction_rate": _rate(known_conjunction_count, total),
        "informative_label_count": informative_label_count,
        "informative_label_rate": _rate(informative_label_count, total),
        "unknown_both_hit_count": unknown_both_hit_count,
        "unknown_both_hit_rate": _rate(unknown_both_hit_count, total),
    }


def _origin_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "label_origin_agent_generated_count": sum(1 for row in rows if row.get("label_origin") == LABEL_ORIGIN),
        "label_method_deterministic_count": sum(1 for row in rows if row.get("label_method_bucket") == LABEL_METHOD_BUCKET),
        "human_calibrated_false_count": sum(1 for row in rows if row.get("human_calibrated") is False),
    }


def _sanitized_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        flags = _label_informativeness(row)
        out.append({
            "anonymous_audit_label_id": f"alra{i:04d}",
            "label_origin_bucket": str(row.get("label_origin", "") or ""),
            "label_method_bucket": str(row.get("label_method_bucket", "") or ""),
            "human_calibrated": bool(row.get("human_calibrated", True)),
            "target_hit_bucket": str(row.get("target_hit_bucket", "") or ""),
            "support_hit_bucket": str(row.get("support_hit_bucket", "") or ""),
            "conjunction_bucket": str(row.get("conjunction_bucket", "") or ""),
            "leakage_risk_bucket": str(row.get("leakage_risk_bucket", "") or ""),
            "known_target_or_support_hit": flags["known_target_or_support_hit"],
            "known_conjunction": flags["known_conjunction"],
            "informative_label": flags["informative_label"],
            "unknown_both_hit": flags["unknown_both_hit"],
        })
    return out


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
    p1_3_artifact, p1_3_status = _load_json(args.p1_3_artifact)
    label_rows, label_read_status = _read_jsonl(args.private_labels_jsonl)
    p1_2 = _p1_2_report(args, p1_2_checks) if label_read_status == "pass" else {}
    p1_2_manifest = p1_2.get("private_label_intake_manifest_records", [{}])
    if not isinstance(p1_2_manifest, list) or not p1_2_manifest:
        p1_2_manifest = [{}]
    p1_2_valid_count = int(p1_2_manifest[0].get("valid_record_count", 0) or 0)
    p1_2_error_count = int(p1_2_manifest[0].get("error_count", 0) or 0)
    valid_rows = p1_2.get("sanitized_real_label_intake_records", [])
    direct_valid_private_rows, direct_label_errors = h._validate_private_labels(label_rows, {str(row.get("anonymous_design_id", "") or "") for row in label_rows}) if label_read_status == "pass" else ([], [])
    origin_counts = _origin_counts(label_rows)
    metrics = _metrics(label_rows)
    sanitized = _sanitized_rows(label_rows)

    p1_3_ok = p1_3_status == "pass" and p1_3_artifact.get("status") == "agent_generated_support_label_fill_pass" and p1_3_artifact.get("forbidden_scan", {}).get("status") == "pass"
    p1_2_ok = p1_2.get("status") == "private_label_intake_validator_real_labels_pass" and p1_2.get("forbidden_scan", {}).get("status") == "pass"
    label_rows_ok = label_read_status == "pass" and len(label_rows) == 18
    p1_2_valid_ok = p1_2_valid_count == 18 and len(valid_rows) == 18
    label_errors_ok = p1_2_error_count == 0 and not direct_label_errors
    origin_ok = origin_counts["label_origin_agent_generated_count"] == 18 and origin_counts["label_method_deterministic_count"] == 18 and origin_counts["human_calibrated_false_count"] == 18
    p1_5_thresholds_ok = metrics["informative_label_rate"] >= P1_5_INFORMATIVE_RATE_MIN and metrics["known_conjunction_rate"] >= P1_5_KNOWN_CONJUNCTION_RATE_MIN and metrics["unknown_both_hit_rate"] <= P1_5_UNKNOWN_BOTH_HIT_RATE_MAX
    self_tests_ok = all(c["passed"] for c in checks)
    intake_origin_ok = p1_3_ok and p1_2_ok and label_rows_ok and p1_2_valid_ok and label_errors_ok and origin_ok
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not intake_origin_ok:
        status = "no_go_p1_4_intake_or_origin_invalid"
    elif p1_5_thresholds_ok:
        status = "automated_label_reliability_audit_pass"
    else:
        status = "no_go_p1_4_low_evidence_labels"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "low_evidence_labels" if status == "no_go_p1_4_low_evidence_labels" else "" if status == "automated_label_reliability_audit_pass" else "intake_or_origin_invalid" if status == "no_go_p1_4_intake_or_origin_invalid" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p1_3_agent_generated_support_label_fill", "load_status": p1_3_status, "source_status": str(p1_3_artifact.get("status", "") or ""), "source_schema": str(p1_3_artifact.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_3_artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_3_artifact.get("forbidden_scan"), dict) else "not_reported"), "record_count": int(p1_3_artifact.get("agent_generated_label_manifest_records", [{}])[0].get("record_count", 0) or 0) if isinstance(p1_3_artifact.get("agent_generated_label_manifest_records"), list) and p1_3_artifact.get("agent_generated_label_manifest_records") else 0},
            {"input_artifact": "p1_2_direct_private_label_intake", "load_status": "pass" if p1_2 else "not_run", "source_status": str(p1_2.get("status", "") or ""), "source_schema": str(p1_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p1_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p1_2.get("forbidden_scan"), dict) else "not_reported"), "record_count": p1_2_valid_count},
        ],
        "automated_label_input_manifest_records": [{
            "manifest_name": "bea_v1_p1_3_agent_generated_support_labels",
            "schema_version": h.PRIVATE_SCHEMA_VERSION,
            "source_queue_schema_version": q.QUEUE_SCHEMA_VERSION,
            "read_status": label_read_status,
            "record_count": len(label_rows),
            "p1_2_valid_record_count": p1_2_valid_count,
            "label_error_count": p1_2_error_count + len(direct_label_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "origin_validation_records": [{
            **origin_counts,
            "label_count": len(label_rows),
            "label_origin_required_bucket": LABEL_ORIGIN,
            "label_method_required_bucket": LABEL_METHOD_BUCKET,
            "origin_gate_passed": origin_ok,
        }],
        "reliability_metric_records": [{
            **metrics,
            "informative_label_rate_threshold": P1_5_INFORMATIVE_RATE_MIN,
            "known_conjunction_rate_threshold": P1_5_KNOWN_CONJUNCTION_RATE_MIN,
            "unknown_both_hit_rate_max_threshold": P1_5_UNKNOWN_BOTH_HIT_RATE_MAX,
            "p1_5_denominator_audit_authorized": bool(intake_origin_ok and p1_5_thresholds_ok),
        }],
        "sanitized_automated_label_audit_records": sanitized,
        "label_origin_summary_records": _summary(sanitized, "label_origin_bucket"),
        "label_method_summary_records": _summary(sanitized, "label_method_bucket"),
        "label_conjunction_summary_records": _summary(sanitized, "conjunction_bucket"),
        "label_risk_summary_records": _summary(sanitized, "leakage_risk_bucket"),
        "label_informativeness_summary_records": [
            {"informativeness_bucket": "informative_label", "count": metrics["informative_label_count"], "rate": metrics["informative_label_rate"]},
            {"informativeness_bucket": "known_target_or_support_hit", "count": metrics["known_target_or_support_hit_count"], "rate": metrics["known_target_or_support_hit_rate"]},
            {"informativeness_bucket": "known_conjunction", "count": metrics["known_conjunction_count"], "rate": metrics["known_conjunction_rate"]},
            {"informativeness_bucket": "unknown_both_hit", "count": metrics["unknown_both_hit_count"], "rate": metrics["unknown_both_hit_rate"]},
        ],
        "label_error_summary_records": _summary(direct_label_errors, "error_bucket"),
        "gate_records": [
            {"gate": "p1_3_artifact_pass", "passed": p1_3_ok, "threshold_relation": "boolean", "value": int(p1_3_ok), "threshold_value": 1},
            {"gate": "direct_p1_2_intake_pass", "passed": p1_2_ok, "threshold_relation": "boolean", "value": int(p1_2_ok), "threshold_value": 1},
            {"gate": "private_label_rows", "passed": label_rows_ok, "threshold_relation": "equals", "value": len(label_rows), "threshold_value": 18},
            {"gate": "p1_2_valid_rows", "passed": p1_2_valid_ok, "threshold_relation": "equals", "value": p1_2_valid_count, "threshold_value": 18},
            {"gate": "label_errors_zero", "passed": label_errors_ok, "threshold_relation": "equals", "value": p1_2_error_count + len(direct_label_errors), "threshold_value": 0},
            {"gate": "origin_agent_generated_all", "passed": origin_counts["label_origin_agent_generated_count"] == 18, "threshold_relation": "equals", "value": origin_counts["label_origin_agent_generated_count"], "threshold_value": 18},
            {"gate": "method_deterministic_all", "passed": origin_counts["label_method_deterministic_count"] == 18, "threshold_relation": "equals", "value": origin_counts["label_method_deterministic_count"], "threshold_value": 18},
            {"gate": "human_calibrated_false_all", "passed": origin_counts["human_calibrated_false_count"] == 18, "threshold_relation": "equals", "value": origin_counts["human_calibrated_false_count"], "threshold_value": 18},
            {"gate": "informative_label_rate_for_p1_5", "passed": metrics["informative_label_rate"] >= P1_5_INFORMATIVE_RATE_MIN, "threshold_relation": "greater_or_equal", "value": metrics["informative_label_rate"], "threshold_value": P1_5_INFORMATIVE_RATE_MIN},
            {"gate": "known_conjunction_rate_for_p1_5", "passed": metrics["known_conjunction_rate"] >= P1_5_KNOWN_CONJUNCTION_RATE_MIN, "threshold_relation": "greater_or_equal", "value": metrics["known_conjunction_rate"], "threshold_value": P1_5_KNOWN_CONJUNCTION_RATE_MIN},
            {"gate": "unknown_both_hit_rate_for_p1_5", "passed": metrics["unknown_both_hit_rate"] <= P1_5_UNKNOWN_BOTH_HIT_RATE_MAX, "threshold_relation": "less_or_equal", "value": metrics["unknown_both_hit_rate"], "threshold_value": P1_5_UNKNOWN_BOTH_HIT_RATE_MAX},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "automated_labels_too_uninformative_for_denominator_audit" if status == "no_go_p1_4_low_evidence_labels" else "automated_label_reliability_thresholds_passed" if status == "automated_label_reliability_audit_pass" else "intake_or_origin_contract_failed",
            "authorization": "automated_label_reliability_audit_only",
            "p1_5_denominator_audit_authorized": bool(intake_origin_ok and p1_5_thresholds_ok),
            "support_counterfactual_execution_authorized": False,
            "support_counterfactual_executed": False,
            "support_marginal_utility_claimed": False,
            "human_labels_claimed": False,
            "human_calibrated_e_s_claimed": False,
            "mechanism_evidence_claimed": False,
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
    label = p1_3._label_row_from_queue(queue[0])
    informative = {**label, "target_hit_bucket": "hit", "conjunction_bucket": "ambiguous_unlabeled"}
    low_metrics = _metrics([label])
    mixed_metrics = _metrics([label, informative])
    valid_queue, queue_errors = intake._validate_queue(queue, {"sl0000"})
    intake_valid, intake_errors = intake._validate_intake_labels([label], valid_queue)
    public = _sanitized_rows([label])
    checks = [
        _check("status_vocab_nonempty", set(STATUSES) == {"automated_label_reliability_audit_pass", "no_go_p1_4_low_evidence_labels", "no_go_p1_4_intake_or_origin_invalid", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("private_root_safety_rejects_public_out", not h._safe_private_path(Path("artifacts/not_private.jsonl"))),
        _check("intake_gate_accepts_origin_label", len(valid_queue) == 1 and not queue_errors and len(intake_valid) == 1 and not intake_errors),
        _check("origin_counts_match", _origin_counts([label]) == {"label_origin_agent_generated_count": 1, "label_method_deterministic_count": 1, "human_calibrated_false_count": 1}),
        _check("metric_arithmetic_low_evidence", low_metrics["informative_label_count"] == 0 and low_metrics["known_conjunction_count"] == 0 and low_metrics["unknown_both_hit_count"] == 1),
        _check("metric_arithmetic_mixed", mixed_metrics["informative_label_count"] == 1 and mixed_metrics["known_target_or_support_hit_count"] == 1 and mixed_metrics["unknown_both_hit_count"] == 1 and mixed_metrics["informative_label_rate"] == 0.5),
        _check("low_evidence_thresholds_fail", not (low_metrics["informative_label_rate"] >= P1_5_INFORMATIVE_RATE_MIN and low_metrics["known_conjunction_rate"] >= P1_5_KNOWN_CONJUNCTION_RATE_MIN and low_metrics["unknown_both_hit_rate"] <= P1_5_UNKNOWN_BOTH_HIT_RATE_MAX)),
        _check("public_records_hide_private_ids", "anonymous_design_id" not in public[0] and "queue_item_id" not in public[0]),
        _check("scanner_accepts_public_records", tg._scan_summary({"sanitized_automated_label_audit_records": public})["status"] == "pass"),
        _check("scanner_rejects_forbidden_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-4 automated-label intake and reliability audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p1-3-artifact", type=Path, default=DEFAULT_P1_3)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--p1-1-artifact", type=Path, default=DEFAULT_P1_1)
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
    metrics = report["reliability_metric_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, labels={metrics['label_count']}, informative_rate={metrics['informative_label_rate']}, known_conjunction_rate={metrics['known_conjunction_rate']})")


if __name__ == "__main__":
    main()
