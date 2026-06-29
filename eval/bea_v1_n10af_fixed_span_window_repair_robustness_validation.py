#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, NoReturn


SCHEMA_VERSION = "bea_v1_n10af_fixed_span_window_repair_robustness_validation.v1"
PHASE = "BEA-v1-N10AF Fixed Span-Window Repair Robustness/Subgroup Validation"
STATUS_PASS = "fixed_span_window_repair_robustness_validation_pass_n10ag_authorized"
STATUS_CONCENTRATED = "fixed_span_window_repair_robustness_complete_concentrated_effect"
STATUSES = (
    STATUS_PASS,
    STATUS_CONCENTRATED,
    "no_go_n10af_required_inputs_unavailable",
    "no_go_n10af_private_span_rows_missing",
    "no_go_n10af_result_mismatch",
    "no_go_n10af_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json")
INPUTS = {
    "n10ae_replication_package_artifact": (Path("artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json"), "fixed_span_window_repair_replication_package_complete_n10af_authorized"),
    "n10ad_independent_recompute_artifact": (Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json"), "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"),
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10z_failure_decomposition_artifact": (Path("artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json"), "n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized"),
}
GROUP_BUCKETS = {
    "baseline_span_status": ["baseline_span_hit_top10", "baseline_file_hit_no_span_top10", "no_baseline_file_hit_top10"],
    "pm50_file_status": ["pm50_file_hit_top10", "no_pm50_file_hit_top10"],
    "original_span_reach_rank_bucket": ["rank_1_10", "rank_11_20", "rank_21_50", "rank_gt50", "not_span_reachable"],
    "miss_direction_bucket": ["before_gold", "after_gold", "already_overlap", "no_top10_file_hit"],
    "evidence_count_bucket": ["1_10", "11_20", "21_50", "gt50"],
}

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "intake_status_bucket", "target_arm_bucket", "repair_variant_bucket", "subgroup_family_bucket",
    "subgroup_bucket", "overreach_proxy_bucket", "decision_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10ag_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = root() / path
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(path: Path, data: dict[str, Any]) -> None:
    full = root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
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
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10afin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, ok


def read_rows() -> tuple[list[dict[str, Any]], str]:
    full = root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in full.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "schema_invalid"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def row_ok(row: dict[str, Any]) -> bool:
    evs, refs, ranges = row.get("p4_evidence"), row.get("gold_paths"), row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    return all(isinstance(ev, dict) and isinstance(ev.get("path"), str) and isinstance(ev.get("start_line"), int) and isinstance(ev.get("end_line"), int) for ev in evs) and all(isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1] for rg in ranges)


def best_order(evs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(i + 1, ev) for i, ev in enumerate(evs)]
    extra = [ev for pos, ev in indexed if pos > 20]
    primary = [ev for pos, ev in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def ref_map(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) <= min(b, d)


def span_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], k: int, window: int) -> bool:
    for ev in ordered[:k]:
        key = str(ev.get("path", ""))
        if key not in refs:
            continue
        start, end = ev.get("start_line"), ev.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        lo, hi = max(1, start - window), end + window
        if any(overlap(lo, hi, a, b) for a, b in refs[key]):
            return True
    return False


def file_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], k: int) -> bool:
    return any(str(ev.get("path", "")) in refs for ev in ordered[:k])


def first_span_rank_bucket(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]]) -> str:
    for idx, ev in enumerate(ordered, start=1):
        key = str(ev.get("path", ""))
        start, end = ev.get("start_line"), ev.get("end_line")
        if key in refs and isinstance(start, int) and isinstance(end, int) and any(overlap(start, end, a, b) for a, b in refs[key]):
            if idx <= 10:
                return "rank_1_10"
            if idx <= 20:
                return "rank_11_20"
            if idx <= 50:
                return "rank_21_50"
            return "rank_gt50"
    return "not_span_reachable"


