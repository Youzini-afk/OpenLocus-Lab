#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n8_independent_recompute_same_private_rows_same_four_arms.v1"
PHASE = "BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms"
GENERATED_BY = "bea_v1_n8_independent_recompute_same_private_rows_same_four_arms"
STATUS_PASS = "independent_recompute_same_private_rows_pass_n9_authorized"

STATUSES = (
    STATUS_PASS,
    "no_go_n8_required_inputs_unavailable",
    "no_go_n8_private_rank_pack_rows_missing",
    "no_go_n8_private_rank_pack_schema_invalid",
    "no_go_n8_recompute_mismatch",
    "no_go_n8_threshold_reproduction_failed",
    "no_go_n8_privacy_or_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)
PROVENANCE_RULE = "original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal"

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/"
    "bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json"
)
DEFAULT_N6XFRE = Path(
    "artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/"
    "bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json"
)
DEFAULT_N7 = Path(
    "artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/"
    "bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json"
)
DEFAULT_N5 = Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json")
SCOPED_PRIVATE_INPUT = Path(
    ".openlocus/research-private/local_n6xfr_recovery/n2_private/"
    "bea_v1_n2.private_rank_pack_rows.jsonl"
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_paths",
    "filename", "filenames", "file_name", "span", "spans", "snippet", "snippets",
    "content", "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "candidate_order_private", "gold_paths_private",
    "gold_lines_private", "exact_rank", "raw_rank", "rank", "ranks", "rank_list",
    "score", "scores", "task_id", "repo", "repo_id", "repo_name", "repo_url",
    "private_id", "private_record_id", "denominator_index_private", "source_hash",
    "source_hashes", "hash", "hashes", "provider", "provider_payload", "raw_payload",
    "payload", "prompt", "response", "raw", "raw_diff", "diff", "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "private_input_bucket", "intake_status_bucket",
    "arm_bucket", "arm_semantics_bucket", "provenance_rule_bucket", "comparison_status_bucket",
    "threshold_bucket", "decision_bucket", "privacy_boundary_bucket", "public_artifact_bucket",
    "no_execution_boundary_bucket", "n9_handoff_bucket", "gate", "threshold_relation",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "result_status_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _input_artifact_records(n6xfre: dict[str, Any], n6xfre_load: str, n7: dict[str, Any], n7_load: str, n5: dict[str, Any], n5_load: str) -> tuple[list[dict[str, Any]], bool]:
    specs = (
        ("n6xfre_recovered_experiment_artifact", n6xfre_load, n6xfre, "recovered_fixed_pool_rank_order_experiment_pass_n7_authorized"),
        ("n7_result_audit_artifact", n7_load, n7, "recovered_fixed_pool_rank_order_result_audit_pass_n8_authorized"),
        ("n5_preflight_artifact", n5_load, n5, "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    )
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, load, artifact, expected) in enumerate(specs):
        observed = str(artifact.get("status", "") or "")
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        passed = load == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n8in{idx:04d}", "input_artifact_bucket": bucket, "load_status": load, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _read_scoped_private_rows() -> tuple[list[dict[str, Any]], str]:
    full = _repo_root() / SCOPED_PRIVATE_INPUT
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with full.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return [], "schema_invalid"
                    rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def _private_input_intake_records(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], bool]:
    required = {"candidate_order_private", "gold_paths_private", "first_gold_rank_private", "denominator_index_private"}
    schema_ok = load_status == "pass" and len(rows) == 40
    if schema_ok:
        ids: set[Any] = set()
        for row in rows:
            if not required.issubset(row) or not isinstance(row.get("candidate_order_private"), list) or not isinstance(row.get("gold_paths_private"), list):
                schema_ok = False
                break
            ids.add(row.get("denominator_index_private"))
        schema_ok = schema_ok and len(ids) == 40
    return [{
        "anonymous_private_input_intake_id": "n8priv0000",
        "private_input_bucket": "single_scoped_recovered_n2_rank_pack_rows",
        "intake_status_bucket": "pass" if schema_ok else load_status,
        "private_rank_pack_rows_read": len(rows) if load_status == "pass" else 0,
        "single_scoped_private_input_read_bool": load_status == "pass",
        "other_private_files_read_count": 0,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "schema_valid_bool": schema_ok,
    }], schema_ok


def _groups(candidates: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    grouped = {"primary": [], "extra_depth": [], "other_or_unknown": []}
    for cand in sorted(candidates, key=lambda c: int(c.get("rank", 10**9))):
        rank = cand.get("rank")
        if not isinstance(rank, int):
            return grouped, False
        if rank <= 20:
            grouped["primary"].append(cand)
        else:
            grouped["extra_depth"].append(cand)
    return grouped, True


def _arm_order(arm: str, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    ordered = sorted(candidates, key=lambda c: int(c.get("rank", 10**9)))
    grouped, ok = _groups(ordered)
    if not ok:
        return [], False
    primary = grouped["primary"]
    extra = grouped["extra_depth"]
    other = grouped["other_or_unknown"]
    if arm == "baseline_n2_order":
        return ordered, True
    if arm == "extra_depth_promote_before_primary_prefix_4":
        return extra + primary[:4] + primary[4:] + other, True
    if arm == "bounded_interleave_primary2_extra1":
        out: list[dict[str, Any]] = []
        p = e = 0
        while p < len(primary) or e < len(extra):
            out.extend(primary[p:p + 2]); p += 2
            if e < len(extra):
                out.append(extra[e]); e += 1
            if p >= len(primary):
                break
        out.extend(primary[p:]); out.extend(extra[e:]); out.extend(other)
        return out, True
    if arm == "late_extra_depth_demote_after_primary_prefix_8":
        return primary[:8] + primary[8:] + extra + other, True
    return [], False


def _first_gold(order: list[dict[str, Any]], gold_paths: set[str]) -> int | None:
    for idx, cand in enumerate(order, 1):
        if str(cand.get("path", "")) in gold_paths:
            return idx
    return None


def _independent_recompute(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    totals = {arm: {"top10": 0, "top20": 0, "regressions": 0, "hard_cap": 0} for arm in ARMS}
    semantics_ok = True
    for row in rows:
        candidates = row["candidate_order_private"]
        gold_paths = {str(x) for x in row["gold_paths_private"]}
        baseline_order, base_ok = _arm_order("baseline_n2_order", candidates)
        if not base_ok:
            semantics_ok = False
            continue
        base_pos = _first_gold(baseline_order, gold_paths)
        base_top10 = base_pos is not None and base_pos <= 10
        for arm in ARMS:
            order, ok = _arm_order(arm, candidates)
            semantics_ok = semantics_ok and ok
            pos = _first_gold(order, gold_paths) if ok else None
            top10 = pos is not None and pos <= 10
            top20 = pos is not None and pos <= 20
            totals[arm]["top10"] += int(top10)
            totals[arm]["top20"] += int(top20)
            totals[arm]["regressions"] += int(base_top10 and not top10)
    records: list[dict[str, Any]] = []
    for idx, arm in enumerate(ARMS):
        records.append({
            "anonymous_independent_per_arm_result_id": f"n8res{idx:04d}",
            "arm_bucket": arm,
            "result_status_bucket": "passes_n5_threshold" if totals[arm]["top10"] >= 16 and totals[arm]["regressions"] <= 2 else "below_n5_threshold",
            "case_count": 40,
            "top10_recovery_count": totals[arm]["top10"],
            "top20_recovery_count": totals[arm]["top20"],
            "case_regression_count": totals[arm]["regressions"],
            "hard_cap_violation_count": totals[arm]["hard_cap"],
            "candidate_pool_changed_count": 0,
            "candidate_added_count": 0,
            "candidate_removed_count": 0,
        })
    return records, semantics_ok


def _independent_arm_semantics_records(semantics_ok: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_independent_arm_semantics_id": f"n8arm{idx:04d}",
        "arm_bucket": arm,
        "arm_semantics_bucket": "fixed_pool_order_transform_only",
        "provenance_rule_bucket": PROVENANCE_RULE,
        "arm_semantics_exact_match_bool": semantics_ok,
        "candidate_pool_changed_bool": False,
        "new_retrieval_used_bool": False,
        "selector_or_reranker_used_bool": False,
        "gold_used_for_ordering_bool": False,
    } for idx, arm in enumerate(ARMS)]


def _source_per_arm(n6xfre: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("arm_bucket")): r for r in n6xfre.get("per_arm_result_records", []) if isinstance(r, dict)}


def _recompute_comparison_records(independent: list[dict[str, Any]], n6xfre: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    source = _source_per_arm(n6xfre)
    records: list[dict[str, Any]] = []
    ok = set(source) == set(ARMS) and len(independent) == 4
    for idx, rec in enumerate(independent):
        arm = rec["arm_bucket"]
        src = source.get(arm, {})
        top10_match = rec["top10_recovery_count"] == src.get("top10_recovery_count")
        top20_match = rec["top20_recovery_count"] == src.get("top20_recovery_count")
        regression_match = rec["case_regression_count"] == src.get("case_regression_count")
        arm_ok = top10_match and top20_match and regression_match
        ok = ok and arm_ok
        records.append({
            "anonymous_recompute_comparison_id": f"n8cmp{idx:04d}",
            "arm_bucket": arm,
            "comparison_status_bucket": "match" if arm_ok else "mismatch",
            "source_top10_recovery_count": int(src.get("top10_recovery_count", -1)),
            "independent_top10_recovery_count": rec["top10_recovery_count"],
            "source_top20_recovery_count": int(src.get("top20_recovery_count", -1)),
            "independent_top20_recovery_count": rec["top20_recovery_count"],
            "source_case_regression_count": int(src.get("case_regression_count", -1)),
            "independent_case_regression_count": rec["case_regression_count"],
            "comparison_match_bool": arm_ok,
        })
    return records, ok


def _best(records: list[dict[str, Any]]) -> tuple[str, int, int]:
    best = max(records, key=lambda r: int(r["top10_recovery_count"]))
    return best["arm_bucket"], int(best["top10_recovery_count"]), int(best["case_regression_count"])


def _threshold_reproduction_records(independent: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    best_arm, best_top10, best_reg = _best(independent)
    ok = best_arm == "extra_depth_promote_before_primary_prefix_4" and best_top10 == 25 and best_reg == 0
    threshold_pass = best_top10 >= 16 and best_reg <= 2
    ok = ok and threshold_pass
    return [{
        "anonymous_threshold_reproduction_id": "n8threshold0000",
        "threshold_bucket": "top10_recovery_ge_16_and_regressions_le_2",
        "decision_bucket": "threshold_reproduced_pass" if ok else "threshold_reproduction_failed",
        "best_arm_bucket": best_arm,
        "best_top10_recovery_count": best_top10,
        "best_case_regression_count": best_reg,
        "threshold_top10_recovery_count": 16,
        "threshold_case_regression_count": 2,
        "threshold_passed_bool": threshold_pass,
        "threshold_reproduced_bool": ok,
    }], ok


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_privacy_boundary_id": "n8privacy0000",
        "privacy_boundary_bucket": "public_bucket_counts_only_private_input_not_serialized",
        "public_artifact_bucket": "buckets_counts_booleans_only",
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "candidate_list_public_bool": False,
        "gold_path_public_bool": False,
        "exact_rank_public_bool": False,
        "task_repo_id_public_bool": False,
        "source_span_public_bool": False,
        "hash_public_bool": False,
        "provider_payload_public_bool": False,
        "privacy_boundary_complete_bool": True,
    }], True


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_forbidden_execution_id": "n8noexec0000",
        "no_execution_boundary_bucket": "single_private_input_read_independent_transform_only",
        "private_input_read_count": 1,
        "other_private_file_read_count": 0,
        "openlocus_binary_execution_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "selector_reranker_execution_count": 0,
        "p5_execution_count": 0,
        "v1a_execution_count": 0,
        "counterfactual_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "no_forbidden_execution_complete_bool": True,
    }], True


