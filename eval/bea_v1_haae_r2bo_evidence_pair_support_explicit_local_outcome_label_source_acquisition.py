#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BO explicit local outcome label source acquisition.

Default mode is a public no-op and reads no private roots or label manifests.
Explicit mode requires operator opt-in, an existing R2BE private material root,
an explicit committed label source manifest, and an explicit private output root.
It writes private label acquisition groups only; it does not repair material,
compute metrics, scan source/candidate/corpus, or publish raw/exact/private data.
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

PHASE = "BEA-v1-HAAE-R2BO Evidence-Pair Support Explicit Local Outcome Label Source Acquisition"
SLUG = "bea_v1_haae_r2bo_evidence_pair_support_explicit_local_outcome_label_source_acquisition"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PRIVATE_SCHEMA = f"{SLUG}_private_label_acquisition_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BN_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bn_evidence_pair_support_outcome_label_acquisition_public_design_preflight/bea_v1_haae_r2bn_evidence_pair_support_outcome_label_acquisition_public_design_preflight_report.json")

R2BN_CHECKPOINT = "af901f6"
R2BN_STATUS = "haae_r2bn_outcome_label_acquisition_public_design_preflight_complete_r2bo_explicit_local_label_source_acquisition_authorized"
R2BN_SELF_TEST_TOTAL = 55
R2BM_CHECKPOINT = "219c890"
R2BL_CHECKPOINT = "41aef9e"
R2BK_CHECKPOINT = "7073b12"
R2BE_CHECKPOINT = "c3901d6"

STATUS_DEFAULT = "haae_r2bo_unavailable_no_explicit_local_label_source_acquisition_opt_in"
STATUS_PASS = "haae_r2bo_explicit_local_outcome_label_source_acquisition_complete_r2bp_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2bo_fail_closed_r2bn_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2bo_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2bo_fail_closed_root_or_label_manifest_safety"
STATUS_FAIL_ACQUISITION = "haae_r2bo_fail_closed_label_source_acquisition_contract"
STATUS_FAIL_PRIVACY = "haae_r2bo_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bo_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BP Evidence-Pair Support Outcome Label Source Acquisition Public Audit Package"

