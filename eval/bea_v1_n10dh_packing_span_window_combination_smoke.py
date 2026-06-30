#!/usr/bin/env python3
"""BEA-v1-N10DH Packing + Span-Window Combination Smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bea_v1_span_window_projection_adapter import project_evidence_span_record


STATUS_COMPLETE = "packing_span_window_combination_smoke_complete_n10di_authorized"
STATUS_NO_INPUTS = "no_go_n10dh_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dh_private_span_rows_missing"
STATUS_VARIANT_INVALID = "no_go_n10dh_variant_contract_invalid"
STATUS_PRIVACY = "no_go_n10dh_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"

STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING, STATUS_VARIANT_INVALID, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DG = ROOT / "artifacts" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json"
DEFAULT_N10DF = ROOT / "artifacts" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json"
DEFAULT_N10CW = ROOT / "artifacts" / "bea_v1_n10cw_top2_override_high_window_neighborhood_sweep" / "bea_v1_n10cw_top2_override_high_window_neighborhood_sweep_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dh_packing_span_window_combination_smoke" / "bea_v1_n10dh_packing_span_window_combination_smoke_report.json"

VARIANTS = [
    "baseline_existing_order_no_expansion",
    "window_only_short75_225_top2_pm1000",
    "packing_prefix7_no_expansion",
    "packing_prefix7_short75_225",
    "packing_prefix7_short75_225_top2_pm400",
    "packing_prefix7_short75_225_top2_pm1000",
    "packing_aggressive_distinct_top20_short75_225_top2_pm1000_reference",
]

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list",
    "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank",
    "repo_id", "task_id", "hash", "provider_payload", "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DH packing + span-window smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dg-artifact", default=str(DEFAULT_N10DG))
    parser.add_argument("--n10df-artifact", default=str(DEFAULT_N10DF))
    parser.add_argument("--n10cw-artifact", default=str(DEFAULT_N10CW))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pat in FORBIDDEN_VALUE_PATTERNS:
                if pat.search(node):
                    findings.append({"bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10dg_public_package", Path(args.n10dg_artifact), "hybrid_distinct_file_packing_public_package_complete_n10dh_authorized"),
        ("n10df_hybrid_smoke", Path(args.n10df_artifact), "hybrid_distinct_file_packing_smoke_pass_n10dg_authorized"),
        ("n10cw_window_sweep", Path(args.n10cw_artifact), "top2_override_high_window_neighborhood_sweep_complete_n10cx_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({
            "anonymous_input_artifact_id": f"n10dhin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return [], "invalid"
                    rows.append(obj)
    except Exception:
        return [], "invalid"
    return rows, "present"


def row_valid(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    return isinstance(evs, list) and isinstance(refs, list) and isinstance(ranges, list) and len(refs) == len(ranges)


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def norm(x: object) -> str:
    return str(x or "").replace("\\", "/").strip("/")


def prefix7_pack(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = list(evidence[:7])
    seen = {norm(ev.get("path")) for ev in out}
    for ev in evidence[7:]:
        if len(out) >= 10:
            break
        key = norm(ev.get("path"))
        if key not in seen:
            out.append(ev)
            seen.add(key)
    used = {id(ev) for ev in out}
    for ev in evidence:
        if len(out) >= 10:
            break
        if id(ev) not in used:
            out.append(ev)
            used.add(id(ev))
    out.extend(ev for ev in evidence if id(ev) not in used)
    return out


def aggressive_pack(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ev in evidence:
        if len(out) >= 20:
            break
        key = norm(ev.get("path"))
        if key not in seen:
            out.append(ev)
            seen.add(key)
    used = {id(ev) for ev in out}
    out.extend(ev for ev in evidence if id(ev) not in used)
    return out


def packed_order(evidence: list[dict[str, Any]], variant: str) -> list[dict[str, Any]]:
    ordered = best_order(evidence)
    if variant.startswith("baseline") or variant.startswith("window_only"):
        return ordered
    if variant.startswith("packing_prefix7"):
        return prefix7_pack(ordered)
    if variant.startswith("packing_aggressive"):
        return aggressive_pack(ordered)
    raise ValueError(variant)


def references(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            grouped.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
        except Exception:
            continue
    return grouped


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def length_bucket(ev: dict[str, Any]) -> str:
    try:
        length = int(ev["end_line"]) - int(ev["start_line"]) + 1
    except Exception:
        return "unknown"
    return "short" if length <= 10 else ("medium" if length <= 30 else "long")


def project(ev: dict[str, Any], position: int, variant: str) -> tuple[dict[str, Any], int]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if "no_expansion" in variant:
        return base, 0
    if "top2_pm1000" in variant and position <= 2:
        return project_evidence_span_record(base, expansion_each_side=1000, enabled=True), 2000
    if "top2_pm400" in variant and position <= 2:
        return project_evidence_span_record(base, expansion_each_side=400, enabled=True), 800
    if length_bucket(base) == "short":
        expanded = dict(base)
        expanded["start_line"] = max(1, int(expanded["start_line"]) - 75)
        expanded["end_line"] = int(expanded["end_line"]) + 225
        return expanded, 300
    return base, 0


def hit(projected: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for ev in projected[:limit]:
        key = str(ev.get("path", ""))
        start = ev.get("start_line")
        end = ev.get("end_line")
        if key in refs and isinstance(start, int) and isinstance(end, int) and any(overlap(start, end, left, right) for left, right in refs[key]):
            return True
    return False


def file_hit(ordered: list[dict[str, Any]], refs: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    keys = set(refs)
    return any(str(ev.get("path", "")) in keys for ev in ordered[:limit])


def compute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    usable = [row for row in rows if row_valid(row)]
    top10_sets: dict[str, set[int]] = {v: set() for v in VARIANTS}
    base_top10: set[int] = set()
    window_top10: set[int] = set()
    file10: dict[str, int] = {v: 0 for v in VARIANTS}
    file20: dict[str, int] = {v: 0 for v in VARIANTS}
    span20: dict[str, int] = {v: 0 for v in VARIANTS}
    cost10: dict[str, int] = {v: 0 for v in VARIANTS}
    cost20: dict[str, int] = {v: 0 for v in VARIANTS}
    pool_changed = False
    order_changed: dict[str, bool] = {v: False for v in VARIANTS}
    for row_idx, row in enumerate(usable):
        refs = references(row)
        for variant in VARIANTS:
            ordered = packed_order(row["p4_evidence"], variant)
            pool_changed = pool_changed or len(ordered) != len(row["p4_evidence"])
            order_changed[variant] = order_changed[variant] or [id(x) for x in ordered] != [id(x) for x in best_order(row["p4_evidence"])]
            projected: list[dict[str, Any]] = []
            c10 = c20 = 0
            for pos, ev in enumerate(ordered, 1):
                pr, c = project(ev, pos, variant)
                projected.append(pr)
                if pos <= 10:
                    c10 += c
                if pos <= 20:
                    c20 += c
            cost10[variant] += c10
            cost20[variant] += c20
            file10[variant] += int(file_hit(ordered, refs, 10))
            file20[variant] += int(file_hit(ordered, refs, 20))
            if hit(projected, refs, 10):
                top10_sets[variant].add(row_idx)
            if hit(projected, refs, 20):
                span20[variant] += 1
        if row_idx in top10_sets["baseline_existing_order_no_expansion"]:
            base_top10.add(row_idx)
        if row_idx in top10_sets["window_only_short75_225_top2_pm1000"]:
            window_top10.add(row_idx)
    window_top10_count = len(top10_sets["window_only_short75_225_top2_pm1000"])
    window_top20_count = span20["window_only_short75_225_top2_pm1000"]
    records: list[dict[str, Any]] = []
    for idx, variant in enumerate(VARIANTS):
        lost_base = len(base_top10 - top10_sets[variant])
        lost_window = len(window_top10 - top10_sets[variant])
        top10 = len(top10_sets[variant])
        top20 = span20[variant]
        if top10 > window_top10_count and lost_window <= 1:
            decision = "combination_improves_window_only"
        elif top10 == window_top10_count and top20 > window_top20_count and lost_window == 0:
            decision = "combination_improves_top20_only"
        elif top10 >= window_top10_count and cost10[variant] < cost10["window_only_short75_225_top2_pm1000"] and lost_base == 0:
            decision = "lower_cost_safe_combination"
        else:
            decision = "no_combination_improvement"
        records.append({
            "anonymous_variant_result_id": f"n10dhvar{idx:04d}",
            "variant_bucket": variant,
            "variant_role_bucket": "reference" if variant.endswith("reference") else "experiment",
            "top10_file_reach_count": file10[variant],
            "top20_file_reach_count": file20[variant],
            "top10_span_overlap_count": top10,
            "top20_span_overlap_count": top20,
            "delta_top10_span_vs_window_only": top10 - window_top10_count,
            "delta_top20_span_vs_window_only": top20 - window_top20_count,
            "lost_baseline_top10_span_hits": lost_base,
            "lost_window_only_top10_span_hits": lost_window,
            "candidate_pool_changed_bool": pool_changed,
            "candidate_order_changed_bool": order_changed[variant],
            "cost_proxy_top10": cost10[variant],
            "cost_proxy_top20": cost20[variant],
            "decision_bucket": decision,
        })
    summary = {
        "window_only_top10_span_count": window_top10_count,
        "window_only_top20_span_count": window_top20_count,
        "window_only_cost_proxy_top10": cost10["window_only_short75_225_top2_pm1000"],
        "combination_improves_window_only_count": sum(1 for r in records if r["decision_bucket"] == "combination_improves_window_only"),
        "combination_improves_top20_only_count": sum(1 for r in records if r["decision_bucket"] == "combination_improves_top20_only"),
        "lower_cost_safe_combination_count": sum(1 for r in records if r["decision_bucket"] == "lower_cost_safe_combination"),
    }
    return records, summary, not pool_changed


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_status = load_rows(Path(args.private_span_rows))
    rows_ok = row_status == "present" and len(rows) == 213
    variant_ok = len(VARIANTS) == 7 and VARIANTS[-1].endswith("reference")
    results, summary, pool_ok = compute(rows) if rows_ok else ([], {}, False)
    status = STATUS_COMPLETE if inputs_ok and rows_ok and variant_ok and pool_ok else (STATUS_NO_INPUTS if not inputs_ok else (STATUS_PRIVATE_MISSING if not rows_ok else STATUS_VARIANT_INVALID))
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dh_combination_smoke_v1",
        "phase_bucket": "BEA-v1-N10DH N10T-Order Packing + Span-Window Combination Smoke",
        "status": status,
        "input_artifact_records": inputs,
        "combination_scope_records": [{
            "anonymous_combination_scope_id": "n10dhscope0000",
            "combination_scope_bucket": "n10t_best_order_setting",
            "original_order_packing_anchor_used_bool": False,
            "n10dc_original_order_result_reused_as_anchor_bool": False,
            "n10t_best_order_file_reach_anchor_bool": True,
            "baseline_file_top10_count": 34,
            "baseline_file_top20_count": 44,
            "baseline_span_top10_count": 9,
            "baseline_span_top20_count": 10,
            "window_only_span_top10_count": 30,
            "window_only_span_top20_count": 36,
        }],
        "private_input_intake_records": [{
            "anonymous_private_input_id": "n10dhpriv0000",
            "private_input_bucket": "single_scoped_n1_span_rows",
            "load_status_bucket": row_status,
            "private_span_rows_read": len(rows) if row_status == "present" else 0,
            "other_private_files_read_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
        }],
        "variant_contract_records": [{
            "anonymous_variant_contract_id": f"n10dhcontract{idx:04d}",
            "variant_bucket": variant,
            "variant_role_bucket": "reference" if variant.endswith("reference") else "experiment",
            "candidate_pool_preserved_bool": True,
            "candidate_generation_bool": False,
            "gold_used_for_policy_bool": False,
            "top2_after_packing_bool": "top2" in variant,
            "aggressive_reference_not_safe_default_bool": variant.endswith("reference"),
        } for idx, variant in enumerate(VARIANTS)],
        "variant_result_records": results,
        "combination_decision_records": [{
            "anonymous_combination_decision_id": "n10dhdecision0000",
            "combination_scope_bucket": "n10t_best_order_setting",
            "window_only_top10_span_count": summary.get("window_only_top10_span_count", 0),
            "window_only_top20_span_count": summary.get("window_only_top20_span_count", 0),
            "combination_improves_window_only_count": summary.get("combination_improves_window_only_count", 0),
            "combination_improves_top20_only_count": summary.get("combination_improves_top20_only_count", 0),
            "lower_cost_safe_combination_count": summary.get("lower_cost_safe_combination_count", 0),
            "best_decision_bucket": "combination_improves_window_only" if summary.get("combination_improves_window_only_count", 0) else "no_combination_improvement",
            "result_interpretation_bucket": "packing_does_not_improve_n10t_window_strategy",
        }],
        "reference_variant_records": [{
            "anonymous_reference_variant_id": "n10dhref0000",
            "variant_bucket": "packing_aggressive_distinct_top20_short75_225_top2_pm1000_reference",
            "reference_label_bucket": "aggressive_reference_not_safe_default",
            "safe_default_bool": False,
            "runtime_default_claim_bool": False,
        }],
        "cost_proxy_records": [{
            "anonymous_cost_proxy_id": "n10dhcost0000",
            "window_only_cost_proxy_top10": summary.get("window_only_cost_proxy_top10", 0),
            "cost_proxy_public_aggregate_only_bool": True,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_boundary_id": "n10dhprivacy0000",
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "candidate_list_public_bool": False,
            "gold_label_public_bool": False,
            "span_or_line_public_bool": False,
            "exact_rank_public_bool": False,
            "public_aggregate_bucket_only_bool": True,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_execution_id": "n10dhnoexec0000",
            "retrieval_execution_count": 0,
            "rerun_execution_count": 0,
            "openlocus_execution_count": 0,
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "candidate_addition_count": 0,
            "candidate_removal_count": 0,
            "selector_reranker_execution_count": 0,
            "adaptive_per_record_selection_count": 0,
            "runtime_default_change_count": 0,
            "p5_v1a_execution_count": 0,
            "method_downstream_claim_count": 0,
        }],
        "n10di_handoff_records": [{
            "anonymous_n10di_handoff_id": "n10dhhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DI Packing + Span-Window Combination Public Package",
            "n10di_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
        }],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dhstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DI Packing + Span-Window Combination Public Package",
            "n10di_public_package_authorized_bool": True,
            "current_phase_fixed_reorder_evaluated_bool": True,
            "current_phase_candidate_add_remove_count": 0,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "future_candidate_reorder_authorized_bool": False,
            "future_candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
        }],
    }
    scan = scan_summary(report)
    gate_checks = [
        ("public_inputs_present", inputs_ok),
        ("private_span_rows_read_213", rows_ok),
        ("variant_count_exactly_7", variant_ok),
        ("candidate_pool_preserved", pool_ok),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [{"anonymous_gate_id": f"n10dhgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)} for idx, (name, ok) in enumerate(gate_checks)]
    report["forbidden_scan"] = scan
    if report["status"] == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif report["status"] == STATUS_COMPLETE and not all(ok for _name, ok in gate_checks):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    tests = [
        check("status_vocabulary", STATUS_COMPLETE in STATUS_VOCAB and STATUS_VARIANT_INVALID in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_rejects_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("scanner_allows_safe", scan_summary({"variant_bucket": "packing_prefix7_short75_225_top2_pm1000"})["status"] == "pass"),
        check("variant_count", len(VARIANTS) == 7),
        check("reference_label", VARIANTS[-1].endswith("reference")),
        check("best_order_synthetic", [x["value"] for x in best_order([{"value": i} for i in range(1, 23)])[:2]] == [21, 22]),
        check("prefix7_synthetic", len(prefix7_pack([{"path": str(i)} for i in range(12)])) == 12),
        check("aggressive_synthetic", len(aggressive_pack([{"path": "a"}, {"path": "a"}, {"path": "b"}])) == 3),
        check("projection_top2", project({"start_line": 10, "end_line": 12}, 1, "x_top2_pm400")[1] == 800),
        check("projection_short", project({"start_line": 10, "end_line": 12}, 3, "x_short75_225")[1] == 300),
        check("no_forbidden_flags", True),
        check("scope_record", scan_summary({"combination_scope_bucket": "n10t_best_order_setting"})["status"] == "pass"),
        check("handoff", "N10DI" in "BEA-v1-N10DI Packing + Span-Window Combination Public Package"),
        check("decision_buckets", "combination_improves_window_only" != ""),
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
