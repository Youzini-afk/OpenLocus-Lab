#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package.v1"
PHASE = "BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package"
STATUS_COMPLETE = "winning_hybrid_cost_refinement_package_complete_n10co_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cn_required_public_inputs_unavailable",
    "no_go_n10cn_refinement_chain_mismatch",
    "no_go_n10cn_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path(
    "artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/"
    "bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json"
)
PUBLIC_INPUTS = {
    "n10cm_refinement_sweep_artifact": (
        Path(
            "artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/"
            "bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json"
        ),
        "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized",
    ),
    "n10cl_adapter_package_artifact": (
        Path(
            "artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/"
            "bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json"
        ),
        "winning_hybrid_adapter_package_complete_n10cm_authorized",
    ),
    "n10cj_winning_hybrid_package_artifact": (
        Path(
            "artifacts/bea_v1_n10cj_winning_hybrid_replication_package/"
            "bea_v1_n10cj_winning_hybrid_replication_package_report.json"
        ),
        "winning_hybrid_replication_package_complete_n10ck_authorized",
    ),
    "n10cg_observable_hybrid_sweep_artifact": (
        Path(
            "artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/"
            "bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json"
        ),
        "observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized",
    ),
}
WINNING = "short75_225_top3_all_pm200"
REFINED = "short75_225_top2_all_pm200"
FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "path",
        "paths",
        "file_path",
        "private_path",
        "source_path",
        "filename",
        "filenames",
        "file_name",
        "content",
        "raw_content",
        "raw_row",
        "raw_rows",
        "candidate",
        "candidates",
        "candidate_list",
        "candidate_order",
        "p4_evidence",
        "gold_path",
        "gold_paths",
        "gold_line",
        "gold_lines",
        "exact_rank",
        "raw_rank",
        "rank",
        "ranks",
        "score",
        "scores",
        "repo_id",
        "repo_name",
        "repo_url",
        "task_id",
        "source_id",
        "span",
        "spans",
        "snippet",
        "snippets",
        "hash",
        "hashes",
        "source_hash",
        "provider",
        "provider_payload",
        "raw_payload",
        "raw_diff",
        "diff",
    }
)
SAFE_VALUE_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "phase",
        "claim_level",
        "generated_by",
        "generated_at",
        "status_vocabulary",
        "input_artifact_bucket",
        "observed_status",
        "expected_status",
        "load_status",
        "forbidden_scan_status",
        "chain_bucket",
        "variant_bucket",
        "comparison_bucket",
        "decision_bucket",
        "policy_boundary_bucket",
        "claim_boundary_bucket",
        "privacy_boundary_bucket",
        "no_recompute_boundary_bucket",
        "n10co_handoff_bucket",
        "authorization",
        "next_allowed_phase",
        "next_allowed_scope_bucket",
        "gate",
        "threshold_relation",
    }
)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = repo_root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
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
            key = marker.rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())],
    }


def first_record(artifact: dict[str, Any], key: str) -> dict[str, Any]:
    rows = artifact.get(key, [])
    return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}


def variant_rows(artifact: dict[str, Any], variant_bucket: str) -> list[dict[str, Any]]:
    rows = artifact.get("variant_result_records", [])
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("variant_bucket") == variant_bucket]


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        artifacts[bucket] = artifact
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append(
            {
                "anonymous_input_artifact_id": f"n10cnin{idx:04d}",
                "input_artifact_bucket": bucket,
                "load_status": load_status,
                "observed_status": observed,
                "expected_status": expected,
                "forbidden_scan_status": str(scan_status),
                "input_gate_passed_bool": passed,
            }
        )
    return rows, artifacts, ok


