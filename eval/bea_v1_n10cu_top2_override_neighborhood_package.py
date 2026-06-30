#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10cu_top2_override_neighborhood_package.v1"
PHASE = "BEA-v1-N10CU Top2 Override Neighborhood Public Package"
STATUS_COMPLETE = "top2_override_neighborhood_package_complete_n10cv_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cu_required_public_inputs_unavailable",
    "no_go_n10cu_n10ct_chain_mismatch",
    "no_go_n10cu_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json")
PUBLIC_INPUTS = {
    "n10ct_top2_override_neighborhood_artifact": (Path("artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json"), "top2_override_window_neighborhood_sweep_complete_n10cu_authorized"),
    "n10cs_local_saturation_package_artifact": (Path("artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json"), "local_saturation_package_complete_n10ct_authorized"),
    "n10cr_local_saturation_sweep_artifact": (Path("artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json"), "mechanism_guided_local_saturation_sweep_complete_n10cs_authorized"),
}
VARIANTS = tuple(f"short75_225_top2_all_pm{pm}" for pm in (200, 225, 250, 275, 300, 325, 350, 375, 400))
KEY_VARIANTS = (
    "short75_225_top2_all_pm200",
    "short75_225_top2_all_pm275",
    "short75_225_top2_all_pm300",
    "short75_225_top2_all_pm325",
    "short75_225_top2_all_pm350",
    "short75_225_top2_all_pm375",
    "short75_225_top2_all_pm400",
)
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "package_bucket", "variant_bucket", "boundary_bucket", "no_recompute_boundary_bucket", "n10cv_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation", "decision_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = repo_root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + str(key))
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            key = marker.rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10cuin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, artifacts, ok


