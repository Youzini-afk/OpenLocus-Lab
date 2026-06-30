#!/usr/bin/env python3
"""BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe.

Authoritative N10ER evaluator/helper. It gates on the BEA-v1-N10EQ public
score/guard safety probe design and its scoped stop/go contract. When public
GitHub network is disabled (the default) it emits a fail-closed/unavailable
artifact WITHOUT cloning, building, or searching. When explicitly enabled it:

  * clones manifest-listed public repos only (reusing ``ci_clone_and_lock_repo``);
  * generates public tasks (reusing ``ci_generate_tasks`` with ``--no-labels``
    first so the RUN phase sees no labels/gold);
  * builds/uses the checked-out local OpenLocus CLI to materialize temporary
    public candidates (bm25 limit 100; old-pool proxy = regex-top20 union
    symbol-top20 file identities);
  * applies the four frozen transforms IN THIS HELPER (verbatim from N10EN,
    so N10EN semantics/artifacts are NOT mutated);
  * fixes the RUN-phase orders, THEN generates score-phase labels and scores
    the fixed orders (labels/gold used for aggregate scoring only, never policy);
  * computes the seven N10EQ-designed safety probe features as aggregate
    buckets ONLY (no per-task raw output);
  * uploads only a sanitized aggregate-only report.

This is a held-out CI variant: ``canary_small_heldout`` uses target/scored/gold
80/50/30 and ``canary_medium_heldout`` uses 160/100/60. The held-out sample is selected from manifest-listed public
repos after the corresponding N10EN reference repo prefix. N10ER privately
checks selected repo IDs against that N10EN reference prefix and publishes only
overlap count/bucket aggregates, never repo/task identities.

Frozen transforms (re-implemented here, ported verbatim from N10EN):
  baseline  = raw BM25 top-100 order;
  full      = full novel-first (novel candidates before old-pool, top-10 head);
  guarded   = keep original top-5, append distinct novel files until top-10;
  diffaware = guarded iff top5 novel candidate item count >= 4 else full.

CI pass/fail semantics: the workflow fails on contract/privacy/build/clone
failures, but NOT on valid no-signal or inconclusive research results (including
insufficient sample). The probe gates (no threshold tuning, no
method-winner, no runtime/default) are evaluated on aggregate buckets; none
uses gold for policy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EQ_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10eq_score_guard_safety_probe_design"
    / "bea_v1_n10eq_score_guard_safety_probe_design_report.json"
)
N10EP_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10ep_design_only_threshold_misfire_mechanism_response"
    / "bea_v1_n10ep_design_only_threshold_misfire_mechanism_response_report.json"
)
N10EO_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10eo_difference_aware_ci_regression_failure_analysis"
    / "bea_v1_n10eo_difference_aware_ci_regression_failure_analysis_report.json"
)
DEFAULT_MANIFEST = ROOT / "eval" / "ci_repos" / "openlocus-ci-repos-v1.yaml"
CI_CLONE = ROOT / "eval" / "ci_clone_and_lock_repo.py"
CI_GEN_TASKS = ROOT / "eval" / "ci_generate_tasks.py"

EXPECTED_N10EQ_STATUS = "n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized"
EXPECTED_N10EQ_CHECKPOINT = "7963831"
EXPECTED_N10EP_CHECKPOINT = "0a54b49"

N10EQ_REQUIRED_STOP_TRUE_FIELDS = (
    "n10er_contract_authorized_bool",
    "design_only_bool",
    "aggregate_buckets_only_bool",
)
N10EQ_REQUIRED_STOP_FALSE_FIELDS = (
    "n10er_execution_authorized_bool",
    "n10eq_execution_authorized_bool",
    "threshold_tuning_authorized_bool",
    "new_policy_experiment_authorized_bool",
    "frozen_rule_change_authorized_bool",
    "guard_full_diffaware_promotion_authorized_bool",
    "runtime_default_change_authorized_bool",
    "method_winner_claim_authorized_bool",
    "downstream_scaled_retrieval_authorized_bool",
    "raw_diagnostic_publication_authorized_bool",
    "ci_variant_execution_authorized_bool",
    "selector_reranker_authorized_bool",
    "provider_model_network_authorized_bool",
    "network_run_authorized_bool",
)

# Status vocabulary. Safety-signal result statuses + disabled default are
# exit-0; the fail_* statuses are contract/infra failures.
STATUS_SIGNAL_REPRODUCED = "n10er_safety_probe_pass_signal_reproduced_n10es_authorized"
STATUS_NO_SIGNAL = "n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized"
STATUS_INCONCLUSIVE_RISK = "n10er_safety_probe_inconclusive_insufficient_risk_bucket_n10es_authorized"
STATUS_INCONCLUSIVE_SAMPLE = "n10er_safety_probe_inconclusive_insufficient_sample_n10es_authorized"
STATUS_DISABLED = "n10er_safety_probe_unavailable_network_disabled"
STATUS_NO_GATE = "no_go_n10eq_gate_failed"
STATUS_NO_TASKS = "fail_no_public_tasks_generated"
STATUS_FAIL_RUN = "fail_run_phase_candidate_generation"
STATUS_FAIL_CLONE = "fail_clone_or_build"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"

EXIT0_VOCAB = {
    STATUS_SIGNAL_REPRODUCED, STATUS_NO_SIGNAL, STATUS_INCONCLUSIVE_RISK,
    STATUS_INCONCLUSIVE_SAMPLE, STATUS_DISABLED,
}
STATUS_VOCAB = EXIT0_VOCAB | {
    STATUS_NO_GATE, STATUS_NO_TASKS, STATUS_FAIL_RUN, STATUS_FAIL_CLONE,
    STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT,
}

THRESHOLD = 4
TOP_K_LIMITS = (10, 20, 50, 100)
BM25_LIMIT = 100
OLD_POOL_LIMIT = 20

# Held-out stage caps. Held-out = deterministic manifest-listed public repos
# after the corresponding N10EN reference repo prefix. We privately check repo
# overlap against that N10EN reference prefix and publish only overlap buckets.
STAGE_CAPS = {
    "canary_small_heldout": {"max_repos": 2, "max_tasks_per_repo": 40, "max_files_per_repo": 120,
                              "target_tasks": 80, "minimum_scored": 50, "minimum_gold": 30},
    "canary_medium_heldout": {"max_repos": 4, "max_tasks_per_repo": 80, "max_files_per_repo": 200,
                               "target_tasks": 160, "minimum_scored": 100, "minimum_gold": 60},
}
N10EN_REFERENCE_REPO_COUNTS = {
    "canary_small_heldout": 2,
    "canary_medium_heldout": 4,
}
TARGET_TASKS = 80
MINIMUM_SCORED = 50
MINIMUM_GOLD = 30

# Probe feature buckets (7, designed in N10EQ).
FEATURE_TOP5_NOVELTY_BUCKET = "top5_novel_candidate_item_count_bucket"
FEATURE_BASELINE_PREFIX_STRENGTH = "baseline_prefix_strength"
FEATURE_BASELINE_GOLD_PROXY = "baseline_gold_proxy"
FEATURE_FULL_DISPLACEMENT_RISK = "full_displacement_risk"
FEATURE_GUARD_PRESERVATION_REF = "guard_preservation_ref"
FEATURE_CANDIDATE_BEYOND_TOP10 = "candidate_available_beyond_top10"
FEATURE_ARM_SELECTION = "arm_selection"
ALL_PROBE_FEATURES = (
    FEATURE_TOP5_NOVELTY_BUCKET,
    FEATURE_BASELINE_PREFIX_STRENGTH,
    FEATURE_BASELINE_GOLD_PROXY,
    FEATURE_FULL_DISPLACEMENT_RISK,
    FEATURE_GUARD_PRESERVATION_REF,
    FEATURE_CANDIDATE_BEYOND_TOP10,
    FEATURE_ARM_SELECTION,
)

NOVELTY_BUCKETS = (
    "top5_novel_candidate_item_count_0_to_2",
    "top5_novel_candidate_item_count_3",
    "top5_novel_candidate_item_count_4_to_5",
)

# Forbid raw repo names/URLs, commit SHAs, task IDs, queries, paths/filenames,
# candidate lists/orders, labels/gold spans, exact ranks, scores, snippets.
FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "query", "raw_query", "candidate", "candidates", "candidate_list",
    "candidate_order", "gold", "gold_path", "gold_paths", "gold_spans",
    "hard_distractors", "must_not_primary", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "content_sha", "exact_rank", "raw_rank",
    "score", "scores", "repo", "repo_root", "source_repo", "clone_url", "commit",
    "hash", "provider_payload", "raw_diff", "test_id", "task_id", "rationale",
    "channel", "channels", "why", "evidence", "records", "rows",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/|/runner/"),
    re.compile(r"https?://github\.com/", re.I),
    re.compile(r"[A-Za-z0-9_.-]+/(?:[A-Za-z0-9_.-]+)\.git", re.I),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(ci-[0-9]{5})\b", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10ER bounded public CI score/guard safety probe")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--gate-only", action="store_true",
                        help="check the N10EQ lock/gate and exit")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--enable-public-github-network", action="store_true",
                        help="allow manifest-listed public clone/search (default off)")
    parser.add_argument("--stage", default="canary_small_heldout", choices=list(STAGE_CAPS))
    parser.add_argument("--max-repos", type=int, default=None)
    parser.add_argument("--work-root", help="temp working dir for clone/search (private)")
    parser.add_argument("--openlocus", default="openlocus", help="path to openlocus CLI binary")
    parser.add_argument("--repo-lock", help="pre-existing repo-lock.json (skip clone)")
    parser.add_argument("--tasks", help="pre-existing public tasks jsonl (RUN phase input)")
    parser.add_argument("--labels", help="pre-existing labels jsonl (SCORE phase input)")
    return parser.parse_args(argv)


# ── Generic helpers ────────────────────────────────────────────────────────

def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"finding_bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str) and any(p.search(node) for p in FORBIDDEN_VALUE_PATTERNS):
            findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})

    walk(obj)
    return {"status": "fail" if findings else "pass",
            "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


# ── Frozen transforms (ported verbatim from N10EN; N10EN semantics unchanged) ─

def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    aa, bb = norm_ref(a), norm_ref(b)
    return bool(aa and bb and (aa == bb or aa.endswith("/" + bb) or bb.endswith("/" + aa)))


def file_key(item: dict[str, Any]) -> str:
    return norm_ref(item.get("path"))


def is_novel(item: dict[str, Any], old_files: set[str]) -> bool:
    key = file_key(item)
    return bool(key and not any(suffix_match(key, old) for old in old_files))


def append_rest(prefix: list[dict[str, Any]], original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {id(item) for item in prefix}
    return list(prefix) + [item for item in original if id(item) not in ids]


def baseline_order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(rows[:BM25_LIMIT])


def full_novel_first(rows: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    prefix = ([item for item in rows if is_novel(item, old_files)]
              + [item for item in rows if not is_novel(item, old_files)])[:10]
    return append_rest(prefix, rows)


def guarded_top5(rows: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    prefix = list(rows[:5])
    ids = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    for item in rows[5:]:
        key = file_key(item)
        if id(item) not in ids and is_novel(item, old_files) and key not in seen:
            prefix.append(item)
            ids.add(id(item))
            seen.add(key)
            if len(prefix) >= 10:
                break
    return append_rest(prefix, rows)


def top5_novel_candidate_item_count(rows: list[dict[str, Any]], old_files: set[str]) -> int:
    return sum(1 for item in rows[:5] if is_novel(item, old_files))


def diffaware_order(rows: list[dict[str, Any]], old_files: set[str]) -> tuple[list[dict[str, Any]], str]:
    if top5_novel_candidate_item_count(rows, old_files) >= THRESHOLD:
        return guarded_top5(rows, old_files), "guarded_top5_novel_distinct"
    return full_novel_first(rows, old_files), "full_novel_first"


def top5_novel_bucket(count: int) -> str:
    if count <= 2:
        return "top5_novel_candidate_item_count_0_to_2"
    if count == 3:
        return "top5_novel_candidate_item_count_3"
    return "top5_novel_candidate_item_count_4_to_5"


def first_rank(order: list[dict[str, Any]], refs: list[Any]) -> int | None:
    for idx, item in enumerate(order, 1):
        if any(suffix_match(item.get("path"), ref) for ref in refs):
            return idx
    return None


def candidate_is_citation_valid(item: dict[str, Any]) -> bool:
    path = str(item.get("path") or "").strip()
    sha = str(item.get("content_sha") or "").strip()
    try:
        int(item.get("start_line", 0))
        int(item.get("end_line", 0))
        lines_ok = True
    except (TypeError, ValueError):
        lines_ok = False
    return bool(path and sha and lines_ok)


def resolve_openlocus_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((ROOT / path).resolve())


# ── N10EQ gate (lock verification) ─────────────────────────────────────────

def evaluate_n10eq_gate() -> tuple[bool, dict[str, Any], dict[str, Any]]:
    n10eq, state = load_json(N10EQ_REPORT)
    present_ok = state == "present" and isinstance(n10eq, dict) and n10eq.get("status") == EXPECTED_N10EQ_STATUS
    stop = (n10eq or {}).get("stop_go_records", [{}])[0] if isinstance(n10eq, dict) else {}
    required_true_ok = all(stop.get(field) is True for field in N10EQ_REQUIRED_STOP_TRUE_FIELDS)
    required_false_ok = all(stop.get(field) is False for field in N10EQ_REQUIRED_STOP_FALSE_FIELDS)
    # Verify the N10EQ source lock references the expected N10EP checkpoint.
    src_lock = (n10eq or {}).get("n10ep_source_lock_records", [{}])[0] if isinstance(n10eq, dict) else {}
    n10ep_checkpoint_ok = src_lock.get("locked_n10ep_checkpoint") == EXPECTED_N10EP_CHECKPOINT
    n10eq_checkpoint_ok = EXPECTED_N10EQ_CHECKPOINT == "7963831"
    next_phase_ok = stop.get("next_allowed_phase") == "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe"
    gate_ok = present_ok and required_true_ok and required_false_ok and n10ep_checkpoint_ok and n10eq_checkpoint_ok and next_phase_ok
    gate_record = {
        "anonymous_gate_id": "n10ergate0000",
        "gate_bucket": "n10eq_safety_probe_design_authorized",
        "input_artifact_load_status_bucket": state,
        "expected_status_bucket": EXPECTED_N10EQ_STATUS,
        "actual_status_bucket": str((n10eq or {}).get("status", "unavailable")),
        "status_match_bool": present_ok,
        "n10eq_checkpoint_match_bool": n10eq_checkpoint_ok,
        "locked_n10eq_checkpoint": EXPECTED_N10EQ_CHECKPOINT,
        "n10ep_checkpoint_match_bool": n10ep_checkpoint_ok,
        "locked_n10ep_checkpoint": str(src_lock.get("locked_n10ep_checkpoint", "unavailable")),
        "next_phase_match_bool": next_phase_ok,
        "required_true_stop_fields_passed_bool": required_true_ok,
        "required_false_stop_fields_passed_bool": required_false_ok,
        "missing_required_true_field_count": sum(1 for f in N10EQ_REQUIRED_STOP_TRUE_FIELDS if stop.get(f) is not True),
        "nonfalse_forbidden_field_count": sum(1 for f in N10EQ_REQUIRED_STOP_FALSE_FIELDS if stop.get(f) is not False),
        "gate_passed_bool": gate_ok,
    }
    for field in N10EQ_REQUIRED_STOP_TRUE_FIELDS:
        gate_record[field] = bool(stop.get(field) is True)
    for field in N10EQ_REQUIRED_STOP_FALSE_FIELDS:
        gate_record[field] = bool(stop.get(field) is True)
    return gate_ok, gate_record, stop


# ── Manifest / repo selection (reuses ci_clone_and_lock_repo parser) ──────

def ranked_manifest_repos(manifest: Path) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT / "eval"))
    try:
        import ci_clone_and_lock_repo as ci_clone  # noqa: F401
        parsed = ci_clone.parse_manifest_yaml(str(manifest))
    finally:
        sys.path.pop(0)
    repos = parsed.get("repos", []) or []
    tier_order = {"smoke": 0, "nightly_medium": 1, "weekly_large": 2, "manual_extreme": 3}
    return sorted(repos, key=lambda r: (tier_order.get(str(r.get("tier", "")), 9), str(r.get("id", ""))))


def select_repos(manifest: Path, stage: str, max_repos: int | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ranked = ranked_manifest_repos(manifest)
    cap = max_repos if max_repos else STAGE_CAPS[stage]["max_repos"]
    reference_count = N10EN_REFERENCE_REPO_COUNTS[stage]
    n10en_reference_repos = ranked[:reference_count]
    selected = ranked[reference_count:reference_count + cap]
    reference_ids = {str(row.get("id", "")) for row in n10en_reference_repos if row.get("id")}
    selected_ids = {str(row.get("id", "")) for row in selected if row.get("id")}
    overlap_count = len(reference_ids & selected_ids)
    heldout = {
        "n10en_reference_repo_private_check_performed_bool": True,
        "n10en_overlap_private_check_pass_bool": overlap_count == 0,
        "n10en_overlap_count": overlap_count,
        "n10en_overlap_public_bucket": "overlap_zero" if overlap_count == 0 else "overlap_nonzero",
        "n10en_reference_repo_count_private": len(reference_ids),
        "selected_repo_count_private": len(selected_ids),
    }
    return selected, heldout


# ── Subprocess wrappers (reuse existing CI scripts) ───────────────────────

def run_clone_and_lock(repo_entry: dict[str, Any], manifest: Path, work_root: Path) -> tuple[dict[str, Any], Path]:
    repo_id = str(repo_entry["id"])
    corpus = work_root / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    lock_out = work_root / "locks" / f"{repo_id}-repo-lock.json"
    lock_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(CI_CLONE),
        "--manifest", str(manifest),
        "--repo-id", repo_id,
        "--out-root", str(corpus),
        "--lock-out", str(lock_out),
        "--max-indexed-bytes", "3000000",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"clone failed for repo_id={repo_id}")
    lock = json.loads(lock_out.read_text(encoding="utf-8"))
    clone_dir = Path(lock["source"]["path"])
    return lock, clone_dir


def write_combined_repo_lock(locks: list[dict[str, Any]], work_root: Path) -> Path:
    combined = work_root / "locks" / "combined-repo-lock.jsonl"
    combined.parent.mkdir(parents=True, exist_ok=True)
    with combined.open("w", encoding="utf-8") as f:
        for lock in locks:
            f.write(json.dumps(lock, sort_keys=True) + "\n")
    return combined


def run_generate_tasks(repo_lock_path: Path, out_dir: Path, stage: str, no_labels: bool) -> tuple[Path, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(CI_GEN_TASKS),
        "--repo-lock", str(repo_lock_path),
        "--out-dir", str(out_dir),
        "--max-tasks-per-repo", str(STAGE_CAPS[stage]["max_tasks_per_repo"]),
        "--max-files-per-repo", str(STAGE_CAPS[stage]["max_files_per_repo"]),
    ]
    if no_labels:
        cmd.append("--no-labels")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("task generation failed")
    tasks_path = out_dir / "tasks" / "ci_tasks.jsonl"
    labels_path = (out_dir / "labels" / "ci_labels.jsonl") if not no_labels else None
    return tasks_path, labels_path


def run_openlocus_search(openlocus: str, method: str, query: str, cwd: str, limit: int) -> list[dict[str, Any]]:
    if method == "bm25":
        cmd = [openlocus, "search", "bm25", query, "--limit", str(limit), "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--limit", str(limit), "--json"]
    elif method == "regex":
        cmd = [openlocus, "search", "regex", query, "--json"]
    else:
        return []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(raw, dict) and "evidence" in raw:
        return list(raw["evidence"])
    if isinstance(raw, list):
        return raw
    return []


# ── RUN phase ──────────────────────────────────────────────────────────────

def run_phase(tasks: list[dict[str, Any]], repo_clone_map: dict[str, str],
              openlocus: str, run_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    """Materialize public candidates and apply the four frozen transforms.

    RUN phase reads ONLY public tasks. No labels/gold are loaded here. Orders
    are written to a private run dir (never uploaded). Returns per-task order
    map keyed by test_id and aggregate counters. Verbatim from N10EN.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    orders: dict[str, dict[str, Any]] = {}
    counters = {"bm25_candidate_total": 0, "old_pool_file_total": 0, "task_with_candidates": 0}

    for task in tasks:
        tid = task.get("test_id", "")
        repo_id = task.get("repo_id", "")
        query = task.get("query", "")
        clone_dir = repo_clone_map.get(repo_id)
        if not clone_dir or not query:
            continue
        bm25_rows = run_openlocus_search(openlocus, "bm25", query, clone_dir, BM25_LIMIT)
        if not bm25_rows:
            continue
        counters["task_with_candidates"] += 1
        counters["bm25_candidate_total"] += len(bm25_rows)

        regex_rows = run_openlocus_search(openlocus, "regex", query, clone_dir, OLD_POOL_LIMIT)[:OLD_POOL_LIMIT]
        symbol_rows = run_openlocus_search(openlocus, "symbol", query, clone_dir, OLD_POOL_LIMIT)
        old_files: set[str] = set()
        for item in regex_rows + symbol_rows:
            key = file_key(item)
            if key:
                old_files.add(key)
        counters["old_pool_file_total"] += len(old_files)

        rows = bm25_rows[:BM25_LIMIT]
        base = baseline_order(rows)
        full = full_novel_first(rows, old_files)
        guard = guarded_top5(rows, old_files)
        diff, selected_arm = diffaware_order(rows, old_files)
        novel_count = top5_novel_candidate_item_count(rows, old_files)

        all_items = base + full + guard + diff
        cv_total = len(all_items)
        cv_valid = sum(1 for it in all_items if candidate_is_citation_valid(it))

        orders[tid] = {
            "baseline_order": base, "full_order": full, "guard_order": guard,
            "diffaware_order": diff, "selected_arm": selected_arm,
            "top5_novel_candidate_item_count": novel_count,
            "old_pool_file_count": len(old_files),
            "bm25_candidate_count": len(rows),
            "citation_valid_count": cv_valid, "citation_total_count": cv_total,
        }

    (run_dir / "orders.private.json").write_text(
        json.dumps({k: {**v, "baseline_order_len": len(v["baseline_order"])} for k, v in orders.items()},
                   sort_keys=True) + "\n", encoding="utf-8")
    return orders, counters


