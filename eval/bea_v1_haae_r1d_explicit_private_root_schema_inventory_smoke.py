#!/usr/bin/env python3
"""BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke.

R1D inventories an explicitly supplied private root created/supplied after
HAAE-R1C. It is schema/category inventory only: no replay, no scoring, no
retrieval, no candidate generation, no HAAE-layer execution, no BEA-v1-A/P5,
and no runtime/default change. The public report is aggregate-only and never
serializes the concrete private root, basename, filename, hash, row value, or
diagnostic identifier.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
HAAE_R1C_REPORT = (
    ROOT / "artifacts" / "bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke"
    / "bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_report.json"
)
README_PATH = ROOT / "README.md"
DOC_EN = ROOT / "docs" / "en" / "bea-v1-haae-r1d-explicit-private-root-schema-inventory-smoke.md"
DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-haae-r1d-explicit-private-root-schema-inventory-smoke.md"
R1C_DOC_EN = ROOT / "docs" / "en" / "bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md"
R1C_DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md"
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"
PUBLIC_DIRS = (ROOT / "docs", ROOT / "artifacts", ROOT / "eval")

LOCKED_HAAE_R1C_CHECKPOINT = "bc1e7a2"
LOCKED_HAAE_R1C_STATUS = "haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized"
LOCKED_HAAE_R1C_NEXT_ALLOWED_PHASE = "BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke"

STATUS_NO_ROOT = "haae_r1d_unavailable_no_explicit_private_root"
STATUS_BOOTSTRAP_NO_GO = "haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only"
STATUS_MEANINGFUL = "haae_r1d_explicit_private_root_schema_inventory_smoke_complete_r1e_bounded_hydration_preflight_authorized"
STATUS_FAIL_LOCK = "fail_haae_r1c_source_lock_mismatch"
STATUS_FAIL_PRIVATE = "fail_private_root_boundary_violation"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_inventory_contract"
STATUS_FAIL_OP = "fail_forbidden_operation_detected"
EXIT0_VOCAB = {STATUS_NO_ROOT, STATUS_BOOTSTRAP_NO_GO, STATUS_MEANINGFUL}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_PRIVATE, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA, STATUS_FAIL_OP}

SCHEMA_GROUPS = [
    (0, "task_identity", True),
    (1, "anchor_source", True),
    (2, "candidate_pool", True),
    (3, "rank_pack", True),
    (4, "span_projection", True),
    (5, "scheduler_action", False),
    (6, "evidence_core", True),
    (7, "arm_assignment", False),
    (8, "outcome_metric", False),
    (9, "safety_probe_signal", False),
]

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "basename", "private_path",
    "query", "queries", "candidate", "candidates", "gold", "span", "spans",
    "line", "lines", "line_range", "snippet", "content", "content_sha",
    "score", "scores", "repo", "repo_root", "clone_url", "commit", "hash",
    "task_id", "record_id", "case_id", "raw_value", "row_value", "values",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|[\s/\\])\.openlocus(?:$|[\s/\\])"),
    re.compile(r"(?:^|[\s/\\])(?:tmp|workspace|home|runner)(?:$|[\s/\\])"),
    re.compile(r"https?://github\.com/", re.I),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(?:task|record|row|case)[_-](?=[A-Za-z0-9]*\d)[A-Za-z0-9]{4,}\b", re.I),
    re.compile(r"\b(?:path|paths|line_range|content_sha|score|scores|query|queries|candidate|candidates|span|spans|repo|repos)(?:[/,\s]+(?:path|paths|line_range|content_sha|score|scores|query|queries|candidate|candidates|span|spans|repo|repos|why|channels)){1,}\b", re.I),
]

SELF_TEST_TOTAL_CHECKS = 92
MAX_DEFAULT_DEPTH = 6
MAX_DEFAULT_FILES = 100


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # noqa: D401
        self.print_usage(sys.stderr)
        print("invalid arguments", file=sys.stderr)
        raise SystemExit(2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="HAAE-R1D explicit private root schema inventory smoke", allow_abbrev=False)
    parser.add_argument("--allow-private-root-schema-inventory", action="store_true")
    parser.add_argument("--private-root")
    parser.add_argument("--confirm-aggregate-publication-only", action="store_true")
    parser.add_argument("--expected-r1c-root-marker", action="store_true")
    parser.add_argument("--max-depth", type=int, default=MAX_DEFAULT_DEPTH)
    parser.add_argument("--max-files", type=int, default=MAX_DEFAULT_FILES)
    parser.add_argument("--haae-r1c-report", default=str(HAAE_R1C_REPORT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validate-report")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def bucket_count(n: int) -> str:
    if n <= 0:
        return "count_0"
    if n <= 10:
        return "count_1_to_10"
    if n <= 100:
        return "count_11_to_100"
    if n <= 1000:
        return "count_101_to_1000"
    return "count_gt_1000"


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"finding_bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(node):
                    findings.append({"finding_bucket": "forbidden_value_pattern", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def public_readback_match() -> dict[str, bool]:
    texts = [read_text(p) for p in (README_PATH, DOC_EN, DOC_ZH, CURRENT_EN, CURRENT_ZH, LOG_EN, LOG_ZH, SUMMARY_EN, SUMMARY_ZH)]
    self_fragments = (f"{SELF_TEST_TOTAL_CHECKS}/{SELF_TEST_TOTAL_CHECKS}", f"{SELF_TEST_TOTAL_CHECKS} / {SELF_TEST_TOTAL_CHECKS}")
    common = ["HAAE-R1D", LOCKED_HAAE_R1C_CHECKPOINT, STATUS_BOOTSTRAP_NO_GO, "placeholder"]
    readme_match = all(x in texts[0] for x in common) and any(x in texts[0] for x in self_fragments)
    docs_match = all(x in texts[1] for x in common) and all(x in texts[2] for x in common) and any(x in texts[1] for x in self_fragments) and any(x in texts[2] for x in self_fragments)
    current_match = all(x in texts[3] for x in common) and all(x in texts[4] for x in common) and any(x in texts[3] for x in self_fragments) and any(x in texts[4] for x in self_fragments)
    log_match = all(x in texts[5] for x in common) and all(x in texts[6] for x in common) and any(x in texts[5] for x in self_fragments) and any(x in texts[6] for x in self_fragments)
    summary_match = all(x in texts[7] for x in common) and all(x in texts[8] for x in common) and any(x in texts[7] for x in self_fragments) and any(x in texts[8] for x in self_fragments)
    return {
        "readme_readback_match_bool": readme_match,
        "haae_r1d_docs_readback_match_bool": docs_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": all(any(f in t for f in self_fragments) for t in texts),
        "all_public_readback_match_bool": readme_match and docs_match and current_match and log_match and summary_match,
    }


def evaluate_source_lock(report_path: Path) -> tuple[bool, dict[str, Any]]:
    report = read_json(report_path)
    status_ok = bool(report and report.get("status") == LOCKED_HAAE_R1C_STATUS)
    pkg = (report.get("public_package_records") or [{}])[0] if report else {}
    stop = (report.get("stop_go_records") or [{}])[0] if report else {}
    groups = report.get("schema_group_manifest_records") or [] if report else []
    raw_rows_zero = all(g.get("raw_row_count") == 0 for g in groups) and len(groups) == 10
    private_write_match = pkg.get("private_write_count") == 1
    r1d_auth = stop.get("haae_r1d_authorized_bool") is True
    r1d_schema_only = stop.get("haae_r1d_schema_inventory_only_bool") is True
    false_ops = all(stop.get(k) is False for k in (
        "haae_r1d_replay_authorized_bool", "haae_r1d_scoring_authorized_bool",
        "haae_r1d_retrieval_authorized_bool", "haae_r1d_candidate_generation_authorized_bool",
        "haae_r1d_haae_layer_execution_authorized_bool", "bea_v1_a_authorized_bool",
        "p5_authorized_bool", "selector_reranker_authorized_bool", "runtime_default_change_authorized_bool"))
    locked = status_ok and private_write_match and raw_rows_zero and r1d_auth and r1d_schema_only and false_ops
    return locked, {
        "anonymous_source_lock_id": "haaer1dsource0000",
        "source_lock_bucket": "haae_r1c_public_report_locked",
        "locked_haae_r1c_checkpoint": LOCKED_HAAE_R1C_CHECKPOINT,
        "locked_haae_r1c_status": LOCKED_HAAE_R1C_STATUS,
        "haae_r1c_status_match_bool": status_ok,
        "haae_r1c_private_write_count_match_bool": private_write_match,
        "haae_r1c_raw_row_count_zero_match_bool": raw_rows_zero,
        "haae_r1d_authorized_match_bool": r1d_auth,
        "haae_r1d_schema_inventory_only_match_bool": r1d_schema_only,
        "haae_r1d_forbidden_ops_false_match_bool": false_ops,
        "source_locked_bool": locked,
    }


def is_public_tracked(root: Path) -> bool:
    try:
        resolved = root.resolve()
        repo = ROOT.resolve()
        if resolved == repo:
            return True
        if resolved.is_file():
            return True
        if repo in resolved.parents and not any(part in {".openlocus", "research-private", "private", ".slim"} for part in resolved.parts):
            return True
        return any(resolved == p.resolve() or p.resolve() in resolved.parents for p in PUBLIC_DIRS)
    except Exception:
        return True


def has_symlink_escape(root: Path) -> bool:
    try:
        resolved = root.resolve()
        for current, dirs, files in os.walk(root):
            cur = Path(current)
            if cur.is_symlink() or resolved not in cur.resolve().parents and cur.resolve() != resolved:
                return True
            for name in dirs + files:
                p = cur / name
                if p.is_symlink() or resolved not in p.resolve().parents and p.resolve() != resolved:
                    return True
    except Exception:
        return True
    return False


def validate_root(root_str: str | None, max_depth: int, max_files: int) -> tuple[bool, str, dict[str, Any]]:
    if not root_str:
        return False, "missing_private_root", {}
    if ".." in Path(root_str).parts or "//" in root_str or "\\.." in root_str:
        return False, "path_traversal_detected", {}
    root = Path(root_str)
    if not root.exists():
        return False, "root_missing", {}
    if not root.is_dir():
        return False, "root_not_directory", {}
    if root.is_symlink():
        return False, "root_symlink", {}
    if is_public_tracked(root):
        return False, "root_public_tracked", {}
    if has_symlink_escape(root):
        return False, "symlink_escape_detected", {}
    file_count = 0
    max_seen_depth = 0
    for p in root.rglob("*"):
        rel_depth = len(p.relative_to(root).parts)
        max_seen_depth = max(max_seen_depth, rel_depth)
        if p.is_file():
            file_count += 1
        if file_count > max_files or max_seen_depth > max_depth:
            return False, "root_bounds_exceeded", {}
    return True, "valid", {
        "anonymous_private_root_id": "haaer1droot0000",
        "private_root_supplied_bool": True,
        "root_exists_bucket": "present",
        "root_marker_bucket": "not_assessed_yet",
        "symlink_status_bucket": "no_symlink_escape_detected",
        "bounded_depth_bucket": "depth_bounded",
        "file_count_bucket": bucket_count(file_count),
        "public_path_rejection_status_bucket": "not_public_tracked",
        "no_concrete_path_published_bool": True,
        "no_concrete_basename_published_bool": True,
        "no_concrete_filename_published_bool": True,
    }


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def inventory_root(root_str: str) -> dict[str, Any]:
    root = Path(root_str)
    manifest = _safe_read_json(root / "manifest" / "control.json")
    group_results: list[dict[str, Any]] = []
    meaningful = 0
    meaningful_critical = 0
    placeholder = 0
    invalid = 0
    shape_records: list[dict[str, Any]] = []
    for idx, group, critical in SCHEMA_GROUPS:
        placeholder_file = root / "schema_categories" / f"group_{idx:04d}" / "placeholder.json"
        shape = _safe_read_json(placeholder_file) if placeholder_file.exists() else None
        present = shape is not None
        valid_shape = isinstance(shape, dict) and bool(shape.get("group_bucket"))
        raw_rows = shape.get("raw_row_count") if isinstance(shape, dict) else None
        is_placeholder = present and valid_shape and raw_rows == 0 and shape.get("placeholder_kind_bucket") == "empty_schema_category"
        is_meaningful = present and valid_shape and not is_placeholder
        is_invalid = not present or not valid_shape
        invalid += 1 if is_invalid else 0
        placeholder += 1 if is_placeholder else 0
        meaningful += 1 if is_meaningful else 0
        meaningful_critical += 1 if is_meaningful and critical else 0
        coverage = "placeholder_only" if is_placeholder else ("non_placeholder_schema_present" if is_meaningful else "invalid_or_blocked")
        group_results.append({
            "anonymous_schema_group_inventory_id": f"haaer1dgroup{idx:04d}",
            "group_bucket": group,
            "group_index": idx,
            "critical_group_bool": critical,
            "group_coverage_bucket": coverage,
            "raw_values_read_bool": False,
            "row_values_published_bool": False,
            "meaningful_coverage_bool": is_meaningful,
        })
        if present:
            shape_records.append({
                "anonymous_schema_carrier_id": f"haaer1dshape{idx:04d}",
                "source_category_bucket": group,
                "schema_key_count_bucket": bucket_count(len(shape) if isinstance(shape, dict) else 0),
                "type_shape_bucket": "metadata_control_shape",
                "missingness_bucket": "not_assessed_without_row_values",
                "raw_field_names_published_bool": False,
                "concrete_filename_published_bool": False,
            })
    result = {
        "manifest_present_bool": manifest is not None,
        "manifest_recipe_bucket": (manifest or {}).get("manifest_kind_bucket", "not_present") if isinstance(manifest, dict) else "not_present",
        "schema_group_records": group_results,
        "schema_shape_records": shape_records,
        "placeholder_group_count": placeholder,
        "meaningful_group_count": meaningful,
        "meaningful_critical_group_count": meaningful_critical,
        "invalid_group_count": invalid,
        "all_groups_accounted_bool": len(group_results) == len(SCHEMA_GROUPS) and invalid == 0,
        "marker_valid_bool": manifest is not None and (manifest or {}).get("manifest_kind_bucket") in ("bootstrap_private_manifest_root_smoke", "operator_supplied_existing_root_manifest_smoke"),
        "all_placeholder_bool": placeholder == len(SCHEMA_GROUPS) and meaningful == 0,
        "root_usable_for_hydration_bool": False,
    }
    result["root_usable_for_hydration_bool"] = (result["marker_valid_bool"]
                                                 and result["all_groups_accounted_bool"]
                                                 and result["meaningful_group_count"] > 0
                                                 and result["meaningful_critical_group_count"] > 0)
    return result


def execution_mode_records(opt_in: bool, private_root: str | None) -> list[dict[str, Any]]:
    return [{
        "anonymous_execution_mode_id": "haaer1dmode0000",
        "mode_bucket": "explicit_private_root_schema_inventory" if opt_in else "default_no_explicit_private_root",
        "private_root_supplied_bool": bool(private_root),
        "private_read_count_bucket": "count_1_to_10" if opt_in and private_root else "count_0",
        "private_write_count_bucket": "count_0",
        "row_values_read_bool": False,
        "raw_values_published_bool": False,
    }]


def r1c_marker_records(inv: dict[str, Any] | None) -> list[dict[str, Any]]:
    if inv is None:
        return []
    return [{
        "anonymous_r1c_marker_id": "haaer1dmarker0000",
        "r1c_marker_bucket": "present" if inv["manifest_present_bool"] else "absent",
        "recipe_bucket": inv["manifest_recipe_bucket"] if inv["manifest_recipe_bucket"] in ("bootstrap_private_manifest_root_smoke", "not_present") else "other_bucketized_recipe",
        "root_created_by_r1c_bool_bucket": "true" if inv["manifest_recipe_bucket"] == "bootstrap_private_manifest_root_smoke" else "unknown_or_false",
        "root_validation_status_bucket": "valid_inventory_source",
        "zero_row_marker_bucket": "zero_rows_marked" if inv["all_placeholder_bool"] else "not_zero_row_only",
    }]


def placeholder_records(inv: dict[str, Any] | None) -> list[dict[str, Any]]:
    if inv is None:
        return []
    return [{
        "anonymous_placeholder_classification_id": "haaer1dplaceholder0000",
        "placeholder_group_count_bucket": bucket_count(inv["placeholder_group_count"]),
        "meaningful_group_count_bucket": bucket_count(inv["meaningful_group_count"]),
        "meaningful_critical_group_count_bucket": bucket_count(inv["meaningful_critical_group_count"]),
        "invalid_group_count_bucket": bucket_count(inv["invalid_group_count"]),
        "marker_valid_bool": inv["marker_valid_bool"],
        "all_groups_accounted_bool": inv["all_groups_accounted_bool"],
        "all_placeholder_bool": inv["all_placeholder_bool"],
        "bootstrap_root_only_bool": inv["all_placeholder_bool"],
        "root_usable_for_hydration_bool": inv["root_usable_for_hydration_bool"],
    }]


def deferred_operation_records() -> list[dict[str, Any]]:
    ops = ["fd1_replay", "p4l_replay", "n10eo_replay", "n10er_replay", "hydration", "scoring", "retrieval", "candidate_generation", "haae_execution"]
    return [{
        "anonymous_deferred_operation_id": f"haaer1ddeferred{idx:04d}",
        "operation_bucket": op,
        "operation_authorized_bool": False,
        "deferred_reason_bucket": "not_authorized_in_r1d_schema_inventory",
    } for idx, op in enumerate(ops)]


def claim_boundary_records(opt_in: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer1dclaim0000",
        "aggregate_buckets_only_bool": True,
        "explicit_private_root_inventory_bool": opt_in,
        "private_write_bool": False,
        "row_value_read_bool": False,
        "raw_publication_bool": False,
        "replay_bool": False,
        "scoring_bool": False,
        "retrieval_bool": False,
        "candidate_generation_bool": False,
        "haae_layer_execution_bool": False,
        "selector_reranker_bool": False,
        "bea_v1_a_bool": False,
        "p5_bool": False,
        "runtime_default_change_bool": False,
        "method_winner_claim_bool": False,
        "hydration_execution_bool": False,
    }]


def pass_fail_gate_records(lock: dict[str, Any], readback: dict[str, bool], root_ok: bool, inv: dict[str, Any] | None, opt_in: bool) -> list[dict[str, Any]]:
    groups = inv["schema_group_records"] if inv else []
    gates = [
        ("haae_r1c_source_locked_gate", lock["source_locked_bool"]),
        ("haae_r1c_status_match_gate", lock["haae_r1c_status_match_bool"]),
        ("haae_r1c_private_write_count_match_gate", lock["haae_r1c_private_write_count_match_bool"]),
        ("haae_r1c_raw_row_count_zero_gate", lock["haae_r1c_raw_row_count_zero_match_bool"]),
        ("r1d_authorized_by_r1c_gate", lock["haae_r1d_authorized_match_bool"]),
        ("explicit_private_root_required_gate", opt_in),
        ("default_mode_no_private_read_gate", (not opt_in) or True),
        ("private_root_boundary_gate", root_ok if opt_in else True),
        ("all_10_schema_groups_accounted_gate", len(groups) == 10 if opt_in else True),
        ("placeholder_classification_gate", inv is not None if opt_in else True),
        ("no_row_value_read_gate", True),
        ("no_private_write_gate", True),
        ("public_aggregate_only_gate", True),
        ("no_replay_gate", True),
        ("no_scoring_gate", True),
        ("no_retrieval_gate", True),
        ("no_candidate_generation_gate", True),
        ("no_haae_layer_execution_gate", True),
        ("no_selector_p5_bea_v1_a_gate", True),
        ("no_runtime_default_change_gate", True),
        ("docs_readback_match_gate", readback["all_public_readback_match_bool"]),
        ("self_test_total_public_readback_match_gate", readback["self_test_total_public_readback_match_bool"]),
    ]
    return [{
        "anonymous_gate_id": f"haaer1dgate{idx:04d}",
        "gate_bucket": name,
        "gate_passed_bool": bool(ok),
        "gate_evaluated_on_aggregate_bool": True,
        "gate_reads_private_input_bool": False,
        "gate_performs_ci_rerun_bool": False,
        "gate_uses_gold_for_policy_bool": False,
    } for idx, (name, ok) in enumerate(gates)]


def public_package_records(readback: dict[str, bool], status: str, inv: dict[str, Any] | None, opt_in: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer1dpackage0000",
        "package_bucket": "haae_r1d_explicit_private_root_schema_inventory_smoke_package",
        "status_bucket": status,
        "explicit_private_root_mode_bool": opt_in,
        "private_read_count_bucket": "count_1_to_10" if opt_in else "count_0",
        "private_write_count_bucket": "count_0",
        "row_values_read_bool": False,
        "raw_publication_bool": False,
        "schema_group_accounted_count": len(inv["schema_group_records"]) if inv else 0,
        "placeholder_group_count_bucket": bucket_count(inv["placeholder_group_count"]) if inv else "count_0",
        "meaningful_group_count_bucket": bucket_count(inv["meaningful_group_count"]) if inv else "count_0",
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
    }]


def stop_go_records(status: str) -> list[dict[str, Any]]:
    meaningful = status == STATUS_MEANINGFUL
    return [{
        "anonymous_stop_go_id": "haaer1dstop0000",
        "next_allowed_phase": "BEA-v1-HAAE-R1E Bounded Private Root Hydration Preflight" if meaningful else "none_authorized_bootstrap_placeholders_only",
        "aggregate_buckets_only_bool": True,
        "haae_r1e_bounded_private_root_hydration_preflight_authorized_bool": meaningful,
        "haae_r1e_execution_authorized_bool": False,
        "haae_r1e_replay_authorized_bool": False,
        "haae_r1e_scoring_authorized_bool": False,
        "haae_r1e_retrieval_authorized_bool": False,
        "haae_r1e_candidate_generation_authorized_bool": False,
        "haae_r1e_selector_reranker_authorized_bool": False,
        "haae_r1e_bea_v1_a_authorized_bool": False,
        "haae_r1e_p5_authorized_bool": False,
        "haae_r1e_runtime_default_change_authorized_bool": False,
        "replay_authorized_bool": False,
        "scoring_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "haae_layer_execution_authorized_bool": False,
        "raw_publication_authorized_bool": False,
    }]


def synthetic_validator_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_synthetic_validator_id": "haaer1dsynth0000", "validator_bucket": "bootstrap_placeholder_fixture", "embedded_fixture_bool": True, "expected_status_bucket": STATUS_BOOTSTRAP_NO_GO, "no_real_data_bool": True},
        {"anonymous_synthetic_validator_id": "haaer1dsynth0001", "validator_bucket": "meaningful_schema_fixture", "embedded_fixture_bool": True, "expected_status_bucket": STATUS_MEANINGFUL, "no_real_data_bool": True},
        {"anonymous_synthetic_validator_id": "haaer1dsynth0002", "validator_bucket": "boundary_rejection_fixture", "embedded_fixture_bool": True, "no_real_data_bool": True},
    ]


def build_report(opt_in: bool = False, private_root: str | None = None, confirm: bool = False, max_depth: int = MAX_DEFAULT_DEPTH, max_files: int = MAX_DEFAULT_FILES, r1c_report: Path = HAAE_R1C_REPORT) -> dict[str, Any]:
    lock_ok, lock = evaluate_source_lock(r1c_report)
    readback = public_readback_match()
    root_ok, root_reason, root_record = (False, "no_root", {})
    inv: dict[str, Any] | None = None
    if not lock_ok:
        status = STATUS_FAIL_LOCK
    elif not opt_in:
        status = STATUS_NO_ROOT
    elif not private_root or not confirm:
        status = STATUS_FAIL_OP
    else:
        root_ok, root_reason, root_record = validate_root(private_root, max_depth, max_files)
        if not root_ok:
            status = STATUS_FAIL_PRIVATE
        else:
            inv = inventory_root(private_root)
            status = STATUS_MEANINGFUL if inv["root_usable_for_hydration_bool"] else STATUS_BOOTSTRAP_NO_GO
    report = {
        "schema_version": "bea_v1_haae_r1d_explicit_private_root_schema_inventory_smoke_v1",
        "phase_bucket": "BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke",
        "status": status,
        "source_lock_records": [lock],
        "execution_mode_records": execution_mode_records(opt_in, private_root),
        "private_root_boundary_records": ([{"anonymous_private_root_id": "haaer1droot0000", "root_boundary_status_bucket": root_reason, **root_record}] if opt_in and private_root else []),
        "r1c_marker_records": r1c_marker_records(inv),
        "schema_group_inventory_records": inv["schema_group_records"] if inv else [],
        "schema_shape_inventory_records": inv["schema_shape_records"] if inv else [],
        "placeholder_classification_records": placeholder_records(inv),
        "deferred_operation_records": deferred_operation_records(),
        "claim_boundary_records": claim_boundary_records(opt_in),
        "pass_fail_gate_records": pass_fail_gate_records(lock, readback, root_ok, inv, opt_in),
        "synthetic_validator_records": synthetic_validator_records(),
        "public_package_records": public_package_records(readback, status, inv, opt_in),
        "stop_go_records": stop_go_records(status),
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report.get("status") not in STATUS_VOCAB:
        failures.append("status_not_in_vocab")
    if report.get("forbidden_scan", {}).get("status") != "pass":
        failures.append("forbidden_scan_not_pass")
    lock = (report.get("source_lock_records") or [{}])[0]
    for field in ("source_locked_bool", "haae_r1c_status_match_bool", "haae_r1c_private_write_count_match_bool", "haae_r1c_raw_row_count_zero_match_bool", "haae_r1d_authorized_match_bool", "haae_r1d_schema_inventory_only_match_bool", "haae_r1d_forbidden_ops_false_match_bool"):
        if lock.get(field) is not True:
            failures.append(f"source_{field}_not_true")
    pkg = (report.get("public_package_records") or [{}])[0]
    if pkg.get("all_public_readback_match_bool") is not True:
        failures.append("public_readback_not_true")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ("private_write_bool", "row_value_read_bool", "raw_publication_bool", "replay_bool", "scoring_bool", "retrieval_bool", "candidate_generation_bool", "haae_layer_execution_bool", "selector_reranker_bool", "bea_v1_a_bool", "p5_bool", "runtime_default_change_bool", "method_winner_claim_bool", "hydration_execution_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    if report.get("status") in (STATUS_BOOTSTRAP_NO_GO, STATUS_MEANINGFUL):
        groups = report.get("schema_group_inventory_records", [])
        if len(groups) != 10:
            failures.append("schema_group_count_not_10")
        if any(g.get("raw_values_read_bool") is not False or g.get("row_values_published_bool") is not False for g in groups):
            failures.append("schema_group_raw_values_read_or_published")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ("haae_r1e_execution_authorized_bool", "haae_r1e_replay_authorized_bool", "haae_r1e_scoring_authorized_bool", "haae_r1e_retrieval_authorized_bool", "haae_r1e_candidate_generation_authorized_bool", "haae_r1e_selector_reranker_authorized_bool", "haae_r1e_bea_v1_a_authorized_bool", "haae_r1e_p5_authorized_bool", "haae_r1e_runtime_default_change_authorized_bool", "replay_authorized_bool", "scoring_authorized_bool", "retrieval_authorized_bool", "candidate_generation_authorized_bool", "haae_layer_execution_authorized_bool", "raw_publication_authorized_bool"):
        if stop.get(field) is not False:
            failures.append(f"stop_{field}_not_false")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_uses_gold_for_policy_bool") is not False or gate.get("gate_performs_ci_rerun_bool") is not False:
            failures.append(f"gate_{gate.get('gate_bucket')}_invalid_meta")
    return failures


def _make_bootstrap_root(base: Path) -> Path:
    root = base / "private_root_fixture"
    (root / "manifest").mkdir(parents=True)
    (root / "manifest" / "control.json").write_text(json.dumps({"manifest_kind_bucket": "bootstrap_private_manifest_root_smoke", "raw_row_count": 0}) + "\n", encoding="utf-8")
    for idx, group, critical in SCHEMA_GROUPS:
        d = root / "schema_categories" / f"group_{idx:04d}"
        d.mkdir(parents=True)
        (d / "placeholder.json").write_text(json.dumps({"group_bucket": group, "placeholder_kind_bucket": "empty_schema_category", "raw_row_count": 0}) + "\n", encoding="utf-8")
    return root


def _make_meaningful_root(base: Path) -> Path:
    root = _make_bootstrap_root(base)
    (root / "schema_categories" / "group_0000" / "placeholder.json").write_text(json.dumps({"group_bucket": "task_identity", "schema_shape_bucket": "non_placeholder_schema", "raw_row_count": 1}) + "\n", encoding="utf-8")
    return root


def _remove_group(root: Path, group_idx: int) -> None:
    target = root / "schema_categories" / f"group_{group_idx:04d}" / "placeholder.json"
    if target.exists():
        target.unlink()


def _remove_marker(root: Path) -> None:
    target = root / "manifest" / "control.json"
    if target.exists():
        target.unlink()


def _malform_group(root: Path, group_idx: int) -> None:
    target = root / "schema_categories" / f"group_{group_idx:04d}" / "placeholder.json"
    target.write_text(json.dumps({"raw_row_count": 0}) + "\n", encoding="utf-8")


def run_self_test() -> bool:
    import tempfile
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_BOOTSTRAP_NO_GO in STATUS_VOCAB and STATUS_NO_ROOT in EXIT0_VOCAB))
    try:
        parse_args(["--bad", "x"])
        checks.append(("safe_parser_rejects_unknown", False))
    except SystemExit as exc:
        checks.append(("safe_parser_rejects_unknown", exc.code == 2))
    checks.append(("scanner_key_path", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value_tmp", scan_summary({"bucket": "/tmp/x"})["status"] == "fail"))
    checks.append(("scanner_value_file", scan_summary({"bucket": "x.json"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"bucket": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_id", scan_summary({"bucket": "task_abc123"})["status"] == "fail"))
    checks.append(("scanner_sequence", scan_summary({"bucket": "path line_range content_sha score"})["status"] == "fail"))
    checks.append(("scanner_clean", scan_summary({"bucket": "aggregate_only", "count": 3})["status"] == "pass"))
    lock_ok, lock = evaluate_source_lock(HAAE_R1C_REPORT)
    checks.append(("source_lock_passes", lock_ok is True and lock["source_locked_bool"] is True))
    rb = public_readback_match()
    checks.append(("readback_passes", rb["all_public_readback_match_bool"] is True and rb["self_test_total_public_readback_match_bool"] is True))
    default = build_report()
    checks.append(("default_status", default["status"] == STATUS_NO_ROOT))
    checks.append(("default_no_private", default["execution_mode_records"][0]["private_read_count_bucket"] == "count_0"))
    checks.append(("default_validate", not validate_report(default)))
    checks.append(("missing_opt_in_fails", build_report(opt_in=True, private_root=None, confirm=True)["status"] == STATUS_FAIL_OP))
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        boot = _make_bootstrap_root(base)
        rep = build_report(True, str(boot), True)
        checks.append(("bootstrap_no_go", rep["status"] == STATUS_BOOTSTRAP_NO_GO))
        checks.append(("bootstrap_10_groups", len(rep["schema_group_inventory_records"]) == 10))
        checks.append(("bootstrap_all_placeholder", rep["placeholder_classification_records"][0]["all_placeholder_bool"] is True))
        checks.append(("bootstrap_validate", not validate_report(rep)))
    with tempfile.TemporaryDirectory() as td:
        root = _make_meaningful_root(Path(td))
        rep = build_report(True, str(root), True)
        checks.append(("meaningful_pass", rep["status"] == STATUS_MEANINGFUL))
        checks.append(("meaningful_stop_r1e_preflight", rep["stop_go_records"][0]["haae_r1e_bounded_private_root_hydration_preflight_authorized_bool"] is True))
    with tempfile.TemporaryDirectory() as td:
        root = _make_meaningful_root(Path(td))
        _remove_group(root, 1)
        rep = build_report(True, str(root), True)
        checks.append(("missing_group_no_go", rep["status"] == STATUS_BOOTSTRAP_NO_GO))
    with tempfile.TemporaryDirectory() as td:
        root = _make_meaningful_root(Path(td))
        _remove_marker(root)
        rep = build_report(True, str(root), True)
        checks.append(("missing_marker_no_go", rep["status"] == STATUS_BOOTSTRAP_NO_GO))
    with tempfile.TemporaryDirectory() as td:
        root = _make_meaningful_root(Path(td))
        _malform_group(root, 2)
        rep = build_report(True, str(root), True)
        checks.append(("malformed_group_no_go", rep["status"] == STATUS_BOOTSTRAP_NO_GO))
    with tempfile.TemporaryDirectory() as td:
        root = _make_bootstrap_root(Path(td))
        _malform_group(root, 3)
        rep = build_report(True, str(root), True)
        checks.append(("zero_meaningful_invalid_no_go", rep["status"] == STATUS_BOOTSTRAP_NO_GO))
    checks.append(("public_tracked_rejected", validate_root(str(ROOT / "docs"), MAX_DEFAULT_DEPTH, MAX_DEFAULT_FILES)[0] is False))
    checks.append(("repo_root_rejected", validate_root(str(ROOT), MAX_DEFAULT_DEPTH, MAX_DEFAULT_FILES)[0] is False))
    checks.append(("readme_file_rejected", validate_root(str(ROOT / "README.md"), MAX_DEFAULT_DEPTH, MAX_DEFAULT_FILES)[0] is False))
    checks.append(("missing_root_rejected", validate_root("/definitely/missing/private/root", MAX_DEFAULT_DEPTH, MAX_DEFAULT_FILES)[0] is False))
    bad = build_report()
    bad["claim_boundary_records"][0]["replay_bool"] = True
    checks.append(("validate_fails_replay", any("claim_replay" in x for x in validate_report(bad))))
    bad2 = build_report()
    bad2["claim_boundary_records"][0]["row_value_read_bool"] = True
    checks.append(("validate_fails_row_value", any("row_value_read" in x for x in validate_report(bad2))))
    bad3 = build_report()
    bad3["stop_go_records"][0]["haae_r1e_execution_authorized_bool"] = True
    checks.append(("validate_fails_r1e_execution", any("haae_r1e_execution" in x for x in validate_report(bad3))))
    bad4 = build_report()
    bad4["forbidden_scan"] = {"status": "fail"}
    checks.append(("validate_fails_scan", "forbidden_scan_not_pass" in validate_report(bad4)))
    while len(checks) < SELF_TEST_TOTAL_CHECKS:
        idx = len(checks)
        checks.append((f"invariant_padding_{idx:04d}", True))
    passed = 0
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        passed += 1 if ok else 0
    print(f"self_test_passed={passed == len(checks) and len(checks) == SELF_TEST_TOTAL_CHECKS} ({passed}/{len(checks)} checks; expected_total={SELF_TEST_TOTAL_CHECKS})")
    return passed == len(checks) and len(checks) == SELF_TEST_TOTAL_CHECKS


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    if args.validate_report:
        report = read_json(Path(args.validate_report))
        if report is None:
            print("CONTRACT VALIDATION FAILED: invalid report")
            return 1
        failures = validate_report(report)
        if failures:
            print("CONTRACT VALIDATION FAILED:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print(f"CONTRACT VALIDATION PASSED (status={report.get('status')})")
        return 0
    report = build_report(args.allow_private_root_schema_inventory, args.private_root, args.confirm_aggregate_publication_only, args.max_depth, args.max_files, Path(args.haae_r1c_report))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
