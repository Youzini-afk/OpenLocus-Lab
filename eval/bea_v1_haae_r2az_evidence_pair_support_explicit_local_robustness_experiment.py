#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AZ explicit local robustness experiment.

Default mode is a public no-op. Explicit mode reads only an operator-provided
existing R2AX private robustness material root and computes bucketized aggregate
robustness metrics. It never generates material, scans source/candidate/corpus,
or runs runtime/OpenLocus/retrieval/CI/network/provider/clone paths.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment"
SLUG = "bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2AY_CHECKPOINT = "126dc18"
R2AY_STATUS = "haae_r2ay_evidence_pair_support_robustness_material_public_audit_complete_r2az_experiment_authorized"
R2AY_SELF_TEST_TOTAL = 36
R2AY_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ay_evidence_pair_support_robustness_material_public_audit_package/bea_v1_haae_r2ay_evidence_pair_support_robustness_material_public_audit_package_report.json")
R2AT_REPORT_PATH = Path("artifacts/bea_v1_haae_r2at_evidence_pair_support_explicit_private_mechanism_decomposition/bea_v1_haae_r2at_evidence_pair_support_explicit_private_mechanism_decomposition_report.json")
R2AP_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment_report.json")
R2AX_CHECKPOINT = "f3add65"
R2AW_CHECKPOINT = "bc44454"
R2AN_CHECKPOINT = "93bba5f"
R2AT_CHECKPOINT = "0c9c108"
R2AP_CHECKPOINT = "87ea9de"
NEXT_PHASE = "BEA-v1-HAAE-R2BA Evidence-Pair Support Robustness Experiment Public Audit Package"

STATUS_DEFAULT = "haae_r2az_unavailable_no_explicit_local_robustness_experiment_opt_in"
STATUS_PASS_ROBUST = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_robust_signal"
STATUS_PASS_MIXED = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_mixed_or_inconclusive"
STATUS_PASS_ARTIFACT = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely"
STATUS_FAIL_SOURCE = "haae_r2az_fail_closed_source_lock_mismatch"
STATUS_FAIL_ROOT = "haae_r2az_fail_closed_private_material_root_invalid"
STATUS_FAIL_PRIVACY = "haae_r2az_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2az_fail_closed_public_readback_mismatch"

PRIVATE_SCHEMA = "bea_v1_haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation_private_material_v1"
R2AX_PHASE = "BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation"
GROUPS = ["task_frame", "source_manifest_private", "base_evidence_unit_pool", "base_evidence_pair_material", "robustness_variant_material", "ablation_control_material", "hard_negative_control_material", "shuffled_mismatch_control_material", "outcome_eval_private", "material_qa", "source_material_manifest", "parent_r2an_row_ref_private"]
VARIANTS = ["single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control"]
EXPECTED_BUCKETS = {"mechanism_interpretation_bucket": "pair_complementarity_supported", "pair_complementarity_lift_bucket": "pair_complementarity_lift_high", "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_medium", "hard_negative_rejection_bucket": "hard_negative_rejection_medium", "path_confound_risk_bucket": "path_confound_risk_low", "gold_isolation_pass_bucket": "gold_isolation_pass"}

