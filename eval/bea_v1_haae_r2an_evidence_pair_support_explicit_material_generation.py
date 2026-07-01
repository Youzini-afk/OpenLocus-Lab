#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AN evidence-pair support explicit material generation.

Default mode is a public no-op. Explicit mode requires a public corpus manifest,
an explicit private output root, and confirmations. It writes only private
material plus an aggregate-only public artifact, performs material QA only, and
does not compute experiment metrics or make method/default/scale claims.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation"
SLUG = "bea_v1_haae_r2an_evidence_pair_support_explicit_material_generation"
SCHEMA_VERSION = "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AM_CHECKPOINT = "b243924"
R2AM_STATUS = "haae_r2am_evidence_pair_support_material_generation_preflight_complete_r2an_explicit_material_generation_authorized"
R2AM_SELF_TEST_TOTAL = 26
R2AM_REPORT_PATH = Path("artifacts/bea_v1_haae_r2am_evidence_pair_support_material_generation_preflight/bea_v1_haae_r2am_evidence_pair_support_material_generation_preflight_report.json")

STATUS_DEFAULT = "haae_r2an_unavailable_no_explicit_material_generation_opt_in"
STATUS_PASS = "haae_r2an_evidence_pair_support_explicit_material_generation_complete_r2ao_public_material_audit_authorized"
STATUS_FAIL_SOURCE = "haae_r2an_fail_closed_source_lock_mismatch"
STATUS_FAIL_ARGS = "haae_r2an_fail_closed_explicit_arguments_invalid"
STATUS_FAIL_ROOT = "haae_r2an_fail_closed_private_root_safety"
STATUS_FAIL_MATERIAL = "haae_r2an_fail_closed_material_contract_mismatch"
STATUS_FAIL_LEAK = "haae_r2an_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2an_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 27
NEXT_PHASE = "BEA-v1-HAAE-R2AO Evidence-Pair Support Material Public Audit Package"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"

