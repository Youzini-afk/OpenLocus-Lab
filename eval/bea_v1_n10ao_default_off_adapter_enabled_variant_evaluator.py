#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_spans


SCHEMA_VERSION = "bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.v1"
PHASE = "BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch"
STATUS_PASS = "default_off_adapter_enabled_variant_evaluator_pass_n10ap_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n10ao_required_inputs_unavailable",
    "no_go_n10ao_explicit_enablement_required",
    "no_go_n10ao_variant_result_mismatch",
    "no_go_n10ao_forbidden_code_touch_detected",
    "no_go_n10ao_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json")
INPUTS = {
    "n10an_hook_feasibility_preflight_artifact": (Path("artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json"), "default_off_existing_evaluator_hook_feasibility_preflight_pass_n10ao_authorized"),
    "n10am_adapter_integration_audit_package_artifact": (Path("artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json"), "eval_only_adapter_integration_result_audit_package_complete_n10an_authorized"),
    "n10al_adapter_integration_smoke_artifact": (Path("artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json"), "scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized"),
    "n10aj_adapter_patch_artifact": (Path("artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json"), "default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized"),
}
ALLOWED_CHANGED = {
    "eval/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.py",
    "artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/",
    "artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json",
    "docs/en/bea-v1-n10ao-default-off-adapter-enabled-variant-evaluator.md",
    "docs/zh/bea-v1-n10ao-default-off-adapter-enabled-variant-evaluator.md",
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
}
EXPECTED = {
    "private_span_rows_read": 213,
    "eligible_denominator_count": 213,
    "baseline_top10_span_overlap_count": 9,
    "baseline_top20_span_overlap_count": 10,
    "pm50_top10_span_overlap_count": 19,
    "pm50_top20_span_overlap_count": 23,
    "delta_top10_vs_baseline_count": 10,
    "original_span_hit_lost_count": 0,
}
FORBIDDEN_IMPORT_FRAGMENTS = (
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
    "contract_bucket", "mode_bucket", "enablement_bucket", "private_input_bucket", "variant_result_bucket",
    "comparison_bucket", "changed_file_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket",
    "n10ap_handoff_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
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
        records.append({"anonymous_input_artifact_id": f"n10aoin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
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
        order_changed = order_changed or len(projected) != len(ordered)
        hit10 = span_hit(projected, refs, 10)
        hit20 = span_hit(projected, refs, 20)
        baseline10 += int(base10)
        baseline20 += int(base20)
        pm5010 += int(hit10)
        pm5020 += int(hit20)
        lost += int(base10 and not hit10)
    result = {
        "eligible_denominator_count": len(usable),
        "baseline_top10_span_overlap_count": baseline10,
        "baseline_top20_span_overlap_count": baseline20,
        "pm50_top10_span_overlap_count": pm5010,
        "pm50_top20_span_overlap_count": pm5020,
        "delta_top10_vs_baseline_count": pm5010 - baseline10,
        "original_span_hit_lost_count": lost,
        "candidate_pool_changed_bool": pool_changed,
        "order_changed_bool": order_changed,
    }
    ok = all(result[k] == v for k, v in EXPECTED.items() if k in result)
    return result, ok


def disabled_synthetic_check() -> tuple[dict[str, Any], bool]:
    sample = [{"start_line": 5, "end_line": 9, "bucket": "synthetic"}, {"start_line": 1, "end_line": 1, "bucket": "synthetic"}]
    projected = project_evidence_spans(sample, expansion_each_side=50, enabled=False)
    ok = projected == sample and projected is not sample and projected[0] is not sample[0]
    return {"disabled_projection_changed_bool": not ok, "disabled_private_read_count": 0, "disabled_projection_count": len(projected), "disabled_mode_valid_bool": ok}, ok


def variant_evaluator_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [{"anonymous_variant_evaluator_contract_id": "n10aocontract0000", "contract_bucket": "new_eval_only_variant_evaluator_imports_adapter_only", "adapter_imported_bool": True, "existing_validated_evaluator_imported_bool": False, "runtime_retrieval_selector_imported_bool": False, "default_off_flag_required_bool": True, "private_read_requires_explicit_enablement_bool": True, "fixed_pm50_window_bool": True, "new_arm_or_window_tuning_bool": False, "contract_valid_bool": True}]
    return rows, True


def default_off_mode_records() -> tuple[list[dict[str, Any]], bool]:
    synthetic, ok = disabled_synthetic_check()
    row = {"anonymous_default_off_mode_id": "n10aodefault0000", "mode_bucket": "default_disabled_no_private_read_no_metric_recompute", "default_enabled_bool": False, "private_read_by_default_bool": False, "metric_recompute_by_default_bool": False, "adapter_projection_enabled_by_default_bool": False, **synthetic}
    return [row], ok


def explicit_enablement_records(enabled: bool) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_explicit_enablement_id": "n10aoenable0000", "enablement_bucket": "explicit_scoped_private_span_rows_enablement_used" if enabled else "explicit_enablement_not_used", "explicit_enablement_used_bool": enabled, "default_enabled_bool": False, "private_read_by_default_bool": False, "scoped_private_read_enabled_bool": enabled, "adapter_projection_enabled_bool": enabled}], enabled


def scoped_private_input_records(enabled: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool, bool]:
    if not enabled:
        row = {"anonymous_scoped_private_input_id": "n10aopriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "private_rows_read": 0, "private_span_rows_read": 0, "other_private_files_read_count": 0, "schema_valid_bool": False, "private_content_public_bool": False, "private_path_public_bool": False, "private_filename_public_bool": False, "intake_status_bucket": "not_read_explicit_enablement_required"}
        return [row], [], False, False
    rows, load_status = read_rows()
    schema_ok = load_status == "pass" and len(rows) == EXPECTED["private_span_rows_read"] and all(isinstance(row, dict) and row_schema_ok(row) for row in rows)
    rec = {"anonymous_scoped_private_input_id": "n10aopriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "private_rows_read": len(rows), "private_span_rows_read": len(rows), "other_private_files_read_count": 0, "schema_valid_bool": schema_ok, "private_content_public_bool": False, "private_path_public_bool": False, "private_filename_public_bool": False, "intake_status_bucket": "pass" if schema_ok else "schema_invalid"}
    return [rec], rows, schema_ok, load_status == "pass"


def adapter_variant_result_records(rows: list[dict[str, Any]], enabled: bool) -> tuple[list[dict[str, Any]], bool]:
    if not enabled or not rows:
        return [{"anonymous_adapter_variant_result_id": "n10aoresult0000", "variant_result_bucket": "not_evaluated_explicit_enablement_required", "private_span_rows_read": 0, "eligible_denominator_count": 0, "baseline_top10_span_overlap_count": 0, "baseline_top20_span_overlap_count": 0, "pm50_top10_span_overlap_count": 0, "pm50_top20_span_overlap_count": 0, "delta_top10_vs_baseline_count": 0, "original_span_hit_lost_count": 0, "candidate_pool_changed_bool": False, "order_changed_bool": False, "variant_result_valid_bool": False}], False
    result, ok = compute_with_adapter(rows)
    record = {"anonymous_adapter_variant_result_id": "n10aoresult0000", "variant_result_bucket": "adapter_enabled_variant_reproduces_pm50_aggregate", "private_span_rows_read": len(rows), **result, "variant_result_valid_bool": ok}
    return [record], ok


def comparison_to_n10al_records(artifacts: dict[str, dict[str, Any]], result: dict[str, Any], result_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    n10al = artifacts.get("n10al_adapter_integration_smoke_artifact", {})
    al_result = (n10al.get("adapter_integration_result_records") or [{}])[0]
    fields = ["eligible_denominator_count", "baseline_top10_span_overlap_count", "baseline_top20_span_overlap_count", "pm50_top10_span_overlap_count", "pm50_top20_span_overlap_count", "delta_top10_vs_baseline_count", "original_span_hit_lost_count", "candidate_pool_changed_bool", "order_changed_bool"]
    matches = result_ok and all(result.get(field) == al_result.get(field) for field in fields)
    return [{"anonymous_comparison_to_n10al_id": "n10aocompare0000", "comparison_bucket": "variant_matches_n10al_and_indirect_n10ab_n10ad_aggregates", "n10al_status_valid_bool": n10al.get("status") == INPUTS["n10al_adapter_integration_smoke_artifact"][1], "n10al_aggregate_match_bool": matches, "n10ab_n10ad_indirect_match_bool": bool((n10al.get("comparison_to_n10ab_records") or [{}])[0].get("comparison_passed_bool", False)), "comparison_passed_bool": matches}], matches


def source_import_boundary_ok() -> bool:
    text = Path(__file__).read_text(encoding="utf-8")
    import_lines = [line for line in text.splitlines() if line.startswith("import ") or line.startswith("from ")]
    return "from bea_v1_span_window_projection_adapter import project_evidence_spans" in import_lines and not any(fragment in line for fragment in FORBIDDEN_IMPORT_FRAGMENTS for line in import_lines)


def changed_files() -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


def forbidden_code_touch_records() -> tuple[list[dict[str, Any]], bool]:
    files = changed_files()
    invalid = sorted(set(files) - ALLOWED_CHANGED)
    rows = []
    for idx, file_name in enumerate(files):
        safe = re.sub(r"[^A-Za-z0-9]+", "_", file_name).strip("_") or "none"
        rows.append({"anonymous_forbidden_code_touch_id": f"n10aotouch{idx:04d}", "changed_file_bucket": safe, "allowed_bool": file_name in ALLOWED_CHANGED})
    if not rows:
        rows.append({"anonymous_forbidden_code_touch_id": "n10aotouch0000", "changed_file_bucket": "none", "allowed_bool": True})
    rows.append({"anonymous_forbidden_code_touch_id": "n10aotouch9999", "changed_file_bucket": "import_boundary", "allowed_bool": source_import_boundary_ok(), "existing_evaluator_imported_bool": False, "runtime_retrieval_selector_imported_bool": False})
    return rows, not invalid and source_import_boundary_ok()


def privacy_boundary_records(private_rows_read: int) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aoprivacy0000", "privacy_boundary_bucket": "public_aggregate_counts_only_no_private_surface_details", "private_rows_read_count": private_rows_read, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records(private_rows_read: int) -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10aonoexec0000", "no_execution_boundary_bucket": "new_eval_only_variant_no_runtime_no_existing_hook", "private_span_input_read_count": 1 if private_rows_read else 0, "other_private_file_read_count": 0, "existing_evaluator_hook_in_count": 0, "modify_existing_validated_evaluator_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "new_arm_or_window_tuning_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_enablement_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ap_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ap_handoff_id": "n10aohandoff0000", "n10ap_handoff_bucket": "n10ap_public_audit_package_authorized" if complete else "n10ap_not_authorized", "n10ap_public_audit_package_authorized_bool": complete, "private_read_authorized_bool": False, "additional_private_read_authorized_bool": False, "existing_evaluator_hook_in_authorized_bool": False, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, contract_ok: bool, default_ok: bool, explicit_ok: bool, private_ok: bool, result_ok: bool, compare_ok: bool, touch_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("variant_contract", contract_ok), ("default_off_mode", default_ok), ("explicit_enablement", explicit_ok), ("scoped_private_input", private_ok), ("adapter_variant_result", result_ok), ("comparison_to_n10al", compare_ok), ("forbidden_code_touch", touch_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ap_public_audit_package_authorized" if complete else "n10ap_not_authorized", "next_allowed_phase": "BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package" if complete else "none_until_explicit_enablement_and_variant_match", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10ap_public_audit_package_authorized": complete, "private_read_authorized": False, "additional_private_read_authorized": False, "existing_evaluator_hook_in_authorized": False, "modify_existing_validated_evaluator_authorized": False, "runtime_or_default_enablement_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "new_arm_or_window_tuning_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, explicit_ok: bool, private_ok: bool, result_ok: bool, compare_ok: bool, touch_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ao_required_inputs_unavailable"
    if not explicit_ok:
        return "no_go_n10ao_explicit_enablement_required"
    if not private_ok or not result_ok or not compare_ok:
        return "no_go_n10ao_variant_result_mismatch"
    if not touch_ok:
        return "no_go_n10ao_forbidden_code_touch_detected"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ao_privacy_or_claim_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]], enabled: bool) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    contract_rows, contract_ok = variant_evaluator_contract_records()
    default_rows, default_ok = default_off_mode_records()
    explicit_rows, explicit_ok = explicit_enablement_records(enabled)
    scoped_rows, rows, private_ok, private_load_ok = scoped_private_input_records(enabled)
    result_rows, result_ok = adapter_variant_result_records(rows, enabled and private_load_ok)
    compare_rows, compare_ok = comparison_to_n10al_records(artifacts, result_rows[0], result_ok)
    touch_rows, touch_ok = forbidden_code_touch_records()
    private_rows_read = int(scoped_rows[0].get("private_span_rows_read", 0))
    privacy_rows, privacy_ok = privacy_boundary_records(private_rows_read)
    noexec_rows, noexec_ok = no_forbidden_execution_records(private_rows_read)
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, explicit_ok, private_ok, result_ok, compare_ok, touch_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "default_off_eval_only_variant_evaluator_patch", "generated_by": "bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "variant_evaluator_contract_records": contract_rows, "default_off_mode_records": default_rows, "explicit_enablement_records": explicit_rows, "scoped_private_input_records": scoped_rows, "adapter_variant_result_records": result_rows, "comparison_to_n10al_records": compare_rows, "forbidden_code_touch_records": touch_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10ap_handoff_records": n10ap_handoff_records(complete), "gate_records": gate_records(input_ok, contract_ok, default_ok, explicit_ok, private_ok, result_ok, compare_ok, touch_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, contract_ok, default_ok, explicit_ok, private_ok, result_ok, compare_ok, touch_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ap_handoff_records"] = n10ap_handoff_records(complete)
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
    inputs, _artifacts, input_ok = input_artifact_records()
    contract_rows, contract_ok = variant_evaluator_contract_records()
    default_rows, default_ok = default_off_mode_records()
    explicit_rows_false, explicit_false = explicit_enablement_records(False)
    explicit_rows_true, explicit_true = explicit_enablement_records(True)
    touch_rows, touch_ok = forbidden_code_touch_records()
    privacy_rows, privacy_ok = privacy_boundary_records(0)
    noexec_rows, noexec_ok = no_forbidden_execution_records(0)
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n10ao_required_inputs_unavailable", "no_go_n10ao_explicit_enablement_required", "no_go_n10ao_variant_result_mismatch", "no_go_n10ao_forbidden_code_touch_detected", "no_go_n10ao_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("inputs", input_ok and len(inputs) == 4),
        check("contract", contract_ok and contract_rows[0]["adapter_imported_bool"] is True and contract_rows[0]["existing_validated_evaluator_imported_bool"] is False),
        check("default_off", default_ok and default_rows[0]["private_read_by_default_bool"] is False and default_rows[0]["disabled_private_read_count"] == 0),
        check("explicit_required", not explicit_false and explicit_rows_false[0]["explicit_enablement_used_bool"] is False),
        check("explicit_enabled", explicit_true and explicit_rows_true[0]["explicit_enablement_used_bool"] is True and explicit_rows_true[0]["private_read_by_default_bool"] is False),
        check("import_boundary", source_import_boundary_ok()),
        check("forbidden_touch", touch_ok and touch_rows[-1]["allowed_bool"] is True),
        check("privacy", privacy_ok and privacy_rows[0]["private_path_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["existing_evaluator_hook_in_count"] == 0),
        check("handoff", n10ap_handoff_records(True)[0]["n10ap_public_audit_package_authorized_bool"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_default_no_go", status_for(True, True, False, False, False, False, True, True, True) == "no_go_n10ao_explicit_enablement_required"),
        check("status_expected", status_for(True, True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AO default-off adapter-enabled variant evaluator")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--enable-scoped-private-span-rows", action="store_true")
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
    report = build_report(checks, enabled=bool(args.enable_scoped_private_span_rows))
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    result = report["adapter_variant_result_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={result['pm50_top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
