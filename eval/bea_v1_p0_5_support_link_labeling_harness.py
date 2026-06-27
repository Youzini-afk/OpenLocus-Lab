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

import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p0_5_support_link_labeling_harness.v1"
PRIVATE_SCHEMA_VERSION = "bea_v1_p0_5_support_link_private_label.v1"
GENERATED_BY = "eval/bea_v1_p0_5_support_link_labeling_harness.py"
CLAIM_LEVEL = "bea_v1_p0_5_support_link_labeling_harness_only"
MODE = "bea_v1_p0_5_support_link_labeling_harness"
PHASE = "BEA-v1-P0-5"

DEFAULT_OUT = Path("artifacts/bea_v1_p0_5_support_link_labeling_harness/bea_v1_p0_5_support_link_labeling_harness_report.json")
DEFAULT_P0_4 = Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json")
DEFAULT_TEMPLATE = Path(".openlocus/research-private/bea_v1_p0_5_support_link_label_template.jsonl")

STATUSES = (
    "support_link_labeling_harness_contract_pass",
    "support_link_labeling_harness_private_labels_pass",
    "no_go_support_link_labeling_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ALLOWED_RELATION = {"missing_support_candidate", "support_without_target", "target_without_support", "ambiguous_or_unknown"}
ALLOWED_HIT = {"hit", "miss", "unknown_not_labeled"}
ALLOWED_CONJUNCTION = {"target_and_support_hit", "target_only", "support_only", "neither", "ambiguous_unlabeled"}
ALLOWED_ROLE = {"precondition", "constraint", "cross_file_dependency", "usage_example", "ambiguous_or_unknown"}
ALLOWED_RISK = {"target_binding_leak_risk", "support_overbroad_risk", "safe_ambiguous_support", "unknown_not_labeled"}


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


def _private_root() -> Path:
    return Path(__file__).resolve().parents[1] / ".openlocus" / "research-private"


def _safe_private_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = _private_root().resolve()
        return str(resolved).startswith(str(root))
    except Exception:
        return False


def _design_rows(p0_4: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p0_4.get("support_link_input_design_records", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _template_rows(design_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in design_rows:
        out.append({
            "schema_version": PRIVATE_SCHEMA_VERSION,
            "anonymous_design_id": str(row.get("anonymous_design_id", "") or ""),
            "failure_category": str(row.get("failure_category", "") or ""),
            "action_layer": str(row.get("action_layer", "") or ""),
            "support_relation_bucket": str(row.get("support_relation_bucket", "ambiguous_or_unknown") or "ambiguous_or_unknown"),
            "target_hit_bucket": "unknown_not_labeled",
            "support_hit_bucket": "unknown_not_labeled",
            "conjunction_bucket": "ambiguous_unlabeled",
            "support_evidence_role_bucket": "ambiguous_or_unknown",
            "leakage_risk_bucket": "unknown_not_labeled",
            "annotator_confidence_bucket": "unknown_not_labeled",
            "annotation_status": "template_unlabeled",
        })
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not _safe_private_path(path):
        raise ValueError("private template path must stay under .openlocus/research-private")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _read_private_labels(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], "not_supplied"
    if not _safe_private_path(path):
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


def _derive_conjunction(target: str, support: str) -> str:
    if target == "hit" and support == "hit":
        return "target_and_support_hit"
    if target == "hit" and support == "miss":
        return "target_only"
    if target == "miss" and support == "hit":
        return "support_only"
    if target == "miss" and support == "miss":
        return "neither"
    return "ambiguous_unlabeled"


def _validate_private_labels(rows: list[dict[str, Any]], design_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        row_id = str(row.get("anonymous_design_id", "") or "")
        relation = str(row.get("support_relation_bucket", "") or "")
        target = str(row.get("target_hit_bucket", "") or "")
        support = str(row.get("support_hit_bucket", "") or "")
        conjunction = str(row.get("conjunction_bucket", "") or "")
        role = str(row.get("support_evidence_role_bucket", "") or "")
        risk = str(row.get("leakage_risk_bucket", "") or "")
        row_errors: list[str] = []
        if row.get("schema_version") != PRIVATE_SCHEMA_VERSION:
            row_errors.append("schema_version_mismatch")
        if row_id not in design_ids:
            row_errors.append("unknown_design_id")
        if row_id in seen:
            row_errors.append("duplicate_design_id")
        if relation not in ALLOWED_RELATION:
            row_errors.append("invalid_relation_bucket")
        if target not in ALLOWED_HIT:
            row_errors.append("invalid_target_hit_bucket")
        if support not in ALLOWED_HIT:
            row_errors.append("invalid_support_hit_bucket")
        if conjunction not in ALLOWED_CONJUNCTION:
            row_errors.append("invalid_conjunction_bucket")
        if role not in ALLOWED_ROLE:
            row_errors.append("invalid_support_role_bucket")
        if risk not in ALLOWED_RISK:
            row_errors.append("invalid_leakage_risk_bucket")
        expected = _derive_conjunction(target, support)
        if conjunction != expected:
            row_errors.append("conjunction_not_derived_from_hit_buckets")
        if row_errors:
            errors.append({"anonymous_error_id": f"le{i:04d}", "error_bucket": "|".join(sorted(row_errors))})
        else:
            seen.add(row_id)
            valid.append(row)
    return valid, errors


def _sanitize_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        out.append({
            "anonymous_label_id": f"lbl{i:04d}",
            "support_relation_bucket": str(row.get("support_relation_bucket", "") or ""),
            "target_hit_bucket": str(row.get("target_hit_bucket", "") or ""),
            "support_hit_bucket": str(row.get("support_hit_bucket", "") or ""),
            "conjunction_bucket": str(row.get("conjunction_bucket", "") or ""),
            "support_evidence_role_bucket": str(row.get("support_evidence_role_bucket", "") or ""),
            "leakage_risk_bucket": str(row.get("leakage_risk_bucket", "") or ""),
            "annotation_status_bucket": str(row.get("annotation_status", "") or ""),
        })
    return out


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_4, p0_4_status = _load_json(args.p0_4_artifact)
    design_rows = _design_rows(p0_4)
    template_rows = _template_rows(design_rows)
    template_written = False
    template_status = "not_requested"
    if args.emit_private_template:
        try:
            _write_jsonl(args.private_template_out, template_rows)
            template_written = True
            template_status = "written_project_private"
        except Exception:
            template_status = "write_failed"
    private_rows, private_status = _read_private_labels(args.private_labels_jsonl)
    valid_private, label_errors = _validate_private_labels(private_rows, {str(row.get("anonymous_design_id", "") or "") for row in design_rows}) if private_status == "pass" else ([], [])
    sanitized_labels = _sanitize_labels(valid_private)
    p0_4_ok = p0_4_status == "pass" and p0_4.get("status") == "support_link_input_design_pass" and p0_4.get("forbidden_scan", {}).get("status") == "pass"
    design_ok = len(design_rows) == 18
    template_ok = len(template_rows) == 18 and all(row.get("schema_version") == PRIVATE_SCHEMA_VERSION for row in template_rows)
    full_private_ok = private_status == "pass" and len(valid_private) == 18 and not label_errors
    if not (p0_4_ok and design_ok and template_ok and all(c["passed"] for c in checks)):
        status = "no_go_support_link_labeling_inputs_unavailable"
    elif full_private_ok:
        status = "support_link_labeling_harness_private_labels_pass"
    else:
        status = "support_link_labeling_harness_contract_pass"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status in {"support_link_labeling_harness_contract_pass", "support_link_labeling_harness_private_labels_pass"} else "required_input_artifact_unavailable_or_unexpected_status",
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
        "private_template_manifest_records": [{
            "manifest_name": "bea_v1_p0_5_support_link_private_label_template",
            "schema_version": PRIVATE_SCHEMA_VERSION,
            "record_count": len(template_rows),
            "records_written": template_written,
            "write_status": template_status,
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
        }],
        "private_label_input_status": private_status,
        "private_label_rows_supplied": args.private_labels_jsonl is not None,
        "private_label_rows_valid_count": len(valid_private),
        "private_label_rows_error_count": len(label_errors),
        "private_label_error_summary_records": _summary(label_errors, "error_bucket"),
        "support_link_labeling_harness_records": [{
            "anonymous_harness_id": str(row.get("anonymous_design_id", "") or ""),
            "failure_category": str(row.get("failure_category", "") or ""),
            "action_layer": str(row.get("action_layer", "") or ""),
            "required_private_schema": PRIVATE_SCHEMA_VERSION,
            "template_row_status": "ready_unlabeled_template",
            "public_release_boundary": "sanitized_bucket_summaries_only",
        } for row in design_rows],
        "support_link_sanitized_label_records": sanitized_labels,
        "label_relation_summary_records": _summary(sanitized_labels, "support_relation_bucket"),
        "label_conjunction_summary_records": _summary(sanitized_labels, "conjunction_bucket"),
        "label_risk_summary_records": _summary(sanitized_labels, "leakage_risk_bucket"),
        "gate_records": [
            {"gate": "p0_4_design_artifact_available", "passed": p0_4_ok, "threshold_relation": "boolean", "value": int(p0_4_ok), "threshold_value": 1},
            {"gate": "design_records_available", "passed": design_ok, "threshold_relation": "equals", "value": len(design_rows), "threshold_value": 18},
            {"gate": "private_template_rows_buildable", "passed": template_ok, "threshold_relation": "equals", "value": len(template_rows), "threshold_value": 18},
            {"gate": "private_label_rows_full_valid", "passed": full_private_ok, "threshold_relation": "boolean_optional", "value": int(full_private_ok), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "private_label_template_contract_ready_without_counterfactual" if status == "support_link_labeling_harness_contract_pass" else "private_label_rows_validated_without_counterfactual" if status == "support_link_labeling_harness_private_labels_pass" else "required_inputs_unavailable",
            "authorization": "private_support_labeling_or_label_validation_only",
            "counterfactual_execution_authorized": False,
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
    template = _template_rows(design)[0]
    valid, errors = _validate_private_labels([{**template, "target_hit_bucket": "hit", "support_hit_bucket": "miss", "conjunction_bucket": "target_only", "support_evidence_role_bucket": "constraint", "leakage_risk_bucket": "safe_ambiguous_support", "annotation_status": "labeled"}], {"sl0000"})
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("private_root_under_project", _private_root().name == "research-private"),
        _check("template_schema", template["schema_version"] == PRIVATE_SCHEMA_VERSION),
        _check("template_unlabeled", template["conjunction_bucket"] == "ambiguous_unlabeled"),
        _check("valid_label_accepts_derived_conjunction", len(valid) == 1 and not errors),
        _check("invalid_conjunction_rejected", bool(_validate_private_labels([{**template, "target_hit_bucket": "hit", "support_hit_bucket": "miss", "conjunction_bucket": "support_only"}], {"sl0000"})[1])),
        _check("sanitized_label_hides_design_id", "anonymous_design_id" not in _sanitize_labels(valid)[0]),
        _check("scanner_accepts_template_manifest", tg._scan_summary({"private_template_manifest_records": [{"path_publicly_serialized": False, "storage_class": "project_ignored_private_jsonl"}]})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-5 support-link labeling harness")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-4-artifact", type=Path, default=DEFAULT_P0_4)
    parser.add_argument("--emit-private-template", action="store_true")
    parser.add_argument("--private-template-out", type=Path, default=DEFAULT_TEMPLATE)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, harness_records={len(report['support_link_labeling_harness_records'])})")


if __name__ == "__main__":
    main()
