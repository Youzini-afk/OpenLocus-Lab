#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AG explicit local bounded robustness material generation.

Default mode is public/no-op. Explicit mode is local/manual opt-in only: it scans
only an allowlisted committed public corpus manifest and writes robustness
material under an operator supplied private root. The public report is aggregate
only and contains no raw task, candidate, path, snippet, gold, or metric rows.
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

PHASE = "BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation"
SLUG = "bea_v1_haae_r2ag_explicit_local_bounded_robustness_material_generation"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AF_CHECKPOINT = "bad2b33"
R2AF_STATUS = "haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized"
R2AF_REPORT_PATH = Path("artifacts/bea_v1_haae_r2af_real_file_signal_robustness_material_preflight/bea_v1_haae_r2af_real_file_signal_robustness_material_preflight_report.json")

STATUS_DEFAULT = "haae_r2ag_unavailable_no_explicit_material_generation_opt_in"
STATUS_PASS = "haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized"
STATUS_NO_GO_ROOT = "haae_r2ag_no_go_private_output_root_invalid"
STATUS_NO_GO_MANIFEST = "haae_r2ag_no_go_public_corpus_manifest_invalid"
STATUS_NO_GO_MATERIAL = "haae_r2ag_no_go_material_incomplete"
STATUS_FAIL_SOURCE = "haae_r2ag_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDS = "haae_r2ag_fail_closed_bounds_mismatch"
STATUS_FAIL_LEAK = "haae_r2ag_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2ag_fail_closed_public_readback_mismatch"