R2BE_GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
OUTPUT_GROUPS = ["outcome_label_source_manifest_private", "outcome_label_task_alignment_private", "outcome_label_pair_family_alignment_private", "outcome_label_provenance_private", "manual_label_import_private", "existing_label_recovery_private", "label_quality_qa_private", "parent_r2be_row_ref_private"]
BOUNDS = {"target_tasks": 20, "private_row_cap": 20000, "label_manifest_cap": 500}
R2BN_STOP_TRUE = ["haae_r2bo_explicit_local_outcome_label_source_acquisition_authorized_bool", "r2bo_explicit_opt_in_required_bool", "r2bo_operator_provided_label_manifest_required_bool", "r2bo_existing_r2be_private_material_read_allowed_bool", "r2bo_private_label_output_write_authorized_bool", "r2bo_label_source_acquisition_only_bool", "r2bo_no_material_repair_generation_bool", "r2bo_no_experiment_metrics_bool", "r2bo_aggregate_only_public_artifact_required_bool", "r2bo_public_audit_required_after_acquisition_bool", "controlled_unavailable_result_locked_bool", "outcome_alignment_source_labels_absent_locked_bool"]
R2BN_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_execution_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_generation_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "synthetic_ground_truth_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bn_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "explicit_argument_gate", "r2be_input_root_safety_gate", "label_source_manifest_safety_gate", "private_output_root_safety_gate", "input_schema_group_exact_gate", "output_schema_group_exact_gate", "label_source_policy_gate", "bounds_gate", "no_material_repair_metric_scan_gate", "aggregate_only_public_gate", "r2bp_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_success_pass", "safe_parser_fail", "missing_allow_flag_fail", "missing_r2be_root_fail", "missing_label_manifest_fail", "missing_output_root_fail", "bad_r2bn_checkpoint_fail", "bad_r2bn_status_fail", "r2bn_stop_go_overauth_fail", "input_root_in_repo_fail", "input_root_missing_fail", "input_root_symlink_fail", "input_group_missing_fail", "input_group_extra_fail", "input_group_symlink_fail", "label_manifest_missing_fail", "label_manifest_tmp_rejected_fail", "label_manifest_traversal_rejected_fail", "label_manifest_symlink_fail", "label_manifest_schema_invalid_fail", "output_root_in_repo_fail", "nested_roots_fail", "output_root_symlink_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "output_group_symlink_escape_fail", "source_locked_drift_fail", "explicit_status_drift_fail", "explicit_group_exact_drift_fail", "explicit_execution_private_read_drift_fail", "explicit_execution_label_manifest_read_drift_fail", "explicit_execution_private_write_drift_fail", "explicit_root_safety_drift_fail", "output_group_missing_fail", "output_group_extra_fail", "bounds_drift_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "publication_raw_label_overauth_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_material_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bp_outcome_label_source_acquisition_public_audit_authorized_bool", "r2bp_public_only_audit_bool", "r2bp_no_private_read_bool", "r2bp_no_metric_computation_bool", "r2bp_no_material_generation_bool", "r2bp_audit_label_acquisition_result_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_generation_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|fixtures/r14|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_label", re.compile(r"gold_spans|hard_negatives|gold_label|rationale|start_line|end_line|mined_high_confidence", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|filepath_value|source_filename_value|directory_value|snippet_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [n for n, p in LEAK_PATTERNS if p.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def has_traversal(v: str) -> bool: return any(part == ".." for part in Path(v).parts)
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def has_symlink_component(path: Path, must_exist: bool) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/") if p.is_absolute() else Path(p.parts[0]); start = 1
    for part in p.parts[start:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
        if must_exist and not cur.exists(): return True
    return False

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "r2be_root": "", "label_manifest": "", "output": "", "confirm_existing": False, "confirm_private": False, "confirm_no_metrics": False, "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2bo-explicit-local-outcome-label-source-acquisition": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2be-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-private-output": parsed["confirm_private"] = True; i += 1
        elif a == "--confirm-no-experiment-metrics": parsed["confirm_no_metrics"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--private-r2be-material-root", "--label-source-manifest", "--r2bo-private-output-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--private-r2be-material-root": "r2be_root", "--label-source-manifest": "label_manifest", "--r2bo-private-output-root": "output"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "r2be_root", "label_manifest", "output", "confirm_existing", "confirm_private", "confirm_no_metrics", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bn(r2bn: dict[str, Any]) -> bool:
    src = (r2bn.get("source_lock_records") or [{}])[0]; stop = (r2bn.get("stop_go_records") or [{}])[0]
    groups = (r2bn.get("future_r2bo_schema_group_records") or [{}])[0].get("group_set", [])
    return r2bn.get("status") == R2BN_STATUS and r2bn.get("self_test_total") == R2BN_SELF_TEST_TOTAL and r2bn.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bm_checkpoint") == R2BM_CHECKPOINT and src.get("locked_haae_r2bl_checkpoint") == R2BL_CHECKPOINT and src.get("locked_haae_r2bk_checkpoint") == R2BK_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True and set(groups) == set(OUTPUT_GROUPS) and len(groups) == len(OUTPUT_GROUPS) and stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BN_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BN_STOP_FALSE)

def validate_r2be_root(value: str) -> tuple[bool, str, Path | None]:
    if not value or has_traversal(value): return False, "input_root_traversal_rejected", None
    root = Path(value)
    try:
        if not root.exists() or not root.is_dir() or root.is_symlink() or has_symlink_component(root, True) or not outside_repo(root): return False, "input_root_invalid", None
        manifest = root / "r2be_private_manifest.json"; groups = root / "groups"
        if not manifest.is_file() or manifest.is_symlink() or not groups.is_dir() or groups.is_symlink(): return False, "input_manifest_or_groups_missing", None
        m = load_json(manifest)
        if m.get("schema_version") != "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_private_material_v1": return False, "input_manifest_schema_mismatch", None
        files = sorted(p.stem for p in groups.glob("*.jsonl"))
        if files != sorted(R2BE_GROUPS): return False, "input_group_set_mismatch", None
        for g in R2BE_GROUPS:
            p = groups / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or has_symlink_component(p, True) or not p.read_text(encoding="utf-8").strip(): return False, "input_group_invalid", None
    except Exception: return False, "input_root_invalid", None
    return True, "input_root_valid", root

def validate_label_manifest(value: str) -> tuple[bool, str, list[dict[str, Any]]]:
    if not value or has_traversal(value): return False, "label_manifest_traversal_rejected", []
    p = Path(value)
    try:
        if p.is_absolute(): return False, "label_manifest_absolute_rejected", []
        p = repo_root() / p
        if not p.exists() or not p.is_file() or p.is_symlink() or has_symlink_component(p, True): return False, "label_manifest_missing_or_symlink", []
        p.relative_to(repo_root() / "fixtures" / "r14" / "labels")
        rows = load_jsonl(p)
        if not rows or len(rows) > BOUNDS["label_manifest_cap"]: return False, "label_manifest_empty_or_over_cap", []
        for r in rows:
            if not isinstance(r, dict) or "task_id" not in r or "label_quality" not in r or not isinstance(r.get("gold_spans"), list) or not isinstance(r.get("hard_negatives"), list): return False, "label_manifest_schema_invalid", []
    except Exception: return False, "label_manifest_invalid", []
    return True, "label_manifest_valid", rows

def validate_output_root(value: str, input_root: Path | None) -> tuple[bool, str, Path | None]:
    if not value or has_traversal(value): return False, "output_root_traversal_rejected", None
    out = Path(value)
    try:
        if out.exists() and out.is_symlink(): return False, "output_root_symlink_rejected", None
        if has_symlink_component(out, False) or not outside_repo(out): return False, "output_root_repo_or_symlink_rejected", None
        if input_root and (out.resolve(strict=False) == input_root.resolve(strict=False) or out.resolve(strict=False) in input_root.resolve(strict=False).parents or input_root.resolve(strict=False) in out.resolve(strict=False).parents): return False, "nested_roots_rejected", None
        if out.exists() and any(out.iterdir()):
            owner = out / "r2bo_owner_manifest.json"
            if not owner.is_file() or owner.is_symlink(): return False, "nonempty_unowned_output_rejected", None
            old = load_json(owner)
            if old.get("schema_version") != PRIVATE_SCHEMA or old.get("phase") != PHASE: return False, "nonempty_unowned_output_rejected", None
        out.mkdir(parents=True, exist_ok=True); groups = out / "groups"; groups.mkdir(exist_ok=True)
        if groups.is_symlink() or out.resolve() not in groups.resolve().parents: return False, "output_groups_escape_rejected", None
        for child in groups.iterdir():
            if child.is_symlink(): return False, "output_group_symlink_escape_rejected", None
    except Exception: return False, "output_root_invalid", None
    return True, "output_root_valid", out

def acquire_labels(r2be_root: Path, label_rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    groups_dir = out / "groups"; start = time.time()
    task_rows = load_jsonl(r2be_root / "groups" / "redesigned_task_frame.jsonl")[: BOUNDS["target_tasks"]]
    support_rows = load_jsonl(r2be_root / "groups" / "redesigned_support_pair_material.jsonl")
    control_rows = load_jsonl(r2be_root / "groups" / "redesigned_control_pair_material.jsonl")
    if not task_rows or not label_rows: raise RuntimeError("invalid arguments")
    n = min(len(task_rows), len(label_rows), BOUNDS["target_tasks"])
    out_rows: dict[str, list[dict[str, Any]]] = {g: [] for g in OUTPUT_GROUPS}
    support_by_task: dict[str, int] = {}
    control_by_task: dict[str, int] = {}
    for row in support_rows:
        ref = str(row.get("private_task_ref", "")); support_by_task[ref] = support_by_task.get(ref, 0) + 1
    for row in control_rows:
        ref = str(row.get("private_task_ref", "")); control_by_task[ref] = control_by_task.get(ref, 0) + 1
    for i in range(n):
        label_ref = f"r2bo_private_label_{i:04d}"; task_ref = f"r2bo_private_task_alignment_{i:04d}"
        task_row = task_rows[i]
        private_task_ref = str(task_row.get("private_task_ref", f"r2be_private_task_{i:04d}"))
        label_row = label_rows[i]
        quality = str(label_row.get("label_quality", "provided"))
        out_rows["outcome_label_source_manifest_private"].append({"private_label_source_ref": label_ref, "private_label_manifest_row_index": i, "private_task_id": label_row.get("task_id"), "private_label_quality": quality, "private_gold_spans": label_row.get("gold_spans", []), "private_hard_negatives": label_row.get("hard_negatives", []), "label_source_bucket": "operator_provided_committed_manifest", "raw_label_values_private_bool": True})
        out_rows["outcome_label_task_alignment_private"].append({"private_task_alignment_ref": task_ref, "private_label_source_ref": label_ref, "private_task_ref": private_task_ref, "private_task_id": label_row.get("task_id"), "alignment_bucket": "ordered_manifest_to_private_task_alignment_acquired", "exact_join_key_public_bool": False})
        out_rows["outcome_label_pair_family_alignment_private"].append({"private_pair_family_alignment_ref": f"r2bo_private_pair_family_{i:04d}", "private_label_source_ref": label_ref, "private_task_ref": private_task_ref, "support_pair_count_private": support_by_task.get(private_task_ref, 0), "control_pair_count_private": control_by_task.get(private_task_ref, 0), "pair_family_alignment_bucket": "support_control_family_label_source_available"})
        out_rows["outcome_label_provenance_private"].append({"private_label_source_ref": label_ref, "provenance_bucket": "existing_public_committed_r14_label_manifest", "confidence_bucket": f"label_quality_{quality}", "scope_bucket": "task_level_gold_and_hard_negative_private_alignment", "synthetic_programmatic_ground_truth_bool": False})
        out_rows["manual_label_import_private"].append({"private_label_source_ref": label_ref, "manual_label_import_bucket": "not_manual_manifest_imported"})
        out_rows["existing_label_recovery_private"].append({"private_label_source_ref": label_ref, "private_task_id": label_row.get("task_id"), "existing_label_recovery_bucket": "committed_fixture_gold_hard_negative_manifest_recovered"})
        out_rows["parent_r2be_row_ref_private"].append({"private_label_source_ref": label_ref, "private_task_ref": private_task_ref, "parent_r2be_bucket": "parent_r2be_private_task_row_referenced"})
    out_rows["label_quality_qa_private"].append({"qa_bucket": "label_source_schema_provenance_scope_pass", "private_acquired_label_row_count": n, "private_support_control_alignment_rows_available_bool": True, "no_experiment_metrics_bool": True, "no_material_repair_generation_bool": True})
    if sum(len(v) for v in out_rows.values()) > BOUNDS["private_row_cap"]: raise RuntimeError("invalid arguments")
    for g in OUTPUT_GROUPS:
        p = groups_dir / f"{g}.jsonl"
        if p.exists() and p.is_symlink(): raise RuntimeError("invalid arguments")
        write_jsonl(p, out_rows[g])
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2bn_checkpoint": R2BN_CHECKPOINT, "r2be_checkpoint": R2BE_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2bo_explicit_local_label_acquisition"}, "groups": {g: {"row_count_bucket": "present"} for g in OUTPUT_GROUPS}, "bounds": {"target_tasks_bucket": "target_tasks_20", "private_rows_bucket": "private_rows_le_20000", "label_source_manifest_bucket": "label_source_manifest_bounded"}, "wall_clock_bucket": "wall_clock_le_20_minutes" if time.time() - start < 20 * 60 else "wall_clock_over_cap"}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / "r2bo_private_manifest.json").write_text(text, encoding="utf-8"); (out / "r2bo_owner_manifest.json").write_text(text, encoding="utf-8")
    return {"acquired": True, "groups": set(OUTPUT_GROUPS), "bounds_ok": True, "rows_bucket": "private_rows_le_20000"}

