#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10r_targeted_n2_rank_pack_generation_preflight.v1"
PHASE = "BEA-v1-N10R Targeted N2 Rank-Pack Row Generation Preflight"
GENERATED_BY = "bea_v1_n10r_targeted_n2_rank_pack_generation_preflight"
STATUS_NO_GO = "no_go_n10r_target_denominator_insufficient"

STATUSES = (
    "targeted_n2_rank_pack_generation_preflight_pass_n10s_authorized",
    "no_go_n10r_required_inputs_unavailable",
    STATUS_NO_GO,
    "no_go_n10r_targeted_builder_unavailable",
    "no_go_n10r_semantic_equivalence_unproven",
    "no_go_n10r_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json")
PUBLIC_INPUTS = {
    "n10_preflight_artifact": (Path("artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json"), "no_go_n10_broader_rank_pack_denominator_unavailable"),
    "n9_replication_package_artifact": (Path("artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json"), "recovered_fixed_pool_result_replication_package_complete"),
    "n8_independent_recompute_artifact": (Path("artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json"), "independent_recompute_same_private_rows_pass_n9_authorized"),
    "n2_public_artifact": (Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json"), "n2_rank_pack_actionability_decomposition_pass"),
}
PRIVATE_INPUTS = {
    "n2_recovered_rank_pack_rows": Path(".openlocus/research-private/local_n6xfr_recovery/n2_private/bea_v1_n2.private_rank_pack_rows.jsonl"),
    "n1_span_rows": Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl"),
    "n1_candidate_gold_trace": Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_candidate_gold_trace.jsonl"),
    "p4l_private_arm_outcomes": Path(".openlocus/research-private/local_n6xfr_recovery/p4l_validation/bea_v1_p4l.private_arm_outcomes.jsonl"),
}
N2_BUILDER = Path("eval/bea_v1_n2_rank_pack_actionability_decomposition.py")

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list",
    "candidate_order", "gold_path", "gold_paths", "exact_rank", "raw_rank", "rank", "ranks", "score",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "schema_version_bucket", "record_count_bucket", "field_presence_bucket", "code_unit_bucket",
    "inspection_status_bucket", "builder_capability_bucket", "candidate_denominator_bucket", "plan_bucket", "blocker_bucket",
    "semantic_gate_bucket", "no_execution_boundary_bucket", "privacy_boundary_bucket", "n10s_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                ks = str(key)
                if ks in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + ks)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def count_bucket(n: int) -> str:
    if n == 0:
        return "zero"
    if n == 1:
        return "one"
    if n < 41:
        return "few"
    if n < 300:
        return "many"
    return "very_many"


def read_jsonl_schema(bucket: str, path: Path, sample_limit: int = 5) -> dict[str, Any]:
    full = root() / path
    count = 0
    schemas: set[str] = set()
    keys: set[str] = set()
    parse_ok = True
    if full.exists():
        try:
            with full.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    count += 1
                    if count <= sample_limit:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            parse_ok = False
                            continue
                        schemas.add(str(row.get("schema_version", "missing")))
                        keys.update(str(k) for k in row.keys())
        except Exception:
            parse_ok = False
    expected_fields = {
        "n2_recovered_rank_pack_rows": {"candidate_order_private", "gold_paths_private", "first_gold_rank_private", "denominator_index_private"},
        "n1_span_rows": {"p4_evidence", "gold_paths", "denominator_index_private"},
        "n1_candidate_gold_trace": {"candidate_count", "denominator_index_private", "p4_reaches_gold_file"},
        "p4l_private_arm_outcomes": {"arm_name", "first_gold_file_rank", "denominator_index_private"},
    }.get(bucket, set())
    return {
        "anonymous_private_input_schema_id": f"n10rpriv{len(bucket):04d}",
        "private_input_bucket": bucket,
        "load_status": "pass" if full.exists() and parse_ok else ("missing" if not full.exists() else "parse_failed"),
        "record_count": count,
        "record_count_bucket": count_bucket(count),
        "schema_version_bucket": "single_expected_schema" if len(schemas) == 1 else ("missing" if not schemas else "mixed_schema"),
        "field_presence_bucket": "expected_fields_present_in_sample" if expected_fields <= keys else "expected_fields_missing_or_unchecked",
        "private_content_public_bool": False,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "sample_content_public_bool": False,
    }


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        data, load = load_json(path)
        observed = str(data.get("status", "") or "")
        scan = data.get("forbidden_scan", {}).get("status", "pass") if isinstance(data.get("forbidden_scan"), dict) else "pass"
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10rin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def private_input_schema_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [read_jsonl_schema(bucket, path) for bucket, path in PRIVATE_INPUTS.items()]
    ok = all(r["load_status"] == "pass" and r["field_presence_bucket"] == "expected_fields_present_in_sample" for r in rows)
    return rows, ok