def refinement_chain_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    cm = artifacts.get("n10cm_refinement_sweep_artifact", {})
    decision = first_record(cm, "cost_reduction_decision_records")
    frontier = first_record(cm, "frontier_summary_records")
    ok = (
        cm.get("status") == "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized"
        and decision.get("preserves_winning_at_lower_cost_count") == 1
        and decision.get("improves_winning_count") == 0
        and frontier.get("lowest_cost_preserving_winning_top10") == 3200
        and frontier.get("lowest_cost_preserving_winning_top20") == 6200
        and frontier.get("winning_reference_top10") == 25
        and frontier.get("winning_reference_top20") == 31
        and frontier.get("winning_reference_cost10") == 3300
        and frontier.get("winning_reference_cost20") == 6300
    )
    return [
        {
            "anonymous_chain_id": "n10cnchain0000",
            "chain_bucket": "n10cm_public_refinement_chain",
            "n10cm_complete_bool": cm.get("status") == "winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized",
            "winning_reference_variant_bucket": WINNING,
            "winning_reference_top10": 25,
            "winning_reference_top20": 31,
            "winning_reference_cost10": 3300,
            "winning_reference_cost20": 6300,
            "preserves_winning_at_lower_cost_count": decision.get("preserves_winning_at_lower_cost_count", 0),
            "improves_winning_count": decision.get("improves_winning_count", 0),
            "near_winning_cost_saving_tradeoff_count": decision.get("near_winning_cost_saving_tradeoff_count", 0),
            "chain_consistent_bool": ok,
        }
    ], ok


def refined_result_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    cm = artifacts.get("n10cm_refinement_sweep_artifact", {})
    refined = variant_rows(cm, REFINED)
    winning = variant_rows(cm, "anchor_winning_top3_pm200")
    ok = (
        len(refined) == 1
        and len(winning) == 1
        and refined[0].get("top10_span_overlap_count") == 25
        and refined[0].get("top20_span_overlap_count") == 31
        and refined[0].get("cost_proxy_top10") == 3200
        and refined[0].get("cost_proxy_top20") == 6200
        and refined[0].get("cost_savings_vs_winning_top10") == 100
        and refined[0].get("cost_savings_vs_winning_top20") == 100
        and refined[0].get("lost_winning_top10_hits") == 0
        and refined[0].get("decision_bucket") == "preserves_winning_at_lower_cost"
        and refined[0].get("candidate_pool_changed_bool") is False
        and refined[0].get("candidate_order_changed_bool") is False
    )
    return [
        {
            "anonymous_refined_result_id": "n10cnrefined0000",
            "variant_bucket": REFINED,
            "comparison_bucket": "refined_vs_winning_reference",
            "top10_span_overlap_count": 25,
            "top20_span_overlap_count": 31,
            "cost_proxy_top10": 3200,
            "cost_proxy_top20": 6200,
            "cost_savings_vs_winning_top10": 100,
            "cost_savings_vs_winning_top20": 100,
            "lost_winning_top10_hits": 0,
            "decision_bucket": "preserves_winning_at_lower_cost",
            "candidate_pool_changed_bool": False,
            "candidate_order_changed_bool": False,
            "refined_result_valid_bool": ok,
        }
    ], ok


def tradeoff_records(artifacts: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    cm = artifacts.get("n10cm_refinement_sweep_artifact", {})
    required = {
        "short75_225_top1_all_pm200": (24, 30, 1),
        "short75_225_top3_all_pm150": (24, 30, 1),
        "short75_225_top3_all_pm175": (24, 30, 1),
    }
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, expected) in enumerate(required.items()):
        matches = variant_rows(cm, variant)
        row_ok = bool(
            matches
            and matches[0].get("top10_span_overlap_count") == expected[0]
            and matches[0].get("top20_span_overlap_count") == expected[1]
            and matches[0].get("lost_winning_top10_hits") == expected[2]
            and matches[0].get("decision_bucket") == "near_winning_cost_saving_tradeoff"
        )
        ok = ok and row_ok
        rows.append(
            {
                "anonymous_tradeoff_id": f"n10cntradeoff{idx:04d}",
                "variant_bucket": variant,
                "top10_span_overlap_count": expected[0],
                "top20_span_overlap_count": expected[1],
                "lost_winning_top10_hits": expected[2],
                "decision_bucket": "near_winning_cost_saving_tradeoff",
                "tradeoff_valid_bool": row_ok,
            }
        )
    return rows, ok


