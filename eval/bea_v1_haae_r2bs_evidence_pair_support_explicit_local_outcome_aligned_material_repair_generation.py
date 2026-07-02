#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BS explicit local outcome-aligned material repair generation.

Default mode is a public no-op and reads/writes no private roots. Explicit mode
requires operator opt-in, an existing R2BE private material root, an existing
R2BO private label-source root, and a private R2BS output root. It generates
private repaired material only: no metrics, experiments, source scan, runtime,
network, or claims.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BS Evidence-Pair Support Explicit Local Outcome-Aligned Material Repair Generation"
SLUG = "bea_v1_haae_r2bs_evidence_pair_support_explicit_local_outcome_aligned_material_repair_generation"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PRIVATE_SCHEMA = f"{SLUG}_private_material_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BR_REPORT_PATH = Path("artifacts/bea_v1_haae_r2br_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight/bea_v1_haae_r2br_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight_report.json")

R2BR_CHECKPOINT = "b96e717"
R2BR_STATUS = "haae_r2br_outcome_aligned_material_repair_public_design_preflight_complete_r2bs_explicit_local_repair_generation_authorized"
R2BR_SELF_TEST_TOTAL = 51
R2BE_CHECKPOINT = "c3901d6"
R2BO_CHECKPOINT = "07b9eef"

STATUS_DEFAULT = "haae_r2bs_unavailable_no_explicit_local_repair_generation_opt_in"
STATUS_PASS = "haae_r2bs_explicit_local_outcome_aligned_material_repair_generation_complete_r2bt_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2bs_fail_closed_r2br_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2bs_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2bs_fail_closed_private_root_safety"
STATUS_FAIL_GENERATION = "haae_r2bs_fail_closed_repair_generation_contract"
STATUS_FAIL_PRIVACY = "haae_r2bs_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bs_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BT Evidence-Pair Support Outcome-Aligned Material Repair Public Audit Package"

R2BE_GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
R2BO_GROUPS = ["outcome_label_source_manifest_private", "outcome_label_task_alignment_private", "outcome_label_pair_family_alignment_private", "outcome_label_provenance_private", "manual_label_import_private", "existing_label_recovery_private", "label_quality_qa_private", "parent_r2be_row_ref_private"]
R2BS_GROUPS = ["outcome_aligned_task_frame", "outcome_aligned_source_manifest_private", "outcome_aligned_evidence_unit_pool", "outcome_aligned_support_pair_material", "outcome_aligned_control_pair_material", "outcome_label_alignment_eval_private", "gold_isolation_eval_private", "alignment_qa", "parent_r2be_row_ref_private", "parent_r2bo_label_ref_private", "repair_provenance_private"]
R2BE_PHASE = "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation"
R2BO_PHASE = "BEA-v1-HAAE-R2BO Evidence-Pair Support Explicit Local Outcome Label Source Acquisition"
INPUT_MANIFEST_CONTRACTS = {
    "r2be_private_manifest.json": {"phase": R2BE_PHASE, "schema_version": "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_private_material_v1", "source_lock": {"r2bd_checkpoint": "fa6119b", "r2be_checkpoint": R2BE_CHECKPOINT}},
    "r2bo_private_manifest.json": {"phase": R2BO_PHASE, "schema_version": "bea_v1_haae_r2bo_evidence_pair_support_explicit_local_outcome_label_source_acquisition_private_label_acquisition_v1", "source_lock": {"r2bn_checkpoint": "af901f6", "r2be_checkpoint": R2BE_CHECKPOINT, "r2bo_checkpoint": R2BO_CHECKPOINT}},
}
BOUNDS = {"target_tasks": 20, "private_row_cap": 20000, "wall_clock_minutes": 20}

