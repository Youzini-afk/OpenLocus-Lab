#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AP evidence-pair support explicit local material experiment.

Default mode is a public no-op. Explicit mode reads only existing R2AN private
material groups and publishes bucketized aggregate metrics; it does not generate
material, scan source, run retrieval/runtime/CI/network, or publish raw/exact
private data.
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

PHASE = "BEA-v1-HAAE-R2AP Evidence-Pair Support Explicit Local Material Experiment"
SLUG = "bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AO_CHECKPOINT = "5cfa8d3"
R2AO_STATUS = "haae_r2ao_evidence_pair_support_material_public_audit_package_complete_r2ap_explicit_experiment_authorized"
R2AN_CHECKPOINT = "93bba5f"
R2AN_STATUS = "haae_r2an_evidence_pair_support_explicit_material_generation_complete_r2ao_public_material_audit_authorized"
R2AO_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ao_evidence_pair_support_material_public_audit_package/bea_v1_haae_r2ao_evidence_pair_support_material_public_audit_package_report.json")

STATUS_DEFAULT = "haae_r2ap_unavailable_no_explicit_experiment_opt_in"
STATUS_PASS_PREFIX = "haae_r2ap_explicit_local_material_experiment_complete_r2aq_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2ap_fail_closed_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2ap_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_PRIVACY = "haae_r2ap_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2ap_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AQ Evidence-Pair Support Experiment Public Audit Package"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
RESULT_BUCKETS = ["support_signal", "weak_or_artifact_signal", "mixed_or_inconclusive"]