def policy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {
            "anonymous_policy_boundary_id": "n10cnpolicy0000",
            "policy_boundary_bucket": "same_source_observable_fixed_variant_package_only",
            "same_source_n1_proxy_only_bool": True,
            "observable_span_length_and_position_only_bool": True,
            "gold_used_for_policy_bool": False,
            "outcome_used_for_policy_bool": False,
            "miss_direction_used_for_policy_bool": False,
            "content_used_for_policy_bool": False,
            "file_identity_used_for_policy_bool": False,
            "candidate_pool_changed_bool": False,
            "candidate_order_changed_bool": False,
            "policy_boundary_valid_bool": True,
        }
    ]
    return rows, True


def claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {
            "anonymous_claim_boundary_id": "n10cnclaim0000",
            "claim_boundary_bucket": "same_source_refinement_package_only",
            "runtime_default_claim_bool": False,
            "existing_evaluator_hook_claim_bool": False,
            "heldout_claim_bool": False,
            "generalization_claim_bool": False,
            "method_winner_claim_bool": False,
            "downstream_value_claim_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "candidate_add_remove_reorder_authorized_bool": False,
            "adaptive_tuning_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "claim_boundary_valid_bool": True,
        }
    ]
    return rows, True


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {
            "anonymous_privacy_boundary_id": "n10cnprivacy0000",
            "privacy_boundary_bucket": "public_refinement_package_only",
            "private_read_count": 0,
            "recompute_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "private_content_public_bool": False,
            "span_public_bool": False,
            "line_number_public_bool": False,
            "snippet_public_bool": False,
            "gold_public_bool": False,
            "candidate_list_public_bool": False,
            "exact_rank_public_bool": False,
            "privacy_boundary_complete_bool": True,
        }
    ]
    return rows, True


def no_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {
            "anonymous_no_recompute_id": "n10cnnorecompute0000",
            "no_recompute_boundary_bucket": "public_package_no_private_read_no_recompute",
            "private_read_count": 0,
            "recompute_count": 0,
            "new_variant_count": 0,
            "runtime_default_promotion_count": 0,
            "existing_evaluator_hook_count": 0,
            "heldout_claim_count": 0,
            "retrieval_execution_count": 0,
            "rerun_execution_count": 0,
            "candidate_generation_count": 0,
            "candidate_add_remove_reorder_count": 0,
            "adaptive_tuning_count": 0,
            "selector_reranker_execution_count": 0,
            "p5_execution_count": 0,
            "v1a_execution_count": 0,
            "no_recompute_boundary_valid_bool": True,
        }
    ]
    return rows, True


def n10co_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [
        {
            "anonymous_n10co_handoff_id": "n10cnhandoff0000",
            "n10co_handoff_bucket": "n10co_default_off_adapter_smoke_refined_hybrid_authorized" if complete else "n10co_not_authorized",
            "n10co_authorized_bool": complete,
            "refined_hybrid_variant_bucket": REFINED,
            "adapter_smoke_only_bool": complete,
            "runtime_default_authorized_bool": False,
            "existing_evaluator_hook_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "candidate_add_remove_reorder_authorized_bool": False,
            "adaptive_tuning_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_authorized_bool": False,
        }
    ]