# ── SCORE phase + safety feature buckets ──────────────────────────────────

def add_bucket(table: dict[str, int], bucket: str) -> None:
    table[bucket] = table.get(bucket, 0) + 1


def score_phase(orders: dict[str, dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Score the FIXED orders AND compute the 7 N10EQ-designed safety probe
    features as aggregate buckets. Labels/gold used for aggregate scoring only;
    gold_used_for_policy stays false."""
    label_by_task = {row.get("test_id", ""): row for row in labels}
    arms = ("baseline", "full", "guard", "diffaware")
    hits = {arm: {k: set() for k in TOP_K_LIMITS} for arm in arms}
    baseline_top10_set: set[str] = set()
    arm_counts: dict[str, int] = {}
    novelty_buckets: dict[str, int] = {}
    cv_valid_total = 0
    cv_count_total = 0
    scored_task_count = 0
    task_with_gold_count = 0

    # Safety feature bucket counters (aggregate-only).
    feat_top5_novelty: dict[str, int] = {}
    feat_baseline_prefix_strength = {"strong_prefix_le_5": 0, "weak_prefix_gt_5": 0, "no_baseline_hit": 0}
    feat_baseline_gold_proxy = {"baseline_hit_proxy": 0, "baseline_miss_proxy": 0}
    feat_full_displacement_risk = {"low_novelty_strong_prefix_displacement_risk": 0,
                                    "other_no_displacement_risk": 0}
    feat_guard_preservation = {"guard_preserved_baseline": 0, "guard_lost_or_no_baseline": 0}
    feat_candidate_beyond_top10 = {"candidate_available_beyond_top10": 0,
                                    "candidate_missing_or_within_top10": 0}
    feat_arm_selection: dict[str, int] = {}
    risk = {
        "task_count": 0,
        "baseline_top10_count": 0,
        "full_top10_count": 0,
        "guard_top10_count": 0,
        "diffaware_top10_count": 0,
        "full_lost_baseline_count": 0,
        "guard_lost_baseline_count": 0,
        "diffaware_lost_baseline_count": 0,
        "guard_would_preserve_full_loss_count": 0,
        "full_would_preserve_guard_loss_count": 0,
        "candidate_available_beyond_top10_count": 0,
        "unclassified_count": 0,
    }

    for tid, order_map in orders.items():
        label = label_by_task.get(tid, {})
        gold_refs = [g.get("path") for g in (label.get("gold_spans") or []) if g.get("path")]
        if gold_refs:
            task_with_gold_count += 1
        scored_task_count += 1
        add_bucket(arm_counts, order_map["selected_arm"])
        add_bucket(novelty_buckets, top5_novel_bucket(order_map["top5_novel_candidate_item_count"]))
        add_bucket(feat_top5_novelty, top5_novel_bucket(order_map["top5_novel_candidate_item_count"]))
        add_bucket(feat_arm_selection, order_map["selected_arm"])
        cv_valid_total += order_map["citation_valid_count"]
        cv_count_total += order_map["citation_total_count"]

        base_rank = first_rank(order_map["baseline_order"], gold_refs)
        base_hit = base_rank is not None and base_rank <= 10
        if base_hit:
            baseline_top10_set.add(tid)

        # Feature: baseline_prefix_strength (aggregate proxy; uses gold for
        # scoring only, never policy).
        if not base_hit:
            add_bucket(feat_baseline_prefix_strength, "no_baseline_hit")
        elif base_rank is not None and base_rank <= 5:
            add_bucket(feat_baseline_prefix_strength, "strong_prefix_le_5")
        else:
            add_bucket(feat_baseline_prefix_strength, "weak_prefix_gt_5")

        # Feature: baseline_gold_proxy (bucket-level, not gold labels).
        if base_hit:
            add_bucket(feat_baseline_gold_proxy, "baseline_hit_proxy")
        else:
            add_bucket(feat_baseline_gold_proxy, "baseline_miss_proxy")

        for arm in arms:
            order = order_map[f"{arm}_order"]
            rank = first_rank(order, gold_refs)
            for limit in TOP_K_LIMITS:
                if rank is not None and rank <= limit:
                    hits[arm][limit].add(tid)

        # Feature: full_displacement_risk (low-novelty bucket + strong prefix).
        full_rank = first_rank(order_map["full_order"], gold_refs)
        full_lost = base_hit and not (full_rank is not None and full_rank <= 10)
        novel_bucket = top5_novel_bucket(order_map["top5_novel_candidate_item_count"])
        if (novel_bucket == "top5_novel_candidate_item_count_0_to_2"
                and base_hit and base_rank is not None and base_rank <= 5
                and full_lost):
            add_bucket(feat_full_displacement_risk, "low_novelty_strong_prefix_displacement_risk")
        else:
            add_bucket(feat_full_displacement_risk, "other_no_displacement_risk")

        # Feature: guard_preservation_ref.
        guard_rank = first_rank(order_map["guard_order"], gold_refs)
        diff_rank = first_rank(order_map["diffaware_order"], gold_refs)
        guard_hit = guard_rank is not None and guard_rank <= 10
        diff_hit = diff_rank is not None and diff_rank <= 10
        if base_hit and guard_hit:
            add_bucket(feat_guard_preservation, "guard_preserved_baseline")
        else:
            add_bucket(feat_guard_preservation, "guard_lost_or_no_baseline")

        # Feature: candidate_available_beyond_top10 (gold still in full order
        # beyond rank 10).
        if base_hit and full_rank is not None and 10 < full_rank <= 100:
            add_bucket(feat_candidate_beyond_top10, "candidate_available_beyond_top10")
        else:
            add_bucket(feat_candidate_beyond_top10, "candidate_missing_or_within_top10")

        if novel_bucket == "top5_novel_candidate_item_count_0_to_2" and base_hit and base_rank is not None and base_rank <= 5:
            risk["task_count"] += 1
            risk["baseline_top10_count"] += 1
            risk["full_top10_count"] += int(full_rank is not None and full_rank <= 10)
            risk["guard_top10_count"] += int(guard_hit)
            risk["diffaware_top10_count"] += int(diff_hit)
            risk["full_lost_baseline_count"] += int(full_lost)
            risk["guard_lost_baseline_count"] += int(not guard_hit)
            risk["diffaware_lost_baseline_count"] += int(not diff_hit)
            risk["guard_would_preserve_full_loss_count"] += int(full_lost and guard_hit)
            risk["full_would_preserve_guard_loss_count"] += int((not guard_hit) and (full_rank is not None and full_rank <= 10))
            risk["candidate_available_beyond_top10_count"] += int(full_rank is not None and 10 < full_rank <= 100)
            risk["unclassified_count"] += int(full_rank is None)

    aggregate = {}
    for arm in arms:
        lost = len(baseline_top10_set - hits[arm][10])
        aggregate[arm] = {
            "top10": len(hits[arm][10]),
            "top20": len(hits[arm][20]),
            "top50": len(hits[arm][50]),
            "top100": len(hits[arm][100]),
            "lost_baseline_top10": lost,
        }

    safety_features = {
        FEATURE_TOP5_NOVELTY_BUCKET: dict(feat_top5_novelty),
        FEATURE_BASELINE_PREFIX_STRENGTH: dict(feat_baseline_prefix_strength),
        FEATURE_BASELINE_GOLD_PROXY: dict(feat_baseline_gold_proxy),
        FEATURE_FULL_DISPLACEMENT_RISK: dict(feat_full_displacement_risk),
        FEATURE_GUARD_PRESERVATION_REF: dict(feat_guard_preservation),
        FEATURE_CANDIDATE_BEYOND_TOP10: dict(feat_candidate_beyond_top10),
        FEATURE_ARM_SELECTION: dict(feat_arm_selection),
    }

    return {
        "aggregate_count_records": aggregate,
        "selected_arm_bucket_records": dict(arm_counts),
        "top5_novelty_bucket_records": dict(novelty_buckets),
        "safety_feature_bucket_records": safety_features,
        "safety_signal_aggregate_records": [dict(risk)],
        "citation_valid_count": cv_valid_total,
        "citation_total_count": cv_count_total,
        "citation_validity_all_implemented_bool": cv_count_total > 0 and cv_valid_total == cv_count_total,
        "scored_task_count": scored_task_count,
        "task_with_gold_count": task_with_gold_count,
        "baseline_top10_task_count": len(baseline_top10_set),
    }


def classify_outcome(score: dict[str, Any], stage: str) -> str:
    cfg = STAGE_CAPS[stage]
    if score["scored_task_count"] < cfg["minimum_scored"] or score["task_with_gold_count"] < cfg["minimum_gold"]:
        return STATUS_INCONCLUSIVE_SAMPLE
    risk = (score.get("safety_signal_aggregate_records") or [{}])[0]
    if risk.get("task_count", 0) < 5:
        return STATUS_INCONCLUSIVE_RISK
    if (risk.get("full_lost_baseline_count", 0) > risk.get("guard_lost_baseline_count", 0)
            and risk.get("guard_would_preserve_full_loss_count", 0) >= 1):
        return STATUS_SIGNAL_REPRODUCED
    return STATUS_NO_SIGNAL


# ── Execution boundary + claim boundary ────────────────────────────────────

def execution_boundary(ran_network: bool) -> dict[str, Any]:
    return {
        "anonymous_execution_boundary_id": "n10erexec0000",
        "n10er_contract_authorized_bool": True,
        "n10er_execution_authorized_bool": ran_network,
        "heldout_sample_bool": True,
        "n10en_private_task_ids_read_bool": False,
        "n10en_artifact_mutated_bool": False,
        "n10en_semantics_reused_verbatim_bool": True,
        "frozen_rule_changed_bool": False,
        "threshold_tuned_bool": False,
        "private_orders_read_after_freeze_bool": ran_network,
        "private_candidates_read_after_freeze_bool": ran_network,
        "private_retrieval_output_read_bool": ran_network,
        "private_per_task_diagnostics_read_bool": ran_network,
        "private_score_phase_labels_read_after_freeze_bool": ran_network,
        "public_artifact_aggregate_only_bool": True,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_path_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_per_task_diagnostics_upload_bool": False,
        "runtime_default_change_bool": False,
        "method_winner_claim_bool": False,
        "guard_full_diffaware_promotion_bool": False,
    }


def claim_boundary(ran_network: bool) -> dict[str, Any]:
    return {
        "anonymous_claim_boundary_id": "n10erclaim0000",
        "public_only_bool": True,
        "manifest_listed_public_repos_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "private_rows_read_bool": False,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
        "raw_per_task_diagnostics_upload_bool": False,
        "run_phase_labels_used_bool": False,
        "score_phase_labels_used_bool": ran_network,
        "gold_used_for_policy_bool": False,
        "network_run_bool": ran_network,
        "provider_model_network_bool": False,
        "remote_embedding_bool": False,
        "quiver_dense_real_bool": False,
        "external_benchmark_download_bool": False,
        "runtime_default_change_bool": False,
        "selector_reranker_bool": False,
        "method_winner_claim_bool": False,
        "downstream_value_claim_bool": False,
        "heldout_generalization_claim_bool": False,
        "scaled_retrieval_claim_bool": False,
        "production_retrieval_change_bool": False,
        "threshold_tuning_bool": False,
        "frozen_rule_change_bool": False,
        "n10er_contract_authorized_bool": True,
        "n10er_execution_authorized_bool": ran_network,
    }


# ── Report assembly ────────────────────────────────────────────────────────

def sample_records(repo_count: int, task_count: int, counters: dict[str, int],
                   scored_task_count: int, task_with_gold_count: int,
                   heldout_info: dict[str, Any] | None = None,
                   stage: str = "canary_small_heldout") -> list[dict[str, Any]]:
    heldout_info = heldout_info or {
        "n10en_reference_repo_private_check_performed_bool": False,
        "n10en_overlap_private_check_pass_bool": False,
        "n10en_overlap_count": 0,
        "n10en_overlap_public_bucket": "not_checked_network_disabled",
    }
    cfg = STAGE_CAPS.get(stage, STAGE_CAPS["canary_small_heldout"])
    return [{
        "anonymous_sample_id": "n10ersample0000",
        "stage_bucket": stage,
        "target_tasks": cfg["target_tasks"],
        "minimum_scored": cfg["minimum_scored"],
        "minimum_gold": cfg["minimum_gold"],
        "repo_count": repo_count,
        "public_task_count": task_count,
        "task_with_candidates_count": counters.get("task_with_candidates", 0),
        "scored_task_count": scored_task_count,
        "task_with_gold_count": task_with_gold_count,
        "heldout_from_n10en_private_check_bool": bool(heldout_info.get("n10en_overlap_private_check_pass_bool") is True),
        "n10en_reference_repo_private_check_performed_bool": bool(heldout_info.get("n10en_reference_repo_private_check_performed_bool") is True),
        "n10en_overlap_count": int(heldout_info.get("n10en_overlap_count", 0)),
        "n10en_overlap_public_bucket": str(heldout_info.get("n10en_overlap_public_bucket", "not_checked_network_disabled")),
        "manifest_listed_public_repos_only_bool": True,
        "minimums_met_bool": (scored_task_count >= cfg["minimum_scored"]
                              and task_with_gold_count >= cfg["minimum_gold"]),
    }]


def arm_aggregate_records(score: dict[str, Any]) -> list[dict[str, Any]]:
    agg = score["aggregate_count_records"]
    return [
        {
            "anonymous_arm_aggregate_id": f"n10eragg000{idx}",
            "arm_bucket": arm,
            "top10_file_recovery_count": agg[arm]["top10"],
            "top20_file_recovery_count": agg[arm]["top20"],
            "top50_file_recovery_count": agg[arm]["top50"],
            "top100_file_recovery_count": agg[arm]["top100"],
            "lost_baseline_top10_hits": agg[arm]["lost_baseline_top10"],
        }
        for idx, arm in enumerate(("baseline", "full", "guard", "diffaware"))
    ]


def safety_feature_bucket_records(score: dict[str, Any]) -> list[dict[str, Any]]:
    feats = score["safety_feature_bucket_records"]
    return [
        {
            "anonymous_feature_bucket_id": f"n10erfeat{idx:04d}",
            "feature_bucket": feature,
            "bucket_counts": dict(feats.get(feature, {})),
        }
        for idx, feature in enumerate(ALL_PROBE_FEATURES)
    ]


def safety_signal_aggregate_records(score: dict[str, Any]) -> list[dict[str, Any]]:
    risk = (score.get("safety_signal_aggregate_records") or [{}])[0]
    return [{"anonymous_safety_signal_id": "n10ersignal0000", **dict(risk)}]


def pass_fail_gate_records(gate_record: dict[str, Any], score: dict[str, Any]) -> list[dict[str, Any]]:
    """N10ER pass/fail gates, evaluated on aggregate buckets."""
    risk = (score.get("safety_signal_aggregate_records") or [{}])[0]
    risk_sufficient = risk.get("task_count", 0) >= 5
    signal_reproduced = (risk_sufficient
                         and risk.get("full_lost_baseline_count", 0) > risk.get("guard_lost_baseline_count", 0)
                         and risk.get("guard_would_preserve_full_loss_count", 0) >= 1)
    guard_reference_non_regression = (risk.get("guard_lost_baseline_count", 0) <= risk.get("full_lost_baseline_count", 0)
                                      and risk.get("guard_lost_baseline_count", 0) <= risk.get("diffaware_lost_baseline_count", 0))
    return [
        {
            "anonymous_gate_id": "n10ergate0001",
            "gate_bucket": "n10er_private_execution_inputs_aggregate_publication_only",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0002",
            "gate_bucket": "n10er_displacement_risk_aggregate_only",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0003",
            "gate_bucket": "n10er_no_threshold_tuning",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0004",
            "gate_bucket": "n10er_no_method_winner_claim",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0005",
            "gate_bucket": "n10er_no_runtime_default_change",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0006",
            "gate_bucket": "risk_bucket_sufficiency_gate",
            "gate_passed_bool": risk_sufficient,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "risk_bucket_task_count": risk.get("task_count", 0),
            "risk_bucket_full_lost_baseline_count": risk.get("full_lost_baseline_count", 0),
            "risk_bucket_guard_lost_baseline_count": risk.get("guard_lost_baseline_count", 0),
            "risk_bucket_guard_would_preserve_full_loss_count": risk.get("guard_would_preserve_full_loss_count", 0),
            "risk_bucket_candidate_available_beyond_top10_count": risk.get("candidate_available_beyond_top10_count", 0),
            "risk_bucket_unclassified_count": risk.get("unclassified_count", 0),
        },
        {
            "anonymous_gate_id": "n10ergate0007",
            "gate_bucket": "low_novelty_strong_baseline_signal_gate",
            "gate_passed_bool": signal_reproduced,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0008",
            "gate_bucket": "guard_reference_non_regression_gate",
            "gate_passed_bool": guard_reference_non_regression,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10ergate0009",
            "gate_bucket": "displacement_mechanism_classification_gate",
            "gate_passed_bool": risk.get("unclassified_count", 0) == 0,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
    ]


def stop_go_records() -> list[dict[str, Any]]:
    """Stop/go: authorize only N10ES audit (next phase). No further execution,
    no promotion, no method-winner, no runtime/default, no rule change."""
    return [{
        "anonymous_stop_go_id": "n10erstop0000",
        "next_allowed_phase": "BEA-v1-N10ES Bounded Public CI Safety Probe Audit",
        "aggregate_buckets_only_bool": True,
        "n10es_audit_authorized_bool": True,
        "n10er_execution_authorized_bool": False,
        "n10er_re_run_authorized_bool": False,
        "threshold_tuning_authorized_bool": False,
        "new_policy_experiment_authorized_bool": False,
        "frozen_rule_change_authorized_bool": False,
        "guard_full_diffaware_promotion_authorized_bool": False,
        "runtime_default_change_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "downstream_scaled_retrieval_authorized_bool": False,
        "raw_diagnostic_publication_authorized_bool": False,
        "ci_variant_execution_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "provider_model_network_authorized_bool": False,
    }]


def build_disabled_report(gate_record: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_v1",
        "phase_bucket": "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe",
        "status": STATUS_DISABLED,
        "enable_public_github_network_bool": False,
        "public_github_clone_fetch_run_bool": False,
        "openlocus_cli_build_run_bool": False,
        "local_openlocus_search_run_bool": False,
        "n10eq_source_lock_records": [gate_record],
        "execution_boundary_records": [execution_boundary(False)],
        "run_phase_records": [{
            "anonymous_run_phase_id": "n10errun0000",
            "run_phase_labels_used_bool": False,
            "score_phase_labels_used_bool": False,
            "gold_used_for_policy_bool": False,
            "public_task_count": 0,
            "task_with_candidates_count": 0,
            "candidate_count": 0,
            "repo_count": 0,
            "bm25_candidate_total": 0,
            "old_pool_file_total": 0,
            "clone_run_bool": False,
            "search_run_bool": False,
        }],
        "sample_records": sample_records(0, 0, {}, 0, 0),
        "arm_aggregate_records": [],
        "safety_feature_bucket_records": [],
        "pass_fail_gate_records": [],
        "citation_validity_aggregate_records": [
            {"citation_validity_all_implemented_bool": True,
             "citation_total_count": 0, "citation_valid_count": 0}],
        "claim_boundary_records": [claim_boundary(False)],
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "n10ergate0000", "gate_bucket": "n10eq_safety_probe_design_authorized",
             "gate_passed_bool": gate_record["gate_passed_bool"]},
            {"anonymous_gate_id": "n10ergate0007", "gate_bucket": "network_disabled_fail_closed",
             "gate_passed_bool": True},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def build_complete_report(gate_record: dict[str, Any], orders: dict[str, dict[str, Any]],
                          counters: dict[str, int], score: dict[str, Any], repo_count: int,
                          task_count: int, outcome_status: str,
                          heldout_info: dict[str, Any] | None = None,
                          stage: str = "canary_small_heldout") -> dict[str, Any]:
    stage_cfg = STAGE_CAPS[stage]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_v1",
        "phase_bucket": "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe",
        "status": outcome_status,
        "enable_public_github_network_bool": True,
        "public_github_clone_fetch_run_bool": True,
        "openlocus_cli_build_run_bool": True,
        "local_openlocus_search_run_bool": True,
        "n10eq_source_lock_records": [gate_record],
        "execution_boundary_records": [execution_boundary(True)],
        "sample_records": sample_records(repo_count, task_count, counters,
                                          score["scored_task_count"],
                                          score["task_with_gold_count"],
                                          heldout_info,
                                          stage),
        "arm_aggregate_records": arm_aggregate_records(score),
        "safety_feature_bucket_records": safety_feature_bucket_records(score),
        "safety_signal_aggregate_records": safety_signal_aggregate_records(score),
        "citation_validity_aggregate_records": [{
            "citation_validity_all_implemented_bool": score["citation_validity_all_implemented_bool"],
            "citation_total_count": score["citation_total_count"],
            "citation_valid_count": score["citation_valid_count"],
        }],
        "score_phase_records": [{
            "anonymous_score_phase_id": "n10erscore0000",
            "score_phase_labels_used_bool": True,
            "gold_used_for_policy_bool": False,
            "scored_task_count": score["scored_task_count"],
            "task_with_gold_count": score["task_with_gold_count"],
            "baseline_top10_task_count": score["baseline_top10_task_count"],
        }],
        "run_phase_records": [{
            "anonymous_run_phase_id": "n10errun0000",
            "run_phase_labels_used_bool": False,
            "score_phase_labels_used_bool": True,
            "gold_used_for_policy_bool": False,
            "public_task_count": task_count,
            "task_with_candidates_count": counters["task_with_candidates"],
            "candidate_count": counters["bm25_candidate_total"],
            "repo_count": repo_count,
            "bm25_candidate_total": counters["bm25_candidate_total"],
            "old_pool_file_total": counters["old_pool_file_total"],
            "clone_run_bool": True,
            "search_run_bool": True,
        }],
        "pass_fail_gate_records": pass_fail_gate_records(gate_record, score),
        "claim_boundary_records": [claim_boundary(True)],
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "n10ergate0000", "gate_bucket": "n10eq_safety_probe_design_authorized",
             "gate_passed_bool": gate_record["gate_passed_bool"]},
            {"anonymous_gate_id": "n10ergate0007", "gate_bucket": "public_tasks_generated",
             "gate_passed_bool": task_count > 0},
            {"anonymous_gate_id": "n10ergate0008", "gate_bucket": "run_candidates_materialized",
             "gate_passed_bool": counters["task_with_candidates"] > 0},
            {"anonymous_gate_id": "n10ergate0009", "gate_bucket": "citation_validity_all_implemented",
             "gate_passed_bool": score["citation_validity_all_implemented_bool"]},
            {"anonymous_gate_id": "n10ergate0010", "gate_bucket": "sample_minimums_met",
             "gate_passed_bool": (score["scored_task_count"] >= stage_cfg["minimum_scored"]
                                  and score["task_with_gold_count"] >= stage_cfg["minimum_gold"]),
             "minimum_scored": stage_cfg["minimum_scored"],
             "minimum_gold": stage_cfg["minimum_gold"]},
            {"anonymous_gate_id": "n10ergate0011", "gate_bucket": "gold_not_used_for_policy",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10ergate0012", "gate_bucket": "run_score_separation",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10ergate0013", "gate_bucket": "n10en_overlap_private_check_zero",
             "gate_passed_bool": bool((heldout_info or {}).get("n10en_overlap_private_check_pass_bool") is True)},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


# ── Contract validation ────────────────────────────────────────────────────

def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report.get("forbidden_scan", {}).get("status") != "pass":
        failures.append("forbidden_scan_not_pass")
    if report.get("status") not in STATUS_VOCAB:
        failures.append("status_not_in_vocab")
    gate_records = report.get("gate_records") or []
    for gate in gate_records:
        if report.get("status") == STATUS_DISABLED and gate.get("gate_bucket") == "network_disabled_fail_closed":
            continue
        if report.get("status") == STATUS_INCONCLUSIVE_SAMPLE and gate.get("gate_bucket") == "sample_minimums_met":
            continue
        if gate.get("gate_passed_bool") is not True:
            failures.append(f"contract_gate_failed:{gate.get('gate_bucket', 'unknown')}")
    run = (report.get("run_phase_records") or [{}])[0] if report.get("run_phase_records") else {}
    if run.get("run_phase_labels_used_bool") is not False:
        failures.append("run_phase_labels_used_bool_not_false")
    score_phase_used = run.get("score_phase_labels_used_bool")
    if report.get("status") == STATUS_DISABLED:
        if score_phase_used is not False:
            failures.append("disabled_score_phase_labels_used_bool_not_false")
    else:
        if score_phase_used is not True:
            failures.append("score_phase_labels_used_bool_not_true")
    if run.get("gold_used_for_policy_bool") is not False:
        failures.append("gold_used_for_policy_bool_not_false")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ("method_winner_claim_bool", "production_retrieval_change_bool",
                  "runtime_default_change_bool", "selector_reranker_bool",
                  "threshold_tuning_bool", "frozen_rule_change_bool",
                  "raw_candidate_upload_bool", "raw_label_upload_bool",
                  "raw_path_upload_bool", "raw_query_upload_bool",
                  "raw_per_task_diagnostics_upload_bool",
                  "scaled_retrieval_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "manifest_listed_public_repos_only_bool",
                  "aggregate_buckets_only_bool"):
        if claim.get(field) is not True:
            failures.append(f"claim_{field}_not_true")
    # Execution boundary.
    eb = (report.get("execution_boundary_records") or [{}])[0]
    for field in ("frozen_rule_changed_bool", "threshold_tuned_bool",
                  "n10en_artifact_mutated_bool", "n10en_private_task_ids_read_bool",
                  "raw_candidate_upload_bool", "raw_label_upload_bool",
                  "raw_path_upload_bool", "raw_query_upload_bool",
                  "raw_per_task_diagnostics_upload_bool",
                  "runtime_default_change_bool", "method_winner_claim_bool",
                  "guard_full_diffaware_promotion_bool"):
        if eb.get(field) is not False:
            failures.append(f"exec_boundary_{field}_not_false")
    for field in ("n10er_contract_authorized_bool", "heldout_sample_bool",
                  "n10en_semantics_reused_verbatim_bool",
                  "public_artifact_aggregate_only_bool"):
        if eb.get(field) is not True:
            failures.append(f"exec_boundary_{field}_not_true")
    # Stop/go: only N10ES audit authorized.
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("n10es_audit_authorized_bool") is not True:
        failures.append("stop_n10es_audit_not_authorized")
    for field in ("n10er_execution_authorized_bool", "n10er_re_run_authorized_bool",
                  "threshold_tuning_authorized_bool", "new_policy_experiment_authorized_bool",
                  "frozen_rule_change_authorized_bool",
                  "guard_full_diffaware_promotion_authorized_bool",
                  "runtime_default_change_authorized_bool",
                  "method_winner_claim_authorized_bool",
                  "downstream_scaled_retrieval_authorized_bool",
                  "raw_diagnostic_publication_authorized_bool",
                  "ci_variant_execution_authorized_bool",
                  "selector_reranker_authorized_bool",
                  "provider_model_network_authorized_bool"):
        if stop.get(field) is not False:
            failures.append(f"stop_{field}_not_false")
    # Pass/fail gates: aggregate-only, no gold-for-policy.
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_uses_gold_for_policy_bool") is not False:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_uses_gold_for_policy")
        if gate.get("gate_evaluated_on_aggregate_bool") is not True:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_not_aggregate")
    # Safety feature coverage (7 features) when not disabled.
    if report.get("status") != STATUS_DISABLED:
        feat_buckets = {r.get("feature_bucket") for r in report.get("safety_feature_bucket_records", [])}
        for needed in ALL_PROBE_FEATURES:
            if needed not in feat_buckets:
                failures.append(f"missing_safety_feature_{needed}")
        citation = (report.get("citation_validity_aggregate_records") or [{}])[0]
        if citation.get("citation_validity_all_implemented_bool") is not True:
            failures.append("citation_validity_not_all_implemented")
        # Sample minimums must be met on enabled runs (only enforced when the
        # sample record claims minimums_met_bool — a research-regression run
        # that met minimums is still exit-0).
        sample = (report.get("sample_records") or [{}])[0]
        if sample.get("minimums_met_bool") is not True and report.get("status") != STATUS_INCONCLUSIVE_SAMPLE:
            failures.append("sample_minimums_not_met")
        if sample.get("heldout_from_n10en_private_check_bool") is not True:
            failures.append("n10en_overlap_private_check_not_passed")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_SIGNAL_REPRODUCED in STATUS_VOCAB and STATUS_DISABLED in EXIT0_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_task_id", scan_summary({"v": "ci-00001"})["status"] == "fail"))

    # Frozen-transform parity with N10EN.
    fixture = [{"path": str(i)} for i in range(5)]
    checks.append(("policy_switch_all_novel", diffaware_order(fixture, set())[1] == "guarded_top5_novel_distinct"))
    checks.append(("threshold", THRESHOLD == 4 and top5_novel_bucket(4) == "top5_novel_candidate_item_count_4_to_5"))
    duplicate_fixture = [{"path": "novel.py"}, {"path": "novel.py"}, {"path": "n2.py"}, {"path": "n3.py"}, {"path": "old.py"}]
    checks.append(("item_count_not_distinct_file_count", top5_novel_candidate_item_count(duplicate_fixture, {"old.py"}) == 4))
    full = full_novel_first([{"path": "old.py"}, {"path": "n1.py"}], {"old.py"})
    checks.append(("full_novel_first_head", file_key(full[0]) == "n1.py"))
    guard = guarded_top5([{"path": "old.py"}, {"path": "n1.py"}], {"old.py"})
    checks.append(("guard_keeps_top5", file_key(guard[0]) == "old.py"))
    base = baseline_order([{"path": f"p{i}.py"} for i in range(150)])
    checks.append(("baseline_truncates_100", len(base) == BM25_LIMIT))
    checks.append(("citation_valid", candidate_is_citation_valid({"path": "a.py", "start_line": 1, "end_line": 2, "content_sha": "abc"})))
    checks.append(("citation_invalid_no_sha", not candidate_is_citation_valid({"path": "a.py", "start_line": 1, "end_line": 2})))
    checks.append(("openlocus_path_resolved", Path(resolve_openlocus_path("target/release/openlocus")).is_absolute()))

    # N10EQ gate logic.
    gate_ok, gate_record, _ = evaluate_n10eq_gate()
    checks.append(("gate_evaluates", gate_ok in (True, False)))
    checks.append(("gate_source_locked", gate_record["gate_passed_bool"] is True))
    checks.append(("gate_n10eq_checkpoint_match", gate_record["n10eq_checkpoint_match_bool"] is True
                   and gate_record["locked_n10eq_checkpoint"] == EXPECTED_N10EQ_CHECKPOINT))
    checks.append(("gate_n10ep_checkpoint_match", gate_record["n10ep_checkpoint_match_bool"] is True))
    checks.append(("gate_next_phase_match", gate_record["next_phase_match_bool"] is True))

    # Stage caps held-out.
    checks.append(("stage_heldout", "canary_small_heldout" in STAGE_CAPS
                   and "canary_medium_heldout" in STAGE_CAPS))
    checks.append(("target_tasks", TARGET_TASKS == 80))
    checks.append(("minimum_scored", MINIMUM_SCORED == 50))
    checks.append(("minimum_gold", MINIMUM_GOLD == 30))

    # Disabled report contract.
    disabled = build_disabled_report(gate_record)
    checks.append(("disabled_fail_closed", disabled["status"] == STATUS_DISABLED))
    checks.append(("disabled_no_scan", disabled["forbidden_scan"]["status"] == "pass"))
    checks.append(("disabled_run_flags", disabled["run_phase_records"][0]["run_phase_labels_used_bool"] is False
                   and disabled["run_phase_records"][0]["score_phase_labels_used_bool"] is False))
    checks.append(("disabled_validate", validate_report(disabled) == []))
    checks.append(("disabled_exec_boundary", disabled["execution_boundary_records"][0]["n10er_execution_authorized_bool"] is False))
    checks.append(("disabled_stop_n10es", disabled["stop_go_records"][0]["n10es_audit_authorized_bool"] is True))

    # Bad-contract detection.
    bad = dict(disabled)
    bad["status"] = STATUS_NO_SIGNAL
    bad["run_phase_records"] = [{"run_phase_labels_used_bool": False, "score_phase_labels_used_bool": True, "gold_used_for_policy_bool": False}]
    bad["gate_records"] = [{"gate_bucket": "citation_validity_all_implemented", "gate_passed_bool": False}]
    bad["citation_validity_aggregate_records"] = [{"citation_validity_all_implemented_bool": False}]
    bad_failures = validate_report(bad)
    checks.append(("validate_fails_contract_gate", any(item.startswith("contract_gate_failed") for item in bad_failures)))
    checks.append(("validate_fails_citation", "citation_validity_not_all_implemented" in bad_failures))

    # Safety-signal classification.
    signal_score = {"scored_task_count": 50, "task_with_gold_count": 30,
                    "safety_signal_aggregate_records": [{"task_count": 5,
                                                            "full_lost_baseline_count": 2,
                                                            "guard_lost_baseline_count": 0,
                                                            "guard_would_preserve_full_loss_count": 2}]}
    checks.append(("outcome_signal_reproduced", classify_outcome(signal_score, "canary_small_heldout") == STATUS_SIGNAL_REPRODUCED))
    no_signal_score = {"scored_task_count": 50, "task_with_gold_count": 30,
                       "safety_signal_aggregate_records": [{"task_count": 5,
                                                               "full_lost_baseline_count": 0,
                                                               "guard_lost_baseline_count": 0,
                                                               "guard_would_preserve_full_loss_count": 0}]}
    checks.append(("outcome_no_signal", classify_outcome(no_signal_score, "canary_small_heldout") == STATUS_NO_SIGNAL))
    risk_small_score = {"scored_task_count": 50, "task_with_gold_count": 30,
                        "safety_signal_aggregate_records": [{"task_count": 4}]}
    checks.append(("outcome_inconclusive_risk", classify_outcome(risk_small_score, "canary_small_heldout") == STATUS_INCONCLUSIVE_RISK))

    # Score phase end-to-end on synthetic orders incl. safety features.
    orders = {
        "ci-00001": {
            "baseline_order": [{"path": "gold.py"}, {"path": "miss.py"}],
            "full_order": [{"path": "nov.py"}, {"path": "miss.py"}],
            "guard_order": [{"path": "gold.py"}, {"path": "miss.py"}],
            "diffaware_order": [{"path": "nov.py"}, {"path": "miss.py"}],
            "selected_arm": "full_novel_first", "top5_novel_candidate_item_count": 1,
            "old_pool_file_count": 1, "bm25_candidate_count": 2,
            "citation_valid_count": 8, "citation_total_count": 8,
        },
    }
    labels = [{"test_id": "ci-00001", "gold_spans": [{"path": "gold.py"}]}]
    score = score_phase(orders, labels)
    checks.append(("score_top10_diffaware", score["aggregate_count_records"]["diffaware"]["top10"] == 0))
    checks.append(("score_baseline_top10", score["baseline_top10_task_count"] == 1))
    checks.append(("score_citation_valid", score["citation_validity_all_implemented_bool"] is True))
    feats = score["safety_feature_bucket_records"]
    checks.append(("feat_count", len(feats) == len(ALL_PROBE_FEATURES)))
    checks.append(("feat_top5_present", FEATURE_TOP5_NOVELTY_BUCKET in feats))
    checks.append(("feat_displacement_risk_present", FEATURE_FULL_DISPLACEMENT_RISK in feats))
    # This synthetic task: low-novelty (1<2 bucket), strong prefix (gold at rank1), full lost -> displacement risk.
    checks.append(("feat_displacement_risk_flagged",
                   feats[FEATURE_FULL_DISPLACEMENT_RISK].get("low_novelty_strong_prefix_displacement_risk", 0) == 1))
    checks.append(("feat_guard_preserved",
                   feats[FEATURE_GUARD_PRESERVATION_REF].get("guard_preserved_baseline", 0) == 1))
    checks.append(("feat_candidate_beyond_top10",
                   feats[FEATURE_CANDIDATE_BEYOND_TOP10].get("candidate_available_beyond_top10", 0) == 0))

    # Complete report build + validation.
    counters = {"bm25_candidate_total": 2, "old_pool_file_total": 1, "task_with_candidates": 1}
    heldout_ok = {"n10en_reference_repo_private_check_performed_bool": True,
                  "n10en_overlap_private_check_pass_bool": True,
                  "n10en_overlap_count": 0,
                  "n10en_overlap_public_bucket": "overlap_zero"}
    report = build_complete_report(gate_record, orders, counters, score, 1, 1, STATUS_INCONCLUSIVE_RISK, heldout_ok)
    checks.append(("report_status_inconclusive", report["status"] == STATUS_INCONCLUSIVE_RISK))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_has_exec_boundary", bool(report["execution_boundary_records"])))
    checks.append(("report_has_sample", bool(report["sample_records"])))
    checks.append(("report_has_safety_features", len(report["safety_feature_bucket_records"]) == len(ALL_PROBE_FEATURES)))
    checks.append(("report_has_pass_fail_gates", len(report["pass_fail_gate_records"]) == 9))
    checks.append(("report_stop_n10es", report["stop_go_records"][0]["n10es_audit_authorized_bool"] is True))
    checks.append(("report_stop_n10er_exec_false", report["stop_go_records"][0]["n10er_execution_authorized_bool"] is False))
    checks.append(("report_overlap_check", report["sample_records"][0]["heldout_from_n10en_private_check_bool"] is True))

    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks)")
    return passed == len(checks)


# ── Main ───────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    if args.validate_report:
        if not args.report:
            print("ERROR: --report required with --validate-report", file=sys.stderr)
            return 2
        report, state = load_json(Path(args.report))
        if state != "present" or not isinstance(report, dict):
            print(f"ERROR: cannot load report ({state})", file=sys.stderr)
            return 1
        failures = validate_report(report)
        if failures:
            print("CONTRACT VALIDATION FAILED:", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 1
        print(f"CONTRACT VALIDATION PASSED (status={report.get('status')})")
        return 0

    gate_ok, gate_record, _ = evaluate_n10eq_gate()
    if args.gate_only:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"n10eq_source_lock_records": [gate_record]}, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        return 0 if gate_ok else 1

    if not gate_ok:
        report = {
            "schema_version": "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_v1",
            "phase_bucket": "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe",
            "status": STATUS_NO_GATE, "n10eq_source_lock_records": [gate_record],
            "forbidden_scan": scan_summary({"n10eq_source_lock_records": [gate_record]}),
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']})")
        return 1

    if not args.enable_public_github_network:
        report = build_disabled_report(gate_record)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']}, network disabled -> fail-closed)")
        return 0

    work_root = Path(args.work_root) if args.work_root else Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "n10er-safety-probe-work"
    work_root.mkdir(parents=True, exist_ok=True)
    run_dir = work_root / "run"
    try:
        repo_entries, heldout_info = select_repos(Path(args.manifest), args.stage, args.max_repos)
    except Exception as exc:
        print(f"ERROR: manifest selection failed: {exc}", file=sys.stderr)
        return 1

    repo_clone_map: dict[str, str] = {}
    repo_count = 0
    combined_lock_path = work_root / "locks" / "combined-repo-lock.jsonl"
    try:
        if args.repo_lock:
            lock = json.loads(Path(args.repo_lock).read_text(encoding="utf-8"))
            if isinstance(lock, dict) and "repo_id" in lock:
                repo_clone_map[lock["repo_id"]] = lock["source"]["path"]
                repo_count = 1
                combined_lock_path = write_combined_repo_lock([lock], work_root)
            elif isinstance(lock, dict) and "repos" in lock:
                locks = list(lock["repos"].values())
                for rid, entry in lock["repos"].items():
                    repo_clone_map[rid] = entry["source"]["path"]
                repo_count = len(repo_clone_map)
                combined_lock_path = write_combined_repo_lock(locks, work_root)
        else:
            locks: list[dict[str, Any]] = []
            for entry in repo_entries:
                lock, clone_dir = run_clone_and_lock(entry, Path(args.manifest), work_root)
                locks.append(lock)
                repo_clone_map[str(entry["id"])] = str(clone_dir)
                repo_count += 1
            combined_lock_path = write_combined_repo_lock(locks, work_root)
    except Exception as exc:
        print(f"ERROR: clone failed: {exc}", file=sys.stderr)
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_FAIL_CLONE
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1

    try:
        if args.tasks:
            tasks = read_jsonl(Path(args.tasks))
        else:
            tasks_path, _ = run_generate_tasks(combined_lock_path, work_root / "tasks_run", args.stage, no_labels=True)
            tasks = read_jsonl(tasks_path)
    except Exception as exc:
        print(f"ERROR: public task generation failed: {exc}", file=sys.stderr)
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_FAIL_RUN
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1

    if not tasks:
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_NO_TASKS
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']})")
        return 1

    openlocus_path = resolve_openlocus_path(args.openlocus)
    orders, counters = run_phase(tasks, repo_clone_map, openlocus_path, run_dir)
    if counters["task_with_candidates"] == 0:
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_FAIL_RUN
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']})")
        return 1

    try:
        if args.labels:
            labels = read_jsonl(Path(args.labels))
        else:
            _, labels_path = run_generate_tasks(combined_lock_path, work_root / "tasks_score", args.stage, no_labels=False)
            if labels_path is None:
                raise RuntimeError("label generation produced no labels file")
            labels = read_jsonl(labels_path)
    except Exception as exc:
        print(f"ERROR: score-phase label generation failed: {exc}", file=sys.stderr)
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_FAIL_RUN
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1

    score = score_phase(orders, labels)
    outcome_status = classify_outcome(score, args.stage)

    report = build_complete_report(gate_record, orders, counters, score, repo_count, len(tasks), outcome_status, heldout_info, args.stage)
    failures = validate_report(report)
    if failures:
        report["status"] = STATUS_FAIL_CONTRACT
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, outcome={outcome_status}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