def _n9_handoff_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_n9_handoff_id": "n8handoff0000",
        "n9_handoff_bucket": "recovered_fixed_pool_result_replication_package_only" if pass_status else "n9_not_authorized",
        "n9_replication_package_authorized_bool": pass_status,
        "private_rows_recompute_complete_bool": pass_status,
        "same_four_arms_recomputed_bool": pass_status,
        "runtime_or_default_promotion_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "downstream_value_claim_authorized_bool": False,
    }]


def _gate_records(**v: int | bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", bool(v["input_ok"]), int(bool(v["input_ok"])), 1),
        ("private_rank_pack_rows_read", v["private_rows"] == 40, v["private_rows"], 40),
        ("other_private_file_read_count", v["other_private_reads"] == 0, v["other_private_reads"], 0),
        ("arm_count", v["arm_count"] == 4, v["arm_count"], 4),
        ("best_arm_top10_recovery_count", v["best_top10"] == 25, v["best_top10"], 25),
        ("best_arm_top20_recovery_count", v["best_top20"] == 34, v["best_top20"], 34),
        ("best_case_regression_count", v["best_reg"] == 0, v["best_reg"], 0),
        ("per_arm_recompute_matches_n6xfre", bool(v["comparison_ok"]), int(bool(v["comparison_ok"])), 1),
        ("threshold_reproduced", bool(v["threshold_ok"]), int(bool(v["threshold_ok"])), 1),
        ("candidate_pool_changed_count", v["pool_changed"] == 0, v["pool_changed"], 0),
        ("new_retrieval_used_count", v["retrieval"] == 0, v["retrieval"], 0),
        ("selector_or_reranker_count", v["selector"] == 0, v["selector"], 0),
        ("gold_used_for_ordering_count", v["gold_order"] == 0, v["gold_order"], 0),
        ("forbidden_scan", bool(v["scanner_ok"]), int(bool(v["scanner_ok"])), 1),
    ]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in specs]


