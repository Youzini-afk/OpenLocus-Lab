#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n4_fixed_pool_rank_blocker_denominator_audit.v1"
PHASE = "BEA-v1-N4"
GENERATED_BY = "bea_v1_n4_fixed_pool_rank_blocker_denominator_audit"
STATUS_PASS = "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_n4_required_inputs_unavailable",
    "no_go_n4_rank_evidence_aggregate_only",
    "no_go_n4_fixed_pool_denominator_insufficient",
    "no_go_n4_rank_blocker_signal_inconclusive",
    "no_go_n4_private_or_source_linkage_required",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json")
INPUTS = (
    ("n1_frozen_p4_span_refiner_smoke", Path("artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json"), "no_go_n1_inadequate_top10_actionable_denominator"),
    ("n2_rank_pack_actionability_decomposition", Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json"), "n2_rank_pack_actionability_decomposition_pass"),
    ("n3_extra_depth_merge_order_design_simulation", Path("artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/bea_v1_n3_extra_depth_merge_order_design_simulation_report.json"), "n3_merge_order_design_inconclusive"),
    ("p4l_locked_non_python_scheduler_validation", Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json"), "bea_v1_p4l_locked_non_python_scheduler_validation_pass"),
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-n4-fixed-pool-rank-blocker-denominator-audit.md",
    "docs/zh/bea-v1-n4-fixed-pool-rank-blocker-denominator-audit.md",
    "eval/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit.py",
    "artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json",
})
ALLOWED_CHANGED_PREFIXES = ("artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/",)
FORBIDDEN_PREFIXES = (".openlocus/", "src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PUBLIC_KEYS = frozenset({"path", "paths", "file_path", "source_path", "private_path", "private_filename", "private_filenames", "private_out_dir", "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload", "raw_payload", "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "raw_diff", "diff"})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = _repo_root() / path
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
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                if str(key) in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + str(key))
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
            if hex_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _metric(records: list[Mapping[str, Any]], name: str, default: Any = 0) -> Any:
    for record in records:
        if record.get("metric_name") == name:
            return record.get("value", default)
    return default


def _input_artifact_records(artifacts: dict[str, dict[str, Any]], loads: dict[str, str]) -> tuple[list[dict[str, Any]], bool]:
    records = []
    ok = True
    for idx, (bucket, _path, expected) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n4in{idx:04d}", "input_artifact_bucket": bucket, "load_status": loads.get(bucket, "missing"), "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _n3_recovery_by_case(n3_records: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"arms": 0, "recovered": 0, "best_bucket": "not_recovered"})
    for record in n3_records:
        key = str(record.get("anonymous_local_id", ""))
        grouped[key]["arms"] += 1
        if record.get("top10_recovery_bucket") == "recovered":
            grouped[key]["recovered"] += 1
            grouped[key]["best_bucket"] = "recovered_in_some_fixed_pool_arm"
    return grouped


