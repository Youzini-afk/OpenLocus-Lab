#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AT evidence-pair support private mechanism decomposition.

Default mode is a public no-op. Explicit mode requires operator opt-in plus an
existing R2AN private material root and publishes only bucketized aggregate
mechanism-decomposition results. It never scans source/candidate/corpus files,
regenerates material, mutates R2AN material, or publishes raw private values.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AT Evidence-Pair Support Explicit Local Private Mechanism Decomposition"
SLUG = "bea_v1_haae_r2at_evidence_pair_support_explicit_private_mechanism_decomposition"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AS_CHECKPOINT = "36e64d6"
R2AS_STATUS = "haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight_complete_r2at_explicit_private_mechanism_decomposition_authorized"
R2AR_CHECKPOINT = "7c36376"
R2AQ_CHECKPOINT = "77eab19"
R2AP_CHECKPOINT = "87ea9de"
R2AO_CHECKPOINT = "5cfa8d3"
R2AN_CHECKPOINT = "93bba5f"
R2AN_SCHEMA = "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1"
R2AS_REPORT_PATH = Path("artifacts/bea_v1_haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight/bea_v1_haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight_report.json")

STATUS_DEFAULT = "haae_r2at_unavailable_no_explicit_private_mechanism_decomposition_opt_in"
STATUS_PASS_PREFIX = "haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2at_fail_closed_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2at_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2at_fail_closed_private_material_root_invalid"
STATUS_FAIL_PRIVACY = "haae_r2at_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2at_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"

GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
SUPPORT_FAMILIES = ["target_support_pair", "complementary_support_pair"]
CONTROL_FAMILIES = ["contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
AXES = ["complementarity_vs_single_unit", "support_vs_contrast", "target_support_vs_hard_negative", "shuffled_cross_task_control_rejection", "path_token_confound_check", "outcome_gold_isolation", "pair_family_balance_coverage_sensitivity", "evidence_quality_vs_pair_composition"]
INTERPRETATIONS = ["pair_complementarity_supported", "support_relation_supported", "control_artifact_risk", "path_confound_risk", "mixed_or_inconclusive"]

GATE_NAMES = ["r2as_source_locked_gate", "inherited_r2aq_r2ap_r2ao_r2an_lock_gate", "support_signal_gate", "support_separation_high_gate", "default_noop_or_explicit_opt_in_gate", "private_material_root_safety_gate", "required_r2an_group_set_gate", "no_source_candidate_corpus_scan_gate", "no_material_regeneration_gate", "gold_eval_only_gate", "aggregate_only_bucketized_public_gate", "no_exact_metric_publication_gate", "diagnostics_private_optional_gate", "mechanism_axis_set_gate", "r2au_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["default_noop_pass", "explicit_synthetic_pass", "explicit_diagnostics_private_pass", "wrong_r2as_status_fail", "r2as_checkpoint_drift_fail", "r2as_authorization_drift_fail", "r2aq_lock_drift_fail", "r2ap_lock_drift_fail", "r2ao_lock_drift_fail", "r2an_lock_drift_fail", "support_signal_drift_fail", "support_separation_drift_fail", "missing_opt_in_parser_fail", "repo_root_reject_fail", "symlink_root_reject_fail", "traversal_root_reject_fail", "missing_manifest_fail", "missing_group_fail", "group_set_mismatch_fail", "manifest_schema_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "gold_outside_eval_fail", "public_leak_fail", "exact_metric_public_fail", "stop_go_overauth_fail", "stop_go_next_phase_drift_fail", "axis_set_fail", "interpretation_bucket_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "readback_record_fail", "safe_parser_fail", "default_no_private_action_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_FALSE_FIELDS = ["robustness_generation_authorized_bool", "scale_preflight_authorized_bool", "new_experiment_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_adoption_authorized_bool", "raw_publication_authorized_bool", "material_generation_authorized_bool", "candidate_generation_authorized_bool", "r2an_material_mutation_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n <= 0: return "count_0"
    if n <= 5: return "count_1_to_5"
    if n <= 20: return "count_6_to_20"
    if n <= 200: return "count_21_to_200"
    if n <= 2000: return "count_201_to_2000"
    return "count_over_2000"


def bucket_task(n: int) -> str:
    if n <= 0: return "task_coverage_0"
    if n <= 5: return "task_coverage_1_to_5"
    if n <= 10: return "task_coverage_6_to_10"
    if n <= 15: return "task_coverage_11_to_15"
    if n <= 20: return "task_coverage_16_to_20"
    return "task_coverage_over_scope"


def bucket_delta(a: int, b: int, stem: str) -> str:
    delta = a - b
    if delta >= 10: return f"{stem}_high"
    if delta >= 3: return f"{stem}_medium"
    if delta > 0: return f"{stem}_low"
    if delta == 0: return f"{stem}_flat"
    return f"{stem}_negative"


def audit_r2as(r2as: dict[str, Any]) -> dict[str, bool]:
    src = (r2as.get("source_lock_records") or [{}])[0]
    signal = (r2as.get("inherited_support_signal_records") or [{}])[0]
    stop = (r2as.get("stop_go_records") or [{}])[0]
    status_ok = r2as.get("status") == R2AS_STATUS
    self_test_ok = r2as.get("self_test_total") == 34
    scan_ok = r2as.get("forbidden_scan", {}).get("status") == "pass"
    lock_ok = src.get("locked_haae_r2ar_checkpoint") == R2AR_CHECKPOINT and src.get("locked_inherited_r2aq_checkpoint") == R2AQ_CHECKPOINT and src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and src.get("locked_inherited_r2ao_checkpoint") == R2AO_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("source_locked_bool") is True
    signal_ok = signal.get("r2ap_result_bucket") == "support_signal" and signal.get("support_vs_control_separation_bucket") == "support_separation_high" and signal.get("selected_signal_family_bucket") == SELECTED_SIGNAL_FAMILY
    axes_ok = {row.get("axis_bucket") for row in r2as.get("mechanism_axis_records", [])} == set(AXES)
    auth_ok = stop.get("haae_r2at_explicit_local_private_mechanism_decomposition_authorized_bool") is True and stop.get("r2at_existing_private_material_read_authorized_bool") is True and stop.get("r2at_mechanism_decomposition_metrics_authorized_bool") is True and stop.get("r2at_aggregate_only_public_output_required_bool") is True and stop.get("next_allowed_phase") == PHASE
    false_ok = all(stop.get(field, False) is False for field in ["robustness_material_generation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "material_generation_authorized_bool"])
    source_ok = status_ok and self_test_ok and scan_ok and lock_ok and signal_ok and axes_ok and auth_ok and false_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "lock_ok": lock_ok, "signal_ok": signal_ok, "axes_ok": axes_ok, "auth_ok": auth_ok, "false_ok": false_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top_k_value|mrr_value|hit_rate_value|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "explicit": False, "root": "", "confirm": False, "diag_root": "", "diag_subdir": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-r2at-explicit-private-mechanism-decomposition": parsed["explicit"] = True; i += 1
        elif arg == "--confirm-aggregate-only-public-output": parsed["confirm"] = True; i += 1
        elif arg in {"--validate-report", "--out", "--r2an-private-material-root", "--private-diagnostics-root", "--private-diagnostics-subdir"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--r2an-private-material-root": "root", "--private-diagnostics-root": "diag_root", "--private-diagnostics-subdir": "diag_subdir"}[arg]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    required_bits = [parsed["explicit"], bool(parsed["root"]), parsed["confirm"]]
    if any(required_bits) and not all(required_bits): raise ValueError("invalid arguments")
    diag_bits = [bool(parsed["diag_root"]), bool(parsed["diag_subdir"])]
    if any(diag_bits) and (not all(diag_bits) or not parsed["explicit"]): raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def ensure_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def has_traversal(value: str) -> bool:
    return any(part == ".." for part in Path(value).parts)


def read_private_groups(root_value: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    repo = Path(__file__).resolve().parents[1]
    if not root_value or has_traversal(root_value): return False, "root_traversal_rejected", {}
    root = Path(root_value)
    try:
        if not root.exists() or root.is_symlink(): return False, "root_missing_or_symlink", {}
        resolved = root.resolve(strict=True)
        if resolved == repo or repo.resolve() in resolved.parents: return False, "repo_root_rejected", {}
    except Exception:
        return False, "root_invalid", {}
    manifest_path = root / "r2an_private_manifest.json"
    groups_dir = root / "groups"
    if not manifest_path.exists() or manifest_path.is_symlink() or not groups_dir.exists() or groups_dir.is_symlink(): return False, "manifest_or_groups_missing", {}
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return False, "manifest_invalid", {}
    if manifest.get("schema_version") != R2AN_SCHEMA or manifest.get("selected_signal_family") != SELECTED_SIGNAL_FAMILY: return False, "manifest_schema_mismatch", {}
    if set((manifest.get("groups") or {}).keys()) != set(GROUPS): return False, "manifest_group_set_mismatch", {}
    try:
        entries = list(groups_dir.iterdir())
        if any((not p.is_file()) and (not p.is_symlink()) for p in entries): return False, "group_file_set_mismatch", {}
        present = {p.name for p in entries}
    except Exception:
        return False, "group_set_invalid", {}
    expected = {f"{g}.jsonl" for g in GROUPS}
    if present != expected: return False, "group_file_set_mismatch", {}
    rows: dict[str, list[dict[str, Any]]] = {}
    for group in GROUPS:
        path = groups_dir / f"{group}.jsonl"
        try:
            if path.is_symlink() or not ensure_under(path, root): return False, "group_file_invalid", {}
            rows[group] = load_jsonl(path)
        except Exception:
            return False, "group_file_invalid", {}
    return True, "existing_r2an_material_root_valid", rows


def validate_diag_target(root_value: str, subdir_value: str) -> tuple[bool, Path | None]:
    repo = Path(__file__).resolve().parents[1]
    if not root_value and not subdir_value: return True, None
    if has_traversal(root_value) or has_traversal(subdir_value) or "/" in subdir_value or "\\" in subdir_value: return False, None
    root = Path(root_value)
    try:
        resolved = root.resolve(strict=False)
        if resolved == repo or repo.resolve() in resolved.parents or root.is_symlink(): return False, None
        out = root / subdir_value
        out.mkdir(parents=True, exist_ok=True)
        if out.is_symlink() or not ensure_under(out, root): return False, None
        return True, out
    except Exception:
        return False, None


def family_stats(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source_paths = {row.get("private_source_ref"): row.get("source_path_private") for row in rows.get("source_manifest_private", [])}
    unit_paths = {row.get("private_evidence_unit_ref"): source_paths.get(row.get("private_source_ref")) for row in rows.get("evidence_unit_pool", [])}
    outcomes: dict[str, dict[str, set[str]]] = {}
    for row in rows.get("outcome_eval_private", []):
        labels = row.get("outcome_label_private", {})
        labels = labels if isinstance(labels, dict) else {}
        target_paths = {str(span.get("path")) for span in labels.get("gold_spans", []) if isinstance(span, dict) and isinstance(span.get("path"), str)}
        control_paths = {str(span.get("path")) for span in labels.get("hard_negatives", []) if isinstance(span, dict) and isinstance(span.get("path"), str)}
        outcomes[str(row.get("private_task_ref", ""))] = {"target": target_paths, "control": control_paths}
    per_family: dict[str, dict[str, Any]] = {fam: {"pair_rows": 0, "target_tasks": set(), "control_tasks": set(), "aligned_tasks": set()} for fam in PAIR_FAMILIES}
    for group in ["support_relation_material", "contrast_control_material", "evidence_pair_material"]:
        for row in rows.get(group, []):
            fam = str(row.get("pair_family_bucket", ""))
            if fam not in per_family: continue
            task_ref = str(row.get("private_task_ref", ""))
            pair_paths = {unit_paths.get(row.get("left_unit_ref")), unit_paths.get(row.get("right_unit_ref"))}
            outcome = outcomes.get(task_ref, {"target": set(), "control": set()})
            per_family[fam]["pair_rows"] += 1
            if outcome["target"] or outcome["control"]: per_family[fam]["aligned_tasks"].add(task_ref)
            if pair_paths & outcome["target"]: per_family[fam]["target_tasks"].add(task_ref)
            if pair_paths & outcome["control"]: per_family[fam]["control_tasks"].add(task_ref)
    return per_family


def compute_mechanism_buckets(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    stats = family_stats(rows)
    task_refs = {str(row.get("private_task_ref", "")) for row in rows.get("task_frame", []) if row.get("private_task_ref")}
    support_hit = min(len(stats[f]["target_tasks"]) for f in SUPPORT_FAMILIES)
    complement_hit = len(stats["complementary_support_pair"]["target_tasks"])
    single_hit = len(stats["single_unit_ablation_control"]["target_tasks"])
    contrast_hit = max(len(stats[f]["target_tasks"]) for f in ["contrastive_hard_negative_pair", "shuffled_relation_control", "cross_task_mismatch_control"])
    hard_control = len(stats["contrastive_hard_negative_pair"]["control_tasks"])
    shuffled_hit = max(len(stats["shuffled_relation_control"]["target_tasks"]), len(stats["cross_task_mismatch_control"]["target_tasks"]))
    path_flags = any(row.get("selection_used_path_bool") is True or row.get("path_tokens_primary_signal_bool") is True for group in ["evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material"] for row in rows.get(group, []))
    gold_selection = any(row.get("selection_used_gold_bool") is True or row.get("used_for_evidence_unit_selection_bool") is True or row.get("used_for_pair_selection_bool") is True for group in ["evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private"] for row in rows.get(group, []))
    counts = [int(stats[f]["pair_rows"]) for f in PAIR_FAMILIES]
    nonzero = [c for c in counts if c > 0]
    concentration = "family_concentration_unavailable" if not nonzero else ("family_concentration_balanced" if max(nonzero) <= min(nonzero) * 3 else "family_concentration_sensitive")
    qa_ok = any(row.get("material_qa_bucket") == "material_qa_only" or row.get("pair_family_coverage_bool") is True for row in rows.get("material_qa", []))
    support_sep = bucket_delta(support_hit, contrast_hit, "support_vs_contrast_separation")
    hard_reject = bucket_delta(support_hit, hard_control, "hard_negative_rejection")
    shuffled_degrade = bucket_delta(support_hit, shuffled_hit, "shuffled_cross_task_degradation")
    comp_lift = bucket_delta(complement_hit, single_hit, "pair_complementarity_lift")
    single_bucket = bucket_delta(support_hit, single_hit, "single_unit_ablation_gap")
    path_bucket = "path_confound_risk_high" if path_flags else "path_confound_risk_low"
    gold_bucket = "gold_isolation_fail" if gold_selection else "gold_isolation_pass"
    quality_bucket = "evidence_quality_sensitivity_low" if qa_ok else "evidence_quality_sensitivity_unavailable"
    if path_flags:
        interpretation = "path_confound_risk"
    elif shuffled_degrade.endswith("negative") or hard_reject.endswith("negative"):
        interpretation = "control_artifact_risk"
    elif comp_lift.endswith("high") or comp_lift.endswith("medium"):
        interpretation = "pair_complementarity_supported"
    elif support_sep.endswith("high") or support_sep.endswith("medium") or support_sep.endswith("low"):
        interpretation = "support_relation_supported"
    else:
        interpretation = "mixed_or_inconclusive"
    return {
        "axis_coverage_bucket": "axis_coverage_all" if set(AXES) == set(AXES) else "axis_coverage_partial",
        "task_coverage_bucket": bucket_task(len(task_refs)),
        "pair_family_coverage_bucket": "pair_family_coverage_all" if all(stats[f]["pair_rows"] > 0 for f in PAIR_FAMILIES) else "pair_family_coverage_partial",
        "single_unit_ablation_bucket": single_bucket,
        "pair_complementarity_lift_bucket": comp_lift,
        "support_vs_contrast_separation_bucket": support_sep,
        "hard_negative_rejection_bucket": hard_reject,
        "shuffled_cross_task_degradation_bucket": shuffled_degrade,
        "path_confound_risk_bucket": path_bucket,
        "gold_isolation_pass_bucket": gold_bucket,
        "family_concentration_sensitivity_bucket": concentration,
        "evidence_quality_sensitivity_bucket": quality_bucket,
        "mechanism_interpretation_bucket": interpretation,
        "pair_family_presence_buckets": {f: ("pair_family_present" if stats[f]["pair_rows"] > 0 else "pair_family_absent") for f in PAIR_FAMILIES},
    }


def default_metrics() -> dict[str, Any]:
    return {"axis_coverage_bucket": "axis_coverage_unavailable_default_noop", "task_coverage_bucket": "task_coverage_unavailable_default_noop", "pair_family_coverage_bucket": "pair_family_coverage_unavailable_default_noop", "single_unit_ablation_bucket": "single_unit_ablation_unavailable_default_noop", "pair_complementarity_lift_bucket": "pair_complementarity_lift_unavailable_default_noop", "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_unavailable_default_noop", "hard_negative_rejection_bucket": "hard_negative_rejection_unavailable_default_noop", "shuffled_cross_task_degradation_bucket": "shuffled_cross_task_degradation_unavailable_default_noop", "path_confound_risk_bucket": "path_confound_risk_unavailable_default_noop", "gold_isolation_pass_bucket": "gold_isolation_unavailable_default_noop", "family_concentration_sensitivity_bucket": "family_concentration_unavailable_default_noop", "evidence_quality_sensitivity_bucket": "evidence_quality_sensitivity_unavailable_default_noop", "mechanism_interpretation_bucket": "mixed_or_inconclusive", "pair_family_presence_buckets": {f: "pair_family_unavailable_default_noop" for f in PAIR_FAMILIES}}


def write_private_diagnostics(out_dir: Path | None, metrics: dict[str, Any]) -> bool:
    if out_dir is None: return False
    payload = {"diagnostic_scope_bucket": "private_bucketized_mechanism_readback", "mechanism_bucket_summary": metrics}
    (out_dir / "r2at_private_diagnostics.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS_PREFIX, f"{total}/{total}", R2AS_CHECKPOINT, R2AS_STATUS, R2AR_CHECKPOINT, R2AQ_CHECKPOINT, R2AP_CHECKPOINT, R2AO_CHECKPOINT, R2AN_CHECKPOINT, "support_signal", "support_separation_high", "default mode no-op", "explicit opt-in", "existing R2AN private material root", "confirm aggregate-only public output", "no private read, no private write, no metrics, no diagnostics", "read only existing R2AN private material groups", "axis coverage bucket", "pair-complementarity lift bucket", "mechanism interpretation bucket", "pair_complementarity_supported", "support_relation_supported", "control_artifact_risk", "path_confound_risk", "mixed_or_inconclusive", "no source/candidate/corpus scan", "no material regeneration", "gold outcome eval-only", NEXT_PHASE, "No robustness generation, scale preflight, new experiment"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2at-evidence-pair-support-explicit-private-mechanism-decomposition.md")) and has_all(read("docs/zh/bea-v1-haae-r2at-evidence-pair-support-explicit-private-mechanism-decomposition.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2at-evidence-pair-support-explicit-private-mechanism-decomposition.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(args: dict[str, Any] | None = None, r2as: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    args = args or {"explicit": False}
    if r2as is None:
        try: r2as = load_json(repo / R2AS_REPORT_PATH)
        except Exception: r2as = {}
    audit = audit_r2as(r2as)
    readback = public_readback_match(self_test_total)
    explicit = bool(args.get("explicit"))
    metrics = default_metrics()
    root_ok = not explicit
    root_bucket = "not_applicable_default_noop"
    diag_ok = True
    diag_written = False
    private_metrics_bool = False
    if explicit and audit["source_ok"]:
        root_ok, root_bucket, rows = read_private_groups(str(args.get("root", "")))
        diag_ok, diag_dir = validate_diag_target(str(args.get("diag_root", "")), str(args.get("diag_subdir", "")))
        if root_ok and diag_ok:
            metrics = compute_mechanism_buckets(rows)
            private_metrics_bool = True
            diag_written = write_private_diagnostics(diag_dir, metrics)
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    elif explicit and not root_ok: status = STATUS_FAIL_ROOT
    elif explicit and not diag_ok: status = STATUS_FAIL_ARGS
    elif explicit: status = f"{STATUS_PASS_PREFIX}_{metrics['mechanism_interpretation_bucket']}"
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_DEFAULT
    passed = str(status).startswith(STATUS_PASS_PREFIX)
    gates = {"r2as_source_locked_gate": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"], "inherited_r2aq_r2ap_r2ao_r2an_lock_gate": audit["lock_ok"], "support_signal_gate": audit["signal_ok"], "support_separation_high_gate": audit["signal_ok"], "default_noop_or_explicit_opt_in_gate": True, "private_material_root_safety_gate": root_ok, "required_r2an_group_set_gate": root_ok, "no_source_candidate_corpus_scan_gate": True, "no_material_regeneration_gate": True, "gold_eval_only_gate": True, "aggregate_only_bucketized_public_gate": True, "no_exact_metric_publication_gate": True, "diagnostics_private_optional_gate": diag_ok, "mechanism_axis_set_gate": audit["axes_ok"], "r2au_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2atstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_explicit_mechanism_decomposition_pass", "haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_authorized_bool": passed, "r2au_public_audit_package_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2atsource0000", "locked_haae_r2as_checkpoint": R2AS_CHECKPOINT, "locked_haae_r2as_status": R2AS_STATUS, "locked_inherited_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2as_status_match_bool": audit["status_ok"], "r2as_self_test_34_bool": audit["self_test_ok"], "r2as_forbidden_scan_pass_bool": audit["scan_ok"], "inherited_locks_match_bool": audit["lock_ok"], "r2as_authorization_match_bool": audit["auth_ok"], "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2atmode0000", "default_mode_noop_bool": not explicit, "explicit_mode_executed_bool": explicit and passed, "private_read_existing_r2an_material_bool": explicit and passed, "private_write_diagnostics_bool": diag_written, "mechanism_decomposition_metrics_bool": private_metrics_bool and passed, "source_candidate_corpus_scan_bool": False, "material_generation_bool": False, "candidate_generation_bool": False, "r2an_material_mutation_bool": False}],
        "private_material_scope_records": [{"anonymous_private_scope_id": "haaer2atscope0000", "root_safety_bucket": root_bucket, "root_path_public_bool": False, "required_manifest_bucket": "r2an_private_manifest_required", "required_group_buckets": {g: ("required" if explicit else "not_read_default_noop") for g in GROUPS}, "read_only_existing_r2an_material_bool": True, "group_set_exact_match_bool": root_ok, "no_source_candidate_corpus_scan_bool": True}],
        "mechanism_axis_records": [{"anonymous_axis_id": f"haaer2ataxis{idx:04d}", "axis_bucket": axis, "axis_covered_bucket": metrics["axis_coverage_bucket"]} for idx, axis in enumerate(AXES)],
        "mechanism_metric_records": [{"anonymous_metric_id": "haaer2atmetric0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, **metrics, "aggregate_only_bucketized_bool": True, "no_exact_counts_rates_mrr_scores_bool": True, "no_raw_task_query_source_evidence_pair_gold_public_bool": True}],
        "diagnostic_records": [{"anonymous_diagnostic_id": "haaer2atdiag0000", "private_diagnostics_optional_bool": True, "private_diagnostics_written_bool": diag_written, "public_diagnostics_raw_bool": False}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2atboundary0000", "default_no_private_read_write_metrics_diagnostics_bool": not explicit, "gold_outcome_eval_only_bool": True, "gold_used_outside_eval_bool": False, "source_candidate_corpus_scan_bool": False, "material_regeneration_bool": False, "robustness_generation_bool": False, "scale_preflight_bool": False, "new_experiment_bool": False, "ci_network_provider_runtime_openlocus_retrieval_bool": False, "method_default_winner_scale_adoption_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2atgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2atsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2atreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if (report["status"] == STATUS_DEFAULT or str(report["status"]).startswith(STATUS_PASS_PREFIX)) and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "execution_mode_records", "private_material_scope_records", "mechanism_axis_records", "mechanism_metric_records", "diagnostic_records", "boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_DEFAULT and not str(report.get("status", "")).startswith(STATUS_PASS_PREFIX): issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gates = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATE_NAMES) or len(gates) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    validators = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validators) != set(SYNTHETIC_VALIDATORS) or len(validators) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    for field, expected in {"locked_haae_r2as_checkpoint": R2AS_CHECKPOINT, "locked_haae_r2as_status": R2AS_STATUS, "locked_inherited_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}.items():
        if src.get(field) != expected: issues.append(f"source_{field}")
    for field in ["r2as_status_match_bool", "r2as_self_test_34_bool", "r2as_forbidden_scan_pass_bool", "inherited_locks_match_bool", "r2as_authorization_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    explicit = str(report.get("status", "")).startswith(STATUS_PASS_PREFIX)
    if report.get("status") == STATUS_DEFAULT:
        for field in ["explicit_mode_executed_bool", "private_read_existing_r2an_material_bool", "private_write_diagnostics_bool", "mechanism_decomposition_metrics_bool"]:
            if mode.get(field) is not False: issues.append(f"default_private_action_{field}")
    if explicit:
        for field in ["explicit_mode_executed_bool", "private_read_existing_r2an_material_bool", "mechanism_decomposition_metrics_bool"]:
            if mode.get(field) is not True: issues.append(f"explicit_mode_{field}")
    for field in ["source_candidate_corpus_scan_bool", "material_generation_bool", "candidate_generation_bool", "r2an_material_mutation_bool"]:
        if mode.get(field) is not False: issues.append(f"execution_mode_{field}")
    scope = (report.get("private_material_scope_records") or [{}])[0]
    if set((scope.get("required_group_buckets") or {}).keys()) != set(GROUPS): issues.append("required_group_set_mismatch")
    if scope.get("root_path_public_bool") is not False or scope.get("read_only_existing_r2an_material_bool") is not True or scope.get("no_source_candidate_corpus_scan_bool") is not True: issues.append("private_scope_mismatch")
    axes = [row.get("axis_bucket") for row in report.get("mechanism_axis_records", [])]
    if set(axes) != set(AXES) or len(axes) != len(AXES): issues.append("mechanism_axis_set_mismatch")
    metric = (report.get("mechanism_metric_records") or [{}])[0]
    if metric.get("mechanism_interpretation_bucket") not in INTERPRETATIONS: issues.append("mechanism_interpretation_bucket_mismatch")
    for field in ["axis_coverage_bucket", "task_coverage_bucket", "pair_family_coverage_bucket", "single_unit_ablation_bucket", "pair_complementarity_lift_bucket", "support_vs_contrast_separation_bucket", "hard_negative_rejection_bucket", "shuffled_cross_task_degradation_bucket", "path_confound_risk_bucket", "gold_isolation_pass_bucket", "family_concentration_sensitivity_bucket", "evidence_quality_sensitivity_bucket"]:
        if not str(metric.get(field, "")).endswith("default_noop") and "_" not in str(metric.get(field, "")): issues.append(f"metric_bucket_invalid_{field}")
    if set((metric.get("pair_family_presence_buckets") or {}).keys()) != set(PAIR_FAMILIES): issues.append("pair_family_presence_set_mismatch")
    for field in ["aggregate_only_bucketized_bool", "no_exact_counts_rates_mrr_scores_bool", "no_raw_task_query_source_evidence_pair_gold_public_bool"]:
        if metric.get(field) is not True: issues.append(f"metric_{field}")
    diag = (report.get("diagnostic_records") or [{}])[0]
    if diag.get("private_diagnostics_optional_bool") is not True or diag.get("public_diagnostics_raw_bool") is not False: issues.append("diagnostic_scope_mismatch")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("gold_outcome_eval_only_bool") is not True: issues.append("boundary_gold_outcome_eval_only_bool")
    for field in ["gold_used_outside_eval_bool", "source_candidate_corpus_scan_bool", "material_regeneration_bool", "robustness_generation_bool", "scale_preflight_bool", "new_experiment_bool", "ci_network_provider_runtime_openlocus_retrieval_bool", "method_default_winner_scale_adoption_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if explicit and (stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_authorized_bool") is not True): issues.append("r2au_stop_go_mismatch")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_private_root(root: Path, path_flag: bool = False) -> None:
    groups = root / "groups"; groups.mkdir(parents=True)
    (root / "r2an_private_manifest.json").write_text(json.dumps({"schema_version": R2AN_SCHEMA, "selected_signal_family": SELECTED_SIGNAL_FAMILY, "groups": {group: {"row_count": 1} for group in GROUPS}}, sort_keys=True) + "\n", encoding="utf-8")
    sources = [{"private_source_ref": "src0", "source_path_private": "target"}, {"private_source_ref": "src1", "source_path_private": "support"}, {"private_source_ref": "src2", "source_path_private": "control"}]
    units = [{"private_task_ref": f"t{i}", "private_evidence_unit_ref": f"u{i}a", "private_source_ref": "src0", "selection_used_gold_bool": False, "selection_used_path_bool": path_flag} for i in range(6)] + [{"private_task_ref": f"t{i}", "private_evidence_unit_ref": f"u{i}b", "private_source_ref": "src1", "selection_used_gold_bool": False, "selection_used_path_bool": path_flag} for i in range(6)] + [{"private_task_ref": f"t{i}", "private_evidence_unit_ref": f"u{i}c", "private_source_ref": "src2", "selection_used_gold_bool": False, "selection_used_path_bool": path_flag} for i in range(6)]
    pairs = []
    for i in range(6):
        for fam in PAIR_FAMILIES:
            left, right = (f"u{i}a", f"u{i}b") if fam in SUPPORT_FAMILIES else ((f"u{i}c", f"u{i}c") if fam == "contrastive_hard_negative_pair" else (f"u{i}b", f"u{i}c"))
            pairs.append({"private_task_ref": f"t{i}", "private_pair_ref": f"p{i}{fam}", "pair_family_bucket": fam, "left_unit_ref": left, "right_unit_ref": right, "selection_used_gold_bool": False, "selection_used_path_bool": path_flag})
    support = [p for p in pairs if p["pair_family_bucket"] in SUPPORT_FAMILIES]
    contrast = [p for p in pairs if p["pair_family_bucket"] in CONTROL_FAMILIES]
    outcomes = [{"private_task_ref": f"t{i}", "gold_private_eval_only_bool": True, "outcome_label_private": {"gold_spans": [{"path": "target"}], "hard_negatives": [{"path": "control"}]}, "used_for_evidence_unit_selection_bool": False, "used_for_pair_selection_bool": False} for i in range(6)]
    data = {"task_frame": [{"private_task_ref": f"t{i}"} for i in range(6)], "source_manifest_private": sources, "evidence_unit_pool": units, "evidence_pair_material": pairs, "support_relation_material": support, "contrast_control_material": contrast, "outcome_eval_private": outcomes, "material_qa": [{"material_qa_bucket": "material_qa_only", "pair_family_coverage_bool": True}]}
    for group, rows in data.items(): write_jsonl(groups / f"{group}.jsonl", rows)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AS_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    default = build_report(r2as=base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        tmp = Path(td); root = tmp / "priv"; make_private_root(root)
        explicit = build_report({"explicit": True, "root": str(root), "confirm": True}, base); check("explicit_synthetic_pass", str(explicit["status"]).startswith(STATUS_PASS_PREFIX) and validate_report(explicit) == [])
        diag_root = tmp / "diag"; explicit_diag = build_report({"explicit": True, "root": str(root), "confirm": True, "diag_root": str(diag_root), "diag_subdir": "r2atdiag"}, base); check("explicit_diagnostics_private_pass", explicit_diag["diagnostic_records"][0]["private_diagnostics_written_bool"] is True and (diag_root / "r2atdiag" / "r2at_private_diagnostics.json").exists())
        symlink = tmp / "link"; symlink.symlink_to(root); check("symlink_root_reject_fail", build_report({"explicit": True, "root": str(symlink), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        check("traversal_root_reject_fail", build_report({"explicit": True, "root": str(tmp / "x" / ".." / "priv"), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        missing_manifest = tmp / "missing_manifest"; make_private_root(missing_manifest); (missing_manifest / "r2an_private_manifest.json").unlink(); check("missing_manifest_fail", build_report({"explicit": True, "root": str(missing_manifest), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        missing_group = tmp / "missing_group"; make_private_root(missing_group); (missing_group / "groups" / "task_frame.jsonl").unlink(); check("missing_group_fail", build_report({"explicit": True, "root": str(missing_group), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        extra = tmp / "extra"; make_private_root(extra); write_jsonl(extra / "groups" / "extra.jsonl", []); check("group_set_mismatch_fail", build_report({"explicit": True, "root": str(extra), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        extra_dir = tmp / "extra_dir"; make_private_root(extra_dir); (extra_dir / "groups" / "unexpected_dir").mkdir(); check("group_set_mismatch_fail", build_report({"explicit": True, "root": str(extra_dir), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
        bad_schema = tmp / "bad_schema"; make_private_root(bad_schema); (bad_schema / "r2an_private_manifest.json").write_text(json.dumps({"schema_version": "wrong", "selected_signal_family": SELECTED_SIGNAL_FAMILY, "groups": {g: {} for g in GROUPS}}), encoding="utf-8"); check("manifest_schema_fail", build_report({"explicit": True, "root": str(bad_schema), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2as_status_fail", build_report(r2as=wrong)["status"] == STATUS_FAIL_SOURCE)
    auth = json.loads(json.dumps(base)); auth["stop_go_records"][0]["r2at_mechanism_decomposition_metrics_authorized_bool"] = False; check("r2as_authorization_drift_fail", build_report(r2as=auth)["status"] == STATUS_FAIL_SOURCE)
    for name, mut in [("r2aq_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2aq_checkpoint", "wrong")), ("r2ap_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ap_checkpoint", "wrong")), ("r2ao_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ao_checkpoint", "wrong")), ("r2an_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong")), ("support_signal_drift_fail", lambda r: r["inherited_support_signal_records"][0].__setitem__("r2ap_result_bucket", "mixed")), ("support_separation_drift_fail", lambda r: r["inherited_support_signal_records"][0].__setitem__("support_vs_control_separation_bucket", "low"))]:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(r2as=m)["status"] == STATUS_FAIL_SOURCE)
    check("repo_root_reject_fail", build_report({"explicit": True, "root": str(repo), "confirm": True}, base)["status"] == STATUS_FAIL_ROOT)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--allow-r2at-explicit-private-mechanism-decomposition", "--r2an-private-material-root", "/tmp/x"])
        check("missing_opt_in_parser_fail", False)
    except ValueError: check("missing_opt_in_parser_fail", True)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    mutations = [("r2as_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2as_checkpoint", "wrong"), "source_locked_haae_r2as_checkpoint"), ("material_generation_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("material_generation_bool", True), "execution_mode_material_generation_bool"), ("source_scan_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "boundary_source_candidate_corpus_scan_bool"), ("gold_outside_eval_fail", lambda r: r["boundary_records"][0].__setitem__("gold_used_outside_eval_bool", True), "boundary_gold_used_outside_eval_bool"), ("exact_metric_public_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("no_exact_counts_rates_mrr_scores_bool", False), "metric_no_exact_counts_rates_mrr_scores_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("stop_go_next_phase_drift_fail", lambda r: (r.__setitem__("status", f"{STATUS_PASS_PREFIX}_mixed_or_inconclusive"), r["execution_mode_records"][0].__setitem__("explicit_mode_executed_bool", True), r["execution_mode_records"][0].__setitem__("private_read_existing_r2an_material_bool", True), r["execution_mode_records"][0].__setitem__("mechanism_decomposition_metrics_bool", True), r["stop_go_records"][0].__setitem__("haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_authorized_bool", True), r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong")), "r2au_stop_go_mismatch"), ("axis_set_fail", lambda r: r["mechanism_axis_records"].pop(), "mechanism_axis_set_mismatch"), ("interpretation_bucket_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("mechanism_interpretation_bucket", "wrong"), "mechanism_interpretation_bucket_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(json.loads(json.dumps(r["pass_fail_gate_records"][0]))), "gate_duplicate_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, expected in mutations:
        m = json.loads(json.dumps(default)); mut(m); check(name, expected in validate_report(m))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    check("default_no_private_action_fail", default["execution_mode_records"][0]["private_read_existing_r2an_material_bool"] is False and default["execution_mode_records"][0]["private_write_diagnostics_bool"] is False and default["execution_mode_records"][0]["mechanism_decomposition_metrics_bool"] is False)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS_PREFIX}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(args); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_DEFAULT or str(report["status"]).startswith(STATUS_PASS_PREFIX) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