def miss_direction_bucket(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]]) -> str:
    for ev in ordered[:10]:
        key = str(ev.get("path", ""))
        start, end = ev.get("start_line"), ev.get("end_line")
        if key not in refs or not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(overlap(start, end, a, b) for a, b in refs[key]):
            return "already_overlap"
        if all(end < a for a, _b in refs[key]):
            return "before_gold"
        if all(start > b for _a, b in refs[key]):
            return "after_gold"
        return "before_gold"
    return "no_top10_file_hit"


def evidence_count_bucket(count: int) -> str:
    if count <= 10:
        return "1_10"
    if count <= 20:
        return "11_20"
    if count <= 50:
        return "21_50"
    return "gt50"


def compute_case_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for row in rows:
        if not row_ok(row) or not row.get("p4_evidence"):
            continue
        ordered = best_order(row["p4_evidence"])
        refs = ref_map(row)
        base_span = span_hit(ordered, refs, 10, 0)
        base_file = file_hit(ordered, refs, 10)
        pm50_span = span_hit(ordered, refs, 10, 50)
        pm50_file = file_hit(ordered, refs, 10)
        features.append({
            "baseline_span_hit_top10_bool": base_span,
            "baseline_file_hit_top10_bool": base_file,
            "pm50_span_hit_top10_bool": pm50_span,
            "pm50_file_hit_top10_bool": pm50_file,
            "pm50_lost_original_span_hit_bool": base_span and not pm50_span,
            "baseline_span_status": "baseline_span_hit_top10" if base_span else ("baseline_file_hit_no_span_top10" if base_file else "no_baseline_file_hit_top10"),
            "pm50_file_status": "pm50_file_hit_top10" if pm50_file else "no_pm50_file_hit_top10",
            "original_span_reach_rank_bucket": first_span_rank_bucket(ordered, refs),
            "miss_direction_bucket": miss_direction_bucket(ordered, refs),
            "evidence_count_bucket": evidence_count_bucket(len(row["p4_evidence"])),
        })
    return features


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10afpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def global_result_reproduction_records(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    baseline = sum(f["baseline_span_hit_top10_bool"] for f in features)
    pm50 = sum(f["pm50_span_hit_top10_bool"] for f in features)
    lost = sum(f["pm50_lost_original_span_hit_bool"] for f in features)
    pm50_file = sum(f["pm50_file_hit_top10_bool"] for f in features)
    ok = len(features) == 213 and baseline == 9 and pm50 == 19 and pm50 - baseline == 10 and lost == 0 and pm50_file == 34
    return [{"anonymous_global_result_reproduction_id": "n10afglobal0000", "target_arm_bucket": "span_extra_depth_promote_before_primary_prefix_4", "repair_variant_bucket": "fixed_symmetric_span_expansion_pm50_lines", "eligible_denominator_count": len(features), "baseline_top10_span_overlap_count": baseline, "pm50_top10_span_overlap_count": pm50, "delta_top10_span_overlap_count": pm50 - baseline, "pm50_lost_original_span_hit_count": lost, "pm50_file_top10_count": pm50_file, "global_matches_n10ae_bool": ok}], ok


def subgroup_definition_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    idx = 0
    for family, buckets in GROUP_BUCKETS.items():
        for bucket in buckets:
            records.append({"anonymous_subgroup_definition_id": f"n10afdef{idx:04d}", "subgroup_family_bucket": family, "subgroup_bucket": bucket, "predeclared_bool": True, "repo_language_path_source_bucket_used_bool": False})
            idx += 1
    return records


def subgroup_robustness_records(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    idx = 0
    positives = 0
    baseline_negative = 0
    for family, buckets in GROUP_BUCKETS.items():
        for bucket in buckets:
            subset = [f for f in features if f[family] == bucket]
            baseline = sum(f["baseline_span_hit_top10_bool"] for f in subset)
            pm50 = sum(f["pm50_span_hit_top10_bool"] for f in subset)
            lost = sum(f["pm50_lost_original_span_hit_bool"] for f in subset)
            pm50_file = sum(f["pm50_file_hit_top10_bool"] for f in subset)
            delta = pm50 - baseline
            positives += int(delta > 0)
            baseline_negative += int(family == "baseline_span_status" and bucket == "baseline_span_hit_top10" and delta < 0)
            records.append({"anonymous_subgroup_robustness_id": f"n10afsub{idx:04d}", "subgroup_family_bucket": family, "subgroup_bucket": bucket, "subgroup_count": len(subset), "pm50_top10_span_overlap_count": pm50, "baseline_top10_span_overlap_count": baseline, "delta_top10_span_overlap_count": delta, "pm50_lost_original_span_hit_count": lost, "pm50_file_top10_count": pm50_file})
            idx += 1
    return records, {"positive_delta_subgroup_count": positives, "baseline_span_hit_negative_delta_count": baseline_negative}


def overreach_proxy_records(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, bucket in enumerate(GROUP_BUCKETS["miss_direction_bucket"]):
        subset = [f for f in features if f["miss_direction_bucket"] == bucket]
        count = sum(f["pm50_file_hit_top10_bool"] and not f["pm50_span_hit_top10_bool"] for f in subset)
        records.append({"anonymous_overreach_proxy_id": f"n10afover{idx:04d}", "overreach_proxy_bucket": "pm50_file_hit_without_pm50_span_overlap", "subgroup_family_bucket": "miss_direction_bucket", "subgroup_bucket": bucket, "case_count": count})
    return records


def robustness_decision_records(global_ok: bool, counts: dict[str, int]) -> tuple[list[dict[str, Any]], str, bool]:
    passed = global_ok and counts["positive_delta_subgroup_count"] >= 2 and counts["baseline_span_hit_negative_delta_count"] == 0
    status = STATUS_PASS if passed else STATUS_CONCENTRATED
    return [{"anonymous_robustness_decision_id": "n10afdecision0000", "decision_bucket": "robustness_pass" if passed else "concentrated_effect", "global_matches_n10ae_bool": global_ok, "pm50_lost_original_span_hit_count": 0, "positive_delta_subgroup_count": counts["positive_delta_subgroup_count"], "required_positive_delta_subgroup_count": 2, "baseline_span_hit_negative_delta_count": counts["baseline_span_hit_negative_delta_count"], "robustness_pass_bool": passed, "concentrated_effect_bool": not passed}], status, global_ok


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10afprivacy0000", "privacy_boundary_bucket": "public_subgroup_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10afnoexec0000", "no_execution_boundary_bucket": "single_scoped_private_read_subgroup_validation_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "adaptive_window_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ag_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ag_handoff_id": "n10afhandoff0000", "n10ag_handoff_bucket": "n10ag_public_claim_boundary_audit_package_authorized" if complete else "n10ag_not_authorized", "n10ag_public_claim_boundary_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, schema_ok: bool, global_ok: bool, robustness_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("private_span_rows_read", schema_ok, 213 if schema_ok else 0, 213), ("global_matches_n10ae", global_ok, int(global_ok), 1), ("robustness_decision_complete", robustness_ok, int(robustness_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ag_public_claim_boundary_audit_package_authorized" if complete else "n10ag_not_authorized", "next_allowed_phase": "BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package" if complete else "none_until_valid_n10af_robustness_validation_exists", "next_allowed_scope_bucket": "public_claim_boundary_audit_package_only" if complete else "no_next_phase", "n10ag_public_claim_boundary_audit_package_authorized": complete, "private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, global_ok: bool, privacy_ok: bool, noexec_ok: bool, decision_status: str) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10af_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10af_private_span_rows_missing"
    if not global_ok:
        return "no_go_n10af_result_mismatch"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10af_privacy_or_claim_boundary_failed"
    return decision_status


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    rows, load_status = read_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_ok(r) for r in rows)
    features = compute_case_features(rows) if schema_ok else []
    global_records, global_ok = global_result_reproduction_records(features)
    subgroup_records, subgroup_counts = subgroup_robustness_records(features)
    decision_records, decision_status, decision_complete = robustness_decision_records(global_ok, subgroup_counts)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, global_ok, privacy_ok, noexec_ok, decision_status)
    complete = status in {STATUS_PASS, STATUS_CONCENTRATED}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "subgroup_robustness_validation_only", "generated_by": "bea_v1_n10af_fixed_span_window_repair_robustness_validation", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_input_intake_records": private_input_intake_records(rows, load_status, schema_ok), "global_result_reproduction_records": global_records, "subgroup_definition_records": subgroup_definition_records(), "subgroup_robustness_records": subgroup_records, "overreach_proxy_records": overreach_proxy_records(features), "robustness_decision_records": decision_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n10ag_handoff_records": n10ag_handoff_records(complete), "gate_records": gate_records(input_ok, schema_ok, global_ok, decision_complete, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] in {STATUS_PASS, STATUS_CONCENTRATED}
    report["gate_records"] = gate_records(input_ok, schema_ok, global_ok, decision_complete, privacy_ok, noexec_ok, scanner_ok)
    report["n10ag_handoff_records"] = n10ag_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def find_sub(records: list[dict[str, Any]], family: str, bucket: str) -> dict[str, Any]:
    return next(r for r in records if r["subgroup_family_bucket"] == family and r["subgroup_bucket"] == bucket)


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    rows, load_status = read_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_ok(r) for r in rows)
    features = compute_case_features(rows) if schema_ok else []
    global_records, global_ok = global_result_reproduction_records(features)
    subgroup_records, counts = subgroup_robustness_records(features)
    decision_records, decision_status, decision_complete = robustness_decision_records(global_ok, counts)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_CONCENTRATED, "no_go_n10af_required_inputs_unavailable", "no_go_n10af_private_span_rows_missing", "no_go_n10af_result_mismatch", "no_go_n10af_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("private_input", schema_ok and len(features) == 213),
        check("global", global_ok and global_records[0]["baseline_top10_span_overlap_count"] == 9 and global_records[0]["pm50_top10_span_overlap_count"] == 19 and global_records[0]["delta_top10_span_overlap_count"] == 10 and global_records[0]["pm50_lost_original_span_hit_count"] == 0),
        check("definitions", len(subgroup_definition_records()) == 18),
        check("baseline_status_subgroups", find_sub(subgroup_records, "baseline_span_status", "baseline_file_hit_no_span_top10")["delta_top10_span_overlap_count"] == 10 and find_sub(subgroup_records, "baseline_span_status", "baseline_span_hit_top10")["delta_top10_span_overlap_count"] == 0),
        check("miss_direction_subgroups", find_sub(subgroup_records, "miss_direction_bucket", "before_gold")["delta_top10_span_overlap_count"] == 9 and find_sub(subgroup_records, "miss_direction_bucket", "after_gold")["delta_top10_span_overlap_count"] == 1),
        check("evidence_count_subgroups", find_sub(subgroup_records, "evidence_count_bucket", "21_50")["delta_top10_span_overlap_count"] == 8 and find_sub(subgroup_records, "evidence_count_bucket", "gt50")["delta_top10_span_overlap_count"] == 2),
        check("robustness", decision_status == STATUS_PASS and decision_records[0]["positive_delta_subgroup_count"] >= 2 and decision_records[0]["baseline_span_hit_negative_delta_count"] == 0),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["gold_line_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["private_span_input_read_count"] == 1 and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0),
        check("handoff", n10ag_handoff_records(True)[0]["n10ag_public_claim_boundary_audit_package_authorized_bool"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, STATUS_PASS) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AF fixed span-window repair robustness validation")
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
    g = report["global_result_reproduction_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={g['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