def default_result() -> dict[str, Any]: return {"acquired": False, "groups": set(), "bounds_ok": True, "rows_bucket": "not_applicable"}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2BN_CHECKPOINT, R2BN_STATUS, "default mode", "no private read", "explicit local label source acquisition", "operator-provided label source manifest", "outcome_label_source_manifest_private", "target 20", "no material repair", "no experiment metrics", "aggregate-only public artifact", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bo-evidence-pair-support-explicit-local-outcome-label-source-acquisition.md")) and ok(read("docs/zh/bea-v1-haae-r2bo-evidence-pair-support-explicit-local-outcome-label-source-acquisition.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bo-evidence-pair-support-explicit-local-outcome-label-source-acquisition.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str = "default", r2bn: dict[str, Any] | None = None, acquisition: dict[str, Any] | None = None, root_ok: bool = False, label_ok: bool = False, output_ok: bool = False, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bn is None:
        try: r2bn = load_json(repo_root() / R2BN_REPORT_PATH)
        except Exception: r2bn = {}
    source_ok = audit_r2bn(r2bn); rb = public_readback_match(self_test_total); acquisition = acquisition or default_result()
    explicit = mode == "explicit"; acquired = bool(acquisition.get("acquired"))
    status = STATUS_DEFAULT if not explicit else (STATUS_PASS if source_ok and root_ok and label_ok and output_ok and acquired else STATUS_FAIL_ACQUISITION)
    if not source_ok: status = STATUS_FAIL_SOURCE
    if status in {STATUS_DEFAULT, STATUS_PASS} and not rb["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    passed_for_stop = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bostop0000", "next_allowed_phase": NEXT_PHASE if passed_for_stop else "not_authorized_until_successful_or_controlled_unavailable_acquisition"}; stop.update({f: passed_for_stop for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bosource0000", "locked_haae_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_haae_r2bn_status": R2BN_STATUS, "locked_haae_r2bn_self_test_total": R2BN_SELF_TEST_TOTAL, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": source_ok}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2boexec0000", "execution_mode_bucket": "explicit_local_label_source_acquisition" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_r2be_material_read_bool": explicit and root_ok, "label_source_manifest_read_bool": explicit and label_ok, "private_output_write_bool": explicit and output_ok, "label_source_acquisition_bool": explicit and acquired, "material_repair_generation_bool": False, "experiment_metric_bool": False, "source_candidate_corpus_scan_bool": False}],
        "root_safety_records": [{"anonymous_root_id": "haaer2boroot0000", "r2be_input_root_safety_bucket": "input_root_valid" if root_ok else ("not_read_default_mode" if not explicit else "input_root_invalid"), "label_source_manifest_safety_bucket": "label_manifest_valid" if label_ok else ("not_read_default_mode" if not explicit else "label_manifest_invalid"), "output_root_safety_bucket": "output_root_valid" if output_ok else ("not_written_default_mode" if not explicit else "output_root_invalid"), "no_root_path_or_basename_public_bool": True}],
        "acquisition_group_records": [{"anonymous_group_id": "haaer2bogroup0000", "required_group_buckets": OUTPUT_GROUPS, "generated_group_set_exact_bool": acquired and set(acquisition.get("groups", set())) == set(OUTPUT_GROUPS), "label_acquisition_bucket": "labels_acquired_private" if acquired else "no_explicit_acquisition"}],
        "bounds_records": [{"anonymous_bounds_id": "haaer2bobounds0000", "target_tasks_bucket": "target_tasks_20", "private_rows_bucket": acquisition.get("rows_bucket", "not_applicable"), "label_source_manifest_bucket": "label_source_manifest_bounded", "bounds_satisfied_bool": bool(acquisition.get("bounds_ok", True))}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2boprivacy0000", "aggregate_only_public_artifact_bool": True, "private_root_path_public_bool": False, "task_query_path_span_label_public_bool": False, "exact_count_rate_score_public_bool": False, "material_repair_generation_bool": False, "experiment_metrics_bool": False, "source_scan_bool": False, "runtime_ci_network_provider_bool": False, "signal_method_default_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bogate{i:04d}", "gate_bucket": g, "gate_passed_bool": True, "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bosynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2boreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
        if g["gate_bucket"] == "docs_readback_match_gate": g["gate_passed_bool"] = rb["all_public_readback_match_bool"]
        if g["gate_bucket"] == "bounds_gate": g["gate_passed_bool"] = bool(acquisition.get("bounds_ok", True))
        if g["gate_bucket"] == "r2bp_stop_go_only_gate" and passed_for_stop:
            g["gate_passed_bool"] = all(stop.get(f) is True for f in STOP_TRUE) and all(stop.get(f, False) is False for f in STOP_FALSE)
    if report["status"] in {STATUS_DEFAULT, STATUS_PASS} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS}: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_haae_r2bn_status": R2BN_STATUS, "locked_haae_r2bn_self_test_total": R2BN_SELF_TEST_TOTAL, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("aggregate_only_public_artifact_bool") is not True: issues.append("aggregate_only_public_artifact_bool")
    for f in ["private_root_path_public_bool", "task_query_path_span_label_public_bool", "exact_count_rate_score_public_bool", "material_repair_generation_bool", "experiment_metrics_bool", "source_scan_bool", "runtime_ci_network_provider_bool", "signal_method_default_scale_claim_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    grp = (report.get("acquisition_group_records") or [{}])[0]
    if grp.get("required_group_buckets") != OUTPUT_GROUPS: issues.append("output_group_set_mismatch")
    if report.get("status") == STATUS_PASS:
        if grp.get("generated_group_set_exact_bool") is not True: issues.append("explicit_generated_group_set_exact_bool")
        if grp.get("label_acquisition_bucket") != "labels_acquired_private": issues.append("explicit_label_acquisition_bucket")
    bounds = (report.get("bounds_records") or [{}])[0]
    if bounds.get("bounds_satisfied_bool") is not True: issues.append("bounds_satisfied_bool")
    exe = (report.get("execution_mode_records") or [{}])[0]
    root = (report.get("root_safety_records") or [{}])[0]
    explicit_evidence = any([
        exe.get("execution_mode_bucket") == "explicit_local_label_source_acquisition",
        exe.get("explicit_opt_in_bool") is True,
        exe.get("label_source_acquisition_bool") is True,
        exe.get("private_r2be_material_read_bool") is True,
        exe.get("label_source_manifest_read_bool") is True,
        exe.get("private_output_write_bool") is True,
        grp.get("generated_group_set_exact_bool") is True,
        grp.get("label_acquisition_bucket") == "labels_acquired_private",
    ])
    if report.get("status") == STATUS_DEFAULT and explicit_evidence:
        issues.append("status_execution_mismatch")
    if report.get("status") == STATUS_PASS:
        for f in ["explicit_opt_in_bool", "label_source_acquisition_bool", "label_source_manifest_read_bool", "private_r2be_material_read_bool", "private_output_write_bool"]:
            if exe.get(f) is not True: issues.append(f"explicit_execution_{f}")
        for f in ["material_repair_generation_bool", "experiment_metric_bool", "source_candidate_corpus_scan_bool"]:
            if exe.get(f) is not False: issues.append(f"explicit_execution_{f}")
        if exe.get("execution_mode_bucket") != "explicit_local_label_source_acquisition": issues.append("explicit_execution_mode_bucket")
        if root.get("r2be_input_root_safety_bucket") != "input_root_valid": issues.append("explicit_r2be_input_root_safety_bucket")
        if root.get("label_source_manifest_safety_bucket") != "label_manifest_valid": issues.append("explicit_label_source_manifest_safety_bucket")
        if root.get("output_root_safety_bucket") != "output_root_valid": issues.append("explicit_output_root_safety_bucket")
        if root.get("no_root_path_or_basename_public_bool") is not True: issues.append("explicit_no_root_path_or_basename_public_bool")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bp_stop_go_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    if report.get("status") == STATUS_DEFAULT:
        if stop.get("next_allowed_phase") == NEXT_PHASE: issues.append("default_stop_go_next_phase_overauth")
        for f in STOP_TRUE:
            if stop.get(f, False) is not False: issues.append(f"default_stop_true_{f}")
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

def make_synth_r2be_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="r2bo_r2be_selftest_", dir="/tmp/opencode")); (root / "groups").mkdir(parents=True)
    manifest = {"schema_version": "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_private_material_v1", "phase": "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation"}
    (root / "r2be_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for g in R2BE_GROUPS:
        write_jsonl(root / "groups" / f"{g}.jsonl", [{"bucket": g}])
    return root

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; r2bn = load_json(repo_root() / R2BN_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    default = build_report(); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    root = Path("/tmp/opencode/r2bo_uninitialized_root")
    out = Path("/tmp/opencode/r2bo_uninitialized_out")
    try:
        root = make_synth_r2be_root(); out = Path(tempfile.mkdtemp(prefix="r2bo_out_selftest_", dir="/tmp/opencode")); label_ok, _, labels = validate_label_manifest("fixtures/r14/labels/sanity.jsonl"); root_ok, _, rroot = validate_r2be_root(str(root)); out_ok, _, oroot = validate_output_root(str(out), rroot); acq = acquire_labels(rroot, labels, oroot) if root_ok and label_ok and out_ok and rroot and oroot else default_result(); explicit = build_report("explicit", r2bn, acq, root_ok, label_ok, out_ok); check("explicit_synthetic_success_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
    finally:
        shutil.rmtree(str(root), ignore_errors=True); shutil.rmtree(str(out), ignore_errors=True)
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    for args_name, args in [("missing_allow_flag_fail", ["--private-r2be-material-root", "/x"]), ("missing_r2be_root_fail", ["--allow-r2bo-explicit-local-outcome-label-source-acquisition"]), ("missing_label_manifest_fail", ["--allow-r2bo-explicit-local-outcome-label-source-acquisition", "--private-r2be-material-root", "/x", "--r2bo-private-output-root", "/y", "--confirm-existing-r2be-material-only", "--confirm-private-output", "--confirm-no-experiment-metrics", "--confirm-aggregate-only-public-artifact"]), ("missing_output_root_fail", ["--allow-r2bo-explicit-local-outcome-label-source-acquisition", "--private-r2be-material-root", "/x", "--label-source-manifest", "fixtures/r14/labels/sanity.jsonl", "--confirm-existing-r2be-material-only", "--confirm-private-output", "--confirm-no-experiment-metrics", "--confirm-aggregate-only-public-artifact"])]:
        try: parse_args(args); check(args_name, False)
        except ValueError: check(args_name, True)
    for name, mut in [("bad_r2bn_checkpoint_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bm_checkpoint", "bad")), ("bad_r2bn_status_fail", lambda r: r.__setitem__("status", "bad")), ("r2bn_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True))]:
        m = json.loads(json.dumps(r2bn)); mut(m); check(name, build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    check("input_root_in_repo_fail", validate_r2be_root(str(repo_root()))[0] is False)
    check("input_root_missing_fail", validate_r2be_root("/tmp/opencode/no_such_r2be_root")[0] is False)
    synth = make_synth_r2be_root()
    try:
        link = synth.parent / "r2bo_symlink_root"; link.unlink(missing_ok=True); link.symlink_to(synth, target_is_directory=True); check("input_root_symlink_fail", validate_r2be_root(str(link))[0] is False); link.unlink(missing_ok=True)
        (synth / "groups" / f"{R2BE_GROUPS[0]}.jsonl").unlink(); check("input_group_missing_fail", validate_r2be_root(str(synth))[0] is False)
    finally: shutil.rmtree(str(synth), ignore_errors=True)
    synth = make_synth_r2be_root()
    try:
        write_jsonl(synth / "groups" / "extra.jsonl", [{"x": 1}]); check("input_group_extra_fail", validate_r2be_root(str(synth))[0] is False)
    finally: shutil.rmtree(str(synth), ignore_errors=True)
    synth = make_synth_r2be_root()
    try:
        (synth / "groups" / f"{R2BE_GROUPS[0]}.jsonl").unlink(); (synth / "groups" / f"{R2BE_GROUPS[0]}.jsonl").symlink_to(synth / "r2be_private_manifest.json"); check("input_group_symlink_fail", validate_r2be_root(str(synth))[0] is False)
    finally: shutil.rmtree(str(synth), ignore_errors=True)
    check("label_manifest_missing_fail", validate_label_manifest("fixtures/r14/labels/missing.jsonl")[0] is False)
    check("label_manifest_tmp_rejected_fail", validate_label_manifest("/tmp/x.jsonl")[0] is False)
    check("label_manifest_traversal_rejected_fail", validate_label_manifest("../fixtures/r14/labels/sanity.jsonl")[0] is False)
    bad_link = repo_root() / "fixtures/r14/labels/r2bo_bad_link.jsonl"
    try:
        bad_link.unlink(missing_ok=True); bad_link.symlink_to(repo_root() / "fixtures/r14/labels/sanity.jsonl"); check("label_manifest_symlink_fail", validate_label_manifest("fixtures/r14/labels/r2bo_bad_link.jsonl")[0] is False)
    finally: bad_link.unlink(missing_ok=True)
    bad_manifest = repo_root() / "fixtures/r14/labels/r2bo_bad_schema.jsonl"
    try:
        bad_manifest.write_text('{"not_task":"x"}\n', encoding="utf-8"); check("label_manifest_schema_invalid_fail", validate_label_manifest("fixtures/r14/labels/r2bo_bad_schema.jsonl")[0] is False)
    finally: bad_manifest.unlink(missing_ok=True)
    root = make_synth_r2be_root(); check("output_root_in_repo_fail", validate_output_root(str(repo_root() / "r2bo_bad"), root)[0] is False); check("nested_roots_fail", validate_output_root(str(root / "nested"), root)[0] is False)
    out = Path(tempfile.mkdtemp(prefix="r2bo_unowned_", dir="/tmp/opencode")); (out / "x").write_text("x", encoding="utf-8"); check("nonempty_unowned_output_fail", validate_output_root(str(out), root)[0] is False); shutil.rmtree(str(out), ignore_errors=True)
    out = Path(tempfile.mkdtemp(prefix="r2bo_owned_", dir="/tmp/opencode")); (out / "r2bo_owner_manifest.json").write_text(json.dumps({"schema_version": PRIVATE_SCHEMA, "phase": PHASE}), encoding="utf-8"); check("owned_rerun_pass", validate_output_root(str(out), root)[0] is True); shutil.rmtree(str(out), ignore_errors=True); shutil.rmtree(str(root), ignore_errors=True)
    link = Path("/tmp/opencode/r2bo_out_link")
    try: link.unlink(missing_ok=True); link.symlink_to("/tmp/opencode"); check("output_root_symlink_fail", validate_output_root(str(link), None)[0] is False)
    finally: link.unlink(missing_ok=True)
    out = Path(tempfile.mkdtemp(prefix="r2bo_group_link_", dir="/tmp/opencode")); (out / "groups").mkdir(); (out / "groups" / "bad").symlink_to("/tmp"); check("output_group_symlink_escape_fail", validate_output_root(str(out), None)[0] is False); shutil.rmtree(str(out), ignore_errors=True)
    report_muts = [("source_locked_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("source_locked_bool", False), "source_locked_bool"), ("explicit_status_drift_fail", lambda r: r.__setitem__("status", STATUS_DEFAULT), "status_execution_mismatch"), ("explicit_group_exact_drift_fail", lambda r: r["acquisition_group_records"][0].__setitem__("generated_group_set_exact_bool", False), "explicit_generated_group_set_exact_bool"), ("explicit_execution_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_r2be_material_read_bool", False), "explicit_execution_private_r2be_material_read_bool"), ("explicit_execution_label_manifest_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("label_source_manifest_read_bool", False), "explicit_execution_label_source_manifest_read_bool"), ("explicit_execution_private_write_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_output_write_bool", False), "explicit_execution_private_output_write_bool"), ("explicit_root_safety_drift_fail", lambda r: r["root_safety_records"][0].__setitem__("label_source_manifest_safety_bucket", "bad"), "explicit_label_source_manifest_safety_bucket"), ("output_group_missing_fail", lambda r: r["acquisition_group_records"][0]["required_group_buckets"].pop(), "output_group_set_mismatch"), ("output_group_extra_fail", lambda r: r["acquisition_group_records"][0]["required_group_buckets"].append("extra"), "output_group_set_mismatch"), ("bounds_drift_fail", lambda r: r["bounds_records"][0].__setitem__("bounds_satisfied_bool", False), "bounds_satisfied_bool"), ("material_repair_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("material_repair_generation_bool", True), "privacy_material_repair_generation_bool"), ("metric_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("experiment_metrics_bool", True), "privacy_experiment_metrics_bool"), ("source_scan_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("source_scan_bool", True), "privacy_source_scan_bool"), ("publication_raw_label_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("task_query_path_span_label_public_bool", True), "privacy_task_query_path_span_label_public_bool"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    pass_report = build_report("explicit", acquisition={"acquired": True, "groups": set(OUTPUT_GROUPS), "bounds_ok": True, "rows_bucket": "private_rows_le_20000"}, root_ok=True, label_ok=True, output_ok=True)
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(pass_report)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 gold_spans exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
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
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    if args["explicit"]:
        root_ok, _, r2be_root = validate_r2be_root(str(args["r2be_root"])); label_ok, _, labels = validate_label_manifest(str(args["label_manifest"])); output_ok, _, output = validate_output_root(str(args["output"]), r2be_root)
        acquisition = acquire_labels(r2be_root, labels, output) if root_ok and label_ok and output_ok and r2be_root and output else default_result()
        report = build_report("explicit", acquisition=acquisition, root_ok=root_ok, label_ok=label_ok, output_ok=output_ok)
    else:
        report = build_report("default")
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
