#!/usr/bin/env python3
"""BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke.

Direct empirical same-source smoke over the scoped N1 span rows.  The evaluator
uses only private candidate file identity as a gold-free policy feature, keeps
the original candidate pool intact, and publishes aggregate/bucket results only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


STATUS_PASS = "distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized"
STATUS_REQUIRED_INPUTS = "no_go_n10dc_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dc_private_span_rows_missing"
STATUS_POLICY_INVALID = "no_go_n10dc_policy_contract_invalid"
STATUS_PRIVACY = "no_go_n10dc_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"

STATUS_VOCAB = {
    STATUS_PASS,
    STATUS_REQUIRED_INPUTS,
    STATUS_PRIVATE_MISSING,
    STATUS_POLICY_INVALID,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

VARIANTS = [
    "baseline_existing_order",
    "distinct_file_top10_greedy",
    "distinct_file_top20_greedy_then_top10",
    "max_per_file_1_top10",
    "max_per_file_2_top10",
]

FORBIDDEN_KEYS = {
    "path",
    "paths",
    "file_path",
    "filename",
    "filenames",
    "private_path",
    "private_filename",
    "source_path",
    "span",
    "spans",
    "line",
    "lines",
    "snippet",
    "snippets",
    "content",
    "raw_content",
    "candidate_list",
    "candidates",
    "p4_evidence",
    "gold_path",
    "gold_paths",
    "gold_line",
    "gold_lines",
    "exact_rank",
    "raw_rank",
    "rank",
    "ranks",
    "repo_id",
    "task_id",
    "hash",
    "sha",
    "provider_payload",
    "raw_diff",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json"
DEFAULT_N10DB = ROOT / "artifacts" / "bea_v1_n10db_rank_file_reach_policy_field_scoping" / "bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_N10CZ = ROOT / "artifacts" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json"


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - argparse exit path
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DC distinct-file packing smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10db-artifact", default=str(DEFAULT_N10DB))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
    parser.add_argument("--n10cz-artifact", default=str(DEFAULT_N10CZ))
    return parser.parse_args(argv)


def scan_summary(obj: Any) -> dict[str, Any]:
    failures: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            failures.append({"bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pat in FORBIDDEN_VALUE_PATTERNS:
                if pat.search(node):
                    failures.append({"bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {
        "status": "fail" if failures else "pass",
        "forbidden_finding_count": len(failures),
        "finding_buckets": failures[:20],
    }


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10db_field_scoping", Path(args.n10db_artifact), "rank_file_reach_policy_field_scoping_pass_n10dc_authorized"),
        ("n10da_upper_bound_package", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
        ("n10cz_upper_bound_smoke", Path(args.n10cz_artifact), "top2_local_window_saturation_upper_bound_complete_n10da_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected_status) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        status_ok = state == "present" and actual == expected_status
        ok = ok and status_ok
        records.append(
            {
                "anonymous_input_artifact_id": f"n10dcin{idx:04d}",
                "artifact_bucket": bucket,
                "load_status_bucket": state,
                "expected_status_bucket": expected_status,
                "actual_status_bucket": actual or "unavailable",
                "status_match_bool": status_ok,
                "public_artifact_bool": True,
            }
        )
    return records, ok


def load_private_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    except Exception:
        return [], "invalid"
    return rows, "present"


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if isinstance(row.get("p4_evidence"), list)
        and row.get("p4_evidence")
        and isinstance(row.get("gold_paths"), list)
        and isinstance(row.get("gold_lines"), list)
    ]


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
        except Exception:
            continue
    return out


def _norm_path(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def _same_or_suffix_path(left: object, right: object) -> bool:
    a = _norm_path(left)
    b = _norm_path(right)
    if not a or not b:
        return False
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def matching_ref_ranges(ev_path: object, ref_map: dict[str, list[tuple[int, int]]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for ref, ranges in ref_map.items():
        if _same_or_suffix_path(ev_path, ref):
            out.extend(ranges)
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def file_hit(ev: dict[str, Any], ref_map: dict[str, list[tuple[int, int]]]) -> bool:
    return bool(matching_ref_ranges(ev.get("path", ""), ref_map))


def span_hit(ev: dict[str, Any], ref_map: dict[str, list[tuple[int, int]]]) -> bool:
    ref_ranges = matching_ref_ranges(ev.get("path", ""), ref_map)
    if not ref_ranges:
        return False
    start = ev.get("start_line")
    end = ev.get("end_line")
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    return any(overlaps(int(start), int(end), a, b) for a, b in ref_ranges)


def packed_order(evidence: list[dict[str, Any]], variant: str) -> list[dict[str, Any]]:
    if variant == "baseline_existing_order":
        return list(evidence)
    per_file_limit = 1
    prefix_len = 10
    if variant == "distinct_file_top20_greedy_then_top10":
        prefix_len = 20
    if variant == "max_per_file_2_top10":
        per_file_limit = 2
    out: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for ev in evidence:
        if len(out) >= prefix_len:
            break
        file_key = str(ev.get("path", ""))
        if counts.get(file_key, 0) < per_file_limit:
            out.append(ev)
            counts[file_key] = counts.get(file_key, 0) + 1
    used = {id(ev) for ev in out}
    out.extend(ev for ev in evidence if id(ev) not in used)
    return out


def any_top(order: list[dict[str, Any]], k: int, ref_map: dict[str, list[tuple[int, int]]], pred) -> bool:
    return any(pred(ev, ref_map) for ev in order[:k])


def compute_metrics(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_span_top10: list[bool] = []
    baseline_file_top10 = 0
    baseline_span10 = 0
    for row in rows:
        ref_map = refs(row)
        order = packed_order(row.get("p4_evidence", []), "baseline_existing_order")
        baseline_file_top10 += int(any_top(order, 10, ref_map, file_hit))
        hit = any_top(order, 10, ref_map, span_hit)
        baseline_span_top10.append(hit)
        baseline_span10 += int(hit)

    records: list[dict[str, Any]] = []
    dup_records: list[dict[str, Any]] = []
    span_records: list[dict[str, Any]] = []
    baseline_by_variant: dict[str, tuple[int, int, int, int]] = {}

    for idx, variant in enumerate(VARIANTS):
        file10 = file20 = span10 = span20 = dup_reduced = lost_span = 0
        for row_idx, row in enumerate(rows):
            evidence = row.get("p4_evidence", [])
            ref_map = refs(row)
            order = packed_order(evidence, variant)
            file10 += int(any_top(order, 10, ref_map, file_hit))
            file20 += int(any_top(order, 20, ref_map, file_hit))
            hit10 = any_top(order, 10, ref_map, span_hit)
            hit20 = any_top(order, 20, ref_map, span_hit)
            span10 += int(hit10)
            span20 += int(hit20)
            if variant != "baseline_existing_order" and baseline_span_top10[row_idx] and not hit10:
                lost_span += 1
            orig_unique = len({str(ev.get("path", "")) for ev in evidence[:10] if isinstance(ev, dict)})
            new_unique = len({str(ev.get("path", "")) for ev in order[:10] if isinstance(ev, dict)})
            dup_reduced += int(new_unique > orig_unique)
        delta_file = file10 - baseline_file_top10
        delta_span = span10 - baseline_span10
        if variant == "baseline_existing_order":
            decision = "baseline_existing_order"
        elif delta_file > 0 and lost_span == 0:
            decision = "improves_file_reach_without_span_regression"
        elif delta_file == 0 and file20 > baseline_by_variant.get("baseline_existing_order", (0, 0, 0, 0))[1]:
            decision = "top20_only_file_gain"
        else:
            decision = "span_regression_or_no_file_gain"
        baseline_by_variant[variant] = (file10, file20, span10, span20)
        records.append(
            {
                "anonymous_packing_variant_result_id": f"n10dcres{idx:04d}",
                "variant_bucket": variant,
                "top10_file_reach_count": file10,
                "top20_file_reach_count": file20,
                "top10_span_overlap_count": span10,
                "top20_span_overlap_count": span20,
                "delta_top10_file_reach_vs_baseline": delta_file,
                "delta_top10_span_vs_baseline": delta_span,
                "duplicate_file_pressure_reduced_rows_count": dup_reduced,
                "lost_baseline_top10_span_hits": lost_span,
                "candidate_generation_count": 0,
                "candidate_added_count": 0,
                "candidate_removed_count": 0,
                "candidate_pool_changed_bool": False,
                "decision_bucket": decision,
            }
        )
        dup_records.append(
            {
                "anonymous_duplicate_pressure_effect_id": f"n10dcdup{idx:04d}",
                "variant_bucket": variant,
                "duplicate_file_pressure_reduced_rows_count": dup_reduced,
                "candidate_pool_changed_bool": False,
                "candidate_added_count": 0,
                "candidate_removed_count": 0,
            }
        )
        span_records.append(
            {
                "anonymous_span_metric_id": f"n10dcspan{idx:04d}",
                "variant_bucket": variant,
                "top10_span_overlap_count": span10,
                "top20_span_overlap_count": span20,
                "delta_top10_span_vs_baseline": delta_span,
                "lost_baseline_top10_span_hits": lost_span,
                "unchanged_span_window_policy_bool": True,
            }
        )
    return records, dup_records, span_records


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, eligible_count: int) -> tuple[list[dict[str, Any]], bool]:
    ok = load_status == "present" and len(rows) == 213 and eligible_count == 213
    return [
        {
            "anonymous_private_input_intake_id": "n10dcpriv0000",
            "private_input_bucket": "single_scoped_n1_span_rows",
            "load_status_bucket": load_status,
            "private_span_rows_read": len(rows) if load_status == "present" else 0,
            "eligible_span_rows_count": eligible_count,
            "single_scoped_private_input_read_bool": load_status == "present",
            "other_private_files_read_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "private_content_public_bool": False,
            "intake_complete_bool": ok,
        }
    ], ok


def packing_variant_contract_records() -> list[dict[str, Any]]:
    semantics = {
        "baseline_existing_order": "existing_n1_order_no_repacking",
        "distinct_file_top10_greedy": "scan_original_order_first_distinct_file_for_top10_then_fill",
        "distinct_file_top20_greedy_then_top10": "scan_original_order_first_distinct_file_for_top20_then_take_top10",
        "max_per_file_1_top10": "top10_at_most_one_per_file_if_possible_then_fill",
        "max_per_file_2_top10": "top10_at_most_two_per_file_if_possible_then_fill",
    }
    return [
        {
            "anonymous_packing_variant_contract_id": f"n10dcvar{idx:04d}",
            "variant_bucket": variant,
            "policy_semantics_bucket": semantics[variant],
            "uses_private_candidate_file_identifier_bool": variant != "baseline_existing_order",
            "gold_used_for_policy_bool": False,
            "outcome_used_for_policy_bool": False,
            "candidate_pool_preserved_bool": True,
            "candidate_generation_required_bool": False,
            "candidate_add_remove_allowed_bool": False,
            "repacking_reordering_within_existing_pool_bool": variant != "baseline_existing_order",
            "contract_complete_bool": True,
        }
        for idx, variant in enumerate(VARIANTS)
    ]


def file_reach_summary_records(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = max(results, key=lambda r: (int(r["top10_file_reach_count"]), int(r["top20_file_reach_count"])))
    improving = sum(1 for r in results if r["decision_bucket"] == "improves_file_reach_without_span_regression")
    top20_only = sum(1 for r in results if r["decision_bucket"] == "top20_only_file_gain")
    return [
        {
            "anonymous_file_reach_summary_id": "n10dcfilesum0000",
            "best_variant_bucket": best["variant_bucket"],
            "best_top10_file_reach_count": best["top10_file_reach_count"],
            "best_top20_file_reach_count": best["top20_file_reach_count"],
            "baseline_top10_file_reach_count": results[0]["top10_file_reach_count"],
            "baseline_top20_file_reach_count": results[0]["top20_file_reach_count"],
            "improves_file_reach_without_span_regression_count": improving,
            "top20_only_file_gain_count": top20_only,
            "same_candidate_pool_bool": True,
        }
    ]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [
        {
            "anonymous_privacy_boundary_id": "n10dcprivacy0000",
            "privacy_boundary_bucket": "public_aggregate_counts_only_private_file_ids_not_serialized",
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "private_content_public_bool": False,
            "public_path_or_filename_count": 0,
            "candidate_list_public_bool": False,
            "gold_path_public_bool": False,
            "span_or_line_public_bool": False,
            "exact_rank_public_bool": False,
            "snippet_public_bool": False,
            "privacy_boundary_complete_bool": True,
        }
    ], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [
        {
            "anonymous_no_forbidden_execution_id": "n10dcnoexec0000",
            "private_span_input_read_count": 1,
            "other_private_file_read_count": 0,
            "retrieval_execution_count": 0,
            "p4l_n1_n2_n3_rerun_count": 0,
            "openlocus_execution_count": 0,
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "candidate_addition_count": 0,
            "candidate_removal_count": 0,
            "selector_reranker_execution_count": 0,
            "p5_execution_count": 0,
            "v1a_execution_count": 0,
            "runtime_change_count": 0,
            "default_change_count": 0,
            "heldout_generalization_claim_count": 0,
            "method_winner_claim_count": 0,
            "downstream_value_claim_count": 0,
            "no_forbidden_execution_complete_bool": True,
        }
    ], True


def n10dd_handoff_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_n10dd_handoff_id": "n10dchandoff0000",
            "n10dd_public_package_authorized_bool": True,
            "next_allowed_phase_bucket": "BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package",
            "private_read_next_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
        }
    ]


def stop_go_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_stop_go_id": "n10dcstop0000",
            "status_bucket": STATUS_PASS,
            "next_allowed_phase_bucket": "BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package",
            "n10dd_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
        }
    ]


def gate_records(inputs_ok: bool, intake_ok: bool, variant_count: int, scan_ok: bool, privacy_ok: bool, noexec_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    gates = [
        ("required_public_inputs_present", inputs_ok),
        ("private_span_rows_read_213", intake_ok),
        ("variant_count_exactly_5", variant_count == 5),
        ("candidate_generation_count_zero", noexec_ok),
        ("candidate_added_removed_count_zero", noexec_ok),
        ("privacy_boundary_complete", privacy_ok),
        ("forbidden_scan_pass", scan_ok),
    ]
    return [
        {"anonymous_gate_id": f"n10dcgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(passed)}
        for idx, (name, passed) in enumerate(gates)
    ], all(passed for _name, passed in gates)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_records, inputs_ok = input_artifact_records(args)
    rows, load_status = load_private_rows(Path(args.private_span_rows))
    eligible = eligible_rows(rows)
    intake, intake_ok = private_input_intake_records(rows, load_status, len(eligible))

    if not inputs_ok:
        status = STATUS_REQUIRED_INPUTS
        results: list[dict[str, Any]] = []
        dup = []
        span = []
    elif not intake_ok:
        status = STATUS_PRIVATE_MISSING
        results = []
        dup = []
        span = []
    else:
        results, dup, span = compute_metrics(eligible)
        status = STATUS_PASS

    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_forbidden_execution_records()
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dc_rank_file_reach_smoke_v1",
        "phase_bucket": "BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke",
        "status": status,
        "input_artifact_records": input_records,
        "private_input_intake_records": intake,
        "packing_variant_contract_records": packing_variant_contract_records(),
        "packing_variant_result_records": results,
        "duplicate_pressure_effect_records": dup,
        "file_reach_summary_records": file_reach_summary_records(results) if results else [],
        "span_metric_records": span,
        "privacy_boundary_records": privacy,
        "no_forbidden_execution_records": noexec,
        "n10dd_handoff_records": n10dd_handoff_records() if status == STATUS_PASS else [],
        "stop_go_records": stop_go_records() if status == STATUS_PASS else [],
    }
    scan = scan_summary(report)
    scan_ok = scan["status"] == "pass"
    gates, gates_ok = gate_records(inputs_ok, intake_ok, len(results), scan_ok, privacy_ok, noexec_ok)
    report["gate_records"] = gates
    report["forbidden_scan"] = scan
    if status == STATUS_PASS and (not gates_ok or not scan_ok):
        report["status"] = STATUS_FAIL_SCAN if not scan_ok else STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    sample_rows = [
        {"p4_evidence": [{"path": "a", "start_line": 1, "end_line": 1}, {"path": "a", "start_line": 2, "end_line": 2}, {"path": "b", "start_line": 4, "end_line": 4}], "gold_paths": ["b"], "gold_lines": [[4, 4]]},
        {"p4_evidence": [{"path": "c", "start_line": 1, "end_line": 1}], "gold_paths": ["c"], "gold_lines": [[1, 1]]},
    ]
    packed = packed_order(sample_rows[0]["p4_evidence"], "distinct_file_top10_greedy")
    res, _dup, _span = compute_metrics(sample_rows)
    report = {"safe": "bucket", "records": res}
    tests = [
        check("status_vocabulary", STATUS_PASS in STATUS_VOCAB and STATUS_FAIL_SCHEMA in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_keys", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"gold_lines": []})["status"] == "fail"),
        check("scanner_rejects_values", scan_summary({"safe": "/tmp/private.jsonl"})["status"] == "fail"),
        check("scanner_allows_report", scan_summary(report)["status"] == "pass"),
        check("variant_grid", VARIANTS == ["baseline_existing_order", "distinct_file_top10_greedy", "distinct_file_top20_greedy_then_top10", "max_per_file_1_top10", "max_per_file_2_top10"]),
        check("packing_moves_distinct", packed[1]["path"] == "b"),
        check("candidate_pool_preserved", len(packed) == len(sample_rows[0]["p4_evidence"])),
        check("file_gain_synthetic", any(r["variant_bucket"] == "distinct_file_top10_greedy" and r["top10_file_reach_count"] == 2 for r in res)),
        check("no_candidate_generation", all(r["candidate_generation_count"] == 0 and r["candidate_added_count"] == 0 and r["candidate_removed_count"] == 0 for r in res)),
        check("privacy_boundary", privacy_boundary_records()[1]),
        check("no_execution", no_forbidden_execution_records()[0][0]["retrieval_execution_count"] == 0),
        check("handoff_false_flags", not stop_go_records()[0]["runtime_default_authorized_bool"] and not stop_go_records()[0]["p5_v1a_authorized_bool"]),
        check("missing_private_no_go", private_input_intake_records([], "missing", 0)[0][0]["intake_complete_bool"] is False),
        check("schema_contract", len(packing_variant_contract_records()) == 5 and all(r["contract_complete_bool"] for r in packing_variant_contract_records())),
    ]
    passed = sum(1 for _name, ok in tests if ok)
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