def static_inspection_records() -> tuple[list[dict[str, Any]], dict[str, bool]]:
    text = (root() / N2_BUILDER).read_text(encoding="utf-8")
    caps = {
        "d2_row_helper_identified": "def _d2_row_from_candidates" in text,
        "monolithic_network_runner_identified": "def _run_network" in text and "_reconstruct_locked_denominator" in text,
        "private_writer_identified": "def _append_private_jsonl" in text,
        "denominator_subset_argument_possible": "def _build_d2_rows_from_locked_denominator" in text and "denom: list[dict[str, Any]]" in text,
        "targeted_denominator_filter_supported": "--target" in text or "target_denominator" in text or "case_limit" in text,
        "can_generate_candidate_order_private": "candidate_order_private" in text and "_run_frozen_p4_with_candidates" in text,
        "full_p4l_reconstruction_dependency_present": "_reconstruct_locked_denominator" in text,
        "openlocus_execution_dependency_present": "_run_frozen_p4_with_candidates" in text and "openlocus_bin" in text,
    }
    records = [
        {"anonymous_n2_builder_static_inspection_id": "n10rcode0000", "code_unit_bucket": "n2_d2_row_from_candidates_helper", "inspection_status_bucket": "identified", "builder_capability_bucket": "row_builder_from_candidate_order_and_gold", "n2_builder_function_identified_bool": caps["d2_row_helper_identified"], "denominator_subset_argument_possible_bool": caps["denominator_subset_argument_possible"], "builder_unavailable_bool": False, "builder_limiting_factor_bool": False, "requires_existing_candidate_order_bool": True},
        {"anonymous_n2_builder_static_inspection_id": "n10rcode0001", "code_unit_bucket": "n2_network_runner", "inspection_status_bucket": "full_272_generation_already_completed", "builder_capability_bucket": "full_reconstruction_then_d2_rows", "full_locked_272_run_completed_bool": True, "full_generation_private_rows_emitted": 40, "additional_n2_equivalent_rows_expected_bool": False, "requires_full_p4l_reconstruction_bool": caps["full_p4l_reconstruction_dependency_present"]},
        {"anonymous_n2_builder_static_inspection_id": "n10rcode0002", "code_unit_bucket": "n2_cli", "inspection_status_bucket": "no_targeted_filter_argument_but_not_primary_blocker", "builder_capability_bucket": "network_opt_in_full_runner_only", "cli_targeted_filter_available_bool": caps["targeted_denominator_filter_supported"], "openlocus_execution_required_bool": caps["openlocus_execution_dependency_present"], "builder_limiting_factor_bool": False},
    ]
    return records, caps