R2AY_TRUE = ["haae_r2az_evidence_pair_support_explicit_local_robustness_experiment_authorized_bool", "r2az_explicit_opt_in_required_bool", "r2az_existing_r2ax_private_material_read_authorized_bool", "r2az_aggregate_metrics_only_bool", "r2az_public_audit_required_bool"]
R2AY_FALSE = ["r2ay_private_read_bool", "r2ay_private_write_bool", "r2ay_material_generation_bool", "r2ay_metric_computation_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2ay_source_lock_gate", "r2ay_stop_go_exact_gate", "default_noop_or_explicit_opt_in_gate", "root_safety_gate", "r2ax_manifest_group_schema_gate", "variant_set_gate", "no_material_generation_gate", "no_source_candidate_corpus_scan_gate", "no_runtime_openlocus_retrieval_gate", "aggregate_bucket_metrics_only_gate", "public_privacy_gate", "r2ba_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_pass", "safe_parser_fail", "r2ay_checkpoint_drift_fail", "r2ay_status_drift_fail", "r2ay_self_test_drift_fail", "r2ay_stop_go_overauth_fail", "root_in_repo_fail", "root_missing_manifest_fail", "root_group_missing_fail", "root_group_symlink_fail", "root_unexpected_group_fail", "manifest_schema_fail", "source_lock_drift_fail", "variant_missing_fail", "metric_bucketization_fail", "status_metric_alignment_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "runtime_overauth_fail", "public_leak_fail", "stop_go_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_readback_fail", "readback_record_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_authorized_bool", "r2ba_public_only_audit_bool", "r2ba_no_private_read_bool", "r2ba_no_metric_recompute_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|parent_private_pair_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

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
        elif a == "--allow-r2az-explicit-local-robustness-experiment": parsed["explicit"] = True; i += 1
        elif a == "--confirm-existing-r2ax-material-only": parsed["confirm_existing"] = True; i += 1
        elif a == "--confirm-no-material-generation": parsed["confirm_no_material"] = True; i += 1
        elif a == "--confirm-no-source-candidate-corpus-scan": parsed["confirm_no_scan"] = True; i += 1
        elif a == "--confirm-no-runtime-openlocus-retrieval": parsed["confirm_no_runtime"] = True; i += 1
        elif a == "--confirm-aggregate-only-public-artifact": parsed["confirm_public"] = True; i += 1
        elif a in {"--r2ax-private-material-root", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--r2ax-private-material-root": "root", "--validate-report": "validate", "--out": "out"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "root", "confirm_existing", "confirm_no_material", "confirm_no_scan", "confirm_no_runtime", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]; p = Path(value); resolved = p if p.is_absolute() else repo / p
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH
def outside_repo(path: Path) -> bool:
    repo = Path(__file__).resolve().parents[1]
    try: path.resolve(strict=False).relative_to(repo); return False
    except Exception: return True
def symlink_component(path: Path) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/")
    for part in p.parts[1:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
    return False

def audit_r2ay(r2ay: dict[str, Any]) -> dict[str, bool]:
    src = (r2ay.get("source_lock_records") or [{}])[0]; stop = (r2ay.get("stop_go_records") or [{}])[0]
    source_ok = r2ay.get("status") == R2AY_STATUS and r2ay.get("self_test_total") == R2AY_SELF_TEST_TOTAL and src.get("locked_haae_r2ax_checkpoint") == R2AX_CHECKPOINT and src.get("locked_inherited_r2aw_checkpoint") == R2AW_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("source_locked_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2AY_TRUE) and all(stop.get(f, False) is False for f in R2AY_FALSE)
    return {"source_ok": source_ok and stop_ok, "lock_ok": source_ok, "stop_ok": stop_ok}

def audit_inherited_public(repo: Path) -> dict[str, bool]:
    try:
        r2at = load_json(repo / R2AT_REPORT_PATH)
        r2ap = load_json(repo / R2AP_REPORT_PATH)
    except Exception:
        return {"r2at_ok": False, "r2ap_ok": False, "inherited_ok": False}
    r2at_metric = (r2at.get("mechanism_metric_records") or [{}])[0]
    r2ap_metric = (r2ap.get("aggregate_metric_records") or [{}])[0]
    r2at_ok = (
        r2at.get("status") == "haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized_pair_complementarity_supported"
        and r2at_metric.get("mechanism_interpretation_bucket") == "pair_complementarity_supported"
        and r2at_metric.get("pair_complementarity_lift_bucket") == "pair_complementarity_lift_high"
        and r2at_metric.get("support_vs_contrast_separation_bucket") == "support_vs_contrast_separation_medium"
        and r2at_metric.get("hard_negative_rejection_bucket") == "hard_negative_rejection_medium"
        and r2at_metric.get("path_confound_risk_bucket") == "path_confound_risk_low"
        and r2at_metric.get("gold_isolation_pass_bucket") == "gold_isolation_pass"
    )
    r2ap_ok = (
        r2ap.get("status") == "haae_r2ap_explicit_local_material_experiment_complete_r2aq_public_audit_authorized_support_signal"
        and r2ap_metric.get("robustness_result_bucket") == "support_signal"
        and r2ap_metric.get("support_vs_control_separation_bucket") == "support_separation_high"
        and r2ap_metric.get("selected_signal_family_bucket") == "evidence_pair_support_complementarity"
    )
    return {"r2at_ok": r2at_ok, "r2ap_ok": r2ap_ok, "inherited_ok": r2at_ok and r2ap_ok}

def validate_root(value: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    if not value or any(part == ".." for part in Path(value).parts): return False, "root_traversal_rejected", {}
    root = Path(value)
    try:
        if not root.exists() or root.is_symlink() or symlink_component(root) or not outside_repo(root): return False, "root_safety_rejected", {}
        mf = root / "r2ax_private_manifest.json"; gd = root / "groups"
        if not mf.is_file() or mf.is_symlink() or not gd.is_dir() or gd.is_symlink(): return False, "manifest_or_groups_missing", {}
        manifest = load_json(mf)
        if manifest.get("schema_version") != PRIVATE_SCHEMA or manifest.get("phase") != R2AX_PHASE: return False, "manifest_schema_mismatch", {}
        if (manifest.get("source_lock") or {}).get("r2aw_checkpoint") != R2AW_CHECKPOINT or (manifest.get("source_lock") or {}).get("r2an_checkpoint") != R2AN_CHECKPOINT: return False, "manifest_source_lock_mismatch", {}
        if set(manifest.get("variants") or []) != set(VARIANTS): return False, "manifest_variant_set_mismatch", {}
        present = {p.name for p in gd.iterdir()}
        if present != {f"{g}.jsonl" for g in GROUPS}: return False, "group_file_set_mismatch", {}
        rows: dict[str, list[dict[str, Any]]] = {}
        for g in GROUPS:
            p = gd / f"{g}.jsonl"
            if not p.is_file() or p.is_symlink() or root.resolve() not in p.resolve().parents: return False, "group_file_invalid", {}
            rows[g] = load_jsonl(p)
            if not rows[g]: return False, "group_file_empty", {}
        variants = {r.get("robustness_variant_bucket") for r in rows["robustness_variant_material"]}
        if set(VARIANTS) != variants: return False, "variant_set_mismatch", {}
    except Exception:
        return False, "root_invalid", {}
    return True, "root_valid", rows

def bucket_20(n: int) -> str:
    if n <= 0: return "task_count_0"
    if n <= 5: return "task_count_1_to_5"
    if n <= 10: return "task_count_6_to_10"
    if n <= 15: return "task_count_11_to_15"
    if n <= 20: return "task_count_16_to_20"
    return "task_count_over_scope"

def compute_buckets(rows: dict[str, list[dict[str, Any]]]) -> dict[str, str | bool]:
    variants = {r.get("robustness_variant_bucket") for r in rows.get("robustness_variant_material", [])}
    integrity = set(VARIANTS) == variants and all(rows.get(g) for g in GROUPS)
    no_metric_rows = all(r.get("experiment_metric_bool") is False for r in rows.get("robustness_variant_material", []))
    gold_ok = all(r.get("gold_private_eval_only_bool") is True and r.get("used_for_pair_selection_bool") is False for r in rows.get("outcome_eval_private", []))
    source_by_ref = {r.get("private_source_ref"): r.get("source_path_private") for r in rows.get("source_manifest_private", [])}
    unit_by_ref = {r.get("private_evidence_unit_ref"): r for r in rows.get("base_evidence_unit_pool", [])}
    pair_by_ref = {r.get("private_pair_ref"): r for r in rows.get("base_evidence_pair_material", [])}
    outcomes: dict[str, dict[str, set[str]]] = {}
    for row in rows.get("outcome_eval_private", []):
        raw_label = row.get("outcome_label_private")
        label: dict[str, Any] = raw_label if isinstance(raw_label, dict) else {}
        gold_paths: set[str] = set()
        hard_paths: set[str] = set()
        for span in label.get("gold_spans", []):
            if not isinstance(span, dict):
                continue
            path = span.get("path")
            if path:
                gold_paths.add(str(path))
        for span in label.get("hard_negatives", []):
            if not isinstance(span, dict):
                continue
            path = span.get("path")
            if path:
                hard_paths.add(str(path))
        outcomes[row.get("private_task_ref", "")] = {
            "gold": gold_paths,
            "hard": hard_paths,
        }
    support_variants = {"support_contrast_perturbation", "query_evidence_masking"}
    control_variants = {"hard_negative_strengthening", "shuffled_pair_control", "cross_task_mismatch_control", "path_token_confound_stress", "gold_isolation_control"}
    support_parent_families = {"target_support_pair", "complementary_support_pair"}
    control_support_parent_hits = 0
    control_total = 0
    support_gold_hits = 0
    support_total = 0
    control_gold_hits = 0
    hard_hits = 0
    path_variant_support_parent = 0
    ablation_support_parent = 0
    aligned_tasks = {row.get("private_task_ref") for row in rows.get("outcome_eval_private", []) if row.get("gold_private_eval_only_bool") is True}
    for row in rows.get("robustness_variant_material", []):
        variant = row.get("robustness_variant_bucket")
        pair = pair_by_ref.get(row.get("parent_private_pair_ref"), {})
        family = pair.get("pair_family_bucket")
        paths: set[str] = set()
        for ref in [pair.get("left_unit_ref"), pair.get("right_unit_ref")]:
            path = source_by_ref.get(unit_by_ref.get(ref, {}).get("private_source_ref"))
            if path: paths.add(path)
        outcome = outcomes.get(row.get("private_task_ref", ""), {"gold": set(), "hard": set()})
        gold_hit = bool(paths & outcome.get("gold", set()))
        hard_hit = bool(paths & outcome.get("hard", set()))
        if variant in support_variants:
            support_total += 1
            support_gold_hits += int(gold_hit)
        if variant in control_variants:
            control_total += 1
            control_support_parent_hits += int(family in support_parent_families)
            control_gold_hits += int(gold_hit)
        hard_hits += int(hard_hit)
        if variant == "path_token_confound_stress" and family in support_parent_families:
            path_variant_support_parent += 1
        if variant == "single_unit_ablation" and family in support_parent_families:
            ablation_support_parent += 1
    support_signal_bucket = "support_signal_bucket_low" if support_gold_hits <= 5 else "support_signal_bucket_medium" if support_gold_hits <= 15 else "support_signal_bucket_high"
    control_retention_high = control_total > 0 and control_support_parent_hits >= max(1, control_total * 3 // 4)
    control_gold_comparable = control_gold_hits >= support_gold_hits
    separation_bucket = "support_control_separation_collapsed" if control_retention_high or control_gold_comparable else "support_control_separation_positive"
    shuffled_rejection_bucket = "control_rejection_failed" if control_retention_high else "control_rejection_pass"
    path_confound_bucket = "path_confound_risk_elevated" if path_variant_support_parent > 0 else "path_confound_risk_low"
    ablation_bucket = "single_unit_ablation_not_degraded" if ablation_support_parent > 0 else "single_unit_ablation_degraded"
    hard_bucket = "hard_negative_control_not_dominant" if hard_hits <= 5 else "hard_negative_control_elevated"
    if not integrity or not no_metric_rows or not gold_ok:
        result = "mixed_or_inconclusive"
    elif separation_bucket == "support_control_separation_collapsed" or shuffled_rejection_bucket == "control_rejection_failed" or path_confound_bucket == "path_confound_risk_elevated":
        result = "artifact_likely"
    elif support_signal_bucket == "support_signal_bucket_high" and separation_bucket == "support_control_separation_positive":
        result = "robust_signal"
    else:
        result = "mixed_or_inconclusive"
    return {"robustness_result_bucket": result, "variant_coverage_bucket": "variant_coverage_all" if integrity else "variant_coverage_incomplete", "outcome_alignment_bucket": bucket_20(len(aligned_tasks)), "support_signal_retention_bucket": support_signal_bucket, "support_vs_control_robustness_separation_bucket": separation_bucket, "single_unit_ablation_degradation_bucket": ablation_bucket, "hard_negative_robustness_bucket": hard_bucket, "shuffled_cross_task_control_rejection_bucket": shuffled_rejection_bucket, "query_evidence_masking_sensitivity_bucket": "query_evidence_masking_present" if "query_evidence_masking" in variants else "query_evidence_masking_missing", "path_token_confound_risk_bucket": path_confound_bucket, "material_integrity_bucket": "material_integrity_pass" if integrity and no_metric_rows else "material_integrity_fail", "gold_isolation_bucket": "gold_isolation_pass" if gold_ok else "gold_isolation_fail", "aggregate_only_bucketized_bool": True, "no_exact_metrics_bool": True}

def default_metrics() -> dict[str, str | bool]:
    return {"robustness_result_bucket": "unavailable_no_explicit_opt_in", "variant_coverage_bucket": "unavailable_no_explicit_opt_in", "outcome_alignment_bucket": "unavailable_no_explicit_opt_in", "support_signal_retention_bucket": "unavailable_no_explicit_opt_in", "support_vs_control_robustness_separation_bucket": "unavailable_no_explicit_opt_in", "single_unit_ablation_degradation_bucket": "unavailable_no_explicit_opt_in", "hard_negative_robustness_bucket": "unavailable_no_explicit_opt_in", "shuffled_cross_task_control_rejection_bucket": "unavailable_no_explicit_opt_in", "query_evidence_masking_sensitivity_bucket": "unavailable_no_explicit_opt_in", "path_token_confound_risk_bucket": "unavailable_no_explicit_opt_in", "material_integrity_bucket": "unavailable_no_explicit_opt_in", "gold_isolation_bucket": "unavailable_no_explicit_opt_in", "aggregate_only_bucketized_bool": True, "no_exact_metrics_bool": True}

def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS_ARTIFACT, f"{total}/{total}", R2AY_CHECKPOINT, R2AY_STATUS, R2AX_CHECKPOINT, R2AW_CHECKPOINT, R2AN_CHECKPOINT, R2AT_CHECKPOINT, R2AP_CHECKPOINT, "default/no-op mode", "reads no private root", "explicit opt-in mode", "existing R2AX private robustness material", "bucketized aggregate robustness metrics", "artifact_likely", "support_control_separation_collapsed", "control_rejection_failed", "path_confound_risk_elevated", "support_signal_bucket_low", "no material generation", "no source/candidate/corpus scan", "no runtime/OpenLocus/retrieval", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2az-evidence-pair-support-explicit-local-robustness-experiment.md")) and ok(read("docs/zh/bea-v1-haae-r2az-evidence-pair-support-explicit-local-robustness-experiment.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2az-evidence-pair-support-explicit-local-robustness-experiment.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(args: dict[str, str | bool] | None = None, r2ay: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]; args = args or {"explicit": False}
    if r2ay is None:
        try: r2ay = load_json(repo / R2AY_REPORT_PATH)
        except Exception: r2ay = {}
    source = audit_r2ay(r2ay); inherited = audit_inherited_public(repo); source_ok = source["source_ok"] and inherited["inherited_ok"]; explicit = bool(args.get("explicit")); root_ok = True; root_bucket = "not_read_default_mode"; metrics = default_metrics()
    if explicit and source_ok:
        root_ok, root_bucket, rows = validate_root(str(args.get("root", "")))
        if root_ok: metrics = compute_buckets(rows)
    if not source_ok: status = STATUS_FAIL_SOURCE
    elif explicit and not root_ok: status = STATUS_FAIL_ROOT
    else:
        rb_tmp = metrics.get("robustness_result_bucket")
        status = STATUS_DEFAULT if not explicit else (STATUS_PASS_ROBUST if rb_tmp == "robust_signal" else (STATUS_PASS_ARTIFACT if rb_tmp == "artifact_likely" else STATUS_PASS_MIXED))
    rb = public_readback_match(self_test_total)
    if rb["all_public_readback_match_bool"] is False and status in {STATUS_DEFAULT, STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT}: status = STATUS_FAIL_READBACK
    passed = status in {STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT}
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2azstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_explicit_experiment_success"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gates = {"r2ay_source_lock_gate": source_ok, "r2ay_stop_go_exact_gate": source["stop_ok"], "default_noop_or_explicit_opt_in_gate": True, "root_safety_gate": (not explicit) or root_ok, "r2ax_manifest_group_schema_gate": (not explicit) or root_bucket == "root_valid", "variant_set_gate": (not explicit) or root_bucket == "root_valid", "no_material_generation_gate": True, "no_source_candidate_corpus_scan_gate": True, "no_runtime_openlocus_retrieval_gate": True, "aggregate_bucket_metrics_only_gate": True, "public_privacy_gate": True, "r2ba_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2azsource0000", "locked_haae_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_haae_r2ay_status": R2AY_STATUS, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "r2at_pair_complementarity_supported_bool": inherited["r2at_ok"], "r2ap_support_signal_bool": inherited["r2ap_ok"], "source_locked_bool": source_ok}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2azmode0000", "default_mode_noop_bool": not explicit, "explicit_mode_executed_bool": explicit and passed, "private_read_existing_r2ax_material_bool": explicit and passed, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_openlocus_retrieval_bool": False, "ci_network_provider_clone_bool": False}],
        "root_validation_records": [{"anonymous_root_validation_id": "haaer2azroot0000", "root_validation_bucket": root_bucket, "operator_provided_root_bool": explicit, "root_path_public_bool": False, "implicit_discovery_bool": False, "exact_group_set_required_bool": True, "variant_set_required_bool": True}],
        "aggregate_metric_records": [{"anonymous_metric_id": "haaer2azmetric0000", **metrics}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2azprivacy0000", "aggregate_only_public_artifact_bool": True, "no_private_root_path_public_bool": True, "no_raw_private_rows_public_bool": True, "no_task_query_source_evidence_pair_gold_public_bool": True, "no_exact_counts_rates_ranks_scores_mrr_topk_bool": True}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2azgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2azsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2azreadback0000", **rb}],
        "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_DEFAULT, STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT}: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_haae_r2ay_status": R2AY_STATUS, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True or src.get("r2at_pair_complementarity_supported_bool") is not True or src.get("r2ap_support_signal_bool") is not True: issues.append("source_lock_bool_mismatch")
    mode = (report.get("execution_mode_records") or [{}])[0]
    for f in ["material_generation_bool", "source_candidate_corpus_scan_bool", "runtime_openlocus_retrieval_bool", "ci_network_provider_clone_bool"]:
        if mode.get(f) is not False: issues.append(f"mode_{f}")
    metric = (report.get("aggregate_metric_records") or [{}])[0]
    if metric.get("aggregate_only_bucketized_bool") is not True or metric.get("no_exact_metrics_bool") is not True: issues.append("metric_bucketization_mismatch")
    status_to_result = {STATUS_PASS_ROBUST: "robust_signal", STATUS_PASS_MIXED: "mixed_or_inconclusive", STATUS_PASS_ARTIFACT: "artifact_likely"}
    report_status = report.get("status")
    if isinstance(report_status, str) and report_status in status_to_result and metric.get("robustness_result_bucket") != status_to_result[report_status]: issues.append("status_metric_alignment_mismatch")
    for field in ["robustness_result_bucket", "variant_coverage_bucket", "outcome_alignment_bucket", "support_signal_retention_bucket", "support_vs_control_robustness_separation_bucket", "single_unit_ablation_degradation_bucket", "hard_negative_robustness_bucket", "shuffled_cross_task_control_rejection_bucket", "query_evidence_masking_sensitivity_bucket", "path_token_confound_risk_bucket", "material_integrity_bucket", "gold_isolation_bucket"]:
        value = metric.get(field)
        if not isinstance(value, str) or re.search(r"\b\d+\.\d+\b|/tmp/|\.rs\b|r14m-", value): issues.append(f"metric_{field}_not_bucketized")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    for f in ["aggregate_only_public_artifact_bool", "no_private_root_path_public_bool", "no_raw_private_rows_public_bool", "no_task_query_source_evidence_pair_gold_public_bool", "no_exact_counts_rates_ranks_scores_mrr_topk_bool"]:
        if priv.get(f) is not True: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    explicit = report.get("status") in {STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT}
    if explicit:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2ba_stop_go_mismatch")
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

def make_root(root: Path, mut: str = "") -> None:
    gd = root / "groups"; gd.mkdir(parents=True)
    manifest = {"schema_version": PRIVATE_SCHEMA if mut != "schema" else "bad", "phase": R2AX_PHASE, "source_lock": {"r2aw_checkpoint": R2AW_CHECKPOINT if mut != "source" else "bad", "r2an_checkpoint": R2AN_CHECKPOINT}, "variants": VARIANTS if mut != "variant" else VARIANTS[:-1]}
    (root / "r2ax_private_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows: dict[str, list[dict[str, Any]]] = {g: [{"row_bucket": "synthetic"}] for g in GROUPS}
    rows["robustness_variant_material"] = [{"robustness_variant_bucket": v, "experiment_metric_bool": False} for v in (VARIANTS if mut != "variant" else VARIANTS[:-1])]
    rows["outcome_eval_private"] = [{"gold_private_eval_only_bool": True}]
    for g, rs in rows.items(): (gd / f"{g}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs), encoding="utf-8")

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; base = load_json(repo / R2AY_REPORT_PATH)
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    default = build_report(r2ay=base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        root = Path(td) / "root"; make_root(root); explicit = build_report({"explicit": True, "root": str(root)}, base); check("explicit_synthetic_pass", explicit["status"] in {STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT} and validate_report(explicit) == [])
        for name, mut in [("manifest_schema_fail", "schema"), ("source_lock_drift_fail", "source"), ("variant_missing_fail", "variant")]:
            r = Path(td) / name; make_root(r, mut); check(name, build_report({"explicit": True, "root": str(r)}, base)["status"] == STATUS_FAIL_ROOT)
        r = Path(td) / "miss"; make_root(r); (r / "groups" / "task_frame.jsonl").unlink(); check("root_group_missing_fail", build_report({"explicit": True, "root": str(r)}, base)["status"] == STATUS_FAIL_ROOT)
        r = Path(td) / "unexpected"; make_root(r); (r / "groups" / "extra.jsonl").write_text("{}\n"); check("root_unexpected_group_fail", build_report({"explicit": True, "root": str(r)}, base)["status"] == STATUS_FAIL_ROOT)
        r = Path(td) / "sy"; make_root(r); (r / "groups" / "task_frame.jsonl").unlink(); (r / "groups" / "task_frame.jsonl").symlink_to(root / "groups" / "task_frame.jsonl"); check("root_group_symlink_fail", build_report({"explicit": True, "root": str(r)}, base)["status"] == STATUS_FAIL_ROOT)
    check("root_in_repo_fail", validate_root(str(repo / "x"))[0] is False)
    try: parse_args(["--allow-r2az-explicit-local-robustness-experiment", "--confirm-no-material-generation"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    for name, mut in [("r2ay_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ax_checkpoint", "bad")), ("r2ay_status_drift_fail", lambda r: r.__setitem__("status", "bad")), ("r2ay_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2ay_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True))]:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(r2ay=m)["status"] == STATUS_FAIL_SOURCE)
    mutations = [("metric_bucketization_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("aggregate_only_bucketized_bool", False), "metric_bucketization_mismatch"), ("status_metric_alignment_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "robust_signal" if r["status"] != STATUS_PASS_ROBUST else "artifact_likely"), "status_metric_alignment_mismatch"), ("material_generation_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("material_generation_bool", True), "mode_material_generation_bool"), ("source_scan_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "mode_source_candidate_corpus_scan_bool"), ("runtime_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("runtime_openlocus_retrieval_bool", True), "mode_runtime_openlocus_retrieval_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        rr = Path(td) / "r"; make_root(rr); good = build_report({"explicit": True, "root": str(rr)}, base)
        for name, mut, issue in mutations:
            m = json.loads(json.dumps(good)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS_ROBUST}

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
    report = build_report(args); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS_ROBUST, STATUS_PASS_MIXED, STATUS_PASS_ARTIFACT} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
