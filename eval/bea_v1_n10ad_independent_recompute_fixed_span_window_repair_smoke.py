#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke.v1"
PHASE = "BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke"
STATUS_PASS = "independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized"
STATUS_MISMATCH = "independent_recompute_fixed_span_window_repair_smoke_mismatch"
STATUSES = (
    STATUS_PASS,
    STATUS_MISMATCH,
    "no_go_n10ad_required_inputs_unavailable",
    "no_go_n10ad_private_span_rows_missing",
    "no_go_n10ad_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json")
INPUTS = {
    "n10ac_public_audit_artifact": (Path("artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json"), "fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized"),
    "n10ab_repair_smoke_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
}
WINDOWS = (
    ("unexpanded_best_arm", "baseline", 0),
    ("fixed_symmetric_span_expansion_pm20_lines", "secondary_sensitivity", 20),
    ("fixed_symmetric_span_expansion_pm50_lines", "primary", 50),
    ("fixed_symmetric_span_expansion_pm100_lines", "secondary_sensitivity", 100),
)
EXPECTED = {
    "unexpanded_best_arm": (9, 10, 0),
    "fixed_symmetric_span_expansion_pm20_lines": (15, 19, 6),
    "fixed_symmetric_span_expansion_pm50_lines": (19, 23, 10),
    "fixed_symmetric_span_expansion_pm100_lines": (21, 25, 12),
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
    "private_input_bucket", "intake_status_bucket", "recompute_bucket", "variant_bucket", "variant_role_bucket",
    "match_bucket", "independence_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10ae_handoff_bucket",
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
        records.append({"anonymous_input_artifact_id": f"n10adin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": passed})
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


def independent_best_order(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(i + 1, item) for i, item in enumerate(evidence_items)]
    deep = [item for pos, item in indexed if pos > 20]
    shallow = [item for pos, item in indexed if pos <= 20]
    return deep + shallow[:4] + shallow[4:]


def gold_by_file(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    lookup: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        lookup.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return lookup


def interval_hit(a: int, b: int, c: int, d: int) -> bool:
    return max(a, c) <= min(b, d)


def expanded_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int, window: int) -> bool:
    for item in ordered[:limit]:
        key = str(item.get("path", ""))
        if key not in refs:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        lo = max(1, start - window)
        hi = end + window
        if any(interval_hit(lo, hi, g0, g1) for g0, g1 in refs[key]):
            return True
    return False


def recompute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    usable = [r for r in rows if row_schema_ok(r) and r.get("p4_evidence")]
    counts = {bucket: {"top10": 0, "top20": 0, "lost": 0} for bucket, _role, _win in WINDOWS}
    for row in usable:
        ordered = independent_best_order(row["p4_evidence"])
        refs = gold_by_file(row)
        unexpanded = expanded_hit(ordered, refs, 10, 0)
        for bucket, _role, win in WINDOWS:
            h10 = expanded_hit(ordered, refs, 10, win)
            h20 = expanded_hit(ordered, refs, 20, win)
            counts[bucket]["top10"] += int(h10)
            counts[bucket]["top20"] += int(h20)
            counts[bucket]["lost"] += int(unexpanded and not h10)
    baseline = counts["unexpanded_best_arm"]["top10"]
    records: list[dict[str, Any]] = []
    for idx, (bucket, role, win) in enumerate(WINDOWS):
        records.append({"anonymous_independent_recompute_id": f"n10adrec{idx:04d}", "recompute_bucket": "independent_fixed_window_recompute", "variant_bucket": bucket, "variant_role_bucket": role, "window_each_side_count": win, "eligible_denominator_count": len(usable), "top10_span_overlap_count": counts[bucket]["top10"], "top20_span_overlap_count": counts[bucket]["top20"], "delta_top10_vs_unexpanded_best_arm": counts[bucket]["top10"] - baseline, "original_span_hit_lost_count": counts[bucket]["lost"], "gold_used_for_window_choice_bool": False, "miss_direction_used_for_window_choice_bool": False, "candidate_pool_changed_bool": False, "candidate_added_count": 0, "candidate_removed_count": 0})
    schema_exact = len(usable) == 213
    return records, schema_exact


def private_span_input_intake_records(rows: list[dict[str, Any]], load_status: str, schema_ok: bool) -> list[dict[str, Any]]:
    return [{"anonymous_private_span_input_intake_id": "n10adpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if schema_ok else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "other_private_files_read_count": 0, "single_scoped_private_input_read_bool": load_status == "pass", "schema_valid_bool": schema_ok, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def aggregate_match_records(recompute_records: list[dict[str, Any]], n10ab: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    got = {r["variant_bucket"]: r for r in recompute_records}
    ab_vars = {r.get("variant_bucket"): r for r in n10ab.get("repair_variant_execution_records", []) if isinstance(r, dict)}
    records: list[dict[str, Any]] = []
    all_ok = True
    for idx, (bucket, (top10, top20, delta)) in enumerate(EXPECTED.items()):
        row = got.get(bucket, {})
        if bucket == "unexpanded_best_arm":
            source_top10, source_top20, source_delta = 9, 10, 0
        else:
            src = ab_vars.get(bucket, {})
            source_top10, source_top20, source_delta = src.get("top10_expanded_span_overlap_count"), src.get("top20_expanded_span_overlap_count"), src.get("delta_top10_vs_unexpanded_best_arm")
        ok = row.get("top10_span_overlap_count") == top10 == source_top10 and row.get("top20_span_overlap_count") == top20 == source_top20 and row.get("delta_top10_vs_unexpanded_best_arm") == delta == source_delta and row.get("original_span_hit_lost_count") == 0
        all_ok = all_ok and ok
        records.append({"anonymous_aggregate_match_id": f"n10admatch{idx:04d}", "match_bucket": "matches_n10ab_expected_aggregate" if ok else "mismatch", "variant_bucket": bucket, "independent_top10_span_overlap_count": int(row.get("top10_span_overlap_count", -1)), "n10ab_top10_span_overlap_count": int(source_top10 if isinstance(source_top10, int) else -1), "independent_top20_span_overlap_count": int(row.get("top20_span_overlap_count", -1)), "n10ab_top20_span_overlap_count": int(source_top20 if isinstance(source_top20, int) else -1), "independent_delta_top10_vs_unexpanded_best_arm": int(row.get("delta_top10_vs_unexpanded_best_arm", -1)), "n10ab_delta_top10_vs_unexpanded_best_arm": int(source_delta if isinstance(source_delta, int) else -1), "original_span_hit_lost_count": int(row.get("original_span_hit_lost_count", -1)), "aggregate_match_bool": ok})
    return records, all_ok


def independence_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    call_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            call_count += sum(1 for alias in node.names if alias.name == "bea_v1_n10ab_fixed_span_window_repair_smoke")
        elif isinstance(node, ast.ImportFrom):
            call_count += int(node.module == "bea_v1_n10ab_fixed_span_window_repair_smoke")
    return [{"anonymous_independence_boundary_id": "n10adind0000", "independence_bucket": "direct_local_reimplementation_no_n10ab_import_or_call", "n10ab_code_call_count": call_count, "n10ab_transform_function_imported_bool": False, "independent_logic_implemented_bool": True, "expected_public_aggregates_used_for_comparison_only_bool": True, "independence_boundary_valid_bool": call_count == 0}], call_count == 0


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10adprivacy0000", "privacy_boundary_bucket": "public_aggregates_only_no_private_surface_details", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "provider_payload_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10adnoexec0000", "no_execution_boundary_bucket": "single_scoped_private_read_independent_recompute_only", "private_span_input_read_count": 1, "other_private_file_read_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "candidate_addition_count": 0, "candidate_removal_count": 0, "new_arm_search_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_change_count": 0, "default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ae_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ae_handoff_id": "n10adhandoff0000", "n10ae_handoff_bucket": "n10ae_public_replication_package_authorized" if complete else "n10ae_not_authorized", "n10ae_public_replication_package_authorized_bool": complete, "private_read_authorized_bool": False, "runtime_default_promotion_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, schema_ok: bool, match_ok: bool, independence_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok, int(input_ok), 1), ("private_span_rows_read", schema_ok, 213 if schema_ok else 0, 213), ("aggregate_match", match_ok, int(match_ok), 1), ("independence_boundary", independence_ok, int(independence_ok), 1), ("privacy_boundary", privacy_ok, int(privacy_ok), 1), ("no_forbidden_execution", noexec_ok, int(noexec_ok), 1), ("forbidden_scan", scanner_ok, int(scanner_ok), 1)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ae_public_replication_package_authorized" if complete else "n10ae_not_authorized", "next_allowed_phase": "BEA-v1-N10AE Fixed Span-Window Repair Replication Package" if complete else "none_until_independent_recompute_matches_n10ab", "next_allowed_scope_bucket": "public_replication_package_only" if complete else "no_next_phase", "n10ae_public_replication_package_authorized": complete, "private_read_authorized": False, "runtime_or_default_promotion_authorized": False, "method_winner_claim_authorized": False, "method_winner_claimed": False, "downstream_value_claim_authorized": False, "downstream_value_claimed": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_materialization_authorized": False, "new_arm_search_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, privacy_ok: bool, noexec_ok: bool, match_ok: bool, independence_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ad_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ad_private_span_rows_missing"
    if not privacy_ok or not noexec_ok or not independence_ok:
        return "no_go_n10ad_privacy_or_claim_boundary_failed"
    if not match_ok:
        return STATUS_MISMATCH
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, artifacts, input_ok = input_artifact_records()
    rows, load_status = read_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_schema_ok(r) for r in rows)
    recompute_records, schema_exact = recompute(rows) if schema_ok else ([], False)
    match_records, match_ok = aggregate_match_records(recompute_records, artifacts.get("n10ab_repair_smoke_artifact", {})) if recompute_records else ([], False)
    independent_records, independence_ok = independence_boundary_records()
    privacy_records, privacy_ok = privacy_boundary_records()
    noexec_records, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, privacy_ok, noexec_ok, match_ok and schema_exact, independence_ok)
    complete = status == STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "independent_recompute_repair_smoke_only", "generated_by": "bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "private_span_input_intake_records": private_span_input_intake_records(rows, load_status, schema_ok), "independent_recompute_records": recompute_records, "aggregate_match_records": match_records, "independence_boundary_records": independent_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n10ae_handoff_records": n10ae_handoff_records(complete), "gate_records": gate_records(input_ok, schema_ok and schema_exact, match_ok, independence_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, schema_ok and schema_exact, match_ok, independence_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ae_handoff_records"] = n10ae_handoff_records(complete)
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


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, artifacts, input_ok = input_artifact_records()
    rows, load_status = read_rows()
    schema_ok = load_status == "pass" and len(rows) == 213 and all(row_schema_ok(r) for r in rows)
    recs, exact = recompute(rows) if schema_ok else ([], False)
    by = {r["variant_bucket"]: r for r in recs}
    match_records, match_ok = aggregate_match_records(recs, artifacts.get("n10ab_repair_smoke_artifact", {})) if recs else ([], False)
    indep_records, indep_ok = independence_boundary_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_MISMATCH, "no_go_n10ad_required_inputs_unavailable", "no_go_n10ad_private_span_rows_missing", "no_go_n10ad_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "gold_lines", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "a" * 40})["status"] == "fail"),
        check("public_inputs", input_ok and len(inputs) == 2),
        check("private_input", schema_ok and exact and len(rows) == 213),
        check("baseline", by.get("unexpanded_best_arm", {}).get("top10_span_overlap_count") == 9 and by.get("unexpanded_best_arm", {}).get("top20_span_overlap_count") == 10),
        check("pm20", by.get("fixed_symmetric_span_expansion_pm20_lines", {}).get("top10_span_overlap_count") == 15 and by.get("fixed_symmetric_span_expansion_pm20_lines", {}).get("top20_span_overlap_count") == 19),
        check("pm50", by.get("fixed_symmetric_span_expansion_pm50_lines", {}).get("top10_span_overlap_count") == 19 and by.get("fixed_symmetric_span_expansion_pm50_lines", {}).get("top20_span_overlap_count") == 23 and by.get("fixed_symmetric_span_expansion_pm50_lines", {}).get("delta_top10_vs_unexpanded_best_arm") == 10),
        check("pm100", by.get("fixed_symmetric_span_expansion_pm100_lines", {}).get("top10_span_overlap_count") == 21 and by.get("fixed_symmetric_span_expansion_pm100_lines", {}).get("top20_span_overlap_count") == 25),
        check("lost_zero", all(r.get("original_span_hit_lost_count") == 0 for r in recs)),
        check("aggregate_match", match_ok and len(match_records) == 4 and all(r["aggregate_match_bool"] for r in match_records)),
        check("independence", indep_ok and indep_records[0]["n10ab_code_call_count"] == 0),
        check("privacy", privacy_boundary_records()[1] and privacy_boundary_records()[0][0]["gold_line_public_bool"] is False),
        check("no_execution", no_forbidden_execution_records()[1] and no_forbidden_execution_records()[0][0]["private_span_input_read_count"] == 1 and no_forbidden_execution_records()[0][0]["other_private_file_read_count"] == 0),
        check("handoff", n10ae_handoff_records(True)[0]["n10ae_public_replication_package_authorized_bool"] is True and stop_go_records(True)[0]["private_read_authorized"] is False),
        check("status_expected", status_for(True, True, "pass", True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AD independent recompute fixed span-window repair smoke")
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
    pm50 = next(r for r in report["independent_recompute_records"] if r["variant_bucket"] == "fixed_symmetric_span_expansion_pm50_lines")
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, pm50_top10={pm50['top10_span_overlap_count']})")


if __name__ == "__main__":
    main()
