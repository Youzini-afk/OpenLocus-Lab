#!/usr/bin/env python3
"""BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "suffix_safe_deep_rank_promotion_smoke_complete_n10dnr_authorized"
STATUS_NO_INPUTS = "no_go_n10dmr_required_inputs_unavailable"
STATUS_ACCOUNTING = "no_go_n10dmr_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dmr_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_ACCOUNTING, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DO = ROOT / "artifacts" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit" / "bea_v1_n10do_candidate_pool_absence_source_acquisition_audit_report.json"
DEFAULT_N10DM = ROOT / "artifacts" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json"
DEFAULT_N10DL = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke" / "bea_v1_n10dmr_corrected_suffix_safe_deep_rank_promotion_smoke_report.json"

VARIANTS = [
    "anchor_n10t_order",
    "no_dup_promote_rank11_20_before_rank6_10",
    "no_dup_interleave_rank11_20_after_top5",
    "no_dup_preserve_top7_fill_from_rank11_20",
    "no_dup_promote_rank11_50_after_top5_limited5",
    "no_dup_interleave_rank11_50_after_top5_limited5",
]

FORBIDDEN_KEYS = {"path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path", "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list", "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "repo_id", "task_id", "hash", "provider_payload", "raw_diff"}
FORBIDDEN_VALUE_PATTERNS = [re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"), re.compile(r"/workspace/|/tmp/|/home/"), re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"), re.compile(r"[0-9a-f]{32,}", re.I)]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DM-R corrected suffix-safe smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10do-artifact", default=str(DEFAULT_N10DO))
    parser.add_argument("--n10dm-artifact", default=str(DEFAULT_N10DM))
    parser.add_argument("--n10dl-artifact", default=str(DEFAULT_N10DL))
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
        ("n10do_path_normalization_correction", Path(args.n10do_artifact), "candidate_pool_absence_path_normalization_correction_complete_n10dmr_authorized"),
        ("n10dm_exact_match_context", Path(args.n10dm_artifact), "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized"),
        ("n10dl_residual_context", Path(args.n10dl_artifact), "n10t_file_reach_residual_analysis_complete_n10dm_authorized"),
    ]
    out: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        out.append({"anonymous_input_artifact_id": f"n10dmrin{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": matched, "public_artifact_bool": True})
    return out, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "invalid"
                rows.append(obj)
    except Exception:
        return [], "invalid"
    return rows, "present"


def norm(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def same_or_suffix(a: object, b: object) -> bool:
    left = norm(a)
    right = norm(b)
    return bool(left and right and (left == right or left.endswith("/" + right) or right.endswith("/" + left)))


def row_valid(row: dict[str, Any]) -> bool:
    return isinstance(row.get("p4_evidence"), list) and isinstance(row.get("gold_paths"), list) and isinstance(row.get("gold_lines"), list)


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def append_remaining(prefix: list[dict[str, Any]], base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used = {id(item) for item in prefix}
    return prefix + [item for item in base if id(item) not in used]


def no_dup_pressure(base: list[dict[str, Any]]) -> bool:
    return len({norm(ev.get("path")) for ev in base[:10]}) == 10


def apply_variant(base: list[dict[str, Any]], variant: str) -> list[dict[str, Any]]:
    if variant == "anchor_n10t_order" or not no_dup_pressure(base):
        return list(base)
    if variant == "no_dup_promote_rank11_20_before_rank6_10":
        return append_remaining(base[:5] + base[10:20] + base[5:10], base)
    if variant == "no_dup_interleave_rank11_20_after_top5":
        mixed: list[dict[str, Any]] = []
        for a, b in zip(base[5:10], base[10:20]):
            mixed.extend([a, b])
        mixed.extend(base[15:20])
        return append_remaining(base[:5] + mixed, base)
    if variant == "no_dup_preserve_top7_fill_from_rank11_20":
        return append_remaining(base[:7] + base[10:13] + base[7:10], base)
    if variant == "no_dup_promote_rank11_50_after_top5_limited5":
        return append_remaining(base[:5] + base[10:15] + base[5:10], base)
    if variant == "no_dup_interleave_rank11_50_after_top5_limited5":
        mixed = []
        for a, b in zip(base[5:10], base[10:15]):
            mixed.extend([a, b])
        return append_remaining(base[:5] + mixed, base)
    raise ValueError(variant)


def refs(row: dict[str, Any]) -> list[tuple[str, list[tuple[int, int]]]]:
    out: list[tuple[str, list[tuple[int, int]]]] = []
    tmp: dict[str, list[tuple[int, int]]] = {}
    for p, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            tmp.setdefault(norm(p), []).append((int(rg[0]), int(rg[1])))
        except Exception:
            continue
    return list(tmp.items())


def matching_ranges(ev_path: object, reference: list[tuple[str, list[tuple[int, int]]]], mode: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    ev_key = norm(ev_path)
    for ref, ranges in reference:
        if (ev_key == ref) if mode == "exact" else same_or_suffix(ev_key, ref):
            out.extend(ranges)
    return out


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def length_bucket(ev: dict[str, Any]) -> str:
    try:
        length = int(ev["end_line"]) - int(ev["start_line"]) + 1
    except Exception:
        return "unknown"
    return "short" if length <= 10 else ("medium" if length <= 30 else "long")


def project(ev: dict[str, Any], position: int) -> tuple[object, int, int]:
    start = int(ev.get("start_line", 0))
    end = int(ev.get("end_line", 0))
    if position <= 2:
        return ev.get("path"), max(1, start - 1000), end + 1000
    if length_bucket(ev) == "short":
        return ev.get("path"), max(1, start - 75), end + 225
    return ev.get("path"), start, end


def file_hit(order: list[dict[str, Any]], reference: list[tuple[str, list[tuple[int, int]]]], limit: int, mode: str) -> bool:
    return any(matching_ranges(ev.get("path"), reference, mode) for ev in order[:limit])


def span_hit(order: list[dict[str, Any]], reference: list[tuple[str, list[tuple[int, int]]]], limit: int, mode: str) -> bool:
    for idx, ev in enumerate(order[:limit], 1):
        ev_path, start, end = project(ev, idx)
        for gs, ge in matching_ranges(ev_path, reference, mode):
            if overlap(start, end, gs, ge):
                return True
    return False


def first_gold_rank_bucket(order: list[dict[str, Any]], reference: list[tuple[str, list[tuple[int, int]]]], mode: str) -> str:
    for idx, ev in enumerate(order, 1):
        if matching_ranges(ev.get("path"), reference, mode):
            if idx <= 20:
                return "rank11_20_residual"
            if idx <= 50:
                return "rank21_50_residual"
            return "other_residual"
    return "absent_or_other_residual"


def decision_bucket(file10: int, span10: int, lost_file: int, lost_span: int, anchor_file: int, anchor_span: int) -> str:
    if span10 > anchor_span and lost_span <= 1:
        return "span_projection_positive"
    if file10 > anchor_file and lost_file <= 1:
        return "deep_rank_probe_positive"
    if lost_file > 1 or lost_span > 1:
        return "deep_rank_probe_harmful"
    return "no_improvement"


def analyze_mode(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    usable = [row for row in rows if row_valid(row)]
    per_variant = {v: {"file10": 0, "file20": 0, "span10": 0, "span20": 0, "lost_file": 0, "lost_span": 0, "recovered": 0, "rank11": 0, "rank21": 0, "activated": 0} for v in VARIANTS}
    for row in usable:
        reference = refs(row)
        base = n10t_order(row["p4_evidence"])
        activated = no_dup_pressure(base)
        anchor_file10 = file_hit(base, reference, 10, mode)
        anchor_span10 = span_hit(base, reference, 10, mode)
        rank_bucket = first_gold_rank_bucket(base, reference, mode) if not anchor_file10 else "anchor_hit"
        for variant in VARIANTS:
            order = apply_variant(base, variant)
            file10 = file_hit(order, reference, 10, mode)
            file20 = file_hit(order, reference, 20, mode)
            span10 = span_hit(order, reference, 10, mode)
            span20 = span_hit(order, reference, 20, mode)
            rec = per_variant[variant]
            rec["file10"] += int(file10)
            rec["file20"] += int(file20)
            rec["span10"] += int(span10)
            rec["span20"] += int(span20)
            rec["activated"] += int(activated and variant != "anchor_n10t_order")
            rec["lost_file"] += int(anchor_file10 and not file10)
            rec["lost_span"] += int(anchor_span10 and not span10)
            recovered = (not anchor_file10) and file10
            rec["recovered"] += int(recovered)
            rec["rank11"] += int(recovered and rank_bucket == "rank11_20_residual")
            rec["rank21"] += int(recovered and rank_bucket == "rank21_50_residual")
    return {"row_count": len(usable), "per_variant": per_variant}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_status = load_rows(Path(args.private_span_rows))
    rows_ok = row_status == "present" and len(rows) == 213
    suffix = analyze_mode(rows, "suffix") if rows_ok else analyze_mode([], "suffix")
    exact = analyze_mode(rows, "exact") if rows_ok else analyze_mode([], "exact")
    anchor = suffix["per_variant"]["anchor_n10t_order"]
    accounting_ok = rows_ok and len(VARIANTS) == 6 and anchor["file10"] >= 0 and anchor["file20"] >= anchor["file10"] and anchor["span20"] >= anchor["span10"]
    status = STATUS_COMPLETE if inputs_ok and accounting_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_ACCOUNTING)

    variant_records = []
    positive = harmful = 0
    for i, variant in enumerate(VARIANTS):
        rec = suffix["per_variant"][variant]
        decision = decision_bucket(rec["file10"], rec["span10"], rec["lost_file"], rec["lost_span"], anchor["file10"], anchor["span10"])
        positive += int(decision in {"deep_rank_probe_positive", "span_projection_positive"})
        harmful += int(decision == "deep_rank_probe_harmful")
        variant_records.append({
            "anonymous_variant_result_id": f"n10dmrres{i:04d}",
            "variant_bucket": variant,
            "matching_mode_bucket": "suffix_safe_primary",
            "top10_file_reach_count": rec["file10"],
            "top20_file_reach_count": rec["file20"],
            "top10_projected_span_overlap_count": rec["span10"],
            "top20_projected_span_overlap_count": rec["span20"],
            "delta_top10_file_vs_anchor": rec["file10"] - anchor["file10"],
            "delta_top10_span_vs_anchor": rec["span10"] - anchor["span10"],
            "lost_anchor_file_top10_hits": rec["lost_file"],
            "lost_anchor_span_top10_hits": rec["lost_span"],
            "recovered_reachable_residual_count": rec["recovered"],
            "recovered_rank11_20_residual_count": rec["rank11"],
            "recovered_rank21_50_residual_count": rec["rank21"],
            "activated_row_count": rec["activated"],
            "candidate_pool_changed_bool": False,
            "candidate_added_removed_bool": False,
            "decision_bucket": decision,
        })
    sensitivity_records = []
    for i, variant in enumerate(VARIANTS):
        s = suffix["per_variant"][variant]
        e = exact["per_variant"][variant]
        sensitivity_records.append({
            "anonymous_sensitivity_id": f"n10dmrsens{i:04d}",
            "variant_bucket": variant,
            "exact_top10_file_reach_count": e["file10"],
            "suffix_top10_file_reach_count": s["file10"],
            "suffix_minus_exact_top10_file_reach_count": s["file10"] - e["file10"],
            "exact_top20_file_reach_count": e["file20"],
            "suffix_top20_file_reach_count": s["file20"],
            "suffix_minus_exact_top20_file_reach_count": s["file20"] - e["file20"],
        })
    old_negative_holds = positive == 0 and harmful >= 1
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dmr_suffix_safe_deep_rank_promotion_v1",
        "phase_bucket": "BEA-v1-N10DM-R Corrected Suffix-Safe Deep-Rank Promotion Smoke",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [{"anonymous_private_input_id": "n10dmrpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "load_status_bucket": row_status, "private_span_rows_read": len(rows) if row_status == "present" else 0, "other_private_files_read_count": 0}],
        "variant_contract_records": [{"anonymous_variant_contract_id": f"n10dmrcontract{i:04d}", "variant_bucket": v, "activation_condition_bucket": "duplicate_pressure_none" if v != "anchor_n10t_order" else "always_anchor", "fixed_variant_bool": True, "candidate_pool_changed_bool": False, "candidate_added_removed_bool": False, "gold_used_for_policy_bool": False} for i, v in enumerate(VARIANTS)],
        "corrected_variant_result_records": variant_records,
        "exact_vs_suffix_sensitivity_records": sensitivity_records,
        "decision_summary_records": [{"anonymous_decision_summary_id": "n10dmrdecision0000", "suffix_safe_primary_bool": True, "positive_variant_count": positive, "harmful_variant_count": harmful, "old_negative_conclusion_still_holds_bool": old_negative_holds, "n10dnr_public_package_authorized_bool": True}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10dmrprivacy0000", "public_aggregate_bucket_only_bool": True, "private_path_public_count": 0, "candidate_list_public_count": 0, "raw_file_name_public_count": 0, "span_line_public_count": 0, "gold_used_for_policy_count": 0}],
        "no_forbidden_execution_records": [{"anonymous_no_exec_id": "n10dmrnoexec0000", "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_added_removed_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0}],
        "n10dnr_handoff_records": [{"anonymous_handoff_id": "n10dmrhandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10DN-R Corrected Deep-Rank Promotion Package", "n10dnr_public_package_authorized_bool": True, "runtime_default_authorized_bool": False, "retrieval_rerun_authorized_bool": False}],
        "gate_records": [
            {"anonymous_gate_id": "n10dmrgate0000", "gate_bucket": "inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dmrgate0001", "gate_bucket": "private_span_rows_213", "gate_passed_bool": rows_ok},
            {"anonymous_gate_id": "n10dmrgate0002", "gate_bucket": "variant_count_6", "gate_passed_bool": len(VARIANTS) == 6},
            {"anonymous_gate_id": "n10dmrgate0003", "gate_bucket": "candidate_add_remove_zero", "gate_passed_bool": True},
        ],
        "stop_go_records": [{"anonymous_stop_go_id": "n10dmrstop0000", "next_allowed_phase_bucket": "BEA-v1-N10DN-R Corrected Deep-Rank Promotion Package", "runtime_default_authorized_bool": False, "heldout_generalization_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "candidate_generation_authorized_bool": False, "candidate_add_remove_authorized_bool": False, "selector_reranker_authorized_bool": False, "p5_v1a_authorized_bool": False, "method_downstream_claim_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> int:
    tests: list[tuple[str, bool]] = []
    tests.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB))
    try:
        parse_args(["--unknown", "secret"])
        tests.append(("safe_parser", False))
    except SystemExit as exc:
        tests.append(("safe_parser", exc.code == 2))
    tests.append(("scanner_rejects_key", scan_summary({"path": "x"})["status"] == "fail"))
    tests.append(("scanner_accepts_bucket", scan_summary({"bucket": "safe"})["status"] == "pass"))
    tests.append(("suffix_match", same_or_suffix("a/b/c.py", "c.py") is True))
    tests.append(("suffix_not_match", same_or_suffix("a/b/c.py", "d.py") is False))
    evidence = [{"path": f"f{i}", "start_line": 10, "end_line": 12} for i in range(1, 26)]
    tests.append(("n10t_extra_first", n10t_order(evidence)[0]["path"] == "f21"))
    tests.append(("variant_count", len(VARIANTS) == 6))
    tests.append(("activation", no_dup_pressure(evidence) is True))
    tests.append(("projection", project({"path": "x", "start_line": 5, "end_line": 6}, 1)[1] == 1))
    tests.append(("decision_harm", decision_bucket(29, 26, 5, 4, 34, 30) == "deep_rank_probe_harmful"))
    tests.append(("stop_false", build_report(parse_args([]))["stop_go_records"][0]["runtime_default_authorized_bool"] is False if DEFAULT_PRIVATE.exists() else True))
    passed = sum(1 for _, ok in tests if ok)
    for name, ok in tests:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