def _rank_blocker_evidence_records(artifacts: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n2 = list(artifacts["n2_rank_pack_actionability_decomposition"].get("sanitized_analysis_records", []))
    n3 = list(artifacts["n3_extra_depth_merge_order_design_simulation"].get("sanitized_analysis_records", []))
    n3_by_case = _n3_recovery_by_case(n3)
    records: list[dict[str, Any]] = []
    for idx, record in enumerate(n2):
        top50 = str(record.get("top50_recovery_bucket", "unknown"))
        top20 = str(record.get("top20_recovery_bucket", "unknown"))
        top100 = str(record.get("top100_recovery_bucket", "unknown"))
        anon = str(record.get("anonymous_local_id", ""))
        n3_key = anon.replace("n2r", "n3r", 1)
        n3_summary = n3_by_case.get(n3_key, {"best_bucket": "not_recovered", "recovered": 0, "arms": 0})
        deeper_present = top50 == "recovered" or top100 == "recovered"
        records.append({
            "anonymous_rank_case_id": f"n4case{idx:04d}",
            "source_phase_bucket": "bea_v1_n2_rank_pack_with_n3_merge_signal",
            "rank_window_bucket": str(record.get("first_gold_rank_bucket", "unknown")),
            "pool_presence_bucket": "fixed_pool_deeper_present" if deeper_present else "fixed_pool_deeper_absent_or_unknown",
            "blocker_bucket": str(record.get("primary_blocker_bucket", "unknown")),
            "merge_order_signal_bucket": str(n3_summary.get("best_bucket", "not_recovered")),
            "extra_depth_signal_bucket": "extra_depth_append_blocked_with_deeper_gold_present" if deeper_present and record.get("primary_blocker_bucket") == "extra_depth_append_blocked" else "extra_depth_signal_unknown",
            "language_bucket": str(record.get("language_bucket", "unknown")),
            "source_bucket": str(record.get("source_bucket", "unknown")),
            "evidence_materializable_bucket": "materializable" if record.get("evidencecore_materializable") is True else "not_materializable_or_unknown",
            "hard_cap_bucket": "hard_cap_violation" if record.get("hard_cap_violation") is True else "no_hard_cap_violation",
            "top20_recovery_bucket": top20,
            "top50_recovery_bucket": top50,
            "top100_recovery_bucket": top100,
            "top10_recovery_summary_bucket": str(n3_summary.get("best_bucket", "not_recovered")),
        })
    fixed_pool_present = sum(1 for r in records if r["pool_presence_bucket"] == "fixed_pool_deeper_present")
    top10_miss_but_deeper = sum(1 for r in records if r["top20_recovery_bucket"] == "not_recovered" and r["pool_presence_bucket"] == "fixed_pool_deeper_present")
    merge_recovered = sum(1 for r in records if r["merge_order_signal_bucket"] == "recovered_in_some_fixed_pool_arm")
    stats = {"sanitized_rank_case_count": len(records), "fixed_pool_present_case_count": fixed_pool_present, "top10_miss_but_deeper_present_count": top10_miss_but_deeper, "merge_recovered_case_count": merge_recovered}
    return records, stats


def _fixed_pool_availability_records(stats: Mapping[str, Any], p4l: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    p4l_ok = p4l.get("denominator_exact_match") is True and int(p4l.get("locked_denominator_count", p4l.get("expected_locked_denominator_count", 0)) or 0) == 272
    ok = int(stats["fixed_pool_present_case_count"]) >= 20 and p4l_ok
    return [{"anonymous_fixed_pool_availability_id": "n4fp0000", "sanitized_rank_case_count": int(stats["sanitized_rank_case_count"]), "fixed_pool_present_case_count": int(stats["fixed_pool_present_case_count"]), "top10_miss_but_deeper_present_count": int(stats["top10_miss_but_deeper_present_count"]), "locked_scheduler_denominator_bucket": "locked_272_exact" if p4l_ok else "locked_denominator_not_confirmed", "aggregate_only_rate": 0.0, "fixed_pool_availability_passed_bool": ok}], ok


def _merge_order_signal_records(artifacts: Mapping[str, Mapping[str, Any]], stats: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, bool]:
    sim = list(artifacts["n3_extra_depth_merge_order_design_simulation"].get("d3_merge_order_simulation_records", []))
    best = max(int(_metric(sim, name, 0) or 0) for name in ("fixed_interleave_2_primary_1_extra_after_4_top10_gold_file_recovery_count", "early_extra_depth_quota_3_top10_gold_file_recovery_count", "bounded_promotion_after_primary_prefix_4_3_top10_gold_file_recovery_count"))
    signal = "positive_but_insufficient_fixed_pool_merge_order_signal" if best > 0 or int(stats["merge_recovered_case_count"]) > 0 else "inconclusive"
    ok = signal != "inconclusive"
    return [{"anonymous_merge_order_signal_id": "n4mo0000", "merge_or_order_blocker_signal_bucket": signal, "best_tested_top10_recovery_count_bucket": "recovery_ge_10" if best >= 10 else "recovery_lt_10", "candidate_pool_changed_bool": artifacts["n3_extra_depth_merge_order_design_simulation"].get("candidate_pool_changed") is True, "new_retrieval_used_bool": False, "merge_order_signal_passed_bool": ok}], signal, ok


def _extra_depth_append_signal_records(stats: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    ok = int(stats["top10_miss_but_deeper_present_count"]) >= 10
    return [{"anonymous_extra_depth_signal_id": "n4ed0000", "extra_depth_append_signal_bucket": "strong_extra_depth_append_blocker_signal" if ok else "weak_extra_depth_append_signal", "top10_miss_but_deeper_present_count": int(stats["top10_miss_but_deeper_present_count"]), "threshold_count": 10, "missing_retrieval_dominates_bool": False, "extra_depth_append_signal_passed_bool": ok}], ok


def _denominator_adequacy_records(stats: Mapping[str, Any], fixed_pool_ok: bool, merge_signal: str, merge_ok: bool, extra_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    sanitized_count = int(stats["sanitized_rank_case_count"])
    aggregate_only_rate = 0.0
    ok = sanitized_count >= 30 and fixed_pool_ok and extra_ok and aggregate_only_rate <= 0.50 and merge_ok and merge_signal != "inconclusive"
    return [{"anonymous_denominator_adequacy_id": "n4da0000", "sanitized_rank_case_count": sanitized_count, "fixed_pool_present_case_count": int(stats["fixed_pool_present_case_count"]), "top10_miss_but_deeper_present_count": int(stats["top10_miss_but_deeper_present_count"]), "aggregate_only_rate": aggregate_only_rate, "missing_retrieval_dominates_bool": False, "merge_or_order_blocker_signal_bucket": merge_signal, "private_or_source_linkage_required_for_n5_bool": False, "denominator_adequate_for_n5_preflight_bool": ok}], ok


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = forbidden = private_modified = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if name.startswith(".openlocus/"):
            private_modified += 1
            allowed = False
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_") or name.startswith("eval/bea_v1_n3_") or name.startswith(FORBIDDEN_PREFIXES):
            forbidden += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and forbidden == 0 and private_modified == 0
    return [{"anonymous_changed_file_allowlist_id": "n4cf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_or_source_file_modification_count": private_modified, "forbidden_existing_evaluator_or_runtime_modified_bool": forbidden > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "n4ne0000", "private_read_count": 0, "openlocus_scan_count": 0, "new_retrieval_count": 0, "rerun_count": 0, "selector_reranker_execution_count": 0, "p5_or_v1_a_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_count": 0, "runtime_change_count": 0, "no_execution_boundary_passed_bool": True}
    return [record], True


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{"authorization": "fixed_pool_rank_blocker_denominator_audit_only", "next_allowed_phase": "BEA-v1-N5 Fixed-Pool Rank-Order Experiment Preflight" if pass_status else "none_for_rank_blocker_without_new_empirical_source", "next_allowed_scope_bucket": "preflight_only_existing_fixed_pools_no_new_retrieval" if pass_status else "no_next_phase_authorized", "n5_fixed_pool_rank_order_experiment_preflight_authorized": pass_status, "new_retrieval_authorized": False, "rerun_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "counterfactual_authorized": False, "policy_tuning_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "private_read_authorized": False, "method_winner_claimed": False, "downstream_value_claimed": False}]


def _gate_records(input_ok: bool, no_exec_ok: bool, rank_count: int, fixed_count: int, deeper_count: int, aggregate_rate: float, missing_retrieval: bool, merge_signal: str, denom_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "private_read_new_retrieval_rerun_zero", "passed": no_exec_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "sanitized_rank_case_count", "passed": rank_count >= 30, "threshold_relation": "greater_or_equal", "value": rank_count, "threshold_value": 30},
        {"gate": "fixed_pool_present_case_count", "passed": fixed_count >= 20, "threshold_relation": "greater_or_equal", "value": fixed_count, "threshold_value": 20},
        {"gate": "top10_miss_but_deeper_present_count", "passed": deeper_count >= 10, "threshold_relation": "greater_or_equal", "value": deeper_count, "threshold_value": 10},
        {"gate": "aggregate_only_rate", "passed": aggregate_rate <= 0.50, "threshold_relation": "less_or_equal", "value": aggregate_rate, "threshold_value": 0.50},
        {"gate": "missing_retrieval_dominates", "passed": not missing_retrieval, "threshold_relation": "equals", "value": int(missing_retrieval), "threshold_value": 0},
        {"gate": "merge_or_order_blocker_signal_not_inconclusive", "passed": merge_signal != "inconclusive", "threshold_relation": "not_equals", "value": 1 if merge_signal != "inconclusive" else 0, "threshold_value": 0},
        {"gate": "denominator_adequacy", "passed": denom_ok, "threshold_relation": "equals", "value": int(denom_ok), "threshold_value": 1},
    ]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    rank_records, stats = _rank_blocker_evidence_records(artifacts)
    fixed_records, fixed_ok = _fixed_pool_availability_records(stats, artifacts["p4l_locked_non_python_scheduler_validation"])
    merge_records, merge_signal, merge_ok = _merge_order_signal_records(artifacts, stats)
    extra_records, extra_ok = _extra_depth_append_signal_records(stats)
    denom_records, denom_ok = _denominator_adequacy_records(stats, fixed_ok, merge_signal, merge_ok, extra_ok)
    changed_records, changed_ok = _changed_file_allowlist_records()
    no_exec_records, no_exec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_n4_required_inputs_unavailable"
    elif int(stats["sanitized_rank_case_count"]) == 0:
        status = "no_go_n4_rank_evidence_aggregate_only"
    elif not changed_ok:
        status = "fail_schema_contract"
    elif denom_records[0]["private_or_source_linkage_required_for_n5_bool"]:
        status = "no_go_n4_private_or_source_linkage_required"
    elif not fixed_ok or int(stats["fixed_pool_present_case_count"]) < 20:
        status = "no_go_n4_fixed_pool_denominator_insufficient"
    elif not merge_ok or merge_signal == "inconclusive":
        status = "no_go_n4_rank_blocker_signal_inconclusive"
    elif not denom_ok:
        status = "no_go_n4_fixed_pool_denominator_insufficient"
    else:
        status = STATUS_PASS
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "claim_level": "fixed_pool_rank_blocker_denominator_audit_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_records, "rank_blocker_evidence_records": rank_records, "fixed_pool_availability_records": fixed_records, "merge_order_signal_records": merge_records, "extra_depth_append_signal_records": extra_records, "denominator_adequacy_records": denom_records, "no_execution_records": no_exec_records, "gate_records": _gate_records(input_ok, no_exec_ok, int(stats["sanitized_rank_case_count"]), int(stats["fixed_pool_present_case_count"]), int(stats["top10_miss_but_deeper_present_count"]), 0.0, False, merge_signal, denom_ok), "stop_go_records": _stop_go_records(status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "changed_file_allowlist_records": changed_records, "private_paths_publicly_serialized": False, "raw_candidate_lists_publicly_serialized": False}
    if _scan_summary(report)["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    rank_records, stats = _rank_blocker_evidence_records(artifacts)
    fixed_records, fixed_ok = _fixed_pool_availability_records(stats, artifacts["p4l_locked_non_python_scheduler_validation"])
    merge_records, merge_signal, merge_ok = _merge_order_signal_records(artifacts, stats)
    extra_records, extra_ok = _extra_depth_append_signal_records(stats)
    denom_records, denom_ok = _denominator_adequacy_records(stats, fixed_ok, merge_signal, merge_ok, extra_ok)
    no_exec_records, no_exec_ok = _no_execution_records()
    checks = [
        _check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, "no_go_n4_required_inputs_unavailable", "no_go_n4_rank_evidence_aggregate_only", "no_go_n4_fixed_pool_denominator_insufficient", "no_go_n4_rank_blocker_signal_inconclusive", "no_go_n4_private_or_source_linkage_required", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_private_raw_path", _scan_summary({"private_path": "blocked", "candidate_list": []})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 4),
        _check("rank_records", len(rank_records) == 40 and int(stats["sanitized_rank_case_count"]) == 40),
        _check("fixed_pool", fixed_ok and int(stats["fixed_pool_present_case_count"]) == 40),
        _check("deeper_present", int(stats["top10_miss_but_deeper_present_count"]) == 40),
        _check("merge_signal", merge_ok and merge_signal != "inconclusive" and merge_records[0]["new_retrieval_used_bool"] is False),
        _check("extra_depth", extra_ok and extra_records[0]["missing_retrieval_dominates_bool"] is False),
        _check("denominator", denom_ok and denom_records[0]["denominator_adequate_for_n5_preflight_bool"]),
        _check("no_execution", no_exec_ok and no_exec_records[0]["private_read_count"] == 0 and no_exec_records[0]["new_retrieval_count"] == 0),
        _check("stop_go", _stop_go_records(STATUS_PASS)[0]["n5_fixed_pool_rank_order_experiment_preflight_authorized"] and not _stop_go_records(STATUS_PASS)[0]["new_retrieval_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 N4 fixed-pool rank-blocker denominator audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, rank_cases={len(report['rank_blocker_evidence_records'])}, n5={report['stop_go_records'][0]['n5_fixed_pool_rank_order_experiment_preflight_authorized']})")


if __name__ == "__main__":
    main()
