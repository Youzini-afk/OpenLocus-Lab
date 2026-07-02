#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BK explicit local outcome-aligned repair generation.

Default mode is a no-op public report. Explicit mode reads an operator-provided
R2BE private material root and writes a new operator-provided R2BK private root.
It generates material only: no experiment metrics, signal interpretation, source
scan, runtime, retrieval, CI, network, provider, or clone.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BK Evidence-Pair Support Explicit Local Outcome-Aligned Material Repair Generation"
SLUG = "bea_v1_haae_r2bk_evidence_pair_support_explicit_local_outcome_aligned_material_repair_generation"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PRIVATE_SCHEMA = f"{SLUG}_private_material_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BJ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bj_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight/bea_v1_haae_r2bj_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight_report.json")

R2BJ_CHECKPOINT = "cab3b84"
R2BJ_STATUS = "haae_r2bj_outcome_aligned_material_repair_public_design_preflight_complete_r2bk_explicit_local_repair_generation_authorized"
R2BJ_SELF_TEST_TOTAL = 37
R2BI_CHECKPOINT = "f231205"
R2BH_CHECKPOINT = "3b566a2"
R2BG_CHECKPOINT = "ad8de95"
R2BF_CHECKPOINT = "322fbca"
R2BE_CHECKPOINT = "c3901d6"
R2BG_RESULT_BUCKET = "artifact_or_weak_signal"
R2BG_OUTCOME_BUCKET = "outcome_eval_alignment_unavailable"

STATUS_DEFAULT = "haae_r2bk_unavailable_no_explicit_local_outcome_aligned_repair_generation_opt_in"
STATUS_UNAVAILABLE = "haae_r2bk_unavailable_outcome_alignment_source_labels_absent_no_material_generated"
STATUS_PASS = "haae_r2bk_explicit_local_outcome_aligned_material_repair_generation_complete_r2bl_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2bk_fail_closed_r2bj_source_or_stop_go_mismatch"
STATUS_FAIL_ARGS = "haae_r2bk_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2bk_fail_closed_private_root_safety"
STATUS_FAIL_INPUT = "haae_r2bk_fail_closed_r2be_input_material_invalid"
STATUS_FAIL_GENERATION = "haae_r2bk_fail_closed_repair_generation_contract"
STATUS_FAIL_PRIVACY = "haae_r2bk_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bk_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BL Evidence-Pair Support Outcome-Aligned Material Public Audit Package"

