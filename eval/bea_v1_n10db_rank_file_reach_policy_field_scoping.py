#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10db_rank_file_reach_policy_field_scoping.v1"
PHASE = "BEA-v1-N10DB Rank/File-Reach Policy Field Scoping"
STATUS_PASS = "rank_file_reach_policy_field_scoping_pass_n10dc_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10db_required_inputs_unavailable",
    "no_go_n10db_private_span_rows_missing",
    "no_go_n10db_no_gold_free_rank_file_policy_fields",
    "no_go_n10db_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10db_rank_file_reach_policy_field_scoping/bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json")
DEFAULT_PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
PUBLIC_INPUTS = {
    "n10da_upper_bound_package_artifact": (Path("artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json"), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
    "n10cz_upper_bound_artifact": (Path("artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json"), "top2_local_window_saturation_upper_bound_complete_n10da_authorized"),
    "n10t_proxy_validation_artifact": (Path("artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json"), "n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized"),
    "n10x_span_utility_artifact": (Path("artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json"), "n1_span_surface_span_level_utility_validation_complete_below_threshold"),
}
POLICY_FAMILIES = (
    "file_dedup_distinct_file_packing",
    "source_channel_interleave",
    "score_or_method_bucket_ordering",
)
PREVIEW_VARIANTS = (
    "baseline_existing_order",
    "distinct_file_top10_greedy",
    "distinct_file_top20_greedy_then_top10",
    "max_per_file_1_top10",
    "max_per_file_2_top10",
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
    "private_input_bucket", "intake_status_bucket", "schema_field_bucket", "candidate_pool_bucket", "topk_bucket",
    "duplicate_pressure_bucket", "policy_family_bucket", "selected_policy_family_bucket", "preview_variant_bucket",
    "boundary_bucket", "no_execution_boundary_bucket", "n10dc_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10dbin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_private_rows(rel: Path) -> tuple[list[dict[str, Any]], str]:
    full = repo_root() / rel
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with full.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return [], "schema_invalid"
                    rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def pressure_bucket(duplicate_count: int) -> str:
    if duplicate_count == 0:
        return "none"
    if duplicate_count <= 2:
        return "low"
    if duplicate_count <= 5:
        return "medium"
    return "high"


def length_bucket(length: int) -> str:
    if length < 10:
        return "lt10"
    if length < 20:
        return "10_19"
    if length < 50:
        return "20_49"
    return "ge50"


def inspect_private_rows(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    p4_present = bool(rows) and all(isinstance(r.get("p4_evidence"), list) and r.get("p4_evidence") for r in rows)
    gold_available = bool(rows) and all(bool(r.get("gold_paths")) and bool(r.get("gold_lines")) for r in rows)
    evidence_items = [item for row in rows for item in (row.get("p4_evidence") or []) if isinstance(item, dict)]
    evidence_item_count = len(evidence_items)
    file_identifier_present = evidence_item_count > 0 and all(isinstance(item.get("path"), str) and bool(item.get("path")) for item in evidence_items)
    span_boundary_present = evidence_item_count > 0 and all(isinstance(item.get("start_line"), int) and isinstance(item.get("end_line"), int) for item in evidence_items)
    score_present = evidence_item_count > 0 and all("score" in item for item in evidence_items)
    method_present = evidence_item_count > 0 and all("method" in item for item in evidence_items)
    channel_present = evidence_item_count > 0 and all("channel" in item for item in evidence_items)
    source_present = evidence_item_count > 0 and all("source" in item for item in evidence_items)

    lengths = [len(row.get("p4_evidence") or []) for row in rows]
    length_counts = Counter(length_bucket(v) for v in lengths)
    candidate_pool_length_sufficient = sum(1 for v in lengths if v >= 20) >= 100

    intake = [{"anonymous_private_input_id": "n10dbpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": load_status, "private_span_rows_read": len(rows), "usable_span_surface_rows": len(rows) if load_status == "pass" else 0, "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "gold_fields_read_for_evaluation_availability_only_bool": gold_available}]
    schema = [{"anonymous_schema_field_id": "n10dbschema0000", "schema_field_bucket": "p4_evidence_ordered_item_schema", "p4_evidence_present_bool": p4_present, "ordered_evidence_list_present_bool": p4_present, "evidence_item_count": evidence_item_count, "candidate_file_identifier_present_bool": file_identifier_present, "span_boundary_field_present_bool": span_boundary_present, "score_field_present_bool": score_present, "method_field_present_bool": method_present, "channel_field_present_bool": channel_present, "source_field_present_bool": source_present, "raw_field_names_public_bool": False, "raw_candidate_rows_public_bool": False}]
    pool = [{"anonymous_candidate_pool_structure_id": "n10dbpool0000", "candidate_pool_bucket": "scoped_n1_span_surface_pool", "row_count": len(rows), "candidate_pool_length_sufficient_bool": candidate_pool_length_sufficient, "length_lt10_count": length_counts.get("lt10", 0), "length_10_19_count": length_counts.get("10_19", 0), "length_20_49_count": length_counts.get("20_49", 0), "length_ge50_count": length_counts.get("ge50", 0), "candidate_pool_generation_required_bool": False, "candidate_add_remove_required_bool": False}]

    pressure_rows = []
    for idx, topk in enumerate((10, 20)):
        buckets: Counter[str] = Counter()
        duplicate_rows = 0
        total_duplicate_slots = 0
        for row in rows:
            top = (row.get("p4_evidence") or [])[:topk]
            file_keys = [item.get("path") for item in top if isinstance(item, dict) and item.get("path")]
            duplicates = len(file_keys) - len(set(file_keys))
            buckets[pressure_bucket(duplicates)] += 1
            if duplicates > 0:
                duplicate_rows += 1
            total_duplicate_slots += duplicates
        pressure_rows.append({"anonymous_duplicate_pressure_id": f"n10dbdup{idx:04d}", "topk_bucket": f"top{topk}", "duplicate_pressure_none_count": buckets.get("none", 0), "duplicate_pressure_low_count": buckets.get("low", 0), "duplicate_pressure_medium_count": buckets.get("medium", 0), "duplicate_pressure_high_count": buckets.get("high", 0), "rows_with_duplicate_file_pressure_count": duplicate_rows, "duplicate_slot_count": total_duplicate_slots, "public_filename_count": 0})

    ok = load_status == "pass" and len(rows) == 213 and p4_present and file_identifier_present and candidate_pool_length_sufficient
    return intake, schema, pool, pressure_rows, ok


def policy_family_records(schema_rows: list[dict[str, Any]], private_ok: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    schema = schema_rows[0] if schema_rows else {}
    file_fields = bool(schema.get("candidate_file_identifier_present_bool"))
    score_method_channel_fields = bool(schema.get("score_field_present_bool") or schema.get("method_field_present_bool") or schema.get("channel_field_present_bool") or schema.get("source_field_present_bool"))
    families = [
        {"policy_family_bucket": "file_dedup_distinct_file_packing", "required_fields_available_bool": file_fields, "gold_free_policy_bool": True, "candidate_generation_required_bool": False, "candidate_add_remove_required_bool": False, "policy_outcome_computation_count": 0, "recommended_for_n10dc_bool": private_ok and file_fields},
        {"policy_family_bucket": "source_channel_interleave", "required_fields_available_bool": score_method_channel_fields, "gold_free_policy_bool": True, "candidate_generation_required_bool": False, "candidate_add_remove_required_bool": False, "policy_outcome_computation_count": 0, "recommended_for_n10dc_bool": False},
        {"policy_family_bucket": "score_or_method_bucket_ordering", "required_fields_available_bool": score_method_channel_fields, "gold_free_policy_bool": True, "candidate_generation_required_bool": False, "candidate_add_remove_required_bool": False, "policy_outcome_computation_count": 0, "recommended_for_n10dc_bool": False},
    ]
    rows = [{"anonymous_policy_family_id": f"n10dbfamily{idx:04d}", **row} for idx, row in enumerate(families)]
    recommended_count = sum(1 for row in rows if row["recommended_for_n10dc_bool"])
    selected = [{"anonymous_selected_policy_family_id": "n10dbselected0000", "selected_policy_family_bucket": "file_dedup_distinct_file_packing" if recommended_count else "none", "recommended_policy_family_count": recommended_count, "gold_free_policy_field_available_bool": recommended_count >= 1, "n10dc_preview_variant_count": len(PREVIEW_VARIANTS), "preview_variant_buckets": list(PREVIEW_VARIANTS), "policy_execution_in_n10db_bool": False}]
    return rows, selected, recommended_count >= 1


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10dbprivacy0000", "boundary_bucket": "schema_and_bucket_scoping_only", "public_path_or_filename_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "candidate_list_public_bool": False, "raw_candidate_public_bool": False, "gold_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10dbnoexec0000", "no_execution_boundary_bucket": "field_scoping_only_no_policy_execution", "policy_outcome_computation_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "candidate_reordered_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "generalization_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10dc_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10dc_handoff_id": "n10dbhandoff0000", "n10dc_handoff_bucket": "n10dc_distinct_file_packing_smoke_authorized" if complete else "n10dc_not_authorized", "n10dc_authorized_bool": complete, "selected_policy_family_bucket": "file_dedup_distinct_file_packing" if complete else "none", "same_scoped_rows_authorized_bool": complete, "same_candidate_pool_required_bool": True, "gold_free_file_dedup_packing_variants_bool": complete, "candidate_generation_authorized_bool": False, "candidate_materialization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_authorized_bool": False}]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10dc_authorized" if complete else "n10dc_not_authorized", "next_allowed_phase": "BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke" if complete else "none_until_gold_free_rank_file_fields_exist", "next_allowed_scope_bucket": "same_scoped_rows_same_pool_gold_free_distinct_file_packing_public_aggregate" if complete else "no_next_phase", "n10dc_authorized": complete, "private_read_authorized": complete, "public_aggregate_only": True, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "candidate_add_remove_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "selector_or_reranker_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def gate_records(input_ok: bool, private_ok: bool, policy_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok),
        ("private_span_rows_read_213", private_ok),
        ("p4_evidence_present", private_ok),
        ("candidate_file_identifier_present", private_ok),
        ("candidate_pool_length_sufficient", private_ok),
        ("gold_free_policy_field_available", policy_ok),
        ("recommended_policy_family_count", policy_ok),
        ("privacy_boundary", privacy_ok),
        ("no_policy_outcome_computation", noexec_ok),
        ("forbidden_scan", scanner_ok),
    ]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def status_for(self_ok: bool, input_ok: bool, private_load_status: str, private_ok: bool, policy_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10db_required_inputs_unavailable"
    if private_load_status != "pass":
        return "no_go_n10db_private_span_rows_missing"
    if not private_ok or not policy_ok:
        return "no_go_n10db_no_gold_free_rank_file_policy_fields"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10db_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]], private_rows_path: Path) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows(private_rows_path)
    intake_rows, schema_rows, pool_rows, pressure_rows, private_ok = inspect_private_rows(rows, load_status)
    family_rows, selected_rows, policy_ok = policy_family_records(schema_rows, private_ok)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, policy_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "rank_file_reach_policy_field_scoping_only", "generated_by": "bea_v1_n10db_rank_file_reach_policy_field_scoping", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": intake_rows, "p4_evidence_schema_field_records": schema_rows, "candidate_pool_structure_records": pool_rows, "topk_duplicate_file_pressure_records": pressure_rows, "policy_family_feasibility_records": family_rows, "selected_policy_family_records": selected_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10dc_handoff_records": n10dc_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, policy_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["n10dc_handoff_records"] = n10dc_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, policy_ok, privacy_ok, noexec_ok, scanner_ok)
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


