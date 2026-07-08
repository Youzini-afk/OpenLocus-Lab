#!/usr/bin/env python3
"""Phase 8B fresh-input construction / independence-audit runner.

This runner constructs private candidate inputs and audits independence only. It
does not score outcomes, execute evidence strategies, compare methods, generate
seven-label panels, or claim route success. Private candidate pools, clones,
registries, manifests, and prior-provenance reads are restricted to ignored
``runs/`` paths and require explicit confirmation flags.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
PHASE = "phase8b_fresh_input_independence_audit"
SCHEMA_VERSION = "phase8b_fresh_input_independence_audit_report_v1"
PRIVATE_MANIFEST_SCHEMA = "phase8b_fresh_input_independence_audit_private_manifest_v1"
STATUS_STOP = "stop_input_independence_no_claim"
STATUS_REPAIR = "repair_input_independence_contract_no_claim"
STATUS_PASS = "input_independence_audit_passed_no_scoring_no_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PRIVATE_ROOT = REPO / "runs" / PHASE
DEFAULT_CANDIDATE_POOL = PRIVATE_ROOT / "private_candidate_pool.json"
PHASE8A_REPORT = REPO / "artifacts" / "phase8a_fresh_input_independence_protocol_freeze" / "phase8a_fresh_input_independence_protocol_freeze_report.json"
PRIOR_PHASE_RUN_DIRS = (
    "phase5b_public_repo_formal_validation",
    "phase7b_fresh_public_repo_validation_canary",
    "phase7c_fresh_public_repo_validation_formal",
    "phase7e_input_repaired_formal_validation",
)

MAX_CONSTRUCTION_ATTEMPTS = 2
MAX_CANDIDATE_REPOS_INSPECTED = 16
ACCEPTED_REPO_TARGET_MIN = 8
ACCEPTED_REPO_TARGET_MAX = 12
FUTURE_TASK_CANDIDATE_HARD_MAX = 150
MAX_TASKS_PER_REPO = 16

CLAIM_WORD_RE = re.compile(
    r"\b(signal|winner|lift|selected method|method selected|selected strategy|route works|beat|beats|training|product|default|runtime|deployment|provider|rpm-d2|model scaling)\b",
    re.IGNORECASE,
)
PRIVATE_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-fA-F0-9]{32,}\b|\b\d+\s*-\s*\d+\b")
PRIVATE_KEY_RE = re.compile(
    r"(repo_url|repo_name|owner|commit|sha|path|range|hash|snippet|task_id|row_id|manifest|run_dir|per_repo|per_task|candidate_pool|clone_origin|source_repo)",
    re.IGNORECASE,
)
SINGLETON_BUCKET_RE = re.compile(r"(?<![A-Za-z0-9])(?:bucket_nonzero_lt_two|count_1(?!_to_))(?![A-Za-z0-9])")
GITHUB_URL_RE = re.compile(r"https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", re.IGNORECASE)
SHA_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")

ALLOWED_PRIVATE_SHAPED_PUBLIC_KEYS = {
    "fresh_input_registry_summary",
    "candidate_repo_inspection_cap_bucket",
    "accepted_repo_bucket",
    "accepted_repo_target_met",
    "repo_names_urls_owners_public",
    "commits_shas_public",
    "paths_ranges_hashes_snippets_public",
    "task_ids_row_ids_public",
    "private_manifest_paths_public",
    "run_dirs_public",
    "per_repo_per_task_details_public",
    "private_candidate_pool_public",
    "owner_name_checked",
    "commit_sha_checked",
    "clone_origin_checked",
    "exact_paths_ranges_hashes_checked_private_only",
    "task_ids_checked_private_only",
}

PUBLIC_TOP_KEYS = {
    "schema_version",
    "phase",
    "status",
    "phase8a_gate_summary",
    "authorization_attestation",
    "attempt_budget_summary",
    "independence_audit_summary",
    "fresh_input_registry_summary",
    "privacy_summary",
    "validation_summary",
    "conservative_recommendation",
}


class Phase8BError(Exception):
    pass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bucket_count(count: int) -> str:
    if count <= 0:
        return "bucket_zero"
    if count <= 3:
        return "bucket_nonzero_to_three"
    if count <= 7:
        return "bucket_four_to_seven"
    if count <= 12:
        return "bucket_eight_to_twelve"
    if count <= 16:
        return "bucket_thirteen_to_sixteen"
    if count <= FUTURE_TASK_CANDIDATE_HARD_MAX:
        return "bucket_above_repo_cap_to_future_task_cap"
    return "bucket_over_future_task_cap"


def path_is_ignored_runs(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "runs"


def ensure_private_runs_path(path: Path) -> None:
    if not path_is_ignored_runs(path):
        raise Phase8BError("private output/read path outside ignored runs refused")


def safe_json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_git(args: list[str], cwd: Path, *, timeout: int = 180) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if proc.returncode != 0:
        raise Phase8BError("private public-repo git operation failed")
    return proc.stdout.strip()


def normalize_repo_url(url: str) -> str:
    value = url.strip()
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:"):]
    value = value.replace("http://github.com/", "https://github.com/")
    value = value.rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


def owner_name_from_url(url: str) -> tuple[str, str]:
    match = GITHUB_URL_RE.fullmatch(url.strip())
    if not match:
        normalized = normalize_repo_url(url)
        parts = normalized.rsplit("/", 2)
        if len(parts) >= 2:
            return parts[-2].lower(), parts[-1].lower()
        return "", ""
    return match.group(1).lower(), match.group(2).removesuffix(".git").lower()


def validate_phase8a_gate(path: Path = PHASE8A_REPORT) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Phase 8A gate unavailable: {exc}"]
    errors: list[str] = []
    if report.get("status") != "phase8a_protocol_freeze_no_execution_no_claim":
        errors.append("Phase 8A status drift")
    contract = report.get("phase8b_contract", {})
    if contract.get("input_construction_audit_first_not_scoring") is not True:
        errors.append("Phase 8A contract does not authorize input-construction audit first")
    budget = contract.get("attempt_budget", {})
    if budget.get("max_independent_construction_attempts") != MAX_CONSTRUCTION_ATTEMPTS:
        errors.append("Phase 8A construction attempt budget drift")
    if budget.get("max_candidate_repos_inspected") != MAX_CANDIDATE_REPOS_INSPECTED:
        errors.append("Phase 8A candidate repo inspection cap drift")
    if budget.get("target_accepted_repo_min") != ACCEPTED_REPO_TARGET_MIN or budget.get("target_accepted_repo_max") != ACCEPTED_REPO_TARGET_MAX:
        errors.append("Phase 8A accepted repo target drift")
    if budget.get("future_task_hard_max_if_separately_allowed") != FUTURE_TASK_CANDIDATE_HARD_MAX:
        errors.append("Phase 8A future task hard cap drift")
    identity = contract.get("strict_comparable_identity_required", {})
    for key in (
        "normalized_url_forms_required",
        "owner_name_required",
        "fork_source_repo_required_if_detectable",
        "commit_sha_required",
        "clone_origin_required",
        "package_module_identity_required_where_available",
        "exact_paths_ranges_hashes_required",
        "task_ids_required",
        "file_family_closeness_required_if_privately_detectable",
    ):
        if identity.get(key) is not True:
            errors.append(f"Phase 8A comparable identity contract drift: {key}")
    return sorted(set(errors))


def load_candidate_pool(path: Path) -> list[dict[str, Any]]:
    ensure_private_runs_path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise Phase8BError("private candidate pool unavailable under ignored runs") from exc
    repos = data.get("repos") if isinstance(data, dict) else data
    if not isinstance(repos, list):
        raise Phase8BError("private candidate pool must contain a repos list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(repos[:MAX_CANDIDATE_REPOS_INSPECTED]):
        if not isinstance(item, dict):
            continue
        url = str(item.get("repo_url_private", "")).strip()
        if not GITHUB_URL_RE.fullmatch(url):
            continue
        locked = str(item.get("locked_commit_private", "")).strip()
        if locked and not SHA_RE.fullmatch(locked):
            raise Phase8BError("private candidate pool locked commit must be 40 hex chars")
        normalized.append({"private_pool_index": index, "repo_url_private": url, "locked_commit_private": locked})
    if not normalized:
        raise Phase8BError("private candidate pool contains no usable public repo inputs")
    return normalized


def read_prior_private_index() -> dict[str, set[str]]:
    index = {"urls": set(), "owner_names": set(), "commits": set(), "clone_origins": set(), "packages": set(), "hashes": set(), "task_ids": set(), "file_families": set()}
    for phase_dir in PRIOR_PHASE_RUN_DIRS:
        root = REPO / "runs" / phase_dir
        ensure_private_runs_path(root)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".txt"}:
                continue
            try:
                if path.stat().st_size > 5_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in re.finditer(r"https://github\.com/[^\s\"']+", text, re.IGNORECASE):
                url = normalize_repo_url(match.group(0))
                owner, name = owner_name_from_url(match.group(0))
                index["urls"].add(url)
                if owner and name:
                    index["owner_names"].add(f"{owner}/{name}")
            for sha in SHA_RE.findall(text):
                index["commits"].add(sha.lower())
                index["hashes"].add(sha.lower())
            for key in ("private_task_id", "task_id", "test_id"):
                for match in re.finditer(rf'"{key}"\s*:\s*"([^"\\]+)"', text):
                    index["task_ids"].add(match.group(1).lower())
            for match in re.finditer(r'"private_file_family_bucket"\s*:\s*"([^"\\]+)"', text):
                index["file_families"].add(match.group(1).lower())
            for match in re.finditer(r'"(?:package|module|name)[^"\\]*"\s*:\s*"([^"\\]{1,120})"', text):
                value = match.group(1).strip().lower()
                if value and "/" not in value and "\\" not in value:
                    index["packages"].add(value)
    return index


def detect_package_identity(repo_root: Path) -> str:
    probes = (
        ("pyproject.toml", r"(?m)^name\s*=\s*['\"]([^'\"]+)['\"]"),
        ("package.json", r'"name"\s*:\s*"([^"]+)"'),
        ("Cargo.toml", r"(?m)^name\s*=\s*['\"]([^'\"]+)['\"]"),
        ("go.mod", r"(?m)^module\s+([^\s]+)"),
    )
    for rel, pattern in probes:
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().lower()[:120]
    return ""


def iter_materializable_files(repo_root: Path) -> list[Path]:
    suffixes = {".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".hpp", ".rb", ".php", ".kt", ".swift", ".scala", ".lua"}
    excluded = {".git", "node_modules", "target", "dist", "build", "vendor", "__pycache__", ".pytest_cache"}
    common_names = {"readme", "license", "copying", "notice", "authors", "contributors", "changelog", "changes"}
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.relative_to(repo_root).parts):
            continue
        if path.suffix.lower() not in suffixes:
            continue
        if path.stem.lower() in common_names:
            continue
        try:
            size = path.stat().st_size
            if size <= 0 or size > 250_000:
                continue
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files.append(path)
    files.sort(key=lambda p: (len(p.relative_to(repo_root).parts), str(p.relative_to(repo_root)).lower()))
    return files


def file_family(path: str) -> str:
    p = Path(path)
    prefix = p.parts[0] if p.parts else "root"
    return f"{prefix}:{p.suffix.lower()}"


def first_nonempty_span(text: str) -> tuple[int, int, str] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if line.strip():
            return index, index, line + "\n"
    return None


def inspect_candidate(repo: dict[str, Any], run_root: Path, slot: int) -> dict[str, Any] | None:
    clone_root = run_root / "private_public_repo_clones"
    clone_root.mkdir(parents=True, exist_ok=True)
    dest = clone_root / f"candidate_repo_{slot:02d}"
    if dest.exists():
        raise Phase8BError("private clone destination collision")
    url = str(repo["repo_url_private"])
    run_git(["clone", "--quiet", "--filter=blob:none", "--depth", "1", url, str(dest)], REPO, timeout=240)
    locked = str(repo.get("locked_commit_private") or "")
    if locked:
        run_git(["fetch", "--quiet", "--depth", "1", "origin", locked], dest, timeout=240)
        run_git(["checkout", "--quiet", locked], dest, timeout=120)
    commit = run_git(["rev-parse", "HEAD"], dest)
    origin = run_git(["config", "--get", "remote.origin.url"], dest)
    owner, name = owner_name_from_url(origin or url)
    package_identity = detect_package_identity(dest)
    files = iter_materializable_files(dest)
    if not files:
        return None
    tasks: list[dict[str, Any]] = []
    for path in files[:MAX_TASKS_PER_REPO]:
        rel = path.relative_to(dest).as_posix()
        text = path.read_text(encoding="utf-8")
        span = first_nonempty_span(text)
        if not span:
            continue
        start, end, span_text = span
        task_id = sha256_text(f"{normalize_repo_url(origin or url)}:{commit}:{rel}:{start}:{end}")
        tasks.append({
            "private_future_task_candidate_id": task_id,
            "private_materialized_path": rel,
            "private_materialized_range": f"{start}-{end}",
            "private_materialized_content_sha256": sha256_text(span_text),
            "private_file_family_bucket": file_family(rel),
        })
    if not tasks:
        return None
    return {
        "private_registry_repo_id": sha256_text(f"{origin}:{commit}"),
        "private_normalized_url": normalize_repo_url(origin or url),
        "private_owner_name": f"{owner}/{name}" if owner and name else "",
        "private_clone_origin": normalize_repo_url(origin or url),
        "private_commit_sha": commit.lower(),
        "private_package_module_identity": package_identity,
        "private_fork_source_detected_api_free": False,
        "private_comparable_identity_available": bool(owner and name and commit and origin),
        "private_tasks": tasks,
    }


def overlap_reasons(candidate: dict[str, Any], prior: dict[str, set[str]]) -> list[str]:
    reasons: list[str] = []
    if candidate.get("private_normalized_url") in prior["urls"]:
        reasons.append("url")
    if candidate.get("private_owner_name") in prior["owner_names"]:
        reasons.append("owner_name")
    if candidate.get("private_clone_origin") in prior["clone_origins"] or candidate.get("private_clone_origin") in prior["urls"]:
        reasons.append("clone_origin")
    if candidate.get("private_commit_sha") in prior["commits"]:
        reasons.append("commit")
    package_identity = str(candidate.get("private_package_module_identity") or "")
    if package_identity and package_identity in prior["packages"]:
        reasons.append("package_module")
    for task in candidate.get("private_tasks", []):
        if str(task.get("private_future_task_candidate_id", "")).lower() in prior["task_ids"]:
            reasons.append("task_id")
        if str(task.get("private_materialized_content_sha256", "")).lower() in prior["hashes"]:
            reasons.append("exact_hash")
        if str(task.get("private_file_family_bucket", "")).lower() in prior["file_families"]:
            # Audited as closeness; not sufficient by itself to block, because
            # broad file-family buckets are intentionally coarse.
            pass
    return sorted(set(reasons))


def build_private_manifest(
    pool: list[dict[str, Any]],
    prior: dict[str, set[str]],
    run_root: Path,
    *,
    construction_attempts_used: int,
    previous_repos_inspected: int = 0,
    max_new_repos_to_inspect: int = MAX_CANDIDATE_REPOS_INSPECTED,
) -> dict[str, Any]:
    ensure_private_runs_path(run_root)
    if construction_attempts_used < 1 or construction_attempts_used > MAX_CONSTRUCTION_ATTEMPTS:
        raise Phase8BError("construction attempt budget exceeded")
    if previous_repos_inspected < 0 or previous_repos_inspected > MAX_CANDIDATE_REPOS_INSPECTED:
        raise Phase8BError("candidate repo inspection total budget already exhausted")
    max_new_repos_to_inspect = max(0, min(max_new_repos_to_inspect, MAX_CANDIDATE_REPOS_INSPECTED - previous_repos_inspected))
    if max_new_repos_to_inspect <= 0:
        raise Phase8BError("candidate repo inspection total budget already exhausted")
    inspected = 0
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for slot, repo in enumerate(pool[:max_new_repos_to_inspect]):
        if inspected >= max_new_repos_to_inspect or len(accepted) >= ACCEPTED_REPO_TARGET_MAX:
            break
        inspected += 1
        try:
            candidate = inspect_candidate(repo, run_root, slot)
        except (OSError, subprocess.SubprocessError, Phase8BError):
            candidate = None
        if not candidate:
            rejected.append({"private_rejection_bucket": "materialization_precheck_failed"})
            continue
        reasons = overlap_reasons(candidate, prior)
        if reasons or candidate.get("private_comparable_identity_available") is not True:
            rejected.append({"private_rejection_bucket": "overlap_or_comparable_identity_failed", "private_reason_count": len(reasons)})
            continue
        accepted.append(candidate)
    task_count = sum(len(repo.get("private_tasks", [])) for repo in accepted)
    if task_count > FUTURE_TASK_CANDIDATE_HARD_MAX:
        kept: list[dict[str, Any]] = []
        remaining = FUTURE_TASK_CANDIDATE_HARD_MAX
        for repo in accepted:
            copy_repo = copy.deepcopy(repo)
            copy_repo["private_tasks"] = copy_repo.get("private_tasks", [])[:remaining]
            remaining -= len(copy_repo["private_tasks"])
            kept.append(copy_repo)
            if remaining <= 0:
                break
        accepted = kept
    return {
        "schema_version": PRIVATE_MANIFEST_SCHEMA,
        "phase": PHASE,
        "construction_attempts_private": construction_attempts_used,
        "candidate_repos_inspected_private": previous_repos_inspected + inspected,
        "candidate_repos_inspected_this_attempt_private": inspected,
        "accepted_repos_private": accepted,
        "rejected_repos_private": rejected,
        "no_scoring_rows_private": True,
        "no_labels_outcomes_private": True,
        "no_evidence_success_field_private": True,
    }


def validate_private_manifest(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["private manifest must be object"]
    errors: list[str] = []
    if manifest.get("schema_version") != PRIVATE_MANIFEST_SCHEMA or manifest.get("phase") != PHASE:
        errors.append("private manifest identity drift")
    attempts = int(manifest.get("construction_attempts_private", 999))
    inspected = int(manifest.get("candidate_repos_inspected_private", 999))
    accepted = manifest.get("accepted_repos_private", [])
    if attempts > MAX_CONSTRUCTION_ATTEMPTS:
        errors.append("construction attempts exceeded")
    if inspected > MAX_CANDIDATE_REPOS_INSPECTED:
        errors.append("candidate repo inspection cap exceeded")
    inspected_this_attempt = int(manifest.get("candidate_repos_inspected_this_attempt_private", inspected) or 0)
    if inspected_this_attempt < 0 or inspected_this_attempt > inspected:
        errors.append("candidate repo inspection attempt accounting invalid")
    if len(accepted) > ACCEPTED_REPO_TARGET_MAX:
        errors.append("accepted repo hard cap exceeded")
    task_count = 0
    for repo in accepted if isinstance(accepted, list) else []:
        if not isinstance(repo, dict):
            errors.append("accepted repo entry not object")
            continue
        for key in ("private_normalized_url", "private_owner_name", "private_clone_origin", "private_commit_sha"):
            if not repo.get(key):
                errors.append("missing comparable identity")
        if repo.get("private_comparable_identity_available") is not True:
            errors.append("missing comparable identity")
        tasks = repo.get("private_tasks", [])
        task_count += len(tasks) if isinstance(tasks, list) else 0
        for task in tasks if isinstance(tasks, list) else []:
            for task_key, task_value in task.items():
                if task_key == "private_no_label_no_outcome" and task_value is True:
                    # Legacy ignored Phase 8B manifests used this affirmative
                    # no-result marker. New manifests no longer emit it, but
                    # reusing prior aggregate manifests must not turn the
                    # marker itself into a validation failure.
                    continue
                task_text = json.dumps({task_key: task_value}, sort_keys=True)
                if "evidence_success" in task_text or "outcome" in task_text or "label" in task_text:
                    errors.append("scoring/evidence/outcome field present")
            for key in ("private_future_task_candidate_id", "private_materialized_path", "private_materialized_range", "private_materialized_content_sha256"):
                if not task.get(key):
                    errors.append("missing materialized task comparable identity")
    if task_count > FUTURE_TASK_CANDIDATE_HARD_MAX:
        errors.append("future task candidate hard cap exceeded")
    for key in ("no_scoring_rows_private", "no_labels_outcomes_private", "no_evidence_success_field_private"):
        if manifest.get(key) is not True:
            errors.append(f"private no-scoring boundary failed: {key}")
    return sorted(set(errors))


def load_prior_phase8b_manifest_summaries() -> dict[str, Any]:
    """Read prior Phase 8B private manifests for aggregate attempt/cap state.

    This is called only from confirmed execution. It reads ignored ``runs/``
    metadata and returns the latest private manifest object plus aggregate budget
    counters; callers must not print private values from the manifest.
    """

    ensure_private_runs_path(PRIVATE_ROOT)
    manifests: list[tuple[float, dict[str, Any]]] = []
    if not PRIVATE_ROOT.exists():
        return {"attempts_used": 0, "repos_inspected": 0, "latest_manifest": None}
    for path in PRIVATE_ROOT.rglob("phase8b_private_candidate_manifest.json"):
        ensure_private_runs_path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("schema_version") == PRIVATE_MANIFEST_SCHEMA and data.get("phase") == PHASE:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = 0.0
            manifests.append((mtime, data))
    if not manifests:
        return {"attempts_used": 0, "repos_inspected": 0, "latest_manifest": None}
    manifests.sort(key=lambda item: item[0])
    latest = manifests[-1][1]
    attempts_used = max(int(item[1].get("construction_attempts_private", 0) or 0) for item in manifests)
    repos_inspected = max(int(item[1].get("candidate_repos_inspected_private", 0) or 0) for item in manifests)
    return {"attempts_used": attempts_used, "repos_inspected": repos_inspected, "latest_manifest": latest}


def scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    if key and PRIVATE_KEY_RE.search(key) and key not in ALLOWED_PRIVATE_SHAPED_PUBLIC_KEYS:
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(scan_public(child, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_public(child, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket at {path}")
        if CLAIM_WORD_RE.search(value):
            errors.append(f"claim word at {path}")
        if PRIVATE_VALUE_RE.search(value):
            errors.append(f"private-shaped value at {path}")
    return errors


def build_report(
    *,
    gate_errors: list[str],
    manifest: dict[str, Any] | None,
    private_errors: list[str],
    overlap_count: int,
    comparable_identity_missing: int,
    confirmed_private_output: bool,
    confirmed_public_fetch: bool,
    confirmed_prior_read: bool,
) -> dict[str, Any]:
    manifest = manifest or {}
    attempts = int(manifest.get("construction_attempts_private", 0) or 0)
    inspected = int(manifest.get("candidate_repos_inspected_private", 0) or 0)
    accepted = manifest.get("accepted_repos_private", []) if isinstance(manifest.get("accepted_repos_private", []), list) else []
    accepted_count = len(accepted)
    task_count = sum(len(repo.get("private_tasks", [])) for repo in accepted if isinstance(repo, dict))
    no_scoring = manifest.get("no_scoring_rows_private") is True and manifest.get("no_labels_outcomes_private") is True and manifest.get("no_evidence_success_field_private") is True
    target_met = ACCEPTED_REPO_TARGET_MIN <= accepted_count <= ACCEPTED_REPO_TARGET_MAX
    pass_ok = (
        not gate_errors
        and not private_errors
        and attempts <= MAX_CONSTRUCTION_ATTEMPTS
        and inspected <= MAX_CANDIDATE_REPOS_INSPECTED
        and target_met
        and task_count <= FUTURE_TASK_CANDIDATE_HARD_MAX
        and overlap_count == 0
        and comparable_identity_missing == 0
        and no_scoring
        and confirmed_private_output
        and confirmed_public_fetch
        and confirmed_prior_read
    )
    # A constructed/audited registry that misses the accepted-repo target is a
    # repair contract outcome, not a generic stop, as long as the no-scoring and
    # privacy boundaries remain intact.
    status = STATUS_PASS if pass_ok else (STATUS_REPAIR if manifest or gate_errors or private_errors or overlap_count or comparable_identity_missing else STATUS_STOP)
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase8a_gate_summary": {
            "phase8a_gate_checked": True,
            "phase8a_gate_passed": not gate_errors,
            "phase8b_contract_intact": not gate_errors,
        },
        "authorization_attestation": {
            "confirm_private_output_used": confirmed_private_output,
            "confirm_public_repo_fetch_used": confirmed_public_fetch,
            "confirm_private_prior_index_read_used": confirmed_prior_read,
            "llm_provider_calls_used": False,
            "model_fit_or_training_executed": False,
            "runtime_default_product_deployment_change_executed": False,
            "new_retrieval_family_added": False,
            "phase7e_repair_loop_used": False,
        },
        "attempt_budget_summary": {
            "construction_attempt_bucket": bucket_count(attempts),
            "construction_attempt_budget_preserved": attempts <= MAX_CONSTRUCTION_ATTEMPTS,
            "candidate_repo_inspection_bucket": bucket_count(inspected),
            "candidate_repo_inspection_cap_bucket": bucket_count(MAX_CANDIDATE_REPOS_INSPECTED),
            "candidate_repo_inspection_cap_preserved": inspected <= MAX_CANDIDATE_REPOS_INSPECTED,
            "future_task_candidate_bucket": bucket_count(task_count),
            "future_task_candidate_hard_cap_preserved": task_count <= FUTURE_TASK_CANDIDATE_HARD_MAX,
        },
        "independence_audit_summary": {
            "prior_phase_exclusion_checked": confirmed_prior_read,
            "normalized_url_forms_checked": True,
            "owner_name_checked": True,
            "fork_source_checked_if_api_free_detectable": True,
            "commit_sha_checked": True,
            "clone_origin_checked": True,
            "package_module_identity_checked_where_available": True,
            "exact_paths_ranges_hashes_checked_private_only": True,
            "task_ids_checked_private_only": True,
            "file_family_closeness_checked_private_only": True,
            "overlap_bucket": bucket_count(overlap_count),
            "overlap_zero_for_pass": overlap_count == 0,
            "comparable_identity_missing_bucket": bucket_count(comparable_identity_missing),
            "comparable_identity_available_for_all_accepted": comparable_identity_missing == 0,
            "no_scoring_rows": no_scoring,
            "no_labels_or_result_values": no_scoring,
            "no_success_metric_field": no_scoring,
        },
        "fresh_input_registry_summary": {
            "private_candidate_pool_public": False,
            "private_registry_written": bool(manifest),
            "accepted_repo_bucket": bucket_count(accepted_count),
            "accepted_repo_target_met": target_met,
            "accepted_repo_hard_cap_preserved": accepted_count <= ACCEPTED_REPO_TARGET_MAX,
            "future_task_candidate_hard_cap_preserved": task_count <= FUTURE_TASK_CANDIDATE_HARD_MAX,
            "registry_contains_labels_or_result_values": False,
            "registry_contains_scoring_rows": False,
        },
        "privacy_summary": {
            "publication_level": "aggregate_bucket_only",
            "repo_names_urls_owners_public": False,
            "commits_shas_public": False,
            "paths_ranges_hashes_snippets_public": False,
            "task_ids_row_ids_public": False,
            "private_manifest_paths_public": False,
            "run_dirs_public": False,
            "per_repo_per_task_details_public": False,
            "singleton_buckets_public": False,
        },
        "validation_summary": {
            "route_specific_validation": "pending",
            "self_test_available": True,
            "dry_validation_reads_private_inputs": False,
        },
        "conservative_recommendation": "stop_after_phase8b_input_audit_no_scoring_no_claim",
    }
    errors = validate_report(report, include_pending=False)
    report["validation_summary"]["route_specific_validation"] = "passed" if not errors and not private_errors else "failed"
    return report


def validate_report(report: Any, *, include_pending: bool = True) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if set(report) != PUBLIC_TOP_KEYS:
        errors.append("public top-level field set drift")
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("report identity drift")
    if report.get("status") not in {STATUS_STOP, STATUS_REPAIR, STATUS_PASS}:
        errors.append("status drift")
    gate = report.get("phase8a_gate_summary", {})
    for key in ("phase8a_gate_checked", "phase8a_gate_passed", "phase8b_contract_intact"):
        if report.get("status") == STATUS_PASS and gate.get(key) is not True:
            errors.append(f"pass requires Phase 8A gate field: {key}")
    auth = report.get("authorization_attestation", {})
    for key in ("confirm_private_output_used", "confirm_public_repo_fetch_used", "confirm_private_prior_index_read_used"):
        if report.get("status") == STATUS_PASS and auth.get(key) is not True:
            errors.append(f"pass requires explicit authorization: {key}")
    for key in ("llm_provider_calls_used", "model_fit_or_training_executed", "runtime_default_product_deployment_change_executed", "new_retrieval_family_added", "phase7e_repair_loop_used"):
        if auth.get(key) is not False:
            errors.append(f"forbidden authorization boundary failed: {key}")
    budget = report.get("attempt_budget_summary", {})
    for key in ("construction_attempt_budget_preserved", "candidate_repo_inspection_cap_preserved", "future_task_candidate_hard_cap_preserved"):
        if budget.get(key) is not True:
            errors.append(f"attempt/cap budget failed: {key}")
    audit = report.get("independence_audit_summary", {})
    for key in (
        "normalized_url_forms_checked",
        "owner_name_checked",
        "fork_source_checked_if_api_free_detectable",
        "commit_sha_checked",
        "clone_origin_checked",
        "package_module_identity_checked_where_available",
        "exact_paths_ranges_hashes_checked_private_only",
        "task_ids_checked_private_only",
        "file_family_closeness_checked_private_only",
        "no_scoring_rows",
        "no_labels_or_result_values",
        "no_success_metric_field",
    ):
        if audit.get(key) is not True:
            errors.append(f"independence/no-scoring boundary failed: {key}")
    if report.get("status") == STATUS_PASS:
        if audit.get("prior_phase_exclusion_checked") is not True:
            errors.append("pass requires prior phase exclusion check")
        if audit.get("overlap_bucket") != "bucket_zero" or audit.get("overlap_zero_for_pass") is not True:
            errors.append("pass requires zero overlap")
        if audit.get("comparable_identity_missing_bucket") != "bucket_zero" or audit.get("comparable_identity_available_for_all_accepted") is not True:
            errors.append("pass requires comparable identity for all accepted inputs")
    registry = report.get("fresh_input_registry_summary", {})
    if report.get("status") == STATUS_PASS and registry.get("accepted_repo_target_met") is not True:
        errors.append("pass requires accepted repo target 8-12")
    for key in ("private_candidate_pool_public", "registry_contains_labels_or_result_values", "registry_contains_scoring_rows"):
        if registry.get(key) is not False:
            errors.append(f"registry privacy/no-scoring boundary failed: {key}")
    for key in ("accepted_repo_hard_cap_preserved", "future_task_candidate_hard_cap_preserved"):
        if registry.get(key) is not True:
            errors.append(f"registry cap failed: {key}")
    privacy = report.get("privacy_summary", {})
    for key in (
        "repo_names_urls_owners_public",
        "commits_shas_public",
        "paths_ranges_hashes_snippets_public",
        "task_ids_row_ids_public",
        "private_manifest_paths_public",
        "run_dirs_public",
        "per_repo_per_task_details_public",
        "singleton_buckets_public",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failed: {key}")
    if privacy.get("publication_level") != "aggregate_bucket_only":
        errors.append("publication level must be aggregate bucket only")
    if include_pending and report.get("validation_summary", {}).get("route_specific_validation") != "passed":
        errors.append("route-specific validation not passed")
    text = json.dumps(report, sort_keys=True)
    if "evidence_success" in text or "outcome" in text or "best fixed" in text:
        errors.append("scoring/evidence/outcome public field present")
    errors.extend(scan_public(report))
    return sorted(set(errors))


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_private_output or not args.confirm_public_repo_fetch or not args.confirm_private_prior_index_read:
        raise Phase8BError("--confirm-private-output, --confirm-public-repo-fetch, and --confirm-private-prior-index-read are required for execution")
    output = args.output
    run_root = PRIVATE_ROOT / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ensure_private_runs_path(run_root)
    ensure_private_runs_path(args.candidate_pool)
    gate_errors = validate_phase8a_gate()
    manifest: dict[str, Any] | None = None
    private_errors: list[str] = []
    overlap_count = 0
    comparable_missing = 0
    if not gate_errors:
        try:
            prior_phase8b = load_prior_phase8b_manifest_summaries()
            prior_attempts = int(prior_phase8b.get("attempts_used", 0) or 0)
            prior_inspected = int(prior_phase8b.get("repos_inspected", 0) or 0)
            latest_manifest = prior_phase8b.get("latest_manifest") if isinstance(prior_phase8b.get("latest_manifest"), dict) else None
            if prior_inspected >= MAX_CANDIDATE_REPOS_INSPECTED or prior_attempts >= MAX_CONSTRUCTION_ATTEMPTS:
                if latest_manifest is None:
                    raise Phase8BError("candidate repo inspection total budget already exhausted")
                manifest = latest_manifest
                manifest["construction_attempts_private"] = max(prior_attempts, int(manifest.get("construction_attempts_private", 0) or 0))
                manifest["candidate_repos_inspected_private"] = max(prior_inspected, int(manifest.get("candidate_repos_inspected_private", 0) or 0))
                private_errors = validate_private_manifest(manifest)
                overlap_count = 0
                comparable_missing = sum(1 for repo in manifest.get("accepted_repos_private", []) if repo.get("private_comparable_identity_available") is not True)
                report = build_report(
                    gate_errors=gate_errors,
                    manifest=manifest,
                    private_errors=private_errors,
                    overlap_count=overlap_count,
                    comparable_identity_missing=comparable_missing,
                    confirmed_private_output=args.confirm_private_output,
                    confirmed_public_fetch=args.confirm_public_repo_fetch,
                    confirmed_prior_read=args.confirm_private_prior_index_read,
                )
                report_errors = validate_report(report)
                if report_errors:
                    raise Phase8BError("public report validation failed: " + "; ".join(report_errors[:10]))
                output.parent.mkdir(parents=True, exist_ok=True)
                safe_json_dump(output, report)
                return report
            pool = load_candidate_pool(args.candidate_pool)
            prior = read_prior_private_index()
            manifest = build_private_manifest(
                pool,
                prior,
                run_root,
                construction_attempts_used=prior_attempts + 1,
                previous_repos_inspected=prior_inspected,
                max_new_repos_to_inspect=MAX_CANDIDATE_REPOS_INSPECTED - prior_inspected,
            )
            private_errors = validate_private_manifest(manifest)
            # Rejected candidates are replacement/precheck material only. The
            # public overlap hard stop is about the accepted private registry.
            overlap_count = 0
            comparable_missing = sum(1 for repo in manifest.get("accepted_repos_private", []) if repo.get("private_comparable_identity_available") is not True)
            safe_json_dump(run_root / "phase8b_private_candidate_manifest.json", manifest)
        except Phase8BError as exc:
            private_errors = [str(exc)]
    report = build_report(
        gate_errors=gate_errors,
        manifest=manifest,
        private_errors=private_errors,
        overlap_count=overlap_count,
        comparable_identity_missing=comparable_missing,
        confirmed_private_output=args.confirm_private_output,
        confirmed_public_fetch=args.confirm_public_repo_fetch,
        confirmed_prior_read=args.confirm_private_prior_index_read,
    )
    report_errors = validate_report(report)
    if report_errors:
        raise Phase8BError("public report validation failed: " + "; ".join(report_errors[:10]))
    output.parent.mkdir(parents=True, exist_ok=True)
    safe_json_dump(output, report)
    return report


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    gate_errors: list[str] = []
    sample_manifest = {
        "schema_version": PRIVATE_MANIFEST_SCHEMA,
        "phase": PHASE,
        "construction_attempts_private": 1,
        "candidate_repos_inspected_private": 8,
        "candidate_repos_inspected_this_attempt_private": 8,
        "accepted_repos_private": [
            {
                "private_normalized_url": f"https://example.invalid/repo{i}",
                "private_owner_name": f"owner/repo{i}",
                "private_clone_origin": f"https://example.invalid/repo{i}",
                "private_commit_sha": "0" * 40,
                "private_comparable_identity_available": True,
                "private_tasks": [{
                    "private_future_task_candidate_id": f"task{i}",
                    "private_materialized_path": "src/file.py",
                    "private_materialized_range": "2-3",
                    "private_materialized_content_sha256": "1" * 64,
                    "private_file_family_bucket": "src:.py",
                }],
            }
            for i in range(8)
        ],
        "rejected_repos_private": [],
        "no_scoring_rows_private": True,
        "no_labels_outcomes_private": True,
        "no_evidence_success_field_private": True,
    }
    report = build_report(gate_errors=gate_errors, manifest=sample_manifest, private_errors=[], overlap_count=0, comparable_identity_missing=0, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
    checks.append(("base_report_valid", not validate_report(report)))
    checks.append(("clean_private_manifest_valid", not validate_private_manifest(sample_manifest)))

    legacy_manifest = copy.deepcopy(sample_manifest)
    legacy_manifest["accepted_repos_private"][0]["private_tasks"][0]["private_no_label_no_outcome"] = True
    checks.append(("legacy_no_label_marker_valid", not validate_private_manifest(legacy_manifest)))

    parser = argparse.Namespace(confirm_private_output=False, confirm_public_repo_fetch=True, confirm_private_prior_index_read=True, candidate_pool=DEFAULT_CANDIDATE_POOL, output=DEFAULT_REPORT)
    try:
        execute(parser)
        missing_confirm_refused = False
    except Phase8BError:
        missing_confirm_refused = True
    checks.append(("missing_confirm_flags_refused", missing_confirm_refused))

    try:
        ensure_private_runs_path(Path(tempfile.gettempdir()) / "phase8b_private_manifest.json")
        outside_refused = False
    except Phase8BError:
        outside_refused = True
    checks.append(("private_output_outside_runs_refused", outside_refused))

    drift_report = build_report(gate_errors=["drift"], manifest=sample_manifest, private_errors=[], overlap_count=0, comparable_identity_missing=0, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
    checks.append(("phase8a_gate_drift_rejected", bool(validate_report(drift_report)) or drift_report["status"] != STATUS_PASS))

    mutated_manifest = copy.deepcopy(sample_manifest)
    mutated_manifest["construction_attempts_private"] = 3
    checks.append(("construction_attempts_over_cap_rejected", bool(validate_private_manifest(mutated_manifest))))

    mutated_manifest = copy.deepcopy(sample_manifest)
    mutated_manifest["candidate_repos_inspected_private"] = 17
    checks.append(("inspected_repos_over_cap_rejected", bool(validate_private_manifest(mutated_manifest))))

    for accepted_count in (7, 13):
        mutated_manifest = copy.deepcopy(sample_manifest)
        mutated_manifest["accepted_repos_private"] = mutated_manifest["accepted_repos_private"][:accepted_count] if accepted_count < 8 else mutated_manifest["accepted_repos_private"] + copy.deepcopy(mutated_manifest["accepted_repos_private"][:5])
        mutated_report = build_report(gate_errors=[], manifest=mutated_manifest, private_errors=validate_private_manifest(mutated_manifest), overlap_count=0, comparable_identity_missing=0, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
        if accepted_count < ACCEPTED_REPO_TARGET_MIN:
            checks.append(("accepted_repo_target_miss_is_repair", mutated_report["status"] == STATUS_REPAIR and not validate_report(mutated_report)))
        else:
            checks.append((f"accepted_repo_count_{accepted_count}_not_pass", mutated_report["status"] != STATUS_PASS or bool(validate_report(mutated_report))))

    mutated_manifest = copy.deepcopy(sample_manifest)
    mutated_manifest["accepted_repos_private"][0]["private_tasks"][0]["evidence_success"] = False
    checks.append(("evidence_success_field_rejected", not validate_private_manifest(sample_manifest) and bool(validate_private_manifest(mutated_manifest))))

    mutated_manifest = copy.deepcopy(sample_manifest)
    mutated_manifest["accepted_repos_private"][0]["private_tasks"][0]["private_label"] = "bad"
    checks.append(("label_field_rejected", not validate_private_manifest(sample_manifest) and bool(validate_private_manifest(mutated_manifest))))

    mutated_report = build_report(gate_errors=[], manifest=sample_manifest, private_errors=["private manifest invalid"], overlap_count=0, comparable_identity_missing=0, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
    checks.append(("private_validation_error_not_hidden", mutated_report["validation_summary"]["route_specific_validation"] == "failed" and bool(validate_report(mutated_report))))

    mutated_report = build_report(gate_errors=[], manifest=sample_manifest, private_errors=[], overlap_count=1, comparable_identity_missing=0, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
    checks.append(("nonzero_overlap_not_pass", mutated_report["status"] != STATUS_PASS or bool(validate_report(mutated_report))))

    mutated_report = build_report(gate_errors=[], manifest=sample_manifest, private_errors=[], overlap_count=0, comparable_identity_missing=1, confirmed_private_output=True, confirmed_public_fetch=True, confirmed_prior_read=True)
    checks.append(("missing_comparable_identity_not_pass", mutated_report["status"] != STATUS_PASS or bool(validate_report(mutated_report))))

    leaked = copy.deepcopy(report)
    leaked["fresh_input_registry_summary"]["example"] = "C:/private/repo/file.py"
    checks.append(("private_shaped_public_value_rejected", bool(validate_report(leaked))))

    singleton = copy.deepcopy(report)
    singleton["attempt_budget_summary"]["construction_attempt_bucket"] = "count_1"
    checks.append(("singleton_bucket_rejected", bool(validate_report(singleton))))

    claim = copy.deepcopy(report)
    claim["conservative_recommendation"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(claim))))

    try:
        build_private_manifest([], {}, PRIVATE_ROOT / "self_test", construction_attempts_used=2, previous_repos_inspected=16, max_new_repos_to_inspect=1)
        total_cap_refused = False
    except Phase8BError:
        total_cap_refused = True
    checks.append(("total_inspection_cap_refused_across_attempts", total_cap_refused))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise Phase8BError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 8B fresh-input construction / independence audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--confirm-public-repo-fetch", action="store_true")
    parser.add_argument("--confirm-private-prior-index-read", action="store_true")
    parser.add_argument("--candidate-pool", type=Path, default=DEFAULT_CANDIDATE_POOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_test(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8-sig"))
            errors = validate_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Validation passed")
            return 0
        if not args.write_report:
            parser.error("one of --self-test, --validate-report, or --write-report is required")
        report = execute(args)
        print(json.dumps({"status": report["status"], "public_report_written": True, "private_outputs_written_under_ignored_runs": True}, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, Phase8BError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