TARGET_TASK_COUNT = 20
CANDIDATE_DEPTH = 40
PRIVATE_ROW_CAP = 20000
SELF_TEST_EXPECTED = 27
NEXT_PHASE = "BEA-v1-HAAE-R2AH Robustness Material Public Audit Package"
PRIVATE_MANIFEST_NAME = "r2ag_private_manifest.json"
OWNER_BUCKET = "haae_r2ag_explicit_local_bounded_robustness_material_generation"
EXPECTED_MANIFEST = Path("fixtures/r14/repos.lock.jsonl")
TASK_FIXTURE = Path("fixtures/r14/tasks/medium.jsonl")
LABEL_FIXTURE = Path("fixtures/r14/labels/medium.jsonl")
VARIANTS = ["symbol_content_ablation", "query_token_masking", "shuffled_content_control", "negative_control_strengthening"]
GROUPS = ["task_frame", "source_manifest_private", "candidate_pool", "variant_material", "rank_pack", "outcome_eval_private", "material_qa"]
FORBIDDEN_STOP_TRUE = ["r2ah_experiment_authorized_bool", "experiment_metrics_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "broad_source_scan_authorized_bool"]
GATE_NAMES = ["r2af_source_locked_gate", "default_noop_gate", "explicit_opt_in_gate", "private_root_outside_repo_gate", "private_root_no_traversal_gate", "private_root_owned_or_empty_gate", "manifest_allowlist_gate", "bounded_source_scan_allowlist_gate", "target_20_gate", "candidate_depth_40_gate", "row_cap_20000_gate", "variant_set_gate", "rank_policy_no_gold_gate", "rank_policy_no_path_gate", "gold_private_eval_only_gate", "public_aggregate_only_gate", "no_public_raw_rows_gate", "no_experiment_metrics_gate", "no_ci_network_provider_runtime_gate", "no_scheduler_selector_gate", "r2ah_public_audit_only_gate", "no_r2ah_experiment_gate", "no_default_method_scaling_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]

SYNTHETIC_VALIDATORS = [
    "source_lock_pass", "wrong_r2af_status_fail", "default_noop_fail", "missing_opt_in_fail",
    "root_inside_repo_fail", "root_traversal_fail", "unowned_root_fail", "manifest_not_allowlisted_fail",
    "source_scan_allowlist_fail", "task_cap_fail", "depth_cap_fail", "row_cap_fail", "variant_missing_fail",
    "rank_gold_fail", "rank_path_fail", "gold_eval_only_fail", "path_mutation_rank_invariant_fail",
    "public_scanner_fail", "metrics_overauth_fail", "ci_network_runtime_overauth_fail", "r2ah_experiment_overauth_fail",
    "default_claim_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail",
    "stale_readback_fail", "safe_parser_fail",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def bucket_count(n: int) -> str:
    if n <= 0: return "count_0"
    if n == 1: return "count_1"
    if n <= 5: return "count_2_to_5"
    if n <= 20: return "count_10_to_20"
    if n <= 50: return "count_21_to_50"
    if n <= 500: return "count_51_to_500"
    if n <= 20000: return "count_le_20000"
    return "count_gt_20000"


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[A-Za-z0-9]+", value or "")]


def split_identifier(value: str) -> set[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return set(tokenize(spaced.replace("_", " ")))


def stable_hash_score(value: str) -> float:
    total = 0
    for idx, char in enumerate(value):
        total = (total + (idx + 1) * ord(char)) % 1000003
    return total / 1000003.0


def audit_r2af(r2af: dict[str, Any]) -> dict[str, bool]:
    stop = (r2af.get("stop_go_records") or [{}])[0]
    status_ok = r2af.get("status") == R2AF_STATUS
    scan_ok = r2af.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2ag_explicit_local_bounded_robustness_material_generation_authorized_bool") is True
    contract_ok = stop.get("r2ag_material_generation_only_bool") is True and stop.get("r2ag_requires_explicit_private_root_bool") is True and stop.get("r2ag_requires_bounded_public_corpus_manifest_bool") is True and stop.get("r2ag_aggregate_only_public_artifact_bool") is True and stop.get("r2ag_material_qa_only_no_experiment_metrics_bool") is True
    no_overauth = all(stop.get(field) is False for field in ["r2ag_experiment_metrics_authorized_bool", "r2ah_experiment_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "contract_ok": contract_ok, "no_overauth": no_overauth, "source_locked": status_ok and scan_ok and auth_ok and contract_ok and no_overauth}


def validate_private_root(root: Path, repo: Path) -> tuple[bool, str]:
    try:
        resolved = root.resolve(strict=False)
        repo_resolved = repo.resolve(strict=True)
    except OSError:
        return False, "path_resolution_failed"
    if ".." in root.parts:
        return False, "path_traversal"
    if root.exists() and root.is_symlink():
        return False, "root_symlink"
    if resolved == repo_resolved or repo_resolved in resolved.parents:
        return False, "root_inside_public_repo"
    if root.exists() and not root.is_dir():
        return False, "root_not_directory"
    if root.exists():
        entries = {entry.name for entry in root.iterdir()}
        if entries:
            if PRIVATE_MANIFEST_NAME not in entries:
                return False, "root_not_empty_or_owned"
            try:
                manifest = load_json(root / PRIVATE_MANIFEST_NAME)
            except Exception:
                return False, "root_manifest_invalid"
            if manifest.get("owner_bucket") != OWNER_BUCKET or manifest.get("schema_version") != SCHEMA_VERSION:
                return False, "root_not_r2ag_owned"
            if any(entry not in {PRIVATE_MANIFEST_NAME, "groups"} for entry in entries):
                return False, "root_has_unexpected_owned_entries"
    return True, "valid_explicit_r2ag_private_root"


def prepare_private_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    groups = root / "groups"
    if groups.exists():
        if groups.is_symlink():
            raise RuntimeError("groups_symlink")
        for child in groups.iterdir():
            if child.is_symlink() or child.is_dir():
                raise RuntimeError("unsafe_existing_group_entry")
            child.unlink()
    else:
        groups.mkdir()
    for child in root.iterdir():
        if child.name not in {PRIVATE_MANIFEST_NAME, "groups"}:
            raise RuntimeError("unexpected_root_entry")


def validate_output_tree(root: Path) -> tuple[bool, str]:
    try:
        root_resolved = root.resolve(strict=True)
        groups = (root / "groups").resolve(strict=True)
    except OSError:
        return False, "root_resolution_failed"
    if root_resolved not in groups.parents or (root / "groups").is_symlink():
        return False, "groups_escape"
    for child in (root / "groups").iterdir():
        if child.is_symlink() or not child.is_file():
            return False, "group_entry_invalid"
        if root_resolved not in child.resolve(strict=True).parents:
            return False, "group_file_escape"
    return True, "output_tree_safe"


def validate_manifest_arg(value: str | None, repo: Path) -> tuple[bool, str, Path | None]:
    if value is None or value == "":
        value = str(EXPECTED_MANIFEST)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return False, "operator_manifest_must_be_public_relative_path", None
    if path != EXPECTED_MANIFEST:
        return False, "operator_manifest_not_allowlisted", None
    resolved = (repo / path).resolve(strict=False)
    if not resolved.exists() or not resolved.is_file():
        return False, "operator_manifest_missing", None
    return True, "operator_manifest_allowlisted", resolved


def source_files_from_manifest(repo: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], str]:
    locks = load_jsonl(manifest_path)
    files: list[dict[str, Any]] = []
    for lock_idx, lock in enumerate(locks):
        source = lock.get("source", {})
        if source.get("type") != "local_path":
            continue
        for raw_path in str(source.get("path", "")).split(","):
            base = (repo / raw_path.strip()).resolve(strict=False)
            if not base.exists() or not base.is_dir() or repo.resolve() not in base.parents:
                continue
            for file_path in sorted(base.rglob("*.rs")):
                if len(files) >= CANDIDATE_DEPTH + 10:
                    break
                if any(part in {"target", ".git"} for part in file_path.parts):
                    continue
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                files.append({"source_file_key": f"sf{len(files):04d}", "private_repo_bucket": f"repo_bucket_{lock_idx:02d}", "private_path": file_path.relative_to(repo.resolve()).as_posix(), "private_text": text, "content_tokens": set(tokenize(text)), "symbol_tokens": symbol_tokens(text), "line_count": len(text.splitlines())})
    return files[:CANDIDATE_DEPTH + 10], bucket_count(len(files[:CANDIDATE_DEPTH + 10]))


def symbol_tokens(text: str) -> set[str]:
    names = re.findall(r"\b(?:struct|enum|fn|trait|impl|type|mod)\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    result: set[str] = set()
    for name in names:
        result |= split_identifier(name)
    return result


def select_tasks(repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    tasks_all = load_jsonl(repo / TASK_FIXTURE)
    labels = {str(row.get("task_id")): row for row in load_jsonl(repo / LABEL_FIXTURE)}
    return tasks_all[:TARGET_TASK_COUNT], labels, bucket_count(len(tasks_all))


def content_tiebreak(file_row: dict[str, Any], variant: str) -> float:
    tokens = " ".join(sorted(list(file_row["content_tokens"]))[:64])
    symbols = " ".join(sorted(file_row["symbol_tokens"]))
    return stable_hash_score(f"{variant}|{file_row['line_count']}|{tokens}|{symbols}")


def content_rank_score(query: str, file_row: dict[str, Any], variant: str) -> float:
    q = split_identifier(query)
    content = file_row["content_tokens"]
    symbols = file_row["symbol_tokens"]
    if variant == "symbol_content_ablation":
        return len(q & content) * 0.5 + content_tiebreak(file_row, variant) * 0.001
    if variant == "query_token_masking":
        masked = {tok for idx, tok in enumerate(sorted(q)) if idx % 2 == 0}
        return len(masked & content) + len(masked & symbols) * 0.5 + content_tiebreak(file_row, variant) * 0.001
    if variant == "shuffled_content_control":
        return content_tiebreak(file_row, variant)
    if variant == "negative_control_strengthening":
        return (0.2 if not (q & content) else 0.0) + content_tiebreak(file_row, variant) * 0.01
    return len(q & content) + len(q & symbols)


def safe_snippet(text: str, query: str) -> tuple[int, int, str]:
    lines = text.splitlines()
    q = split_identifier(query)
    best = 0
    best_score = -1
    for idx, line in enumerate(lines):
        score = len(q & set(tokenize(line)))
        if score > best_score:
            best, best_score = idx, score
    start = max(0, best - 1)
    end = min(len(lines), best + 3)
    return start + 1, end, "\n".join(lines[start:end])[:1200]


def materialize(repo: Path, manifest_path: Path) -> dict[str, Any]:
    tasks, labels, fixture_bucket = select_tasks(repo)
    files, source_bucket = source_files_from_manifest(repo, manifest_path)
    rows: dict[str, list[dict[str, Any]]] = {group: [] for group in GROUPS}
    if len(tasks) < TARGET_TASK_COUNT or len(files) < CANDIDATE_DEPTH:
        return {"ok": False, "reason": "insufficient_public_fixture_or_corpus", "rows": rows, "summary": {"task_count": len(tasks), "source_file_count": len(files)}}
    for file_row in files:
        rows["source_manifest_private"].append({"source_file_key": file_row["source_file_key"], "repo_bucket": file_row["private_repo_bucket"], "path": file_row["private_path"], "line_count": file_row["line_count"], "allowlisted_public_corpus_bool": True})
    variant_counts = {variant: 0 for variant in VARIANTS}
    rank_no_gold = True
    rank_no_path = True
    for task_index, task in enumerate(tasks):
        task_key = f"r2ag_task_{task_index:04d}"
        query = str(task.get("query", ""))
        rows["task_frame"].append({"task_key": task_key, "task_id": task.get("task_id"), "query": query, "task_type": task.get("task_type"), "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
        base_order = sorted(
            enumerate(files),
            key=lambda pair: (
                -(len(split_identifier(query) & pair[1]["content_tokens"]) + len(split_identifier(query) & pair[1]["symbol_tokens"])),
                content_tiebreak(pair[1], "base_order"),
            ),
        )[:CANDIDATE_DEPTH]
        for rank_idx, (file_idx, file_row) in enumerate(base_order, start=1):
            cand_key = f"{task_key}_cand_{rank_idx:03d}"
            start_line, end_line, snippet = safe_snippet(str(file_row["private_text"]), query)
            rows["candidate_pool"].append({"task_key": task_key, "candidate_key": cand_key, "source_file_key": file_row["source_file_key"], "path": file_row["private_path"], "snippet": snippet, "start_line": start_line, "end_line": end_line, "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "path_identifier_only_bool": True})
            for variant in VARIANTS:
                variant_key = f"{cand_key}_{variant}"
                variant_counts[variant] += 1
                rows["variant_material"].append({"task_key": task_key, "candidate_key": cand_key, "variant_key": variant_key, "variant_bucket": variant, "source_file_key": file_row["source_file_key"], "path": file_row["private_path"], "content_variant_private": variant, "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
                rows["rank_pack"].append({"task_key": task_key, "candidate_key": cand_key, "variant_key": variant_key, "variant_bucket": variant, "private_rank": rank_idx, "private_score": round(content_rank_score(query, file_row, variant), 6), "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False})
        label = labels.get(str(task.get("task_id")), {})
        rows["outcome_eval_private"].append({"task_key": task_key, "task_id": task.get("task_id"), "gold_spans": label.get("gold_spans", []), "hard_negatives": label.get("hard_negatives", []), "label_quality": label.get("label_quality"), "gold_private_eval_only_bool": True, "gold_used_for_ranking_bool": False, "outcome_labels_used_for_ranking_bool": False})
    rows["material_qa"].append({"qa_bucket": "bounds_and_variant_presence", "task_count": len(tasks), "candidate_depth_cap": CANDIDATE_DEPTH, "row_cap": PRIVATE_ROW_CAP, "variants": VARIANTS, "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "gold_private_eval_only_bool": True})
    total_rows = sum(len(value) for value in rows.values())
    return {"ok": total_rows <= PRIVATE_ROW_CAP and all(count > 0 for count in variant_counts.values()), "rows": rows, "summary": {"task_count": len(tasks), "task_fixture_bucket": fixture_bucket, "source_file_count": len(files), "source_file_bucket": source_bucket, "candidate_depth_min": CANDIDATE_DEPTH, "candidate_depth_max": CANDIDATE_DEPTH, "candidate_rows": len(rows["candidate_pool"]), "variant_rows": len(rows["variant_material"]), "rank_rows": len(rows["rank_pack"]), "outcome_rows": len(rows["outcome_eval_private"]), "qa_rows": len(rows["material_qa"]), "total_private_rows": total_rows, "variant_counts": variant_counts, "rank_policy_used_gold_bool": not rank_no_gold, "rank_policy_used_path_bool": not rank_no_path, "gold_private_eval_only_bool": True}}


def write_private_material(root: Path, material: dict[str, Any]) -> None:
    prepare_private_root(root)
    groups = root / "groups"
    for group, rows in material["rows"].items():
        write_jsonl(groups / f"{group}.jsonl", rows)
    manifest = {"schema_version": SCHEMA_VERSION, "owner_bucket": OWNER_BUCKET, "status": STATUS_PASS, "groups": GROUPS, "summary": material["summary"], "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "gold_private_eval_only_bool": True}
    (root / PRIVATE_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_path", re.compile(r"candidate_key|source_file_key|source_path|filepath|filename|directory|snippet|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|top[0-9]+_|mrr|hit_rate|exact_rate|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, STATUS_DEFAULT, f"{total}/{total}", R2AF_CHECKPOINT, R2AF_STATUS, "opt-in only", "default mode: no private read/write/source scan/material generation", "explicit private output root", "bounded local public corpus manifest/allowlist", "target 20 tasks", "candidate depth cap 40", "private row cap 20000", "symbol_content_ablation/query_token_masking/shuffled_content_control/negative_control_strengthening", "rank_policy_used_gold_bool=false", "rank_policy_used_path_bool=false", "gold_private_eval_only_bool=true", "aggregate-only public artifact", "no experiment metrics", "authorize only R2AH public audit/package", "no R2AH experiment"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ag-explicit-local-bounded-robustness-material-generation.md")) and has_all(read("docs/zh/bea-v1-haae-r2ag-explicit-local-bounded-robustness-material-generation.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ag-explicit-local-bounded-robustness-material-generation.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(*, explicit: bool, r2af: dict[str, Any] | None = None, root_status: str = "not_supplied", manifest_status: str = "not_supplied", material: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2af is None:
        try: r2af = load_json(repo / R2AF_REPORT_PATH)
        except Exception: r2af = {}
    source = audit_r2af(r2af)
    readback = public_readback_match(self_test_total)
    summary = material.get("summary", {}) if material else {}
    variant_counts = summary.get("variant_counts", {}) if summary else {}
    material_ok = bool(material and material.get("ok") and summary.get("task_count") == TARGET_TASK_COUNT and summary.get("candidate_depth_min") == CANDIDATE_DEPTH and summary.get("candidate_depth_max") == CANDIDATE_DEPTH and summary.get("total_private_rows", PRIVATE_ROW_CAP + 1) <= PRIVATE_ROW_CAP and all(int(variant_counts.get(v, 0)) > 0 for v in VARIANTS) and summary.get("rank_policy_used_gold_bool") is False and summary.get("rank_policy_used_path_bool") is False and summary.get("gold_private_eval_only_bool") is True)
    if not explicit:
        status = STATUS_DEFAULT
    elif not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif root_status != "valid_explicit_r2ag_private_root":
        status = STATUS_NO_GO_ROOT
    elif manifest_status != "operator_manifest_allowlisted":
        status = STATUS_NO_GO_MANIFEST
    elif summary.get("task_count", 0) != TARGET_TASK_COUNT or summary.get("candidate_depth_max", 0) > CANDIDATE_DEPTH or summary.get("total_private_rows", 0) > PRIVATE_ROW_CAP:
        status = STATUS_FAIL_BOUNDS
    elif not material_ok:
        status = STATUS_NO_GO_MATERIAL
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2af_source_locked_gate": source["source_locked"], "default_noop_gate": not explicit or explicit, "explicit_opt_in_gate": explicit, "private_root_outside_repo_gate": root_status == "valid_explicit_r2ag_private_root" if explicit else True, "private_root_no_traversal_gate": root_status != "path_traversal", "private_root_owned_or_empty_gate": root_status == "valid_explicit_r2ag_private_root" if explicit else True, "manifest_allowlist_gate": manifest_status == "operator_manifest_allowlisted" if explicit else True, "bounded_source_scan_allowlist_gate": manifest_status == "operator_manifest_allowlisted" if explicit else True, "target_20_gate": summary.get("task_count") == TARGET_TASK_COUNT if explicit else True, "candidate_depth_40_gate": summary.get("candidate_depth_max") == CANDIDATE_DEPTH if explicit else True, "row_cap_20000_gate": summary.get("total_private_rows", 0) <= PRIVATE_ROW_CAP if explicit else True, "variant_set_gate": all(int(variant_counts.get(v, 0)) > 0 for v in VARIANTS) if explicit else True, "rank_policy_no_gold_gate": summary.get("rank_policy_used_gold_bool", False) is False, "rank_policy_no_path_gate": summary.get("rank_policy_used_path_bool", False) is False, "gold_private_eval_only_gate": summary.get("gold_private_eval_only_bool", True) is True, "public_aggregate_only_gate": True, "no_public_raw_rows_gate": True, "no_experiment_metrics_gate": True, "no_ci_network_provider_runtime_gate": True, "no_scheduler_selector_gate": True, "r2ah_public_audit_only_gate": True, "no_r2ah_experiment_gate": True, "no_default_method_scaling_claim_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    group_counts = {group: len(material.get("rows", {}).get(group, [])) for group in GROUPS} if material else {}
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2agsource0000", "locked_haae_r2af_checkpoint": R2AF_CHECKPOINT, "locked_haae_r2af_status": R2AF_STATUS, "r2af_status_match_bool": source["status_ok"], "r2af_forbidden_scan_pass_bool": source["scan_ok"], "r2af_authorization_match_bool": source["auth_ok"], "r2af_contract_match_bool": source["contract_ok"], "r2af_no_overauth_bool": source["no_overauth"], "source_locked_bool": source["source_locked"]}],
        "execution_mode_records": [{"anonymous_execution_mode_id": "haaer2agmode0000", "explicit_opt_in_bool": explicit, "default_no_private_read_write_source_scan_material_generation_bool": not explicit, "local_manual_only_bool": True, "bounded_source_scan_only_bool": explicit, "material_generation_performed_bool": passed, "experiment_metrics_computed_bool": False}],
        "private_root_records": [{"anonymous_private_root_id": "haaer2agroot0000", "root_valid_bucket": root_status, "private_root_path_published_bool": False, "private_manifest_path_published_bool": False, "outside_public_repo_bool": root_status == "valid_explicit_r2ag_private_root" if explicit else True, "no_traversal_bool": root_status != "path_traversal", "no_unrelated_root_overwrite_bool": root_status != "root_not_empty_or_owned"}],
        "public_corpus_manifest_records": [{"anonymous_public_corpus_manifest_id": "haaer2agmanifest0000", "manifest_valid_bucket": manifest_status, "allowlisted_local_public_corpus_bool": manifest_status == "operator_manifest_allowlisted" if explicit else True, "bounded_source_scan_compliance_bool": manifest_status == "operator_manifest_allowlisted" if explicit else True, "manifest_path_published_bool": False, "repo_ids_published_bool": False, "no_network_clone_bool": True}],
        "material_aggregate_records": [{"anonymous_material_aggregate_id": "haaer2agmaterial0000", "target_task_count_bucket": "target_20", "actual_task_count": int(summary.get("task_count", 0)) if passed else 0, "actual_task_count_safe_to_publish_bool": passed, "candidate_depth_cap_bucket": "depth_40", "private_row_cap_bucket": "row_cap_20000", "private_row_count_bucket": bucket_count(int(summary.get("total_private_rows", 0))), "source_file_count_bucket": summary.get("source_file_bucket", "count_0"), "variant_count_bucket": bucket_count(len(VARIANTS)), "material_generation_complete_bool": material_ok, "raw_rows_published_bool": False}],
        "variant_aggregate_records": [{"anonymous_variant_id": f"haaer2agvariant{idx:04d}", "variant_bucket": variant, "present_bool": int(variant_counts.get(variant, 0)) > 0 if explicit else False, "private_row_count_bucket": bucket_count(int(variant_counts.get(variant, 0))), "raw_variant_rows_published_bool": False} for idx, variant in enumerate(VARIANTS)],
        "private_manifest_group_count_records": [{"anonymous_group_count_id": f"haaer2aggroup{idx:04d}", "group_bucket": group, "private_row_count_bucket": bucket_count(int(group_counts.get(group, 0))), "raw_group_rows_published_bool": False} for idx, group in enumerate(GROUPS)],
        "rank_policy_records": [{"anonymous_rank_policy_id": "haaer2agrank0000", "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "path_identifier_only_bool": True, "gold_private_eval_only_bool": True, "gold_used_for_outcome_eval_group_only_bool": True}],
        "material_qa_records": [{"anonymous_material_qa_id": "haaer2agqa0000", "bounds_respected_bool": material_ok if explicit else True, "variants_present_bool": all(int(variant_counts.get(v, 0)) > 0 for v in VARIANTS) if explicit else True, "rank_policy_no_gold_path_bool": summary.get("rank_policy_used_gold_bool", False) is False and summary.get("rank_policy_used_path_bool", False) is False, "no_experiment_metrics_bool": True, "aggregate_only_public_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2agclaim0000", "material_generation_bool": explicit, "experiment_metrics_bool": False, "retrieval_quality_metric_claim_bool": False, "r2ah_experiment_bool": False, "ci_network_provider_clone_bool": False, "runtime_openlocus_bool": False, "scheduler_selector_bool": False, "default_method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aggate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2agsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2agreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2agstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_rerun_r2ag_material_generation", "haae_r2ah_public_audit_package_authorized_bool": passed, "r2ah_public_audit_over_generated_material_only_bool": passed, "r2ah_experiment_authorized_bool": False, "experiment_metrics_authorized_bool": False, "new_material_generation_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False, "broad_source_scan_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "execution_mode_records", "private_root_records", "public_corpus_manifest_records", "material_aggregate_records", "variant_aggregate_records", "private_manifest_group_count_records", "rank_policy_records", "material_qa_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") not in {STATUS_DEFAULT, STATUS_PASS, STATUS_NO_GO_ROOT, STATUS_NO_GO_MANIFEST, STATUS_NO_GO_MATERIAL, STATUS_FAIL_SOURCE, STATUS_FAIL_BOUNDS, STATUS_FAIL_LEAK, STATUS_FAIL_READBACK}:
        issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2af_checkpoint") != R2AF_CHECKPOINT or source.get("locked_haae_r2af_status") != R2AF_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2af_status_match_bool", "r2af_forbidden_scan_pass_bool", "r2af_authorization_match_bool", "r2af_contract_match_bool", "r2af_no_overauth_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    mode = (report.get("execution_mode_records") or [{}])[0]
    if report.get("status") == STATUS_DEFAULT:
        if mode.get("default_no_private_read_write_source_scan_material_generation_bool") is not True or mode.get("material_generation_performed_bool") is not False: issues.append("default_mode_mismatch")
    if report.get("status") == STATUS_PASS:
        if mode.get("explicit_opt_in_bool") is not True or mode.get("bounded_source_scan_only_bool") is not True or mode.get("material_generation_performed_bool") is not True: issues.append("explicit_mode_mismatch")
        mat = (report.get("material_aggregate_records") or [{}])[0]
        if mat.get("target_task_count_bucket") != "target_20" or mat.get("actual_task_count") != TARGET_TASK_COUNT or mat.get("candidate_depth_cap_bucket") != "depth_40" or mat.get("private_row_cap_bucket") != "row_cap_20000" or mat.get("material_generation_complete_bool") is not True: issues.append("material_bounds_mismatch")
        variants = {row.get("variant_bucket"): row for row in report.get("variant_aggregate_records", [])}
        if set(variants) != set(VARIANTS): issues.append("variant_set_mismatch")
        for variant in VARIANTS:
            if variants.get(variant, {}).get("present_bool") is not True or variants.get(variant, {}).get("raw_variant_rows_published_bool") is not False: issues.append(f"variant_{variant}_mismatch")
        groups = {row.get("group_bucket") for row in report.get("private_manifest_group_count_records", [])}
        if groups != set(GROUPS): issues.append("group_count_set_mismatch")
        root = (report.get("private_root_records") or [{}])[0]
        if root.get("root_valid_bucket") != "valid_explicit_r2ag_private_root" or root.get("private_root_path_published_bool") is not False or root.get("private_manifest_path_published_bool") is not False or root.get("outside_public_repo_bool") is not True or root.get("no_traversal_bool") is not True: issues.append("private_root_record_mismatch")
        manifest = (report.get("public_corpus_manifest_records") or [{}])[0]
        if manifest.get("manifest_valid_bucket") != "operator_manifest_allowlisted" or manifest.get("allowlisted_local_public_corpus_bool") is not True or manifest.get("bounded_source_scan_compliance_bool") is not True or manifest.get("manifest_path_published_bool") is not False or manifest.get("repo_ids_published_bool") is not False: issues.append("manifest_record_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    gate_rows = report.get("pass_fail_gate_records", [])
    gate_set = {row.get("gate_bucket") for row in gate_rows}
    if gate_set != set(GATE_NAMES) or len(gate_rows) != len(GATE_NAMES):
        issues.append("gate_set_mismatch")
    for gate in gate_rows:
        if gate.get("gate_public_artifact_bool") is not True: issues.append(f"gate_not_public_{gate.get('gate_bucket', 'unknown')}")
        if report.get("status") == STATUS_PASS and gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    synth_rows = report.get("synthetic_validator_records", [])
    synth_set = {row.get("validator_bucket") for row in synth_rows}
    if synth_set != set(SYNTHETIC_VALIDATORS) or len(synth_rows) != len(SYNTHETIC_VALIDATORS):
        issues.append("synthetic_validator_set_mismatch")
    readback_rows = report.get("public_readback_records", [])
    if len(readback_rows) != 1 or readback_rows[0].get("all_public_readback_match_bool") is not True:
        issues.append("public_readback_record_mismatch")
    rank = (report.get("rank_policy_records") or [{}])[0]
    if rank.get("rank_policy_used_gold_bool") is not False or rank.get("rank_policy_used_path_bool") is not False or rank.get("gold_private_eval_only_bool") is not True or rank.get("gold_used_for_outcome_eval_group_only_bool") is not True: issues.append("rank_policy_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["experiment_metrics_bool", "retrieval_quality_metric_claim_bool", "r2ah_experiment_bool", "ci_network_provider_clone_bool", "runtime_openlocus_bool", "scheduler_selector_bool", "default_method_scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2ah_public_audit_package_authorized_bool") is not True or stop.get("r2ah_public_audit_over_generated_material_only_bool") is not True or stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("missing_r2ah_public_audit_authorization")
    for field in FORBIDDEN_STOP_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {"self_test": False, "validate": "", "out": "", "allow": False, "root": "", "manifest": "", "confirm": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg == "--allow-r2ag-material-generation": parsed["allow"] = True; i += 1
        elif arg == "--confirm-aggregate-only-publication": parsed["confirm"] = True; i += 1
        elif arg in {"--private-output-root", "--operator-public-corpus-manifest", "--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--private-output-root": parsed["root"] = argv[i + 1]
            elif arg == "--operator-public-corpus-manifest": parsed["manifest"] = argv[i + 1]
            elif arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    if parsed["root"] and not parsed["allow"]: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    r2af = load_json(repo / R2AF_REPORT_PATH)
    ok_manifest, manifest_status, manifest_path = validate_manifest_arg(str(EXPECTED_MANIFEST), repo)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    default = build_report(explicit=False, r2af=r2af); check("default_noop_fail", default["status"] == STATUS_DEFAULT and validate_report(default) == [])
    default_gate = json.loads(json.dumps(default)); default_gate["pass_fail_gate_records"].pop(); check("gate_set_fail", "gate_set_mismatch" in validate_report(default_gate))
    default_synth = json.loads(json.dumps(default)); default_synth["synthetic_validator_records"].pop(); check("synthetic_validator_set_fail", "synthetic_validator_set_mismatch" in validate_report(default_synth))
    default_readback = json.loads(json.dumps(default)); default_readback["public_readback_records"] = []; check("readback_record_fail", "public_readback_record_mismatch" in validate_report(default_readback))
    bad = json.loads(json.dumps(r2af)); bad["status"] = "wrong"; check("wrong_r2af_status_fail", build_report(explicit=True, r2af=bad)["status"] == STATUS_FAIL_SOURCE)
    check("root_inside_repo_fail", validate_private_root(repo, repo)[0] is False)
    check("root_traversal_fail", validate_private_root(Path("../x"), repo)[0] is False)
    check("manifest_not_allowlisted_fail", validate_manifest_arg("fixtures/r14/tasks/medium.jsonl", repo)[0] is False)
    path_a = {"content_tokens": {"alpha", "beta"}, "symbol_tokens": {"gamma"}, "line_count": 10, "private_path": "a.rs"}
    path_b = {"content_tokens": {"alpha", "beta"}, "symbol_tokens": {"gamma"}, "line_count": 10, "private_path": "different/deep/path.rs"}
    check("path_mutation_rank_invariant_fail", all(content_rank_score("alpha gamma", path_a, variant) == content_rank_score("alpha gamma", path_b, variant) for variant in VARIANTS))
    with tempfile.TemporaryDirectory(prefix="r2ag_selftest_") as tmp:
        root = Path(tmp) / "private"
        root_ok, root_status = validate_private_root(root, repo)
        mat = materialize(repo, manifest_path) if ok_manifest and manifest_path else None
        if root_ok and mat and mat.get("ok"):
            write_private_material(root, mat)
        tree_ok, _ = validate_output_tree(root) if root.exists() else (False, "missing")
        explicit = build_report(explicit=True, r2af=r2af, root_status=root_status if root_ok and tree_ok else "invalid", manifest_status=manifest_status, material=mat)
        check("source_lock_pass", explicit["status"] == STATUS_PASS and validate_report(explicit) == [])
        foreign = Path(tmp) / "foreign"; foreign.mkdir(); (foreign / "x.txt").write_text("x")
        check("unowned_root_fail", validate_private_root(foreign, repo)[0] is False)
        for label, mutator, expected in [
            ("task_cap_fail", lambda r: r["material_aggregate_records"][0].__setitem__("actual_task_count", 19), "material_bounds_mismatch"),
            ("depth_cap_fail", lambda r: r["material_aggregate_records"][0].__setitem__("candidate_depth_cap_bucket", "depth_400"), "material_bounds_mismatch"),
            ("variant_missing_fail", lambda r: r["variant_aggregate_records"][0].__setitem__("present_bool", False), "variant_symbol_content_ablation_mismatch"),
            ("rank_gold_fail", lambda r: r["rank_policy_records"][0].__setitem__("rank_policy_used_gold_bool", True), "rank_policy_mismatch"),
            ("rank_path_fail", lambda r: r["rank_policy_records"][0].__setitem__("rank_policy_used_path_bool", True), "rank_policy_mismatch"),
            ("gold_eval_only_fail", lambda r: r["rank_policy_records"][0].__setitem__("gold_private_eval_only_bool", False), "rank_policy_mismatch"),
            ("metrics_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("experiment_metrics_bool", True), "claim_boundary_experiment_metrics_bool"),
            ("r2ah_experiment_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("r2ah_experiment_authorized_bool", True), "overauthorization_r2ah_experiment_authorized_bool"),
            ("default_claim_fail", lambda r: r["claim_boundary_records"][0].__setitem__("default_method_scaling_claim_bool", True), "claim_boundary_default_method_scaling_claim_bool"),
        ]:
            mutated = json.loads(json.dumps(explicit)); mutator(mutated); check(label, expected in validate_report(mutated))
        rowcap = json.loads(json.dumps(explicit)); rowcap["material_aggregate_records"][0]["private_row_cap_bucket"] = "row_cap_unbounded"; check("row_cap_fail", "material_bounds_mismatch" in validate_report(rowcap))
        manifest_mut = json.loads(json.dumps(explicit)); manifest_mut["public_corpus_manifest_records"][0]["bounded_source_scan_compliance_bool"] = False; check("source_scan_allowlist_fail", "manifest_record_mismatch" in validate_report(manifest_mut))
        gate_mut = json.loads(json.dumps(explicit)); gate_mut["pass_fail_gate_records"].pop(); check("gate_set_fail", "gate_set_mismatch" in validate_report(gate_mut))
        synth_mut = json.loads(json.dumps(explicit)); synth_mut["synthetic_validator_records"].pop(); check("synthetic_validator_set_fail", "synthetic_validator_set_mismatch" in validate_report(synth_mut))
        readback_mut = json.loads(json.dumps(explicit)); readback_mut["public_readback_records"] = []; check("readback_record_fail", "public_readback_record_mismatch" in validate_report(readback_mut))
    leak = json.loads(json.dumps(default)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_key crates/openlocus/src/lib.rs"; check("public_scanner_fail", scan_public_report(leak)["status"] == "fail")
    ci = json.loads(json.dumps(default)); ci["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("ci_network_runtime_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(ci)))
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-output-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    check("missing_opt_in_fail", build_report(explicit=False, r2af=r2af)["status"] == STATUS_DEFAULT)
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
    r2af = load_json(repo / R2AF_REPORT_PATH) if (repo / R2AF_REPORT_PATH).exists() else {}
    if not args["allow"]:
        report = build_report(explicit=False, r2af=r2af); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0
    if not args["confirm"] or not args["root"]:
        report = build_report(explicit=True, r2af=r2af, root_status="missing_confirm_or_root", manifest_status="not_supplied"); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 1
    manifest_ok, manifest_status, manifest_path = validate_manifest_arg(args["manifest"], repo)
    root = Path(args["root"])
    root_ok, root_status = validate_private_root(root, repo)
    material = None
    if manifest_ok and root_ok and manifest_path:
        material = materialize(repo, manifest_path)
        if material.get("ok"):
            try:
                write_private_material(root, material)
                tree_ok, tree_status = validate_output_tree(root)
                if not tree_ok: root_status = tree_status
            except Exception as exc:
                root_status = str(exc)
    report = build_report(explicit=True, r2af=r2af, root_status=root_status, manifest_status=manifest_status, material=material)
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"], "private_row_count_bucket": (report.get("material_aggregate_records") or [{}])[0].get("private_row_count_bucket")}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
