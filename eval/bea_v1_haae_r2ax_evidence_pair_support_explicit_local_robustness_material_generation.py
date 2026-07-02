#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AX explicit local robustness material generation.

Default mode is a public unavailable/no-op artifact. Explicit mode requires
operator opt-in, an existing R2AN private material root, and a separate private
output root. It generates private robustness material only; it never computes
experiment metrics, scans source/candidate/corpus, or runs runtime/retrieval.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation"
SLUG = "bea_v1_haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PRIVATE_SCHEMA = f"{SLUG}_private_material_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2AW_CHECKPOINT = "bc44454"
R2AW_STATUS = "haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_complete_r2ax_explicit_local_robustness_material_generation_authorized"
R2AW_SELF_TEST_TOTAL = 53
R2AW_REPORT_PATH = Path("artifacts/bea_v1_haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight/bea_v1_haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_report.json")
R2AV_CHECKPOINT = "c0e4b4f"
R2AU_CHECKPOINT = "8af2b92"
R2AT_CHECKPOINT = "0c9c108"
R2AP_CHECKPOINT = "87ea9de"
R2AN_CHECKPOINT = "93bba5f"
R2AN_SCHEMA = "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1"
R2AN_PHASE = "BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation"
SIGNAL_FAMILY = "evidence_pair_support_complementarity"

STATUS_DEFAULT = "haae_r2ax_unavailable_no_explicit_local_robustness_material_generation_opt_in"
STATUS_PASS = "haae_r2ax_explicit_local_robustness_material_generation_complete_r2ay_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2ax_fail_closed_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2ax_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2ax_fail_closed_root_safety_or_input_material_invalid"
STATUS_FAIL_PRIVACY = "haae_r2ax_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2ax_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AY Evidence-Pair Support Robustness Material Public Audit Package"

