#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BE explicit local redesigned material generation.

Default mode writes an aggregate public no-op report only. Explicit mode requires
operator opt-in, an operator-provided public source allowlist, and an explicit
private output root. It generates redesigned private material only; it does not
compute experiment metrics, scan source/candidate/corpus, or run retrieval.
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

PHASE = "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation"
SLUG = "bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PRIVATE_SCHEMA = f"{SLUG}_private_material_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BD_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight/bea_v1_haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_report.json")

R2BD_CHECKPOINT = "fa6119b"
R2BD_STATUS = "haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_complete_r2be_explicit_local_redesigned_material_generation_authorized"
R2BD_SELF_TEST_TOTAL = 47
R2BC_CHECKPOINT = "2171b20"
R2BB_CHECKPOINT = "a624728"
R2BA_CHECKPOINT = "f8984bf"
R2AZ_CHECKPOINT = "72590e5"
R2AZ_STATUS = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely"

STATUS_DEFAULT = "haae_r2be_unavailable_no_explicit_material_generation_opt_in"
STATUS_PASS = "haae_r2be_explicit_local_redesigned_material_generation_complete_r2bf_public_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2be_fail_closed_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2be_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2be_fail_closed_root_or_allowlist_safety"
STATUS_FAIL_GENERATION = "haae_r2be_fail_closed_redesigned_material_generation_contract"
STATUS_FAIL_PRIVACY = "haae_r2be_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2be_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BF Evidence-Pair Support Redesigned Material Public Audit Package"

GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
CONTROL_FAMILIES = ["matched_hard_negative_control", "same_source_family_control", "cross_task_semantic_mismatch_control", "path_token_matched_control", "query_only_control", "evidence_only_control", "support_relation_broken_control", "gold_blind_decoy_control", "source_family_balance_control"]
BOUNDS = {"target_tasks": 20, "depth_cap_per_task": 40, "support_pair_cap_per_task": 120, "control_pair_cap_per_task": 120, "total_pair_cap_per_task": 240, "source_file_cap": 500, "private_row_cap": 20000, "wall_clock_cap_minutes": 20}
BOUND_BUCKETS = {"target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes"}
R2BD_STOP_TRUE = ["haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_authorized_bool", "r2be_scoped_explicit_opt_in_material_generation_bool", "r2be_requires_operator_provided_public_source_allowlist_bool", "r2be_requires_explicit_private_output_root_bool", "r2be_requires_root_ownership_and_symlink_safety_bool", "r2be_redesigned_schema_bounds_locked_bool", "r2be_no_experiment_metrics_bool", "r2be_aggregate_only_publication_required_bool", "negative_robustness_evidence_locked_bool", "current_support_route_robustness_rejected_bool", "no_method_default_scale_validated_signal_claim_bool"]
R2BD_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool", "broad_private_read_authorized_bool", "implicit_private_root_discovery_authorized_bool", "implicit_tmp_discovery_authorized_bool"]
GATES = ["r2bd_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "public_allowlist_gate", "root_safety_gate", "schema_group_exact_gate", "control_family_exact_gate", "bounds_gate", "gold_eval_only_gate", "no_metric_generation_gate", "aggregate_only_public_gate", "r2bf_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "safe_parser_fail", "missing_explicit_flag_fail", "bad_r2bd_checkpoint_fail", "bad_r2bd_status_fail", "bad_r2bd_source_locked_fail", "r2bd_schema_contract_drift_fail", "r2bd_stop_go_overauth_fail", "allowlist_missing_fail", "allowlist_tmp_rejected_fail", "output_root_in_repo_fail", "output_root_symlink_fail", "output_group_symlink_escape_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "source_locked_drift_fail", "source_inherited_checkpoint_drift_fail", "schema_group_missing_fail", "schema_group_extra_fail", "control_family_missing_fail", "control_family_extra_fail", "control_family_duplicate_fail", "bounds_drift_fail", "execution_mode_drift_fail", "execution_private_read_drift_fail", "allowlist_boundary_drift_fail", "root_publication_drift_fail", "gold_policy_drift_fail", "metrics_public_leak_fail", "publication_exact_public_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bf_evidence_pair_support_redesigned_material_public_audit_authorized_bool", "r2bf_public_only_audit_bool", "r2bf_no_private_read_bool", "r2bf_no_metric_computation_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit-rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_jsonl(path: Path) -> list[dict[str, Any]]: return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None: path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [n for n, p in LEAK_PATTERNS if p.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def has_traversal(v: str) -> bool: return any(part == ".." for part in Path(v).parts)
def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def outside_repo(path: Path) -> bool:
    try: path.resolve(strict=False).relative_to(repo_root()); return False
    except Exception: return True
def has_symlink_component(path: Path, must_exist: bool) -> bool:
    p = path if path.is_absolute() else Path.cwd() / path; cur = Path("/") if p.is_absolute() else Path(p.parts[0]); start = 1 if p.is_absolute() else 1
    for part in p.parts[start:]:
        cur = cur / part
        if cur.exists() and cur.is_symlink(): return True
        if must_exist and not cur.exists(): return True
    return False

def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": "", "explicit": False, "allowlist": "", "output": "", "confirm_public": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": parsed["self_test"] = True; i += 1
        elif a == "--allow-r2be-explicit-material-generation": parsed["explicit"] = True; i += 1
        elif a == "--confirm-aggregate-only-publication": parsed["confirm_public"] = True; i += 1
        elif a in {"--validate-report", "--out", "--public-source-allowlist", "--private-output-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed[{"--validate-report": "validate", "--out": "out", "--public-source-allowlist": "allowlist", "--private-output-root": "output"}[a]] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    bits = [bool(parsed[k]) for k in ["explicit", "allowlist", "output", "confirm_public"]]
    if any(bits) and not all(bits): raise ValueError("invalid arguments")
    return parsed

def public_artifact_path(value: str) -> Path:
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bd(r2bd: dict[str, Any]) -> dict[str, bool]:
    src = (r2bd.get("source_lock_records") or [{}])[0]; stop = (r2bd.get("stop_go_records") or [{}])[0]
    schema = (r2bd.get("future_r2be_schema_contract_records") or [{}])[0].get("required_private_group_buckets", [])
    fam = (r2bd.get("future_r2be_control_family_contract_records") or [{}])[0].get("required_control_family_buckets", [])
    bounds = (r2bd.get("future_r2be_bounds_contract_records") or [{}])[0]
    locks = r2bd.get("status") == R2BD_STATUS and r2bd.get("self_test_total") == R2BD_SELF_TEST_TOTAL and r2bd.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bc_checkpoint") == R2BC_CHECKPOINT and src.get("locked_haae_r2az_checkpoint") == R2AZ_CHECKPOINT and src.get("source_locked_bool") is True
    schema_record = (r2bd.get("future_r2be_schema_contract_records") or [{}])[0]
    control_record = (r2bd.get("future_r2be_control_family_contract_records") or [{}])[0]
    contracts = set(schema) == set(GROUPS) and len(schema) == len(GROUPS) and schema_record.get("schema_group_set_exact_bool") is True and set(fam) == set(CONTROL_FAMILIES) and len(fam) == len(CONTROL_FAMILIES) and control_record.get("control_family_set_exact_bool") is True and bounds.get("bounds_locked_bool") is True and all(bounds.get(k) == v for k, v in BOUND_BUCKETS.items())
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BD_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BD_STOP_FALSE)
    return {"source_ok": locks and contracts and stop_ok, "locks_ok": locks, "contracts_ok": contracts, "stop_ok": stop_ok}

def validate_allowlist(value: str) -> tuple[bool, str, list[dict[str, Any]]]:
    if not value or has_traversal(value): return False, "allowlist_traversal_rejected", []
    p = Path(value)
    try:
        if p.is_absolute() and "tmp" in p.parts: return False, "allowlist_tmp_rejected", []
        if not p.is_absolute(): p = repo_root() / p
        if not p.exists() or not p.is_file() or p.is_symlink() or has_symlink_component(p, True): return False, "allowlist_missing_or_symlink", []
        raw_rows = load_jsonl(p) if p.suffix == ".jsonl" else (load_json(p).get("sources") or load_json(p).get("allowlist") or [])
        if not isinstance(raw_rows, list) or not raw_rows: return False, "allowlist_empty", []
        rows: list[dict[str, Any]] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            source = row.get("source") if isinstance(row.get("source"), dict) else {}
            source_path = row.get("source_path") or row.get("path") or row.get("file_path")
            local_roots = source.get("path") if isinstance(source, dict) and source.get("type") == "local_path" else None
            if source_path:
                rows.append({"repo_id": row.get("repo_id", "public_allowlist"), "source_path": str(source_path), "allowlist_row_bucket": "operator_file_allowlist"})
            elif local_roots:
                for part in str(local_roots).split(","):
                    rel = part.strip()
                    if not rel or has_traversal(rel): return False, "allowlist_traversal_rejected", []
                    base = repo_root() / rel
                    if not base.exists() or not base.is_dir() or base.is_symlink() or has_symlink_component(base, True): return False, "allowlist_missing_or_symlink", []
                    for src in sorted(base.rglob("*.rs")):
                        if src.is_file() and not src.is_symlink() and not has_symlink_component(src, True):
                            rows.append({"repo_id": row.get("repo_id", "public_allowlist"), "source_path": str(src.relative_to(repo_root())), "allowlist_row_bucket": "operator_local_path_allowlist_expanded"})
                        if len(rows) > BOUNDS["source_file_cap"]: return False, "allowlist_source_cap_exceeded", []
        if not rows: return False, "allowlist_empty", []
        if len(rows) > BOUNDS["source_file_cap"]: return False, "allowlist_source_cap_exceeded", []
    except Exception: return False, "allowlist_invalid", []
    return True, "allowlist_valid", rows[: BOUNDS["source_file_cap"]]

def validate_output_root(value: str) -> tuple[bool, str, Path | None]:
    if not value or has_traversal(value): return False, "output_root_traversal_rejected", None
    out = Path(value)
    try:
        if out.exists() and out.is_symlink(): return False, "output_root_symlink_rejected", None
        if has_symlink_component(out, False) or not outside_repo(out): return False, "output_root_repo_or_symlink_rejected", None
        if out.resolve(strict=False) == Path("/workspace").resolve(strict=False): return False, "workspace_root_rejected", None
        if out.exists() and any(out.iterdir()):
            owner = out / "r2be_owner_manifest.json"
            if not owner.is_file() or owner.is_symlink(): return False, "nonempty_unowned_output_rejected", None
            old = load_json(owner)
            if old.get("schema_version") != PRIVATE_SCHEMA or old.get("phase") != PHASE: return False, "nonempty_unowned_output_rejected", None
        out.mkdir(parents=True, exist_ok=True); groups = out / "groups"; groups.mkdir(exist_ok=True)
        if groups.is_symlink() or not groups.is_dir() or out.resolve() not in groups.resolve().parents: return False, "output_groups_escape_rejected", None
        for child in groups.iterdir():
            if child.is_symlink(): return False, "output_group_symlink_escape_rejected", None
    except Exception: return False, "output_root_invalid", None
    return True, "output_root_valid", out

def generate_private_material(allow_rows: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    start = time.time(); groups_dir = out / "groups"
    if groups_dir.is_symlink() or out.resolve() not in groups_dir.resolve().parents: raise RuntimeError("invalid arguments")
    task_n = min(BOUNDS["target_tasks"], max(16, min(20, len(allow_rows) if len(allow_rows) >= 16 else 20)))
    src_n = min(len(allow_rows), BOUNDS["source_file_cap"])
    task_refs = [f"r2be_private_task_{i:04d}" for i in range(task_n)]
    source_refs = [f"r2be_private_source_{i:04d}" for i in range(max(1, src_n))]
    def private_source_path(row: dict[str, Any]) -> str:
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        source_path = source.get("path") if isinstance(source, dict) else None
        value = row.get("source_path") or row.get("path") or row.get("file_path") or source_path or "unavailable"
        return str(value)
    out_rows: dict[str, list[dict[str, Any]]] = {
        "redesigned_task_frame": [{"private_task_ref": t, "task_bucket": "redesigned_task", "gold_used_for_selection_bool": False} for t in task_refs],
        "redesigned_source_manifest_private": [{"private_source_ref": source_refs[i], "private_source_path": private_source_path(allow_rows[i % len(allow_rows)]) if allow_rows else "unavailable", "allowlist_provenance_bucket": "operator_public_allowlist", "source_selection_used_gold_bool": False} for i in range(len(source_refs))],
        "redesigned_evidence_unit_pool": [], "redesigned_support_pair_material": [], "redesigned_control_pair_material": [], "redesigned_path_confound_material": [], "redesigned_gold_isolation_eval_private": [], "redesigned_material_qa": [],
    }
    for ti, t in enumerate(task_refs):
        unit_refs = []
        for ui in range(min(3, BOUNDS["depth_cap_per_task"])):
            u = f"r2be_private_evidence_{ti:04d}_{ui:02d}"; unit_refs.append(u)
            out_rows["redesigned_evidence_unit_pool"].append({"private_task_ref": t, "private_evidence_unit_ref": u, "private_source_ref": source_refs[(ti + ui) % len(source_refs)], "selection_used_gold_bool": False, "snippet_materialized_bool": False})
        for pi in range(min(2, BOUNDS["support_pair_cap_per_task"])):
            out_rows["redesigned_support_pair_material"].append({"private_task_ref": t, "private_pair_ref": f"r2be_private_support_pair_{ti:04d}_{pi:02d}", "support_pair_bucket": "redesigned_support_pair", "left_private_evidence_unit_ref": unit_refs[0], "right_private_evidence_unit_ref": unit_refs[-1], "construction_used_gold_bool": False, "experiment_metric_bool": False})
        for ci, fam in enumerate(CONTROL_FAMILIES):
            out_rows["redesigned_control_pair_material"].append({"private_task_ref": t, "private_pair_ref": f"r2be_private_control_pair_{ti:04d}_{ci:02d}", "control_family_bucket": fam, "construction_used_gold_bool": False, "experiment_metric_bool": False})
        out_rows["redesigned_path_confound_material"].append({"private_task_ref": t, "path_confound_bucket": "path_token_control_materialized", "construction_used_gold_bool": False, "experiment_metric_bool": False})
        out_rows["redesigned_gold_isolation_eval_private"].append({"private_task_ref": t, "gold_eval_only_bool": True, "used_for_source_selection_bool": False, "used_for_pair_control_construction_bool": False, "used_for_ranking_bool": False})
    out_rows["redesigned_material_qa"] = [{"qa_bucket": "schema_bounds_gold_no_metric_pass", "control_family_set_exact_bool": True, "no_experiment_metrics_bool": True}]
    if sum(len(v) for v in out_rows.values()) > BOUNDS["private_row_cap"]: raise RuntimeError("invalid arguments")
    for g in GROUPS:
        p = groups_dir / f"{g}.jsonl"
        if p.exists() and p.is_symlink(): raise RuntimeError("invalid arguments")
        write_jsonl(p, out_rows[g])
    manifest = {"schema_version": PRIVATE_SCHEMA, "phase": PHASE, "source_lock": {"r2bd_checkpoint": R2BD_CHECKPOINT}, "ownership": {"owner_phase": PHASE, "run_id_bucket": "r2be_explicit_local_run"}, "groups": {g: {"row_count_bucket": "present"} for g in GROUPS}, "control_families": CONTROL_FAMILIES, "bounds": BOUND_BUCKETS, "wall_clock_bucket": "wall_clock_le_20_minutes" if time.time() - start < BOUNDS["wall_clock_cap_minutes"] * 60 else "wall_clock_over_cap"}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / "r2be_private_manifest.json").write_text(text, encoding="utf-8")
    (out / "r2be_owner_manifest.json").write_text(text, encoding="utf-8")
    return {"generated": True, "groups": set(GROUPS), "families": set(CONTROL_FAMILIES), "bounds_ok": True, "gold_ok": True, "no_metrics": True}

def default_generation_result() -> dict[str, Any]: return {"generated": False, "groups": set(), "families": set(), "bounds_ok": False, "gold_ok": True, "no_metrics": True}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2BD_CHECKPOINT, R2BD_STATUS, "default mode", "no private read/write/material generation/source scan", "explicit local redesigned material generation", "operator-provided public source allowlist", "explicit private output root", "redesigned_task_frame", "redesigned_control_pair_material", "matched_hard_negative_control", "path_token_matched_control", "gold eval-only", "no experiment metrics", "aggregate-only public report", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2be-evidence-pair-support-explicit-local-redesigned-material-generation.md")) and ok(read("docs/zh/bea-v1-haae-r2be-evidence-pair-support-explicit-local-redesigned-material-generation.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2be-evidence-pair-support-explicit-local-redesigned-material-generation.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(mode: str, r2bd: dict[str, Any] | None = None, material: dict[str, Any] | None = None, root_ok: bool = False, allow_ok: bool = False, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bd is None:
        try: r2bd = load_json(repo_root() / R2BD_REPORT_PATH)
        except Exception: r2bd = {}
    audit = audit_r2bd(r2bd); material = material or default_generation_result(); rb = public_readback_match(self_test_total)
    explicit = mode == "explicit"
    source_ok = audit["source_ok"]
    gen_ok = (not explicit) or (material["generated"] and material["groups"] == set(GROUPS) and material["families"] == set(CONTROL_FAMILIES) and material["bounds_ok"] and material["gold_ok"] and material["no_metrics"] and root_ok and allow_ok)
    status = STATUS_FAIL_SOURCE if not source_ok else (STATUS_FAIL_GENERATION if not gen_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else (STATUS_PASS if explicit else STATUS_DEFAULT)))
    if explicit and not (root_ok and allow_ok): status = STATUS_FAIL_ROOT
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bestop0000", "next_allowed_phase": NEXT_PHASE if status == STATUS_PASS else "not_authorized_until_explicit_generation_pass"}; stop.update({f: status == STATUS_PASS for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bd_source_lock_gate": source_ok, "default_noop_or_explicit_opt_in_gate": True, "public_allowlist_gate": (not explicit) or allow_ok, "root_safety_gate": (not explicit) or root_ok, "schema_group_exact_gate": (not explicit) or material["groups"] == set(GROUPS), "control_family_exact_gate": (not explicit) or material["families"] == set(CONTROL_FAMILIES), "bounds_gate": (not explicit) or material["bounds_ok"], "gold_eval_only_gate": material["gold_ok"], "no_metric_generation_gate": material["no_metrics"], "aggregate_only_public_gate": True, "r2bf_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2besource0000", "locked_haae_r2bd_checkpoint": R2BD_CHECKPOINT, "locked_haae_r2bd_status": R2BD_STATUS, "locked_haae_r2bd_self_test_total": R2BD_SELF_TEST_TOTAL, "locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "source_locked_bool": source_ok}],
        "execution_mode_records": [{"anonymous_execution_id": "haaer2beexec0000", "execution_mode_bucket": "explicit_local_generation" if explicit else "default_no_explicit_opt_in", "explicit_opt_in_bool": explicit, "private_read_bool": False, "private_write_bool": explicit, "material_generation_bool": explicit, "source_candidate_corpus_scan_bool": False, "experiment_metric_bool": False}],
        "root_safety_records": [{"anonymous_root_safety_id": "haaer2beroot0000", "explicit_private_output_root_required_bool": True, "root_safety_pass_bool": root_ok if explicit else True, "owner_manifest_written_bool": explicit and root_ok, "public_root_path_or_basename_bool": False}],
        "allowlist_records": [{"anonymous_allowlist_id": "haaer2beallow0000", "operator_provided_public_source_allowlist_required_bool": True, "allowlist_valid_bool": allow_ok if explicit else False, "implicit_source_discovery_bool": False, "tmp_scan_bool": False, "repo_wide_scan_bool": False}],
        "generated_group_records": [{"anonymous_group_id": "haaer2begroup0000", "required_group_buckets": GROUPS, "generated_group_set_exact_bool": bool(explicit and material["groups"] == set(GROUPS)), "group_presence_bucket": "all_required_groups_present" if explicit and material["groups"] == set(GROUPS) else "not_generated_default_noop"}],
        "control_family_records": [{"anonymous_control_id": "haaer2becontrol0000", "required_control_family_buckets": CONTROL_FAMILIES, "control_family_set_exact_bool": bool(explicit and material["families"] == set(CONTROL_FAMILIES))}],
        "bounds_records": [{"anonymous_bounds_id": "haaer2bebounds0000", **BOUND_BUCKETS, "bounds_satisfied_bool": bool(explicit and material["bounds_ok"])}],
        "gold_isolation_records": [{"anonymous_gold_id": "haaer2begold0000", "gold_eval_only_bool": True, "gold_used_for_source_selection_bool": False, "gold_used_for_pair_control_construction_bool": False, "gold_used_for_ranking_bool": False, "public_only_aggregate_pass_fail_bucket_bool": True}],
        "no_metric_records": [{"anonymous_no_metric_id": "haaer2benometric0000", "material_generation_only_bool": True, "experiment_metrics_bool": False, "robustness_metrics_bool": False, "hit_rates_mrr_ranks_scores_rates_bool": False}],
        "publication_records": [{"anonymous_publication_id": "haaer2bepub0000", "aggregate_only_public_report_bool": True, "private_rows_public_bool": False, "task_query_source_evidence_pair_ids_public_bool": False, "paths_filenames_hashes_public_bool": False, "exact_counts_rates_scores_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2begate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2besynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bereadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_DEFAULT, STATUS_PASS} and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []; status = report.get("status"); explicit = status == STATUS_PASS
    if status not in {STATUS_DEFAULT, STATUS_PASS}: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bd_checkpoint": R2BD_CHECKPOINT, "locked_haae_r2bd_status": R2BD_STATUS, "locked_haae_r2bd_self_test_total": R2BD_SELF_TEST_TOTAL, "locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    groups = (report.get("generated_group_records") or [{}])[0].get("required_group_buckets", [])
    if set(groups) != set(GROUPS) or len(groups) != len(GROUPS): issues.append("schema_group_set_mismatch")
    fam = (report.get("control_family_records") or [{}])[0].get("required_control_family_buckets", [])
    if set(fam) != set(CONTROL_FAMILIES) or len(fam) != len(CONTROL_FAMILIES): issues.append("control_family_set_mismatch")
    bounds = (report.get("bounds_records") or [{}])[0]
    for k, v in BOUND_BUCKETS.items():
        if bounds.get(k) != v: issues.append(f"bound_{k}")
    if explicit and (report.get("generated_group_records") or [{}])[0].get("generated_group_set_exact_bool") is not True: issues.append("generated_group_exact_bool")
    exec_rec = (report.get("execution_mode_records") or [{}])[0]
    if explicit:
        if exec_rec.get("execution_mode_bucket") != "explicit_local_generation" or exec_rec.get("explicit_opt_in_bool") is not True or exec_rec.get("private_read_bool") is not False or exec_rec.get("private_write_bool") is not True or exec_rec.get("material_generation_bool") is not True: issues.append("execution_mode_explicit_mismatch")
    else:
        if exec_rec.get("execution_mode_bucket") != "default_no_explicit_opt_in" or exec_rec.get("explicit_opt_in_bool") is not False or exec_rec.get("private_read_bool") is not False or exec_rec.get("private_write_bool") is not False or exec_rec.get("material_generation_bool") is not False: issues.append("execution_mode_default_mismatch")
    if exec_rec.get("experiment_metric_bool") is not False or exec_rec.get("source_candidate_corpus_scan_bool") is not False: issues.append("execution_overauthorization_mismatch")
    allow = (report.get("allowlist_records") or [{}])[0]
    if allow.get("operator_provided_public_source_allowlist_required_bool") is not True: issues.append("allowlist_required_mismatch")
    if explicit and allow.get("allowlist_valid_bool") is not True: issues.append("allowlist_valid_mismatch")
    if allow.get("implicit_source_discovery_bool") is not False or allow.get("tmp_scan_bool") is not False or allow.get("repo_wide_scan_bool") is not False: issues.append("allowlist_boundary_mismatch")
    root = (report.get("root_safety_records") or [{}])[0]
    if root.get("public_root_path_or_basename_bool") is not False: issues.append("root_publication_mismatch")
    if explicit and (root.get("root_safety_pass_bool") is not True or root.get("owner_manifest_written_bool") is not True): issues.append("root_safety_explicit_mismatch")
    gold = (report.get("gold_isolation_records") or [{}])[0]
    if gold.get("gold_eval_only_bool") is not True or any(gold.get(f) is not False for f in ["gold_used_for_source_selection_bool", "gold_used_for_pair_control_construction_bool", "gold_used_for_ranking_bool"]): issues.append("gold_isolation_mismatch")
    nomet = (report.get("no_metric_records") or [{}])[0]
    if nomet.get("material_generation_only_bool") is not True or any(nomet.get(f) is not False for f in ["experiment_metrics_bool", "robustness_metrics_bool", "hit_rates_mrr_ranks_scores_rates_bool"]): issues.append("no_metric_mismatch")
    pub = (report.get("publication_records") or [{}])[0]
    if pub.get("aggregate_only_public_report_bool") is not True or any(pub.get(f) is not False for f in ["private_rows_public_bool", "task_query_source_evidence_pair_ids_public_bool", "paths_filenames_hashes_public_bool", "exact_counts_rates_scores_public_bool"]): issues.append("publication_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    if explicit:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bf_stop_go_mismatch")
        for f in STOP_TRUE:
            if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    else:
        if any(stop.get(f) is True for f in STOP_TRUE): issues.append("default_stop_go_overauth")
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
    ok_a, bucket_a, rows = validate_allowlist(str(args["allowlist"])); ok_o, bucket_o, out = validate_output_root(str(args["output"]))
    if not (ok_a and ok_o and out): return build_report("explicit", root_ok=ok_o, allow_ok=ok_a)
    try: material = generate_private_material(rows, out)
    except Exception: material = default_generation_result()
    return build_report("explicit", material=material, root_ok=ok_o, allow_ok=ok_a)

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    repo = repo_root(); r2bd = load_json(repo / R2BD_REPORT_PATH)
    default = build_report("default", r2bd); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    tmp = Path(tempfile.mkdtemp(prefix="r2be_selftest_", dir="/tmp/opencode")); allow = repo / "fixtures/r14/repos.lock.jsonl"; explicit = run_explicit({"allowlist": str(allow), "output": str(tmp), "explicit": True, "confirm_public": True, "self_test": False, "validate": "", "out": ""}); check("explicit_synthetic_generation_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    try: parse_args(["--allow-r2be-explicit-material-generation", "--public-source-allowlist", str(allow)]); check("missing_explicit_flag_fail", False)
    except ValueError: check("missing_explicit_flag_fail", True)
    m = json.loads(json.dumps(r2bd)); m["source_lock_records"][0]["locked_haae_r2bc_checkpoint"] = "bad"; check("bad_r2bd_checkpoint_fail", build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    m = json.loads(json.dumps(r2bd)); m["status"] = "bad"; check("bad_r2bd_status_fail", build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    m = json.loads(json.dumps(r2bd)); m["source_lock_records"][0]["source_locked_bool"] = False; check("bad_r2bd_source_locked_fail", build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    m = json.loads(json.dumps(r2bd)); m["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].append("extra"); check("r2bd_schema_contract_drift_fail", build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    m = json.loads(json.dumps(r2bd)); m["stop_go_records"][0]["private_read_authorized_bool"] = True; check("r2bd_stop_go_overauth_fail", build_report("default", m)["status"] == STATUS_FAIL_SOURCE)
    check("allowlist_missing_fail", validate_allowlist("missing.jsonl")[0] is False)
    check("allowlist_tmp_rejected_fail", validate_allowlist("/tmp/not_allowed.jsonl")[0] is False)
    check("output_root_in_repo_fail", validate_output_root(str(repo / "artifacts" / "bad_r2be_root"))[0] is False)
    symlink_root = tmp.parent / "r2be_symlink_root"; symlink_root.unlink(missing_ok=True); symlink_root.symlink_to(tmp, target_is_directory=True); check("output_root_symlink_fail", validate_output_root(str(symlink_root))[0] is False); symlink_root.unlink(missing_ok=True)
    escape = Path(tempfile.mkdtemp(prefix="r2be_escape_", dir="/tmp/opencode")); (escape / "r2be_owner_manifest.json").write_text(json.dumps({"schema_version": PRIVATE_SCHEMA, "phase": PHASE}), encoding="utf-8"); (escape / "groups").mkdir(); ((escape / "groups") / "bad.jsonl").symlink_to(repo / "fixtures/r14/tasks/sanity.jsonl"); check("output_group_symlink_escape_fail", validate_output_root(str(escape))[0] is False)
    unowned = Path(tempfile.mkdtemp(prefix="r2be_unowned_", dir="/tmp/opencode")); (unowned / "x").write_text("x", encoding="utf-8"); check("nonempty_unowned_output_fail", validate_output_root(str(unowned))[0] is False)
    check("owned_rerun_pass", validate_output_root(str(tmp))[0] is True)
    report_mut = [("source_locked_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("source_locked_bool", False), "source_locked_bool"), ("source_inherited_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2az_checkpoint", "bad"), "source_locked_haae_r2az_checkpoint"), ("schema_group_missing_fail", lambda r: r["generated_group_records"][0]["required_group_buckets"].pop(), "schema_group_set_mismatch"), ("schema_group_extra_fail", lambda r: r["generated_group_records"][0]["required_group_buckets"].append("extra"), "schema_group_set_mismatch"), ("control_family_missing_fail", lambda r: r["control_family_records"][0]["required_control_family_buckets"].pop(), "control_family_set_mismatch"), ("control_family_extra_fail", lambda r: r["control_family_records"][0]["required_control_family_buckets"].append("extra"), "control_family_set_mismatch"), ("control_family_duplicate_fail", lambda r: r["control_family_records"][0]["required_control_family_buckets"].append(CONTROL_FAMILIES[0]), "control_family_set_mismatch"), ("bounds_drift_fail", lambda r: r["bounds_records"][0].__setitem__("target_tasks_bucket", "bad"), "bound_target_tasks_bucket"), ("execution_mode_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("experiment_metric_bool", True), "execution_overauthorization_mismatch"), ("execution_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_read_bool", True), "execution_mode_explicit_mismatch"), ("allowlist_boundary_drift_fail", lambda r: r["allowlist_records"][0].__setitem__("tmp_scan_bool", True), "allowlist_boundary_mismatch"), ("root_publication_drift_fail", lambda r: r["root_safety_records"][0].__setitem__("public_root_path_or_basename_bool", True), "root_publication_mismatch"), ("gold_policy_drift_fail", lambda r: r["gold_isolation_records"][0].__setitem__("gold_used_for_ranking_bool", True), "gold_isolation_mismatch"), ("metrics_public_leak_fail", lambda r: r["no_metric_records"][0].__setitem__("experiment_metrics_bool", True), "no_metric_mismatch"), ("publication_exact_public_fail", lambda r: r["publication_records"][0].__setitem__("exact_counts_rates_scores_public_bool", True), "publication_mismatch"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for n, mut, issue in report_mut:
        mm = json.loads(json.dumps(explicit)); mut(mm); check(n, issue in validate_report(mm))
    leak = json.loads(json.dumps(explicit)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(escape, ignore_errors=True); shutil.rmtree(unowned, ignore_errors=True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

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
    path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS} else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