def gate_records(input_ok: bool, chain_ok: bool, refined_ok: bool, tradeoff_ok: bool, policy_ok: bool, claim_ok: bool, privacy_ok: bool, norecompute_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [
        ("public_inputs_loaded", input_ok),
        ("refinement_chain", chain_ok),
        ("refined_result", refined_ok),
        ("tradeoff_facts", tradeoff_ok),
        ("policy_boundary", policy_ok),
        ("claim_boundary", claim_ok),
        ("privacy_boundary", privacy_ok),
        ("no_private_read_or_recompute", norecompute_ok),
        ("forbidden_scan", scanner_ok),
    ]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [
        {
            "authorization": "n10co_authorized" if complete else "n10co_not_authorized",
            "next_allowed_phase": "BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid short75_225_top2_all_pm200" if complete else "none_until_refinement_package_matches",
            "next_allowed_scope_bucket": "default_off_adapter_smoke_only" if complete else "no_next_phase",
            "n10co_authorized": complete,
            "runtime_or_default_authorized": False,
            "existing_evaluator_hook_authorized": False,
            "heldout_or_generalization_claim_authorized": False,
            "method_winner_claim_authorized": False,
            "downstream_value_claim_authorized": False,
            "retrieval_authorized": False,
            "rerun_authorized": False,
            "candidate_generation_authorized": False,
            "candidate_add_remove_reorder_authorized": False,
            "adaptive_tuning_authorized": False,
            "selector_or_reranker_authorized": False,
            "p5_authorized": False,
            "v1_a_authorized": False,
        }
    ]


def status_for(self_ok: bool, input_ok: bool, chain_ok: bool, refined_ok: bool, tradeoff_ok: bool, policy_ok: bool, claim_ok: bool, privacy_ok: bool, norecompute_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cn_required_public_inputs_unavailable"
    if not chain_ok or not refined_ok or not tradeoff_ok:
        return "no_go_n10cn_refinement_chain_mismatch"
    if not policy_ok or not claim_ok or not privacy_ok or not norecompute_ok:
        return "no_go_n10cn_claim_boundary_invalid"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = refinement_chain_records(artifacts)
    refined_rows, refined_ok = refined_result_records(artifacts)
    tradeoff_rows, tradeoff_ok = tradeoff_records(artifacts)
    policy_rows, policy_ok = policy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, chain_ok, refined_ok, tradeoff_ok, policy_ok, claim_ok, privacy_ok, norecompute_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "phase": PHASE,
        "claim_level": "public_winning_hybrid_cost_refinement_package_only",
        "generated_by": "bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package",
        "generated_at": now(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_rows,
        "refinement_chain_records": chain_rows,
        "refined_result_records": refined_rows,
        "tradeoff_result_records": tradeoff_rows,
        "policy_boundary_records": policy_rows,
        "claim_boundary_records": claim_rows,
        "privacy_boundary_records": privacy_rows,
        "no_recompute_records": norecompute_rows,
        "n10co_handoff_records": n10co_handoff_records(complete),
        "gate_records": gate_records(input_ok, chain_ok, refined_ok, tradeoff_ok, policy_ok, claim_ok, privacy_ok, norecompute_ok, True),
        "stop_go_records": stop_go_records(complete),
        "forbidden_scan": {},
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10co_handoff_records"] = n10co_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, chain_ok, refined_ok, tradeoff_ok, policy_ok, claim_ok, privacy_ok, norecompute_ok, scanner_ok)
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
    input_rows, artifacts, input_ok = input_artifact_records()
    chain_rows, chain_ok = refinement_chain_records(artifacts)
    refined_rows, refined_ok = refined_result_records(artifacts)
    tradeoff_rows, tradeoff_ok = tradeoff_records(artifacts)
    policy_rows, policy_ok = policy_boundary_records()
    claim_rows, claim_ok = claim_boundary_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    norecompute_rows, norecompute_ok = no_recompute_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cn_required_public_inputs_unavailable", "no_go_n10cn_refinement_chain_mismatch", "no_go_n10cn_claim_boundary_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("refinement_chain", chain_ok and chain_rows[0]["preserves_winning_at_lower_cost_count"] == 1),
        check("refined_result", refined_ok and refined_rows[0]["variant_bucket"] == REFINED and refined_rows[0]["top10_span_overlap_count"] == 25 and refined_rows[0]["cost_proxy_top10"] == 3200),
        check("tradeoff_rows", tradeoff_ok and len(tradeoff_rows) == 3 and all(r["top10_span_overlap_count"] == 24 for r in tradeoff_rows)),
        check("policy_boundary", policy_ok and policy_rows[0]["gold_used_for_policy_bool"] is False and policy_rows[0]["file_identity_used_for_policy_bool"] is False),
        check("claim_boundary", claim_ok and claim_rows[0]["runtime_default_claim_bool"] is False and claim_rows[0]["method_winner_claim_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["private_read_count"] == 0 and privacy_rows[0]["span_public_bool"] is False),
        check("no_recompute", norecompute_ok and norecompute_rows[0]["private_read_count"] == 0 and norecompute_rows[0]["recompute_count"] == 0),
        check("synthetic_mismatch", status_for(True, True, True, False, True, True, True, True, True) == "no_go_n10cn_refinement_chain_mismatch"),
        check("false_flags", stop_go_records(True)[0]["n10co_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_generation_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CN winning hybrid cost-refinement audit package")
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")


if __name__ == "__main__":
    main()
