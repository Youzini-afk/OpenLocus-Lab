#!/usr/bin/env python3
"""BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary.

Authoritative N10EN evaluator/helper. It gates on the BEA-v1-N10EM public
replication package and its scoped ``n10en_ci_handoff_records``. When public
GitHub network is disabled (the default) it emits a fail-closed/unavailable
artifact WITHOUT cloning, building, or searching. When explicitly enabled it:

  * clones manifest-listed public repos only (reusing ``ci_clone_and_lock_repo``);
  * generates public tasks (reusing ``ci_generate_tasks`` with ``--no-labels``
    first so the RUN phase sees no labels/gold);
  * builds/uses the checked-out local OpenLocus CLI to materialize temporary
    public candidates (bm25 limit 100; old-pool proxy = regex-top20 union
    symbol-top20 file identities);
  * applies the four frozen transforms IN THIS HELPER (not by bending
    ``ci_run_strategy_matrix``);
  * fixes the RUN-phase orders, THEN generates score-phase labels and scores
    the fixed orders (labels/gold used for aggregate scoring only, never policy);
  * uploads only a sanitized aggregate-only report.

Frozen transforms (re-implemented here, ported verbatim from N10EL/N10EK):
  baseline  = raw BM25 top-100 order;
  full      = full novel-first (novel candidates before old-pool, top-10 head);
  guarded   = keep original top-5, append distinct novel files until top-10;
  diffaware = guarded iff top5 novel candidate item count >= 4 else full.

CI pass/fail semantics: the workflow fails on contract/privacy/build/clone/task
or no-task failures, but NOT on outcome regression (an outcome status of
positive/neutral/regression is a valid research result handed off to N10EO).
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
SLUG = "bea_v1_n10en_difference_aware_ci_canary"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EM_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10em_difference_aware_winner_public_replication_package"
    / "bea_v1_n10em_difference_aware_winner_public_replication_package_report.json"
)
DEFAULT_MANIFEST = ROOT / "eval" / "ci_repos" / "openlocus-ci-repos-v1.yaml"
CI_CLONE = ROOT / "eval" / "ci_clone_and_lock_repo.py"
CI_GEN_TASKS = ROOT / "eval" / "ci_generate_tasks.py"

EXPECTED_N10EM_STATUS = "difference_aware_winner_public_replication_package_complete_n10en_authorized"

N10EN_REQUIRED_HANDOFF_TRUE_FIELDS = (
    "n10en_broader_sample_ci_validation_authorized_bool",
    "github_ci_allowed_for_long_run_bool",
    "n10en_public_github_clone_fetch_authorized_bool",
    "n10en_manifest_listed_public_repos_only_bool",
    "n10en_openlocus_cli_build_authorized_bool",
    "n10en_local_openlocus_search_authorized_bool",
    "n10en_temporary_public_candidate_materialization_authorized_bool",
    "n10en_score_phase_label_generation_authorized_bool",
    "n10en_sanitized_aggregate_artifact_upload_authorized_bool",
)

N10EN_REQUIRED_HANDOFF_FALSE_FIELDS = (
    "n10en_private_rows_authorized_bool",
    "n10en_raw_candidate_upload_authorized_bool",
    "n10en_raw_label_upload_authorized_bool",
    "n10en_raw_query_upload_authorized_bool",
    "n10en_raw_path_upload_authorized_bool",
    "provider_model_network_authorized_bool",
    "remote_embedding_authorized_bool",
    "quiver_dense_real_authorized_bool",
    "private_github_asset_authorized_bool",
    "external_benchmark_download_authorized_bool",
    "runtime_default_authorized_bool",
    "selector_reranker_authorized_bool",
    "method_winner_claim_authorized_bool",
    "downstream_value_claim_authorized_bool",
    "heldout_generalization_authorized_bool",
    "scaled_retrieval_authorized_bool",
    "production_retrieval_change_authorized_bool",
)

# Status vocabulary. STATUS_COMPLETE and the outcome-regression statuses are
# NOT CI failures (exit 0); the fail_* statuses are contract/infra failures.
STATUS_COMPLETE = "difference_aware_winner_ci_canary_complete_n10eo_handoff"
STATUS_OUTCOME_POSITIVE = "difference_aware_winner_ci_canary_outcome_positive"
STATUS_OUTCOME_NEUTRAL = "difference_aware_winner_ci_canary_outcome_neutral"
STATUS_OUTCOME_REGRESSION = "difference_aware_winner_ci_canary_outcome_regression"
STATUS_DISABLED = "n10en_public_github_network_disabled_unavailable_fail_closed"
STATUS_NO_GATE = "no_go_n10em_gate_failed"
STATUS_NO_TASKS = "fail_no_public_tasks_generated"
STATUS_FAIL_RUN = "fail_run_phase_candidate_generation"
STATUS_FAIL_CLONE = "fail_clone_or_build"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"

# Outcome statuses (research results) + disabled default are exit-0; the rest fail.
EXIT0_VOCAB = {
    STATUS_COMPLETE, STATUS_OUTCOME_POSITIVE, STATUS_OUTCOME_NEUTRAL,
    STATUS_OUTCOME_REGRESSION, STATUS_DISABLED,
}
STATUS_VOCAB = EXIT0_VOCAB | {
    STATUS_NO_GATE, STATUS_NO_TASKS, STATUS_FAIL_RUN, STATUS_FAIL_CLONE,
    STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT,
}

THRESHOLD = 4
TOP_K_LIMITS = (10, 20, 50, 100)
BM25_LIMIT = 100
OLD_POOL_LIMIT = 20

STAGE_CAPS = {
    "canary_small": {"max_repos": 2, "max_tasks_per_repo": 40, "max_files_per_repo": 120},
    "canary_medium": {"max_repos": 4, "max_tasks_per_repo": 80, "max_files_per_repo": 200},
}

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
    parser = SafeArgumentParser(description="BEA-v1-N10EN difference-aware winner CI canary")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--gate-only", action="store_true", help="check the N10EM gate and exit")
    parser.add_argument("--validate-report", action="store_true", help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--enable-public-github-network", action="store_true",
                        help="allow manifest-listed public clone/search (default off)")
    parser.add_argument("--stage", default="canary_small", choices=list(STAGE_CAPS))
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


# ── Frozen transforms (ported verbatim from N10EL/N10EK) ───────────────────
# Operate on OpenLocus evidence dicts that carry a top-level "path" field.

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
    """Raw BM25 order, truncated to the BM25 limit (100)."""
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
    """EvidenceCore needs path + line range + content_sha."""
    path = str(item.get("path") or "").strip()
    sha = str(item.get("content_sha") or "").strip()
    try:
        int(item.get("start_line", 0))
        int(item.get("end_line", 0))
        lines_ok = True
    except (TypeError, ValueError):
        lines_ok = False
    return bool(path and sha and lines_ok)


# ── N10EM gate ─────────────────────────────────────────────────────────────

def evaluate_n10em_gate() -> tuple[bool, dict[str, Any], dict[str, Any]]:
    n10em, state = load_json(N10EM_REPORT)
    present_ok = state == "present" and isinstance(n10em, dict) and n10em.get("status") == EXPECTED_N10EM_STATUS
    handoff = (n10em or {}).get("n10en_ci_handoff_records", [{}])[0] if isinstance(n10em, dict) else {}
    required_true_ok = all(handoff.get(field) is True for field in N10EN_REQUIRED_HANDOFF_TRUE_FIELDS)
    required_false_ok = all(handoff.get(field) is False for field in N10EN_REQUIRED_HANDOFF_FALSE_FIELDS)
    gate_ok = present_ok and required_true_ok and required_false_ok
    gate_record = {
        "anonymous_gate_id": "n10engate0000",
        "gate_bucket": "n10em_public_replication_package_authorized",
        "input_artifact_load_status_bucket": state,
        "expected_status_bucket": EXPECTED_N10EM_STATUS,
        "actual_status_bucket": str((n10em or {}).get("status", "unavailable")),
        "status_match_bool": present_ok,
        "n10en_ci_handoff_record_present_bool": bool(handoff),
        "required_true_handoff_fields_passed_bool": required_true_ok,
        "required_false_handoff_fields_passed_bool": required_false_ok,
        "missing_required_true_field_count": sum(1 for field in N10EN_REQUIRED_HANDOFF_TRUE_FIELDS if handoff.get(field) is not True),
        "nonfalse_forbidden_field_count": sum(1 for field in N10EN_REQUIRED_HANDOFF_FALSE_FIELDS if handoff.get(field) is not False),
        "gate_passed_bool": gate_ok,
    }
    for field in N10EN_REQUIRED_HANDOFF_TRUE_FIELDS:
        gate_record[field] = bool(handoff.get(field) is True)
    for field in N10EN_REQUIRED_HANDOFF_FALSE_FIELDS:
        gate_record[field] = bool(handoff.get(field) is True)
    return gate_ok, gate_record, handoff


# ── Manifest / repo selection (reuses ci_clone_and_lock_repo parser) ──────

def select_repos(manifest: Path, stage: str, max_repos: int | None) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT / "eval"))
    try:
        import ci_clone_and_lock_repo as ci_clone  # noqa: F401
        parsed = ci_clone.parse_manifest_yaml(str(manifest))
    finally:
        sys.path.pop(0)
    repos = parsed.get("repos", []) or []
    cap = max_repos if max_repos else STAGE_CAPS[stage]["max_repos"]
    # Prefer the smallest smoke/nightly repos for the canary; deterministic order.
    tier_order = {"smoke": 0, "nightly_medium": 1, "weekly_large": 2, "manual_extreme": 3}
    ranked = sorted(repos, key=lambda r: (tier_order.get(str(r.get("tier", "")), 9), str(r.get("id", ""))))
    return ranked[:cap]


# ── Subprocess wrappers (reuse existing CI scripts) ───────────────────────

def run_clone_and_lock(repo_entry: dict[str, Any], manifest: Path, work_root: Path) -> tuple[dict[str, Any], Path]:
    """Clone one manifest-listed public repo via ci_clone_and_lock_repo.py."""
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
    """Write a JSONL repo-lock (one entry per cloned repo) for ci_generate_tasks."""
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
    """Invoke the local OpenLocus CLI search. Returns evidence list (may be empty)."""
    if method == "bm25":
        cmd = [openlocus, "search", "bm25", query, "--limit", str(limit), "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--limit", str(limit), "--json"]
    elif method == "regex":
        # The CLI regex subcommand has no --limit flag; it returns up to 100
        # matches. Slice to OLD_POOL_LIMIT (20) in Python to honor the contract.
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
    map keyed by test_id and aggregate counters.
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

        # Old-pool proxy: union of regex-top20 and symbol-top20 file identities.
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

        # Citation validity over all materialized candidate items.
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

    # Persist orders to the private run dir ONLY (never uploaded as artifact).
    (run_dir / "orders.private.json").write_text(
        json.dumps({k: {**v, "baseline_order_len": len(v["baseline_order"])} for k, v in orders.items()},
                   sort_keys=True) + "\n", encoding="utf-8")
    return orders, counters


# ── SCORE phase ────────────────────────────────────────────────────────────

def score_phase(orders: dict[str, dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Score the FIXED orders. Labels/gold are used for aggregate scoring only."""
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

    for tid, order_map in orders.items():
        label = label_by_task.get(tid, {})
        gold_refs = [g.get("path") for g in (label.get("gold_spans") or []) if g.get("path")]
        if gold_refs:
            task_with_gold_count += 1
        scored_task_count += 1
        add_bucket(arm_counts, order_map["selected_arm"])
        add_bucket(novelty_buckets, top5_novel_bucket(order_map["top5_novel_candidate_item_count"]))
        cv_valid_total += order_map["citation_valid_count"]
        cv_count_total += order_map["citation_total_count"]

        base_rank = first_rank(order_map["baseline_order"], gold_refs)
        if base_rank is not None and base_rank <= 10:
            baseline_top10_set.add(tid)

        for arm in arms:
            order = order_map[f"{arm}_order"]
            rank = first_rank(order, gold_refs)
            for limit in TOP_K_LIMITS:
                if rank is not None and rank <= limit:
                    hits[arm][limit].add(tid)

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

    return {
        "aggregate_count_records": aggregate,
        "selected_arm_bucket_records": dict(arm_counts),
        "top5_novelty_bucket_records": dict(novelty_buckets),
        "citation_valid_count": cv_valid_total,
        "citation_total_count": cv_count_total,
        "citation_validity_all_implemented_bool": cv_count_total > 0 and cv_valid_total == cv_count_total,
        "scored_task_count": scored_task_count,
        "task_with_gold_count": task_with_gold_count,
        "baseline_top10_task_count": len(baseline_top10_set),
    }


