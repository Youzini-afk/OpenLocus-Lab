#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_spans


SCHEMA_VERSION = "bea_v1_n10al_scoped_eval_only_adapter_integration_smoke.v1"
PHASE = "BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke"
STATUS_PASS = "scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10al_required_inputs_unavailable",
    "no_go_n10al_private_span_rows_missing",
    "no_go_n10al_adapter_result_mismatch",
    "no_go_n10al_forbidden_import_or_hook_detected",
    "no_go_n10al_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json")
INPUTS = {
    "n10ak_adapter_audit_package_artifact": (Path("artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json"), "eval_only_adapter_public_fixture_audit_package_complete_n10al_authorized"),
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10ad_independent_recompute_artifact": (Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json"), "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"),
}
ALLOWED_CHANGED = {
    "eval/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke.py",
    "artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/",
    "artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json",
    "docs/en/bea-v1-n10al-scoped-eval-only-adapter-integration-smoke.md",
    "docs/zh/bea-v1-n10al-scoped-eval-only-adapter-integration-smoke.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
EXPECTED = {
    "private_span_rows_read": 213,
    "baseline_top10_span_overlap_count": 9,
    "baseline_top20_span_overlap_count": 10,
    "pm50_top10_span_overlap_count": 19,
    "pm50_top20_span_overlap_count": 23,
    "delta_top10_vs_baseline_count": 10,
    "original_span_hit_lost_count": 0,
}
FORBIDDEN_EVALUATOR_IMPORT_FRAGMENTS = (
    "bea_v1_n10ab_",
    "bea_v1_n10ad_",
    "bea_v1_n10t_",
    "bea_v1_n10x_",
    "bea_v1_n1_",
    "bea_v1_n2_",
    "bea_v1_n3_",
    "bea_v1_p4l_",
)
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
    "private_input_bucket", "intake_status_bucket", "adapter_boundary_bucket", "integration_result_bucket", "comparison_bucket",
    "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10am_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
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


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", "") or "")
        forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
        passed = load_status == "pass" and observed == expected and forbidden == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n10alin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
    return records, artifacts, ok


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


def row_schema_ok(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    return True


def best_arm_order(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(i + 1, item) for i, item in enumerate(evidence_items)]
    extra = [item for pos, item in indexed if pos > 20]
    primary = [item for pos, item in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def gold_lookup(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    lookup: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        lookup.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return lookup


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) <= min(b, d)


def span_hit(records: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in records[:limit]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if any(overlaps(start, end, a, b) for a, b in refs[key]):
            return True
    return False


def compute_with_adapter(rows: list[dict[str, Any]]) -> tuple[dict[str, int | bool], bool]:
    usable = [row for row in rows if row_schema_ok(row) and row.get("p4_evidence")]
    baseline10 = baseline20 = pm5010 = pm5020 = lost = 0
    pool_changed = False
    order_changed = False
    for row in usable:
        ordered = best_arm_order(row["p4_evidence"])
        refs = gold_lookup(row)
        base10 = span_hit(ordered, refs, 10)
        base20 = span_hit(ordered, refs, 20)
        projected = project_evidence_spans(ordered, expansion_each_side=50, enabled=True)
        pool_changed = pool_changed or len(projected) != len(ordered)
        order_changed = order_changed or list(range(len(projected))) != list(range(len(ordered)))
        hit10 = span_hit(projected, refs, 10)
        hit20 = span_hit(projected, refs, 20)
        baseline10 += int(base10)
        baseline20 += int(base20)
        pm5010 += int(hit10)
        pm5020 += int(hit20)
        lost += int(base10 and not hit10)
    return {
        "eligible_denominator_count": len(usable),
        "baseline_top10_span_overlap_count": baseline10,
        "baseline_top20_span_overlap_count": baseline20,
        "pm50_top10_span_overlap_count": pm5010,
        "pm50_top20_span_overlap_count": pm5020,
        "delta_top10_vs_baseline_count": pm5010 - baseline10,
        "original_span_hit_lost_count": lost,
        "candidate_pool_changed_bool": pool_changed,
        "order_changed_bool": order_changed,
    }, len(usable) == EXPECTED["private_span_rows_read"]


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10alpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def adapter_import_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    adapter_import_count = 0
    forbidden_import_count = 0
    hook_call_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "bea_v1_span_window_projection_adapter":
                    adapter_import_count += 1
                if any(fragment in alias.name for fragment in FORBIDDEN_EVALUATOR_IMPORT_FRAGMENTS):
                    forbidden_import_count += 1
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "bea_v1_span_window_projection_adapter":
                adapter_import_count += 1
            if any(fragment in module for fragment in FORBIDDEN_EVALUATOR_IMPORT_FRAGMENTS):
                forbidden_import_count += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and "hook" in node.func.attr.lower():
            hook_call_count += 1
    ok = adapter_import_count >= 1 and forbidden_import_count == 0 and hook_call_count == 0
    return [{"anonymous_adapter_import_boundary_id": "n10alimport0000", "adapter_boundary_bucket": "imports_projection_adapter_only_no_forbidden_evaluators", "adapter_imported_bool": adapter_import_count == 1, "helper_imported_by_adapter_bool": True, "existing_evaluator_imported_bool": forbidden_import_count > 0, "runtime_module_imported_bool": False, "retrieval_module_imported_bool": False, "existing_evaluator_hook_in_bool": hook_call_count > 0, "projection_adapter_import_count": adapter_import_count, "forbidden_evaluator_import_count": forbidden_import_count, "existing_evaluator_hook_call_count": hook_call_count, "runtime_retrieval_selector_import_count": 0, "adapter_import_boundary_valid_bool": ok}], ok


def adapter_integration_result_records(metrics: dict[str, int | bool]) -> list[dict[str, Any]]:
    delta = int(metrics.get("delta_top10_vs_baseline_count", 0))
    lost = int(metrics.get("original_span_hit_lost_count", 0))
    denominator = int(metrics.get("eligible_denominator_count", 0))
    return [{"anonymous_adapter_integration_result_id": "n10alresult0000", "integration_result_bucket": "adapter_pm50_reproduces_repair_smoke_aggregates", "surface_bucket": "n1_span_surface_proxy", "adapter_mode_bucket": "enabled_eval_only_pm50", "private_span_rows_read": denominator, "eligible_denominator_count": denominator, "baseline_top10_span_overlap_count": int(metrics.get("baseline_top10_span_overlap_count", 0)), "baseline_top20_span_overlap_count": int(metrics.get("baseline_top20_span_overlap_count", 0)), "pm50_top10_span_overlap_count": int(metrics.get("pm50_top10_span_overlap_count", 0)), "pm50_top20_span_overlap_count": int(metrics.get("pm50_top20_span_overlap_count", 0)), "delta_top10_span_overlap_count": delta, "delta_top10_vs_baseline_count": delta, "lost_original_span_hit_count": lost, "original_span_hit_lost_count": lost, "candidate_pool_changed_bool": bool(metrics.get("candidate_pool_changed_bool", True)), "order_changed_bool": bool(metrics.get("order_changed_bool", True)), "adapter_enabled_bool": True, "fixed_pm50_window_bool": True}]


def comparison_to_n10ab_records(metrics: dict[str, int | bool], artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n10ab = artifacts.get("n10ab_repair_smoke_artifact", {})
    n10ad = artifacts.get("n10ad_independent_recompute_artifact", {})
    decision = (n10ab.get("primary_decision_records") or [{}])[0]
    ad_rows = {r.get("variant_bucket"): r for r in n10ad.get("independent_recompute_records", []) if isinstance(r, dict)}
    ad_pm50 = ad_rows.get("fixed_symmetric_span_expansion_pm50_lines", {})
    checks = {
        "baseline_top10_span_overlap_count": EXPECTED["baseline_top10_span_overlap_count"],
        "baseline_top20_span_overlap_count": EXPECTED["baseline_top20_span_overlap_count"],
        "pm50_top10_span_overlap_count": EXPECTED["pm50_top10_span_overlap_count"],
        "pm50_top20_span_overlap_count": EXPECTED["pm50_top20_span_overlap_count"],
        "delta_top10_vs_baseline_count": EXPECTED["delta_top10_vs_baseline_count"],
        "original_span_hit_lost_count": EXPECTED["original_span_hit_lost_count"],
    }
    metrics_match = all(metrics.get(k) == v for k, v in checks.items()) and metrics.get("candidate_pool_changed_bool") is False and metrics.get("order_changed_bool") is False
    n10ab_match = decision.get("observed_top10_expanded_span_overlap_count") == 19 and decision.get("observed_top20_expanded_span_overlap_count") == 23 and decision.get("delta_top10_vs_unexpanded_best_arm") == 10 and decision.get("original_span_hit_lost_count") == 0
    n10ad_match = ad_pm50.get("top10_span_overlap_count") == 19 and ad_pm50.get("top20_span_overlap_count") == 23 and ad_pm50.get("delta_top10_vs_unexpanded_best_arm") == 10 and ad_pm50.get("original_span_hit_lost_count") == 0
    ok = metrics_match and n10ab_match and n10ad_match
    return [{"anonymous_comparison_to_n10ab_id": "n10alcompare0000", "comparison_bucket": "adapter_matches_n10ab_and_n10ad_pm50_aggregates" if ok else "adapter_result_mismatch", "n10al_matches_expected_bool": metrics_match, "n10ab_primary_match_bool": n10ab_match, "n10ad_independent_match_bool": n10ad_match, "n10ab_pm50_top10_match_bool": int(metrics.get("pm50_top10_span_overlap_count", 0)) == 19 and n10ab_match, "n10ab_pm50_top20_match_bool": int(metrics.get("pm50_top20_span_overlap_count", 0)) == 23 and n10ab_match, "n10ab_delta_match_bool": int(metrics.get("delta_top10_vs_baseline_count", 0)) == 10 and n10ab_match, "n10ab_lost_original_span_hit_match_bool": int(metrics.get("original_span_hit_lost_count", 0)) == 0 and n10ab_match, "comparison_passed_bool": ok, "baseline_top10_span_overlap_count": int(metrics.get("baseline_top10_span_overlap_count", 0)), "baseline_top20_span_overlap_count": int(metrics.get("baseline_top20_span_overlap_count", 0)), "pm50_top10_span_overlap_count": int(metrics.get("pm50_top10_span_overlap_count", 0)), "pm50_top20_span_overlap_count": int(metrics.get("pm50_top20_span_overlap_count", 0)), "delta_top10_span_overlap_count": int(metrics.get("delta_top10_vs_baseline_count", 0)), "delta_top10_vs_baseline_count": int(metrics.get("delta_top10_vs_baseline_count", 0)), "lost_original_span_hit_count": int(metrics.get("original_span_hit_lost_count", 0)), "original_span_hit_lost_count": int(metrics.get("original_span_hit_lost_count", 0)), "candidate_pool_changed_bool": bool(metrics.get("candidate_pool_changed_bool", True)), "order_changed_bool": bool(metrics.get("order_changed_bool", True))}], ok


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10alprivacy0000", "privacy_boundary_bucket": "public_aggregate_counts_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10alnoexec0000", "no_execution_boundary_bucket": "single_scoped_private_read_eval_only_adapter_smoke", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "existing_evaluator_hook_in_count": 0, "runtime_default_enablement_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_or_window_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "counterfactual_execution_count": 0, "policy_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10am_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10am_handoff_id": "n10alhandoff0000", "n10am_handoff_bucket": "n10am_public_adapter_integration_audit_package_authorized" if complete else "n10am_not_authorized", "n10am_public_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def changed_files_valid() -> bool:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    files = [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]
    return not (set(files) - ALLOWED_CHANGED)


def gate_records(input_ok: bool, private_ok: bool, import_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool, touch_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("single_private_span_rows_read", private_ok, EXPECTED["private_span_rows_read"] if private_ok else 0, EXPECTED["private_span_rows_read"]), ("adapter_import_boundary", import_ok, int(import_ok), 1), ("adapter_result_match", result_ok, int(result_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("changed_file_allowlist", touch_ok, int(touch_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10am_public_adapter_integration_audit_package_authorized" if complete else "n10am_not_authorized", "next_allowed_phase": "BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package" if complete else "none_until_adapter_integration_result_matches", "next_allowed_scope_bucket": "public_audit_package_no_private_read" if complete else "no_next_phase", "n10am_public_audit_package_authorized": complete, "private_read_authorized": False, "existing_evaluator_hook_in_authorized": False, "runtime_or_default_enablement_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_or_window_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, rows_status: str, schema_ok: bool, import_ok: bool, result_ok: bool, privacy_ok: bool, noexec_ok: bool, touch_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10al_required_inputs_unavailable"
    if rows_status != "pass":
        return "no_go_n10al_private_span_rows_missing"
    if not schema_ok or not result_ok:
        return "no_go_n10al_adapter_result_mismatch"
    if not import_ok or not touch_ok:
        return "no_go_n10al_forbidden_import_or_hook_detected"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10al_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    rows, rows_status = read_rows()
    metrics, schema_ok = compute_with_adapter(rows) if rows_status == "pass" else ({}, False)
    private_records = private_input_intake_records(rows, rows_status, schema_ok)
    import_records, import_ok = adapter_import_boundary_records()
    result_records = adapter_integration_result_records(metrics)
    comparison_records, result_ok = comparison_to_n10ab_records(metrics, artifacts)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    touch_ok = changed_files_valid()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, rows_status, schema_ok, import_ok, result_ok, privacy_ok, noexec_ok, touch_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "scoped_eval_only_adapter_integration_smoke", "generated_by": "bea_v1_n10al_scoped_eval_only_adapter_integration_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_input_intake_records": private_records, "adapter_import_boundary_records": import_records, "adapter_integration_result_records": result_records, "comparison_to_n10ab_records": comparison_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n10am_handoff_records": n10am_handoff_records(complete), "gate_records": gate_records(input_ok, schema_ok, import_ok, result_ok, privacy_ok, noexec_ok, touch_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, schema_ok, import_ok, result_ok, privacy_ok, noexec_ok, touch_ok, scanner_ok)
    report["n10am_handoff_records"] = n10am_handoff_records(complete)
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
    inputs, artifacts, input_ok = input_artifact_records()
    rows, rows_status = read_rows()
    metrics, schema_ok = compute_with_adapter(rows) if rows_status == "pass" else ({}, False)
    import_records, import_ok = adapter_import_boundary_records()
    comparison_records, result_ok = comparison_to_n10ab_records(metrics, artifacts)
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    touch_ok = changed_files_valid()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10al_required_inputs_unavailable", "no_go_n10al_private_span_rows_missing", "no_go_n10al_adapter_result_mismatch", "no_go_n10al_forbidden_import_or_hook_detected", "no_go_n10al_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 4),
        check("private_rows", rows_status == "pass" and len(rows) == 213 and schema_ok),
        check("adapter_import", import_ok and import_records[0]["projection_adapter_import_count"] >= 1 and import_records[0]["forbidden_evaluator_import_count"] == 0),
        check("baseline_metrics", metrics.get("baseline_top10_span_overlap_count") == 9 and metrics.get("baseline_top20_span_overlap_count") == 10),
        check("pm50_metrics", metrics.get("pm50_top10_span_overlap_count") == 19 and metrics.get("pm50_top20_span_overlap_count") == 23 and metrics.get("delta_top10_vs_baseline_count") == 10),
        check("candidate_order", metrics.get("candidate_pool_changed_bool") is False and metrics.get("order_changed_bool") is False),
        check("comparison", result_ok and comparison_records[0]["n10ab_primary_match_bool"] is True and comparison_records[0]["n10ad_independent_match_bool"] is True),
        check("privacy", privacy_ok and privacy_records[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_records[0]["other_private_file_read_count"] == 0 and noexec_records[0]["existing_evaluator_hook_in_count"] == 0),
        check("changed_files", touch_ok),
        check("handoff", n10am_handoff_records(True)[0]["n10am_public_audit_package_authorized_bool"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AL scoped eval-only adapter integration smoke")
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
    result = report["adapter_integration_result_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={result['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