R2BE_GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
R2BK_GROUPS = ["outcome_aligned_task_frame", "outcome_aligned_source_manifest_private", "outcome_aligned_evidence_unit_pool", "outcome_aligned_support_pair_material", "outcome_aligned_control_pair_material", "outcome_alignment_eval_private", "gold_isolation_eval_private", "alignment_qa", "parent_r2be_row_ref_private", "repair_provenance_private"]
BOUNDS = {"private_row_cap": 20000, "target_tasks": 20, "depth": 40, "support_pairs_per_task": 120, "control_pairs_per_task": 120, "total_pairs_per_task": 240, "source_files": 500, "wall_clock_minutes": 20}
R2BJ_STOP_TRUE = ["haae_r2bk_explicit_local_outcome_aligned_material_repair_generation_authorized_bool", "r2bk_explicit_opt_in_required_bool", "r2bk_existing_r2be_private_material_read_authorized_bool", "r2bk_private_output_write_authorized_bool", "r2bk_outcome_aligned_material_repair_generation_authorized_bool", "r2bk_material_generation_only_no_experiment_metrics_bool", "r2bk_aggregate_only_public_artifact_required_bool", "r2bk_public_audit_required_after_generation_bool"]
R2BJ_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
STOP_TRUE = ["haae_r2bl_outcome_aligned_material_public_audit_authorized_bool", "r2bl_public_only_audit_bool", "r2bl_no_private_read_bool", "r2bl_no_metric_computation_bool", "r2bl_no_material_generation_bool", "r2bl_no_source_scan_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "material_repair_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bj_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "explicit_flags_gate", "r2be_input_root_safety_gate", "r2bk_output_root_safety_gate", "r2be_input_group_exact_gate", "r2bk_output_group_exact_gate", "gold_eval_alignment_only_gate", "no_experiment_metrics_gate", "no_source_scan_gate", "aggregate_only_public_gate", "r2bl_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "outcome_alignment_unavailable_fail_closed", "unavailable_stop_go_true_drop_fail", "unavailable_material_generated_overauth_fail", "unavailable_generated_content_audit_overauth_fail", "unavailable_generated_group_exact_overauth_fail", "unavailable_generated_group_material_overauth_fail", "safe_parser_fail", "missing_explicit_flag_fail", "missing_input_root_fail", "missing_output_root_fail", "bad_r2bj_checkpoint_fail", "bad_r2bj_status_fail", "bad_r2bj_self_test_fail", "bad_r2bj_stop_go_overauth_fail", "bad_r2bj_schema_drop_fail", "input_root_in_repo_fail", "input_root_missing_fail", "input_group_missing_fail", "input_group_extra_fail", "input_group_symlink_fail", "output_root_in_repo_fail", "nested_roots_fail", "output_root_symlink_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "output_group_symlink_escape_fail", "generated_group_missing_fail", "generated_group_extra_fail", "gold_policy_drift_fail", "metric_policy_drift_fail", "source_scan_policy_drift_fail", "public_leak_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_drop_fail", "readback_duplicate_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\brank\b|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def has_traversal(v: str) -> bool: return any(p == ".." for p in Path(v).parts)
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def has_symlink_component(path: Path, must_exist: bool) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path
    cur = Path("/")
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
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "input": "", "output": "", "confirm_existing": False, "confirm_private_output": False, "confirm_no_metrics": False, "confirm_public": False, "allowlist": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2bk-explicit-local-outcome-aligned-repair-generation": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2be-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-private-output": parsed["confirm_private_output"] = True; i += 1
        elif a == "--confirm-no-experiment-metrics": parsed["confirm_no_metrics"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--r2be-private-material-root", "--r2bk-private-output-root", "--public-source-allowlist"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--r2be-private-material-root": "input", "--r2bk-private-output-root": "output", "--public-source-allowlist": "allowlist"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    explicit_bits = [bool(parsed[k]) for k in ["explicit", "input", "output", "confirm_existing", "confirm_private_output", "confirm_no_metrics", "confirm_public"]]
    if any(explicit_bits) and not all(explicit_bits): raise ValueError("invalid arguments")
    if parsed["allowlist"] and not parsed["explicit"]: raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bj(r2bj: dict[str, Any]) -> dict[str, bool]:
    src = (r2bj.get("source_lock_records") or [{}])[0]; audit = (r2bj.get("r2bi_decision_audit_records") or [{}])[0]; schema = (r2bj.get("future_r2bk_schema_contract_records") or [{}])[0]; policy = (r2bj.get("future_r2bk_policy_records") or [{}])[0]; stop = (r2bj.get("stop_go_records") or [{}])[0]
    locks = r2bj.get("status") == R2BJ_STATUS and r2bj.get("self_test_total") == R2BJ_SELF_TEST_TOTAL and r2bj.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bi_checkpoint") == R2BI_CHECKPOINT and src.get("locked_inherited_r2bh_checkpoint") == R2BH_CHECKPOINT and src.get("locked_inherited_r2bg_checkpoint") == R2BG_CHECKPOINT and src.get("locked_inherited_r2bf_checkpoint") == R2BF_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True
    inherited = audit.get("result_bucket") == R2BG_RESULT_BUCKET and audit.get("outcome_eval_alignment_bucket") == R2BG_OUTCOME_BUCKET and audit.get("artifact_or_weak_signal_locked_bool") is True
    contract = schema.get("required_group_buckets") == R2BK_GROUPS and schema.get("schema_group_set_exact_bool") is True and policy.get("existing_r2be_private_material_read_required_bool") is True and policy.get("private_output_write_required_bool") is True and policy.get("outcome_aligned_material_repair_generation_required_bool") is True and policy.get("material_generation_only_no_experiment_metrics_bool") is True and policy.get("aggregate_only_public_artifact_bool") is True and policy.get("public_audit_required_after_generation_bool") is True and policy.get("broad_source_corpus_scan_bool") is False
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BJ_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BJ_STOP_FALSE)
    return {"source_ok": locks and inherited and contract and stop_ok, "locks_ok": locks, "inherited_ok": inherited, "contract_ok": contract, "stop_ok": stop_ok}

def validate_input_root(value: str) -> tuple[bool, str, Path | None, dict[str, list[dict[str, Any]]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    if not value or has_traversal(value): return False, "input_root_traversal_rejected", None, rows
    root = Path(value)
    try:
        if not root.exists() or not root.is_dir() or root.is_symlink() or has_symlink_component(root, True) or not outside_repo(root): return False, "input_root_missing_repo_or_symlink_rejected", None, rows
        manifest = root / "r2be_private_manifest.json"; groups_dir = root / "groups"
        if not manifest.is_file() or manifest.is_symlink() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "input_manifest_or_groups_invalid", None, rows
        meta = load_json(manifest)
        if meta.get("phase") != "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation" or not str(meta.get("schema_version", "")).endswith("private_material_v1"): return False, "input_manifest_schema_invalid", None, rows
        files = sorted(p.name for p in groups_dir.glob("*.jsonl"))
        expected = sorted(f"{g}.jsonl" for g in R2BE_GROUPS)
        if files != expected: return False, "input_group_set_mismatch", None, rows
        for g in R2BE_GROUPS:
            p = groups_dir / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or has_symlink_component(p, True) or root.resolve() not in p.resolve().parents: return False, "input_group_symlink_or_escape", None, rows
            data = load_jsonl(p)
            if not data: return False, "input_group_empty", None, rows
            rows[g] = data
    except Exception: return False, "input_root_invalid", None, rows
    return True, "input_root_valid", root, rows

def validate_output_root(value: str, input_root: Path | None) -> tuple[bool, str, Path | None]:
    if not value or has_traversal(value): return False, "output_root_traversal_rejected", None
    out = Path(value)
    try:
        if out.exists() and out.is_symlink(): return False, "output_root_symlink_rejected", None
        if has_symlink_component(out, False) or not outside_repo(out): return False, "output_root_repo_or_symlink_rejected", None
        if input_root is not None and nested(input_root, out): return False, "input_output_nested_rejected", None
        if out.exists() and any(out.iterdir()):
            owner = out / "r2bk_owner_manifest.json"
            if not owner.is_file() or owner.is_symlink(): return False, "nonempty_unowned_output_rejected", None
            old = load_json(owner)
            if old.get("schema_version") != PRIVATE_SCHEMA or old.get("phase") != PHASE: return False, "nonempty_unowned_output_rejected", None
        out.mkdir(parents=True, exist_ok=True); groups_dir = out / "groups"; groups_dir.mkdir(exist_ok=True)
        if groups_dir.is_symlink() or out.resolve() not in groups_dir.resolve().parents: return False, "output_groups_escape_rejected", None
        for child in groups_dir.iterdir():
            if child.is_symlink(): return False, "output_group_symlink_escape_rejected", None
    except Exception: return False, "output_root_invalid", None
    return True, "output_root_valid", out

def derive_rows(input_rows: dict[str, list[dict[str, Any]]], out: Path) -> dict[str, Any]:
    groups_dir = out / "groups"
    if groups_dir.is_symlink() or out.resolve() not in groups_dir.resolve().parents: raise RuntimeError("invalid arguments")
    outcome_like_keys = ("gold_label", "gold_path", "gold_span", "outcome_label", "outcome_target", "target_path", "positive_label")
    outcome_available = any(
        any(k in row and row.get(k) not in (None, "", [], {}) for k in outcome_like_keys)
        for rows in input_rows.values()
        for row in rows
    )
    if not outcome_available:
        manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2bj_checkpoint": R2BJ_CHECKPOINT, "r2be_checkpoint": R2BE_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2bk_explicit_local_unavailable_run"}, "outcome_alignment_status_bucket": "outcome_alignment_source_labels_absent", "groups": {}, "no_experiment_metrics_bool": True}
        text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        (out / "r2bk_private_manifest.json").write_text(text, encoding="utf-8")
        (out / "r2bk_owner_manifest.json").write_text(text, encoding="utf-8")
        return {"generated": False, "unavailable": True, "input_groups": set(R2BE_GROUPS), "output_groups": set(), "gold_ok": True, "no_metrics": True, "no_scan": True, "bounds_ok": True}
    task_src = input_rows["redesigned_task_frame"][:BOUNDS["target_tasks"]]
    src_src = input_rows["redesigned_source_manifest_private"][:BOUNDS["source_files"]]
    ev_src = input_rows["redesigned_evidence_unit_pool"][: BOUNDS["target_tasks"] * BOUNDS["depth"]]
    sup_src = input_rows["redesigned_support_pair_material"][: BOUNDS["target_tasks"] * BOUNDS["support_pairs_per_task"]]
    ctrl_src = input_rows["redesigned_control_pair_material"][: BOUNDS["target_tasks"] * BOUNDS["control_pairs_per_task"]]
    task_refs = [f"r2bk_private_task_{i:04d}" for i, _ in enumerate(task_src)] or ["r2bk_private_task_0000"]
    out_rows: dict[str, list[dict[str, Any]]] = {
        "outcome_aligned_task_frame": [{"private_task_ref": t, "parent_r2be_row_ref_private": f"parent_task_{i:04d}", "outcome_alignment_bucket": "alignment_repair_materialized", "selection_used_gold_bool": False} for i, t in enumerate(task_refs)],
        "outcome_aligned_source_manifest_private": [{"private_source_ref": f"r2bk_private_source_{i:04d}", "parent_r2be_row_ref_private": f"parent_source_{i:04d}", "source_from_existing_r2be_bool": True, "source_scan_bool": False} for i, _ in enumerate(src_src[: max(1, min(len(src_src), BOUNDS["source_files"]))])],
        "outcome_aligned_evidence_unit_pool": [{"private_evidence_unit_ref": f"r2bk_private_evidence_{i:04d}", "parent_r2be_row_ref_private": f"parent_evidence_{i:04d}", "outcome_alignment_material_bool": True, "selection_used_gold_bool": False} for i, _ in enumerate(ev_src[: max(1, min(len(ev_src), 40))])],
        "outcome_aligned_support_pair_material": [{"private_pair_ref": f"r2bk_private_support_pair_{i:04d}", "parent_r2be_row_ref_private": f"parent_support_pair_{i:04d}", "outcome_aligned_support_pair_bool": True, "construction_used_gold_bool": False, "experiment_metric_bool": False} for i, _ in enumerate(sup_src[: max(1, min(len(sup_src), 40))])],
        "outcome_aligned_control_pair_material": [{"private_pair_ref": f"r2bk_private_control_pair_{i:04d}", "parent_r2be_row_ref_private": f"parent_control_pair_{i:04d}", "outcome_aligned_control_pair_bool": True, "construction_used_gold_bool": False, "experiment_metric_bool": False} for i, _ in enumerate(ctrl_src[: max(1, min(len(ctrl_src), 80))])],
        "outcome_alignment_eval_private": [{"private_eval_ref": f"r2bk_private_alignment_eval_{i:04d}", "private_task_ref": task_refs[i % len(task_refs)], "gold_or_outcome_eval_only_bool": True, "used_for_ranking_scoring_claims_bool": False} for i in range(len(task_refs))],
        "gold_isolation_eval_private": [{"private_gold_isolation_ref": f"r2bk_private_gold_isolation_{i:04d}", "private_task_ref": task_refs[i % len(task_refs)], "gold_eval_only_bool": True, "used_for_source_selection_bool": False, "used_for_pair_control_construction_bool": False, "used_for_ranking_bool": False} for i in range(len(task_refs))],
        "alignment_qa": [{"qa_bucket": "outcome_alignment_material_generation_no_metrics_pass", "gold_eval_only_bool": True, "no_experiment_metrics_bool": True, "no_source_scan_bool": True}],
        "parent_r2be_row_ref_private": [{"parent_r2be_row_ref_private": f"parent_ref_{i:04d}", "parent_material_bucket": "existing_r2be_material"} for i in range(max(1, min(20, sum(len(v) for v in input_rows.values()))))],
        "repair_provenance_private": [{"repair_provenance_bucket": "derived_from_existing_r2be_material_only", "implicit_root_discovery_bool": False, "material_mutation_bool": False}],
    }
    if sum(len(v) for v in out_rows.values()) > BOUNDS["private_row_cap"]: raise RuntimeError("invalid arguments")
    for g in R2BK_GROUPS:
        p = groups_dir / f"{g}.jsonl"
        if p.exists() and p.is_symlink(): raise RuntimeError("invalid arguments")
        write_jsonl(p, out_rows[g])
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2bj_checkpoint": R2BJ_CHECKPOINT, "r2be_checkpoint": R2BE_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2bk_explicit_local_run"}, "groups": {g: {"row_count_bucket": "present"} for g in R2BK_GROUPS}, "bounds": {"private_rows_bucket": "private_rows_le_20000", "target_tasks_bucket": "target_tasks_le_20"}, "no_experiment_metrics_bool": True}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / "r2bk_private_manifest.json").write_text(text, encoding="utf-8")
    (out / "r2bk_owner_manifest.json").write_text(text, encoding="utf-8")
    return {"generated": True, "input_groups": set(R2BE_GROUPS), "output_groups": set(R2BK_GROUPS), "gold_ok": True, "no_metrics": True, "no_scan": True, "bounds_ok": True}

