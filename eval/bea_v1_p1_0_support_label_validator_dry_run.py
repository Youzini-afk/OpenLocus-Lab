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


SCHEMA_VERSION = "bea_v1_p1_0_support_label_validator_dry_run.v1"
GENERATED_BY = "eval/bea_v1_p1_0_support_label_validator_dry_run.py"
CLAIM_LEVEL = "bea_v1_p1_0_support_label_validator_dry_run_only"
MODE = "bea_v1_p1_0_support_label_validator_dry_run"
PHASE = "BEA-v1-P1-0"
DEFAULT_OUT = Path("artifacts/bea_v1_p1_0_support_label_validator_dry_run/bea_v1_p1_0_support_label_validator_dry_run_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_P0_5_OUT = Path(".openlocus/research-private/bea_v1_p1_0_synthetic_support_labels.jsonl")

STATUSES = (
    "support_label_validator_dry_run_pass",
    "no_go_support_label_validator_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PATTERN = (
    ("hit", "hit", "target_and_support_hit", "precondition", "safe_ambiguous_support"),
    ("hit", "miss", "target_only", "constraint", "support_overbroad_risk"),
    ("miss", "hit", "support_only", "cross_file_dependency", "target_binding_leak_risk"),
    ("miss", "miss", "neither", "usage_example", "safe_ambiguous_support"),
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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not h._safe_private_path(path):
        raise ValueError("synthetic private labels must stay under .openlocus/research-private")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _synthetic_rows(design_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = h._template_rows(design_rows)
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        target, support, conjunction, role, risk = PATTERN[i % len(PATTERN)]
        out.append({
            **row,
            "target_hit_bucket": target,
            "support_hit_bucket": support,
            "conjunction_bucket": conjunction,
            "support_evidence_role_bucket": role,
            "leakage_risk_bucket": risk,
            "annotator_confidence_bucket": "synthetic_fixture_high",
            "annotation_status": "synthetic_fixture_labeled",
        })
    return out


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    design_rows = h._design_rows(p0_4)
    synthetic_rows = _synthetic_rows(design_rows)
    write_status = "not_requested"
    if args.emit_private_fixture:
        try:
            _write_jsonl(args.private_fixture_out, synthetic_rows)
            write_status = "written_project_private"
        except Exception:
            write_status = "write_failed"
    valid, errors = h._validate_private_labels(synthetic_rows, {str(row.get("anonymous_design_id", "") or "") for row in design_rows})
    sanitized = h._sanitize_labels(valid)
    p0_4_ok = p0_4_status == "pass" and p0_4.get("status") == "support_link_input_design_pass" and p0_4.get("forbidden_scan", {}).get("status") == "pass"
    dry_run_ok = p0_4_ok and len(design_rows) == 18 and len(valid) == 18 and not errors and all(c["passed"] for c in checks)
    status = "support_label_validator_dry_run_pass" if dry_run_ok else "no_go_support_label_validator_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if dry_run_ok else "required_input_artifact_unavailable_or_validation_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [{
            "input_artifact": "p0_4_support_link_input_design",
            "load_status": p0_4_status,
            "source_status": str(p0_4.get("status", "") or ""),
            "source_schema": str(p0_4.get("schema_version", "") or ""),
            "forbidden_scan_status": str(p0_4.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_4.get("forbidden_scan"), dict) else "not_reported"),
            "record_count": len(design_rows),
        }],
        "synthetic_private_fixture_manifest_records": [{
            "manifest_name": "bea_v1_p1_0_synthetic_support_label_fixture",
            "schema_version": h.PRIVATE_SCHEMA_VERSION,
            "record_count": len(synthetic_rows),
            "records_written": args.emit_private_fixture and write_status == "written_project_private",
            "write_status": write_status,
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_synthetic_private_jsonl",
        }],
        "validator_dry_run_records": [{
            "surface": "support_label_private_validator",
            "row_kind": "synthetic_fixture_validation_summary",
            "design_row_count": len(design_rows),
            "synthetic_private_row_count": len(synthetic_rows),
            "valid_private_row_count": len(valid),
            "error_count": len(errors),
            "fixture_is_real_label_data": False,
            "counterfactual_ready": False,
        }],
        "sanitized_synthetic_label_records": sanitized,
        "label_relation_summary_records": _summary(sanitized, "support_relation_bucket"),
        "label_conjunction_summary_records": _summary(sanitized, "conjunction_bucket"),
        "label_risk_summary_records": _summary(sanitized, "leakage_risk_bucket"),
        "gate_records": [
            {"gate": "p0_4_design_artifact_available", "passed": p0_4_ok, "threshold_relation": "boolean", "value": int(p0_4_ok), "threshold_value": 1},
            {"gate": "synthetic_private_fixture_validates", "passed": len(valid) == 18 and not errors, "threshold_relation": "equals", "value": len(valid), "threshold_value": 18},
            {"gate": "real_private_labels_available", "passed": False, "threshold_relation": "boolean_required_for_counterfactual", "value": 0, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "synthetic_validator_path_passed_real_labels_still_required" if dry_run_ok else "required_inputs_unavailable",
            "authorization": "validator_path_test_only",
            "real_private_labeling_authorized": dry_run_ok,
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
    rows = _synthetic_rows(design)
    valid, errors = h._validate_private_labels(rows, {"sl0000"})
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("synthetic_rows_validate", len(valid) == 1 and not errors),
        _check("fixture_not_real_label_data", rows[0]["annotation_status"] == "synthetic_fixture_labeled"),
        _check("sanitized_hides_design_id", "anonymous_design_id" not in h._sanitize_labels(valid)[0]),
        _check("scanner_accepts_sanitized", tg._scan_summary({"sanitized_synthetic_label_records": h._sanitize_labels(valid)})["status"] == "pass"),
        _check("scanner_rejects_forbidden_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P1-0 support-label validator dry run")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--emit-private-fixture", action="store_true")
    parser.add_argument("--private-fixture-out", type=Path, default=DEFAULT_P0_5_OUT)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, synthetic_labels={len(report['sanitized_synthetic_label_records'])})")


if __name__ == "__main__":
    main()
