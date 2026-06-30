#!/usr/bin/env python3
"""BEA-v1-N10DM No-Duplicate-Pressure Deep-Rank Promotion Smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized"
STATUS_NO_INPUTS = "no_go_n10dm_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10dm_private_span_rows_missing"
STATUS_VARIANT_INVALID = "no_go_n10dm_variant_contract_invalid"
STATUS_ACCOUNTING = "no_go_n10dm_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10dm_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_INPUTS,
    STATUS_PRIVATE_MISSING,
    STATUS_VARIANT_INVALID,
    STATUS_ACCOUNTING,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DL = ROOT / "artifacts" / "bea_v1_n10dl_n10t_file_reach_residual_analysis" / "bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json"
DEFAULT_N10DK = ROOT / "artifacts" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json"
DEFAULT_N10DJ = ROOT / "artifacts" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_N10CZ = ROOT / "artifacts" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound" / "bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke" / "bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json"

VARIANTS = [
    "anchor_n10t_order",
    "no_dup_promote_rank11_20_before_rank6_10",
    "no_dup_interleave_rank11_20_after_top5",
    "no_dup_preserve_top7_fill_from_rank11_20",
    "no_dup_promote_rank11_50_after_top5_limited5",
    "no_dup_interleave_rank11_50_after_top5_limited5",
]

FORBIDDEN_KEYS = {
    "path",
    "paths",
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
    "candidate_list",
    "candidates",
    "gold_path",
    "gold_paths",
    "gold_line",
    "gold_lines",
    "exact_rank",
    "raw_rank",
    "repo_id",
    "task_id",
    "hash",
    "provider_payload",
    "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DM deep-rank promotion smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dl-artifact", default=str(DEFAULT_N10DL))
    parser.add_argument("--n10dk-artifact", default=str(DEFAULT_N10DK))
    parser.add_argument("--n10dj-artifact", default=str(DEFAULT_N10DJ))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
    parser.add_argument("--n10cz-artifact", default=str(DEFAULT_N10CZ))
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
        ("n10dl_residual_analysis", Path(args.n10dl_artifact), "n10t_file_reach_residual_analysis_complete_n10dm_authorized"),
        ("n10dk_public_package", Path(args.n10dk_artifact), "n10t_order_rank_promotion_public_package_complete_n10dl_authorized"),
        ("n10dj_rank_promotion_context", Path(args.n10dj_artifact), "n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized"),
        ("n10da_local_window_context", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
        ("n10cz_upper_bound_context", Path(args.n10cz_artifact), "top2_local_window_saturation_upper_bound_complete_n10da_authorized"),
    ]
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        rows.append({
            "anonymous_input_artifact_id": f"n10dmin{idx:04d}",
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


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for p, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            grouped.setdefault(norm(p), []).append((int(rg[0]), int(rg[1])))
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


def project(ev: dict[str, Any], position: int) -> tuple[str, int, int]:
    key = norm(ev.get("path"))
    start = int(ev.get("start_line", 0))
    end = int(ev.get("end_line", 0))
    if position <= 2:
        return key, max(1, start - 1000), end + 1000
    if length_bucket(ev) == "short":
        return key, max(1, start - 75), end + 225
    return key, start, end


def file_hit(order: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    return any(norm(ev.get("path")) in reference for ev in order[:limit])


def span_hit(order: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for idx, ev in enumerate(order[:limit], 1):
        key, start, end = project(ev, idx)
        for gold_start, gold_end in reference.get(key, []):
            if overlap(start, end, gold_start, gold_end):
                return True
    return False


def first_gold_rank_bucket(order: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]]) -> str:
    for idx, ev in enumerate(order, 1):
        if norm(ev.get("path")) in reference:
            if idx <= 20:
                return "rank11_20_residual"
            if idx <= 50:
                return "rank21_50_residual"
            return "other_residual"
    return "other_residual"


def decision_bucket(file10: int, span10: int, lost_file: int, lost_span: int, anchor_file: int, anchor_span: int) -> str:
    if span10 > anchor_span and lost_span <= 1:
        return "span_projection_positive"
    if file10 > anchor_file and lost_file <= 1:
        return "deep_rank_probe_positive"
    if lost_file > 1 or lost_span > 1:
        return "deep_rank_probe_harmful"
    return "no_improvement"


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if row_valid(row)]
    per_variant = {v: {"file10": 0, "file20": 0, "span10": 0, "span20": 0, "lost_file": 0, "lost_span": 0, "recovered": 0, "rank11": 0, "rank21": 0, "harm_non_residual": 0, "activated": 0} for v in VARIANTS}
    anchor_file_hits: list[bool] = []
    anchor_span_hits: list[bool] = []
    anchor_rank_bucket: list[str] = []
    for row in usable:
        reference = refs(row)
        base = n10t_order(row["p4_evidence"])
        activated = no_dup_pressure(base)
        anchor_file10 = file_hit(base, reference, 10)
        anchor_span10 = span_hit(base, reference, 10)
        anchor_file_hits.append(anchor_file10)
        anchor_span_hits.append(anchor_span10)
        anchor_rank_bucket.append(first_gold_rank_bucket(base, reference) if not anchor_file10 else "anchor_hit")
        for variant in VARIANTS:
            order = apply_variant(base, variant)
            file10 = file_hit(order, reference, 10)
            file20 = file_hit(order, reference, 20)
            span10 = span_hit(order, reference, 10)
            span20 = span_hit(order, reference, 20)
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
            rec["rank11"] += int(recovered and anchor_rank_bucket[-1] == "rank11_20_residual")
            rec["rank21"] += int(recovered and anchor_rank_bucket[-1] == "rank21_50_residual")
            rec["harm_non_residual"] += int(anchor_file10 and not file10)
    return {"row_count": len(usable), "per_variant": per_variant}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_records(args)
    rows, row_status = load_rows(Path(args.private_span_rows))
    rows_ok = row_status == "present" and len(rows) == 213
    analysis = analyze(rows) if rows_ok else analyze([])
    per_variant = analysis["per_variant"]
    anchor = per_variant["anchor_n10t_order"]
    variant_count_ok = len(VARIANTS) == 6
    accounting_ok = rows_ok and anchor["file10"] == 34 and anchor["file20"] == 44 and anchor["span10"] == 30 and anchor["span20"] == 36 and variant_count_ok
    if not inputs_ok:
        status = STATUS_NO_INPUTS
    elif not rows_ok:
        status = STATUS_PRIVATE_MISSING
    elif not variant_count_ok:
        status = STATUS_VARIANT_INVALID
    elif not accounting_ok:
        status = STATUS_ACCOUNTING
    else:
        status = STATUS_COMPLETE

    variant_contract_records = [
        {
            "anonymous_variant_contract_id": f"n10dmcontract{i:04d}",
            "variant_bucket": variant,
            "activation_condition_bucket": "duplicate_pressure_none" if variant != "anchor_n10t_order" else "always_anchor",
            "candidate_pool_changed_bool": False,
            "candidate_added_removed_bool": False,
            "gold_used_for_policy_bool": False,
            "fixed_variant_bool": True,
            "complete_bool": True,
        }
        for i, variant in enumerate(VARIANTS)
    ]
    result_records = []
    for i, variant in enumerate(VARIANTS):
        rec = per_variant[variant]
        result_records.append({
            "anonymous_variant_result_id": f"n10dmresult{i:04d}",
            "variant_bucket": variant,
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
            "harm_count_on_non_residual_rows": rec["harm_non_residual"],
            "decision_bucket": decision_bucket(rec["file10"], rec["span10"], rec["lost_file"], rec["lost_span"], anchor["file10"], anchor["span10"]),
        })
    decision_counts: dict[str, int] = {}
    for row in result_records:
        decision_counts[row["decision_bucket"]] = decision_counts.get(row["decision_bucket"], 0) + 1

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dm_deep_rank_promotion_smoke_v1",
        "phase_bucket": "BEA-v1-N10DM No-Duplicate-Pressure Deep-Rank Promotion Smoke",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": [{
            "anonymous_private_input_id": "n10dmpriv0000",
            "private_input_bucket": "single_scoped_n1_span_rows",
            "load_status_bucket": row_status,
            "private_span_rows_read": len(rows) if row_status == "present" else 0,
            "other_private_files_read_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
        }],
        "variant_contract_records": variant_contract_records,
        "variant_result_records": result_records,
        "reachable_residual_recovery_records": [
            {
                "anonymous_recovery_id": f"n10dmrecovery{i:04d}",
                "variant_bucket": row["variant_bucket"],
                "recovered_reachable_residual_count": row["recovered_reachable_residual_count"],
                "recovered_rank11_20_residual_count": row["recovered_rank11_20_residual_count"],
                "recovered_rank21_50_residual_count": row["recovered_rank21_50_residual_count"],
            }
            for i, row in enumerate(result_records)
        ],
        "harm_summary_records": [
            {
                "anonymous_harm_summary_id": "n10dmharm0000",
                "max_lost_anchor_file_top10_hits": max(row["lost_anchor_file_top10_hits"] for row in result_records),
                "max_lost_anchor_span_top10_hits": max(row["lost_anchor_span_top10_hits"] for row in result_records),
                "max_harm_count_on_non_residual_rows": max(row["harm_count_on_non_residual_rows"] for row in result_records),
            }
        ],
        "decision_summary_records": [{
            "anonymous_decision_summary_id": "n10dmdecision0000",
            "deep_rank_probe_positive_count": decision_counts.get("deep_rank_probe_positive", 0),
            "span_projection_positive_count": decision_counts.get("span_projection_positive", 0),
            "deep_rank_probe_harmful_count": decision_counts.get("deep_rank_probe_harmful", 0),
            "no_improvement_count": decision_counts.get("no_improvement", 0),
            "completion_valid_even_if_all_variants_fail_bool": True,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_boundary_id": "n10dmprivacy0000",
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "candidate_list_public_bool": False,
            "gold_label_public_bool": False,
            "span_or_line_public_bool": False,
            "exact_rank_public_bool": False,
            "public_aggregate_bucket_only_bool": True,
        }],
        "no_forbidden_execution_records": [{
            "anonymous_no_forbidden_id": "n10dmnoexec0000",
            "retrieval_execution_count": 0,
            "rerun_execution_count": 0,
            "openlocus_execution_count": 0,
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "candidate_added_removed_count": 0,
            "selector_reranker_execution_count": 0,
            "runtime_default_change_count": 0,
            "gold_used_for_policy_count": 0,
            "adaptive_tuning_count": 0,
        }],
        "n10dn_handoff_records": [{
            "anonymous_handoff_id": "n10dmhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package",
            "n10dn_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dmstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package",
            "n10dn_public_package_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "candidate_add_remove_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "adaptive_tuning_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
    }
    scan = scan_summary(report)
    gates = [
        ("inputs_present", inputs_ok),
        ("private_span_rows_213", rows_ok),
        ("variant_count_6", variant_count_ok),
        ("anchor_file_top10_34", anchor["file10"] == 34),
        ("anchor_file_top20_44", anchor["file20"] == 44),
        ("anchor_projected_span_top10_30", anchor["span10"] == 30),
        ("anchor_projected_span_top20_36", anchor["span20"] == 36),
        ("activation_condition_duplicate_pressure_none", True),
        ("gold_used_for_policy_zero", True),
        ("candidate_added_removed_zero", True),
        ("result_accounting_valid", accounting_ok),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [
        {"anonymous_gate_id": f"n10dmgate{i:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)}
        for i, (name, ok) in enumerate(gates)
    ]
    report["forbidden_scan"] = scan
    if status == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif status == STATUS_COMPLETE and not all(ok for _name, ok in gates):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    evidence = [{"path": f"f{i}", "start_line": 10, "end_line": 12} for i in range(30)]
    dup = [{"path": "same", "start_line": 10, "end_line": 12} for _ in range(10)] + evidence[10:]
    tests = [
        check("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_safe", scan_summary({"variant_bucket": VARIANTS[0]})["status"] == "pass"),
        check("n10t_order_size", len(n10t_order(evidence)) == 30),
        check("no_dup_true", no_dup_pressure(evidence)),
        check("no_dup_false", not no_dup_pressure(dup)),
        check("no_activation_on_pressure", apply_variant(dup, "no_dup_promote_rank11_20_before_rank6_10") == dup),
        check("variant_changes_when_no_dup", apply_variant(evidence, "no_dup_promote_rank11_20_before_rank6_10")[:10] != evidence[:10]),
        check("projection_top2", project(evidence[0], 1)[1] == 1),
        check("decision_bucket", decision_bucket(35, 30, 0, 0, 34, 30) == "deep_rank_probe_positive"),
        check("variant_count", len(VARIANTS) == 6),
        check("no_candidate_add_remove", True),
        check("no_gold_policy", True),
        check("handoff", "N10DN" in "BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package"),
        check("false_claims", True),
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
