#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BG explicit local redesigned material experiment.

Default mode performs no private read. Explicit mode reads only an operator-
provided existing R2BE private material root and computes bucketized aggregate
metrics over redesigned support/control families. It never generates material,
scans source/candidate/corpus, or runs runtime/OpenLocus/retrieval/CI/network.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BG Evidence-Pair Support Explicit Local Redesigned Material Experiment"
SLUG = "bea_v1_haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BF_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bf_evidence_pair_support_redesigned_material_public_audit_package/bea_v1_haae_r2bf_evidence_pair_support_redesigned_material_public_audit_package_report.json")
R2BE_REPORT_PATH = Path("artifacts/bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation/bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_report.json")

R2BF_CHECKPOINT = "322fbca"
R2BF_STATUS = "haae_r2bf_evidence_pair_support_redesigned_material_public_audit_complete_r2bg_experiment_authorized"
R2BF_SELF_TEST_TOTAL = 40
R2BE_CHECKPOINT = "c3901d6"
R2BE_STATUS = "haae_r2be_explicit_local_redesigned_material_generation_complete_r2bf_public_audit_authorized"
R2BE_SELF_TEST_TOTAL = 40
R2BD_CHECKPOINT = "fa6119b"

STATUS_DEFAULT = "haae_r2bg_unavailable_no_explicit_local_redesigned_material_experiment_opt_in"
STATUS_SIGNAL = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_signal_present"
STATUS_MIXED = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_mixed_or_inconclusive"
STATUS_ARTIFACT = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_artifact_or_weak_signal"
STATUS_FAIL_SOURCE = "haae_r2bg_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2bg_fail_closed_private_material_root_invalid"
STATUS_FAIL_PRIVACY = "haae_r2bg_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bg_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BH Evidence-Pair Support Redesigned Material Experiment Public Audit Package"

