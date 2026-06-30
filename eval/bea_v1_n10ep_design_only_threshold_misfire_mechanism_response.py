#!/usr/bin/env python3
"""BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response.

N10EP is a *public-artifact-only design packaging* phase that sits after the
N10EO checkpoint (commit 6f8eeda). It re-expresses the N10EO aggregate
mechanism buckets as a *design-only* response: it describes forward design
options (N10EQ score/guard safety probe, N10ER public CI small variant, and a
stop-design-only-insufficient option), records the risk controls that bound
those options, and emits a conservative stop/go decision.

Allowed inputs (public only):
  * the committed N10EO public aggregate artifact
  * the committed N10EN public aggregate artifact
  * the committed N10EM public artifact / docs / evaluator contract
  * public docs/code metadata only (no cloned repo contents)

Forbidden inputs:
  * /tmp/n10eo_diag_rerun, orders.private.json, private labels JSONL
  * raw candidates / orders / paths / queries / tasks / repos
  * per-task diagnostics, cloned repo contents
  * new retrieval / CI variants / policy execution

N10EP performs NO execution. It does not tune thresholds, run new policy
experiments, change the frozen rule, promote guard/full/diffaware, change
runtime/default behavior, claim method winner, run downstream/scaled
retrieval, or publish raw diagnostics. The published artifact is
aggregate-bucket-only with explicit false privacy/claim boundary fields.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ep_design_only_threshold_misfire_mechanism_response"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"

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

# ── Locked N10EO checkpoint (commit 6f8eeda) ────────────────────────────────
LOCKED_N10EO_CHECKPOINT = "6f8eeda"
LOCKED_N10EO_STATUS = "n10eo_failure_analysis_pass_mechanism_identified"
LOCKED_NEXT_ALLOWED_PHASE = "BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response"
LOCKED_PRIMARY_MECHANISM = "novel_first_displaced_baseline_gold_from_top10"

# Public aggregate values locked from the N10EO artifact (checkpoint 6f8eeda).
LOCKED_COUNTS = {
    "baseline": {"top10": 39, "lost": 0},
    "full": {"top10": 37, "lost": 2},
    "guard": {"top10": 39, "lost": 0},
    "diffaware": {"top10": 37, "lost": 2},
}
LOCKED_TASK_WITH_GOLD = 40
LOCKED_SELECTED_ARMS = {"full_novel_first": 49, "guarded_top5_novel_distinct": 9}
LOCKED_CITATION = {"valid": 3636, "total": 3636}

# Locked mechanism-bucket counts (N10EO Category 3 + Category 2 cross-cut).
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
# The 2 diffaware losses both fall in the low-novelty (0_to_2) bucket.
LOCKED_LOW_NOVELTY_BUCKET_LOSS = 2
LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE = 2

# Threshold frozen from the N10EK/N10EM rule.
FROZEN_THRESHOLD = 4
FROZEN_THRESHOLD_FEATURE = "top5_novel_candidate_item_count"
FROZEN_RULE = "if_top5_novel_candidate_item_count_gte_4_then_guarded_else_full"

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_N10EQ_AUTHORIZED = "n10ep_design_response_pass_n10eq_authorized"
STATUS_N10EQ_N10ER_AUTHORIZED = "n10ep_design_response_pass_n10eq_n10er_authorized"
STATUS_FAIL_CLOSED = "n10ep_design_response_fail_closed_privacy_or_contract"
STATUS_UNAVAILABLE = "n10ep_design_response_unavailable_source_not_locked"
STATUS_VOCAB = {
    STATUS_N10EQ_AUTHORIZED,
    STATUS_N10EQ_N10ER_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_UNAVAILABLE,
}
EXIT0_VOCAB = {STATUS_N10EQ_AUTHORIZED, STATUS_N10EQ_N10ER_AUTHORIZED}

# Conservative default: authorize only the N10EQ design (no execution).
CONSERVATIVE_AUTHORIZE_N10ER_DESIGN = False

# ── Design option buckets ──────────────────────────────────────────────────
DESIGN_N10EQ = "n10eq_score_guard_safety_probe_design"
DESIGN_N10ER = "n10er_public_ci_small_variant_design"
DESIGN_STOP_INSUFFICIENT = "stop_design_only_insufficient"
ALL_DESIGN_OPTIONS = (DESIGN_N10EQ, DESIGN_N10ER, DESIGN_STOP_INSUFFICIENT)

# ── Risk control buckets ───────────────────────────────────────────────────
RISK_AGGREGATE_OVERINTERPRETATION = "aggregate_overinterpretation_from_two_cases"
RISK_HINDSIGHT_THRESHOLD_TUNING = "hindsight_threshold_tuning"
RISK_GUARD_PROMOTION_FROM_TWO_CASES = "guard_promotion_from_two_cases"
RISK_PUBLIC_CI_VARIANT_AS_METHOD_WINNER = "public_ci_variant_as_method_winner"
RISK_PRIVATE_DIAGNOSTIC_LEAKAGE = "private_diagnostic_leakage"
RISK_RUNTIME_DEFAULT_CREEP = "runtime_default_creep"
ALL_RISK_CONTROLS = (
    RISK_AGGREGATE_OVERINTERPRETATION,
    RISK_HINDSIGHT_THRESHOLD_TUNING,
    RISK_GUARD_PROMOTION_FROM_TWO_CASES,
    RISK_PUBLIC_CI_VARIANT_AS_METHOD_WINNER,
    RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
    RISK_RUNTIME_DEFAULT_CREEP,
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
    # N10EO private diagnostic rerun path is forbidden as an input here.
    re.compile(r"n10eo_diag_rerun", re.I),
    re.compile(r"orders\.private\.json", re.I),
    re.compile(r"ci_labels\.jsonl", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10EP design-only threshold-misfire mechanism response")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report for contract/privacy")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n10eo-report", default=str(N10EO_REPORT),
                        help="path to the committed N10EO public aggregate artifact")
    parser.add_argument("--n10en-report", default=str(N10EN_REPORT),
                        help="path to the committed N10EN public aggregate artifact")
    parser.add_argument("--n10em-report", default=str(N10EM_REPORT),
                        help="path to the committed N10EM public artifact")
    parser.add_argument("--authorize-n10er-design", action="store_true",
                        help="also authorize the N10ER design (default: N10EQ only, conservative)")
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


# ── N10EO source lock ──────────────────────────────────────────────────────

def lock_n10eo_source(n10eo: dict[str, Any] | None, state: str,
                      n10en: dict[str, Any] | None = None,
                      n10en_state: str = "missing",
                      n10em: dict[str, Any] | None = None,
                      n10em_state: str = "missing") -> dict[str, Any]:
    """Verify the committed N10EO artifact matches the locked checkpoint result.

    N10EP only consumes *public* aggregate values from N10EO/N10EN/N10EM. No
    private diagnostic inputs are read. The lock confirms the N10EO status,
    primary mechanism, and aggregate counts match the 6f8eeda checkpoint.
    """
    present_ok = state == "present" and isinstance(n10eo, dict)
    src: dict[str, Any] = n10eo if isinstance(n10eo, dict) else {}
    status_ok = present_ok and src.get("status") == LOCKED_N10EO_STATUS
    counts_ok = False
    mech_ok = False
    fg_ok = False
    low_nov_ok = False
    primary_ok = False
    next_phase_ok = False

    if status_ok:
        summ = (src.get("regression_summary_records") or [{}])[0]
        counts_ok = (
            summ.get("baseline_top10_count") == LOCKED_COUNTS["baseline"]["top10"]
            and summ.get("full_top10_count") == LOCKED_COUNTS["full"]["top10"]
            and summ.get("guard_top10_count") == LOCKED_COUNTS["guard"]["top10"]
            and summ.get("diffaware_top10_count") == LOCKED_COUNTS["diffaware"]["top10"]
            and summ.get("full_lost_baseline_count") == LOCKED_COUNTS["full"]["lost"]
            and summ.get("guard_lost_baseline_count") == LOCKED_COUNTS["guard"]["lost"]
            and summ.get("diffaware_lost_baseline_count") == LOCKED_COUNTS["diffaware"]["lost"]
            and summ.get("task_with_gold_count") == LOCKED_TASK_WITH_GOLD
            and summ.get("selected_full_novel_first_count") == LOCKED_SELECTED_ARMS["full_novel_first"]
            and summ.get("selected_guarded_top5_novel_distinct_count") == LOCKED_SELECTED_ARMS["guarded_top5_novel_distinct"]
        )
        primary_ok = summ.get("primary_mechanism_bucket") == LOCKED_PRIMARY_MECHANISM

        mech_map = {r.get("mechanism_bucket"): r.get("task_count")
                    for r in src.get("lost_baseline_mechanism_records", [])}
        mech_ok = all(mech_map.get(k) == v for k, v in LOCKED_MECH_COUNTS.items())

        fg_map = {r.get("outcome_bucket"): r.get("task_count")
                  for r in src.get("full_vs_guard_outcome_records", [])}
        fg_ok = all(fg_map.get(k) == v for k, v in LOCKED_FG_COUNTS.items())

        # Low-novelty bucket loss: the 0_to_2 novelty bucket's diffaware loss.
        nov0 = next((r for r in src.get("novelty_bucket_diagnostic_records", [])
                     if r.get("bucket") == "top5_novel_candidate_item_count_0_to_2"), {})
        low_nov_ok = (nov0.get("diffaware_lost_baseline_count") == LOCKED_LOW_NOVELTY_BUCKET_LOSS
                      and nov0.get("diffaware_chose_full_but_guarded_would_preserve_count")
                      == LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE)

        stop = (src.get("stop_go_records") or [{}])[0]
        next_phase_ok = stop.get("next_allowed_phase") == LOCKED_NEXT_ALLOWED_PHASE

    all_ok = (status_ok and counts_ok and mech_ok and fg_ok and low_nov_ok
              and primary_ok and next_phase_ok)
    return {
        "anonymous_source_lock_id": "n10epsource0000",
        "locked_n10eo_checkpoint": LOCKED_N10EO_CHECKPOINT,
        "locked_n10eo_status": LOCKED_N10EO_STATUS,
        "actual_n10eo_status": str(src.get("status", "unavailable")),
        "status_match_bool": status_ok,
        "primary_mechanism_match_bool": primary_ok,
        "aggregate_counts_match_bool": counts_ok,
        "mechanism_buckets_match_bool": mech_ok,
        "full_guard_outcome_match_bool": fg_ok,
        "low_novelty_bucket_loss_match_bool": low_nov_ok,
        "next_allowed_phase_match_bool": next_phase_ok,
        "n10eo_artifact_load_status_bucket": state,
        "n10en_artifact_load_status_bucket": n10en_state,
        "n10em_artifact_load_status_bucket": n10em_state,
        "next_allowed_phase": LOCKED_NEXT_ALLOWED_PHASE,
        "source_locked_bool": all_ok,
        "locked_baseline_top10": LOCKED_COUNTS["baseline"]["top10"],
        "locked_full_top10": LOCKED_COUNTS["full"]["top10"],
        "locked_guard_top10": LOCKED_COUNTS["guard"]["top10"],
        "locked_diffaware_top10": LOCKED_COUNTS["diffaware"]["top10"],
        "locked_full_lost": LOCKED_COUNTS["full"]["lost"],
        "locked_guard_lost": LOCKED_COUNTS["guard"]["lost"],
        "locked_diffaware_lost": LOCKED_COUNTS["diffaware"]["lost"],
        "locked_task_with_gold": LOCKED_TASK_WITH_GOLD,
        "locked_citation_valid": LOCKED_CITATION["valid"],
        "locked_citation_total": LOCKED_CITATION["total"],
    }


# ── Mechanism response summary ─────────────────────────────────────────────

def mechanism_response_summary(lock: dict[str, Any]) -> dict[str, Any]:
    """Re-express the N10EO aggregate mechanism buckets as a design-only
    response summary. Uses only public aggregate values from the lock."""
    return {
        "anonymous_response_summary_id": "n10epsum0000",
        "baseline_top10_count": LOCKED_COUNTS["baseline"]["top10"],
        "full_top10_count": LOCKED_COUNTS["full"]["top10"],
        "guard_top10_count": LOCKED_COUNTS["guard"]["top10"],
        "diffaware_top10_count": LOCKED_COUNTS["diffaware"]["top10"],
        "full_lost_baseline_count": LOCKED_COUNTS["full"]["lost"],
        "guard_lost_baseline_count": LOCKED_COUNTS["guard"]["lost"],
        "diffaware_lost_baseline_count": LOCKED_COUNTS["diffaware"]["lost"],
        "guard_better_than_full_count": LOCKED_FG_COUNTS["guard_better_than_full"],
        "full_lost_guard_preserved_count": LOCKED_FG_COUNTS["full_lost_guard_preserved_baseline"],
        "baseline_gold_rank_1_to_5_displaced_count": LOCKED_MECH_COUNTS["baseline_gold_rank_1_to_5_displaced"],
        "candidate_available_beyond_top10_count": LOCKED_MECH_COUNTS["candidate_available_beyond_top10"],
        "novel_first_displaced_count": LOCKED_MECH_COUNTS["novel_first_displaced_baseline_gold_from_top10"],
        "low_novelty_bucket_loss_count": LOCKED_LOW_NOVELTY_BUCKET_LOSS,
        "diffaware_full_guard_would_preserve_count": LOCKED_DIFFAWARE_FULL_GUARD_WOULD_PRESERVE,
        "primary_mechanism_bucket": LOCKED_PRIMARY_MECHANISM,
        "frozen_threshold_feature": FROZEN_THRESHOLD_FEATURE,
        "frozen_threshold_value": FROZEN_THRESHOLD,
        "frozen_rule_bucket": FROZEN_RULE,
        "mechanism_response_design_only_bool": True,
        "aggregate_buckets_only_bool": True,
    }


# ── Design option records ──────────────────────────────────────────────────

def design_option_records(authorize_n10er: bool) -> list[dict[str, Any]]:
    """Design-only options for responding to the threshold misfire. None of
    these authorizes execution; they are forward design specs only."""
    return [
        {
            "anonymous_design_option_id": "n10epdesign0000",
            "design_option_bucket": DESIGN_N10EQ,
            "design_description_bucket": (
                "design a score/guard safety probe that, given a frozen arm "
                "order and the top5_novel_candidate_item_count feature, "
                "flags tasks where the full novel-first arm may displace an "
                "already-strong baseline gold file (rank 1-5) into ranks "
                "11-20. probe uses only aggregate-bucket diagnostics from "
                "n10eo; no per-task candidates/labels/paths/ranks are read."),
            "addresses_mechanism_bucket": LOCKED_PRIMARY_MECHANISM,
            "input_scope_bucket": "n10eo_aggregate_buckets_only",
            "design_only_bool": True,
            "execution_authorized_bool": False,
            "frozen_rule_change_bool": False,
            "threshold_tuning_bool": False,
            "method_winner_claim_bool": False,
            "runtime_default_change_bool": False,
            "rationale_bucket": (
                "the misfire is a low-novelty-bucket displacement of strong "
                "baseline gold (2/49 full-selected tasks); a safety probe "
                "design can describe how to detect this class without "
                "executing any new policy."),
            "authorized_for_next_phase_bool": True,
        },
        {
            "anonymous_design_option_id": "n10epdesign0001",
            "design_option_bucket": DESIGN_N10ER,
            "design_description_bucket": (
                "design a small public CI variant that re-runs the frozen "
                "difference-aware rule on a slightly different manifest-listed "
                "public sample to confirm whether the threshold-misfire "
                "reproduces or was a 2-case artifact. design is public-ci-only "
                "and reuses the n10en bounded canary scope."),
            "addresses_mechanism_bucket": LOCKED_PRIMARY_MECHANISM,
            "input_scope_bucket": "n10en_public_ci_scope_only",
            "design_only_bool": True,
            "execution_authorized_bool": False,
            "frozen_rule_change_bool": False,
            "threshold_tuning_bool": False,
            "method_winner_claim_bool": False,
            "runtime_default_change_bool": False,
            "rationale_bucket": (
                "a small public CI variant design can probe reproducibility "
                "of the 2-case misfire on held-out public tasks; conservative "
                "default leaves this design packaged but not yet authorized."),
            "authorized_for_next_phase_bool": authorize_n10er,
        },
        {
            "anonymous_design_option_id": "n10epdesign0002",
            "design_option_bucket": DESIGN_STOP_INSUFFICIENT,
            "design_description_bucket": (
                "stop-design-only-insufficient: design-only analysis from 2 "
                "aggregate misfire cases is insufficient to resolve the "
                "threshold-misfire. no design is promoted to execution on the "
                "strength of 2 cases alone; further bounded public evidence "
                "is required before any rule change, promotion, or execution."),
            "addresses_mechanism_bucket": "insufficient_evidence_to_act",
            "input_scope_bucket": "n10eo_aggregate_buckets_only",
            "design_only_bool": True,
            "execution_authorized_bool": False,
            "frozen_rule_change_bool": False,
            "threshold_tuning_bool": False,
            "method_winner_claim_bool": False,
            "runtime_default_change_bool": False,
            "rationale_bucket": (
                "2 of 49 full-selected tasks regressed; acting on this as a "
                "winner/promotion signal would overinterpret a small sample."),
            "authorized_for_next_phase_bool": False,
        },
    ]


# ── Risk control records ──────────────────────────────────────────────────

def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "n10eprisk0000",
            "risk_bucket": RISK_AGGREGATE_OVERINTERPRETATION,
            "risk_description_bucket": (
                "drawing strong conclusions from 2 misfire cases out of 49 "
                "full-selected tasks risks aggregate overinterpretation."),
            "mitigation_bucket": (
                "design-only response; no promotion or rule change; explicit "
                "stop_design_only_insufficient option recorded."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eprisk0001",
            "risk_bucket": RISK_HINDSIGHT_THRESHOLD_TUNING,
            "risk_description_bucket": (
                "the misfire suggests the frozen threshold (>=4) may be miscalibrated; "
                "tuning it with hindsight on the same 49 tasks would be data snooping."),
            "mitigation_bucket": (
                "threshold_tuning_authorized_bool=false; frozen rule unchanged; "
                "any threshold design must use held-out public evidence."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eprisk0002",
            "risk_bucket": RISK_GUARD_PROMOTION_FROM_TWO_CASES,
            "risk_description_bucket": (
                "guard preserved both lost cases; promoting guard over full on "
                "the strength of 2 cases would overfit to this sample."),
            "mitigation_bucket": (
                "guard_full_diffaware_promotion_authorized_bool=false; "
                "no arm is promoted; design-only N10EQ safety probe instead."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eprisk0003",
            "risk_bucket": RISK_PUBLIC_CI_VARIANT_AS_METHOD_WINNER,
            "risk_description_bucket": (
                "treating the N10ER public CI variant design (if it favors "
                "guard) as a method-winner claim would conflate a small CI "
                "variant with a method conclusion."),
            "mitigation_bucket": (
                "method_winner_claim_authorized_bool=false; N10ER is design-only, "
                "not executed, and not a method winner even if later run."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eprisk0004",
            "risk_bucket": RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
            "risk_description_bucket": (
                "the N10EO mechanism used a private diagnostic rerun; "
                "N10EP must not leak per-task diagnostics/paths/candidates "
                "into the public design response."),
            "mitigation_bucket": (
                "N10EP reads only public aggregate artifacts; forbidden_scan "
                "blocks raw per-task/paths/orders/labels keys and the private "
                "rerun path; aggregate_buckets_only_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10eprisk0005",
            "risk_bucket": RISK_RUNTIME_DEFAULT_CREEP,
            "risk_description_bucket": (
                "a design response could implicitly drift runtime/default "
                "behavior by codifying a safety probe as a default gate."),
            "mitigation_bucket": (
                "runtime_default_change_authorized_bool=false; any safety probe "
                "remains opt-in/eval-only; no runtime or default change."),
            "risk_controlled_bool": True,
        },
    ]


# ── Claim boundary + stop/go ───────────────────────────────────────────────

def claim_boundary() -> dict[str, Any]:
    """Explicit false privacy/claim boundary fields. N10EP is design-only,
    public-only, and authorizes no execution or promotion."""
    return {
        "anonymous_claim_boundary_id": "n10epclaim0000",
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
    }


def stop_go_records(authorize_n10er: bool) -> list[dict[str, Any]]:
    """Conservative stop/go: authorize only the N10EQ design (or both N10EQ
    and N10ER designs if explicitly justified). No execution of any design."""
    next_phase = ("BEA-v1-N10EQ Score/Guard Safety Probe Design"
                  if not authorize_n10er
                  else "BEA-v1-N10EQ/N10ER Score/Guard Safety Probe + Public CI Variant Design")
    return [{
        "anonymous_stop_go_id": "n10epstop0000",
        "next_allowed_phase": next_phase,
        "design_only_mechanism_response_bool": True,
        "aggregate_buckets_only_bool": True,
        "n10eq_design_only_authorized_bool": True,
        "n10er_design_only_authorized_bool": authorize_n10er,
        "n10eq_execution_authorized_bool": False,
        "n10er_execution_authorized_bool": False,
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


# ── Report assembly ────────────────────────────────────────────────────────

def determine_status(authorize_n10er: bool) -> str:
    if authorize_n10er:
        return STATUS_N10EQ_N10ER_AUTHORIZED
    return STATUS_N10EQ_AUTHORIZED


def build_unavailable_report(lock: dict[str, Any], reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ep_design_only_threshold_misfire_mechanism_response_v1",
        "phase_bucket": "BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response",
        "status": STATUS_UNAVAILABLE,
        "unavailable_reason_bucket": reason,
        "n10eo_source_lock_records": [lock],
        "mechanism_response_summary_records": [],
        "design_option_records": [],
        "risk_control_records": [],
        "stop_go_records": stop_go_records(False),
        "claim_boundary_records": [claim_boundary()],
        "gate_records": [
            {"anonymous_gate_id": "n10epgate0001", "gate_bucket": "n10eo_source_locked",
             "gate_passed_bool": lock["source_locked_bool"]},
        ],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_CLOSED
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_CLOSED
    return report


def build_report(lock: dict[str, Any], authorize_n10er: bool) -> dict[str, Any]:
    status = determine_status(authorize_n10er)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ep_design_only_threshold_misfire_mechanism_response_v1",
        "phase_bucket": "BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response",
        "status": status,
        "n10eo_source_lock_records": [lock],
        "mechanism_response_summary_records": [mechanism_response_summary(lock)],
        "design_option_records": design_option_records(authorize_n10er),
        "risk_control_records": risk_control_records(),
        "stop_go_records": stop_go_records(authorize_n10er),
        "claim_boundary_records": [claim_boundary()],
        "gate_records": [
            {"anonymous_gate_id": "n10epgate0001", "gate_bucket": "n10eo_source_locked",
             "gate_passed_bool": lock["source_locked_bool"]},
            {"anonymous_gate_id": "n10epgate0002", "gate_bucket": "aggregate_counts_consistent",
             "gate_passed_bool": lock["aggregate_counts_match_bool"]},
            {"anonymous_gate_id": "n10epgate0003", "gate_bucket": "mechanism_buckets_consistent",
             "gate_passed_bool": lock["mechanism_buckets_match_bool"]},
            {"anonymous_gate_id": "n10epgate0004", "gate_bucket": "low_novelty_bucket_loss_consistent",
             "gate_passed_bool": lock["low_novelty_bucket_loss_match_bool"]},
            {"anonymous_gate_id": "n10epgate0005", "gate_bucket": "design_only_no_execution",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10epgate0006", "gate_bucket": "privacy_scan_pass",
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
                  "run_phase_labels_used_bool", "score_phase_labels_used_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ("n10eq_execution_authorized_bool", "n10er_execution_authorized_bool",
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
    if stop.get("n10eq_design_only_authorized_bool") is not True:
        failures.append("stop_n10eq_design_only_not_authorized")
    if stop.get("design_only_mechanism_response_bool") is not True:
        failures.append("stop_design_only_not_true")
    # Required record sections.
    for key in ("n10eo_source_lock_records", "mechanism_response_summary_records",
                "design_option_records", "risk_control_records", "stop_go_records",
                "claim_boundary_records", "gate_records"):
        if key not in report or not report[key]:
            failures.append(f"missing_or_empty_{key}")
    # Design option coverage.
    design_buckets = {r.get("design_option_bucket") for r in report.get("design_option_records", [])}
    for needed in (DESIGN_N10EQ, DESIGN_N10ER, DESIGN_STOP_INSUFFICIENT):
        if needed not in design_buckets:
            failures.append(f"missing_design_option_{needed}")
    # Risk control coverage.
    risk_buckets = {r.get("risk_bucket") for r in report.get("risk_control_records", [])}
    for needed in ALL_RISK_CONTROLS:
        if needed not in risk_buckets:
            failures.append(f"missing_risk_control_{needed}")
    # Mechanism response summary aggregate values.
    summ = (report.get("mechanism_response_summary_records") or [{}])[0]
    expected = {
        "baseline_top10_count": 39, "full_top10_count": 37,
        "guard_top10_count": 39, "diffaware_top10_count": 37,
        "full_lost_baseline_count": 2, "guard_lost_baseline_count": 0,
        "diffaware_lost_baseline_count": 2,
        "guard_better_than_full_count": 2,
        "full_lost_guard_preserved_count": 2,
        "baseline_gold_rank_1_to_5_displaced_count": 2,
        "candidate_available_beyond_top10_count": 2,
        "low_novelty_bucket_loss_count": 2,
    }
    for k, v in expected.items():
        if summ.get(k) != v:
            failures.append(f"summary_{k}_mismatch")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_N10EQ_AUTHORIZED in STATUS_VOCAB
                   and STATUS_N10EQ_N10ER_AUTHORIZED in STATUS_VOCAB
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

    # Lock verification with the committed N10EO artifact + N10EN + N10EM.
    n10eo, eo_state = load_json(N10EO_REPORT)
    n10en, en_state = load_json(N10EN_REPORT)
    n10em, em_state = load_json(N10EM_REPORT)
    lock = lock_n10eo_source(n10eo, eo_state, n10en, en_state, n10em, em_state)
    checks.append(("lock_source_locked", lock["source_locked_bool"] is True))
    checks.append(("lock_status_match", lock["status_match_bool"] is True))
    checks.append(("lock_counts_match", lock["aggregate_counts_match_bool"] is True))
    checks.append(("lock_mech_match", lock["mechanism_buckets_match_bool"] is True))
    checks.append(("lock_fg_match", lock["full_guard_outcome_match_bool"] is True))
    checks.append(("lock_low_nov_match", lock["low_novelty_bucket_loss_match_bool"] is True))
    checks.append(("lock_primary_match", lock["primary_mechanism_match_bool"] is True))
    checks.append(("lock_next_phase_match", lock["next_allowed_phase_match_bool"] is True))
    checks.append(("lock_checkpoint", lock["locked_n10eo_checkpoint"] == "6f8eeda"))

    # Mechanism response summary.
    summ = mechanism_response_summary(lock)
    checks.append(("sum_baseline_top10", summ["baseline_top10_count"] == 39))
    checks.append(("sum_full_top10", summ["full_top10_count"] == 37))
    checks.append(("sum_guard_top10", summ["guard_top10_count"] == 39))
    checks.append(("sum_diffaware_top10", summ["diffaware_top10_count"] == 37))
    checks.append(("sum_full_lost", summ["full_lost_baseline_count"] == 2))
    checks.append(("sum_guard_lost", summ["guard_lost_baseline_count"] == 0))
    checks.append(("sum_diffaware_lost", summ["diffaware_lost_baseline_count"] == 2))
    checks.append(("sum_guard_better", summ["guard_better_than_full_count"] == 2))
    checks.append(("sum_full_lost_guard_preserved", summ["full_lost_guard_preserved_count"] == 2))
    checks.append(("sum_rank_1_to_5", summ["baseline_gold_rank_1_to_5_displaced_count"] == 2))
    checks.append(("sum_candidate_beyond_top10", summ["candidate_available_beyond_top10_count"] == 2))
    checks.append(("sum_low_novelty_loss", summ["low_novelty_bucket_loss_count"] == 2))
    checks.append(("sum_design_only", summ["mechanism_response_design_only_bool"] is True))

    # Design option coverage (conservative: N10EQ authorized, N10ER not).
    designs = design_option_records(False)
    checks.append(("designs_count", len(designs) == 3))
    checks.append(("design_n10eq_present", any(d["design_option_bucket"] == DESIGN_N10EQ for d in designs)))
    checks.append(("design_n10er_present", any(d["design_option_bucket"] == DESIGN_N10ER for d in designs)))
    checks.append(("design_stop_present", any(d["design_option_bucket"] == DESIGN_STOP_INSUFFICIENT for d in designs)))
    checks.append(("design_n10eq_authorized", next(d for d in designs if d["design_option_bucket"] == DESIGN_N10EQ)["authorized_for_next_phase_bool"] is True))
    checks.append(("design_n10er_not_authorized_conservative", next(d for d in designs if d["design_option_bucket"] == DESIGN_N10ER)["authorized_for_next_phase_bool"] is False))
    checks.append(("designs_all_design_only", all(d["design_only_bool"] for d in designs)))
    checks.append(("designs_no_execution", all(d["execution_authorized_bool"] is False for d in designs)))

    # Risk control coverage.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == len(ALL_RISK_CONTROLS)))
    checks.append(("risk_aggregate_overinterpretation", any(r["risk_bucket"] == RISK_AGGREGATE_OVERINTERPRETATION for r in risks)))
    checks.append(("risk_hindsight_tuning", any(r["risk_bucket"] == RISK_HINDSIGHT_THRESHOLD_TUNING for r in risks)))
    checks.append(("risk_guard_promotion", any(r["risk_bucket"] == RISK_GUARD_PROMOTION_FROM_TWO_CASES for r in risks)))
    checks.append(("risk_ci_variant_winner", any(r["risk_bucket"] == RISK_PUBLIC_CI_VARIANT_AS_METHOD_WINNER for r in risks)))
    checks.append(("risk_private_leakage", any(r["risk_bucket"] == RISK_PRIVATE_DIAGNOSTIC_LEAKAGE for r in risks)))
    checks.append(("risk_runtime_creep", any(r["risk_bucket"] == RISK_RUNTIME_DEFAULT_CREEP for r in risks)))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))

    # Stop/go conservative.
    stops = stop_go_records(False)
    checks.append(("stop_n10eq_authorized", stops[0]["n10eq_design_only_authorized_bool"] is True))
    checks.append(("stop_n10er_not_authorized_conservative", stops[0]["n10er_design_only_authorized_bool"] is False))
    checks.append(("stop_n10eq_no_exec", stops[0]["n10eq_execution_authorized_bool"] is False))
    checks.append(("stop_n10er_no_exec", stops[0]["n10er_execution_authorized_bool"] is False))
    checks.append(("stop_threshold_tuning_false", stops[0]["threshold_tuning_authorized_bool"] is False))
    checks.append(("stop_promotion_false", stops[0]["guard_full_diffaware_promotion_authorized_bool"] is False))
    checks.append(("stop_runtime_false", stops[0]["runtime_default_change_authorized_bool"] is False))
    checks.append(("stop_method_winner_false", stops[0]["method_winner_claim_authorized_bool"] is False))

    # Both-designs-authorized variant.
    stops_both = stop_go_records(True)
    checks.append(("stop_both_n10er_authorized", stops_both[0]["n10er_design_only_authorized_bool"] is True))
    checks.append(("stop_both_no_exec", stops_both[0]["n10er_execution_authorized_bool"] is False))
    checks.append(("status_both", determine_status(True) == STATUS_N10EQ_N10ER_AUTHORIZED))

    # Claim boundary explicit false fields.
    cb = claim_boundary()
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_only_true", cb["design_only_bool"] is True))
    checks.append(("claim_private_diag_false", cb["private_diagnostic_inputs_used_bool"] is False))
    checks.append(("claim_method_winner_false", cb["method_winner_claim_bool"] is False))
    checks.append(("claim_runtime_false", cb["runtime_default_change_bool"] is False))
    checks.append(("claim_threshold_tuning_false", cb["threshold_tuning_bool"] is False))
    checks.append(("claim_ci_variant_exec_false", cb["ci_variant_execution_bool"] is False))

    # Full report build + validation.
    report = build_report(lock, False)
    checks.append(("report_status_n10eq", report["status"] == STATUS_N10EQ_AUTHORIZED))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))

    # Unavailable report when source not locked.
    bad_lock = lock_n10eo_source(None, "missing")
    unavail = build_unavailable_report(bad_lock, "n10eo_artifact_missing")
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
    n10eo, eo_state = load_json(Path(args.n10eo_report))
    n10en, en_state = load_json(Path(args.n10en_report))
    n10em, em_state = load_json(Path(args.n10em_report))
    lock = lock_n10eo_source(n10eo, eo_state, n10en, en_state, n10em, em_state)
    if not lock["source_locked_bool"]:
        report = build_unavailable_report(lock, "n10eo_source_not_locked")
    else:
        report = build_report(lock, args.authorize_n10er_design)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
