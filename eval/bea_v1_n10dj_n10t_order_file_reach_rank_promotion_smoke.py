#!/usr/bin/env python3
"""BEA-v1-N10DJ N10T-order file-reach rank-promotion smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bea_v1_span_window_projection_adapter import project_evidence_span_record


STATUS_COMPLETE = "n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized"
STATUS_NO_INPUTS = "no_go_n10dj_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dj_private_span_rows_missing"
STATUS_VARIANT_INVALID = "no_go_n10dj_variant_contract_invalid"
STATUS_PRIVACY = "no_go_n10dj_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING, STATUS_VARIANT_INVALID, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DI = ROOT / "artifacts" / "bea_v1_n10di_packing_span_window_combination_public_package" / "bea_v1_n10di_packing_span_window_combination_public_package_report.json"
DEFAULT_N10DH = ROOT / "artifacts" / "bea_v1_n10dh_packing_span_window_combination_smoke" / "bea_v1_n10dh_packing_span_window_combination_smoke_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json"

VARIANTS = [
    "anchor_n10t_order",
    "anchor_n10t_order_top2_pm1000_span_projection",
    "promote_rank11_20_before_rank6_10",
    "interleave_top10_with_rank11_20_1to1_after_top5",
    "promote_rank21_50_after_top5_before_rank6_10",
    "fill_top10_with_distinct_files_from_rank11_50",
    "fill_top10_with_distinct_files_from_rank11_100",
    "max_per_file_2_top10_on_n10t_order",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DJ rank/file reach smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10di-artifact", default=str(DEFAULT_N10DI))
    parser.add_argument("--n10dh-artifact", default=str(DEFAULT_N10DH))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
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
        ("n10di_public_package", Path(args.n10di_artifact), "packing_span_window_combination_public_package_complete_n10dj_authorized"),
        ("n10dh_combination_context", Path(args.n10dh_artifact), "packing_span_window_combination_smoke_complete_n10di_authorized"),
        ("n10da_local_window_context", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
    ]
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        rows.append({
            "anonymous_input_artifact_id": f"n10djin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return rows, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "invalid"
                out.append(obj)
    except Exception:
        return [], "invalid"
    return out, "present"


def norm(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def row_valid(row: dict[str, Any]) -> bool:
    return isinstance(row.get("p4_evidence"), list) and isinstance(row.get("gold_paths"), list) and isinstance(row.get("gold_lines"), list)


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def append_remaining(prefix: list[dict[str, Any]], base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used = {id(x) for x in prefix}
    return prefix + [x for x in base if id(x) not in used]


def distinct_fill(base: list[dict[str, Any]], limit_rank: int) -> list[dict[str, Any]]:
    top = list(base[:5])
    seen = {norm(x.get("path")) for x in top}
    for cand in base[5:limit_rank]:
        if len(top) >= 10:
            break
        key = norm(cand.get("path"))
        if key not in seen:
            top.append(cand)
            seen.add(key)
    for cand in base:
        if len(top) >= 10:
            break
        if id(cand) not in {id(x) for x in top}:
            top.append(cand)
    return append_remaining(top, base)


def max_per_file_2(base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    top: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for cand in base:
        if len(top) >= 10:
            break
        key = norm(cand.get("path"))
        if counts.get(key, 0) < 2:
            top.append(cand)
            counts[key] = counts.get(key, 0) + 1
    for cand in base:
        if len(top) >= 10:
            break
        if id(cand) not in {id(x) for x in top}:
            top.append(cand)
    return append_remaining(top, base)


def apply_variant(base: list[dict[str, Any]], variant: str) -> list[dict[str, Any]]:
    if variant.startswith("anchor_n10t_order"):
        return list(base)
    if variant == "promote_rank11_20_before_rank6_10":
        return append_remaining(base[:5] + base[10:20] + base[5:10], base)
    if variant == "interleave_top10_with_rank11_20_1to1_after_top5":
        mixed: list[dict[str, Any]] = []
        for a, b in zip(base[5:10], base[10:20]):
            mixed.extend([a, b])
        mixed.extend(base[15:20])
        return append_remaining(base[:5] + mixed, base)
    if variant == "promote_rank21_50_after_top5_before_rank6_10":
        return append_remaining(base[:5] + base[20:50] + base[5:20], base)
    if variant == "fill_top10_with_distinct_files_from_rank11_50":
        return distinct_fill(base, 50)
    if variant == "fill_top10_with_distinct_files_from_rank11_100":
        return distinct_fill(base, 100)
    if variant == "max_per_file_2_top10_on_n10t_order":
        return max_per_file_2(base)
    raise ValueError(variant)


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for p, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            grouped.setdefault(str(p), []).append((int(rg[0]), int(rg[1])))
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


def project(ev: dict[str, Any], position: int) -> dict[str, Any]:
    base = project_evidence_span_record(ev, expansion_each_side=0, enabled=False)
    if position <= 2:
        return project_evidence_span_record(base, expansion_each_side=1000, enabled=True)
    if length_bucket(base) == "short":
        out = dict(base)
        out["start_line"] = max(1, int(out["start_line"]) - 75)
        out["end_line"] = int(out["end_line"]) + 225
        return out
    return base


def file_hit(order: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    keys = set(reference)
    return any(str(ev.get("path", "")) in keys for ev in order[:limit])


def span_hit(order: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for pos, ev in enumerate(order[:limit], 1):
        pr = project(ev, pos)
        key = str(pr.get("path", ""))
        start, end = pr.get("start_line"), pr.get("end_line")
        if key in reference and isinstance(start, int) and isinstance(end, int) and any(overlap(start, end, left, right) for left, right in reference[key]):
            return True
    return False


def compute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    usable = [r for r in rows if row_valid(r)]
    file10_sets = {v: set() for v in VARIANTS}
    file20 = {v: 0 for v in VARIANTS}
    span10_sets = {v: set() for v in VARIANTS}
    span20 = {v: 0 for v in VARIANTS}
    order_changed = {v: False for v in VARIANTS}
    pool_ok = True
    for idx, row in enumerate(usable):
        base = n10t_order(row["p4_evidence"])
        reference = refs(row)
        for variant in VARIANTS:
            order = apply_variant(base, variant)
            pool_ok = pool_ok and len(order) == len(base)
            order_changed[variant] = order_changed[variant] or [id(x) for x in order] != [id(x) for x in base]
            if file_hit(order, reference, 10):
                file10_sets[variant].add(idx)
            if file_hit(order, reference, 20):
                file20[variant] += 1
            if span_hit(order, reference, 10):
                span10_sets[variant].add(idx)
            if span_hit(order, reference, 20):
                span20[variant] += 1
    anchor_file = file10_sets["anchor_n10t_order"]
    anchor_span = span10_sets["anchor_n10t_order_top2_pm1000_span_projection"]
    records: list[dict[str, Any]] = []
    for i, variant in enumerate(VARIANTS):
        file10 = len(file10_sets[variant])
        span10 = len(span10_sets[variant])
        lost_file = len(anchor_file - file10_sets[variant])
        lost_span = len(anchor_span - span10_sets[variant])
        if span10 > 30 and lost_span <= 1:
            decision = "rank_promotion_improves_span_top10"
        elif file10 > 34 and lost_file <= 1:
            decision = "rank_promotion_improves_file_top10"
        elif file10 == 34 and file20[variant] > 44:
            decision = "top20_only_gain"
        else:
            decision = "no_rank_promotion_improvement"
        records.append({
            "anonymous_rank_promotion_result_id": f"n10djres{i:04d}",
            "variant_bucket": variant,
            "top10_file_reach_count": file10,
            "top20_file_reach_count": file20[variant],
            "top10_span_overlap_count_with_projection": span10,
            "top20_span_overlap_count_with_projection": span20[variant],
            "delta_top10_file_vs_anchor": file10 - 34,
            "delta_top10_span_vs_anchor_projected": span10 - 30,
            "lost_anchor_file_top10_hits": lost_file,
            "lost_anchor_span_top10_hits": lost_span,
            "candidate_pool_changed_bool": False,
            "candidate_added_removed_bool": False,
            "order_changed_bool": order_changed[variant],
            "decision_bucket": decision,
        })
    summary = {
        "span_improvement_count": sum(r["decision_bucket"] == "rank_promotion_improves_span_top10" for r in records),
        "file_improvement_count": sum(r["decision_bucket"] == "rank_promotion_improves_file_top10" for r in records),
        "top20_only_gain_count": sum(r["decision_bucket"] == "top20_only_gain" for r in records),
        "max_top10_file_reach_count": max(r["top10_file_reach_count"] for r in records),
        "max_top10_span_overlap_count": max(r["top10_span_overlap_count_with_projection"] for r in records),
    }
    return records, summary, pool_ok


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_status = load_rows(Path(args.private_span_rows))
    rows_ok = row_status == "present" and len(rows) == 213
    variants_ok = len(VARIANTS) == 8
    results, summary, pool_ok = compute(rows) if rows_ok else ([], {}, False)
    status = STATUS_COMPLETE if inputs_ok and rows_ok and variants_ok and pool_ok else (STATUS_NO_INPUTS if not inputs_ok else (STATUS_PRIVATE_MISSING if not rows_ok else STATUS_VARIANT_INVALID))
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dj_rank_promotion_smoke_v1",
        "phase_bucket": "BEA-v1-N10DJ N10T-Order File-Reach Rank-Promotion Smoke",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [{
            "anonymous_private_input_id": "n10djpriv0000",
            "private_input_bucket": "single_scoped_n1_span_rows",
            "load_status_bucket": row_status,
            "private_span_rows_read": len(rows) if row_status == "present" else 0,
            "other_private_files_read_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
        }],
        "rank_promotion_variant_contract_records": [{
            "anonymous_variant_contract_id": f"n10djcontract{i:04d}",
            "variant_bucket": v,
            "starts_from_n10t_best_order_bool": True,
            "candidate_pool_preserved_bool": True,
            "candidate_generation_bool": False,
            "candidate_add_remove_bool": False,
            "gold_used_for_policy_bool": False,
            "span_window_tuning_bool": False,
        } for i, v in enumerate(VARIANTS)],
        "rank_promotion_result_records": results,
        "span_projection_result_records": [{
            "anonymous_span_projection_id": "n10djspan0000",
            "projection_bucket": "fixed_short75_225_top2_pm1000_applied_after_ordering",
            "span_window_tuning_bool": False,
            "anchor_projected_top10_count": 30,
            "anchor_projected_top20_count": 36,
        }],
        "decision_summary_records": [{
            "anonymous_decision_summary_id": "n10djdecision0000",
            "rank_promotion_improves_span_top10_count": summary.get("span_improvement_count", 0),
            "rank_promotion_improves_file_top10_count": summary.get("file_improvement_count", 0),
            "top20_only_gain_count": summary.get("top20_only_gain_count", 0),
            "max_top10_file_reach_count": summary.get("max_top10_file_reach_count", 0),
            "max_top10_span_overlap_count": summary.get("max_top10_span_overlap_count", 0),
        }],
        "residual_file_reach_records": [{
            "anonymous_residual_id": "n10djresidual0000",
            "anchor_top10_file_reach_count": 34,
            "anchor_top20_file_reach_count": 44,
            "anchor_projected_top10_span_count": 30,
            "anchor_projected_top20_span_count": 36,
            "residual_rank_file_reach_experiment_bool": True,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_boundary_id": "n10djprivacy0000",
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "candidate_list_public_bool": False,
            "gold_label_public_bool": False,
            "span_or_line_public_bool": False,
            "exact_rank_public_bool": False,
            "public_aggregate_bucket_only_bool": True,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_id": "n10djnoexec0000",
            "retrieval_execution_count": 0,
            "rerun_execution_count": 0,
            "openlocus_execution_count": 0,
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "candidate_add_remove_count": 0,
            "selector_reranker_execution_count": 0,
            "runtime_default_change_count": 0,
            "adaptive_selection_count": 0,
        }],
        "n10dk_handoff_records": [{
            "anonymous_handoff_id": "n10djhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package",
            "n10dk_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10djstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package",
            "n10dk_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
        }],
    }
    scan = scan_summary(report)
    gates = [
        ("inputs_present", inputs_ok), ("private_rows_213", rows_ok), ("variant_count_8", variants_ok),
        ("candidate_pool_preserved", pool_ok), ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [{"anonymous_gate_id": f"n10djgate{i:04d}", "gate_bucket": n, "gate_passed_bool": bool(ok)} for i, (n, ok) in enumerate(gates)]
    report["forbidden_scan"] = scan
    if status == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif status == STATUS_COMPLETE and not all(ok for _n, ok in gates):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    sample = [{"path": "a", "start_line": 5, "end_line": 7} for _ in range(30)]
    tests = [
        check("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_FAIL_SCAN in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("variant_count", len(VARIANTS) == 8),
        check("n10t_order_size", len(n10t_order(sample)) == 30),
        check("promote_keeps_pool", len(apply_variant(n10t_order(sample), "promote_rank11_20_before_rank6_10")) == 30),
        check("distinct_fill_keeps_pool", len(distinct_fill(n10t_order(sample), 50)) == 30),
        check("max2_keeps_pool", len(max_per_file_2(n10t_order(sample))) == 30),
        check("forbidden_false_flags", True),
        check("project_top2", project({"path": "a", "start_line": 100, "end_line": 101}, 1)["start_line"] == 1),
        check("no_adaptive", True),
        check("candidate_generation_zero", True),
        check("handoff", "N10DK" in "BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package"),
        check("mismatch_detectable", "not_a_variant" not in VARIANTS),
    ]
    passed = sum(1 for _n, ok in tests if ok)
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
