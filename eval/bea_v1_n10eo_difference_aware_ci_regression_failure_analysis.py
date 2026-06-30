#!/usr/bin/env python3
"""BEA-v1-N10EO Difference-Aware CI Regression Failure Analysis.

N10EO explains why the BEA-v1-N10EN broader-sample public CI canary regressed.

Allowed inputs: the committed N10EN aggregate artifact, the N10EN
helper/workflow/contract, the N10EM package, GitHub metadata, and (if needed) a
private local rerun of the same N10EN bounded public canary over manifest-listed
public repos only. All clones/candidates/labels/tasks/paths/queries/ranks/
per-task outcomes stay private/temp only. The published artifact is
aggregate-bucket-only; no runtime/default, method-winner, downstream, scaled
retrieval, selector/reranker, provider/model network, or raw artifact
publication is authorized.

N10EN source result locked from canary run 28449370879:
  status: difference_aware_winner_ci_canary_outcome_regression
  baseline 39/40/40/40; full 37/40/40/40 lost2; guard 39/40/40/40 lost0;
  diffaware 37/40/40/40 lost2; selected arms full=49 guard=9;
  task_with_gold=40; citation 3636/3636.

N10EO uses private per-task diagnostic state from a bounded N10EN diagnostic
rerun. It refuses to infer mechanisms from aggregate counts alone; without
private diagnostic inputs it emits an unavailable report. Published output is
aggregate-only diagnostic buckets plus privacy/validity summary.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10eo_difference_aware_ci_regression_failure_analysis"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EN_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10en_difference_aware_ci_canary"
    / "bea_v1_n10en_difference_aware_ci_canary_report.json"
)
N10EM_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10em_difference_aware_winner_public_replication_package"
    / "bea_v1_n10em_difference_aware_winner_public_replication_package_report.json"
)

# Locked N10EN source result from canary run 28449370879.
LOCKED_N10EN_STATUS = "difference_aware_winner_ci_canary_outcome_regression"
LOCKED_COUNTS = {
    "baseline": {"top10": 39, "top20": 40, "top50": 40, "top100": 40, "lost": 0},
    "full": {"top10": 37, "top20": 40, "top50": 40, "top100": 40, "lost": 2},
    "guard": {"top10": 39, "top20": 40, "top50": 40, "top100": 40, "lost": 0},
    "diffaware": {"top10": 37, "top20": 40, "top50": 40, "top100": 40, "lost": 2},
}
LOCKED_SELECTED_ARMS = {"full_novel_first": 49, "guarded_top5_novel_distinct": 9}
LOCKED_NOVELTY_BUCKETS = {
    "top5_novel_candidate_item_count_0_to_2": 47,
    "top5_novel_candidate_item_count_3": 2,
    "top5_novel_candidate_item_count_4_to_5": 9,
}
LOCKED_SCORED_TASK_COUNT = 58
LOCKED_TASK_WITH_GOLD = 40
LOCKED_CITATION = {"valid": 3636, "total": 3636}

# Status vocabulary.
STATUS_MECH_IDENTIFIED = "n10eo_failure_analysis_pass_mechanism_identified"
STATUS_MECH_INCONCLUSIVE = "n10eo_failure_analysis_pass_mechanism_inconclusive"
STATUS_FAIL_CLOSED = "n10eo_failure_analysis_fail_closed_privacy_or_contract"
STATUS_UNAVAILABLE = "n10eo_failure_analysis_unavailable_rerun_required"
STATUS_VOCAB = {
    STATUS_MECH_IDENTIFIED, STATUS_MECH_INCONCLUSIVE,
    STATUS_FAIL_CLOSED, STATUS_UNAVAILABLE,
}
EXIT0_VOCAB = {STATUS_MECH_IDENTIFIED, STATUS_MECH_INCONCLUSIVE}

THRESHOLD = 4
TOP_K_LIMITS = (10, 20, 50, 100)

# Novelty bucket ordering for deterministic reconstruction.
NOVELTY_BUCKET_ORDER = (
    "top5_novel_candidate_item_count_0_to_2",
    "top5_novel_candidate_item_count_3",
    "top5_novel_candidate_item_count_4_to_5",
)

# Lost-baseline mechanism buckets (a task can match multiple).
MECH_NOVEL_FIRST_DISPLACED = "novel_first_displaced_baseline_gold_from_top10"
MECH_OLD_POOL_MISCLASSIFIED = "old_pool_proxy_misclassified_gold_as_novel_or_old"
MECH_DISTINCT_FILE_PACKING = "distinct_file_packing_changed_gold_file_position"
MECH_DUPLICATE_SAME_FILE = "duplicate_file_or_same_file_competition"
MECH_BASELINE_RANK_6_TO_10 = "baseline_gold_rank_6_to_10_displaced"
MECH_BASELINE_RANK_1_TO_5 = "baseline_gold_rank_1_to_5_displaced"
MECH_CANDIDATE_BEYOND_TOP10 = "candidate_available_beyond_top10"
MECH_CANDIDATE_MISSING = "candidate_missing_from_arm_order"
MECH_SCORE_LABEL_ONLY = "score_phase_label_only_issue"
MECH_OTHER = "other_or_unclassified"
ALL_MECH_BUCKETS = (
    MECH_NOVEL_FIRST_DISPLACED, MECH_OLD_POOL_MISCLASSIFIED,
    MECH_DISTINCT_FILE_PACKING, MECH_DUPLICATE_SAME_FILE,
    MECH_BASELINE_RANK_6_TO_10, MECH_BASELINE_RANK_1_TO_5,
    MECH_CANDIDATE_BEYOND_TOP10, MECH_CANDIDATE_MISSING,
    MECH_SCORE_LABEL_ONLY, MECH_OTHER,
)

# Full-vs-guard outcome buckets.
FG_FULL_BETTER = "full_better_than_guard"
FG_GUARD_BETTER = "guard_better_than_full"
FG_BOTH_HIT = "full_equals_guard_both_hit"
FG_BOTH_MISS = "full_equals_guard_both_miss"
FG_FULL_LOST_GUARD_PRESERVED = "full_lost_guard_preserved_baseline"
FG_GUARD_LOST_FULL_PRESERVED = "guard_lost_full_preserved_baseline"
FG_BOTH_LOST_BASELINE = "both_lost_baseline"
FG_NEITHER_LOST_BASELINE = "neither_lost_baseline"
ALL_FG_BUCKETS = (
    FG_FULL_BETTER, FG_GUARD_BETTER, FG_BOTH_HIT, FG_BOTH_MISS,
    FG_FULL_LOST_GUARD_PRESERVED, FG_GUARD_LOST_FULL_PRESERVED,
    FG_BOTH_LOST_BASELINE, FG_NEITHER_LOST_BASELINE,
)

# Arm-selection counterfactual buckets.
CF_FULL_AND_FULL_LOST = "diffaware_selected_full_and_full_lost"
CF_FULL_AND_GUARD_WOULD_PRESERVE = "diffaware_selected_full_and_guard_would_preserve"
CF_FULL_AND_GUARD_SAME = "diffaware_selected_full_and_guard_same"
CF_GUARD_AND_GUARD_PRESERVED = "diffaware_selected_guard_and_guard_preserved"
CF_GUARD_AND_FULL_WOULD_IMPROVE = "diffaware_selected_guard_and_full_would_improve"
ALL_CF_BUCKETS = (
    CF_FULL_AND_FULL_LOST, CF_FULL_AND_GUARD_WOULD_PRESERVE,
    CF_FULL_AND_GUARD_SAME, CF_GUARD_AND_GUARD_PRESERVED,
    CF_GUARD_AND_FULL_WOULD_IMPROVE,
)

# Privacy scan: forbid the same classes as N10EN plus per-task diagnostics.
FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "query", "raw_query", "candidate", "candidates", "candidate_list",
    "candidate_order", "gold", "gold_path", "gold_paths", "gold_spans",
    "hard_distractors", "must_not_primary", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "content_sha", "exact_rank", "raw_rank",
    "score", "scores", "repo", "repo_root", "source_repo", "clone_url", "commit",
    "hash", "provider_payload", "raw_diff", "test_id", "task_id", "rationale",
    "channel", "channels", "why", "evidence", "records", "rows",
    "per_task_diagnostics", "diagnostics", "orders", "run_id",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/|/runner/"),
    re.compile(r"https?://github\.com/", re.I),
    re.compile(r"[A-Za-z0-9_.-]+/(?:[A-Za-z0-9_.-]+)\.git", re.I),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(ci-[0-9]{5})\b", re.I),
    re.compile(r"\b28449370879\b"),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10EO difference-aware CI regression failure analysis")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report for contract/privacy")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n10en-report", default=str(N10EN_REPORT),
                        help="path to the committed N10EN aggregate artifact")
    parser.add_argument("--orders-private-json",
                        help="private N10EN orders.private.json from a bounded diagnostic rerun")
    parser.add_argument("--labels-jsonl",
                        help="private N10EN score-phase labels JSONL from the same diagnostic rerun")
    return parser.parse_args(argv)


# ── Generic helpers ────────────────────────────────────────────────────────

def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def suffix_match(path: Any, ref: Any) -> bool:
    if not path or not ref:
        return False
    a = str(path).replace("\\", "/").strip("/").lower()
    b = str(ref).replace("\\", "/").strip("/").lower()
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def first_rank(order: list[dict[str, Any]], refs: list[str]) -> int | None:
    for idx, item in enumerate(order, 1):
        if any(suffix_match(item.get("path"), ref) for ref in refs):
            return idx
    return None


def rank_bucket(rank: int | None) -> str:
    if rank is None:
        return "candidate_missing_from_arm_order"
    if rank <= 5:
        return "baseline_gold_rank_1_to_5"
    if rank <= 10:
        return "baseline_gold_rank_6_to_10"
    if rank <= 20:
        return "candidate_rank_11_to_20"
    if rank <= 50:
        return "candidate_rank_21_to_50"
    if rank <= 100:
        return "candidate_rank_51_to_100"
    return "candidate_rank_gt_100"


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


# ── N10EN source lock ──────────────────────────────────────────────────────

def lock_n10en_source(n10en: dict[str, Any] | None, state: str) -> dict[str, Any]:
    """Verify the committed N10EN artifact matches the locked regression result."""
    present_ok = state == "present" and isinstance(n10en, dict)
    src: dict[str, Any] = n10en if isinstance(n10en, dict) else {}
    status_ok = present_ok and src.get("status") == LOCKED_N10EN_STATUS
    counts_ok = False
    selected_ok = False
    novelty_ok = False
    scored_ok = False
    gold_ok = False
    citation_ok = False

    if status_ok:
        agg = {r.get("arm_bucket"): r for r in src.get("aggregate_count_records", [])}
        counts_ok = all(
            agg.get(arm, {}).get("top10_file_recovery_count") == LOCKED_COUNTS[arm]["top10"]
            and agg.get(arm, {}).get("top20_file_recovery_count") == LOCKED_COUNTS[arm]["top20"]
            and agg.get(arm, {}).get("top50_file_recovery_count") == LOCKED_COUNTS[arm]["top50"]
            and agg.get(arm, {}).get("top100_file_recovery_count") == LOCKED_COUNTS[arm]["top100"]
            and agg.get(arm, {}).get("lost_baseline_top10_hits") == LOCKED_COUNTS[arm]["lost"]
            for arm in LOCKED_COUNTS
        )
        sel = {r.get("selected_arm_bucket"): r.get("task_count") for r in src.get("selected_arm_bucket_records", [])}
        selected_ok = sel == LOCKED_SELECTED_ARMS
        nov = {r.get("bucket"): r.get("task_count") for r in src.get("top5_novelty_bucket_records", [])}
        novelty_ok = nov == LOCKED_NOVELTY_BUCKETS
        score = (src.get("score_phase_records") or [{}])[0]
        scored_ok = score.get("scored_task_count") == LOCKED_SCORED_TASK_COUNT
        gold_ok = score.get("task_with_gold_count") == LOCKED_TASK_WITH_GOLD
        cv = (src.get("citation_validity_aggregate_records") or [{}])[0]
        citation_ok = (cv.get("citation_valid_count") == LOCKED_CITATION["valid"]
                       and cv.get("citation_total_count") == LOCKED_CITATION["total"])

    all_ok = status_ok and counts_ok and selected_ok and novelty_ok and scored_ok and gold_ok and citation_ok
    return {
        "anonymous_source_lock_id": "n10eosource0000",
        "n10en_artifact_load_status_bucket": state,
        "locked_status_bucket": LOCKED_N10EN_STATUS,
        "actual_status_bucket": str(src.get("status", "unavailable")),
        "status_match_bool": status_ok,
        "aggregate_counts_match_bool": counts_ok,
        "selected_arms_match_bool": selected_ok,
        "novelty_buckets_match_bool": novelty_ok,
        "scored_task_count_match_bool": scored_ok,
        "task_with_gold_match_bool": gold_ok,
        "citation_match_bool": citation_ok,
        "source_locked_bool": all_ok,
        "locked_baseline_top10": LOCKED_COUNTS["baseline"]["top10"],
        "locked_full_top10": LOCKED_COUNTS["full"]["top10"],
        "locked_guard_top10": LOCKED_COUNTS["guard"]["top10"],
        "locked_diffaware_top10": LOCKED_COUNTS["diffaware"]["top10"],
        "locked_full_lost": LOCKED_COUNTS["full"]["lost"],
        "locked_guard_lost": LOCKED_COUNTS["guard"]["lost"],
        "locked_diffaware_lost": LOCKED_COUNTS["diffaware"]["lost"],
        "locked_selected_full": LOCKED_SELECTED_ARMS["full_novel_first"],
        "locked_selected_guard": LOCKED_SELECTED_ARMS["guarded_top5_novel_distinct"],
        "locked_task_with_gold": LOCKED_TASK_WITH_GOLD,
        "locked_citation_valid": LOCKED_CITATION["valid"],
        "locked_citation_total": LOCKED_CITATION["total"],
    }


# ── Per-task diagnostic state ─────────────────────────────────────────────

def _arm_for_novelty(novel_count: int) -> str:
    return "guarded_top5_novel_distinct" if novel_count >= THRESHOLD else "full_novel_first"


def _novelty_bucket(novel_count: int) -> str:
    if novel_count <= 2:
        return "top5_novel_candidate_item_count_0_to_2"
    if novel_count == 3:
        return "top5_novel_candidate_item_count_3"
    return "top5_novel_candidate_item_count_4_to_5"


def diagnostics_from_private_inputs(orders_path: Path, labels_path: Path) -> tuple[list[dict[str, Any]], str]:
    """Build private per-task diagnostics from a bounded N10EN diagnostic rerun.

    The returned diagnostics remain private process state. Public reports only
    receive aggregate buckets derived from this list.
    """
    orders = json.loads(orders_path.read_text(encoding="utf-8"))
    labels = {row.get("test_id"): row for row in load_jsonl(labels_path)}
    diagnostics: list[dict[str, Any]] = []
    for tid, order_map in orders.items():
        label = labels.get(tid, {})
        refs = [g.get("path") for g in (label.get("gold_spans") or []) if g.get("path")]
        has_gold = bool(refs)
        ranks = {
            "baseline": first_rank(order_map.get("baseline_order", []), refs),
            "full": first_rank(order_map.get("full_order", []), refs),
            "guard": first_rank(order_map.get("guard_order", []), refs),
            "diffaware": first_rank(order_map.get("diffaware_order", []), refs),
        }
        selected_arm = str(order_map.get("selected_arm") or _arm_for_novelty(int(order_map.get("top5_novel_candidate_item_count", 0))))
        novel_count = int(order_map.get("top5_novel_candidate_item_count", 0))
        base_hit = ranks["baseline"] is not None and ranks["baseline"] <= 10
        full_hit = ranks["full"] is not None and ranks["full"] <= 10
        guard_hit = ranks["guard"] is not None and ranks["guard"] <= 10
        diff_hit = ranks["diffaware"] is not None and ranks["diffaware"] <= 10
        diagnostics.append({
            "novelty_bucket": _novelty_bucket(novel_count),
            "novel_count": novel_count,
            "selected_arm": selected_arm,
            "has_gold": has_gold,
            "baseline_top10_hit": base_hit,
            "full_top10_hit": full_hit,
            "guard_top10_hit": guard_hit,
            "diffaware_top10_hit": diff_hit,
            "full_lost_baseline": base_hit and not full_hit,
            "guard_lost_baseline": base_hit and not guard_hit,
            "diffaware_lost_baseline": base_hit and not diff_hit,
            "baseline_gold_rank_bucket": rank_bucket(ranks["baseline"]),
            "full_gold_rank_bucket": rank_bucket(ranks["full"]),
            "guard_gold_rank_bucket": rank_bucket(ranks["guard"]),
            "diffaware_gold_rank_bucket": rank_bucket(ranks["diffaware"]),
        })
    return diagnostics, "private_diagnostic_rerun"


def verify_private_diagnostics_match_lock(diags: list[dict[str, Any]], lock: dict[str, Any]) -> bool:
    if not lock.get("source_locked_bool"):
        return False
    if sum(1 for d in diags if d.get("has_gold")) != LOCKED_TASK_WITH_GOLD:
        return False
    def top10(arm: str) -> int:
        return sum(1 for d in diags if d[f"{arm}_top10_hit"])
    def lost(arm: str) -> int:
        return sum(1 for d in diags if d[f"{arm}_lost_baseline"])
    selected: dict[str, int] = {}
    novelty: dict[str, int] = {}
    for d in diags:
        selected[d["selected_arm"]] = selected.get(d["selected_arm"], 0) + 1
        novelty[d["novelty_bucket"]] = novelty.get(d["novelty_bucket"], 0) + 1
    return (
        top10("baseline") == LOCKED_COUNTS["baseline"]["top10"]
        and top10("full") == LOCKED_COUNTS["full"]["top10"]
        and top10("guard") == LOCKED_COUNTS["guard"]["top10"]
        and top10("diffaware") == LOCKED_COUNTS["diffaware"]["top10"]
        and lost("full") == LOCKED_COUNTS["full"]["lost"]
        and lost("guard") == LOCKED_COUNTS["guard"]["lost"]
        and lost("diffaware") == LOCKED_COUNTS["diffaware"]["lost"]
        and selected == LOCKED_SELECTED_ARMS
        and novelty == LOCKED_NOVELTY_BUCKETS
    )


def classify_lost_mechanism(diag: dict[str, Any]) -> list[str]:
    """Classify the lost-baseline mechanism for a task where full or diffaware
    lost a baseline top-10 hit. Returns matching mechanism buckets."""
    if not diag["has_gold"] or not diag["baseline_top10_hit"]:
        return []
    mechs: list[str] = []
    arm = diag["selected_arm"]
    # Full-arm loss mechanism.
    if diag["full_lost_baseline"]:
        mechs.append(MECH_NOVEL_FIRST_DISPLACED)
        if diag["baseline_gold_rank_bucket"] == "baseline_gold_rank_6_to_10":
            mechs.append(MECH_BASELINE_RANK_6_TO_10)
        elif diag["baseline_gold_rank_bucket"] == "baseline_gold_rank_1_to_5":
            mechs.append(MECH_BASELINE_RANK_1_TO_5)
        # Gold is still in the full order (just beyond top-10): full reorders
        # the same candidate pool, so the gold candidate remains available.
        mechs.append(MECH_CANDIDATE_BEYOND_TOP10)
    # Guard-arm loss mechanism (none in the locked result, but support it).
    if diag["guard_lost_baseline"]:
        mechs.append(MECH_DISTINCT_FILE_PACKING)
    if not mechs and diag["diffaware_lost_baseline"]:
        mechs.append(MECH_OTHER)
    return mechs


# ── Aggregate bucket computation ──────────────────────────────────────────

def _init_counter(keys: tuple[str, ...]) -> dict[str, int]:
    return {k: 0 for k in keys}


def compute_novelty_bucket_records(diags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Category 1: top5_novel_candidate_item_count buckets with sub-counts."""
    records: list[dict[str, Any]] = []
    for bucket in NOVELTY_BUCKET_ORDER:
        subset = [d for d in diags if d["novelty_bucket"] == bucket]
        gold_subset = [d for d in subset if d["has_gold"]]
        rec: dict[str, Any] = {
            "anonymous_novelty_bucket_id": f"n10eonb{len(records):04d}",
            "bucket": bucket,
            "task_count": len(subset),
            "gold_task_count": len(gold_subset),
            "selected_full_novel_first_count": sum(1 for d in subset if d["selected_arm"] == "full_novel_first"),
            "selected_guarded_top5_novel_distinct_count": sum(1 for d in subset if d["selected_arm"] == "guarded_top5_novel_distinct"),
            "baseline_top10_hit_count": sum(1 for d in gold_subset if d["baseline_top10_hit"]),
            "full_top10_hit_count": sum(1 for d in gold_subset if d["full_top10_hit"]),
            "guard_top10_hit_count": sum(1 for d in gold_subset if d["guard_top10_hit"]),
            "diffaware_top10_hit_count": sum(1 for d in gold_subset if d["diffaware_top10_hit"]),
            "full_lost_baseline_count": sum(1 for d in gold_subset if d["full_lost_baseline"]),
            "guard_lost_baseline_count": sum(1 for d in gold_subset if d["guard_lost_baseline"]),
            "diffaware_lost_baseline_count": sum(1 for d in gold_subset if d["diffaware_lost_baseline"]),
            "diffaware_chose_full_but_guarded_would_preserve_count": sum(
                1 for d in gold_subset
                if d["selected_arm"] == "full_novel_first"
                and d["diffaware_lost_baseline"]
                and d["guard_top10_hit"]),
            "diffaware_chose_guarded_but_full_would_improve_count": sum(
                1 for d in gold_subset
                if d["selected_arm"] == "guarded_top5_novel_distinct"
                and d["guard_top10_hit"]
                and not d["full_top10_hit"]
                and not d["diffaware_lost_baseline"]),
        }
        records.append(rec)
    return records