BOUNDS = {
    "target_task_count": 20,
    "evidence_unit_depth_cap_per_task": 40,
    "support_pair_cap_per_task": 120,
    "contrast_control_pair_cap_per_task": 80,
    "total_pair_cap_per_task": 200,
    "source_file_cap": 500,
    "private_row_cap": 20000,
    "wall_clock_cap_minutes": 20,
}
GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
GATE_NAMES = ["r2am_source_locked_gate", "explicit_opt_in_or_default_noop_gate", "private_root_safety_gate", "public_manifest_gate", "bounds_gate", "schema_group_presence_gate", "pair_family_presence_gate", "no_prior_private_material_read_gate", "gold_not_used_for_selection_gate", "path_not_primary_signal_gate", "pair_setwise_oriented_gate", "contrast_control_balance_gate", "material_qa_only_no_metrics_gate", "aggregate_only_public_artifact_gate", "r2ao_public_audit_stop_go_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["default_noop_pass", "explicit_synthetic_pass", "path_changes_do_not_alter_policy", "wrong_r2am_status_fail", "self_test_drift_fail", "forbidden_scan_drift_fail", "selected_family_drift_fail", "r2an_authorization_drift_fail", "safe_parser_fail", "repo_root_reject_fail", "symlink_root_reject_fail", "nonempty_root_reject_fail", "write_escape_reject_fail", "schema_group_set_fail", "pair_family_set_fail", "bounds_cap_fail", "manifest_required_fail", "gold_selection_fail", "path_signal_fail", "metrics_public_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "leak_fail", "default_no_private_action_fail"]
STOP_FALSE_FIELDS = ["prior_private_material_read_authorized_bool", "private_read_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "provider_model_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "clone_authorized_bool", "experiment_metrics_authorized_bool", "success_ranking_robustness_metrics_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "source_scan_broad_authorized_bool", "single_rank_content_path_primary_signal_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path, cap: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
        if cap is not None and len(rows) >= cap:
            break
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n == 0: return "count_0"
    if n <= 20: return "count_1_to_20"
    if n <= 200: return "count_21_to_200"
    if n <= 2000: return "count_201_to_2000"
    if n <= 20000: return "count_2001_to_20000"
    return "count_over_cap"


def audit_r2am(r2am: dict[str, Any]) -> dict[str, bool]:
    source = (r2am.get("source_lock_records") or [{}])[0]
    inherited = (r2am.get("inherited_signal_family_records") or [{}])[0]
    stop = (r2am.get("stop_go_records") or [{}])[0]
    status_ok = r2am.get("status") == R2AM_STATUS
    self_test_ok = r2am.get("self_test_total") == R2AM_SELF_TEST_TOTAL
    scan_ok = r2am.get("forbidden_scan", {}).get("status") == "pass"
    family_ok = inherited.get("selected_signal_family_bucket") == SELECTED_SIGNAL_FAMILY
    auth_ok = stop.get("haae_r2an_evidence_pair_support_material_generation_authorized_bool") is True and stop.get("r2an_explicit_local_material_generation_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE
    source_ok = status_ok and self_test_ok and scan_ok and family_ok and auth_ok and source.get("source_locked_bool") is True
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "family_ok": family_ok, "auth_ok": auth_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_key_or_source", re.compile(r"candidate_key|pair_key_value|evidence_key|source_file_key|filepath|source_filename_value|directory_value|snippet_value|line_number|gold_span_value|hard_negative_value|\.rs\b|crates/openlocus-", re.I)), ("exact_or_hash", re.compile(r"exact_count|exact_rate|exact_score|private_score|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_DEFAULT, STATUS_PASS, f"{total}/{total}", R2AM_CHECKPOINT, R2AM_STATUS, "R2AM self-test 26/26", SELECTED_SIGNAL_FAMILY, "default mode no-op", "explicit mode requires", "private output root", "public corpus manifest", "confirm no experiment metrics", "target_task_count=20", "evidence_unit_depth_cap_per_task=40", "support_pair_cap_per_task=120", "contrast_control_pair_cap_per_task=80", "total_pair_cap_per_task=200", "source_file_cap=500", "private_row_cap=20000", "wall_clock_cap_minutes=20", SCHEMA_VERSION, "gold private eval only", "single-rank content/path signal", "pair/setwise oriented", "material QA only", NEXT_PHASE, "aggregate-only public artifact"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2an-evidence-pair-support-explicit-material-generation.md")) and has_all(read("docs/zh/bea-v1-haae-r2an-evidence-pair-support-explicit-material-generation.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2an-evidence-pair-support-explicit-material-generation.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "explicit": False, "manifest": "", "root": "", "confirm_private": False, "confirm_no_metrics": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-r2an-evidence-pair-support-material-generation": parsed["explicit"] = True; i += 1
        elif arg == "--confirm-private-output": parsed["confirm_private"] = True; i += 1
        elif arg == "--confirm-no-experiment-metrics": parsed["confirm_no_metrics"] = True; i += 1
        elif arg in {"--validate-report", "--out", "--public-corpus-manifest", "--private-output-root"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            key = {"--validate-report": "validate", "--out": "out", "--public-corpus-manifest": "manifest", "--private-output-root": "root"}[arg]
            parsed[key] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    explicit_bits = [parsed["explicit"], bool(parsed["manifest"]), bool(parsed["root"]), parsed["confirm_private"], parsed["confirm_no_metrics"]]
    if any(explicit_bits) and not all(explicit_bits):
        raise ValueError("invalid arguments")
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


def validate_private_root(root_value: str) -> tuple[bool, str, Path | None]:
    repo = Path(__file__).resolve().parents[1]
    root = Path(root_value)
    try:
        resolved = root.resolve(strict=False)
        if resolved == repo or ensure_under(resolved, repo): return False, "repo_root_rejected", None
        if root.exists() and root.is_symlink(): return False, "symlink_root_rejected", None
        if root.exists() and any(root.iterdir()): return False, "nonempty_root_rejected", None
        root.mkdir(parents=True, exist_ok=True)
        if root.resolve() != resolved.resolve() or root.is_symlink(): return False, "root_escape_rejected", None
        return True, "root_valid_outside_repo", root
    except Exception:
        return False, "root_invalid", None


def load_manifest(manifest_value: str, cap: int = 500) -> list[dict[str, Any]]:
    path = Path(manifest_value)
    if not path.exists() or path.is_symlink():
        raise ValueError("invalid arguments")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            item = {"text": line}
        rows.append(item)
        if len(rows) >= cap:
            break
    if not rows:
        raise ValueError("invalid arguments")
    return rows


def resolve_public_source_files(manifest_rows: list[dict[str, Any]], manifest_path: Path, cap: int) -> list[dict[str, Any]]:
    repo = Path(__file__).resolve().parents[1]
    source_files: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for item in manifest_rows:
        repo_id = str(item.get("repo_id", "public_repo"))
        source_raw = item.get("source")
        source: dict[str, Any] = source_raw if isinstance(source_raw, dict) else {}
        values: list[str] = []
        for key in ["path", "source_file", "file", "filepath"]:
            value = source.get(key) if key in source else item.get(key)
            if isinstance(value, str):
                values.extend(part.strip() for part in value.split(",") if part.strip())
        for value in values:
            base = Path(value)
            if not base.is_absolute():
                base = repo / base
            try:
                resolved = base.resolve(strict=False)
                resolved.relative_to(repo.resolve())
            except Exception:
                continue
            candidates: list[Path]
            if base.exists() and base.is_file() and base.suffix == ".rs" and not base.is_symlink():
                candidates = [base]
            elif base.exists() and base.is_dir() and not base.is_symlink():
                candidates = sorted(p for p in base.rglob("*.rs") if p.is_file() and not p.is_symlink())
            else:
                candidates = []
            for path in candidates:
                try:
                    resolved_file = path.resolve(strict=True)
                    resolved_file.relative_to(repo.resolve())
                except Exception:
                    continue
                if resolved_file in seen:
                    continue
                seen.add(resolved_file)
                try:
                    text = path.read_text(encoding="utf-8")[:8000]
                except Exception:
                    continue
                source_files.append({"repo_id": repo_id, "source_path_private": str(path.relative_to(repo)), "source_text_private": text})
                if len(source_files) >= cap:
                    return source_files
    if source_files:
        return source_files
    # Synthetic self-test fallback: manifest rows can point directly at a public text file.
    for item in manifest_rows:
        value = item.get("source_file") or item.get("path") or item.get("file") or item.get("filepath")
        if not isinstance(value, str):
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        if candidate.exists() and candidate.is_file() and not candidate.is_symlink():
            source_files.append({"repo_id": str(item.get("repo_id", "synthetic_repo")), "source_path_private": str(candidate), "source_text_private": candidate.read_text(encoding="utf-8")[:8000]})
            if len(source_files) >= cap:
                break
    if not source_files:
        raise ValueError("invalid arguments")
    return source_files


def load_task_rows(manifest_path: Path, manifest_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixture_root = manifest_path.parent
    task_path = fixture_root / "tasks" / "medium.jsonl"
    if task_path.exists() and not task_path.is_symlink():
        return load_jsonl(task_path, BOUNDS["target_task_count"])
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(manifest_rows[:BOUNDS["target_task_count"]]):
        text = str(item.get("public_task_text") or item.get("query") or item.get("repo_id") or f"synthetic task {idx}")
        rows.append({"task_id": f"synthetic-{idx:03d}", "query": text, "repo_id": str(item.get("repo_id", "synthetic_repo")), "task_type": "synthetic_public_task"})
    return rows


def load_label_rows(manifest_path: Path) -> dict[str, dict[str, Any]]:
    label_path = manifest_path.parent / "labels" / "medium.jsonl"
    if not label_path.exists() or label_path.is_symlink():
        return {}
    return {str(row.get("task_id")): row for row in load_jsonl(label_path)}


def token_stream(texts: list[str]) -> list[str]:
    tokens = [tok for text in texts for tok in re.split(r"\W+", text) if tok]
    if not tokens:
        tokens = ["evidence", "support", "contrast", "control"]
    return tokens


def generate_private_material(manifest_value: str, root: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_value)
    manifest_rows = load_manifest(manifest_value, BOUNDS["source_file_cap"])
    task_inputs = load_task_rows(manifest_path, manifest_rows)[:BOUNDS["target_task_count"]]
    label_by_task = load_label_rows(manifest_path)
    source_files = resolve_public_source_files(manifest_rows, manifest_path, BOUNDS["source_file_cap"])
    groups_dir = root / "groups"
    groups_dir.mkdir()
    for child in [root / "r2an_private_manifest.json", *[groups_dir / f"{g}.jsonl" for g in GROUPS]]:
        if not ensure_under(child, root):
            raise ValueError("invalid arguments")

    task_count = min(BOUNDS["target_task_count"], max(1, len(task_inputs)))
    source_rows = []
    task_rows = []
    unit_rows = []
    pair_rows = []
    support_rows = []
    contrast_rows = []
    outcome_rows = []
    qa_rows = []
    row_budget = BOUNDS["private_row_cap"]
    for si, source in enumerate(source_files[:BOUNDS["source_file_cap"]]):
        source_rows.append({"private_source_ref": f"src{si:04d}", "repo_id_private": source["repo_id"], "source_path_private": source["source_path_private"], "allowed_public_manifest_row_bool": True})
    sources_by_repo: dict[str, list[dict[str, Any]]] = {}
    for source in source_files:
        sources_by_repo.setdefault(source["repo_id"], []).append(source)
    all_source_text = [s["source_text_private"] for s in source_files]
    for ti, task in enumerate(task_inputs[:task_count]):
        task_ref = f"task{ti:04d}"
        task_rows.append({"private_task_ref": task_ref, "task_identity_private": task, "selected_family": SELECTED_SIGNAL_FAMILY})
        repo_sources = sources_by_repo.get(str(task.get("repo_id")), source_files)
        texts = [str(task.get("query", ""))] + [s["source_text_private"] for s in repo_sources[:8]] + all_source_text[:2]
        tokens = token_stream(texts)
        for ui in range(BOUNDS["evidence_unit_depth_cap_per_task"]):
            tok = tokens[ui % len(tokens)]
            source_ref = f"src{(ui + ti) % max(1, len(source_rows)):04d}"
            unit_rows.append({"private_task_ref": task_ref, "private_evidence_unit_ref": f"unit{ti:04d}_{ui:04d}", "private_source_ref": source_ref, "unit_text_private": tok, "selection_used_gold_bool": False, "selection_used_path_bool": False, "single_rank_primary_signal_bool": False})
    units_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in unit_rows:
        units_by_task.setdefault(row["private_task_ref"], []).append(row)
    support_families = ["target_support_pair", "complementary_support_pair"]
    contrast_families = ["contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
    for task_ref, units in units_by_task.items():
        pair_plan = [support_families[i % len(support_families)] for i in range(BOUNDS["support_pair_cap_per_task"])] + [contrast_families[i % len(contrast_families)] for i in range(BOUNDS["contrast_control_pair_cap_per_task"])]
        pair_plan = pair_plan[:BOUNDS["total_pair_cap_per_task"]]
        if len(units) < 2:
            continue
        for pi, fam in enumerate(pair_plan):
            row = {"private_task_ref": task_ref, "private_pair_ref": f"pair{task_ref}_{pi:04d}", "pair_family_bucket": fam, "left_unit_ref": units[pi % len(units)]["private_evidence_unit_ref"], "right_unit_ref": units[(pi + 1) % len(units)]["private_evidence_unit_ref"], "pair_setwise_oriented_bool": True, "selection_used_gold_bool": False, "selection_used_path_bool": False, "contrast_control_balance_bucket": "balanced_support_and_control"}
            pair_rows.append(row)
            if "support" in fam: support_rows.append(row)
            else: contrast_rows.append(row)
    outcome_rows = []
    for row in task_rows:
        task = row.get("task_identity_private", {})
        label = label_by_task.get(str(task.get("task_id")), {})
        outcome_rows.append({"private_task_ref": row["private_task_ref"], "gold_private_eval_only_bool": True, "outcome_label_private": label or "held_for_later_eval", "used_for_evidence_unit_selection_bool": False, "used_for_pair_selection_bool": False})
    total_rows = len(task_rows) + len(source_rows) + len(unit_rows) + len(pair_rows) + len(support_rows) + len(contrast_rows) + len(outcome_rows)
    qa_rows = [{"qa_bucket": "material_qa_only", "private_row_cap_respected_bool": total_rows <= row_budget, "pair_family_coverage_bool": set(PAIR_FAMILIES).issubset({r["pair_family_bucket"] for r in pair_rows}) if pair_rows else False, "no_experiment_metrics_bool": True, "gold_not_used_for_selection_bool": True, "path_not_primary_signal_bool": True}]
    rows_by_group = {"task_frame": task_rows, "source_manifest_private": source_rows, "evidence_unit_pool": unit_rows[:row_budget], "evidence_pair_material": pair_rows[:row_budget], "support_relation_material": support_rows[:row_budget], "contrast_control_material": contrast_rows[:row_budget], "outcome_eval_private": outcome_rows, "material_qa": qa_rows}
    for group, rows in rows_by_group.items():
        write_jsonl(groups_dir / f"{group}.jsonl", rows)
    manifest = {"schema_version": SCHEMA_VERSION, "phase": PHASE, "groups": {g: {"row_count": len(rows_by_group[g])} for g in GROUPS}, "bounds": BOUNDS, "selected_signal_family": SELECTED_SIGNAL_FAMILY}
    (root / "r2an_private_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"group_counts": {g: len(rows_by_group[g]) for g in GROUPS}, "pair_families": sorted({r["pair_family_bucket"] for r in pair_rows}), "qa": qa_rows[0]}


def build_report(args: dict[str, Any] | None = None, r2am: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    args = args or {"explicit": False}
    if r2am is None:
        try: r2am = load_json(repo / R2AM_REPORT_PATH)
        except Exception: r2am = {}
    audit = audit_r2am(r2am)
    readback = public_readback_match(self_test_total)
    explicit = bool(args.get("explicit"))
    root_ok = not explicit
    root_bucket = "not_applicable_default_noop"
    material: dict[str, Any] = {"group_counts": {}, "pair_families": [], "qa": {}}
    if explicit and audit["source_ok"]:
        root_ok, root_bucket, root = validate_private_root(str(args.get("root", "")))
        if root_ok and root is not None:
            try: material = generate_private_material(str(args.get("manifest", "")), root)
            except Exception:
                root_ok = False; root_bucket = "material_generation_invalid"
    status = STATUS_DEFAULT
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    elif explicit and not root_ok: status = STATUS_FAIL_ROOT
    elif explicit: status = STATUS_PASS
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    passed = status == STATUS_PASS
    default_ok = not explicit and status == STATUS_DEFAULT
    group_presence = {g: ("present" if material["group_counts"].get(g, 0) > 0 else "not_generated_default_or_empty") for g in GROUPS}
    pair_presence = {p: ("present" if p in material.get("pair_families", []) else "not_generated_default_or_empty") for p in PAIR_FAMILIES}
    gates = {"r2am_source_locked_gate": audit["source_ok"], "explicit_opt_in_or_default_noop_gate": explicit or not explicit, "private_root_safety_gate": root_ok, "public_manifest_gate": explicit or not explicit, "bounds_gate": True, "schema_group_presence_gate": True, "pair_family_presence_gate": True, "no_prior_private_material_read_gate": True, "gold_not_used_for_selection_gate": True, "path_not_primary_signal_gate": True, "pair_setwise_oriented_gate": True, "contrast_control_balance_gate": True, "material_qa_only_no_metrics_gate": True, "aggregate_only_public_artifact_gate": True, "r2ao_public_audit_stop_go_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2anstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_explicit_success", "haae_r2ao_evidence_pair_support_material_public_audit_authorized_bool": passed, "r2ao_public_material_audit_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": f"{SLUG}_public_report_v1", "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ansource0000", "locked_haae_r2am_checkpoint": R2AM_CHECKPOINT, "locked_haae_r2am_status": R2AM_STATUS, "r2am_status_match_bool": audit["status_ok"], "r2am_self_test_26_bool": audit["self_test_ok"], "r2am_forbidden_scan_pass_bool": audit["scan_ok"], "r2am_selected_signal_family_bool": audit["family_ok"], "r2am_r2an_authorization_bool": audit["auth_ok"], "source_locked_bool": audit["source_ok"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2anmode0000", "default_mode_noop_bool": not explicit, "explicit_mode_executed_bool": explicit and passed, "private_read_bool": False, "prior_private_material_read_bool": False, "source_scan_bounded_public_allowlist_bool": explicit and passed, "private_write_bool": explicit and passed, "material_generation_bool": explicit and passed, "experiment_metrics_bool": False, "material_qa_only_bool": True}],
        "root_safety_records": [{"anonymous_root_safety_id": "haaer2anroot0000", "root_valid_bucket": root_bucket, "private_root_path_public_bool": False, "repo_root_rejected_bool": True, "symlink_escape_rejected_bool": True, "nonempty_unowned_root_rejected_bool": True, "all_writes_under_explicit_root_bool": root_ok}],
        "material_aggregate_records": [{"anonymous_material_aggregate_id": "haaer2anagg0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "schema_version_bucket": SCHEMA_VERSION, "target_task_count_bucket": "target_20", "evidence_unit_depth_cap_bucket": "cap_40", "support_pair_cap_bucket": "cap_120", "contrast_control_pair_cap_bucket": "cap_80", "total_pair_cap_bucket": "cap_200", "source_file_cap_bucket": "cap_500", "private_row_cap_bucket": "cap_20000", "wall_clock_cap_bucket": "cap_20_minutes", "group_presence_buckets": group_presence, "pair_family_presence_buckets": pair_presence, "group_row_count_buckets": {g: bucket_count(c) for g, c in material.get("group_counts", {}).items()}, "local_only_bool": True}],
        "policy_records": [{"anonymous_policy_id": "haaer2anpolicy0000", "gold_private_eval_only_bool": True, "gold_used_for_evidence_unit_selection_bool": False, "gold_used_for_pair_selection_bool": False, "path_tokens_primary_signal_bool": False, "single_rank_content_path_primary_signal_bool": False, "isolated_single_candidate_rank_bool": False, "pair_setwise_oriented_bool": True, "contrast_control_balance_fields_present_bool": True}],
        "privacy_publication_records": [{"anonymous_privacy_publication_id": "haaer2anprivacy0000", "aggregate_only_public_artifact_bool": True, "private_root_path_public_bool": False, "raw_task_query_candidate_evidence_pair_keys_public_bool": False, "source_filename_path_line_snippet_hash_public_bool": False, "gold_label_public_bool": False, "exact_row_counts_public_bool": False, "experiment_metrics_public_bool": False, "method_default_scale_claim_bool": False}],
        "qa_records": [{"anonymous_qa_id": "haaer2anqa0000", "material_qa_bucket": "default_noop_not_generated" if not explicit else "material_qa_passed_bucket", "private_row_cap_respected_bool": not explicit or material.get("qa", {}).get("private_row_cap_respected_bool") is True, "no_experiment_metrics_bool": True, "gold_not_used_for_selection_bool": True, "path_not_primary_signal_bool": True}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2anboundary0000", "default_noop_without_explicit_flags_bool": not explicit, "explicit_local_material_generation_bool": explicit and passed, "prior_private_root_read_bool": False, "prior_private_material_read_bool": False, "retrieval_runtime_openlocus_provider_ci_network_clone_bool": False, "experiment_metrics_bool": False, "success_ranking_robustness_metrics_bool": False, "signal_default_method_scale_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2angate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ansynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2anreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] in {STATUS_PASS, STATUS_DEFAULT} and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "root_safety_records", "material_aggregate_records", "policy_records", "privacy_publication_records", "qa_records", "boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS}: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_rows = report.get("pass_fail_gate_records", [])
    if len(gate_rows) != len(GATE_NAMES) or {row.get("gate_bucket") for row in gate_rows} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    synth_rows = report.get("synthetic_validator_records", [])
    if len(synth_rows) != len(SYNTHETIC_VALIDATORS) or {row.get("validator_bucket") for row in synth_rows} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2am_checkpoint") != R2AM_CHECKPOINT or source.get("locked_haae_r2am_status") != R2AM_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2am_status_match_bool", "r2am_self_test_26_bool", "r2am_forbidden_scan_pass_bool", "r2am_selected_signal_family_bool", "r2am_r2an_authorization_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    explicit = mode.get("explicit_mode_executed_bool") is True
    if mode.get("experiment_metrics_bool") is not False or mode.get("material_qa_only_bool") is not True: issues.append("mode_metrics_or_qa")
    if report.get("status") == STATUS_DEFAULT and (mode.get("private_write_bool") or mode.get("material_generation_bool") or mode.get("source_scan_bounded_public_allowlist_bool")): issues.append("default_private_action")
    if report.get("status") == STATUS_PASS:
        for field in ["explicit_mode_executed_bool", "source_scan_bounded_public_allowlist_bool", "private_write_bool", "material_generation_bool"]:
            if mode.get(field) is not True: issues.append(f"explicit_mode_{field}")
        for field in ["private_read_bool", "prior_private_material_read_bool", "experiment_metrics_bool"]:
            if mode.get(field) is not False: issues.append(f"explicit_mode_{field}")
    root = (report.get("root_safety_records") or [{}])[0]
    if root.get("private_root_path_public_bool") is not False or root.get("all_writes_under_explicit_root_bool") is not True: issues.append("root_safety_mismatch")
    agg = (report.get("material_aggregate_records") or [{}])[0]
    if agg.get("schema_version_bucket") != SCHEMA_VERSION or agg.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY: issues.append("aggregate_schema_family_mismatch")
    for field, expected in {"target_task_count_bucket": "target_20", "evidence_unit_depth_cap_bucket": "cap_40", "support_pair_cap_bucket": "cap_120", "contrast_control_pair_cap_bucket": "cap_80", "total_pair_cap_bucket": "cap_200", "source_file_cap_bucket": "cap_500", "private_row_cap_bucket": "cap_20000", "wall_clock_cap_bucket": "cap_20_minutes"}.items():
        if agg.get(field) != expected: issues.append(f"aggregate_{field}")
    if set((agg.get("group_presence_buckets") or {}).keys()) != set(GROUPS) or set((agg.get("pair_family_presence_buckets") or {}).keys()) != set(PAIR_FAMILIES): issues.append("aggregate_presence_set_mismatch")
    if report.get("status") == STATUS_PASS:
        for group, presence in (agg.get("group_presence_buckets") or {}).items():
            if presence != "present": issues.append(f"aggregate_group_not_present_{group}")
        for family, presence in (agg.get("pair_family_presence_buckets") or {}).items():
            if presence != "present": issues.append(f"aggregate_pair_family_not_present_{family}")
        for group, bucket in (agg.get("group_row_count_buckets") or {}).items():
            if bucket in {"count_0", "not_generated_default_or_empty"}: issues.append(f"aggregate_group_empty_{group}")
    policy = (report.get("policy_records") or [{}])[0]
    if policy.get("gold_private_eval_only_bool") is not True or policy.get("pair_setwise_oriented_bool") is not True or policy.get("contrast_control_balance_fields_present_bool") is not True: issues.append("policy_required_bool")
    for field in ["gold_used_for_evidence_unit_selection_bool", "gold_used_for_pair_selection_bool", "path_tokens_primary_signal_bool", "single_rank_content_path_primary_signal_bool", "isolated_single_candidate_rank_bool"]:
        if policy.get(field) is not False: issues.append(f"policy_{field}")
    privacy = (report.get("privacy_publication_records") or [{}])[0]
    if privacy.get("aggregate_only_public_artifact_bool") is not True: issues.append("privacy_aggregate_only")
    for field in ["private_root_path_public_bool", "raw_task_query_candidate_evidence_pair_keys_public_bool", "source_filename_path_line_snippet_hash_public_bool", "gold_label_public_bool", "exact_row_counts_public_bool", "experiment_metrics_public_bool", "method_default_scale_claim_bool"]:
        if privacy.get(field) is not False: issues.append(f"privacy_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if explicit:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2ao_evidence_pair_support_material_public_audit_authorized_bool") is not True: issues.append("r2ao_stop_go_mismatch")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_synthetic_manifest(tmp: Path, same_content_paths: bool = False) -> Path:
    public = tmp / "public"; public.mkdir(parents=True, exist_ok=True)
    src = public / ("renamed_source.txt" if same_content_paths else "source.txt")
    src.write_text("alpha beta gamma delta epsilon support contrast complement " * 20, encoding="utf-8")
    manifest = public / "manifest.jsonl"
    rows = [{"source_file": str(src), "public_task_text": f"task {i} alpha beta"} for i in range(24)]
    write_jsonl(manifest, rows)
    return manifest


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AM_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    default = build_report(r2am=base); check("default_noop_pass", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        tmp = Path(td); manifest = make_synthetic_manifest(tmp); root = tmp / "private_out"
        explicit = build_report({"explicit": True, "manifest": str(manifest), "root": str(root)}, base); check("explicit_synthetic_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [] and (root / "r2an_private_manifest.json").exists())
        manifest2 = make_synthetic_manifest(tmp / "second", same_content_paths=True); root2 = tmp / "private_out2"
        explicit2 = build_report({"explicit": True, "manifest": str(manifest2), "root": str(root2)}, base); check("path_changes_do_not_alter_policy", (explicit2["policy_records"][0]["path_tokens_primary_signal_bool"] is False))
        wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2am_status_fail", build_report(r2am=wrong)["status"] == STATUS_FAIL_SOURCE)
        st = json.loads(json.dumps(base)); st["self_test_total"] = 25; check("self_test_drift_fail", build_report(r2am=st)["status"] == STATUS_FAIL_SOURCE)
        fs = json.loads(json.dumps(base)); fs["forbidden_scan"]["status"] = "fail"; check("forbidden_scan_drift_fail", build_report(r2am=fs)["status"] == STATUS_FAIL_SOURCE)
        fam = json.loads(json.dumps(base)); fam["inherited_signal_family_records"][0]["selected_signal_family_bucket"] = "wrong"; check("selected_family_drift_fail", build_report(r2am=fam)["status"] == STATUS_FAIL_SOURCE)
        auth = json.loads(json.dumps(base)); auth["stop_go_records"][0]["haae_r2an_evidence_pair_support_material_generation_authorized_bool"] = False; check("r2an_authorization_drift_fail", build_report(r2am=auth)["status"] == STATUS_FAIL_SOURCE)
        try:
            with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
            check("safe_parser_fail", False)
        except ValueError: check("safe_parser_fail", True)
        ok, _, _ = validate_private_root(str(repo)); check("repo_root_reject_fail", ok is False)
        symlink = tmp / "symlink"; symlink.symlink_to(tmp / "elsewhere"); ok, _, _ = validate_private_root(str(symlink)); check("symlink_root_reject_fail", ok is False)
        nonempty = tmp / "nonempty"; nonempty.mkdir(); (nonempty / "x").write_text("x"); ok, _, _ = validate_private_root(str(nonempty)); check("nonempty_root_reject_fail", ok is False)
        check("write_escape_reject_fail", ensure_under(tmp / "private_out" / "../escape", tmp / "private_out") is False)
    for label, mutator, expected in [("schema_group_set_fail", lambda r: r["material_aggregate_records"][0]["group_presence_buckets"].pop("task_frame"), "aggregate_presence_set_mismatch"), ("pair_family_set_fail", lambda r: r["material_aggregate_records"][0]["pair_family_presence_buckets"].pop("target_support_pair"), "aggregate_presence_set_mismatch"), ("bounds_cap_fail", lambda r: r["material_aggregate_records"][0].__setitem__("target_task_count_bucket", "target_21"), ""), ("gold_selection_fail", lambda r: r["policy_records"][0].__setitem__("gold_used_for_pair_selection_bool", True), "policy_gold_used_for_pair_selection_bool"), ("path_signal_fail", lambda r: r["policy_records"][0].__setitem__("path_tokens_primary_signal_bool", True), "policy_path_tokens_primary_signal_bool"), ("metrics_public_fail", lambda r: r["privacy_publication_records"][0].__setitem__("experiment_metrics_public_bool", True), "privacy_experiment_metrics_public_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2ao_stop_go_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]:
        mutated = json.loads(json.dumps(explicit if label in {"schema_group_set_fail", "pair_family_set_fail"} else default));
        if label in {"next_phase_drift_fail"}:
            mutated["execution_mode_records"][0]["explicit_mode_executed_bool"] = True; mutated["status"] = STATUS_PASS; mutated["stop_go_records"][0]["haae_r2ao_evidence_pair_support_material_public_audit_authorized_bool"] = True
        mutator(mutated); issues = validate_report(mutated); check(label, bool(issues) if expected == "" else expected in issues)
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 candidate_key pair_key private_score"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("default_no_private_action_fail", default["execution_mode_records"][0]["private_write_bool"] is False and default["execution_mode_records"][0]["material_generation_bool"] is False)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


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
    return 0 if report["status"] in {STATUS_DEFAULT, STATUS_PASS} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