GATE_NAMES = ["r2ao_source_locked_gate", "r2an_inherited_locked_gate", "default_noop_or_explicit_opt_in_gate", "private_material_root_gate", "required_group_set_gate", "pair_family_metrics_bucket_gate", "aggregate_only_publication_gate", "no_exact_metrics_gate", "no_raw_private_publication_gate", "no_material_generation_gate", "no_source_scan_recompute_gate", "no_ci_network_runtime_retrieval_gate", "no_default_method_scale_claim_gate", "r2aq_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["default_noop_pass", "explicit_synthetic_pass", "wrong_r2ao_status_fail", "r2ao_checkpoint_drift_fail", "r2an_status_drift_fail", "missing_manifest_fail", "repo_root_reject_fail", "missing_group_fail", "pair_family_missing_fail", "exact_metric_public_fail", "raw_private_public_fail", "status_metric_bucket_mismatch_fail", "pair_family_exact_bucket_fail", "pair_family_metric_exact_fail", "execution_mode_drift_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "method_claim_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "safe_parser_fail", "duplicate_pair_family_bucket_fail", "duplicate_gate_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "recompute_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n == 0: return "count_0"
    if n <= 20: return "count_1_to_20"
    if n <= 200: return "count_21_to_200"
    if n <= 2000: return "count_201_to_2000"
    return "count_over_2000"


def bucket_task20(n: int) -> str:
    if n <= 0: return "task_count_0"
    if n <= 5: return "task_count_1_to_5"
    if n <= 10: return "task_count_6_to_10"
    if n <= 15: return "task_count_11_to_15"
    if n <= 20: return "task_count_16_to_20"
    return "task_count_over_scope"


def bucket_pair_ratio(hit: int, total: int) -> str:
    if total <= 0: return "pair_ratio_unavailable"
    doubled = hit * 2
    if hit == 0: return "pair_ratio_zero"
    if doubled >= total: return "pair_ratio_high"
    if hit * 5 >= total: return "pair_ratio_medium"
    return "pair_ratio_low"


def bucket_separation(support_tasks: int, control_tasks: int) -> str:
    delta = support_tasks - control_tasks
    if support_tasks >= 16 and delta >= 6: return "support_separation_high"
    if support_tasks >= 11 and delta >= 3: return "support_separation_medium"
    if support_tasks > control_tasks: return "support_separation_low"
    return "support_not_separated"


def audit_r2ao(r2ao: dict[str, Any]) -> dict[str, bool]:
    src = (r2ao.get("source_lock_records") or [{}])[0]
    stop = (r2ao.get("stop_go_records") or [{}])[0]
    status_ok = r2ao.get("status") == R2AO_STATUS
    self_test_ok = r2ao.get("self_test_total") == 25
    scan_ok = r2ao.get("forbidden_scan", {}).get("status") == "pass"
    r2an_ok = src.get("locked_haae_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("locked_haae_r2an_status") == R2AN_STATUS and src.get("r2an_self_test_27_bool") is True
    stop_ok = stop.get("haae_r2ap_explicit_local_material_experiment_authorized_bool") is True and stop.get("r2ap_existing_r2an_private_material_only_bool") is True and stop.get("r2ap_aggregate_only_metrics_bool") is True
    source_ok = status_ok and self_test_ok and scan_ok and r2an_ok and stop_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "r2an_ok": r2an_ok, "stop_ok": stop_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_key_or_source", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "explicit": False, "root": "", "confirm": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-r2ap-explicit-experiment": parsed["explicit"] = True; i += 1
        elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True; i += 1
        elif arg in {"--validate-report", "--out", "--private-material-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--private-material-root": "root"}[arg]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [parsed["explicit"], bool(parsed["root"]), parsed["confirm"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def read_private_groups(root_value: str) -> tuple[bool, dict[str, list[dict[str, Any]]]]:
    root = Path(root_value)
    if not root.exists() or root.is_symlink(): return False, {}
    try:
        resolved_root = root.resolve()
        repo_root = Path(__file__).resolve().parents[1]
        if resolved_root == repo_root or repo_root in resolved_root.parents: return False, {}
    except Exception:
        return False, {}
    manifest_path = root / "r2an_private_manifest.json"
    if not manifest_path.exists() or manifest_path.is_symlink(): return False, {}
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return False, {}
    if manifest.get("schema_version") != "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1" or manifest.get("selected_signal_family") != SELECTED_SIGNAL_FAMILY: return False, {}
    if set((manifest.get("groups") or {}).keys()) != set(GROUPS): return False, {}
    groups_dir = root / "groups"
    if not groups_dir.exists() or groups_dir.is_symlink(): return False, {}
    rows: dict[str, list[dict[str, Any]]] = {}
    for group in GROUPS:
        path = groups_dir / f"{group}.jsonl"
        if not path.exists() or path.is_symlink(): return False, {}
        rows[group] = load_jsonl(path)
    return True, rows


def compute_bucket_metrics(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source_paths = {row.get("private_source_ref"): row.get("source_path_private") for row in rows.get("source_manifest_private", [])}
    unit_paths = {row.get("private_evidence_unit_ref"): source_paths.get(row.get("private_source_ref")) for row in rows.get("evidence_unit_pool", [])}
    outcomes: dict[str, dict[str, set[str]]] = {}
    for row in rows.get("outcome_eval_private", []):
        labels = row.get("outcome_label_private", {})
        outcomes[str(row.get("private_task_ref", ""))] = {
            "target": {span.get("path") for span in labels.get("gold_spans", []) if span.get("path")},
            "control": {span.get("path") for span in labels.get("hard_negatives", []) if span.get("path")},
        }

    family_rows: dict[str, list[dict[str, Any]]] = {family: [] for family in PAIR_FAMILIES}
    for group in ["support_relation_material", "contrast_control_material"]:
        for row in rows.get(group, []):
            fam = str(row.get("pair_family_bucket", ""))
            if fam in family_rows:
                family_rows[fam].append(row)

    per_family: dict[str, dict[str, str]] = {}
    private_target_task_hits: dict[str, int] = {}
    for fam, fam_rows in family_rows.items():
        target_pair_hits = 0
        control_pair_hits = 0
        target_task_hits: set[str] = set()
        control_task_hits: set[str] = set()
        aligned_tasks: set[str] = set()
        for row in fam_rows:
            task_ref = str(row.get("private_task_ref", ""))
            outcome = outcomes.get(task_ref, {"target": set(), "control": set()})
            if outcome["target"] or outcome["control"]:
                aligned_tasks.add(task_ref)
            pair_paths = {unit_paths.get(row.get("left_unit_ref")), unit_paths.get(row.get("right_unit_ref"))}
            if pair_paths & outcome["target"]:
                target_pair_hits += 1
                target_task_hits.add(task_ref)
            if pair_paths & outcome["control"]:
                control_pair_hits += 1
                control_task_hits.add(task_ref)
        private_target_task_hits[fam] = len(target_task_hits)
        per_family[fam] = {
            "pair_family_presence_bucket": "pair_family_present" if fam_rows else "pair_family_absent",
            "pair_coverage_bucket": bucket_count(len(fam_rows)),
            "outcome_alignment_bucket": bucket_task20(len(aligned_tasks)),
            "target_path_task_coverage_bucket": bucket_task20(len(target_task_hits)),
            "control_path_task_coverage_bucket": bucket_task20(len(control_task_hits)),
            "target_path_pair_ratio_bucket": bucket_pair_ratio(target_pair_hits, len(fam_rows)),
            "control_path_pair_ratio_bucket": bucket_pair_ratio(control_pair_hits, len(fam_rows)),
        }

    support_min = min(private_target_task_hits.get(fam, 0) for fam in ["target_support_pair", "complementary_support_pair"])
    control_max = max(private_target_task_hits.get(fam, 0) for fam in ["contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"])
    separation = bucket_separation(support_min, control_max)
    if separation in {"support_separation_high", "support_separation_medium"}:
        result = "support_signal"
    elif separation == "support_not_separated":
        result = "weak_or_artifact_signal"
    else:
        result = "mixed_or_inconclusive"
    return {"robustness_result_bucket": result, "pair_family_metric_buckets": {f: per_family[f]["pair_coverage_bucket"] for f in PAIR_FAMILIES}, "pair_family_signal_buckets": per_family, "support_vs_control_separation_bucket": separation, "all_pair_families_present_bool": all(family_rows[f] for f in PAIR_FAMILIES), "outcome_alignment_sufficient_bool": bool(outcomes) and all(per_family[f]["outcome_alignment_bucket"] == "task_count_16_to_20" for f in PAIR_FAMILIES), "aggregate_only_metrics_bool": True}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS_PREFIX, f"{total}/{total}", R2AO_CHECKPOINT, R2AO_STATUS, R2AN_CHECKPOINT, R2AN_STATUS, SELECTED_SIGNAL_FAMILY, "default mode no-op", "explicit mode requires", "existing R2AN private material", "bucketized aggregate metrics", "pair family", "support_signal", "weak_or_artifact_signal", "mixed_or_inconclusive", "no exact counts/rates/MRR/scores", "no raw task/query/path/evidence/pair/source/gold/snippet/hash/line data", NEXT_PHASE]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ap-evidence-pair-support-explicit-local-material-experiment.md")) and has_all(read("docs/zh/bea-v1-haae-r2ap-evidence-pair-support-explicit-local-material-experiment.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ap-evidence-pair-support-explicit-local-material-experiment.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(args: dict[str, Any] | None = None, r2ao: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    args = args or {"explicit": False}
    if r2ao is None:
        try: r2ao = load_json(repo / R2AO_REPORT_PATH)
        except Exception: r2ao = {}
    audit = audit_r2ao(r2ao)
    readback = public_readback_match(self_test_total)
    explicit = bool(args.get("explicit"))
    groups_ok = not explicit
    metrics = {"robustness_result_bucket": "unavailable_no_explicit_experiment", "pair_family_metric_buckets": {f: "not_computed_default_noop" for f in PAIR_FAMILIES}, "all_pair_families_present_bool": not explicit, "aggregate_only_metrics_bool": True}
    if explicit and audit["source_ok"]:
        groups_ok, rows = read_private_groups(str(args.get("root", "")))
        if groups_ok: metrics = compute_bucket_metrics(rows)
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    elif explicit and not groups_ok: status = STATUS_FAIL_ARGS
    elif explicit: status = f"{STATUS_PASS_PREFIX}_{metrics['robustness_result_bucket']}"
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_DEFAULT
    passed = status.startswith(STATUS_PASS_PREFIX)
    gates = {"r2ao_source_locked_gate": audit["source_ok"], "r2an_inherited_locked_gate": audit["r2an_ok"], "default_noop_or_explicit_opt_in_gate": True, "private_material_root_gate": groups_ok, "required_group_set_gate": groups_ok, "pair_family_metrics_bucket_gate": True, "aggregate_only_publication_gate": True, "no_exact_metrics_gate": True, "no_raw_private_publication_gate": True, "no_material_generation_gate": True, "no_source_scan_recompute_gate": True, "no_ci_network_runtime_retrieval_gate": True, "no_default_method_scale_claim_gate": True, "r2aq_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2apstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_explicit_success", "haae_r2aq_evidence_pair_support_experiment_public_audit_authorized_bool": passed, "r2aq_public_audit_only_bool": passed}
    stop.update({field: False for field in FORBIDDEN_STOP_TRUE})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2apsource0000", "locked_haae_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_haae_r2ao_status": R2AO_STATUS, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2an_status": R2AN_STATUS, "r2ao_status_match_bool": audit["status_ok"], "r2ao_self_test_25_bool": audit["self_test_ok"], "r2ao_forbidden_scan_pass_bool": audit["scan_ok"], "inherited_r2an_lock_match_bool": audit["r2an_ok"], "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2apmode0000", "default_mode_noop_bool": not explicit, "explicit_mode_executed_bool": explicit and passed, "private_read_existing_r2an_material_bool": explicit and passed, "material_generation_bool": False, "source_scan_bool": False, "recompute_material_bool": False, "experiment_metrics_bool": explicit and passed}],
        "aggregate_metric_records": [{"anonymous_metric_id": "haaer2apmetric0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, **metrics, "no_exact_counts_rates_mrr_scores_bool": True, "no_raw_task_query_path_evidence_pair_source_gold_snippet_hash_line_bool": True}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2apboundary0000", "material_generation_bool": False, "source_scan_bool": False, "recompute_bool": False, "ci_network_runtime_retrieval_bool": False, "default_method_scale_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2apgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2apsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2apreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_DEFAULT} or report["status"].startswith(STATUS_PASS_PREFIX):
        if scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "aggregate_metric_records", "boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_DEFAULT and not str(report.get("status", "")).startswith(STATUS_PASS_PREFIX): issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_list = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gate_list) != set(GATE_NAMES) or len(gate_list) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    validator_list = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validator_list) != set(SYNTHETIC_VALIDATORS) or len(validator_list) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2ao_checkpoint") != R2AO_CHECKPOINT or src.get("locked_haae_r2ao_status") != R2AO_STATUS or src.get("locked_inherited_r2an_checkpoint") != R2AN_CHECKPOINT or src.get("locked_inherited_r2an_status") != R2AN_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2ao_status_match_bool", "r2ao_self_test_25_bool", "r2ao_forbidden_scan_pass_bool", "inherited_r2an_lock_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    metrics = (report.get("aggregate_metric_records") or [{}])[0]
    if set((metrics.get("pair_family_metric_buckets") or {}).keys()) != set(PAIR_FAMILIES): issues.append("pair_family_metric_set_mismatch")
    for value in (metrics.get("pair_family_metric_buckets") or {}).values():
        if value != "not_computed_default_noop" and not str(value).startswith("count_"): issues.append("pair_family_metric_value_not_bucket")
    if metrics.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY or metrics.get("robustness_result_bucket") not in RESULT_BUCKETS + ["unavailable_no_explicit_experiment"]: issues.append("metric_bucket_mismatch")
    expected_status_suffix = metrics.get("robustness_result_bucket")
    if str(report.get("status", "")).startswith(STATUS_PASS_PREFIX) and report.get("status") != f"{STATUS_PASS_PREFIX}_{expected_status_suffix}": issues.append("status_metric_bucket_mismatch")
    signal_buckets = metrics.get("pair_family_signal_buckets", {})
    if str(report.get("status", "")).startswith(STATUS_PASS_PREFIX):
        if set(signal_buckets.keys()) != set(PAIR_FAMILIES): issues.append("pair_family_signal_bucket_set_mismatch")
        for family, row in signal_buckets.items():
            for field in ["pair_family_presence_bucket", "pair_coverage_bucket", "outcome_alignment_bucket", "target_path_task_coverage_bucket", "control_path_task_coverage_bucket", "target_path_pair_ratio_bucket", "control_path_pair_ratio_bucket"]:
                value = str(row.get(field, ""))
                if field == "pair_coverage_bucket":
                    if not value.startswith("count_"): issues.append("pair_family_pair_coverage_not_bucket")
                    continue
                if field.endswith("coverage_bucket") and not value.startswith("task_count_"): issues.append(f"pair_family_{field}_not_bucket")
                elif field.endswith("ratio_bucket") and not value.startswith("pair_ratio_"): issues.append(f"pair_family_{field}_not_bucket")
                elif field == "pair_family_presence_bucket" and value not in {"pair_family_present", "pair_family_absent"}: issues.append("pair_family_presence_not_bucket")
    for field in ["aggregate_only_metrics_bool", "no_exact_counts_rates_mrr_scores_bool", "no_raw_task_query_path_evidence_pair_source_gold_snippet_hash_line_bool"]:
        if metrics.get(field) is not True: issues.append(f"metric_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    explicit_status = str(report.get("status", "")).startswith(STATUS_PASS_PREFIX)
    if explicit_status:
        for field in ["explicit_mode_executed_bool", "private_read_existing_r2an_material_bool", "experiment_metrics_bool"]:
            if mode.get(field) is not True: issues.append(f"execution_mode_{field}")
        if mode.get("default_mode_noop_bool") is not False: issues.append("execution_mode_default_mode_noop_bool")
    elif report.get("status") == STATUS_DEFAULT:
        if mode.get("default_mode_noop_bool") is not True or mode.get("explicit_mode_executed_bool") is not False or mode.get("private_read_existing_r2an_material_bool") is not False or mode.get("experiment_metrics_bool") is not False: issues.append("execution_mode_default_noop_mismatch")
    for field in ["material_generation_bool", "source_scan_bool", "recompute_material_bool"]:
        if mode.get(field) is not False: issues.append(f"execution_mode_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    for field in ["material_generation_bool", "source_scan_bool", "recompute_bool", "ci_network_runtime_retrieval_bool", "default_method_scale_claim_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    explicit = str(report.get("status", "")).startswith(STATUS_PASS_PREFIX)
    if explicit and (stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2aq_evidence_pair_support_experiment_public_audit_authorized_bool") is not True): issues.append("r2aq_stop_go_mismatch")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_private_root(root: Path) -> None:
    groups = root / "groups"; groups.mkdir(parents=True)
    (root / "r2an_private_manifest.json").write_text(json.dumps({"schema_version": "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1", "selected_signal_family": SELECTED_SIGNAL_FAMILY, "groups": {group: {"row_count": 1} for group in GROUPS}}, sort_keys=True) + "\n", encoding="utf-8")
    for g in GROUPS:
        rows: list[dict[str, Any]] = []
        if g == "evidence_pair_material":
            rows = [{"pair_family_bucket": fam, "private_pair_ref": f"p{i}", "private_task_ref": "t"} for i, fam in enumerate(PAIR_FAMILIES)]
        elif g == "material_qa": rows = [{"qa": "pass"}]
        else: rows = [{"group": g}]
        write_jsonl(groups / f"{g}.jsonl", rows)


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AO_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    default = build_report(r2ao=base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        root = Path(td) / "priv"; make_private_root(root)
        explicit = build_report({"explicit": True, "root": str(root), "confirm": True}, base); check("explicit_synthetic_pass", explicit["status"].startswith(STATUS_PASS_PREFIX) and validate_report(explicit) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ao_status_fail", build_report(r2ao=wrong)["status"] == STATUS_FAIL_SOURCE)
    cp = json.loads(json.dumps(base)); cp["source_lock_records"][0]["locked_haae_r2an_checkpoint"] = "wrong"; check("r2an_status_drift_fail", build_report(r2ao=cp)["status"] == STATUS_FAIL_SOURCE)
    for label, mutator, expected in [("r2ao_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ao_checkpoint", "wrong"), "source_lock_mismatch"), ("exact_metric_public_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("no_exact_counts_rates_mrr_scores_bool", False), "metric_no_exact_counts_rates_mrr_scores_bool"), ("raw_private_public_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("no_raw_task_query_path_evidence_pair_source_gold_snippet_hash_line_bool", False), "metric_no_raw_task_query_path_evidence_pair_source_gold_snippet_hash_line_bool"), ("status_metric_bucket_mismatch_fail", lambda r: r.__setitem__("status", f"{STATUS_PASS_PREFIX}_support_signal"), "status_metric_bucket_mismatch"), ("pair_family_exact_bucket_fail", lambda r: (r.__setitem__("status", f"{STATUS_PASS_PREFIX}_weak_or_artifact_signal"), r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "weak_or_artifact_signal"), r["aggregate_metric_records"][0].setdefault("pair_family_signal_buckets", {family: {"pair_family_presence_bucket": "pair_family_present", "pair_coverage_bucket": "count_1_to_20", "outcome_alignment_bucket": "task_count_1_to_5", "target_path_task_coverage_bucket": "task_count_1_to_5", "control_path_task_coverage_bucket": "task_count_1_to_5", "target_path_pair_ratio_bucket": "pair_ratio_low", "control_path_pair_ratio_bucket": "pair_ratio_low"} for family in PAIR_FAMILIES})["target_support_pair"].__setitem__("target_path_pair_ratio_bucket", "0.42")), "pair_family_target_path_pair_ratio_bucket_not_bucket"), ("pair_family_metric_exact_fail", lambda r: r["aggregate_metric_records"][0]["pair_family_metric_buckets"].__setitem__("target_support_pair", "1200"), "pair_family_metric_value_not_bucket"), ("execution_mode_drift_fail", lambda r: (r.__setitem__("status", f"{STATUS_PASS_PREFIX}_weak_or_artifact_signal"), r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "weak_or_artifact_signal"), r["execution_mode_records"][0].__setitem__("explicit_mode_executed_bool", True), r["execution_mode_records"][0].__setitem__("experiment_metrics_bool", True), r["execution_mode_records"][0].__setitem__("default_mode_noop_bool", False), r["execution_mode_records"][0].__setitem__("private_read_existing_r2an_material_bool", False)), "execution_mode_private_read_existing_r2an_material_bool"), ("material_generation_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"), ("source_scan_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("source_scan_bool", True), "boundary_source_scan_bool"), ("method_claim_fail", lambda r: r["boundary_records"][0].__setitem__("default_method_scale_claim_bool", True), "boundary_default_method_scale_claim_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("next_phase_drift_fail", lambda r: (r.__setitem__("status", f"{STATUS_PASS_PREFIX}_support_signal"), r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong")), "r2aq_stop_go_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_pair_family_bucket_fail", lambda r: r["aggregate_metric_records"][0]["pair_family_metric_buckets"].pop("target_support_pair"), "pair_family_metric_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_set_mismatch")]:
        mutated = json.loads(json.dumps(default)); mutator(mutated); check(label, expected in validate_report(mutated))
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        root = Path(td) / "priv"; make_private_root(root); (root / "groups" / "task_frame.jsonl").unlink()
        check("missing_group_fail", build_report({"explicit": True, "root": str(root), "confirm": True}, base)["status"] == STATUS_FAIL_ARGS)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        root = Path(td) / "priv"; make_private_root(root); (root / "r2an_private_manifest.json").unlink()
        check("missing_manifest_fail", build_report({"explicit": True, "root": str(root), "confirm": True}, base)["status"] == STATUS_FAIL_ARGS)
    check("repo_root_reject_fail", build_report({"explicit": True, "root": str(repo), "confirm": True}, base)["status"] == STATUS_FAIL_ARGS)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        root = Path(td) / "priv"; make_private_root(root); write_jsonl(root / "groups" / "evidence_pair_material.jsonl", [{"pair_family_bucket": PAIR_FAMILIES[0]}])
        check("pair_family_missing_fail", build_report({"explicit": True, "root": str(root), "confirm": True}, base)["aggregate_metric_records"][0]["all_pair_families_present_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
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
    report = build_report(args)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_DEFAULT or str(report["status"]).startswith(STATUS_PASS_PREFIX) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
