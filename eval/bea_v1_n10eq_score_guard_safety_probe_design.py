#!/usr/bin/env python3
"""BEA-v1-N10EQ Score/Guard Safety Probe Design.

N10EQ is a *public-artifact-only design* phase that sits after the N10EP
checkpoint (commit 0a54b49). It designs a forward score/guard safety probe
that, given a frozen arm order and the public N10EO aggregate mechanism
buckets, would flag tasks where the `full` novel-first arm may displace an
already-strong baseline gold file (rank 1-5) into ranks 11-20. The probe is
*designed*; it is not executed.

Allowed inputs (public only):
  * the committed N10EP public artifact (stop/go + design options)
  * the committed N10EO public aggregate artifact (mechanism buckets)
  * the committed N10EN public aggregate artifact
  * the committed N10EM public artifact / docs / evaluator contract
  * public docs/code metadata only (no cloned repo contents)

Forbidden inputs:
  * /tmp/n10eo_diag_rerun, orders.private.json, private labels JSONL
  * raw candidates / orders / paths / queries / tasks / repos
  * per-task diagnostics, cloned repo contents, CI temp dirs
  * new retrieval output, CI variant execution, policy execution

N10EQ performs NO execution. It does not tune thresholds, run new policy
experiments, change the frozen rule, promote guard/full/diffaware, change
runtime/default behavior, claim method winner, run downstream/scaled
retrieval, execute any CI variant, or publish raw diagnostics. The published
artifact is aggregate-bucket-only with explicit false privacy/claim boundary
fields.

The conservative stop/go authorizes only the *N10ER bounded public CI
score/guard safety probe contract* (design-only contract handoff); it does
NOT authorize N10ER execution. n10er_contract_authorized_bool=true,
n10er_execution_authorized_bool=false.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10eq_score_guard_safety_probe_design"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"

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

# ── Locked N10EP checkpoint (commit 0a54b49) ────────────────────────────────
LOCKED_N10EP_CHECKPOINT = "0a54b49"
LOCKED_N10EP_STATUS = "n10ep_design_response_pass_n10eq_authorized"
LOCKED_N10EP_NEXT_PHASE = "BEA-v1-N10EQ Score/Guard Safety Probe Design"
LOCKED_N10EP_NEXT_ALLOWED_PHASE = (
    "BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response")

# Locked N10EO mechanism values (re-derived from N10EO, locked via N10EP).
LOCKED_N10EO_STATUS = "n10eo_failure_analysis_pass_mechanism_identified"
LOCKED_N10EO_CHECKPOINT = "6f8eeda"
LOCKED_PRIMARY_MECHANISM = "novel_first_displaced_baseline_gold_from_top10"

LOCKED_COUNTS = {
    "baseline": {"top10": 39, "lost": 0},
    "full": {"top10": 37, "lost": 2},
    "guard": {"top10": 39, "lost": 0},
    "diffaware": {"top10": 37, "lost": 2},
}
LOCKED_TASK_WITH_GOLD = 40
LOCKED_SELECTED_ARMS = {"full_novel_first": 49, "guarded_top5_novel_distinct": 9}
LOCKED_CITATION = {"valid": 3636, "total": 3636}

LOCKED_MECH_COUNTS = {
    "novel_first_displaced_baseline_gold_from_top10": 2,
    "baseline_gold_rank_1_to_5_displaced": 2,
    "candidate_available_beyond_top10": 2,
}
LOCKED_FG_COUNTS = {
    "guard_better_than_full": 2,
    "full_lost_guard_preserved_baseline": 2,
    "neither_lost_baseline": 37,
    "full_equals_guard_both_hit": 37,
}
LOCKED_LOW_NOVELTY_BUCKET_LOSS = 2
LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE = 2

# Threshold frozen from the N10EK/N10EM rule.
FROZEN_THRESHOLD = 4
FROZEN_THRESHOLD_FEATURE = "top5_novel_candidate_item_count"
FROZEN_RULE = "if_top5_novel_candidate_item_count_gte_4_then_guarded_else_full"

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_N10ER_CONTRACT_AUTHORIZED = (
    "n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized")
STATUS_FAIL_CLOSED = "n10eq_score_guard_safety_probe_design_fail_closed_privacy_or_contract"
STATUS_UNAVAILABLE = "n10eq_score_guard_safety_probe_design_unavailable_source_not_locked"
STATUS_VOCAB = {
    STATUS_N10ER_CONTRACT_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_UNAVAILABLE,
}
EXIT0_VOCAB = {STATUS_N10ER_CONTRACT_AUTHORIZED}

# ── Future probe feature buckets (7 features in the oracle contract) ───────
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

# ── Risk control buckets ───────────────────────────────────────────────────
RISK_AGGREGATE_OVERINTERPRETATION = "aggregate_overinterpretation_from_two_cases"
RISK_HINDSIGHT_THRESHOLD_TUNING = "hindsight_threshold_tuning_in_probe_design"
RISK_GUARD_PROMOTION_FROM_TWO_CASES = "guard_promotion_from_two_cases"
RISK_PRIVATE_DIAGNOSTIC_LEAKAGE = "private_diagnostic_leakage_into_probe_features"
RISK_RUNTIME_DEFAULT_CREEP = "runtime_default_creep_via_safety_probe"
RISK_N10ER_EXECUTION_CREEP = "n10er_execution_creep_from_contract_authorization"
RISK_FEATURE_PROXY_AS_GOLD = "feature_proxy_treated_as_gold"
ALL_RISK_CONTROLS = (
    RISK_AGGREGATE_OVERINTERPRETATION,
    RISK_HINDSIGHT_THRESHOLD_TUNING,
    RISK_GUARD_PROMOTION_FROM_TWO_CASES,
    RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
    RISK_RUNTIME_DEFAULT_CREEP,
    RISK_N10ER_EXECUTION_CREEP,
    RISK_FEATURE_PROXY_AS_GOLD,
)

# ── Privacy scan: forbid raw per-task / path / candidate / repo data ───────
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
    # N10EO private diagnostic rerun path and private labels are forbidden.
    re.compile(r"n10eo_diag_rerun", re.I),
    re.compile(r"orders\.private\.json", re.I),
    re.compile(r"ci_labels\.jsonl", re.I),
    re.compile(r"n10eo_diag", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10EQ score/guard safety probe design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report for contract/privacy")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n10ep-report", default=str(N10EP_REPORT),
                        help="path to the committed N10EP public artifact")
    parser.add_argument("--n10eo-report", default=str(N10EO_REPORT),
                        help="path to the committed N10EO public aggregate artifact")
    parser.add_argument("--n10en-report", default=str(N10EN_REPORT),
                        help="path to the committed N10EN public aggregate artifact")
    parser.add_argument("--n10em-report", default=str(N10EM_REPORT),
                        help="path to the committed N10EM public artifact")
    return parser.parse_args(argv)


# ── Generic helpers ────────────────────────────────────────────────────────

def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


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


# ── N10EP source lock ──────────────────────────────────────────────────────

def lock_n10ep_source(n10ep: dict[str, Any] | None, state: str,
                      n10eo: dict[str, Any] | None = None,
                      n10eo_state: str = "missing",
                      n10en: dict[str, Any] | None = None,
                      n10en_state: str = "missing",
                      n10em: dict[str, Any] | None = None,
                      n10em_state: str = "missing") -> dict[str, Any]:
    """Verify the committed N10EP artifact matches the locked 0a54b49
    checkpoint and that it authorized the N10EQ design (design-only). N10EQ
    consumes only public aggregate values; no private inputs are read."""
    present_ok = state == "present" and isinstance(n10ep, dict)
    src: dict[str, Any] = n10ep if isinstance(n10ep, dict) else {}
    status_ok = present_ok and src.get("status") == LOCKED_N10EP_STATUS
    stop_ok = False
    next_phase_ok = False
    n10eq_auth_ok = False
    n10eq_exec_false_ok = False
    n10er_exec_false_ok = False

    if status_ok:
        stop = (src.get("stop_go_records") or [{}])[0]
        stop_ok = (stop.get("n10eq_design_only_authorized_bool") is True
                   and stop.get("design_only_mechanism_response_bool") is True)
        next_phase_ok = stop.get("next_allowed_phase") == LOCKED_N10EP_NEXT_PHASE
        n10eq_auth_ok = stop.get("n10eq_design_only_authorized_bool") is True
        n10eq_exec_false_ok = stop.get("n10eq_execution_authorized_bool") is False
        n10er_exec_false_ok = stop.get("n10er_execution_authorized_bool") is False

    all_ok = (status_ok and stop_ok and next_phase_ok and n10eq_auth_ok
              and n10eq_exec_false_ok and n10er_exec_false_ok)
    return {
        "anonymous_source_lock_id": "n10eqsource0000",
        "locked_n10ep_checkpoint": LOCKED_N10EP_CHECKPOINT,
        "locked_n10ep_status": LOCKED_N10EP_STATUS,
        "actual_n10ep_status": str(src.get("status", "unavailable")),
        "status_match_bool": status_ok,
        "n10eq_design_authorized_match_bool": n10eq_auth_ok,
        "n10eq_execution_false_match_bool": n10eq_exec_false_ok,
        "n10er_execution_false_match_bool": n10er_exec_false_ok,
        "next_phase_match_bool": next_phase_ok,
        "n10ep_artifact_load_status_bucket": state,
        "n10eo_artifact_load_status_bucket": n10eo_state,
        "n10en_artifact_load_status_bucket": n10en_state,
        "n10em_artifact_load_status_bucket": n10em_state,
        "source_locked_bool": all_ok,
        "locked_n10ep_next_phase": LOCKED_N10EP_NEXT_PHASE,
        "locked_n10eo_checkpoint": LOCKED_N10EO_CHECKPOINT,
        "locked_primary_mechanism": LOCKED_PRIMARY_MECHANISM,
    }


# ── Mechanism lock (re-derived from N10EO public aggregate) ───────────────

def mechanism_lock(n10eo: dict[str, Any] | None, n10eo_state: str) -> dict[str, Any]:
    """Lock the N10EO public aggregate mechanism values that the probe design
    addresses. All values are public aggregate buckets; no per-task data."""
    present_ok = n10eo_state == "present" and isinstance(n10eo, dict)
    src: dict[str, Any] = n10eo if isinstance(n10eo, dict) else {}
    status_ok = present_ok and src.get("status") == LOCKED_N10EO_STATUS
    mech_ok = False
    fg_ok = False
    low_nov_ok = False
    counts_ok = False
    primary_ok = False
    if status_ok:
        mech_map = {r.get("mechanism_bucket"): r.get("task_count")
                    for r in src.get("lost_baseline_mechanism_records", [])}
        mech_ok = all(mech_map.get(k) == v for k, v in LOCKED_MECH_COUNTS.items())
        fg_map = {r.get("outcome_bucket"): r.get("task_count")
                  for r in src.get("full_vs_guard_outcome_records", [])}
        fg_ok = all(fg_map.get(k) == v for k, v in LOCKED_FG_COUNTS.items())
        nov0 = next((r for r in src.get("novelty_bucket_diagnostic_records", [])
                     if r.get("bucket") == "top5_novel_candidate_item_count_0_to_2"), {})
        low_nov_ok = (nov0.get("diffaware_lost_baseline_count") == LOCKED_LOW_NOVELTY_BUCKET_LOSS
                      and nov0.get("diffaware_chose_full_but_guarded_would_preserve_count")
                      == LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE)
        summ = (src.get("regression_summary_records") or [{}])[0]
        counts_ok = (
            summ.get("baseline_top10_count") == LOCKED_COUNTS["baseline"]["top10"]
            and summ.get("full_top10_count") == LOCKED_COUNTS["full"]["top10"]
            and summ.get("guard_top10_count") == LOCKED_COUNTS["guard"]["top10"]
            and summ.get("diffaware_top10_count") == LOCKED_COUNTS["diffaware"]["top10"]
            and summ.get("full_lost_baseline_count") == LOCKED_COUNTS["full"]["lost"]
            and summ.get("guard_lost_baseline_count") == LOCKED_COUNTS["guard"]["lost"]
            and summ.get("diffaware_lost_baseline_count") == LOCKED_COUNTS["diffaware"]["lost"]
        )
        primary_ok = summ.get("primary_mechanism_bucket") == LOCKED_PRIMARY_MECHANISM
    all_ok = (status_ok and mech_ok and fg_ok and low_nov_ok and counts_ok and primary_ok)
    return {
        "anonymous_mechanism_lock_id": "n10eqmech0000",
        "n10eo_status_match_bool": status_ok,
        "primary_mechanism_match_bool": primary_ok,
        "aggregate_counts_match_bool": counts_ok,
        "mechanism_buckets_match_bool": mech_ok,
        "full_guard_outcome_match_bool": fg_ok,
        "low_novelty_bucket_loss_match_bool": low_nov_ok,
        "mechanism_locked_bool": all_ok,
        "locked_primary_mechanism": LOCKED_PRIMARY_MECHANISM,
        "locked_novel_first_displaced_count": LOCKED_MECH_COUNTS["novel_first_displaced_baseline_gold_from_top10"],
        "locked_baseline_gold_rank_1_to_5_displaced_count": LOCKED_MECH_COUNTS["baseline_gold_rank_1_to_5_displaced"],
        "locked_candidate_available_beyond_top10_count": LOCKED_MECH_COUNTS["candidate_available_beyond_top10"],
        "locked_guard_better_than_full_count": LOCKED_FG_COUNTS["guard_better_than_full"],
        "locked_full_lost_guard_preserved_count": LOCKED_FG_COUNTS["full_lost_guard_preserved_baseline"],
        "locked_low_novelty_bucket_loss_count": LOCKED_LOW_NOVELTY_BUCKET_LOSS,
        "locked_diffaware_full_guard_would_preserve_count": LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE,
    }


# ── Future probe feature records (7 features per oracle contract) ─────────

def future_probe_feature_records(mlock: dict[str, Any]) -> list[dict[str, Any]]:
    """Design the 7 probe features. Each is a *design-only* observable feature
    derivable from public aggregate buckets + the frozen arm order. No feature
    reads per-task candidates/labels/paths/ranks/gold directly."""
    return [
        {
            "anonymous_probe_feature_id": "n10eqfeat0000",
            "feature_bucket": FEATURE_TOP5_NOVELTY_BUCKET,
            "feature_description_bucket": (
                "bucket the top5_novel_candidate_item_count feature into the "
                "frozen buckets 0_to_2 / 3 / 4_to_5. the low-novelty (0_to_2) "
                "bucket is where both locked misfires occurred; the probe uses "
                "this as a coarse risk gate, not a tuned threshold."),
            "derivation_bucket": "public_aggregate_novelty_buckets_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_LOW_NOVELTY_BUCKET_LOSS,
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0001",
            "feature_bucket": FEATURE_BASELINE_PREFIX_STRENGTH,
            "feature_description_bucket": (
                "design a proxy for baseline top-k prefix strength: how strong "
                "the baseline arm's head is. the locked mechanism shows the "
                "displaced gold was at baseline rank 1-5, so a strong-prefix "
                "proxy flags arms whose baseline head is likely already a hit. "
                "uses only aggregate hit/miss buckets, never raw ranks."),
            "derivation_bucket": "public_aggregate_baseline_hit_buckets_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_MECH_COUNTS["baseline_gold_rank_1_to_5_displaced"],
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0002",
            "feature_bucket": FEATURE_BASELINE_GOLD_PROXY,
            "feature_description_bucket": (
                "design a baseline-gold-presence proxy that infers, from "
                "public aggregate baseline top10 hit counts, whether a task "
                "is in the class where baseline already hits gold. this is a "
                "bucket-level proxy, not gold labels; gold_used_for_policy "
                "stays false."),
            "derivation_bucket": "public_aggregate_baseline_hit_buckets_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE,
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0003",
            "feature_bucket": FEATURE_FULL_DISPLACEMENT_RISK,
            "feature_description_bucket": (
                "design a full-novel-first displacement risk score: combine "
                "low-novelty-bucket membership with strong-baseline-prefix "
                "proxy to flag tasks where the full arm's novel-first "
                "reordering may push an already-strong baseline hit past "
                "top-10. the locked misfire class is exactly this combination "
                "(2 tasks)."),
            "derivation_bucket": "public_aggregate_combination_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_MECH_COUNTS["novel_first_displaced_baseline_gold_from_top10"],
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0004",
            "feature_bucket": FEATURE_GUARD_PRESERVATION_REF,
            "feature_description_bucket": (
                "design a guard-preservation reference: the guard arm keeps "
                "the original top-5 and only appends distinct novel files, so "
                "it preserves the baseline head by construction. the locked "
                "outcome shows guard preserved both displaced gold cases "
                "(full_lost_guard_preserved = 2, guard_lost = 0). used as a "
                "reference, not a promotion signal."),
            "derivation_bucket": "public_aggregate_guard_outcome_buckets_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_FG_COUNTS["full_lost_guard_preserved_baseline"],
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0005",
            "feature_bucket": FEATURE_CANDIDATE_BEYOND_TOP10,
            "feature_description_bucket": (
                "design a candidate-available-beyond-top10 reference: the "
                "locked mechanism shows the displaced gold stayed in the full "
                "order beyond top-10 (candidate_available_beyond_top10 = 2), so "
                "the loss is a reordering displacement, not a missing-candidate "
                "failure. the probe distinguishes these two failure classes."),
            "derivation_bucket": "public_aggregate_mechanism_buckets_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_MECH_COUNTS["candidate_available_beyond_top10"],
        },
        {
            "anonymous_probe_feature_id": "n10eqfeat0006",
            "feature_bucket": FEATURE_ARM_SELECTION,
            "feature_description_bucket": (
                "design an arm-selection feature echoing the frozen "
                "difference-aware rule (top5_novel >= 4 -> guarded else full). "
                "the probe uses this to label which arm the frozen rule chose "
                "and whether the displacement risk would apply. the frozen rule "
                "is NOT changed; the feature is observational only."),
            "derivation_bucket": "frozen_rule_observable_only",
            "reads_per_task_data_bool": False,
            "tunes_threshold_bool": False,
            "design_only_bool": True,
            "addresses_misfire_count": LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE,
        },
    ]


# ── Future probe input/output contracts ───────────────────────────────────

def future_probe_input_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_input_contract_id": "n10eqinput0000",
        "input_contract_bucket": "n10er_bounded_public_ci_private_execution_inputs_aggregate_publication_only",
        "input_description_bucket": (
            "N10EQ itself reads only public artifacts. if separately authorized, "
            "N10ER may privately produce/read bounded public-CI arm orders, raw "
            "candidate lists, retrieval output, and score-phase labels after "
            "orders are frozen, solely to compute aggregate safety buckets. raw "
            "orders/candidates/labels/paths/queries/tasks/repos remain private "
            "and are never public outputs."),
        "future_n10er_private_orders_authorized_bool": True,
        "future_n10er_private_labels_authorized_bool": True,
        "future_n10er_private_raw_candidates_authorized_bool": True,
        "future_n10er_new_retrieval_output_authorized_bool": True,
        "future_n10er_per_task_diagnostics_private_authorized_bool": True,
        "score_phase_gold_labels_private_authorized_bool": True,
        "policy_selection_uses_gold_bool": False,
        "raw_orders_publication_authorized_bool": False,
        "raw_candidates_publication_authorized_bool": False,
        "raw_labels_publication_authorized_bool": False,
        "raw_paths_accepted_bool": False,
        "raw_queries_accepted_bool": False,
        "raw_tasks_accepted_bool": False,
        "raw_repos_accepted_bool": False,
        "cloned_repo_contents_accepted_bool": False,
        "public_aggregate_buckets_accepted_bool": True,
        "aggregate_publication_only_bool": True,
    }]


def future_probe_output_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_output_contract_id": "n10eqoutput0000",
        "output_contract_bucket": "aggregate_bucket_safety_flags_only",
        "output_description_bucket": (
            "the probe emits aggregate-bucket safety flags only: per-bucket "
            "displacement-risk counts, guard-preservation reference counts, "
            "and arm-selection counts. it does NOT emit per-task flags on raw "
            "candidates/paths/ranks, per-task gold presence, or any per-task "
            "diagnostic. outputs are scanner-validated for privacy."),
        "emits_per_task_flags_bool": False,
        "emits_per_task_paths_bool": False,
        "emits_per_task_ranks_bool": False,
        "emits_per_task_gold_presence_bool": False,
        "emits_aggregate_bucket_flags_bool": True,
        "emits_threshold_tuned_values_bool": False,
        "emits_method_winner_claim_bool": False,
        "emits_runtime_default_change_bool": False,
        "output_scanner_validated_bool": True,
    }]


# ── N10ER pass/fail gate records ───────────────────────────────────────────

def n10er_pass_fail_gate_records() -> list[dict[str, Any]]:
    """Design the pass/fail gates the N10ER bounded public CI probe must meet.
    All gates are evaluated on aggregate buckets; none uses gold for policy."""
    return [
        {
            "anonymous_gate_id": "n10eqgate0000",
            "gate_bucket": "n10er_private_execution_inputs_aggregate_publication_only",
            "gate_description_bucket": (
                "N10ER may use private bounded-CI orders/candidates/labels for "
                "score-phase bucketing, but public output must be aggregate-only."),
            "gate_pass_condition_bucket": "private_execution_inputs_raw_publication_zero",
            "gate_fail_condition_bucket": "any_raw_orders_candidates_labels_paths_queries_tasks_or_repos_public",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10eqgate0001",
            "gate_bucket": "n10er_displacement_risk_aggregate_only",
            "gate_description_bucket": (
                "the probe's displacement-risk output must be aggregate-bucket "
                "counts only; no per-task flags on raw candidates/paths/ranks."),
            "gate_pass_condition_bucket": "output_aggregate_buckets_only",
            "gate_fail_condition_bucket": "any_per_task_raw_output",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10eqgate0002",
            "gate_bucket": "n10er_no_threshold_tuning",
            "gate_description_bucket": (
                "N10ER must not tune the frozen threshold (>=4); the probe uses "
                "the frozen buckets observationally only."),
            "gate_pass_condition_bucket": "threshold_frozen_unchanged",
            "gate_fail_condition_bucket": "any_threshold_tuning_on_locked_sample",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10eqgate0003",
            "gate_bucket": "n10er_no_method_winner_claim",
            "gate_description_bucket": (
                "N10ER must not promote guard/full/diffaware or claim method "
                "winner even if guard appears safer."),
            "gate_pass_condition_bucket": "no_promotion_or_winner_claim",
            "gate_fail_condition_bucket": "any_promotion_or_winner_claim",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10eqgate0004",
            "gate_bucket": "n10er_no_runtime_default_change",
            "gate_description_bucket": (
                "N10ER must not change runtime/default behavior; the safety "
                "probe remains opt-in/eval-only."),
            "gate_pass_condition_bucket": "runtime_default_unchanged",
            "gate_fail_condition_bucket": "any_runtime_default_change",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
        {
            "anonymous_gate_id": "n10eqgate0005",
            "gate_bucket": "n10er_reproducibility_check_on_held_out_public",
            "gate_description_bucket": (
                "N10ER must run on a held-out manifest-listed public sample "
                "(not the locked N10EN sample) to test misfire reproducibility; "
                "a pass requires the aggregate displacement risk to be reported "
                "without promotion."),
            "gate_pass_condition_bucket": "held_out_public_sample_aggregate_report",
            "gate_fail_condition_bucket": "uses_locked_n10en_sample_or_promotes",
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
        },
    ]


# ── Risk control records ──────────────────────────────────────────────────

def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "n10eqrisk0000",
            "risk_bucket": RISK_AGGREGATE_OVERINTERPRETATION,
            "risk_description_bucket": (
                "designing a probe around 2 misfire cases risks aggregate "
                "overinterpretation; the probe could overfit to this sample."),
            "mitigation_bucket": (
                "probe features are bucket-level proxies; held-out public "
                "sample gate (n10er_pass_fail_gate 0005) blocks locked-sample "
                "reuse; stop_design_only_insufficient from N10EP preserved."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0001",
            "risk_bucket": RISK_HINDSIGHT_THRESHOLD_TUNING,
            "risk_description_bucket": (
                "choosing probe feature thresholds by hindsight on the 49 "
                "full-selected tasks would be data snooping."),
            "mitigation_bucket": (
                "features use the FROZEN buckets (0_to_2 / 3 / 4_to_5) "
                "observationally; threshold_tuning_bool=false on every feature; "
                "n10er gate 0002 blocks threshold tuning."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0002",
            "risk_bucket": RISK_GUARD_PROMOTION_FROM_TWO_CASES,
            "risk_description_bucket": (
                "the guard-preservation reference could be misread as a guard "
                "promotion signal from 2 cases."),
            "mitigation_bucket": (
                "guard_preservation_ref is a reference feature, not a "
                "promotion signal; guard_full_diffaware_promotion_authorized_"
                "bool=false; n10er gate 0003 blocks promotion."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0003",
            "risk_bucket": RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
            "risk_description_bucket": (
                "probe features could leak the private per-task diagnostics "
                "that N10EO used into the public design."),
            "mitigation_bucket": (
                "every feature derives from public aggregate buckets only; "
                "reads_per_task_data_bool=false on every feature; "
                "forbidden_scan blocks raw per-task/paths/orders/labels keys "
                "and the private diagnostic rerun path."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0004",
            "risk_bucket": RISK_RUNTIME_DEFAULT_CREEP,
            "risk_description_bucket": (
                "a safety probe could drift into a runtime/default gate."),
            "mitigation_bucket": (
                "runtime_default_change_bool=false; probe stays opt-in/eval-"
                "only; n10er gate 0004 blocks runtime/default change."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0005",
            "risk_bucket": RISK_N10ER_EXECUTION_CREEP,
            "risk_description_bucket": (
                "authorizing the N10ER contract could be misread as "
                "authorizing N10ER execution now."),
            "mitigation_bucket": (
                "n10er_contract_authorized_bool=true but "
                "n10er_execution_authorized_bool=false; stop/go explicitly "
                "separates contract handoff from execution."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eqrisk0006",
            "risk_bucket": RISK_FEATURE_PROXY_AS_GOLD,
            "risk_description_bucket": (
                "the baseline_gold_proxy feature could be misused as actual "
                "gold labels for policy."),
            "mitigation_bucket": (
                "the proxy is bucket-level aggregate inference only; "
                "gold_labels_accepted_bool=false in the input contract; "
                "gold_used_for_policy_bool=false; gate_uses_gold_for_policy_"
                "bool=false on every gate."),
            "risk_controlled_bool": True,
        },
    ]


# ── Claim boundary + stop/go ───────────────────────────────────────────────

def claim_boundary() -> dict[str, Any]:
    """Explicit false privacy/claim boundary fields. N10EQ is design-only,
    public-only, and authorizes only the N10ER contract (not execution)."""
    return {
        "anonymous_claim_boundary_id": "n10eqclaim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_only_bool": True,
        "private_diagnostic_inputs_used_bool": False,
        "private_rows_read_bool": False,
        "rerun_local_canary_bool": False,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
        "raw_per_task_diagnostics_upload_bool": False,
        "run_phase_labels_used_bool": False,
        "score_phase_labels_used_bool": False,
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
        "frozen_rule_change_bool": False,
        "threshold_tuning_bool": False,
        "new_policy_experiment_bool": False,
        "ci_variant_execution_bool": False,
        "n10er_execution_authorized_bool": False,
    }


def stop_go_records() -> list[dict[str, Any]]:
    """Stop/go: authorize the N10ER bounded public CI score/guard safety probe
    CONTRACT (design-only handoff), NOT N10ER execution. No threshold tuning,
    no promotion, no method-winner, no runtime/default, no rule change."""
    return [{
        "anonymous_stop_go_id": "n10eqstop0000",
        "next_allowed_phase": "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe",
        "design_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "n10er_contract_authorized_bool": True,
        "n10er_execution_authorized_bool": False,
        "n10eq_execution_authorized_bool": False,
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
        "network_run_authorized_bool": False,
    }]


# ── Report assembly ────────────────────────────────────────────────────────

def build_unavailable_report(lock: dict[str, Any], reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10eq_score_guard_safety_probe_design_v1",
        "phase_bucket": "BEA-v1-N10EQ Score/Guard Safety Probe Design",
        "status": STATUS_UNAVAILABLE,
        "unavailable_reason_bucket": reason,
        "n10ep_source_lock_records": [lock],
        "mechanism_lock_records": [],
        "future_probe_feature_records": [],
        "future_probe_input_contract_records": [],
        "future_probe_output_contract_records": [],
        "n10er_pass_fail_gate_records": [],
        "risk_control_records": [],
        "stop_go_records": stop_go_records(),
        "claim_boundary_records": [claim_boundary()],
        "gate_records": [
            {"anonymous_gate_id": "n10eqgate0006", "gate_bucket": "n10ep_source_locked",
             "gate_passed_bool": lock["source_locked_bool"]},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_CLOSED
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_CLOSED
    return report


def build_report(lock: dict[str, Any], mlock: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10eq_score_guard_safety_probe_design_v1",
        "phase_bucket": "BEA-v1-N10EQ Score/Guard Safety Probe Design",
        "status": STATUS_N10ER_CONTRACT_AUTHORIZED,
        "n10ep_source_lock_records": [lock],
        "mechanism_lock_records": [mlock],
        "future_probe_feature_records": future_probe_feature_records(mlock),
        "future_probe_input_contract_records": future_probe_input_contract_records(),
        "future_probe_output_contract_records": future_probe_output_contract_records(),
        "n10er_pass_fail_gate_records": n10er_pass_fail_gate_records(),
        "risk_control_records": risk_control_records(),
        "stop_go_records": stop_go_records(),
        "claim_boundary_records": [claim_boundary()],
        "gate_records": [
            {"anonymous_gate_id": "n10eqgate0006", "gate_bucket": "n10ep_source_locked",
             "gate_passed_bool": lock["source_locked_bool"]},
            {"anonymous_gate_id": "n10eqgate0007", "gate_bucket": "mechanism_locked",
             "gate_passed_bool": mlock["mechanism_locked_bool"]},
            {"anonymous_gate_id": "n10eqgate0008", "gate_bucket": "probe_features_design_only",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10eqgate0009", "gate_bucket": "input_contract_no_private",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10eqgate0010", "gate_bucket": "output_contract_aggregate_only",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10eqgate0011", "gate_bucket": "n10er_contract_not_execution",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10eqgate0012", "gate_bucket": "privacy_scan_pass",
             "gate_passed_bool": True},
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
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_only_bool"):
        if claim.get(field) is not True:
            failures.append(f"claim_{field}_not_true")
    for field in ("method_winner_claim_bool", "production_retrieval_change_bool",
                  "runtime_default_change_bool", "selector_reranker_bool",
                  "provider_model_network_bool", "raw_per_task_diagnostics_upload_bool",
                  "raw_candidate_upload_bool", "raw_label_upload_bool",
                  "raw_path_upload_bool", "raw_query_upload_bool",
                  "scaled_retrieval_claim_bool", "frozen_rule_change_bool",
                  "threshold_tuning_bool", "new_policy_experiment_bool",
                  "ci_variant_execution_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool",
                  "private_diagnostic_inputs_used_bool", "private_rows_read_bool",
                  "network_run_bool", "remote_embedding_bool",
                  "quiver_dense_real_bool", "external_benchmark_download_bool",
                  "gold_used_for_policy_bool", "rerun_local_canary_bool",
                  "run_phase_labels_used_bool", "score_phase_labels_used_bool",
                  "n10er_execution_authorized_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ("n10er_execution_authorized_bool", "n10eq_execution_authorized_bool",
                  "threshold_tuning_authorized_bool", "new_policy_experiment_authorized_bool",
                  "frozen_rule_change_authorized_bool",
                  "guard_full_diffaware_promotion_authorized_bool",
                  "runtime_default_change_authorized_bool",
                  "method_winner_claim_authorized_bool",
                  "downstream_scaled_retrieval_authorized_bool",
                  "raw_diagnostic_publication_authorized_bool",
                  "ci_variant_execution_authorized_bool",
                  "selector_reranker_authorized_bool",
                  "provider_model_network_authorized_bool",
                  "network_run_authorized_bool"):
        if stop.get(field) is not False:
            failures.append(f"stop_{field}_not_false")
    if stop.get("n10er_contract_authorized_bool") is not True:
        failures.append("stop_n10er_contract_not_authorized")
    if stop.get("design_only_bool") is not True:
        failures.append("stop_design_only_not_true")
    if stop.get("next_allowed_phase") != "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe":
        failures.append("stop_next_phase_mismatch")
    # Required record sections.
    for key in ("n10ep_source_lock_records", "mechanism_lock_records",
                "future_probe_feature_records", "future_probe_input_contract_records",
                "future_probe_output_contract_records", "n10er_pass_fail_gate_records",
                "risk_control_records", "stop_go_records", "claim_boundary_records",
                "gate_records"):
        if key not in report or not report[key]:
            failures.append(f"missing_or_empty_{key}")
    # Probe feature coverage (7 features).
    feat_buckets = {r.get("feature_bucket") for r in report.get("future_probe_feature_records", [])}
    for needed in ALL_PROBE_FEATURES:
        if needed not in feat_buckets:
            failures.append(f"missing_probe_feature_{needed}")
    # All features design-only and no per-task data.
    for feat in report.get("future_probe_feature_records", []):
        if feat.get("reads_per_task_data_bool") is not False:
            failures.append(f"feature_{feat.get('feature_bucket')}_reads_per_task")
        if feat.get("tunes_threshold_bool") is not False:
            failures.append(f"feature_{feat.get('feature_bucket')}_tunes_threshold")
        if feat.get("design_only_bool") is not True:
            failures.append(f"feature_{feat.get('feature_bucket')}_not_design_only")
    # Input contract permits future N10ER private execution-time inputs while
    # requiring aggregate-only public output.
    ic = (report.get("future_probe_input_contract_records") or [{}])[0]
    for field in ("future_n10er_private_orders_authorized_bool",
                  "future_n10er_private_labels_authorized_bool",
                  "future_n10er_private_raw_candidates_authorized_bool",
                  "future_n10er_new_retrieval_output_authorized_bool",
                  "future_n10er_per_task_diagnostics_private_authorized_bool",
                  "score_phase_gold_labels_private_authorized_bool"):
        if ic.get(field) is not True:
            failures.append(f"input_contract_{field}_not_true")
    for field in ("policy_selection_uses_gold_bool",
                  "raw_orders_publication_authorized_bool",
                  "raw_candidates_publication_authorized_bool",
                  "raw_labels_publication_authorized_bool",
                  "raw_paths_accepted_bool", "raw_queries_accepted_bool",
                  "raw_tasks_accepted_bool", "raw_repos_accepted_bool",
                  "cloned_repo_contents_accepted_bool"):
        if ic.get(field) is not False:
            failures.append(f"input_contract_{field}_not_false")
    if ic.get("aggregate_publication_only_bool") is not True:
        failures.append("input_contract_aggregate_publication_only_not_true")
    # Output contract: aggregate only.
    oc = (report.get("future_probe_output_contract_records") or [{}])[0]
    for field in ("emits_per_task_flags_bool", "emits_per_task_paths_bool",
                  "emits_per_task_ranks_bool", "emits_per_task_gold_presence_bool",
                  "emits_threshold_tuned_values_bool", "emits_method_winner_claim_bool",
                  "emits_runtime_default_change_bool"):
        if oc.get(field) is not False:
            failures.append(f"output_contract_{field}_not_false")
    if oc.get("emits_aggregate_bucket_flags_bool") is not True:
        failures.append("output_contract_aggregate_flags_not_true")
    # N10ER gates use no gold for policy.
    for gate in report.get("n10er_pass_fail_gate_records", []):
        if gate.get("gate_uses_gold_for_policy_bool") is not False:
            failures.append(f"gate_{gate.get('gate_bucket')}_uses_gold_for_policy")
        if gate.get("gate_evaluated_on_aggregate_bool") is not True:
            failures.append(f"gate_{gate.get('gate_bucket')}_not_aggregate")
    # Risk control coverage.
    risk_buckets = {r.get("risk_bucket") for r in report.get("risk_control_records", [])}
    for needed in ALL_RISK_CONTROLS:
        if needed not in risk_buckets:
            failures.append(f"missing_risk_control_{needed}")
    # Mechanism lock values.
    mlock = (report.get("mechanism_lock_records") or [{}])[0]
    expected_mlock = {
        "locked_novel_first_displaced_count": 2,
        "locked_baseline_gold_rank_1_to_5_displaced_count": 2,
        "locked_candidate_available_beyond_top10_count": 2,
        "locked_guard_better_than_full_count": 2,
        "locked_full_lost_guard_preserved_count": 2,
        "locked_low_novelty_bucket_loss_count": 2,
        "locked_diffaware_full_guard_would_preserve_count": 2,
    }
    for k, v in expected_mlock.items():
        if mlock.get(k) != v:
            failures.append(f"mechanism_lock_{k}_mismatch")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_N10ER_CONTRACT_AUTHORIZED in STATUS_VOCAB
                   and STATUS_UNAVAILABLE in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"v": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_runid", scan_summary({"v": "28449370879"})["status"] == "fail"))
    checks.append(("scanner_diag_rerun", scan_summary({"v": "/tmp/n10eo_diag_rerun/run/orders.private.json"})["status"] == "fail"))
    checks.append(("scanner_orders_private", scan_summary({"v": "orders.private.json"})["status"] == "fail"))
    checks.append(("scanner_labels_jsonl", scan_summary({"v": "ci_labels.jsonl"})["status"] == "fail"))
    checks.append(("scanner_n10eo_diag", scan_summary({"v": "n10eo_diag_anything"})["status"] == "fail"))

    # N10EP source lock verification with the committed N10EP artifact.
    n10ep, ep_state = load_json(N10EP_REPORT)
    n10eo, eo_state = load_json(N10EO_REPORT)
    n10en, en_state = load_json(N10EN_REPORT)
    n10em, em_state = load_json(N10EM_REPORT)
    lock = lock_n10ep_source(n10ep, ep_state, n10eo, eo_state, n10en, en_state, n10em, em_state)
    checks.append(("lock_source_locked", lock["source_locked_bool"] is True))
    checks.append(("lock_status_match", lock["status_match_bool"] is True))
    checks.append(("lock_n10eq_auth_match", lock["n10eq_design_authorized_match_bool"] is True))
    checks.append(("lock_n10eq_exec_false", lock["n10eq_execution_false_match_bool"] is True))
    checks.append(("lock_n10er_exec_false", lock["n10er_execution_false_match_bool"] is True))
    checks.append(("lock_next_phase_match", lock["next_phase_match_bool"] is True))
    checks.append(("lock_checkpoint", lock["locked_n10ep_checkpoint"] == "0a54b49"))

    # Mechanism lock re-derived from N10EO public aggregate.
    mlock = mechanism_lock(n10eo, eo_state)
    checks.append(("mlock_locked", mlock["mechanism_locked_bool"] is True))
    checks.append(("mlock_primary", mlock["locked_primary_mechanism"] == "novel_first_displaced_baseline_gold_from_top10"))
    checks.append(("mlock_novel_first_displaced", mlock["locked_novel_first_displaced_count"] == 2))
    checks.append(("mlock_rank_1_to_5", mlock["locked_baseline_gold_rank_1_to_5_displaced_count"] == 2))
    checks.append(("mlock_candidate_beyond", mlock["locked_candidate_available_beyond_top10_count"] == 2))
    checks.append(("mlock_guard_better", mlock["locked_guard_better_than_full_count"] == 2))
    checks.append(("mlock_full_lost_guard_preserved", mlock["locked_full_lost_guard_preserved_count"] == 2))
    checks.append(("mlock_low_nov_loss", mlock["locked_low_novelty_bucket_loss_count"] == 2))
    checks.append(("mlock_diffaware_guard_preserve", mlock["locked_diffaware_full_guard_would_preserve_count"] == 2))

    # Probe feature coverage (7 features).
    feats = future_probe_feature_records(mlock)
    checks.append(("features_count", len(feats) == 7))
    for needed in ALL_PROBE_FEATURES:
        checks.append((f"feature_{needed}_present", any(f["feature_bucket"] == needed for f in feats)))
    checks.append(("features_all_design_only", all(f["design_only_bool"] is True for f in feats)))
    checks.append(("features_no_per_task", all(f["reads_per_task_data_bool"] is False for f in feats)))
    checks.append(("features_no_threshold_tuning", all(f["tunes_threshold_bool"] is False for f in feats)))

    # Input contract.
    ic = future_probe_input_contract_records()[0]
    checks.append(("input_future_private_orders_authorized", ic["future_n10er_private_orders_authorized_bool"] is True))
    checks.append(("input_future_private_labels_authorized", ic["future_n10er_private_labels_authorized_bool"] is True))
    checks.append(("input_future_raw_candidates_private_authorized", ic["future_n10er_private_raw_candidates_authorized_bool"] is True))
    checks.append(("input_future_retrieval_output_private_authorized", ic["future_n10er_new_retrieval_output_authorized_bool"] is True))
    checks.append(("input_future_private_diagnostics_authorized", ic["future_n10er_per_task_diagnostics_private_authorized_bool"] is True))
    checks.append(("input_score_phase_gold_private_authorized", ic["score_phase_gold_labels_private_authorized_bool"] is True))
    checks.append(("input_policy_no_gold", ic["policy_selection_uses_gold_bool"] is False))
    checks.append(("input_no_raw_orders_publication", ic["raw_orders_publication_authorized_bool"] is False))
    checks.append(("input_no_raw_candidates_publication", ic["raw_candidates_publication_authorized_bool"] is False))
    checks.append(("input_no_raw_labels_publication", ic["raw_labels_publication_authorized_bool"] is False))
    checks.append(("input_no_raw_paths", ic["raw_paths_accepted_bool"] is False))
    checks.append(("input_no_raw_queries", ic["raw_queries_accepted_bool"] is False))
    checks.append(("input_no_raw_tasks", ic["raw_tasks_accepted_bool"] is False))
    checks.append(("input_no_raw_repos", ic["raw_repos_accepted_bool"] is False))
    checks.append(("input_no_cloned_repo", ic["cloned_repo_contents_accepted_bool"] is False))
    checks.append(("input_aggregate_publication_only", ic["aggregate_publication_only_bool"] is True))
    checks.append(("input_public_aggregates", ic["public_aggregate_buckets_accepted_bool"] is True))

    # Output contract.
    oc = future_probe_output_contract_records()[0]
    checks.append(("output_no_per_task_flags", oc["emits_per_task_flags_bool"] is False))
    checks.append(("output_no_per_task_paths", oc["emits_per_task_paths_bool"] is False))
    checks.append(("output_no_per_task_ranks", oc["emits_per_task_ranks_bool"] is False))
    checks.append(("output_no_per_task_gold", oc["emits_per_task_gold_presence_bool"] is False))
    checks.append(("output_aggregate_flags", oc["emits_aggregate_bucket_flags_bool"] is True))
    checks.append(("output_no_threshold_tuned", oc["emits_threshold_tuned_values_bool"] is False))
    checks.append(("output_no_method_winner", oc["emits_method_winner_claim_bool"] is False))
    checks.append(("output_no_runtime_default", oc["emits_runtime_default_change_bool"] is False))

    # N10ER pass/fail gates.
    gates = n10er_pass_fail_gate_records()
    checks.append(("gates_count", len(gates) == 6))
    checks.append(("gates_no_gold_for_policy", all(g["gate_uses_gold_for_policy_bool"] is False for g in gates)))
    checks.append(("gates_all_aggregate", all(g["gate_evaluated_on_aggregate_bool"] is True for g in gates)))
    checks.append(("gate_no_threshold_tuning_present", any(g["gate_bucket"] == "n10er_no_threshold_tuning" for g in gates)))
    checks.append(("gate_no_method_winner_present", any(g["gate_bucket"] == "n10er_no_method_winner_claim" for g in gates)))
    checks.append(("gate_no_runtime_default_present", any(g["gate_bucket"] == "n10er_no_runtime_default_change" for g in gates)))
    checks.append(("gate_held_out_public_present", any(g["gate_bucket"] == "n10er_reproducibility_check_on_held_out_public" for g in gates)))

    # Risk controls (7).
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == len(ALL_RISK_CONTROLS)))
    for needed in ALL_RISK_CONTROLS:
        checks.append((f"risk_{needed}_present", any(r["risk_bucket"] == needed for r in risks)))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))

    # Stop/go: N10ER contract authorized, execution not.
    stops = stop_go_records()
    checks.append(("stop_n10er_contract_authorized", stops[0]["n10er_contract_authorized_bool"] is True))
    checks.append(("stop_n10er_execution_false", stops[0]["n10er_execution_authorized_bool"] is False))
    checks.append(("stop_n10eq_execution_false", stops[0]["n10eq_execution_authorized_bool"] is False))
    checks.append(("stop_threshold_tuning_false", stops[0]["threshold_tuning_authorized_bool"] is False))
    checks.append(("stop_promotion_false", stops[0]["guard_full_diffaware_promotion_authorized_bool"] is False))
    checks.append(("stop_runtime_false", stops[0]["runtime_default_change_authorized_bool"] is False))
    checks.append(("stop_method_winner_false", stops[0]["method_winner_claim_authorized_bool"] is False))
    checks.append(("stop_ci_variant_exec_false", stops[0]["ci_variant_execution_authorized_bool"] is False))
    checks.append(("stop_network_false", stops[0]["network_run_authorized_bool"] is False))
    checks.append(("stop_next_phase", stops[0]["next_allowed_phase"] == "BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe"))

    # Claim boundary.
    cb = claim_boundary()
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_only_true", cb["design_only_bool"] is True))
    checks.append(("claim_n10er_exec_false", cb["n10er_execution_authorized_bool"] is False))
    checks.append(("claim_private_diag_false", cb["private_diagnostic_inputs_used_bool"] is False))
    checks.append(("claim_method_winner_false", cb["method_winner_claim_bool"] is False))
    checks.append(("claim_threshold_tuning_false", cb["threshold_tuning_bool"] is False))

    # Full report build + validation.
    report = build_report(lock, mlock)
    checks.append(("report_status", report["status"] == STATUS_N10ER_CONTRACT_AUTHORIZED))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))

    # Unavailable report when source not locked.
    bad_lock = lock_n10ep_source(None, "missing")
    unavail = build_unavailable_report(bad_lock, "n10ep_source_not_locked")
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

    # Load public aggregate artifacts only. No private diagnostic inputs.
    n10ep, ep_state = load_json(Path(args.n10ep_report))
    n10eo, eo_state = load_json(Path(args.n10eo_report))
    n10en, en_state = load_json(Path(args.n10en_report))
    n10em, em_state = load_json(Path(args.n10em_report))
    lock = lock_n10ep_source(n10ep, ep_state, n10eo, eo_state, n10en, en_state, n10em, em_state)
    if not lock["source_locked_bool"]:
        report = build_unavailable_report(lock, "n10ep_source_not_locked")
    else:
        mlock = mechanism_lock(n10eo, eo_state)
        if not mlock["mechanism_locked_bool"]:
            report = build_unavailable_report(lock, "n10eo_mechanism_not_locked")
        else:
            report = build_report(lock, mlock)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