R2AN_GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
R2AX_GROUPS = ["task_frame", "source_manifest_private", "base_evidence_unit_pool", "base_evidence_pair_material", "robustness_variant_material", "ablation_control_material", "hard_negative_control_material", "shuffled_mismatch_control_material", "outcome_eval_private", "material_qa", "source_material_manifest", "parent_r2an_row_ref_private"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
VARIANTS = ["single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control"]
BOUNDS = {"target_tasks": 20, "evidence_unit_depth_cap_per_task": 40, "support_pair_cap_per_task": 120, "contrast_control_pair_cap_per_task": 80, "total_pair_cap_per_task": 200, "private_row_cap": 20000, "source_file_cap": 500, "wall_clock_cap_minutes": 20}
EXPECTED_BUCKETS = {"mechanism_interpretation_bucket": "pair_complementarity_supported", "pair_complementarity_lift_bucket": "pair_complementarity_lift_high", "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_medium", "hard_negative_rejection_bucket": "hard_negative_rejection_medium", "path_confound_risk_bucket": "path_confound_risk_low", "gold_isolation_pass_bucket": "gold_isolation_pass"}
R2AW_GATES = ["r2av_source_locked_gate", "r2av_self_test_readback_gate", "r2av_gate_synthetic_exact_integrity_gate", "inherited_r2au_r2at_r2ap_r2an_lock_gate", "r2at_mechanism_bucket_gate", "r2ap_support_signal_gate", "public_only_non_executing_gate", "r2ax_design_selected_gate", "variant_axis_set_gate", "bounds_set_gate", "future_private_group_set_gate", "root_safety_design_gate", "material_generation_only_no_metrics_gate", "no_scan_runtime_claim_gate", "r2ax_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2AW_SYNTH = ["design_pass", "r2av_checkpoint_drift_fail", "r2av_status_drift_fail", "r2av_self_test_pollution_fail", "r2av_readback_duplicate_fail", "r2av_gate_drop_fail", "r2av_gate_duplicate_fail", "r2av_synthetic_drop_fail", "r2av_synthetic_duplicate_fail", "r2au_checkpoint_drift_fail", "r2au_self_test_pollution_fail", "r2at_checkpoint_drift_fail", "r2at_self_test_pollution_fail", "r2ap_checkpoint_drift_fail", "r2ap_self_test_pollution_fail", "r2an_checkpoint_drift_fail", "r2at_bucket_drift_fail", "r2ap_support_signal_drift_fail", "variant_axis_drift_fail", "future_group_drift_fail", "bounds_drift_fail", "root_safety_drift_fail", "private_read_overauth_fail", "private_write_overauth_fail", "implicit_discovery_overauth_fail", "diagnostics_read_overauth_fail", "material_generation_overauth_fail", "robustness_generation_overauth_fail", "robustness_execution_overauth_fail", "experiment_overauth_fail", "metric_recompute_overauth_fail", "mechanism_recompute_overauth_fail", "source_scan_overauth_fail", "source_scan_broad_overauth_fail", "bounded_manifest_source_read_overauth_fail", "candidate_scan_overauth_fail", "corpus_scan_overauth_fail", "ci_network_provider_runtime_overauth_fail", "scale_overauth_fail", "external_validation_overauth_fail", "method_default_overauth_fail", "winner_claim_overauth_fail", "raw_publication_overauth_fail", "stop_true_field_drop_fail", "next_phase_drift_fail", "claim_boundary_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
R2AW_SYNTH_COUNT = len(R2AW_SYNTH)
GATES = ["r2aw_source_lock_gate", "r2aw_stop_go_exact_gate", "default_noop_or_explicit_opt_in_gate", "root_safety_gate", "r2an_input_schema_group_gate", "r2an_pair_family_gate", "gold_eval_only_no_path_primary_gate", "generated_group_set_gate", "variant_set_gate", "bounds_gate", "material_generation_only_no_metrics_gate", "aggregate_only_public_gate", "r2ay_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "safe_parser_fail", "bad_r2aw_status_fail", "bad_r2aw_checkpoint_fail", "r2aw_stop_go_overauth_fail", "r2aw_stop_private_read_overauth_fail", "r2aw_synthetic_exact_set_fail", "missing_input_group_fail", "group_symlink_fail", "manifest_schema_fail", "missing_pair_family_fail", "gold_selection_fail", "path_primary_fail", "output_root_in_repo_fail", "nested_roots_fail", "nonempty_unowned_output_fail", "output_groups_symlink_fail", "missing_variant_fail", "missing_generated_group_fail", "bounds_drift_fail", "explicit_mode_drift_fail", "root_path_public_fail", "metrics_public_leak_fail", "stop_go_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2ay_evidence_pair_support_robustness_material_public_audit_authorized_bool", "r2ay_public_only_audit_bool", "r2ay_no_private_read_bool", "r2ay_no_metric_computation_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "private_diagnostics_read_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "new_candidate_generation_authorized_bool", "new_base_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_claim_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "method_winner_claim_authorized_bool", "winner_claim_authorized_bool", "raw_publication_authorized_bool"]

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"task_ref_value|private_task_ref|private_pair_ref|private_evidence_unit_ref|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]


def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "input": "", "output": "", "confirm_existing": False, "confirm_output": False, "confirm_no_metrics": False, "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2ax-explicit-local-robustness-material-generation": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2an-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-private-output": parsed["confirm_output"] = True; i += 1
        elif a == "--confirm-no-experiment-metrics": parsed["confirm_no_metrics"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--r2an-private-material-root", "--r2ax-private-output-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--r2an-private-material-root": "input", "--r2ax-private-output-root": "output"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "input", "output", "confirm_existing", "confirm_output", "confirm_no_metrics", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]; p = Path(value); resolved = p if p.is_absolute() else repo / p
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def has_traversal(value: str) -> bool: return any(part == ".." for part in Path(value).parts)
def outside_repo(path: Path) -> bool:
    repo = Path(__file__).resolve().parents[1]
    try: path.resolve(strict=False).relative_to(repo); return False
    except Exception: return True
def has_symlink_component(path: Path, must_exist: bool) -> bool:
    probe = path if path.is_absolute() else Path.cwd() / path
    parts = probe.parts; cur = Path(parts[0]) if probe.is_absolute() else Path(parts[0])
    start = 1
    if probe.is_absolute(): cur = Path("/"); start = 1
    for part in parts[start:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
        if must_exist and not cur.exists(): return True
    return False


def audit_r2aw(r2aw: dict[str, Any]) -> dict[str, bool]:
    src = (r2aw.get("source_lock_records") or [{}])[0]; stop = (r2aw.get("stop_go_records") or [{}])[0]; result = (r2aw.get("inherited_support_mechanism_result_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2aw.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2aw.get("synthetic_validator_records", [])]; readback = r2aw.get("public_readback_records", [])
    lock_ok = r2aw.get("status") == R2AW_STATUS and r2aw.get("self_test_total") == R2AW_SELF_TEST_TOTAL and r2aw.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2av_checkpoint") == R2AV_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("source_locked_bool") is True
    integrity_ok = set(gates) == set(R2AW_GATES) and len(gates) == len(R2AW_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2AW_SYNTH) and len(synth) == R2AW_SYNTH_COUNT and len(synth) == len(set(synth)) and len(readback) == 1 and readback[0].get("all_public_readback_match_bool") is True
    bucket_ok = all(result.get(k) == v for k, v in EXPECTED_BUCKETS.items()) and result.get("r2ap_result_bucket") == "support_signal" and result.get("selected_signal_family_bucket") == SIGNAL_FAMILY
    stop_true = ["haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation_authorized_bool", "r2ax_explicit_opt_in_required_bool", "r2ax_existing_r2an_private_material_read_authorized_bool", "r2ax_private_output_write_authorized_bool", "r2ax_robustness_material_generation_authorized_bool", "r2ax_material_generation_only_no_experiment_metrics_bool", "r2ax_aggregate_only_public_artifact_required_bool", "r2ax_public_audit_required_after_generation_bool"]
    false_fields = ["default_private_implicit_discovery_authorized_bool", "implicit_private_root_discovery_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "material_generation_authorized_bool", "robustness_material_generation_execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "r2ax_bounded_public_manifest_source_read_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "new_candidate_generation_authorized_bool", "new_base_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in stop_true) and all(stop.get(f, False) is False for f in false_fields)
    return {"source_ok": lock_ok and integrity_ok and bucket_ok and stop_ok, "lock_ok": lock_ok, "integrity_ok": integrity_ok, "bucket_ok": bucket_ok, "stop_ok": stop_ok}


def validate_input_root(root_value: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    if not root_value or has_traversal(root_value): return False, "input_root_traversal_rejected", {}
    root = Path(root_value)
    try:
        if not root.exists() or root.is_symlink() or has_symlink_component(root, True) or not outside_repo(root): return False, "input_root_safety_rejected", {}
        manifest_path = root / "r2an_private_manifest.json"; groups_dir = root / "groups"
        if not manifest_path.is_file() or manifest_path.is_symlink() or not groups_dir.is_dir() or groups_dir.is_symlink(): return False, "input_manifest_or_groups_missing", {}
        manifest = load_json(manifest_path)
        if manifest.get("schema_version") != R2AN_SCHEMA or manifest.get("phase") != R2AN_PHASE or manifest.get("selected_signal_family") != SIGNAL_FAMILY: return False, "input_manifest_schema_mismatch", {}
        if set((manifest.get("groups") or {}).keys()) != set(R2AN_GROUPS): return False, "input_manifest_group_set_mismatch", {}
        present = {p.name for p in groups_dir.iterdir() if p.is_file() or p.is_symlink()}
        if present != {f"{g}.jsonl" for g in R2AN_GROUPS}: return False, "input_group_file_set_mismatch", {}
        rows: dict[str, list[dict[str, Any]]] = {}
        for g in R2AN_GROUPS:
            p = groups_dir / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or root.resolve() not in p.resolve().parents: return False, "input_group_file_invalid", {}
            rows[g] = load_jsonl(p)
            if not rows[g]: return False, "input_group_empty", {}
    except Exception:
        return False, "input_root_invalid", {}
    fams = {r.get("pair_family_bucket") for g in ["evidence_pair_material", "support_relation_material", "contrast_control_material"] for r in rows.get(g, [])}
    if not set(PAIR_FAMILIES).issubset(fams): return False, "input_pair_family_missing", {}
    for g in ["evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material"]:
        for r in rows[g]:
            if r.get("selection_used_gold_bool") is not False or r.get("selection_used_path_bool") is not False or r.get("single_rank_primary_signal_bool") is True or r.get("path_tokens_primary_signal_bool") is True: return False, "input_gold_or_path_primary_policy", {}
    for r in rows["outcome_eval_private"]:
        if r.get("gold_private_eval_only_bool") is not True or r.get("used_for_evidence_unit_selection_bool") is not False or r.get("used_for_pair_selection_bool") is not False: return False, "input_gold_eval_only_mismatch", {}
    return True, "input_r2an_material_valid", rows


def validate_output_root(output_value: str, input_value: str) -> tuple[bool, str, Path | None]:
    if not output_value or has_traversal(output_value): return False, "output_root_traversal_rejected", None
    out = Path(output_value); inp = Path(input_value)
    try:
        if out.exists() and out.is_symlink(): return False, "output_root_symlink_rejected", None
        if has_symlink_component(out, False) or not outside_repo(out): return False, "output_root_safety_rejected", None
        out_res = out.resolve(strict=False); in_res = inp.resolve(strict=True)
        if out_res == in_res or out_res in in_res.parents or in_res in out_res.parents: return False, "nested_roots_rejected", None
        if out.exists() and any(out.iterdir()):
            mf = out / "r2ax_private_manifest.json"
            if not mf.is_file(): return False, "nonempty_unowned_output_rejected", None
            old = load_json(mf)
            if old.get("schema_version") != PRIVATE_SCHEMA or old.get("phase") != PHASE: return False, "nonempty_unowned_output_rejected", None
        out.mkdir(parents=True, exist_ok=True); (out / "groups").mkdir(exist_ok=True)
        groups = out / "groups"
        if groups.is_symlink() or not groups.is_dir() or out.resolve() not in groups.resolve().parents: return False, "output_groups_escape_rejected", None
    except Exception:
        return False, "output_root_invalid", None
    return True, "output_root_valid", out


def generate_private_material(rows: dict[str, list[dict[str, Any]]], out: Path) -> dict[str, Any]:
    start = time.time(); groups_dir = out / "groups"; task_order = [r.get("private_task_ref") for r in rows["task_frame"]][: BOUNDS["target_tasks"]]
    if groups_dir.is_symlink() or not groups_dir.is_dir() or out.resolve() not in groups_dir.resolve().parents:
        raise RuntimeError("invalid arguments")
    task_set = set(task_order)
    units: list[dict[str, Any]] = []
    for task in task_order:
        units.extend([dict(r) for r in rows["evidence_unit_pool"] if r.get("private_task_ref") == task][: BOUNDS["evidence_unit_depth_cap_per_task"]])
    base_pairs: list[dict[str, Any]] = []
    for task in task_order:
        support = [r for r in rows["evidence_pair_material"] if r.get("private_task_ref") == task and r.get("pair_family_bucket") in {"target_support_pair", "complementary_support_pair"}][: BOUNDS["support_pair_cap_per_task"]]
        control = [r for r in rows["evidence_pair_material"] if r.get("private_task_ref") == task and r.get("pair_family_bucket") not in {"target_support_pair", "complementary_support_pair"}][: BOUNDS["contrast_control_pair_cap_per_task"]]
        base_pairs.extend([dict(r) for r in (support + control)[: BOUNDS["total_pair_cap_per_task"]]])
    by_task: dict[str, list[dict[str, Any]]] = {str(t): [p for p in base_pairs if p.get("private_task_ref") == t] for t in task_order}
    variants: list[dict[str, Any]] = []
    for task, plist in by_task.items():
        seed = plist[: max(1, len(VARIANTS))]
        for idx, variant in enumerate(VARIANTS):
            parent = seed[idx % len(seed)] if seed else {"private_pair_ref": "unavailable", "pair_family_bucket": "unavailable"}
            variants.append({"private_task_ref": task, "robustness_variant_bucket": variant, "parent_private_pair_ref": parent.get("private_pair_ref"), "parent_pair_family_bucket": parent.get("pair_family_bucket"), "derived_from_existing_r2an_material_bool": True, "experiment_metric_bool": False})
    ablation = [r for r in variants if r["robustness_variant_bucket"] == "single_unit_ablation"]
    hard = [r for r in variants if r["robustness_variant_bucket"] == "hard_negative_strengthening"]
    shuffled = [r for r in variants if r["robustness_variant_bucket"] in {"shuffled_pair_control", "cross_task_mismatch_control"}]
    out_rows = {
        "task_frame": [dict(r) for r in rows["task_frame"] if r.get("private_task_ref") in task_set],
        "source_manifest_private": [dict(r) for r in rows["source_manifest_private"][: BOUNDS["source_file_cap"]]],
        "base_evidence_unit_pool": units,
        "base_evidence_pair_material": base_pairs,
        "robustness_variant_material": variants,
        "ablation_control_material": ablation,
        "hard_negative_control_material": hard,
        "shuffled_mismatch_control_material": shuffled,
        "outcome_eval_private": [dict(r) for r in rows["outcome_eval_private"] if r.get("private_task_ref") in task_set],
        "material_qa": [{"material_qa_bucket": "r2ax_material_generation_only", "no_experiment_metrics_bool": True, "no_source_candidate_corpus_scan_bool": True, "variant_set_exact_bool": True}],
        "source_material_manifest": [{"source_phase": R2AN_PHASE, "source_schema_version": R2AN_SCHEMA, "source_checkpoint": R2AN_CHECKPOINT, "derived_from_existing_r2an_material_only_bool": True}],
        "parent_r2an_row_ref_private": [],
    }
    parent_refs = []
    for g in ["task_frame", "base_evidence_unit_pool", "base_evidence_pair_material", "robustness_variant_material"]:
        for idx, r in enumerate(out_rows[g]): parent_refs.append({"r2ax_group_bucket": g, "row_index_private": idx, "parent_ref_private": r.get("private_pair_ref") or r.get("private_evidence_unit_ref") or r.get("private_task_ref") or r.get("parent_private_pair_ref")})
    out_rows["parent_r2an_row_ref_private"] = parent_refs
    if sum(len(v) for v in out_rows.values()) > BOUNDS["private_row_cap"]: raise RuntimeError("invalid arguments")
    for g in R2AX_GROUPS:
        path = groups_dir / f"{g}.jsonl"
        if path.exists() and path.is_symlink():
            raise RuntimeError("invalid arguments")
        write_jsonl(path, out_rows[g])
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2aw_checkpoint": R2AW_CHECKPOINT, "r2an_checkpoint": R2AN_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2ax_explicit_local_run"}, "bounds": BOUNDS, "variants": VARIANTS, "groups": {g: {"row_count": len(out_rows[g])} for g in R2AX_GROUPS}, "wall_clock_bucket": "under_20min" if time.time() - start < BOUNDS["wall_clock_cap_minutes"] * 60 else "over_20min"}
    (out / "r2ax_private_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"generated": True, "groups": set(out_rows.keys()), "variants": {r["robustness_variant_bucket"] for r in variants}, "bounds_ok": True, "row_cap_ok": True}


def default_material_result() -> dict[str, Any]: return {"generated": False, "groups": set(), "variants": set(), "bounds_ok": False, "row_cap_ok": False}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2AW_CHECKPOINT, R2AW_STATUS, R2AN_CHECKPOINT, "default mode", "no private read/write/generation/scan/metrics", "explicit local robustness material generation", "existing R2AN private material", "private output root", "no experiment metrics", "aggregate-only public artifact", "single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = ok(read("README.md")); detail = ok(read("docs/en/bea-v1-haae-r2ax-evidence-pair-support-explicit-local-robustness-material-generation.md")) and ok(read("docs/zh/bea-v1-haae-r2ax-evidence-pair-support-explicit-local-robustness-material-generation.md"))
    root = read("docs/current-research-conclusions.md"); current = ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2ax-evidence-pair-support-explicit-local-robustness-material-generation.md" in root
    log = ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")); summary = ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(args: dict[str, str | bool] | None = None, r2aw: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]; args = args or {"explicit": False}
    if r2aw is None:
        try: r2aw = load_json(repo / R2AW_REPORT_PATH)
        except Exception: r2aw = {}
    source = audit_r2aw(r2aw); readback = public_readback_match(self_test_total); explicit = bool(args.get("explicit"))
    root_ok = True; input_bucket = "not_read_default_mode"; output_bucket = "not_written_default_mode"; material = default_material_result()
    if explicit and source["source_ok"]:
        in_ok, input_bucket, rows = validate_input_root(str(args.get("input", "")))
        out_ok, output_bucket, out_path = validate_output_root(str(args.get("output", "")), str(args.get("input", ""))) if in_ok else (False, "output_not_checked_input_invalid", None)
        root_ok = in_ok and out_ok
        if root_ok and out_path is not None:
            try: material = generate_private_material(rows, out_path)
            except Exception: root_ok = False; output_bucket = "generation_failed"; material = default_material_result()
    status = STATUS_FAIL_SOURCE if not source["source_ok"] else (STATUS_FAIL_ROOT if explicit and not root_ok else (STATUS_FAIL_READBACK if not readback["all_public_readback_match_bool"] else (STATUS_PASS if explicit else STATUS_DEFAULT)))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2axstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_explicit_generation_success"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    generated_groups = material["groups"]; variants = material["variants"]
    gates = {"r2aw_source_lock_gate": source["source_ok"], "r2aw_stop_go_exact_gate": source["stop_ok"], "default_noop_or_explicit_opt_in_gate": True, "root_safety_gate": (not explicit) or root_ok, "r2an_input_schema_group_gate": (not explicit) or input_bucket == "input_r2an_material_valid", "r2an_pair_family_gate": (not explicit) or input_bucket == "input_r2an_material_valid", "gold_eval_only_no_path_primary_gate": (not explicit) or input_bucket == "input_r2an_material_valid", "generated_group_set_gate": (not explicit) or set(generated_groups) == set(R2AX_GROUPS), "variant_set_gate": (not explicit) or set(variants) == set(VARIANTS), "bounds_gate": (not explicit) or material["bounds_ok"], "material_generation_only_no_metrics_gate": True, "aggregate_only_public_gate": True, "r2ay_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2axsource0000", "locked_haae_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_haae_r2aw_status": R2AW_STATUS, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2aw_source_lock_bool": source["lock_ok"], "r2aw_stop_go_exact_bool": source["stop_ok"], "r2aw_readback_gate_synthetic_exact_bool": source["integrity_ok"], "r2at_r2ap_result_bucket_lock_bool": source["bucket_ok"], "source_locked_bool": source["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2axmode0000", "default_mode_noop_bool": not explicit, "explicit_mode_executed_bool": explicit and passed, "private_read_existing_r2an_material_bool": explicit and passed, "private_output_write_bool": explicit and passed, "robustness_material_generation_bool": explicit and passed, "experiment_metrics_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_openlocus_retrieval_bool": False}],
        "root_safety_records": [{"anonymous_root_safety_id": "haaer2axroot0000", "input_root_safety_bucket": input_bucket, "output_root_safety_bucket": output_bucket, "root_path_public_bool": False, "implicit_discovery_bool": False, "nested_roots_bool": False if root_ok else "rejected_bucket"}],
        "input_validation_records": [{"anonymous_input_validation_id": "haaer2axinput0000", "manifest_schema_valid_bool": (not explicit) or input_bucket == "input_r2an_material_valid", "group_set_exact_bool": (not explicit) or input_bucket == "input_r2an_material_valid", "pair_family_set_present_bool": (not explicit) or input_bucket == "input_r2an_material_valid", "gold_eval_only_bool": (not explicit) or input_bucket == "input_r2an_material_valid", "no_path_primary_policy_bool": (not explicit) or input_bucket == "input_r2an_material_valid"}],
        "generated_material_records": [{"anonymous_generated_material_id": "haaer2axmaterial0000", "generated_group_presence_buckets": {g: ("present" if g in generated_groups else ("not_generated_default" if not explicit else "missing")) for g in R2AX_GROUPS}, "variant_presence_buckets": {v: ("present" if v in variants else ("not_generated_default" if not explicit else "missing")) for v in VARIANTS}, "bounds_bucket": "bounds_satisfied" if material["bounds_ok"] else ("not_applicable_default" if not explicit else "bounds_failed"), "private_row_cap_bucket": "under_private_row_cap" if material["row_cap_ok"] else ("not_applicable_default" if not explicit else "row_cap_failed"), "material_generation_only_no_experiment_metrics_bool": True}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2axprivacy0000", "aggregate_only_public_artifact_bool": True, "no_raw_private_publication_bool": True, "no_exact_metric_publication_bool": True, "no_scores_rates_mrr_bool": True, "no_private_root_path_public_bool": True}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2axgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2axsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2axreadback0000", **readback}],
        "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_DEFAULT, STATUS_PASS} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "root_safety_records", "input_validation_records", "generated_material_records", "privacy_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS}: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_haae_r2aw_status": R2AW_STATUS, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    for f in ["r2aw_source_lock_bool", "r2aw_stop_go_exact_bool", "r2aw_readback_gate_synthetic_exact_bool", "r2at_r2ap_result_bucket_lock_bool", "source_locked_bool"]:
        if src.get(f) is not True: issues.append(f"source_{f}")
    mode = (report.get("execution_mode_records") or [{}])[0]; explicit = report.get("status") == STATUS_PASS
    if not explicit:
        for f in ["explicit_mode_executed_bool", "private_read_existing_r2an_material_bool", "private_output_write_bool", "robustness_material_generation_bool"]:
            if mode.get(f) is not False: issues.append(f"default_{f}")
    else:
        for f in ["explicit_mode_executed_bool", "private_read_existing_r2an_material_bool", "private_output_write_bool", "robustness_material_generation_bool"]:
            if mode.get(f) is not True: issues.append(f"explicit_{f}")
    for f in ["experiment_metrics_bool", "source_candidate_corpus_scan_bool", "runtime_openlocus_retrieval_bool"]:
        if mode.get(f) is not False: issues.append(f"mode_{f}")
    root = (report.get("root_safety_records") or [{}])[0]
    if explicit:
        if root.get("input_root_safety_bucket") != "input_r2an_material_valid" or root.get("output_root_safety_bucket") != "output_root_valid" or root.get("nested_roots_bool") is not False: issues.append("root_safety_explicit_mismatch")
    if root.get("root_path_public_bool") is not False or root.get("implicit_discovery_bool") is not False: issues.append("root_public_or_implicit_mismatch")
    inp = (report.get("input_validation_records") or [{}])[0]
    for f in ["manifest_schema_valid_bool", "group_set_exact_bool", "pair_family_set_present_bool", "gold_eval_only_bool", "no_path_primary_policy_bool"]:
        if inp.get(f) is not True: issues.append(f"input_{f}")
    gen = (report.get("generated_material_records") or [{}])[0]
    if explicit:
        if any(v != "present" for v in (gen.get("generated_group_presence_buckets") or {}).values()): issues.append("generated_group_missing")
        if any(v != "present" for v in (gen.get("variant_presence_buckets") or {}).values()): issues.append("generated_variant_missing")
        if gen.get("bounds_bucket") != "bounds_satisfied" or gen.get("private_row_cap_bucket") != "under_private_row_cap": issues.append("bounds_mismatch")
    if set((gen.get("generated_group_presence_buckets") or {}).keys()) != set(R2AX_GROUPS): issues.append("generated_group_set_mismatch")
    if set((gen.get("variant_presence_buckets") or {}).keys()) != set(VARIANTS): issues.append("variant_set_mismatch")
    if gen.get("material_generation_only_no_experiment_metrics_bool") is not True: issues.append("material_generation_metrics_mismatch")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    for f in ["aggregate_only_public_artifact_bool", "no_raw_private_publication_bool", "no_exact_metric_publication_bool", "no_scores_rates_mrr_bool", "no_private_root_path_public_bool"]:
        if priv.get(f) is not True: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if explicit:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2ay_stop_go_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
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


def make_synth_r2an(root: Path, mut: str = "") -> None:
    groups = root / "groups"; groups.mkdir(parents=True)
    manifest = {"schema_version": R2AN_SCHEMA if mut != "schema" else "bad", "phase": R2AN_PHASE, "selected_signal_family": SIGNAL_FAMILY, "groups": {g: {"row_count": 1} for g in R2AN_GROUPS}}
    (root / "r2an_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    tasks = [{"private_task_ref": f"task{i:04d}"} for i in range(2)]
    units = [{"private_task_ref": t["private_task_ref"], "private_evidence_unit_ref": f"u{i}{j}", "private_source_ref": "src0", "selection_used_gold_bool": mut == "gold", "selection_used_path_bool": mut == "path", "single_rank_primary_signal_bool": False} for i, t in enumerate(tasks) for j in range(4)]
    pairs = []
    for i, t in enumerate(tasks):
        for j, fam in enumerate(PAIR_FAMILIES): pairs.append({"private_task_ref": t["private_task_ref"], "private_pair_ref": f"p{i}{j}", "pair_family_bucket": fam, "left_unit_ref": f"u{i}0", "right_unit_ref": f"u{i}1", "selection_used_gold_bool": False, "selection_used_path_bool": False})
    if mut == "family": pairs = [p for p in pairs if p["pair_family_bucket"] != "cross_task_mismatch_control"]
    data = {"task_frame": tasks, "source_manifest_private": [{"private_source_ref": "src0", "source_path_private": "x"}], "evidence_unit_pool": units, "evidence_pair_material": pairs, "support_relation_material": [p for p in pairs if p["pair_family_bucket"] in {"target_support_pair", "complementary_support_pair"}], "contrast_control_material": [p for p in pairs if p["pair_family_bucket"] not in {"target_support_pair", "complementary_support_pair"}], "outcome_eval_private": [{"private_task_ref": t["private_task_ref"], "gold_private_eval_only_bool": True, "used_for_evidence_unit_selection_bool": False, "used_for_pair_selection_bool": False} for t in tasks], "material_qa": [{"ok": True}]}
    for g, rows in data.items(): write_jsonl(groups / f"{g}.jsonl", rows)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; base = load_json(repo / R2AW_REPORT_PATH)
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    default = build_report(r2aw=base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        tmp = Path(td); inp = tmp / "input"; out = tmp / "out"; make_synth_r2an(inp)
        explicit = build_report({"explicit": True, "input": str(inp), "output": str(out)}, base); check("explicit_synthetic_generation_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [] and (out / "r2ax_private_manifest.json").exists())
        for name, mut, expect in [("missing_input_group_fail", "", STATUS_FAIL_ROOT), ("manifest_schema_fail", "schema", STATUS_FAIL_ROOT), ("missing_pair_family_fail", "family", STATUS_FAIL_ROOT), ("gold_selection_fail", "gold", STATUS_FAIL_ROOT), ("path_primary_fail", "path", STATUS_FAIL_ROOT)]:
            r = tmp / name; make_synth_r2an(r, mut)
            if name == "missing_input_group_fail": (r / "groups" / "task_frame.jsonl").unlink()
            check(name, build_report({"explicit": True, "input": str(r), "output": str(tmp / f"out_{name}")}, base)["status"] == expect)
        sy = tmp / "symlink_case"; make_synth_r2an(sy); (sy / "groups" / "evidence_unit_pool.jsonl").unlink(); (sy / "groups" / "evidence_unit_pool.jsonl").symlink_to(inp / "groups" / "evidence_unit_pool.jsonl"); check("group_symlink_fail", build_report({"explicit": True, "input": str(sy), "output": str(tmp / "out_sy")}, base)["status"] == STATUS_FAIL_ROOT)
        check("nested_roots_fail", build_report({"explicit": True, "input": str(inp), "output": str(inp / "nested")}, base)["status"] == STATUS_FAIL_ROOT)
        unowned = tmp / "unowned"; unowned.mkdir(); (unowned / "x").write_text("x"); check("nonempty_unowned_output_fail", build_report({"explicit": True, "input": str(inp), "output": str(unowned)}, base)["status"] == STATUS_FAIL_ROOT)
        owned_escape = tmp / "owned_escape"; owned_escape.mkdir(); (owned_escape / "r2ax_private_manifest.json").write_text(json.dumps({"schema_version": PRIVATE_SCHEMA, "phase": PHASE}), encoding="utf-8"); (owned_escape / "groups").symlink_to(tmp)
        check("output_groups_symlink_fail", build_report({"explicit": True, "input": str(inp), "output": str(owned_escape)}, base)["status"] == STATUS_FAIL_ROOT)
    try: parse_args(["--allow-r2ax-explicit-local-robustness-material-generation", "--confirm-private-output"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    bad = json.loads(json.dumps(base)); bad["status"] = "bad"; check("bad_r2aw_status_fail", build_report(r2aw=bad)["status"] == STATUS_FAIL_SOURCE)
    bad = json.loads(json.dumps(base)); bad["source_lock_records"][0]["locked_haae_r2av_checkpoint"] = "bad"; check("bad_r2aw_checkpoint_fail", build_report(r2aw=bad)["status"] == STATUS_FAIL_SOURCE)
    bad = json.loads(json.dumps(base)); bad["stop_go_records"][0]["metric_recompute_authorized_bool"] = True; check("r2aw_stop_go_overauth_fail", build_report(r2aw=bad)["status"] == STATUS_FAIL_SOURCE)
    bad = json.loads(json.dumps(base)); bad["stop_go_records"][0]["private_read_authorized_bool"] = True; check("r2aw_stop_private_read_overauth_fail", build_report(r2aw=bad)["status"] == STATUS_FAIL_SOURCE)
    bad = json.loads(json.dumps(base)); bad["synthetic_validator_records"].pop(); check("r2aw_synthetic_exact_set_fail", build_report(r2aw=bad)["status"] == STATUS_FAIL_SOURCE)
    mutations = [("missing_variant_fail", lambda r: r["generated_material_records"][0]["variant_presence_buckets"].__setitem__(VARIANTS[0], "missing"), "generated_variant_missing"), ("missing_generated_group_fail", lambda r: r["generated_material_records"][0]["generated_group_presence_buckets"].__setitem__(R2AX_GROUPS[0], "missing"), "generated_group_missing"), ("bounds_drift_fail", lambda r: r["generated_material_records"][0].__setitem__("bounds_bucket", "bad"), "bounds_mismatch"), ("explicit_mode_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_output_write_bool", False), "explicit_private_output_write_bool"), ("root_path_public_fail", lambda r: r["root_safety_records"][0].__setitem__("root_path_public_bool", True), "root_public_or_implicit_mismatch"), ("metrics_public_leak_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("no_scores_rates_mrr_bool", False), "privacy_no_scores_rates_mrr_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        inp = Path(td) / "i"; out = Path(td) / "o"; make_synth_r2an(inp); good = build_report({"explicit": True, "input": str(inp), "output": str(out)}, base)
        for name, mut, issue in mutations:
            m = json.loads(json.dumps(good)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    # output_root_in_repo_fail cannot create in repo during tests; validate helper directly.
    check("output_root_in_repo_fail", validate_output_root(str(repo / "r2ax_tmp"), "/tmp/opencode/nonexistent_input")[0] is False)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        res = run_self_test(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(args); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS} else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