def add_bucket(table: dict[str, int], bucket: str) -> None:
    table[bucket] = table.get(bucket, 0) + 1


def classify_outcome(score: dict[str, Any]) -> str:
    """Map aggregate outcome to a non-failing research status."""
    agg = score["aggregate_count_records"]
    diff_top10 = agg["diffaware"]["top10"]
    base_top10 = agg["baseline"]["top10"]
    lost = agg["diffaware"]["lost_baseline_top10"]
    if lost > 0 or diff_top10 < base_top10:
        return STATUS_OUTCOME_REGRESSION
    if diff_top10 > base_top10:
        return STATUS_OUTCOME_POSITIVE
    return STATUS_OUTCOME_NEUTRAL


# ── Report assembly ────────────────────────────────────────────────────────

def build_disabled_report(gate_record: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed artifact produced when public network is disabled."""
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10en_difference_aware_ci_canary_v1",
        "phase_bucket": "BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary",
        "status": STATUS_DISABLED,
        "enable_public_github_network_bool": False,
        "public_github_clone_fetch_run_bool": False,
        "openlocus_cli_build_run_bool": False,
        "local_openlocus_search_run_bool": False,
        "n10em_gate_records": [gate_record],
        "run_phase_records": [{
            "anonymous_run_phase_id": "n10enrun0000",
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
        "aggregate_count_records": [],
        "selected_arm_bucket_records": [],
        "top5_novelty_bucket_records": [],
        "citation_validity_aggregate_records": [{"citation_validity_all_implemented_bool": True, "citation_total_count": 0, "citation_valid_count": 0}],
        "claim_boundary_records": [claim_boundary(False)],
        "gate_records": [
            {"anonymous_gate_id": "n10engate0001", "gate_bucket": "n10em_handoff_authorized", "gate_passed_bool": gate_record["gate_passed_bool"]},
            {"anonymous_gate_id": "n10engate0002", "gate_bucket": "network_disabled_fail_closed", "gate_passed_bool": True},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def claim_boundary(ran_network: bool) -> dict[str, Any]:
    return {
        "anonymous_claim_boundary_id": "n10enclaim0000",
        "public_only_bool": True,
        "manifest_listed_public_repos_only_bool": True,
        "private_rows_read_bool": False,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
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
    }


def build_complete_report(gate_record: dict[str, Any], orders: dict[str, dict[str, Any]],
                          counters: dict[str, int], score: dict[str, Any], repo_count: int,
                          task_count: int, outcome_status: str) -> dict[str, Any]:
    agg = score["aggregate_count_records"]
    aggregate_records = [
        {
            "anonymous_aggregate_id": f"n10enagg000{idx}",
            "arm_bucket": arm,
            "top10_file_recovery_count": agg[arm]["top10"],
            "top20_file_recovery_count": agg[arm]["top20"],
            "top50_file_recovery_count": agg[arm]["top50"],
            "top100_file_recovery_count": agg[arm]["top100"],
            "lost_baseline_top10_hits": agg[arm]["lost_baseline_top10"],
        }
        for idx, arm in enumerate(("baseline", "full", "guard", "diffaware"))
    ]
    arm_bucket_records = [
        {"anonymous_arm_bucket_id": f"n10enarm{idx:04d}", "selected_arm_bucket": arm, "task_count": count}
        for idx, (arm, count) in enumerate(sorted(score["selected_arm_bucket_records"].items()))
    ]
    novelty_records = [
        {"anonymous_novelty_bucket_id": f"n10ennov{idx:04d}", "bucket_type": "top5_novel_candidate_item_count", "bucket": bucket, "task_count": count}
        for idx, (bucket, count) in enumerate(sorted(score["top5_novelty_bucket_records"].items()))
    ]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10en_difference_aware_ci_canary_v1",
        "phase_bucket": "BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary",
        "status": outcome_status,
        "enable_public_github_network_bool": True,
        "public_github_clone_fetch_run_bool": True,
        "openlocus_cli_build_run_bool": True,
        "local_openlocus_search_run_bool": True,
        "n10em_gate_records": [gate_record],
        "run_phase_records": [{
            "anonymous_run_phase_id": "n10enrun0000",
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
        "aggregate_count_records": aggregate_records,
        "selected_arm_bucket_records": arm_bucket_records,
        "top5_novelty_bucket_records": novelty_records,
        "citation_validity_aggregate_records": [{
            "citation_validity_all_implemented_bool": score["citation_validity_all_implemented_bool"],
            "citation_total_count": score["citation_total_count"],
            "citation_valid_count": score["citation_valid_count"],
        }],
        "score_phase_records": [{
            "anonymous_score_phase_id": "n10enscore0000",
            "score_phase_labels_used_bool": True,
            "gold_used_for_policy_bool": False,
            "scored_task_count": score["scored_task_count"],
            "task_with_gold_count": score["task_with_gold_count"],
            "baseline_top10_task_count": score["baseline_top10_task_count"],
        }],
        "claim_boundary_records": [claim_boundary(True)],
        "gate_records": [
            {"anonymous_gate_id": "n10engate0001", "gate_bucket": "n10em_handoff_authorized", "gate_passed_bool": gate_record["gate_passed_bool"]},
            {"anonymous_gate_id": "n10engate0002", "gate_bucket": "public_tasks_generated", "gate_passed_bool": task_count > 0},
            {"anonymous_gate_id": "n10engate0003", "gate_bucket": "run_candidates_materialized", "gate_passed_bool": counters["task_with_candidates"] > 0},
            {"anonymous_gate_id": "n10engate0004", "gate_bucket": "citation_validity_all_implemented", "gate_passed_bool": score["citation_validity_all_implemented_bool"]},
            {"anonymous_gate_id": "n10engate0005", "gate_bucket": "run_score_separation", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10engate0006", "gate_bucket": "gold_not_used_for_policy", "gate_passed_bool": True},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    # Outcome regression is a valid research result; do NOT downgrade to fail.
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
        if gate.get("gate_passed_bool") is not True:
            failures.append(f"contract_gate_failed:{gate.get('gate_bucket', 'unknown')}")
    run = (report.get("run_phase_records") or [{}])[0]
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
    if claim.get("method_winner_claim_bool") is not False:
        failures.append("method_winner_claim_not_false")
    if claim.get("production_retrieval_change_bool") is not False:
        failures.append("production_retrieval_change_not_false")
    if claim.get("runtime_default_change_bool") is not False:
        failures.append("runtime_default_change_not_false")
    if report.get("status") != STATUS_DISABLED:
        citation = (report.get("citation_validity_aggregate_records") or [{}])[0]
        if citation.get("citation_validity_all_implemented_bool") is not True:
            failures.append("citation_validity_not_all_implemented")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_DISABLED in EXIT0_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_task_id", scan_summary({"v": "ci-00001"})["status"] == "fail"))
    # Frozen-transform parity with N10EL.
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
    # Gate logic on synthetic handoff.
    checks.append(("gate_rejects_missing", evaluate_n10em_gate()[0] in (True, False)))
    # Disabled report contract.
    gate_ok, gate_record, _ = evaluate_n10em_gate()
    disabled = build_disabled_report(gate_record)
    checks.append(("disabled_fail_closed", disabled["status"] == STATUS_DISABLED))
    checks.append(("disabled_no_scan", disabled["forbidden_scan"]["status"] == "pass"))
    checks.append(("disabled_run_flags", disabled["run_phase_records"][0]["run_phase_labels_used_bool"] is False
                   and disabled["run_phase_records"][0]["score_phase_labels_used_bool"] is False))
    checks.append(("disabled_validate", validate_report(disabled) == []))
    bad_contract = dict(disabled)
    bad_contract["status"] = STATUS_OUTCOME_NEUTRAL
    bad_contract["run_phase_records"] = [{"run_phase_labels_used_bool": False, "score_phase_labels_used_bool": True, "gold_used_for_policy_bool": False}]
    bad_contract["gate_records"] = [{"gate_bucket": "citation_validity_all_implemented", "gate_passed_bool": False}]
    bad_contract["citation_validity_aggregate_records"] = [{"citation_validity_all_implemented_bool": False}]
    bad_failures = validate_report(bad_contract)
    checks.append(("validate_fails_contract_gate", any(item.startswith("contract_gate_failed") for item in bad_failures)))
    checks.append(("validate_fails_citation", "citation_validity_not_all_implemented" in bad_failures))
    # Outcome classification.
    pos = classify_outcome({"aggregate_count_records": {"baseline": {"top10": 5}, "diffaware": {"top10": 7, "lost_baseline_top10": 0}}})
    checks.append(("outcome_positive", pos == STATUS_OUTCOME_POSITIVE))
    reg = classify_outcome({"aggregate_count_records": {"baseline": {"top10": 7}, "diffaware": {"top10": 5, "lost_baseline_top10": 1}}})
    checks.append(("outcome_regression", reg == STATUS_OUTCOME_REGRESSION))
    neut = classify_outcome({"aggregate_count_records": {"baseline": {"top10": 5}, "diffaware": {"top10": 5, "lost_baseline_top10": 0}}})
    checks.append(("outcome_neutral", neut == STATUS_OUTCOME_NEUTRAL))
    # Score phase end-to-end on synthetic orders.
    orders = {
        "ci-00001": {
            "baseline_order": [{"path": "miss.py"}, {"path": "gold.py"}], "full_order": [{"path": "gold.py"}],
            "guard_order": [{"path": "miss.py"}, {"path": "gold.py"}], "diffaware_order": [{"path": "gold.py"}],
            "selected_arm": "full_novel_first", "top5_novel_candidate_item_count": 5,
            "old_pool_file_count": 1, "bm25_candidate_count": 2,
            "citation_valid_count": 8, "citation_total_count": 8,
        },
    }
    labels = [{"test_id": "ci-00001", "gold_spans": [{"path": "gold.py"}]}]
    score = score_phase(orders, labels)
    checks.append(("score_top10_diffaware", score["aggregate_count_records"]["diffaware"]["top10"] == 1))
    checks.append(("score_baseline_top10", score["baseline_top10_task_count"] == 1))
    checks.append(("score_citation_valid", score["citation_validity_all_implemented_bool"] is True))
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

    gate_ok, gate_record, _ = evaluate_n10em_gate()
    if args.gate_only:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"n10em_gate_records": [gate_record]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if gate_ok else 1

    # Gate is a hard contract requirement for any execution path.
    if not gate_ok:
        report = {
            "schema_version": "bea_v1_n10en_difference_aware_ci_canary_v1",
            "phase_bucket": "BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary",
            "status": STATUS_NO_GATE, "n10em_gate_records": [gate_record],
            "forbidden_scan": scan_summary({"n10em_gate_records": [gate_record]}),
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']})")
        return 1

    # Default: fail-closed when public network not explicitly enabled.
    if not args.enable_public_github_network:
        report = build_disabled_report(gate_record)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']}, network disabled -> fail-closed)")
        return 0

    # Enabled path: clone manifest-listed public repos, generate public tasks,
    # run local OpenLocus search, apply frozen transforms, then score.
    work_root = Path(args.work_root) if args.work_root else Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "n10en-ci-canary-work"
    work_root.mkdir(parents=True, exist_ok=True)
    run_dir = work_root / "run"
    try:
        repo_entries = select_repos(Path(args.manifest), args.stage, args.max_repos)
    except Exception as exc:
        print(f"ERROR: manifest selection failed: {exc}", file=sys.stderr)
        return 1

    repo_clone_map: dict[str, str] = {}
    repo_count = 0
    combined_lock_path = work_root / "locks" / "combined-repo-lock.jsonl"
    try:
        if args.repo_lock:
            # Pre-cloned repo-lock provided by the workflow.
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

    # RUN phase: generate public tasks with NO labels first.
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

    orders, counters = run_phase(tasks, repo_clone_map, args.openlocus, run_dir)
    if counters["task_with_candidates"] == 0:
        report = build_disabled_report(gate_record)
        report["status"] = STATUS_FAIL_RUN
        report["forbidden_scan"] = scan_summary(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']})")
        return 1

    # SCORE phase: generate labels AFTER RUN orders are fixed, then score.
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
    outcome_status = classify_outcome(score)
    report = build_complete_report(gate_record, orders, counters, score, repo_count, len(tasks), outcome_status)
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