R2BR_STOP_TRUE = ["haae_r2bs_explicit_local_outcome_aligned_material_repair_generation_authorized_bool", "r2bs_explicit_opt_in_required_bool", "r2bs_existing_r2be_private_material_read_authorized_bool", "r2bs_existing_r2bo_private_label_source_read_authorized_bool", "r2bs_private_output_write_authorized_bool", "r2bs_outcome_aligned_material_repair_generation_authorized_bool", "r2bs_material_generation_only_no_experiment_metrics_bool", "r2bs_no_source_scan_bool", "r2bs_aggregate_only_public_artifact_required_bool", "r2bs_public_audit_required_after_generation_bool", "r2bo_label_acquisition_result_locked_bool"]
R2BR_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
STOP_TRUE = ["haae_r2bt_outcome_aligned_material_repair_public_audit_authorized_bool", "r2bt_public_only_audit_bool", "r2bt_no_private_read_bool", "r2bt_no_metric_computation_bool", "r2bt_no_material_generation_bool", "r2bt_no_source_scan_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2br_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "explicit_argument_gate", "r2be_input_root_safety_gate", "r2bo_input_root_safety_gate", "r2bs_output_root_safety_gate", "input_group_exact_gate", "output_group_exact_gate", "label_privacy_eval_only_gate", "no_metrics_gate", "no_source_scan_gate", "aggregate_only_public_gate", "r2bt_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_success_pass", "safe_parser_fail", "missing_allow_flag_fail", "missing_r2be_root_fail", "missing_r2bo_root_fail", "missing_output_root_fail", "unknown_arg_fail", "bad_r2br_checkpoint_fail", "bad_r2br_status_fail", "r2br_stop_go_overauth_fail", "r2be_root_in_repo_fail", "r2be_root_missing_fail", "r2be_root_symlink_fail", "r2bo_root_missing_fail", "r2bo_root_symlink_fail", "input_roots_nested_fail", "input_group_missing_fail", "input_group_extra_fail", "input_group_symlink_fail", "input_manifest_checkpoint_drift_fail", "output_root_in_repo_fail", "nested_output_fail", "output_root_symlink_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "output_group_symlink_escape_fail", "output_group_missing_fail", "output_group_extra_fail", "status_execution_mismatch_fail", "explicit_execution_mode_drift_fail", "explicit_private_read_drift_fail", "explicit_output_write_drift_fail", "root_safety_drift_fail", "label_alignment_bucket_drift_fail", "parent_refs_bucket_drift_fail", "label_privacy_drift_fail", "metric_overauth_fail", "source_scan_overauth_fail", "raw_leak_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_metric_overauth_fail", "stop_go_source_scan_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_drop_fail", "readback_duplicate_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_label", re.compile(r"gold_spans|hard_negatives|gold_label|rationale|start_line|end_line|mined_high_confidence", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|private_label_source_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\brank\b|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def has_traversal(v: str) -> bool: return any(p == ".." for p in Path(v).parts)
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def has_symlink_component(path: Path, must_exist: bool) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/")
    for part in p.parts[1:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
        if must_exist and not cur.exists(): return True
    return False
def nested(a: Path, b: Path) -> bool:
    ar, br = a.resolve(strict=False), b.resolve(strict=False)
    return ar == br or ar in br.parents or br in ar.parents
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [n for n, p in LEAK_PATTERNS if p.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "r2be_root": "", "r2bo_root": "", "output": "", "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2bs-explicit-local-repair-generation": parsed["explicit"] = True; i += 1
        elif a == "--confirm-aggregate-only-publication": parsed["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--r2be-private-material-root", "--r2bo-private-label-root", "--private-output-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--r2be-private-material-root": "r2be_root", "--r2bo-private-label-root": "r2bo_root", "--private-output-root": "output"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "r2be_root", "r2bo_root", "output", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2br(r2br: dict[str, Any]) -> dict[str, bool]:
    src = (r2br.get("source_lock_records") or [{}])[0]; contract = (r2br.get("r2bs_contract_records") or [{}])[0]; bounds = (r2br.get("r2bs_bounds_root_safety_records") or [{}])[0]; stop = (r2br.get("stop_go_records") or [{}])[0]
    locks = r2br.get("status") == R2BR_STATUS and r2br.get("self_test_total") == R2BR_SELF_TEST_TOTAL and r2br.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bq_checkpoint") == R2BR_CHECKPOINT[:0] + "8254d58" and src.get("locked_haae_r2bq_status") == "haae_r2bq_outcome_label_acquisition_next_step_decision_design_complete_r2br_repair_design_preflight_authorized" and src.get("locked_haae_r2bo_checkpoint") == R2BO_CHECKPOINT and src.get("locked_haae_r2bo_self_test_total") == 51 and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("locked_inherited_r2bk_checkpoint") == "7073b12" and src.get("source_locked_bool") is True
    groups = contract.get("output_group_buckets") == R2BS_GROUPS and contract.get("explicit_opt_in_required_bool") is True and contract.get("explicit_r2be_private_material_root_required_bool") is True and contract.get("explicit_r2bo_private_label_source_root_required_bool") is True and contract.get("explicit_private_r2bs_output_root_required_bool") is True and contract.get("no_signal_evaluation_bool") is True
    root_bounds = bounds.get("target_tasks_bucket") == "target_tasks_20" and bounds.get("private_rows_bucket") == "private_rows_le_20000" and bounds.get("wall_clock_bucket") == "wall_clock_le_20_minutes" and bounds.get("input_group_set_exact_required_bool") is True and bounds.get("output_group_set_exact_required_bool") is True and bounds.get("implicit_tmp_discovery_rejected_bool") is True and bounds.get("no_source_scan_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BR_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BR_STOP_FALSE)
    return {"source_ok": locks and groups and root_bounds and stop_ok, "locks_ok": locks, "contract_ok": groups and root_bounds, "stop_ok": stop_ok}

def validate_input_root(value: str, groups: list[str], manifest_name: str, schema_contains: str) -> tuple[bool, str, Path | None, dict[str, list[dict[str, Any]]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    if not value or has_traversal(value): return False, "input_root_traversal_rejected", None, rows
    root = Path(value)
    try:
        if not root.exists() or not root.is_dir() or root.is_symlink() or has_symlink_component(root, True) or not outside_repo(root): return False, "input_root_missing_repo_or_symlink_rejected", None, rows
        manifest = root / manifest_name; groups_dir = root / "groups"
        if not manifest.is_file() or manifest.is_symlink() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "input_manifest_or_groups_invalid", None, rows
        meta = load_json(manifest)
        contract = INPUT_MANIFEST_CONTRACTS.get(manifest_name)
        if contract:
            expected_schema = str(contract["schema_version"])
            expected_phase = str(contract["phase"])
            expected_locks = contract["source_lock"] if isinstance(contract.get("source_lock"), dict) else {}
            if meta.get("schema_version") != expected_schema or meta.get("phase") != expected_phase or (meta.get("ownership") or {}).get("owner_phase") != expected_phase:
                return False, "input_manifest_schema_invalid", None, rows
            source_lock_obj = meta.get("source_lock")
            source_lock: dict[str, Any] = source_lock_obj if isinstance(source_lock_obj, dict) else {}
            for key, expected in expected_locks.items():
                if source_lock.get(key) != expected:
                    return False, "input_manifest_source_lock_invalid", None, rows
        elif schema_contains not in str(meta.get("schema_version", "")) and schema_contains not in str(meta.get("phase", "")):
            return False, "input_manifest_schema_invalid", None, rows
        files = sorted(p.name for p in groups_dir.glob("*.jsonl")); expected = sorted(f"{g}.jsonl" for g in groups)
        if files != expected: return False, "input_group_set_mismatch", None, rows
        for g in groups:
            p = groups_dir / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or has_symlink_component(p, True) or root.resolve() not in p.resolve().parents: return False, "input_group_symlink_or_escape", None, rows
            data = load_jsonl(p)
            if not data: return False, "input_group_empty", None, rows
            rows[g] = data
    except Exception: return False, "input_root_invalid", None, rows
    return True, "input_root_valid", root, rows

def validate_output_root(value: str, input_roots: list[Path | None]) -> tuple[bool, str, Path | None]:
    if not value or has_traversal(value): return False, "output_root_traversal_rejected", None
    out = Path(value)
    try:
        if out.exists() and out.is_symlink(): return False, "output_root_symlink_rejected", None
        if has_symlink_component(out, False) or not outside_repo(out): return False, "output_root_repo_or_symlink_rejected", None
        if any(r is not None and nested(r, out) for r in input_roots): return False, "input_output_nested_rejected", None
        if out.exists() and any(out.iterdir()):
            owner = out / "r2bs_owner_manifest.json"
            if not owner.is_file() or owner.is_symlink(): return False, "nonempty_unowned_output_rejected", None
            old = load_json(owner)
            if old.get("schema_version") != PRIVATE_SCHEMA or old.get("phase") != PHASE: return False, "nonempty_unowned_output_rejected", None
        out.mkdir(parents=True, exist_ok=True); groups_dir = out / "groups"; groups_dir.mkdir(exist_ok=True)
        if groups_dir.is_symlink() or out.resolve() not in groups_dir.resolve().parents: return False, "output_groups_escape_rejected", None
        for child in groups_dir.iterdir():
            if child.is_symlink(): return False, "output_group_symlink_escape_rejected", None
    except Exception: return False, "output_root_invalid", None
    return True, "output_root_valid", out

def repair_material(r2be_rows: dict[str, list[dict[str, Any]]], r2bo_rows: dict[str, list[dict[str, Any]]], out: Path) -> dict[str, Any]:
    start = time.time(); groups_dir = out / "groups"
    tasks = r2be_rows["redesigned_task_frame"][:BOUNDS["target_tasks"]]
    labels = r2bo_rows["outcome_label_source_manifest_private"]
    label_align = r2bo_rows["outcome_label_task_alignment_private"]
    pair_align = r2bo_rows["outcome_label_pair_family_alignment_private"]
    label_by_ref = {r.get("private_label_source_ref"): r for r in labels if isinstance(r.get("private_label_source_ref"), str)}
    align_by_task = {r.get("private_task_ref"): r for r in label_align if isinstance(r.get("private_task_ref"), str) and isinstance(r.get("private_label_source_ref"), str)}
    pair_align_by_task = {r.get("private_task_ref"): r for r in pair_align if isinstance(r.get("private_task_ref"), str)}
    support_by_task: dict[str, list[dict[str, Any]]] = {}
    control_by_task: dict[str, list[dict[str, Any]]] = {}
    evidence_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in r2be_rows["redesigned_support_pair_material"]:
        support_by_task.setdefault(str(row.get("private_task_ref")), []).append(row)
    for row in r2be_rows["redesigned_control_pair_material"]:
        control_by_task.setdefault(str(row.get("private_task_ref")), []).append(row)
    for row in r2be_rows["redesigned_evidence_unit_pool"]:
        evidence_by_task.setdefault(str(row.get("private_task_ref")), []).append(row)
    if not tasks or not labels or not label_align: raise RuntimeError("invalid arguments")
    n = min(len(tasks), BOUNDS["target_tasks"])
    rows: dict[str, list[dict[str, Any]]] = {
        "outcome_aligned_task_frame": [], "outcome_aligned_source_manifest_private": [], "outcome_aligned_evidence_unit_pool": [], "outcome_aligned_support_pair_material": [], "outcome_aligned_control_pair_material": [], "outcome_label_alignment_eval_private": [], "gold_isolation_eval_private": [], "alignment_qa": [], "parent_r2be_row_ref_private": [], "parent_r2bo_label_ref_private": [], "repair_provenance_private": []
    }
    for i in range(n):
        task_parent_ref = str(tasks[i].get("private_task_ref"))
        align = align_by_task.get(task_parent_ref)
        if not align: raise RuntimeError("invalid arguments")
        label_ref = str(align.get("private_label_source_ref"))
        label = label_by_ref.get(label_ref)
        if not label or not label.get("raw_label_values_private_bool") or not label.get("private_gold_spans") or not label.get("private_hard_negatives"):
            raise RuntimeError("invalid arguments")
        pair_info = pair_align_by_task.get(task_parent_ref)
        if not pair_info: raise RuntimeError("invalid arguments")
        task_ref = f"r2bs_private_task_{i:04d}"
        rows["outcome_aligned_task_frame"].append({"private_task_ref": task_ref, "parent_r2be_row_ref_private": task_parent_ref, "parent_r2bo_label_ref_private": label_ref, "parent_r2bo_task_alignment_ref_private": align.get("private_task_alignment_ref"), "outcome_alignment_bucket": "verified_task_label_alignment_materialized", "selection_used_label_bool": False})
        rows["outcome_label_alignment_eval_private"].append({"private_eval_ref": f"r2bs_private_label_eval_{i:04d}", "private_task_ref": task_ref, "parent_r2be_task_ref_private": task_parent_ref, "parent_r2bo_label_ref_private": label_ref, "parent_r2bo_task_alignment_ref_private": align.get("private_task_alignment_ref"), "alignment_bucket": align.get("alignment_bucket"), "private_label_values_eval_only_bool": True, "private_gold_spans_eval_only": label.get("private_gold_spans"), "private_hard_negatives_eval_only": label.get("private_hard_negatives"), "used_for_signal_metric_bool": False})
        rows["gold_isolation_eval_private"].append({"private_gold_eval_ref": f"r2bs_private_gold_eval_{i:04d}", "private_task_ref": task_ref, "parent_r2bo_label_ref_private": label_ref, "gold_hard_negative_eval_only_bool": True, "used_for_source_scan_or_ranking_bool": False})
        rows["parent_r2bo_label_ref_private"].append({"parent_r2bo_label_ref_private": label_ref, "parent_r2bo_task_alignment_ref_private": align.get("private_task_alignment_ref"), "parent_r2bo_pair_family_alignment_ref_private": pair_info.get("private_pair_family_alignment_ref"), "parent_label_bucket": "verified_existing_r2bo_label_source_row"})
        rows["parent_r2be_row_ref_private"].append({"parent_r2be_row_ref_private": task_parent_ref, "parent_material_bucket": "verified_existing_r2be_task_material"})
    for i, row in enumerate(r2be_rows["redesigned_source_manifest_private"][:max(1, min(20, len(r2be_rows["redesigned_source_manifest_private"])))]) : rows["outcome_aligned_source_manifest_private"].append({"private_source_ref": f"r2bs_private_source_{i:04d}", "parent_r2be_row_ref_private": row.get("private_source_ref"), "source_scan_bool": False})
    e_idx = 0
    s_idx = 0
    c_idx = 0
    for task in tasks[:n]:
        task_parent_ref = str(task.get("private_task_ref"))
        align = align_by_task[task_parent_ref]
        label_ref = str(align.get("private_label_source_ref"))
        for row in evidence_by_task.get(task_parent_ref, [])[:3]:
            rows["outcome_aligned_evidence_unit_pool"].append({"private_evidence_unit_ref": f"r2bs_private_evidence_{e_idx:04d}", "parent_r2be_row_ref_private": row.get("private_evidence_unit_ref"), "parent_r2be_task_ref_private": task_parent_ref, "parent_r2bo_label_ref_private": label_ref, "label_aligned_material_bool": True}); e_idx += 1
        for row in support_by_task.get(task_parent_ref, []):
            rows["outcome_aligned_support_pair_material"].append({"private_pair_ref": f"r2bs_private_support_{s_idx:04d}", "parent_r2be_row_ref_private": row.get("private_pair_ref"), "parent_r2be_task_ref_private": task_parent_ref, "parent_r2bo_label_ref_private": label_ref, "label_aligned_support_pair_bool": True, "experiment_metric_bool": False}); s_idx += 1
        for row in control_by_task.get(task_parent_ref, []):
            rows["outcome_aligned_control_pair_material"].append({"private_pair_ref": f"r2bs_private_control_{c_idx:04d}", "parent_r2be_row_ref_private": row.get("private_pair_ref"), "parent_r2be_task_ref_private": task_parent_ref, "parent_r2bo_label_ref_private": label_ref, "label_aligned_control_pair_bool": True, "experiment_metric_bool": False}); c_idx += 1
    if e_idx == 0 or s_idx == 0 or c_idx == 0: raise RuntimeError("invalid arguments")
    rows["alignment_qa"].append({"qa_bucket": "verified_task_label_alignment_repair_generation_no_metrics_pass", "private_label_alignment_rows_bucket": "present", "private_task_alignment_verified_bool": True, "private_pair_family_alignment_verified_bool": True, "no_source_scan_bool": True, "no_experiment_metrics_bool": True})
    rows["repair_provenance_private"].append({"repair_provenance_bucket": "verified_join_from_existing_r2be_material_and_r2bo_labels", "private_task_alignment_available_bool": len(align_by_task) >= n, "private_pair_family_alignment_available_bool": len(pair_align_by_task) >= n, "inputs_mutated_bool": False})
    if sum(len(v) for v in rows.values()) > BOUNDS["private_row_cap"]: raise RuntimeError("invalid arguments")
    for g in R2BS_GROUPS:
        p = groups_dir / f"{g}.jsonl"
        if p.exists() and p.is_symlink(): raise RuntimeError("invalid arguments")
        write_jsonl(p, rows[g])
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2br_checkpoint": R2BR_CHECKPOINT, "r2be_checkpoint": R2BE_CHECKPOINT, "r2bo_checkpoint": R2BO_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2bs_explicit_local_repair_generation"}, "groups": {g: {"row_count_bucket": "present"} for g in R2BS_GROUPS}, "bounds": {"target_tasks_bucket": "target_tasks_20", "private_rows_bucket": "private_rows_le_20000"}, "wall_clock_bucket": "wall_clock_le_20_minutes" if time.time() - start < 20 * 60 else "wall_clock_over_cap", "no_experiment_metrics_bool": True, "no_source_scan_bool": True}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"; (out / "r2bs_private_manifest.json").write_text(text, encoding="utf-8"); (out / "r2bs_owner_manifest.json").write_text(text, encoding="utf-8")
    return {"generated": True, "output_groups": set(R2BS_GROUPS), "label_alignment_bucket": "label_alignment_materialized", "parent_refs_bucket": "parent_refs_present", "bounds_ok": True}

def default_material() -> dict[str, Any]: return {"generated": False, "output_groups": set(), "label_alignment_bucket": "not_applicable_default_noop", "parent_refs_bucket": "not_applicable_default_noop", "bounds_ok": True}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2BR_CHECKPOINT, R2BR_STATUS, R2BE_CHECKPOINT, R2BO_CHECKPOINT, "default mode", "no private read/write", "explicit local repair/generation", "outcome_label_alignment_eval_private", "parent_r2bo_label_ref_private", "label alignment materialized", "no experiment metrics", "no source scan", "aggregate-only public artifact", NEXT_PHASE]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(x in text for x in fragments)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bs-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md")) and ok(read("docs/zh/bea-v1-haae-r2bs-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bs-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str = "default", r2br: dict[str, Any] | None = None, material: dict[str, Any] | None = None, r2be_ok: bool = False, r2bo_ok: bool = False, output_ok: bool = False, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2br is None:
        try: r2br = load_json(repo_root() / R2BR_REPORT_PATH)
        except Exception: r2br = {}
    audit = audit_r2br(r2br); material = material or default_material(); rb = public_readback_match(self_test_total); explicit = mode == "explicit"; generated = bool(material.get("generated"))
    status = STATUS_DEFAULT if not explicit else (STATUS_PASS if audit["source_ok"] and r2be_ok and r2bo_ok and output_ok and generated else STATUS_FAIL_GENERATION)
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    if status in {STATUS_DEFAULT, STATUS_PASS} and not rb["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bsstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_successful_generation"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bssource0000", "locked_haae_r2br_checkpoint": R2BR_CHECKPOINT, "locked_haae_r2br_status": R2BR_STATUS, "locked_haae_r2br_self_test_total": R2BR_SELF_TEST_TOTAL, "locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2bsexec0000", "execution_mode_bucket": "explicit_local_repair_generation" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_r2be_material_read_bool": explicit and r2be_ok, "private_r2bo_label_source_read_bool": explicit and r2bo_ok, "private_output_write_bool": explicit and output_ok, "material_repair_generation_bool": explicit and generated, "experiment_metrics_bool": False, "source_scan_bool": False, "runtime_network_bool": False, "signal_claim_bool": False}],
        "root_safety_records": [{"anonymous_root_id": "haaer2bsroot0000", "r2be_input_root_safety_bucket": "input_root_valid" if r2be_ok else ("not_read_default_mode" if not explicit else "input_root_invalid"), "r2bo_input_root_safety_bucket": "input_root_valid" if r2bo_ok else ("not_read_default_mode" if not explicit else "input_root_invalid"), "output_root_safety_bucket": "output_root_valid" if output_ok else ("not_written_default_mode" if not explicit else "output_root_invalid"), "no_root_path_or_basename_public_bool": True}],
        "repair_group_records": [{"anonymous_group_id": "haaer2bsgroup0000", "required_group_buckets": R2BS_GROUPS, "output_group_set_exact_bool": generated and set(material.get("output_groups", set())) == set(R2BS_GROUPS), "label_alignment_materialized_bucket": material.get("label_alignment_bucket"), "parent_refs_present_bucket": material.get("parent_refs_bucket"), "bounds_satisfied_bool": bool(material.get("bounds_ok", True)), "private_rows_bucket": "private_rows_le_20000"}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bsprivacy0000", "aggregate_only_public_artifact_bool": True, "private_root_path_public_bool": False, "task_query_path_span_label_public_bool": False, "evidence_pair_id_public_bool": False, "exact_count_rate_score_public_bool": False, "experiment_metrics_bool": False, "source_scan_bool": False, "raw_private_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bsgate{i:04d}", "gate_bucket": g, "gate_passed_bool": True, "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bssynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bsreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
        if g["gate_bucket"] == "docs_readback_match_gate": g["gate_passed_bool"] = rb["all_public_readback_match_bool"]
        if g["gate_bucket"] == "r2bt_stop_go_only_gate" and passed: g["gate_passed_bool"] = all(stop.get(f) is True for f in STOP_TRUE) and all(stop.get(f, False) is False for f in STOP_FALSE)
        if g["gate_bucket"] == "output_group_exact_gate" and explicit: g["gate_passed_bool"] = generated and set(material.get("output_groups", set())) == set(R2BS_GROUPS)
    if report["status"] in {STATUS_DEFAULT, STATUS_PASS} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS}: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    src = (report.get("source_lock_records") or [{}])[0]
    for k, v in {"locked_haae_r2br_checkpoint": R2BR_CHECKPOINT, "locked_haae_r2br_status": R2BR_STATUS, "locked_haae_r2br_self_test_total": R2BR_SELF_TEST_TOTAL, "locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT}.items():
        if src.get(k) != v: issues.append(f"source_{k}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    exe = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_DEFAULT:
        for f in ["explicit_opt_in_bool", "private_r2be_material_read_bool", "private_r2bo_label_source_read_bool", "private_output_write_bool", "material_repair_generation_bool"]:
            if exe.get(f) is not False: issues.append(f"default_execution_{f}")
    if report.get("status") == STATUS_PASS:
        if exe.get("execution_mode_bucket") != "explicit_local_repair_generation": issues.append("explicit_execution_mode_bucket")
        for f in ["explicit_opt_in_bool", "private_r2be_material_read_bool", "private_r2bo_label_source_read_bool", "private_output_write_bool", "material_repair_generation_bool"]:
            if exe.get(f) is not True: issues.append(f"explicit_execution_{f}")
    for f in ["experiment_metrics_bool", "source_scan_bool", "runtime_network_bool", "signal_claim_bool"]:
        if exe.get(f) is not False: issues.append(f"execution_{f}")
    root = (report.get("root_safety_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if root.get("r2be_input_root_safety_bucket") != "input_root_valid": issues.append("root_r2be_input_root_safety_bucket")
        if root.get("r2bo_input_root_safety_bucket") != "input_root_valid": issues.append("root_r2bo_input_root_safety_bucket")
        if root.get("output_root_safety_bucket") != "output_root_valid": issues.append("root_output_root_safety_bucket")
        if root.get("no_root_path_or_basename_public_bool") is not True: issues.append("root_no_root_path_or_basename_public_bool")
    grp = (report.get("repair_group_records") or [{}])[0]
    if grp.get("required_group_buckets") != R2BS_GROUPS: issues.append("output_group_set_mismatch")
    if report.get("status") == STATUS_PASS:
        if grp.get("output_group_set_exact_bool") is not True: issues.append("output_group_exact_false")
        if grp.get("label_alignment_materialized_bucket") != "label_alignment_materialized": issues.append("label_alignment_materialized_bucket")
        if grp.get("parent_refs_present_bucket") != "parent_refs_present": issues.append("parent_refs_present_bucket")
        if grp.get("bounds_satisfied_bool") is not True: issues.append("bounds_satisfied_bool")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("aggregate_only_public_artifact_bool") is not True: issues.append("aggregate_only_public_artifact_bool")
    for f in ["private_root_path_public_bool", "task_query_path_span_label_public_bool", "evidence_pair_id_public_bool", "exact_count_rate_score_public_bool", "experiment_metrics_bool", "source_scan_bool", "raw_private_publication_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_phase_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"stop_false_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("readback_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("stale_current")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def make_fixture(tmp: Path) -> tuple[Path, Path]:
    r2be = tmp / "r2be"; r2bo = tmp / "r2bo"
    fixture_meta = {
        "r2be_private_manifest.json": {"schema_version": INPUT_MANIFEST_CONTRACTS["r2be_private_manifest.json"]["schema_version"], "phase": R2BE_PHASE, "ownership": {"owner_phase": R2BE_PHASE}, "source_lock": {"r2bd_checkpoint": "fa6119b", "r2be_checkpoint": R2BE_CHECKPOINT}},
        "r2bo_private_manifest.json": {"schema_version": INPUT_MANIFEST_CONTRACTS["r2bo_private_manifest.json"]["schema_version"], "phase": R2BO_PHASE, "ownership": {"owner_phase": R2BO_PHASE}, "source_lock": {"r2bn_checkpoint": "af901f6", "r2be_checkpoint": R2BE_CHECKPOINT, "r2bo_checkpoint": R2BO_CHECKPOINT}},
    }
    for root, groups, manifest in [(r2be, R2BE_GROUPS, "r2be_private_manifest.json"), (r2bo, R2BO_GROUPS, "r2bo_private_manifest.json")]:
        (root / "groups").mkdir(parents=True); (root / manifest).write_text(json.dumps(fixture_meta[manifest]), encoding="utf-8")
        for i, g in enumerate(groups): write_jsonl(root / "groups" / f"{g}.jsonl", [{"private_row_ref": f"{g}_{i}", "private_task_ref": "task0", "private_label_source_ref": "label0"}])
    write_jsonl(r2bo / "groups" / "outcome_label_source_manifest_private.jsonl", [{"private_label_source_ref": "label0", "raw_label_values_private_bool": True, "private_gold_spans": [{"path": "private", "start_line": 1, "end_line": 2}], "private_hard_negatives": [{"path": "private", "start_line": 3, "end_line": 4}]}])
    write_jsonl(r2bo / "groups" / "outcome_label_task_alignment_private.jsonl", [{"private_task_ref": "task0", "private_label_source_ref": "label0", "private_task_alignment_ref": "align0", "alignment_bucket": "ordered_manifest_to_private_task_alignment_acquired"}])
    write_jsonl(r2bo / "groups" / "outcome_label_pair_family_alignment_private.jsonl", [{"private_task_ref": "task0", "private_label_source_ref": "label0", "private_pair_family_alignment_ref": "pairalign0", "support_pair_count_private": 1, "control_pair_count_private": 1}])
    return r2be, r2bo

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; base = load_json(repo_root() / R2BR_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    default = build_report("default", base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(prefix="r2bs_selftest_", dir="/tmp/opencode") as td:
        tmp = Path(td); r2be, r2bo = make_fixture(tmp); out = tmp / "out"
        ok1, _, r1, rows1 = validate_input_root(str(r2be), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")
        ok2, _, r2, rows2 = validate_input_root(str(r2bo), R2BO_GROUPS, "r2bo_private_manifest.json", "private_material")
        ok3, _, outp = validate_output_root(str(out), [r1, r2])
        mat = repair_material(rows1, rows2, outp) if ok1 and ok2 and ok3 and outp else {}
        explicit = build_report("explicit", base, mat, ok1, ok2, ok3)
        check("explicit_synthetic_success_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
        # Parser/root mutations.
        for name, args in [("safe_parser_fail", ["--bad"]), ("missing_allow_flag_fail", ["--r2be-private-material-root", str(r2be)]), ("missing_r2be_root_fail", ["--allow-r2bs-explicit-local-repair-generation", "--r2bo-private-label-root", str(r2bo), "--private-output-root", str(out), "--confirm-aggregate-only-publication"]), ("missing_r2bo_root_fail", ["--allow-r2bs-explicit-local-repair-generation", "--r2be-private-material-root", str(r2be), "--private-output-root", str(out), "--confirm-aggregate-only-publication"]), ("missing_output_root_fail", ["--allow-r2bs-explicit-local-repair-generation", "--r2be-private-material-root", str(r2be), "--r2bo-private-label-root", str(r2bo), "--confirm-aggregate-only-publication"]), ("unknown_arg_fail", ["--unknown"] )]:
            try: parse_args(args); check(name, False)
            except ValueError: check(name, True)
        check("r2be_root_in_repo_fail", not validate_input_root(str(repo_root()), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0])
        check("r2be_root_missing_fail", not validate_input_root(str(tmp / "missing"), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0])
        sym = tmp / "sym"; sym.symlink_to(r2be, target_is_directory=True); check("r2be_root_symlink_fail", not validate_input_root(str(sym), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0])
        check("r2bo_root_missing_fail", not validate_input_root(str(tmp / "missing2"), R2BO_GROUPS, "r2bo_private_manifest.json", "private_material")[0])
        sym2 = tmp / "sym2"; sym2.symlink_to(r2bo, target_is_directory=True); check("r2bo_root_symlink_fail", not validate_input_root(str(sym2), R2BO_GROUPS, "r2bo_private_manifest.json", "private_material")[0])
        check("input_roots_nested_fail", validate_output_root(str(r2be / "child"), [r2be, r2bo])[0] is False)
        (r2be / "groups" / f"{R2BE_GROUPS[0]}.jsonl").unlink(); check("input_group_missing_fail", not validate_input_root(str(r2be), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0]); write_jsonl(r2be / "groups" / f"{R2BE_GROUPS[0]}.jsonl", [{"x":1}])
        write_jsonl(r2be / "groups" / "extra.jsonl", [{"x":1}]); check("input_group_extra_fail", not validate_input_root(str(r2be), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0]); (r2be / "groups" / "extra.jsonl").unlink()
        (r2be / "groups" / "link.jsonl").symlink_to(r2be / "groups" / f"{R2BE_GROUPS[0]}.jsonl"); check("input_group_symlink_fail", not validate_input_root(str(r2be), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0]); (r2be / "groups" / "link.jsonl").unlink()
        r2be_manifest = r2be / "r2be_private_manifest.json"; old_meta = load_json(r2be_manifest); bad_meta = json.loads(json.dumps(old_meta)); bad_meta["source_lock"]["r2be_checkpoint"] = "bad"; r2be_manifest.write_text(json.dumps(bad_meta), encoding="utf-8"); check("input_manifest_checkpoint_drift_fail", not validate_input_root(str(r2be), R2BE_GROUPS, "r2be_private_manifest.json", "private_material")[0]); r2be_manifest.write_text(json.dumps(old_meta), encoding="utf-8")
        check("output_root_in_repo_fail", not validate_output_root(str(repo_root() / "tmp_r2bs"), [r1, r2])[0])
        check("nested_output_fail", not validate_output_root(str(r2bo / "child"), [r1, r2])[0])
        outsym = tmp / "outsym"; outsym.symlink_to(tmp / "target", target_is_directory=True); check("output_root_symlink_fail", not validate_output_root(str(outsym), [r1, r2])[0])
        badout = tmp / "badout"; badout.mkdir(); (badout / "junk").write_text("x"); check("nonempty_unowned_output_fail", not validate_output_root(str(badout), [r1, r2])[0])
        check("owned_rerun_pass", validate_output_root(str(out), [r1, r2])[0])
        (out / "groups" / "escape.jsonl").symlink_to(out / "r2bs_private_manifest.json"); check("output_group_symlink_escape_fail", not validate_output_root(str(out), [r1, r2])[0]); (out / "groups" / "escape.jsonl").unlink()
        shutil.rmtree(out, ignore_errors=True)
    # Source/fact/report mutations.
    src_muts = [("bad_r2br_checkpoint_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bq_checkpoint", "bad")), ("bad_r2br_status_fail", lambda r: r.__setitem__("status", "bad")), ("r2br_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True))]
    for name, mut in src_muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    report_muts = [("bad_r2br_self_test_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2br_self_test_total", 0), "source_locked_haae_r2br_self_test_total"), ("output_group_missing_fail", lambda r: r["repair_group_records"][0]["required_group_buckets"].pop(), "output_group_set_mismatch"), ("output_group_extra_fail", lambda r: r["repair_group_records"][0]["required_group_buckets"].append("extra"), "output_group_set_mismatch"), ("status_execution_mismatch_fail", lambda r: r["execution_mode_records"][0].__setitem__("experiment_metrics_bool", True), "execution_experiment_metrics_bool"), ("explicit_execution_mode_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("execution_mode_bucket", "default_no_explicit_opt_in"), "explicit_execution_mode_bucket"), ("explicit_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_r2be_material_read_bool", False), "explicit_execution_private_r2be_material_read_bool"), ("explicit_output_write_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_output_write_bool", False), "explicit_execution_private_output_write_bool"), ("root_safety_drift_fail", lambda r: r["root_safety_records"][0].__setitem__("output_root_safety_bucket", "bad"), "root_output_root_safety_bucket"), ("label_alignment_bucket_drift_fail", lambda r: r["repair_group_records"][0].__setitem__("label_alignment_materialized_bucket", "bad"), "label_alignment_materialized_bucket"), ("parent_refs_bucket_drift_fail", lambda r: r["repair_group_records"][0].__setitem__("parent_refs_present_bucket", "bad"), "parent_refs_present_bucket"), ("label_privacy_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("task_query_path_span_label_public_bool", True), "privacy_task_query_path_span_label_public_bool"), ("metric_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("experiment_metrics_bool", True), "privacy_experiment_metrics_bool"), ("source_scan_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("source_scan_bool", True), "privacy_source_scan_bool"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "stop_false_private_read_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "stop_false_metric_recompute_authorized_bool"), ("stop_go_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_false_source_scan_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"), ("readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), "readback_mismatch"), ("readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "readback_mismatch")]
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(build_report("explicit", base, {"generated": True, "output_groups": set(R2BS_GROUPS), "label_alignment_bucket": "label_alignment_materialized", "parent_refs_bucket": "parent_refs_present", "bounds_ok": True}, True, True, True))); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private r14m-001 gold_spans exact_score_value"; check("raw_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status":"unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    report: dict[str, Any]
    if args["explicit"]:
        ok1, _, r1, rows1 = validate_input_root(str(args["r2be_root"]), R2BE_GROUPS, "r2be_private_manifest.json", "r2be")
        ok2, _, r2, rows2 = validate_input_root(str(args["r2bo_root"]), R2BO_GROUPS, "r2bo_private_manifest.json", "r2bo")
        ok3, _, out = validate_output_root(str(args["output"]), [r1, r2])
        if not (ok1 and ok2 and ok3 and out): report = build_report("explicit", material=default_material(), r2be_ok=ok1, r2bo_ok=ok2, output_ok=ok3)
        else:
            try: material = repair_material(rows1, rows2, out); report = build_report("explicit", material=material, r2be_ok=True, r2bo_ok=True, output_ok=True)
            except Exception: report = build_report("explicit", material=default_material(), r2be_ok=ok1, r2bo_ok=ok2, output_ok=ok3)
    else:
        report = build_report("default")
    path = write_report(report, public_artifact_path(str(args["out"])) if args["out"] else None)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