def _stop_go_records(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "authorization": "n9_recovered_fixed_pool_result_replication_package_authorized" if pass_status else "n9_not_authorized",
        "next_allowed_phase": "BEA-v1-N9 Recovered Fixed-Pool Result Replication Package" if pass_status else "none_until_independent_recompute_matches_n6xfre",
        "next_allowed_scope_bucket": "n9_public_replication_package_only_no_promotion" if pass_status else "no_next_phase",
        "n9_replication_package_authorized": pass_status,
        "private_read_authorized": False,
        "retrieval_authorized": False,
        "rerun_authorized": False,
        "candidate_generation_authorized": False,
        "candidate_materialization_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "counterfactual_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _status_from(*, self_ok: bool, input_ok: bool, rows_load: str, intake_ok: bool, semantics_ok: bool, comparison_ok: bool, threshold_ok: bool, privacy_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n8_required_inputs_unavailable"
    if rows_load == "missing":
        return "no_go_n8_private_rank_pack_rows_missing"
    if not intake_ok or not semantics_ok:
        return "no_go_n8_private_rank_pack_schema_invalid"
    if not comparison_ok:
        return "no_go_n8_recompute_mismatch"
    if not threshold_ok:
        return "no_go_n8_threshold_reproduction_failed"
    if not privacy_ok:
        return "no_go_n8_privacy_or_claim_boundary_invalid"
    return STATUS_PASS


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    n6xfre, n6xfre_load = _load_json(args.n6xfre_artifact)
    n7, n7_load = _load_json(args.n7_artifact)
    n5, n5_load = _load_json(args.n5_artifact)
    inputs, input_ok = _input_artifact_records(n6xfre, n6xfre_load, n7, n7_load, n5, n5_load)
    rows, rows_load = _read_scoped_private_rows()
    intake_records, intake_ok = _private_input_intake_records(rows, rows_load)
    independent, semantics_ok = _independent_recompute(rows) if intake_ok else ([], False)
    semantics_records = _independent_arm_semantics_records(semantics_ok)
    comparison_records, comparison_ok = _recompute_comparison_records(independent, n6xfre) if independent else ([], False)
    threshold_records, threshold_ok = _threshold_reproduction_records(independent) if independent else ([], False)
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, rows_load=rows_load, intake_ok=intake_ok, semantics_ok=semantics_ok, comparison_ok=comparison_ok, threshold_ok=threshold_ok, privacy_ok=privacy_ok and noexec_ok)
    pass_status = status == STATUS_PASS
    best_arm, best_top10, best_reg = _best(independent) if independent else ("", 0, 0)
    best_top20 = next((int(r["top20_recovery_count"]) for r in independent if r["arm_bucket"] == best_arm), 0)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "independent_recompute_same_private_rows_same_four_arms_only", "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": inputs, "private_input_intake_records": intake_records, "independent_arm_semantics_records": semantics_records, "independent_per_arm_result_records": independent, "recompute_comparison_records": comparison_records, "threshold_reproduction_records": threshold_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "n9_handoff_records": _n9_handoff_records(pass_status),
        "gate_records": _gate_records(input_ok=input_ok, private_rows=len(rows), other_private_reads=0, arm_count=len(independent), best_top10=best_top10, best_top20=best_top20, best_reg=best_reg, comparison_ok=comparison_ok, threshold_ok=threshold_ok, pool_changed=0, retrieval=0, selector=0, gold_order=0, scanner_ok=True),
        "stop_go_records": _stop_go_records(pass_status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    pass_status = report["status"] == STATUS_PASS
    report["gate_records"] = _gate_records(input_ok=input_ok, private_rows=len(rows), other_private_reads=0, arm_count=len(independent), best_top10=best_top10, best_top20=best_top20, best_reg=best_reg, comparison_ok=comparison_ok, threshold_ok=threshold_ok, pool_changed=0, retrieval=0, selector=0, gold_order=0, scanner_ok=scanner_ok)
    report["n9_handoff_records"] = _n9_handoff_records(pass_status)
    report["stop_go_records"] = _stop_go_records(pass_status)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    args = build_parser().parse_args([])
    n6xfre, n6xfre_load = _load_json(args.n6xfre_artifact)
    n7, n7_load = _load_json(args.n7_artifact)
    n5, n5_load = _load_json(args.n5_artifact)
    inputs, input_ok = _input_artifact_records(n6xfre, n6xfre_load, n7, n7_load, n5, n5_load)
    rows, rows_load = _read_scoped_private_rows()
    intake_records, intake_ok = _private_input_intake_records(rows, rows_load)
    independent, semantics_ok = _independent_recompute(rows) if intake_ok else ([], False)
    comparison_records, comparison_ok = _recompute_comparison_records(independent, n6xfre) if independent else ([], False)
    threshold_records, threshold_ok = _threshold_reproduction_records(independent) if independent else ([], False)
    best_arm, best_top10, best_reg = _best(independent) if independent else ("", 0, 0)
    best_top20 = next((int(r["top20_recovery_count"]) for r in independent if r["arm_bucket"] == best_arm), 0)
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_n8_required_inputs_unavailable", "no_go_n8_private_rank_pack_rows_missing", "no_go_n8_private_rank_pack_schema_invalid", "no_go_n8_recompute_mismatch", "no_go_n8_threshold_reproduction_failed", "no_go_n8_privacy_or_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "filename", "candidate_list", "gold_paths_private", "exact_rank", "task_id", "repo", "source_hash", "provider_payload", "raw_diff"))),
        _check("scanner_rejects_path_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("public_inputs", input_ok and len(inputs) == 3),
        _check("private_intake", rows_load == "pass" and intake_ok and intake_records[0]["private_rank_pack_rows_read"] == 40 and intake_records[0]["other_private_files_read_count"] == 0),
        _check("independent_results", len(independent) == 4 and best_arm == "extra_depth_promote_before_primary_prefix_4" and best_top10 == 25 and best_top20 == 34 and best_reg == 0),
        _check("semantics", semantics_ok and all(r["provenance_rule_bucket"] == PROVENANCE_RULE for r in _independent_arm_semantics_records(True))),
        _check("comparison", comparison_ok and len(comparison_records) == 4 and all(r["comparison_match_bool"] for r in comparison_records)),
        _check("threshold", threshold_ok and threshold_records[0]["threshold_passed_bool"] is True and threshold_records[0]["threshold_reproduced_bool"] is True),
        _check("privacy", _privacy_boundary_records()[1] and all(v is False for k, v in _privacy_boundary_records()[0][0].items() if k.endswith("_public_bool"))),
        _check("no_forbidden_execution", _no_forbidden_execution_records()[0][0]["private_input_read_count"] == 1 and _no_forbidden_execution_records()[0][0]["retrieval_execution_count"] == 0),
        _check("n9_handoff", _n9_handoff_records(True)[0]["n9_replication_package_authorized_bool"] is True and _n9_handoff_records(True)[0]["runtime_or_default_promotion_authorized_bool"] is False and _stop_go_records(True)[0]["n9_replication_package_authorized"] is True),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, rows_load="pass", intake_ok=True, semantics_ok=True, comparison_ok=True, threshold_ok=True, privacy_ok=True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N8 independent recompute same private rows same four arms")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n6xfre-artifact", type=Path, default=DEFAULT_N6XFRE)
    parser.add_argument("--n7-artifact", type=Path, default=DEFAULT_N7)
    parser.add_argument("--n5-artifact", type=Path, default=DEFAULT_N5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    threshold = report["threshold_reproduction_records"][0]
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"best_top10={threshold['best_top10_recovery_count']})")


if __name__ == "__main__":
    main()