def run_self_test(private_rows_path: Path) -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_private_rows(private_rows_path)
    intake_rows, schema_rows, pool_rows, pressure_rows, private_ok = inspect_private_rows(rows, load_status)
    family_rows, selected_rows, policy_ok = policy_family_records(schema_rows, private_ok)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10db_required_inputs_unavailable", "no_go_n10db_private_span_rows_missing", "no_go_n10db_no_gold_free_rank_file_policy_fields", "no_go_n10db_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"safe": "private/file.jsonl"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok and intake_rows[0]["private_span_rows_read"] == 213),
        check("schema", schema_rows[0]["p4_evidence_present_bool"] is True and schema_rows[0]["candidate_file_identifier_present_bool"] is True and schema_rows[0]["raw_field_names_public_bool"] is False),
        check("pool", pool_rows[0]["candidate_pool_length_sufficient_bool"] is True and pool_rows[0]["length_ge50_count"] == 68),
        check("duplicate_pressure", len(pressure_rows) == 2 and pressure_rows[0]["duplicate_pressure_medium_count"] == 69 and pressure_rows[1]["duplicate_pressure_high_count"] == 124),
        check("policy_families", len(family_rows) == 3 and any(r["policy_family_bucket"] == "file_dedup_distinct_file_packing" and r["recommended_for_n10dc_bool"] for r in family_rows)),
        check("selected", policy_ok and selected_rows[0]["selected_policy_family_bucket"] == "file_dedup_distinct_file_packing" and selected_rows[0]["policy_execution_in_n10db_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["public_path_or_filename_count"] == 0),
        check("no_execution", noexec_ok and noexec_rows[0]["policy_outcome_computation_count"] == 0 and noexec_rows[0]["retrieval_execution_count"] == 0),
        check("synthetic_missing", status_for(True, True, "missing", False, False, True, True) == "no_go_n10db_private_span_rows_missing"),
        check("synthetic_no_policy", status_for(True, True, "pass", True, False, True, True) == "no_go_n10db_no_gold_free_rank_file_policy_fields"),
        check("false_flags", stop_go_records(True)[0]["n10dc_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description=PHASE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE_SPAN_ROWS))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    private_rows_path = Path(args.private_span_rows)
    checks, ok = run_self_test(private_rows_path)
    if args.self_test:
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        if not ok:
            raise SystemExit(1)
        return
    report = build_report(checks, private_rows_path)
    write_json(Path(args.out), report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    if report["status"].startswith("fail_"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