def by_variant(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in artifact.get("variant_result_records", []):
        if isinstance(row, dict) and isinstance(row.get("variant_bucket"), str):
            out[row["variant_bucket"]] = row
    return out


def package_records(n10ct: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    variants = by_variant(n10ct)
    summary = n10ct.get("neighborhood_summary_records", [{}])[0] if isinstance(n10ct.get("neighborhood_summary_records"), list) and n10ct.get("neighborhood_summary_records") else {}
    expected = {
        "short75_225_top2_all_pm200": (25, 31, 3200, 6200),
        "short75_225_top2_all_pm275": (26, 32, 3500, 6500),
        "short75_225_top2_all_pm300": (26, 32, 3600, 6600),
        "short75_225_top2_all_pm325": (26, 32, 3700, 6700),
        "short75_225_top2_all_pm350": (26, 32, 3800, 6800),
        "short75_225_top2_all_pm375": (26, 32, 3900, 6900),
        "short75_225_top2_all_pm400": (27, 33, 4000, 7000),
    }
    ok = len(variants) == 9 and all(v in variants for v in VARIANTS)
    ok = ok and all((variants[v].get("top10_span_overlap_count"), variants[v].get("top20_span_overlap_count"), variants[v].get("cost_proxy_top10"), variants[v].get("cost_proxy_top20")) == values for v, values in expected.items())
    ok = ok and variants["short75_225_top2_all_pm275"].get("lost_pm300_top10_hits") == 0
    ok = ok and variants["short75_225_top2_all_pm275"].get("cost_proxy_top10", 0) < variants["short75_225_top2_all_pm300"].get("cost_proxy_top10", 0)
    ok = ok and all(variants[v].get("candidate_pool_changed_bool") is False and variants[v].get("candidate_order_changed_bool") is False for v in VARIANTS)
    ok = ok and summary.get("minimum_pm_for_26_32") == 275 and summary.get("max_observed_top10_span_overlap_count") == 27 and summary.get("max_observed_top20_span_overlap_count") == 33
    package = [{"anonymous_neighborhood_package_id": "n10cupackage0000", "package_bucket": "n10ct_top2_override_neighborhood_public_package", "n10ct_status_complete_bool": n10ct.get("status") == "top2_override_window_neighborhood_sweep_complete_n10cu_authorized", "fixed_variant_count": len(variants), "pm_window_values_count": 9, "minimum_pm_for_26_32": summary.get("minimum_pm_for_26_32"), "max_observed_top10_span_overlap_count": summary.get("max_observed_top10_span_overlap_count"), "max_observed_top20_span_overlap_count": summary.get("max_observed_top20_span_overlap_count"), "package_consistent_bool": ok}]
    rows = []
    for idx, variant in enumerate(KEY_VARIANTS):
        row = variants.get(variant, {})
        rows.append({"anonymous_key_variant_id": f"n10cukey{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": row.get("top10_span_overlap_count"), "top20_span_overlap_count": row.get("top20_span_overlap_count"), "cost_proxy_top10": row.get("cost_proxy_top10"), "cost_proxy_top20": row.get("cost_proxy_top20"), "lost_pm300_top10_hits": row.get("lost_pm300_top10_hits"), "decision_bucket": row.get("decision_bucket"), "candidate_pool_changed_bool": row.get("candidate_pool_changed_bool"), "candidate_order_changed_bool": row.get("candidate_order_changed_bool")})
    boundary = [{"anonymous_policy_boundary_id": "n10cuboundary0000", "boundary_bucket": "fixed_top2_pm_neighborhood_only", "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "top3_override_bool": False, "medium_long_extra_gate_bool": False, "gold_policy_input_bool": False, "outcome_policy_input_bool": False, "file_identity_policy_input_bool": False, "privacy_boundary_complete_bool": True}]
    return package, rows, boundary, ok


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_recompute_id": "n10cunorecompute0000", "no_recompute_boundary_bucket": "public_package_only", "private_read_count": 0, "recompute_count": 0, "new_variant_count": 0, "runtime_default_promotion_count": 0, "candidate_generation_count": 0, "candidate_add_remove_reorder_count": 0, "adaptive_tuning_count": 0, "top3_override_count": 0, "no_recompute_boundary_valid_bool": True}], True


def n10cv_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cv_handoff_id": "n10cuhandoff0000", "n10cv_handoff_bucket": "n10cv_followup_authorized" if complete else "n10cv_not_authorized", "n10cv_authorized_bool": complete, "next_followup_bucket": "pm400_gain_mechanism_or_pm400_neighborhood_oracle_scoped" if complete else "none", "private_read_authorized_next_bool": False, "recompute_authorized_next_bool": False, "new_variant_authorized_next_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_reorder_authorized_bool": False, "top3_override_authorized_bool": False, "adaptive_tuning_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def gate_records(input_ok: bool, package_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("n10ct_package_facts", package_ok), ("no_private_read_or_recompute", norecompute_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cv_authorized" if complete else "n10cv_not_authorized", "next_allowed_phase": "BEA-v1-N10CV Follow-up Around pm400 Gain" if complete else "none_until_top2_override_package_valid", "next_allowed_scope_bucket": "pm400_gain_mechanism_or_pm400_neighborhood_oracle_scoped" if complete else "no_next_phase", "n10cv_authorized": complete, "private_read_authorized": False, "recompute_authorized": False, "new_variant_authorized": False, "runtime_or_default_authorized": False, "existing_evaluator_hook_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "top3_override_authorized": False, "adaptive_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, package_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cu_required_public_inputs_unavailable"
    if not package_ok:
        return "no_go_n10cu_n10ct_chain_mismatch"
    if not norecompute_ok:
        return "no_go_n10cu_privacy_or_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, key_rows, boundary_rows, package_ok = package_records(artifacts.get("n10ct_top2_override_neighborhood_artifact", {}))
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, package_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "public_top2_override_neighborhood_package_only", "generated_by": "bea_v1_n10cu_top2_override_neighborhood_package", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "neighborhood_package_records": package_rows, "key_variant_package_records": key_rows, "policy_boundary_records": boundary_rows, "no_private_recompute_records": norecompute_rows, "n10cv_handoff_records": n10cv_handoff_records(complete), "gate_records": gate_records(input_ok, package_ok, norecompute_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cv_handoff_records"] = n10cv_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, package_ok, norecompute_ok, scanner_ok)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, artifacts, input_ok = input_artifact_records()
    package_rows, key_rows, boundary_rows, package_ok = package_records(artifacts.get("n10ct_top2_override_neighborhood_artifact", {}))
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cu_required_public_inputs_unavailable", "no_go_n10cu_n10ct_chain_mismatch", "no_go_n10cu_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 3),
        check("package", package_ok and package_rows[0]["minimum_pm_for_26_32"] == 275 and package_rows[0]["max_observed_top10_span_overlap_count"] == 27),
        check("key_variants", len(key_rows) == len(KEY_VARIANTS) and any(r["variant_bucket"] == "short75_225_top2_all_pm400" and r["top10_span_overlap_count"] == 27 for r in key_rows)),
        check("pm275", any(r["variant_bucket"] == "short75_225_top2_all_pm275" and r["top10_span_overlap_count"] == 26 and r["lost_pm300_top10_hits"] == 0 for r in key_rows)),
        check("boundary", boundary_rows[0]["top3_override_bool"] is False and boundary_rows[0]["medium_long_extra_gate_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_mismatch", status_for(True, True, False, True) == "no_go_n10cu_n10ct_chain_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10cv_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["top3_override_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CU top2 override neighborhood public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")


if __name__ == "__main__":
    main()