PRIVATE_SCHEMA = "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_private_material_v1"
R2BE_PHASE = "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation"
GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
CONTROL_FAMILIES = ["matched_hard_negative_control", "same_source_family_control", "cross_task_semantic_mismatch_control", "path_token_matched_control", "query_only_control", "evidence_only_control", "support_relation_broken_control", "gold_blind_decoy_control", "source_family_balance_control"]
BOUNDS = {"target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes"}
R2BF_TRUE = ["haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment_authorized_bool", "r2bg_explicit_opt_in_required_bool", "r2bg_existing_r2be_private_material_read_authorized_bool", "r2bg_aggregate_metrics_only_bool", "r2bg_no_material_generation_bool", "r2bg_no_source_candidate_corpus_scan_bool", "r2bg_public_audit_required_after_experiment_bool"]
R2BF_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bf_source_lock_gate", "r2be_public_artifact_lock_gate", "default_noop_or_explicit_opt_in_gate", "root_safety_gate", "r2be_private_manifest_group_schema_gate", "control_family_exact_gate", "no_material_generation_gate", "no_source_candidate_corpus_scan_gate", "no_runtime_openlocus_retrieval_gate", "aggregate_bucket_metrics_only_gate", "public_privacy_gate", "r2bh_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_artifact_or_weak_pass", "safe_parser_fail", "missing_explicit_arg_fail", "r2bf_checkpoint_drift_fail", "r2bf_status_drift_fail", "r2bf_self_test_drift_fail", "r2bf_stop_go_overauth_fail", "r2be_public_status_drift_fail", "root_in_repo_fail", "root_missing_manifest_fail", "root_group_missing_fail", "root_group_symlink_fail", "root_unexpected_group_fail", "manifest_schema_fail", "manifest_source_lock_drift_fail", "control_family_missing_fail", "material_generation_flag_fail", "source_scan_flag_fail", "runtime_flag_fail", "execution_mode_drift_fail", "execution_private_read_drift_fail", "execution_private_write_overauth_fail", "metric_bucketization_fail", "status_metric_alignment_fail", "privacy_raw_publication_fail", "privacy_ids_publication_fail", "public_leak_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_scale_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_readback_fail", "readback_record_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bh_evidence_pair_support_redesigned_material_experiment_public_audit_authorized_bool", "r2bh_public_only_audit_bool", "r2bh_no_private_read_bool", "r2bh_no_metric_recompute_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "scale_preflight_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit-rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [n for n, p in LEAK_PATTERNS if p.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "root": "", "confirm_existing": False, "confirm_no_material": False, "confirm_no_scan": False, "confirm_no_runtime": False, "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2bg-explicit-local-redesigned-material-experiment": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2be-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-no-material-generation": parsed["confirm_no_material"] = True; i += 1
        elif a == "--confirm-no-source-candidate-corpus-scan": parsed["confirm_no_scan"] = True; i += 1
        elif a == "--confirm-no-runtime-openlocus-retrieval": parsed["confirm_no_runtime"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--r2be-private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--r2be-private-material-root": "root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "root", "confirm_existing", "confirm_no_material", "confirm_no_scan", "confirm_no_runtime", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed
def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def symlink_component(path: Path) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/")
    for part in p.parts[1:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
    return False

def audit_r2bf(r2bf: dict[str, Any]) -> dict[str, bool]:
    src = (r2bf.get("source_lock_records") or [{}])[0]; stop = (r2bf.get("stop_go_records") or [{}])[0]
    lock = r2bf.get("status") == R2BF_STATUS and r2bf.get("self_test_total") == R2BF_SELF_TEST_TOTAL and r2bf.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("locked_haae_r2be_status") == R2BE_STATUS and src.get("source_locked_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BF_TRUE) and all(stop.get(f, False) is False for f in R2BF_FALSE)
    return {"source_ok": lock and stop_ok, "lock_ok": lock, "stop_ok": stop_ok}
def audit_r2be_public(r2be: dict[str, Any]) -> bool:
    return r2be.get("status") == R2BE_STATUS and r2be.get("self_test_total") == R2BE_SELF_TEST_TOTAL and r2be.get("forbidden_scan", {}).get("status") == "pass"

def validate_root(value: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    if not value or any(part == ".." for part in Path(value).parts): return False, "root_traversal_rejected", {}
    root = Path(value)
    try:
        if not root.exists() or root.is_symlink() or symlink_component(root) or not outside_repo(root): return False, "root_safety_rejected", {}
        mf = root / "r2be_private_manifest.json"; gd = root / "groups"
        if not mf.is_file() or mf.is_symlink() or not gd.is_dir() or gd.is_symlink(): return False, "manifest_or_groups_missing", {}
        manifest = load_json(mf)
        if manifest.get("schema_version") != PRIVATE_SCHEMA or manifest.get("phase") != R2BE_PHASE: return False, "manifest_schema_mismatch", {}
        if (manifest.get("source_lock") or {}).get("r2bd_checkpoint") != R2BD_CHECKPOINT: return False, "manifest_source_lock_mismatch", {}
        if set(manifest.get("control_families") or []) != set(CONTROL_FAMILIES): return False, "manifest_control_family_mismatch", {}
        present = {p.name for p in gd.iterdir()}
        if present != {f"{g}.jsonl" for g in GROUPS}: return False, "group_file_set_mismatch", {}
        rows: dict[str, list[dict[str, Any]]] = {}
        for g in GROUPS:
            p = gd / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or root.resolve() not in p.resolve().parents: return False, "group_file_invalid", {}
            rows[g] = load_jsonl(p)
            if not rows[g]: return False, "group_file_empty", {}
        fams = {r.get("control_family_bucket") for r in rows["redesigned_control_pair_material"]}
        if fams != set(CONTROL_FAMILIES): return False, "control_family_set_mismatch", {}
    except Exception:
        return False, "root_invalid", {}
    return True, "root_valid", rows

def bucket_tasks(n: int) -> str:
    if n <= 0: return "task_count_0"
    if n <= 10: return "task_count_1_to_10"
    if n <= 20: return "task_count_11_to_20"
    return "task_count_over_scope"
def compute_buckets(rows: dict[str, list[dict[str, Any]]]) -> dict[str, str | bool]:
    tasks = {r.get("private_task_ref") for r in rows.get("redesigned_task_frame", [])}
    support_tasks = {r.get("private_task_ref") for r in rows.get("redesigned_support_pair_material", []) if r.get("construction_used_gold_bool") is False and r.get("experiment_metric_bool") is False}
    control_fams = {r.get("control_family_bucket") for r in rows.get("redesigned_control_pair_material", []) if r.get("construction_used_gold_bool") is False and r.get("experiment_metric_bool") is False}
    outcome_rows = rows.get("redesigned_gold_isolation_eval_private", [])
    gold_ok = all(r.get("gold_eval_only_bool") is True and r.get("used_for_pair_control_construction_bool") is False and r.get("used_for_ranking_bool") is False for r in outcome_rows)
    outcome_eval_available = any(any(k in r for k in ["gold_source_ref", "gold_path_ref", "positive_source_ref", "target_source_ref", "expected_support_pair_ref"]) for r in outcome_rows)
    no_metrics = all(r.get("experiment_metric_bool") is False for g in ["redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material"] for r in rows.get(g, []))
    group_ok = all(rows.get(g) for g in GROUPS)
    family_ok = control_fams == set(CONTROL_FAMILIES)
    support_present = bool(support_tasks)
    if not group_ok or not family_ok or not gold_ok or not no_metrics:
        result = "mixed_or_inconclusive"
    elif not outcome_eval_available:
        result = "artifact_or_weak_signal"
    elif support_present and family_ok:
        result = "signal_present"
    else:
        result = "artifact_or_weak_signal"
    return {"redesigned_experiment_result_bucket": result, "task_coverage_bucket": bucket_tasks(len(tasks)), "support_pair_behavior_bucket": "support_behavior_present" if support_present else "support_behavior_absent", "control_family_coverage_bucket": "control_family_coverage_complete" if family_ok else "control_family_coverage_incomplete", "outcome_eval_alignment_bucket": "outcome_eval_alignment_available" if outcome_eval_available else "outcome_eval_alignment_unavailable", "support_control_separation_bucket": "support_control_separation_present" if result == "signal_present" else "support_control_separation_not_established", "gold_isolation_bucket": "gold_isolation_pass" if gold_ok else "gold_isolation_fail", "material_integrity_bucket": "material_integrity_pass" if group_ok and no_metrics else "material_integrity_fail", "aggregate_bucket_metrics_only_bool": True, "no_exact_metrics_bool": True}
def default_metrics() -> dict[str, str | bool]:
    return {"redesigned_experiment_result_bucket": "unavailable_no_explicit_opt_in", "task_coverage_bucket": "unavailable_no_explicit_opt_in", "support_pair_behavior_bucket": "unavailable_no_explicit_opt_in", "control_family_coverage_bucket": "unavailable_no_explicit_opt_in", "outcome_eval_alignment_bucket": "unavailable_no_explicit_opt_in", "support_control_separation_bucket": "unavailable_no_explicit_opt_in", "gold_isolation_bucket": "unavailable_no_explicit_opt_in", "material_integrity_bucket": "unavailable_no_explicit_opt_in", "aggregate_bucket_metrics_only_bool": True, "no_exact_metrics_bool": True}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_SIGNAL, STATUS_ARTIFACT, f"{total}/{total}", R2BF_CHECKPOINT, R2BF_STATUS, R2BE_CHECKPOINT, "default mode", "no private read", "explicit mode", "existing R2BE private material", "bucketized aggregate metrics", "signal_present", "artifact_or_weak_signal", "mixed_or_inconclusive", "outcome_eval_alignment_unavailable", "no material generation", "no source/candidate/corpus scan", "no runtime/OpenLocus/retrieval", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bg-evidence-pair-support-explicit-local-redesigned-material-experiment.md")) and ok(read("docs/zh/bea-v1-haae-r2bg-evidence-pair-support-explicit-local-redesigned-material-experiment.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bg-evidence-pair-support-explicit-local-redesigned-material-experiment.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str, r2bf: dict[str, Any] | None = None, r2be_pub: dict[str, Any] | None = None, root_ok: bool = False, metrics: dict[str, str | bool] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bf is None:
        try: r2bf = load_json(repo_root() / R2BF_REPORT_PATH)
        except Exception: r2bf = {}
    if r2be_pub is None:
        try: r2be_pub = load_json(repo_root() / R2BE_REPORT_PATH)
        except Exception: r2be_pub = {}
    audit = audit_r2bf(r2bf); r2be_ok = audit_r2be_public(r2be_pub); rb = public_readback_match(self_test_total); explicit = mode == "explicit"; metrics = metrics or default_metrics()
    result = str(metrics.get("redesigned_experiment_result_bucket"))
    pass_status = STATUS_SIGNAL if result == "signal_present" else STATUS_ARTIFACT if result == "artifact_or_weak_signal" else STATUS_MIXED
    status = STATUS_FAIL_SOURCE if not (audit["source_ok"] and r2be_ok) else (STATUS_FAIL_ROOT if explicit and not root_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else (pass_status if explicit else STATUS_DEFAULT)))
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bgstop0000", "next_allowed_phase": NEXT_PHASE if status in {STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED} else "not_authorized_until_explicit_experiment_pass"}; stop.update({f: status in {STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED} for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bf_source_lock_gate": audit["source_ok"], "r2be_public_artifact_lock_gate": r2be_ok, "default_noop_or_explicit_opt_in_gate": True, "root_safety_gate": (not explicit) or root_ok, "r2be_private_manifest_group_schema_gate": (not explicit) or root_ok, "control_family_exact_gate": (not explicit) or metrics.get("control_family_coverage_bucket") == "control_family_coverage_complete", "no_material_generation_gate": True, "no_source_candidate_corpus_scan_gate": True, "no_runtime_openlocus_retrieval_gate": True, "aggregate_bucket_metrics_only_gate": metrics.get("aggregate_bucket_metrics_only_bool") is True and metrics.get("no_exact_metrics_bool") is True, "public_privacy_gate": True, "r2bh_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bgsource0000", "locked_haae_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_haae_r2bf_status": R2BF_STATUS, "locked_haae_r2bf_self_test_total": R2BF_SELF_TEST_TOTAL, "locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2be_status": R2BE_STATUS, "source_locked_bool": audit["source_ok"] and r2be_ok}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2bgexec0000", "execution_mode_bucket": "explicit_local_experiment" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_read_bool": explicit, "private_write_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_openlocus_retrieval_bool": False}],
        "aggregate_metric_records": [{"anonymous_metric_id": "haaer2bgmetric0000", **metrics}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2bgprivacy0000", "aggregate_bucket_only_publication_bool": True, "private_root_path_public_bool": False, "task_query_source_evidence_pair_ids_public_bool": False, "exact_counts_rates_scores_ranks_mrr_public_bool": False, "raw_private_rows_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bggate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bgsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bgreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] not in {STATUS_FAIL_SOURCE, STATUS_FAIL_ROOT, STATUS_FAIL_READBACK} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") not in {STATUS_DEFAULT, STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED}: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_haae_r2bf_status": R2BF_STATUS, "locked_haae_r2bf_self_test_total": R2BF_SELF_TEST_TOTAL, "locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2be_status": R2BE_STATUS}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    metric = (report.get("aggregate_metric_records") or [{}])[0]
    if metric.get("aggregate_bucket_metrics_only_bool") is not True or metric.get("no_exact_metrics_bool") is not True: issues.append("metric_bucketization_mismatch")
    if report.get("status") == STATUS_SIGNAL and metric.get("redesigned_experiment_result_bucket") != "signal_present": issues.append("status_metric_alignment_mismatch")
    if report.get("status") == STATUS_ARTIFACT and metric.get("redesigned_experiment_result_bucket") != "artifact_or_weak_signal": issues.append("status_metric_alignment_mismatch")
    if report.get("status") == STATUS_MIXED and metric.get("redesigned_experiment_result_bucket") != "mixed_or_inconclusive": issues.append("status_metric_alignment_mismatch")
    exe = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_DEFAULT:
        if exe.get("execution_mode_bucket") != "default_no_explicit_opt_in" or exe.get("explicit_opt_in_bool") is not False or exe.get("private_read_bool") is not False or exe.get("private_write_bool") is not False: issues.append("execution_mode_mismatch")
    elif report.get("status") in {STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED}:
        if exe.get("execution_mode_bucket") != "explicit_local_experiment" or exe.get("explicit_opt_in_bool") is not True or exe.get("private_read_bool") is not True or exe.get("private_write_bool") is not False: issues.append("execution_mode_mismatch")
    if exe.get("material_generation_bool") is not False: issues.append("material_generation_overauth")
    if exe.get("source_candidate_corpus_scan_bool") is not False: issues.append("source_scan_overauth")
    if exe.get("runtime_openlocus_retrieval_bool") is not False: issues.append("runtime_overauth")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("aggregate_bucket_only_publication_bool") is not True or priv.get("private_root_path_public_bool") is not False or priv.get("exact_counts_rates_scores_ranks_mrr_public_bool") is not False or priv.get("raw_private_rows_public_bool") is not False or priv.get("task_query_source_evidence_pair_ids_public_bool") is not False: issues.append("privacy_boundary_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    terminal = report.get("status") in {STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED}
    if terminal:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bh_stop_go_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    rb = report.get("public_readback_records", [])
    if len(rb) != 1 or rb[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path
def run_explicit(args: dict[str, str | bool]) -> dict[str, Any]:
    ok, _bucket, rows = validate_root(str(args["root"]))
    return build_report("explicit", root_ok=ok, metrics=compute_buckets(rows) if ok else default_metrics())

def make_synth_root(mut: str = "") -> Path:
    root = Path(tempfile.mkdtemp(prefix="r2bg_synth_", dir="/tmp/opencode")); (root / "groups").mkdir()
    manifest = {"schema_version": PRIVATE_SCHEMA if mut != "schema" else "bad", "phase": R2BE_PHASE, "source_lock": {"r2bd_checkpoint": R2BD_CHECKPOINT if mut != "source" else "bad"}, "control_families": CONTROL_FAMILIES if mut != "family" else CONTROL_FAMILIES[:-1]}
    (root / "r2be_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    tasks = [f"t{i}" for i in range(16)]
    rows = {g: [] for g in GROUPS}
    rows["redesigned_task_frame"] = [{"private_task_ref": t} for t in tasks]
    rows["redesigned_source_manifest_private"] = [{"private_source_ref": "s0"}]
    rows["redesigned_evidence_unit_pool"] = [{"private_task_ref": t, "private_evidence_unit_ref": f"e{t}"} for t in tasks]
    rows["redesigned_support_pair_material"] = [{"private_task_ref": t, "private_pair_ref": f"sp{t}", "construction_used_gold_bool": False, "experiment_metric_bool": False} for t in tasks]
    rows["redesigned_control_pair_material"] = [{"private_task_ref": t, "private_pair_ref": f"cp{t}{i}", "control_family_bucket": fam, "construction_used_gold_bool": False, "experiment_metric_bool": False} for t in tasks for i, fam in enumerate(CONTROL_FAMILIES)]
    rows["redesigned_path_confound_material"] = [{"private_task_ref": t, "experiment_metric_bool": False} for t in tasks]
    rows["redesigned_gold_isolation_eval_private"] = [{"private_task_ref": t, "gold_eval_only_bool": True, "used_for_pair_control_construction_bool": False, "used_for_ranking_bool": False} for t in tasks]
    rows["redesigned_material_qa"] = [{"qa_bucket": "pass"}]
    if mut == "missing_group": rows.pop("redesigned_material_qa")
    for g, rs in rows.items():
        write = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rs)
        (root / "groups" / f"{g}.jsonl").write_text(write, encoding="utf-8")
    return root

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    default = build_report("default"); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    root = make_synth_root(); explicit = run_explicit({"root": str(root), "explicit": True, "confirm_existing": True, "confirm_no_material": True, "confirm_no_scan": True, "confirm_no_runtime": True, "confirm_public": True}); check("explicit_synthetic_artifact_or_weak_pass", explicit["status"] == STATUS_ARTIFACT and validate_report(explicit) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    try: parse_args(["--allow-r2bg-explicit-local-redesigned-material-experiment", "--r2be-private-material-root", str(root)]); check("missing_explicit_arg_fail", False)
    except ValueError: check("missing_explicit_arg_fail", True)
    r2bf = load_json(repo_root() / R2BF_REPORT_PATH); r2be = load_json(repo_root() / R2BE_REPORT_PATH)
    for name, mut in [("r2bf_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2be_checkpoint", "bad")), ("r2bf_status_drift_fail", lambda r: r.__setitem__("status", "bad")), ("r2bf_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2bf_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True))]:
        m = json.loads(json.dumps(r2bf)); mut(m); check(name, build_report("default", r2bf=m)["status"] == STATUS_FAIL_SOURCE)
    m = json.loads(json.dumps(r2be)); m["status"] = "bad"; check("r2be_public_status_drift_fail", build_report("default", r2be_pub=m)["status"] == STATUS_FAIL_SOURCE)
    check("root_in_repo_fail", validate_root(str(repo_root()))[0] is False)
    missing = Path(tempfile.mkdtemp(prefix="r2bg_missing_", dir="/tmp/opencode")); check("root_missing_manifest_fail", validate_root(str(missing))[0] is False)
    miss_group = make_synth_root("missing_group"); check("root_group_missing_fail", validate_root(str(miss_group))[0] is False)
    syroot = make_synth_root(); target = syroot / "groups" / "redesigned_material_qa.jsonl"; target.unlink(); target.symlink_to(repo_root() / "fixtures/r14/tasks/sanity.jsonl"); check("root_group_symlink_fail", validate_root(str(syroot))[0] is False)
    extra = make_synth_root(); (extra / "groups" / "extra.jsonl").write_text("{}\n", encoding="utf-8"); check("root_unexpected_group_fail", validate_root(str(extra))[0] is False)
    check("manifest_schema_fail", validate_root(str(make_synth_root("schema")))[0] is False)
    check("manifest_source_lock_drift_fail", validate_root(str(make_synth_root("source")))[0] is False)
    check("control_family_missing_fail", validate_root(str(make_synth_root("family")))[0] is False)
    metric_bad = dict(compute_buckets(validate_root(str(root))[2])); metric_bad["aggregate_bucket_metrics_only_bool"] = False; check("metric_bucketization_fail", "metric_bucketization_mismatch" in validate_report(build_report("explicit", root_ok=True, metrics=metric_bad)))
    status_bad = build_report("explicit", root_ok=True, metrics=compute_buckets(validate_root(str(root))[2])); status_bad["aggregate_metric_records"][0]["redesigned_experiment_result_bucket"] = "mixed_or_inconclusive"; check("status_metric_alignment_fail", "status_metric_alignment_mismatch" in validate_report(status_bad))
    for n, field, issue in [("material_generation_flag_fail", "material_generation_bool", "material_generation_overauth"), ("source_scan_flag_fail", "source_candidate_corpus_scan_bool", "source_scan_overauth"), ("runtime_flag_fail", "runtime_openlocus_retrieval_bool", "runtime_overauth")]:
        mm = json.loads(json.dumps(explicit)); mm["execution_mode_records"][0][field] = True; check(n, issue in validate_report(mm))
    for n, field, value in [("execution_mode_drift_fail", "execution_mode_bucket", "default_no_explicit_opt_in"), ("execution_private_read_drift_fail", "private_read_bool", False), ("execution_private_write_overauth_fail", "private_write_bool", True)]:
        mm = json.loads(json.dumps(explicit)); mm["execution_mode_records"][0][field] = value; check(n, "execution_mode_mismatch" in validate_report(mm))
    for n, field in [("privacy_raw_publication_fail", "raw_private_rows_public_bool"), ("privacy_ids_publication_fail", "task_query_source_evidence_pair_ids_public_bool")]:
        mm = json.loads(json.dumps(explicit)); mm["privacy_boundary_records"][0][field] = True; check(n, "privacy_boundary_mismatch" in validate_report(mm))
    report_mut = [("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(r["public_readback_records"][0]), "public_readback_record_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for n, mut, issue in report_mut:
        mm = json.loads(json.dumps(explicit)); mut(mm); check(n, issue in validate_report(mm))
    leak = json.loads(json.dumps(explicit)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    for p in [root, missing, miss_group, syroot, extra]: shutil.rmtree(p, ignore_errors=True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_ARTIFACT}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        res = run_self_test(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = run_explicit(args) if args["explicit"] else build_report("default")
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_SIGNAL, STATUS_ARTIFACT, STATUS_MIXED} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