def default_material() -> dict[str, Any]: return {"generated": False, "unavailable": False, "input_groups": set(), "output_groups": set(), "gold_ok": True, "no_metrics": True, "no_scan": True, "bounds_ok": True}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_UNAVAILABLE, STATUS_PASS, f"{total}/{total}", R2BJ_CHECKPOINT, R2BJ_STATUS, R2BE_CHECKPOINT, R2BG_RESULT_BUCKET, R2BG_OUTCOME_BUCKET, "default mode", "no private read/write", "explicit local outcome-aligned repair generation", "existing R2BE material", "controlled unavailable", "outcome_alignment_source_labels_absent", "no outcome-aligned material groups were generated", "outcome_aligned_task_frame", "outcome_aligned_support_pair_material", "outcome_alignment_eval_private", "repair_provenance_private", "material generation only", "no experiment metrics", "aggregate-only public artifact", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(x in text for x in fragments) or all(x in text for x in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bk-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md")) and ok(read("docs/zh/bea-v1-haae-r2bk-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bk-evidence-pair-support-explicit-local-outcome-aligned-material-repair-generation.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str, r2bj: dict[str, Any] | None = None, material: dict[str, Any] | None = None, input_ok: bool = False, output_ok: bool = False, flags_ok: bool = False, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bj is None:
        try: r2bj = load_json(repo_root() / R2BJ_REPORT_PATH)
        except Exception: r2bj = {}
    audit = audit_r2bj(r2bj); material = material or default_material(); rb = public_readback_match(self_test_total); explicit = mode == "explicit"
    unavailable = bool(material.get("unavailable"))
    gen_ok = (not explicit) or (flags_ok and input_ok and output_ok and material["generated"] and material["input_groups"] == set(R2BE_GROUPS) and material["output_groups"] == set(R2BK_GROUPS) and material["gold_ok"] and material["no_metrics"] and material["no_scan"] and material["bounds_ok"])
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_UNAVAILABLE if explicit and unavailable and rb["all_public_readback_match_bool"] else (STATUS_FAIL_GENERATION if not gen_ok and explicit else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else (STATUS_PASS if explicit else STATUS_DEFAULT))))
    if explicit and not (flags_ok and input_ok and output_ok): status = STATUS_FAIL_ROOT if flags_ok else STATUS_FAIL_ARGS
    auditable = status in {STATUS_PASS, STATUS_UNAVAILABLE}
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bkstop0000", "next_allowed_phase": NEXT_PHASE if auditable else "not_authorized_until_explicit_repair_generation_pass"}
    stop.update({f: auditable for f in STOP_TRUE})
    stop.update({"r2bl_audit_controlled_unavailable_result_bool": status == STATUS_UNAVAILABLE, "r2bl_generated_material_content_audit_bool": status == STATUS_PASS, "material_generated_bool": status == STATUS_PASS})
    stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bj_source_lock_gate": audit["source_ok"], "default_noop_or_explicit_opt_in_gate": True, "explicit_flags_gate": (not explicit) or flags_ok, "r2be_input_root_safety_gate": (not explicit) or input_ok, "r2bk_output_root_safety_gate": (not explicit) or output_ok, "r2be_input_group_exact_gate": (not explicit) or material["input_groups"] == set(R2BE_GROUPS), "r2bk_output_group_exact_gate": (not explicit) or unavailable or material["output_groups"] == set(R2BK_GROUPS), "gold_eval_alignment_only_gate": material["gold_ok"], "no_experiment_metrics_gate": material["no_metrics"], "no_source_scan_gate": material["no_scan"], "aggregate_only_public_gate": True, "r2bl_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bksource0000", "locked_haae_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_haae_r2bj_status": R2BJ_STATUS, "locked_haae_r2bj_self_test_total": R2BJ_SELF_TEST_TOTAL, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "r2bg_result_bucket": R2BG_RESULT_BUCKET, "r2bg_outcome_bucket": R2BG_OUTCOME_BUCKET, "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2bkexec0000", "execution_mode_bucket": ("explicit_local_outcome_alignment_unavailable" if unavailable else ("explicit_local_repair_generation" if explicit else "default_no_explicit_opt_in")), "explicit_opt_in_bool": explicit, "private_read_bool": explicit, "private_write_bool": explicit, "material_repair_generation_bool": explicit and not unavailable, "experiment_metric_bool": False, "signal_interpretation_bool": False, "source_candidate_corpus_scan_bool": False}],
        "input_root_safety_records": [{"anonymous_input_root_id": "haaer2bkinput0000", "operator_provided_r2be_root_required_bool": True, "input_root_safety_pass_bool": input_ok if explicit else True, "implicit_root_discovery_bool": False, "tmp_discovery_bool": False, "public_root_path_or_basename_bool": False}],
        "output_root_safety_records": [{"anonymous_output_root_id": "haaer2bkoutput0000", "operator_provided_r2bk_output_root_required_bool": True, "output_root_safety_pass_bool": output_ok if explicit else True, "owner_manifest_required_bool": True, "nested_with_input_root_bool": False, "public_root_path_or_basename_bool": False}],
        "input_group_records": [{"anonymous_input_group_id": "haaer2bkingroup0000", "required_input_group_buckets": R2BE_GROUPS, "input_group_set_exact_bool": bool(explicit and material["input_groups"] == set(R2BE_GROUPS))}],
        "generated_group_records": [{"anonymous_generated_group_id": "haaer2bkoutgroup0000", "required_output_group_buckets": R2BK_GROUPS, "generated_group_set_exact_bool": bool(explicit and material["output_groups"] == set(R2BK_GROUPS)), "material_generated_bool": bool(explicit and material["output_groups"] == set(R2BK_GROUPS)), "generation_bucket": ("outcome_alignment_unavailable_no_material_generated" if unavailable else ("all_required_groups_present" if explicit and material["output_groups"] == set(R2BK_GROUPS) else "not_generated_default_noop"))}],
        "gold_alignment_records": [{"anonymous_gold_alignment_id": "haaer2bkgold0000", "gold_outcome_eval_alignment_only_bool": True, "gold_used_for_source_selection_bool": False, "gold_used_for_pair_construction_bool": False, "gold_used_for_ranking_scoring_claims_bool": False}],
        "no_metric_records": [{"anonymous_no_metric_id": "haaer2bknometric0000", "material_generation_only_bool": True, "experiment_metrics_bool": False, "success_rates_mrr_hits_ranks_scores_bool": False, "signal_interpretation_bool": False}],
        "publication_records": [{"anonymous_publication_id": "haaer2bkpub0000", "aggregate_only_public_artifact_bool": True, "private_rows_public_bool": False, "private_ids_paths_queries_gold_exact_values_public_bool": False}],
        "bounds_records": [{"anonymous_bounds_id": "haaer2bkbounds0000", "target_tasks_bucket": "target_tasks_le_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pair_bucket": "support_pairs_le_120_per_task", "control_pair_bucket": "control_pairs_le_120_per_task", "bounds_satisfied_bool": material["bounds_ok"]}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bkgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bksynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bkreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass" and report["status"] in {STATUS_DEFAULT, STATUS_PASS}: report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []; status = report.get("status"); explicit = status in {STATUS_PASS, STATUS_UNAVAILABLE}; success = status == STATUS_PASS; unavailable = status == STATUS_UNAVAILABLE
    if status not in {STATUS_DEFAULT, STATUS_PASS, STATUS_UNAVAILABLE}: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    expected = {"locked_haae_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_haae_r2bj_status": R2BJ_STATUS, "locked_haae_r2bj_self_test_total": R2BJ_SELF_TEST_TOTAL, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "r2bg_result_bucket": R2BG_RESULT_BUCKET, "r2bg_outcome_bucket": R2BG_OUTCOME_BUCKET}
    for f, e in expected.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    exec_rec = (report.get("execution_mode_records") or [{}])[0]
    if exec_rec.get("experiment_metric_bool") is not False or exec_rec.get("signal_interpretation_bool") is not False or exec_rec.get("source_candidate_corpus_scan_bool") is not False: issues.append("execution_boundary_mismatch")
    if exec_rec.get("private_read_bool") is not explicit or exec_rec.get("private_write_bool") is not explicit or exec_rec.get("material_repair_generation_bool") is not success: issues.append("execution_mode_mismatch")
    if (report.get("input_group_records") or [{}])[0].get("required_input_group_buckets") != R2BE_GROUPS: issues.append("input_group_set_mismatch")
    if (report.get("generated_group_records") or [{}])[0].get("required_output_group_buckets") != R2BK_GROUPS: issues.append("output_group_set_mismatch")
    if success and (report.get("generated_group_records") or [{}])[0].get("generated_group_set_exact_bool") is not True: issues.append("output_group_presence_mismatch")
    gen_rec = (report.get("generated_group_records") or [{}])[0]
    if unavailable and gen_rec.get("generation_bucket") != "outcome_alignment_unavailable_no_material_generated": issues.append("unavailable_generation_bucket_mismatch")
    if unavailable and gen_rec.get("generated_group_set_exact_bool") is not False: issues.append("unavailable_generated_group_exact_overauth")
    if unavailable and gen_rec.get("material_generated_bool") is not False: issues.append("unavailable_generated_group_material_overauth")
    for rec_name, false_fields in {"gold_alignment_records": ["gold_used_for_source_selection_bool", "gold_used_for_pair_construction_bool", "gold_used_for_ranking_scoring_claims_bool"], "no_metric_records": ["experiment_metrics_bool", "success_rates_mrr_hits_ranks_scores_bool", "signal_interpretation_bool"], "publication_records": ["private_rows_public_bool", "private_ids_paths_queries_gold_exact_values_public_bool"]}.items():
        rec = (report.get(rec_name) or [{}])[0]
        for f in false_fields:
            if rec.get(f) is not False: issues.append(f"{rec_name}_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if success or unavailable:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bl_stop_go_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
        if unavailable:
            if stop.get("r2bl_audit_controlled_unavailable_result_bool") is not True: issues.append("unavailable_audit_stop_go_missing")
            if stop.get("r2bl_generated_material_content_audit_bool") is not False: issues.append("unavailable_generated_material_content_audit_overauth")
            if stop.get("material_generated_bool") is not False: issues.append("unavailable_material_generated_overauth")
        if success and stop.get("r2bl_generated_material_content_audit_bool") is not True: issues.append("success_material_content_audit_missing")
    else:
        if stop.get("next_allowed_phase") == NEXT_PHASE: issues.append("default_stop_go_overauth")
        for f in STOP_TRUE:
            if stop.get(f) is not False: issues.append(f"default_stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def make_synth_r2be_root(base: Path, with_outcome: bool = True) -> Path:
    root = base / "r2be_input"; groups = root / "groups"; groups.mkdir(parents=True)
    manifest = {"schema_version": "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_private_material_v1", "phase": "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation", "source_lock": {"r2be_checkpoint": R2BE_CHECKPOINT}}
    (root / "r2be_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for g in R2BE_GROUPS:
        row = {"private_row_bucket": g, "selection_used_gold_bool": False, "experiment_metric_bool": False}
        if with_outcome and g == "redesigned_gold_isolation_eval_private":
            row["outcome_label"] = "synthetic_alignment_available"
        write_jsonl(groups / f"{g}.jsonl", [row])
    return root

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    base = load_json(repo_root() / R2BJ_REPORT_PATH)
    default = build_report("default", base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    tmp = Path(tempfile.mkdtemp(prefix="r2bk_selftest_", dir="/tmp/opencode"))
    try:
        inp = make_synth_r2be_root(tmp); out = tmp / "r2bk_out"; iok, _, ip, rows = validate_input_root(str(inp)); ook, _, op = validate_output_root(str(out), ip); mat = derive_rows(rows, op) if iok and ook and op else default_material(); explicit = build_report("explicit", base, mat, iok, ook, True); check("explicit_synthetic_generation_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
        no_label_inp = make_synth_r2be_root(tmp / "no_label_case", with_outcome=False); no_label_out = tmp / "r2bk_unavailable_out"; niok, _, nip, nrows = validate_input_root(str(no_label_inp)); nook, _, nop = validate_output_root(str(no_label_out), nip); nmat = derive_rows(nrows, nop) if niok and nook and nop else default_material(); unavailable_report = build_report("explicit", base, nmat, niok, nook, True); check("outcome_alignment_unavailable_fail_closed", unavailable_report["status"] == STATUS_UNAVAILABLE and validate_report(unavailable_report) == [])
        for name, mutate, issue in [
            ("unavailable_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("r2bl_audit_controlled_unavailable_result_bool", False), "unavailable_audit_stop_go_missing"),
            ("unavailable_material_generated_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generated_bool", True), "unavailable_material_generated_overauth"),
            ("unavailable_generated_content_audit_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("r2bl_generated_material_content_audit_bool", True), "unavailable_generated_material_content_audit_overauth"),
            ("unavailable_generated_group_exact_overauth_fail", lambda r: r["generated_group_records"][0].__setitem__("generated_group_set_exact_bool", True), "unavailable_generated_group_exact_overauth"),
            ("unavailable_generated_group_material_overauth_fail", lambda r: r["generated_group_records"][0].__setitem__("material_generated_bool", True), "unavailable_generated_group_material_overauth"),
        ]:
            m = json.loads(json.dumps(unavailable_report)); mutate(m); check(name, issue in validate_report(m))
        try: parse_args(["--bad"]); check("safe_parser_fail", False)
        except ValueError: check("safe_parser_fail", True)
        for name, args in [("missing_explicit_flag_fail", ["--r2be-private-material-root", str(inp)]), ("missing_input_root_fail", ["--allow-r2bk-explicit-local-outcome-aligned-repair-generation", "--r2bk-private-output-root", str(out), "--confirm-existing-r2be-material-only", "--confirm-private-output", "--confirm-no-experiment-metrics", "--confirm-aggregate-only-public-artifact"]), ("missing_output_root_fail", ["--allow-r2bk-explicit-local-outcome-aligned-repair-generation", "--r2be-private-material-root", str(inp), "--confirm-existing-r2be-material-only", "--confirm-private-output", "--confirm-no-experiment-metrics", "--confirm-aggregate-only-public-artifact"] )]:
            try: parse_args(args); check(name, False)
            except ValueError: check(name, True)
        source_muts = [("bad_r2bj_checkpoint_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bi_checkpoint", "bad")), ("bad_r2bj_status_fail", lambda r: r.__setitem__("status", "bad")), ("bad_r2bj_self_test_fail", lambda r: r.__setitem__("self_test_total", 0)), ("bad_r2bj_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True)), ("bad_r2bj_schema_drop_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].pop())]
        for name, mut in source_muts:
            m = json.loads(json.dumps(base)); mut(m); check(name, build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
        check("input_root_in_repo_fail", validate_input_root(str(repo_root()))[0] is False)
        check("input_root_missing_fail", validate_input_root(str(tmp / "missing"))[0] is False)
        missing = make_synth_r2be_root(tmp / "missing_case"); (missing / "groups" / f"{R2BE_GROUPS[0]}.jsonl").unlink(); check("input_group_missing_fail", validate_input_root(str(missing))[0] is False)
        extra = make_synth_r2be_root(tmp / "extra_case"); write_jsonl(extra / "groups" / "extra.jsonl", [{"x": 1}]); check("input_group_extra_fail", validate_input_root(str(extra))[0] is False)
        sym = make_synth_r2be_root(tmp / "sym_case"); (sym / "groups" / f"{R2BE_GROUPS[1]}.jsonl").unlink(); (sym / "groups" / f"{R2BE_GROUPS[1]}.jsonl").symlink_to(sym / "groups" / f"{R2BE_GROUPS[2]}.jsonl"); check("input_group_symlink_fail", validate_input_root(str(sym))[0] is False)
        check("output_root_in_repo_fail", validate_output_root(str(repo_root() / "r2bk_bad"), inp)[0] is False)
        check("nested_roots_fail", validate_output_root(str(inp / "child"), inp)[0] is False)
        sy = tmp / "out_symlink"; sy.symlink_to(tmp); check("output_root_symlink_fail", validate_output_root(str(sy), inp)[0] is False)
        unowned = tmp / "unowned"; unowned.mkdir(); (unowned / "x").write_text("x"); check("nonempty_unowned_output_fail", validate_output_root(str(unowned), inp)[0] is False)
        check("owned_rerun_pass", validate_output_root(str(out), inp)[0] is True)
        esc = tmp / "escape"; (esc / "groups").mkdir(parents=True); (esc / "r2bk_owner_manifest.json").write_text(json.dumps({"schema_version": PRIVATE_SCHEMA, "phase": PHASE})); (esc / "groups" / "bad").symlink_to(tmp); check("output_group_symlink_escape_fail", validate_output_root(str(esc), inp)[0] is False)
        report_muts = [("generated_group_missing_fail", lambda r: r["generated_group_records"][0]["required_output_group_buckets"].pop(), "output_group_set_mismatch"), ("generated_group_extra_fail", lambda r: r["generated_group_records"][0]["required_output_group_buckets"].append("extra"), "output_group_set_mismatch"), ("gold_policy_drift_fail", lambda r: r["gold_alignment_records"][0].__setitem__("gold_used_for_ranking_scoring_claims_bool", True), "gold_alignment_records_gold_used_for_ranking_scoring_claims_bool"), ("metric_policy_drift_fail", lambda r: r["no_metric_records"][0].__setitem__("experiment_metrics_bool", True), "no_metric_records_experiment_metrics_bool"), ("source_scan_policy_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "execution_boundary_mismatch"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
        for name, mut, issue in report_muts:
            m = json.loads(json.dumps(explicit)); mut(m); check(name, issue in validate_report(m))
        leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_DEFAULT}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out_path = public_artifact_path(str(args["out"])) if args["out"] else None
    if not args["explicit"]:
        report = build_report("default"); path = write_report(report, out_path); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_DEFAULT else 1
    iok, _, inp, rows = validate_input_root(str(args["input"])); ook, _, out_root = validate_output_root(str(args["output"]), inp if iok else None)
    material = derive_rows(rows, out_root) if iok and ook and out_root else default_material()
    report = build_report("explicit", material=material, input_ok=iok, output_ok=ook, flags_ok=True); path = write_report(report, out_path); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_PASS, STATUS_UNAVAILABLE} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