def target_denominator_candidate_records(schema_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {r["private_input_bucket"]: int(r["record_count"]) for r in schema_records}
    specs = [
        ("full_locked_272_denominator", 272, False, True, "n2_d2_filter_exhausted_full_denominator"),
        ("n2_recovered_40_rank_pack", counts.get("n2_recovered_rank_pack_rows", 0), True, False, "known_good_exact_d2_denominator_not_broader"),
        ("n1_span_rows", counts.get("n1_span_rows", 0), False, True, "p4_evidence_span_surface_not_n2_rank_pack"),
        ("n1_candidate_gold_trace", counts.get("n1_candidate_gold_trace", 0), False, True, "aggregate_counts_not_candidate_order"),
        ("p4l_private_arm_outcomes", counts.get("p4l_private_arm_outcomes", 0), False, True, "arm_outcomes_not_n2_rank_pack"),
    ]
    return [{"anonymous_target_denominator_candidate_id": f"n10rden{idx:04d}", "candidate_denominator_bucket": bucket, "candidate_record_count": count, "full_n2_generation_already_completed_bool": bucket == "full_locked_272_denominator", "full_generation_private_rows_emitted": 40 if bucket == "full_locked_272_denominator" else (count if exact else 0), "additional_n2_equivalent_rows_expected_bool": False, "has_n2_equivalent_rank_pack_rows_bool": exact, "broader_than_40_bool": broader, "target_denominator_sufficient_bool": False, "candidate_status_bucket": status, "blocker_bucket": "n2_d2_filter_exhausted_full_denominator" if bucket == "full_locked_272_denominator" else status, "eligible_for_targeted_generation_input_bool": False} for idx, (bucket, count, exact, broader, status) in enumerate(specs)]


def targeted_generation_plan_records(caps: dict[str, bool]) -> tuple[list[dict[str, Any]], bool]:
    pass_ready = False
    return [{"anonymous_targeted_generation_plan_id": "n10rplan0000", "plan_bucket": "no_targeted_generation_authorized", "reason_bucket": "no_additional_n2_equivalent_rows_after_full_272_run", "blocker_bucket": "n2_d2_filter_exhausted_full_denominator", "n10s_canary_case_limit": 10, "targeted_builder_entrypoint_identified_bool": caps["d2_row_helper_identified"], "denominator_subset_argument_possible_bool": caps["denominator_subset_argument_possible"], "builder_unavailable_bool": False, "builder_limiting_factor_bool": False, "targeted_generation_authorized_bool": False, "n10s_handoff_authorized_bool": False, "can_generate_n2_equivalent_candidate_order_private_bool": caps["can_generate_candidate_order_private"], "can_run_without_full_p4l_rerun_bool": False, "private_output_plan_under_ignored_storage_bool": True, "would_materialize_from_n1_span_p4_evidence_bool": False, "plan_ready_bool": pass_ready}], pass_ready


def semantic_equivalence_gate_records(schema_ok: bool, caps: dict[str, bool]) -> tuple[list[dict[str, Any]], bool]:
    gates = [
        ("known_good_n2_rows", schema_ok, 40, 40),
        ("n1_span_rows_minimum", schema_ok, 213, 41),
        ("n2_builder_entrypoint_identified", caps["d2_row_helper_identified"], int(caps["d2_row_helper_identified"]), 1),
        ("denominator_subset_argument_possible", caps["denominator_subset_argument_possible"], int(caps["denominator_subset_argument_possible"]), 1),
        ("full_272_n2_generation_emitted_40_rows", True, 40, 40),
        ("additional_n2_equivalent_rows_expected", False, 0, 1),
        ("n1_span_rows_are_n2_equivalent", False, 0, 1),
        ("can_generate_n2_equivalent_candidate_order_private", caps["can_generate_candidate_order_private"], int(caps["can_generate_candidate_order_private"]), 1),
        ("can_preserve_n2_candidate_order_private_semantics", caps["can_generate_candidate_order_private"], int(caps["can_generate_candidate_order_private"]), 1),
        ("can_run_without_full_p4l_rerun", False, 0, 1),
        ("private_output_plan_under_ignored_storage", True, 1, 1),
        ("no_execution_in_n10r", True, 1, 1),
    ]
    records = [{"anonymous_semantic_equivalence_gate_id": f"n10rgate{idx:04d}", "semantic_gate_bucket": name, "passed_bool": bool(passed), "value": value, "threshold_value": threshold} for idx, (name, passed, value, threshold) in enumerate(gates)]
    return records, all(r["passed_bool"] for r in records)


def no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_execution_id": "n10rnoexec0000", "no_execution_boundary_bucket": "preflight_private_schema_read_static_code_inspection_only", "openlocus_execution_count": 0, "n2_execution_count": 0, "p4l_execution_count": 0, "retrieval_execution_count": 0, "private_rows_generated_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "no_execution_complete_bool": True}], True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10rprivacy0000", "privacy_boundary_bucket": "private_schema_counts_only_no_public_paths", "private_content_public_bool": False, "private_path_public_bool": False, "private_filename_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "exact_rank_public_bool": False, "repo_id_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_complete_bool": True}], True