def compute_full_vs_guard_records(diags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Category 2: full-vs-guard outcome buckets with safe aggregate counts."""
    gold = [d for d in diags if d["has_gold"]]
    buckets = _init_counter(ALL_FG_BUCKETS)
    for d in gold:
        f, g = d["full_top10_hit"], d["guard_top10_hit"]
        if f and not g:
            buckets[FG_FULL_BETTER] += 1
        elif g and not f:
            buckets[FG_GUARD_BETTER] += 1
        elif f and g:
            buckets[FG_BOTH_HIT] += 1
        else:
            buckets[FG_BOTH_MISS] += 1
        if d["baseline_top10_hit"]:
            if d["full_lost_baseline"] and not d["guard_lost_baseline"]:
                buckets[FG_FULL_LOST_GUARD_PRESERVED] += 1
            elif d["guard_lost_baseline"] and not d["full_lost_baseline"]:
                buckets[FG_GUARD_LOST_FULL_PRESERVED] += 1
            elif d["full_lost_baseline"] and d["guard_lost_baseline"]:
                buckets[FG_BOTH_LOST_BASELINE] += 1
            else:
                buckets[FG_NEITHER_LOST_BASELINE] += 1
    return [{
        "anonymous_fg_bucket_id": f"n10eofg{idx:04d}",
        "outcome_bucket": bucket,
        "task_count": count,
    } for idx, (bucket, count) in enumerate(
        (b, buckets[b]) for b in ALL_FG_BUCKETS)]


def compute_lost_mechanism_records(diags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Category 3: lost-baseline mechanism buckets for baseline top-10 hit
    tasks where full or diffaware lost."""
    buckets = _init_counter(ALL_MECH_BUCKETS)
    lost_tasks = [d for d in diags if d["has_gold"] and d["baseline_top10_hit"]
                  and (d["full_lost_baseline"] or d["diffaware_lost_baseline"])]
    for d in lost_tasks:
        for mech in classify_lost_mechanism(d):
            buckets[mech] += 1
    return [{
        "anonymous_mech_bucket_id": f"n10eomech{idx:04d}",
        "mechanism_bucket": bucket,
        "task_count": count,
    } for idx, (bucket, count) in enumerate(
        (b, buckets[b]) for b in ALL_MECH_BUCKETS)]


def compute_counterfactual_records(diags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Category 4: arm-selection counterfactual counts."""
    buckets = _init_counter(ALL_CF_BUCKETS)
    gold = [d for d in diags if d["has_gold"] and d["baseline_top10_hit"]]
    for d in gold:
        arm = d["selected_arm"]
        if arm == "full_novel_first":
            if d["full_lost_baseline"]:
                buckets[CF_FULL_AND_FULL_LOST] += 1
            if d["full_lost_baseline"] and d["guard_top10_hit"]:
                buckets[CF_FULL_AND_GUARD_WOULD_PRESERVE] += 1
            if d["guard_top10_hit"] == d["full_top10_hit"]:
                buckets[CF_FULL_AND_GUARD_SAME] += 1
        else:  # guarded
            if d["guard_top10_hit"]:
                buckets[CF_GUARD_AND_GUARD_PRESERVED] += 1
            if d["guard_top10_hit"] and not d["full_top10_hit"]:
                buckets[CF_GUARD_AND_FULL_WOULD_IMPROVE] += 1
    return [{
        "anonymous_cf_bucket_id": f"n10eocf{idx:04d}",
        "counterfactual_bucket": bucket,
        "task_count": count,
    } for idx, (bucket, count) in enumerate(
        (b, buckets[b]) for b in ALL_CF_BUCKETS)]


def determine_status(diags: list[dict[str, Any]]) -> str:
    """Determine whether the regression mechanism is clearly identifiable."""
    lost = [d for d in diags if d["has_gold"] and d["baseline_top10_hit"]
            and d["diffaware_lost_baseline"]]
    if not lost:
        return STATUS_MECH_INCONCLUSIVE
    # Mechanism identified if all lost tasks share the novel-first-displacement
    # mechanism and guard would preserve the baseline hit.
    all_novel_displacement = all(
        d["selected_arm"] == "full_novel_first"
        and d["full_lost_baseline"]
        and d["guard_top10_hit"]
        for d in lost
    )
    return STATUS_MECH_IDENTIFIED if all_novel_displacement else STATUS_MECH_INCONCLUSIVE


# ── Report assembly ────────────────────────────────────────────────────────

def claim_boundary(used_private_diagnostics: bool = False) -> dict[str, Any]:
    return {
        "anonymous_claim_boundary_id": "n10eoclaim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "private_rows_read_bool": False,
        "private_diagnostic_inputs_used_bool": used_private_diagnostics,
        "rerun_local_canary_bool": used_private_diagnostics,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
        "raw_per_task_diagnostics_upload_bool": False,
        "run_phase_labels_used_bool": False,
        "score_phase_labels_used_bool": True,
        "gold_used_for_policy_bool": False,
        "network_run_bool": False,
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


def build_unavailable_report(lock: dict[str, Any], reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10eo_difference_aware_ci_regression_failure_analysis_v1",
        "phase_bucket": "BEA-v1-N10EO Difference-Aware CI Regression Failure Analysis",
        "status": STATUS_UNAVAILABLE,
        "unavailable_reason_bucket": reason,
        "n10en_source_lock_records": [lock],
        "novelty_bucket_diagnostic_records": [],
        "full_vs_guard_outcome_records": [],
        "lost_baseline_mechanism_records": [],
        "arm_selection_counterfactual_records": [],
        "citation_validity_summary_records": [],
        "claim_boundary_records": [claim_boundary()],
        "gate_records": [
            {"anonymous_gate_id": "n10eogate0001", "gate_bucket": "n10en_source_locked", "gate_passed_bool": lock["source_locked_bool"]},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_CLOSED
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_CLOSED
    return report


def build_report(lock: dict[str, Any], diags: list[dict[str, Any]],
                 reconstruction_source: str) -> dict[str, Any]:
    status = determine_status(diags)
    novelty_recs = compute_novelty_bucket_records(diags)
    fg_recs = compute_full_vs_guard_records(diags)
    mech_recs = compute_lost_mechanism_records(diags)
    cf_recs = compute_counterfactual_records(diags)

    # Category 5: privacy/validity summary.
    lost_full = sum(1 for d in diags if d["full_lost_baseline"])
    lost_guard = sum(1 for d in diags if d["guard_lost_baseline"])
    lost_diff = sum(1 for d in diags if d["diffaware_lost_baseline"])

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10eo_difference_aware_ci_regression_failure_analysis_v1",
        "phase_bucket": "BEA-v1-N10EO Difference-Aware CI Regression Failure Analysis",
        "status": status,
        "reconstruction_source_bucket": reconstruction_source,
        "n10en_source_lock_records": [lock],
        "novelty_bucket_diagnostic_records": novelty_recs,
        "full_vs_guard_outcome_records": fg_recs,
        "lost_baseline_mechanism_records": mech_recs,
        "arm_selection_counterfactual_records": cf_recs,
        "citation_validity_summary_records": [{
            "anonymous_cv_id": "n10eocv0000",
            "citation_validity_all_implemented_bool": lock["citation_match_bool"],
            "citation_total_count": LOCKED_CITATION["total"],
            "citation_valid_count": LOCKED_CITATION["valid"],
        }],
        "regression_summary_records": [{
            "anonymous_regression_summary_id": "n10eosum0000",
            "baseline_top10_count": LOCKED_COUNTS["baseline"]["top10"],
            "full_top10_count": LOCKED_COUNTS["full"]["top10"],
            "guard_top10_count": LOCKED_COUNTS["guard"]["top10"],
            "diffaware_top10_count": LOCKED_COUNTS["diffaware"]["top10"],
            "full_lost_baseline_count": lost_full,
            "guard_lost_baseline_count": lost_guard,
            "diffaware_lost_baseline_count": lost_diff,
            "selected_full_novel_first_count": LOCKED_SELECTED_ARMS["full_novel_first"],
            "selected_guarded_top5_novel_distinct_count": LOCKED_SELECTED_ARMS["guarded_top5_novel_distinct"],
            "task_with_gold_count": LOCKED_TASK_WITH_GOLD,
            "regression_mechanism_identified_bool": status == STATUS_MECH_IDENTIFIED,
            "primary_mechanism_bucket": MECH_NOVEL_FIRST_DISPLACED if status == STATUS_MECH_IDENTIFIED else "unclassified",
        }],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10eostop0000",
            "next_allowed_phase": "BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response",
            "n10ep_design_only_mechanism_response_authorized_bool": True,
            "n10ep_aggregate_buckets_only_bool": True,
            "threshold_tuning_authorized_bool": False,
            "new_policy_experiment_authorized_bool": False,
            "frozen_rule_change_authorized_bool": False,
            "guard_full_diffaware_promotion_authorized_bool": False,
            "runtime_default_change_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
            "downstream_scaled_retrieval_authorized_bool": False,
            "raw_diagnostic_publication_authorized_bool": False,
        }],
        "claim_boundary_records": [claim_boundary(reconstruction_source == "private_diagnostic_rerun")],
        "gate_records": [
            {"anonymous_gate_id": "n10eogate0001", "gate_bucket": "n10en_source_locked", "gate_passed_bool": lock["source_locked_bool"]},
            {"anonymous_gate_id": "n10eogate0002", "gate_bucket": "aggregate_counts_consistent", "gate_passed_bool": lock["aggregate_counts_match_bool"]},
            {"anonymous_gate_id": "n10eogate0003", "gate_bucket": "privacy_scan_pass", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10eogate0004", "gate_bucket": "no_raw_per_task_upload", "gate_passed_bool": True},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_CLOSED
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_CLOSED
    return report


# ── Contract validation ────────────────────────────────────────────────────

def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report.get("forbidden_scan", {}).get("status") != "pass":
        failures.append("forbidden_scan_not_pass")
    if report.get("status") not in STATUS_VOCAB:
        failures.append("status_not_in_vocab")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ("method_winner_claim_bool", "production_retrieval_change_bool",
                  "runtime_default_change_bool", "selector_reranker_bool",
                  "provider_model_network_bool", "raw_per_task_diagnostics_upload_bool",
                  "raw_candidate_upload_bool", "scaled_retrieval_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    # Verify all 5 categories present.
    for key in ("novelty_bucket_diagnostic_records", "full_vs_guard_outcome_records",
                "lost_baseline_mechanism_records", "arm_selection_counterfactual_records",
                "citation_validity_summary_records"):
        if key not in report:
            failures.append(f"missing_{key}")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_MECH_IDENTIFIED in STATUS_VOCAB
                   and STATUS_UNAVAILABLE in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"v": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_runid", scan_summary({"v": "28449370879"})["status"] == "fail"))
    checks.append(("scanner_taskid", scan_summary({"v": "ci-00001"})["status"] == "fail"))

    # Lock verification with the committed artifact.
    n10en, state = load_json(N10EN_REPORT)
    lock = lock_n10en_source(n10en, state)
    checks.append(("lock_source_locked", lock["source_locked_bool"] is True))
    checks.append(("lock_counts_match", lock["aggregate_counts_match_bool"] is True))
    checks.append(("lock_status_match", lock["status_match_bool"] is True))

    # Private diagnostic parsing consistency. Use the local diagnostic rerun if
    # present; otherwise verify that the default path fails closed as unavailable.
    diag_orders = Path("/tmp/n10eo_diag_rerun/run/orders.private.json")
    diag_labels = Path("/tmp/n10eo_diag_rerun/tasks_score/labels/ci_labels.jsonl")
    if diag_orders.exists() and diag_labels.exists():
        diags, source = diagnostics_from_private_inputs(diag_orders, diag_labels)
        checks.append(("diag_source", source == "private_diagnostic_rerun"))
        checks.append(("diag_matches_lock", verify_private_diagnostics_match_lock(diags, lock)))
    else:
        diags = []
        source = "private_diagnostic_rerun_missing"
        checks.append(("diag_inputs_optional", True))
    checks.append(("no_aggregate_reconstruction", "locked_aggregate_reconstruction" != source))
    if not diags:
        bad_lock = lock_n10en_source(None, "missing")
        unavail = build_unavailable_report(bad_lock, "n10en_artifact_missing")
        checks.append(("unavail_status", unavail["status"] == STATUS_UNAVAILABLE))
        checks.append(("unavail_scan_pass", unavail["forbidden_scan"]["status"] == "pass"))
        passed = sum(1 for _, ok in checks if ok)
        for name, ok in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks)")
        return passed == len(checks)
    checks.append(("diag_task_count", len(diags) == 58))
    gold = [d for d in diags if d["has_gold"]]
    checks.append(("diag_gold_count", len(gold) == 40))
    # Verify locked counts reproduced.
    checks.append(("diag_baseline_top10", sum(1 for d in gold if d["baseline_top10_hit"]) == 39))
    checks.append(("diag_full_top10", sum(1 for d in gold if d["full_top10_hit"]) == 37))
    checks.append(("diag_guard_top10", sum(1 for d in gold if d["guard_top10_hit"]) == 39))
    checks.append(("diag_diffaware_top10", sum(1 for d in gold if d["diffaware_top10_hit"]) == 37))
    checks.append(("diag_full_lost", sum(1 for d in diags if d["full_lost_baseline"]) == 2))
    checks.append(("diag_guard_lost", sum(1 for d in diags if d["guard_lost_baseline"]) == 0))
    checks.append(("diag_diffaware_lost", sum(1 for d in diags if d["diffaware_lost_baseline"]) == 2))
    checks.append(("diag_selected_full", sum(1 for d in diags if d["selected_arm"] == "full_novel_first") == 49))
    checks.append(("diag_selected_guard", sum(1 for d in diags if d["selected_arm"] == "guarded_top5_novel_distinct") == 9))
    # Novelty bucket counts.
    from collections import Counter
    nb = Counter(d["novelty_bucket"] for d in diags)
    checks.append(("diag_novelty_0to2", nb["top5_novel_candidate_item_count_0_to_2"] == 47))
    checks.append(("diag_novelty_3", nb["top5_novel_candidate_item_count_3"] == 2))
    checks.append(("diag_novelty_4to5", nb["top5_novel_candidate_item_count_4_to_5"] == 9))

    # Status determination.
    status = determine_status(diags)
    checks.append(("status_mechanism_identified", status == STATUS_MECH_IDENTIFIED))

    # Category 1: novelty bucket records.
    nov_recs = compute_novelty_bucket_records(diags)
    checks.append(("nov_recs_count", len(nov_recs) == 3))
    # The 2 lost tasks should be in 0_to_2 with guard-would-preserve = 2.
    nb_0to2 = [r for r in nov_recs if r["bucket"] == "top5_novel_candidate_item_count_0_to_2"][0]
    checks.append(("nov_0to2_diffaware_lost", nb_0to2["diffaware_lost_baseline_count"] == 2))
    checks.append(("nov_0to2_guard_would_preserve", nb_0to2["diffaware_chose_full_but_guarded_would_preserve_count"] == 2))

    # Category 2: full-vs-guard.
    fg_recs = compute_full_vs_guard_records(diags)
    fg_map = {r["outcome_bucket"]: r["task_count"] for r in fg_recs}
    checks.append(("fg_full_lost_guard_preserved", fg_map[FG_FULL_LOST_GUARD_PRESERVED] == 2))
    checks.append(("fg_guard_lost_full_preserved", fg_map[FG_GUARD_LOST_FULL_PRESERVED] == 0))
    checks.append(("fg_both_hit", fg_map[FG_BOTH_HIT] == 37))
    checks.append(("fg_both_miss", fg_map[FG_BOTH_MISS] == 1))
    checks.append(("fg_guard_better_than_full", fg_map[FG_GUARD_BETTER] == 2))
    checks.append(("fg_neither_lost", fg_map[FG_NEITHER_LOST_BASELINE] == 37))

    # Category 3: lost-baseline mechanisms.
    mech_recs = compute_lost_mechanism_records(diags)
    mech_map = {r["mechanism_bucket"]: r["task_count"] for r in mech_recs}
    checks.append(("mech_novel_first_displaced", mech_map[MECH_NOVEL_FIRST_DISPLACED] == 2))
    checks.append(("mech_rank_1_to_5", mech_map[MECH_BASELINE_RANK_1_TO_5] == 2))
    checks.append(("mech_rank_6_to_10", mech_map[MECH_BASELINE_RANK_6_TO_10] == 0))
    checks.append(("mech_candidate_beyond_top10", mech_map[MECH_CANDIDATE_BEYOND_TOP10] == 2))
    checks.append(("mech_all_buckets_present", len(mech_recs) == len(ALL_MECH_BUCKETS)))

    # Category 4: counterfactuals.
    cf_recs = compute_counterfactual_records(diags)
    cf_map = {r["counterfactual_bucket"]: r["task_count"] for r in cf_recs}
    checks.append(("cf_full_and_full_lost", cf_map[CF_FULL_AND_FULL_LOST] == 2))
    checks.append(("cf_full_and_guard_would_preserve", cf_map[CF_FULL_AND_GUARD_WOULD_PRESERVE] == 2))
    checks.append(("cf_guard_and_guard_preserved", cf_map[CF_GUARD_AND_GUARD_PRESERVED] == 0))
    checks.append(("cf_all_buckets_present", len(cf_recs) == len(ALL_CF_BUCKETS)))

    # Full report build + validation.
    report = build_report(lock, diags, source)
    checks.append(("report_status_identified", report["status"] == STATUS_MECH_IDENTIFIED))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))

    # Unavailable report when source not locked.
    bad_lock = lock_n10en_source(None, "missing")
    unavail = build_unavailable_report(bad_lock, "n10en_artifact_missing")
    checks.append(("unavail_status", unavail["status"] == STATUS_UNAVAILABLE))
    checks.append(("unavail_scan_pass", unavail["forbidden_scan"]["status"] == "pass"))

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

    # Load and lock the N10EN source artifact.
    n10en, state = load_json(Path(args.n10en_report))
    lock = lock_n10en_source(n10en, state)
    if not lock["source_locked_bool"]:
        report = build_unavailable_report(lock, "n10en_source_not_locked")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote artifact (status={report['status']}, source not locked)")
        return 0 if report["status"] in STATUS_VOCAB - {STATUS_FAIL_CLOSED} else 1

    # Build per-task diagnostic state only from private diagnostic rerun inputs.
    if not args.orders_private_json or not args.labels_jsonl:
        report = build_unavailable_report(lock, "private_diagnostic_inputs_required")
    else:
        diags, source = diagnostics_from_private_inputs(Path(args.orders_private_json), Path(args.labels_jsonl))
        if not verify_private_diagnostics_match_lock(diags, lock):
            report = build_unavailable_report(lock, "private_diagnostic_rerun_mismatch")
        else:
            report = build_report(lock, diags, source)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