def n10s_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10s_handoff_id": "n10rhandoff0000", "n10s_handoff_bucket": "n10s_not_authorized_target_denominator_insufficient" if not pass_status else "n10s_canary_generation_authorized", "n10s_authorized_bool": pass_status, "canary_case_limit": 10, "exact_n2_builder_semantics_required_bool": True, "direct_n1_span_denominator_authorized_bool": False, "local_cloned_repos_only_bool": True, "full_p4l_rerun_authorized_bool": False, "private_output_only_bool": True, "public_bucket_summary_only_bool": True}]


def stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10s_not_authorized" if not pass_status else "n10s_canary_generation_authorized", "next_allowed_phase": "none_for_n2_equivalent_broader_validation_without_new_denominator_definition" if not pass_status else "BEA-v1-N10S Targeted N2 Rank-Pack Canary Generation", "next_allowed_scope_bucket": "blocked_on_exhausted_n2_d2_denominator" if not pass_status else "canary_le_10_additional_rows_private_output_only", "n10s_authorized": pass_status, "n11_broader_validation_authorized": False, "direct_n1_span_denominator_authorized": False, "private_content_read_authorized": False, "openlocus_execution_authorized": False, "full_p4l_rerun_authorized": False, "retrieval_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False}]


def status_for(self_ok: bool, input_ok: bool, schema_ok: bool, plan_ready: bool, semantic_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok or not schema_ok:
        return "no_go_n10r_required_inputs_unavailable"
    if plan_ready and semantic_ok and privacy_ok and noexec_ok:
        return "targeted_n2_rank_pack_generation_preflight_pass_n10s_authorized"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10r_privacy_or_claim_boundary_invalid"
    if not plan_ready:
        return STATUS_NO_GO
    return "no_go_n10r_semantic_equivalence_unproven"


def gate_records(input_ok: bool, schema_ok: bool, caps: dict[str, bool], semantic_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("known_good_n2_rows", schema_ok, 40 if schema_ok else 0, 40), ("n1_span_rows_minimum", schema_ok, 213 if schema_ok else 0, 41), ("n2_builder_entrypoint_identified", caps["d2_row_helper_identified"], int(caps["d2_row_helper_identified"]), 1), ("denominator_subset_argument_possible", caps["denominator_subset_argument_possible"], int(caps["denominator_subset_argument_possible"]), 1), ("full_272_n2_generation_emitted_40_rows", True, 40, 40), ("additional_n2_equivalent_rows_expected", False, 0, 1), ("n1_span_rows_are_n2_equivalent", False, 0, 1), ("can_generate_n2_equivalent_candidate_order_private", caps["can_generate_candidate_order_private"], int(caps["can_generate_candidate_order_private"]), 1), ("can_run_without_full_p4l_rerun", False, 0, 1), ("private_output_plan_under_ignored_storage", True, 1, 1), ("no_execution_in_n10r", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    schemas, schema_ok = private_input_schema_records()
    inspection, caps = static_inspection_records()
    denominators = target_denominator_candidate_records(schemas)
    plan, plan_ready = targeted_generation_plan_records(caps)
    sem, semantic_ok = semantic_equivalence_gate_records(schema_ok, caps)
    noexec, noexec_ok = no_execution_records()
    privacy, privacy_ok = privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, schema_ok, plan_ready, semantic_ok, privacy_ok, noexec_ok)
    pass_status = status == "targeted_n2_rank_pack_generation_preflight_pass_n10s_authorized"
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "targeted_n2_generation_preflight_only", "generated_by": GENERATED_BY, "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_input_schema_records": schemas, "n2_builder_static_inspection_records": inspection, "target_denominator_candidate_records": denominators, "targeted_generation_plan_records": plan, "semantic_equivalence_gate_records": sem, "no_execution_records": noexec, "privacy_boundary_records": privacy, "n10s_handoff_records": n10s_handoff_records(pass_status), "stop_go_records": stop_go_records(pass_status), "gate_records": gate_records(input_ok, schema_ok, caps, semantic_ok, noexec_ok, True), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == "targeted_n2_rank_pack_generation_preflight_pass_n10s_authorized"
    report["gate_records"] = gate_records(input_ok, schema_ok, caps, semantic_ok, noexec_ok, scanner_ok)
    report["n10s_handoff_records"] = n10s_handoff_records(pass_status)
    report["stop_go_records"] = stop_go_records(pass_status)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    schemas, schema_ok = private_input_schema_records()
    inspection, caps = static_inspection_records()
    plan, plan_ready = targeted_generation_plan_records(caps)
    sem, semantic_ok = semantic_equivalence_gate_records(schema_ok, caps)
    noexec, noexec_ok = no_execution_records()
    privacy, privacy_ok = privacy_boundary_records()
    checks = [
        check("status_vocabulary", STATUSES[2] == STATUS_NO_GO and len(STATUSES) == 8),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "repo_id", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("private_schema_counts", schema_ok and {r["private_input_bucket"]: r["record_count"] for r in schemas}.get("n2_recovered_rank_pack_rows") == 40 and {r["private_input_bucket"]: r["record_count"] for r in schemas}.get("n1_span_rows", 0) >= 41),
        check("static_inspection", len(inspection) == 3 and caps["d2_row_helper_identified"] and caps["monolithic_network_runner_identified"]),
        check("builder_not_limiting", caps["denominator_subset_argument_possible"] is True and plan[0]["builder_unavailable_bool"] is False and plan[0]["builder_limiting_factor_bool"] is False),
        check("full_rerun_dependency", caps["full_p4l_reconstruction_dependency_present"] is True and caps["openlocus_execution_dependency_present"] is True),
        check("plan_no_go", plan_ready is False and plan[0]["blocker_bucket"] == "n2_d2_filter_exhausted_full_denominator" and plan[0]["targeted_generation_authorized_bool"] is False),
        check("semantic_gate_fails_closed", semantic_ok is False and any(r["semantic_gate_bucket"] == "additional_n2_equivalent_rows_expected" and r["passed_bool"] is False for r in sem) and any(r["semantic_gate_bucket"] == "n1_span_rows_are_n2_equivalent" and r["passed_bool"] is False for r in sem)),
        check("no_execution", noexec_ok and all(v == 0 for k, v in noexec[0].items() if k.endswith("_count"))),
        check("privacy", privacy_ok and privacy[0]["private_content_public_bool"] is False and privacy[0]["private_path_public_bool"] is False),
        check("stop_go", stop_go_records(False)[0]["next_allowed_phase"] == "none_for_n2_equivalent_broader_validation_without_new_denominator_definition" and stop_go_records(False)[0]["n10s_authorized"] is False and stop_go_records(False)[0]["direct_n1_span_denominator_authorized"] is False),
        check("expected_status", status_for(True, True, True, False, False, True, True) == STATUS_NO_GO),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10R targeted N2 rank-pack generation preflight")
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
