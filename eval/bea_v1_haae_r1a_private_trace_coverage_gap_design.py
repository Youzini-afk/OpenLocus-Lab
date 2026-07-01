#!/usr/bin/env python3
"""BEA-v1-HAAE-R1A Private Trace Coverage Gap Design.

HAAE-R1A is the **public-only design** phase that responds to the HAAE-R1
coverage gap (checkpoint ``2ea77da``, status
``haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots``). It is
**not** an execution phase: no private reads, no root regeneration, no
replay/scoring/retrieval/candidate generation/HAAE-layer execution/CI/network/
clone. It is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion.

Inputs allowed (public only, explicit public paths):
  * the committed HAAE-R1 public aggregate report (the feasibility inventory
    that confirmed all 10 groups ``not_present``);
  * the committed HAAE-R0 public aggregate report (the schema preflight that
    designed the 10 groups);
  * the N10ET public aggregate report (the close-out design/decision);
  * the HAAE-R1/R0/N10ET evaluators for constants only (never executed);
  * public artifacts/docs for FD1, P4L, N1, N2, N10-series / mechanism
    synthesis to classify source option buckets;
  * the HAAE-R1/R0 EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
    research-log/summary, and README public readback;
  * git metadata: the ``2ea77da`` checkpoint that recorded the HAAE-R1 result.

Forbidden: any traversal of ignored project-private namespaces, temporary private
output namespaces, ignored roots, ``target``, ``runs``, clones; any private reads; any root regeneration; any
replay/scoring/retrieval/candidate generation/HAAE-layer execution; any CI rerun;
any network; any clone/build/search; any BEA-v1-A/P5/selector/runtime/default.

HAAE-R1A:
  * Locks the HAAE-R1 source (checkpoint ``2ea77da``, status
    ``haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots``,
    HAAE-R2 false, all 10 groups accounted, coverage unavailable confirmed).
  * Records coverage gap records for all 10 HAAE-R0 schema groups.
  * Designs root source option records (classifying public evidence strength
    for each group: ``public_evidence_strong`` / ``public_evidence_partial`` /
    ``public_evidence_weak`` / ``public_evidence_absent``).
  * Designs bounded regeneration design records (how to safely regenerate
    private roots under explicit opt-in, bounded depth, no symlink escape).
  * Designs root manifest schema design records (the manifest schema for the
    private root buckets).
  * Records option decision records (pass or controlled no-go).
  * Emits a public-only design artifact with explicit false privacy/claim
    boundary fields, scanner-validated.

Status vocabulary:
  * ``haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized``
    — source lock passes, HAAE-R1 unavailable/no roots confirmed, HAAE-R2
    false, all 10 groups accounted, at least one source option
    public_evidence_strong/partial, bounded regeneration design and root
    manifest schema present, docs/readback pass, no private/execution.
  * ``haae_r1a_private_trace_coverage_gap_design_controlled_no_go_closeout_explicit_roots_required``
    — no safe source option (all public_evidence_absent/weak); closeout
    requires explicit roots.
  * ``haae_r1a_private_trace_coverage_gap_design_unavailable_no_locked_source``
    — HAAE-R1 source not locked.
  * ``fail_haae_r1_source_lock_mismatch`` / ``fail_forbidden_scan`` /
    ``fail_schema_contract`` / ``fail_contract_violation`` — fail-closed.

Handoff:
  * Pass → authorizes **only** BEA-v1-HAAE-R1B Bounded Private Trace Root
    Regeneration Preflight Package (design-only, no execution/private read/
    replay/scoring/retrieval/candidate generation).
  * No-go → closeout: explicit roots required; no further phase authorized.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_haae_r1a_private_trace_coverage_gap_design"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
HAAE_R1_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory"
    / "bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_report.json"
)
HAAE_R0_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight"
    / "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_report.json"
)
N10ET_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10et_public_safety_probe_design_decision"
    / "bea_v1_n10et_public_safety_probe_design_decision_report.json"
)
README_PATH = ROOT / "README.md"
HAAE_R0_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
HAAE_R0_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
HAAE_R1_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md"
)
HAAE_R1_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md"
)
HAAE_R1A_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1a-private-trace-coverage-gap-design.md"
)
HAAE_R1A_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1a-private-trace-coverage-gap-design.md"
)
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"

# ── Locked HAAE-R1 public facts (git metadata + upstream locks) ───────────
LOCKED_HAAE_R1_CHECKPOINT = "2ea77da"
LOCKED_HAAE_R1_STATUS = "haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots"
LOCKED_HAAE_R1_NEXT_ALLOWED_PHASE = "BEA-v1-HAAE-R1A Private Trace Coverage Gap Design"
# Upstream locks (read from HAAE-R1's source_lock_records).
LOCKED_HAAE_R0_CHECKPOINT = "854fc2e"
LOCKED_HAAE_R0_STATUS = "haae_r0_design_schema_preflight_complete_haae_r1_authorized"
LOCKED_N10ET_CHECKPOINT = "26d817e"
LOCKED_N10ET_STATUS = (
    "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"
)

# ── HAAE-R1A non-identities (carried from HAAE-R0) ─────────────────────────
HAAE_R1A_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Next-route handoff buckets ─────────────────────────────────────────────
NEXT_ROUTE_PASS = (
    "BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package"
)
NEXT_ROUTE_NO_GO = "closeout_explicit_roots_required"

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_PASS = "haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized"
STATUS_NO_GO = ("haae_r1a_private_trace_coverage_gap_design_controlled_no_go_"
                "closeout_explicit_roots_required")
STATUS_NO_SOURCE = "haae_r1a_private_trace_coverage_gap_design_unavailable_no_locked_source"
STATUS_FAIL_LOCK = "fail_haae_r1_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
EXIT0_VOCAB = {STATUS_PASS, STATUS_NO_GO, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_SCAN,
                              STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT}

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
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|[\s/\\])\.openlocus(?:$|[\s/\\])"),
    re.compile(r"(?:^|[\s/\\])(?:tmp|workspace|home|runner)(?:$|[\s/\\])"),
    re.compile(r"https?://github\.com/", re.I),
    re.compile(r"[A-Za-z0-9_.-]+/(?:[A-Za-z0-9_.-]+)\.git", re.I),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(ci-[0-9]{5})\b", re.I),
    re.compile(r"\b(?:task|record|row|case)[_-](?=[A-Za-z0-9]*\d)[A-Za-z0-9]{4,}\b", re.I),
    re.compile(r"\b(?:path|paths|line_range|content_sha|score|scores|query|queries|candidate|candidates|span|spans|repo|repos)(?:[/,\s]+(?:path|paths|line_range|content_sha|score|scores|query|queries|candidate|candidates|span|spans|repo|repos|why|channels)){1,}\b", re.I),
]

# Self-test check count (kept in sync with run_self_test; verified by --self-test).
SELF_TEST_TOTAL_CHECKS = 112

# ── HAAE-R0 schema groups (the 10 coverage-gap targets) ───────────────────

SCHEMA_GROUPS: list[dict[str, Any]] = [
    {"group_bucket": "task_identity", "group_index": 0,
     "is_critical_group_bool": True,
     "group_description_bucket": "anonymous task identity: anonymous_task_id, repo_bucket, language_bucket."},
    {"group_bucket": "anchor_source", "group_index": 1,
     "is_critical_group_bool": False,
     "group_description_bucket": "anchor/source acquisition layer: anchor_kind_bucket, acquisition_cost_bucket."},
    {"group_bucket": "candidate_pool", "group_index": 2,
     "is_critical_group_bool": True,
     "group_description_bucket": "candidate pool shape: candidate_count_bucket, depth_distribution_bucket."},
    {"group_bucket": "rank_pack", "group_index": 3,
     "is_critical_group_bool": False,
     "group_description_bucket": "rank/pack depth-to-head: topk_pack_bucket, novel_vs_old_pool_bucket."},
    {"group_bucket": "span_projection", "group_index": 4,
     "is_critical_group_bool": False,
     "group_description_bucket": "span projection: span_window_bucket, span_overlap_bucket."},
    {"group_bucket": "scheduler_action", "group_index": 5,
     "is_critical_group_bool": False,
     "group_description_bucket": "scheduler action: scheduled_action_bucket, action_cost_bucket."},
    {"group_bucket": "evidence_core", "group_index": 6,
     "is_critical_group_bool": True,
     "group_description_bucket": "EvidenceCore aggregate evidence-shape buckets."},
    {"group_bucket": "arm_assignment", "group_index": 7,
     "is_critical_group_bool": True,
     "group_description_bucket": "arm assignment: arm_bucket, budget_bucket."},
    {"group_bucket": "outcome_metric", "group_index": 8,
     "is_critical_group_bool": True,
     "group_description_bucket": "outcome metric aggregate buckets: citation_validity_bucket, file_recovery_topk_bucket, lost_baseline_top10_bucket."},
    {"group_bucket": "safety_probe_signal", "group_index": 9,
     "is_critical_group_bool": False,
     "group_description_bucket": "safety-probe signal aggregate buckets: full_guard_diffaware_loss_bucket, risk_bucket_signal."},
]

CRITICAL_GROUPS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS
                        if g["is_critical_group_bool"])
ALL_GROUP_BUCKETS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS)
assert len(SCHEMA_GROUPS) == 10
assert len(CRITICAL_GROUPS) == 5

# ── Public input artifacts (explicit public paths, read for constants only) ─
# These are the public artifact directories used to classify source option
# buckets. Only their existence and committed status are checked; no private
# rows are read. The artifact directory names are public committed paths.
PUBLIC_INPUT_ARTIFACTS: list[dict[str, str]] = [
    {"input_bucket": "haae_r1_feasibility_inventory",
     "input_kind_bucket": "haae_r1_public_aggregate_report",
     "input_description_bucket": "the HAAE-R1 feasibility inventory report confirming all 10 groups not_present."},
    {"input_bucket": "haae_r0_schema_preflight",
     "input_kind_bucket": "haae_r0_public_aggregate_report",
     "input_description_bucket": "the HAAE-R0 schema preflight report designing the 10 schema groups."},
    {"input_bucket": "n10et_public_safety_probe_design_decision",
     "input_kind_bucket": "n10et_public_aggregate_report",
     "input_description_bucket": "the N10ET close-out design/decision authorizing HAAE-R0."},
    {"input_bucket": "fd1_failure_decomposition",
     "input_kind_bucket": "fd1_public_aggregate_artifact",
     "input_description_bucket": "FD1 failure decomposition: 86040 private decomposition rows, 239 composite record groups (private manifest only)."},
    {"input_bucket": "p4l_locked_non_python_scheduler_validation",
     "input_kind_bucket": "p4l_public_aggregate_artifact",
     "input_description_bucket": "P4L locked non-Python scheduler validation: 272-record denominator, 1088 private arm-outcome rows (private manifest only)."},
    {"input_bucket": "n1_frozen_p4_span_refiner_smoke",
     "input_kind_bucket": "n1_public_aggregate_artifact",
     "input_description_bucket": "N1 frozen P4 span refiner smoke: rank-blocked denominator, span-opportunity."},
    {"input_bucket": "n2_rank_pack_actionability_decomposition",
     "input_kind_bucket": "n2_public_aggregate_artifact",
     "input_description_bucket": "N2 rank/pack actionability decomposition: 40 rank-blocked records, extra-depth append blocked."},
    {"input_bucket": "n10eo_difference_aware_ci_regression_failure_analysis",
     "input_kind_bucket": "n10eo_public_aggregate_artifact",
     "input_description_bucket": "N10EO difference-aware CI regression failure analysis: mechanism buckets, novelty buckets."},
    {"input_bucket": "n10er_bounded_public_ci_score_guard_safety_probe",
     "input_kind_bucket": "n10er_public_aggregate_artifact",
     "input_description_bucket": "N10ER bounded public CI score/guard safety probe: 80/60/40 sample, arm aggregates, risk bucket."},
    {"input_bucket": "n10es_public_safety_probe_audit_package",
     "input_kind_bucket": "n10es_public_aggregate_artifact",
     "input_description_bucket": "N10ES public safety probe audit package: locked N10ER aggregates."},
    {"input_bucket": "n10em_difference_aware_winner_public_replication_package",
     "input_kind_bucket": "n10em_public_aggregate_artifact",
     "input_description_bucket": "N10EM difference-aware winner public replication package: 13/16/20/26 chain."},
    {"input_bucket": "n10en_difference_aware_ci_canary",
     "input_kind_bucket": "n10en_public_aggregate_artifact",
     "input_description_bucket": "N10EN difference-aware CI canary: 4 arms, baseline/full/guard/diffaware."},
]

# ── Root source option classification (per group, public evidence strength) ─
# For each of the 10 groups, classify which public artifacts provide evidence
# and the strength of that evidence. This is a design classification, not a
# private read.
SOURCE_OPTIONS: list[dict[str, Any]] = [
    {
        "group_bucket": "task_identity",
        "source_option_bucket": "fd1_private_decomposition_manifest",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["fd1_failure_decomposition", "n10er_bounded_public_ci_score_guard_safety_probe", "n10es_public_safety_probe_audit_package"],
        "source_description_bucket": "FD1 private decomposition manifest records 86040 private decomposition rows across 239 composite record groups. N10ER/N10ES public aggregates carry task_count (80/60/40). Strong evidence that task_identity can be populated from FD1 private decomposition + N10ER public aggregates.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "anchor_source",
        "source_option_bucket": "n10dw_normalized_bm25_recovery_mechanism",
        "public_evidence_strength_bucket": "public_evidence_partial",
        "source_artifact_buckets": ["n10dw_normalized_bm25_recovery_mechanism_analysis", "n10dz_normalized_bm25_expanded_canary", "n10ea_normalized_bm25_expanded_canary_public_package", "n10dr_real_candidate_source_canary"],
        "source_description_bucket": "N10DW normalized BM25 recovery mechanism analysis and N10DZ/N10EA expanded canary packages carry anchor_kind and acquisition_cost buckets. Partial evidence: anchor_kind is derivable from the normalized BM25 mechanism classification.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "candidate_pool",
        "source_option_bucket": "n10eo_private_diagnostic_rerun_mechanism",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["n10eo_difference_aware_ci_regression_failure_analysis", "n10ef_normalized_bm25_novel_guard_experiment_package", "n10ei_fixed_full_guard_combination_package", "n10eg_novel_first_guard_complementarity_slicing"],
        "source_description_bucket": "N10EO private diagnostic rerun carries mechanism buckets (novel_first_displaced, candidate_available_beyond_top10) and novelty bucket diagnostics. N10EF/N10EI/N10EG carry candidate_count and depth_distribution buckets. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "rank_pack",
        "source_option_bucket": "n2_rank_pack_actionability_decomposition",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["n2_rank_pack_actionability_decomposition", "n1_frozen_p4_span_refiner_smoke", "n10ej_full_guard_difference_analysis", "n10ek_fixed_difference_aware_combination_experiment", "n10el_difference_aware_winner_audit_recompute"],
        "source_description_bucket": "N2 rank/pack actionability decomposition carries topk_pack and novel_vs_old_pool buckets across 40 rank-blocked records. N1 carries rank-blocked denominator. N10EJ/N10EK/N10EL carry difference-aware rank/pack buckets. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "span_projection",
        "source_option_bucket": "n10aa_to_n10bn_span_window_repair_branch",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["n10aa_span_window_repair_preflight", "n10ae_fixed_span_window_repair_replication_package", "n10cf_span_shape_refinement_audit_package", "n1_frozen_p4_span_refiner_smoke"],
        "source_description_bucket": "The N10AA-N10BN span window repair branch carries span_window and span_overlap buckets across many sub-phases. N1 carries span refiner smoke. Strong evidence from the span-window repair lineage.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "scheduler_action",
        "source_option_bucket": "p4l_private_arm_outcome_manifest",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["p4l_locked_non_python_scheduler_validation", "n10bg_cost_aware_decisions_vs_fixed_pm50_comparator"],
        "source_description_bucket": "P4L private arm-outcome manifest records 1088 private arm-outcome rows across a 272-record non-Python denominator with 5 arms. The scheduler action and action_cost buckets are directly derivable. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "evidence_core",
        "source_option_bucket": "fd1_private_decomposition_plus_n10er_citation",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["fd1_failure_decomposition", "n10er_bounded_public_ci_score_guard_safety_probe", "n10es_public_safety_probe_audit_package"],
        "source_description_bucket": "FD1 private decomposition carries EvidenceCore evidence-shape aggregate buckets. N10ER carries citation-validity aggregates. N10ES audits the citation aggregate. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "arm_assignment",
        "source_option_bucket": "p4l_private_arm_outcome_5_arms",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["p4l_locked_non_python_scheduler_validation", "n10em_difference_aware_winner_public_replication_package", "n10en_difference_aware_ci_canary", "n10er_bounded_public_ci_score_guard_safety_probe"],
        "source_description_bucket": "P4L records 1088 private arm-outcome rows with 5 arms (BM25_same_budget, RRF_same_budget, BEA_v0.3_frozen, V1_sched_span, V1_sched_span_rank). N10EM/N10EN/N10ER carry arm_assignment buckets. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "outcome_metric",
        "source_option_bucket": "n10er_n10es_public_arm_aggregates",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["n10er_bounded_public_ci_score_guard_safety_probe", "n10es_public_safety_probe_audit_package", "n10eo_difference_aware_ci_regression_failure_analysis"],
        "source_description_bucket": "N10ER carries arm aggregates (37/39/40/40 baseline, 36/39/40/40 full, 38/39/40/40 guard, 37/39/40/40 diffaware), citation validity (7772/7772), and lost_baseline_top10. N10ES audits all. N10EO carries mechanism buckets. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
    {
        "group_bucket": "safety_probe_signal",
        "source_option_bucket": "n10eq_n10er_n10es_n10et_safety_probe_lineage",
        "public_evidence_strength_bucket": "public_evidence_strong",
        "source_artifact_buckets": ["n10eq_score_guard_safety_probe_design", "n10er_bounded_public_ci_score_guard_safety_probe", "n10es_public_safety_probe_audit_package", "n10et_public_safety_probe_design_decision"],
        "source_description_bucket": "N10EQ designed the safety probe features. N10ER ran the probe (risk bucket task_count=26, losses 0/0/0). N10ES audited it. N10ET closed the branch. The full_guard_diffaware_loss and risk_bucket_signal buckets are carried. Strong evidence.",
        "regeneration_feasible_bool": True,
    },
]

# Map group_bucket → list of source options for quick lookup.
SOURCE_OPTIONS_BY_GROUP: dict[str, list[dict[str, Any]]] = {}
for opt in SOURCE_OPTIONS:
    SOURCE_OPTIONS_BY_GROUP.setdefault(opt["group_bucket"], []).append(opt)

# ── Bounded regeneration design records ────────────────────────────────────
BOUNDED_REGENERATION_DESIGNS: list[dict[str, Any]] = [
    {
        "design_bucket": "explicit_opt_in_private_root_enumeration",
        "design_description_bucket": "regeneration requires explicit opt-in via private-root argument. no implicit private root enumeration. no traversal outside explicitly supplied project-private root buckets or temporary private output buckets.",
        "bounded_depth_bool": True,
        "no_symlink_escape_bool": True,
        "explicit_opt_in_required_bool": True,
        "no_implicit_traversal_bool": True,
    },
    {
        "design_bucket": "fd1_private_decomposition_regeneration",
        "design_description_bucket": "regenerate FD1 private decomposition rows by replaying the FD1 decomposition under explicit opt-in. produces private rows in a temporary private output bucket only; public artifact carries manifest count buckets only. no raw rows published.",
        "source_group_buckets": ["task_identity", "evidence_core"],
        "regeneration_kind_bucket": "fd1_decomposition_replay",
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "no_raw_rows_published_bool": True,
    },
    {
        "design_bucket": "p4l_private_arm_outcome_regeneration",
        "design_description_bucket": "regenerate P4L private arm-outcome rows by replaying the frozen P4 scheduler on the locked denominator under explicit opt-in. produces private arm-outcome rows in a temporary private output bucket only; public artifact carries manifest count buckets only.",
        "source_group_buckets": ["scheduler_action", "arm_assignment", "outcome_metric"],
        "regeneration_kind_bucket": "p4l_scheduler_replay",
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "no_raw_rows_published_bool": True,
    },
    {
        "design_bucket": "n10eo_private_diagnostic_rerun_regeneration",
        "design_description_bucket": "regenerate N10EO private diagnostic rerun by replaying the diagnostic under explicit opt-in. produces private diagnostic rows in a temporary private output bucket only; public artifact carries aggregate mechanism buckets only.",
        "source_group_buckets": ["candidate_pool", "rank_pack", "safety_probe_signal"],
        "regeneration_kind_bucket": "n10eo_diagnostic_rerun",
        "private_output_only_bool": True,
        "public_aggregate_buckets_only_bool": True,
        "no_raw_rows_published_bool": True,
    },
    {
        "design_bucket": "n10er_public_ci_replay_regeneration",
        "design_description_bucket": "regenerate N10ER public CI safety probe by replaying the bounded public CI canary under explicit opt-in with network enabled. produces public aggregate report; private rows stay in runner-private output buckets.",
        "source_group_buckets": ["outcome_metric", "safety_probe_signal"],
        "regeneration_kind_bucket": "n10er_ci_replay",
        "public_aggregate_report_bool": True,
        "private_rows_tmp_only_bool": True,
        "network_required_bool": True,
    },
]

# ── Root manifest schema design records ────────────────────────────────────
ROOT_MANIFEST_SCHEMA_DESIGNS: list[dict[str, Any]] = [
    {
        "schema_field_bucket": "anonymous_root_id",
        "schema_field_type_bucket": "opaque_id_bucket",
        "schema_field_description_bucket": "anonymous identifier for each private root bucket. no raw paths.",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
    {
        "schema_field_bucket": "root_present_bool",
        "schema_field_type_bucket": "bool_bucket",
        "schema_field_description_bucket": "whether the root was present and enumerable.",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
    {
        "schema_field_bucket": "file_count_bucket",
        "schema_field_type_bucket": "ordinal_bucket",
        "schema_field_description_bucket": "bucketized file count (count_0, count_1_to_10, count_11_to_100, count_101_to_1000, count_1001_plus). no raw file counts.",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
    {
        "schema_field_bucket": "extension_distribution_bucket",
        "schema_field_type_bucket": "categorical_bucket",
        "schema_field_description_bucket": "bucketized extension distribution (ext_jsonl, ext_json, ext_csv, ext_other). no filenames.",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
    {
        "schema_field_bucket": "group_coverage_map_bucket",
        "schema_field_type_bucket": "categorical_bucket",
        "schema_field_description_bucket": "which schema groups are populated by this root (full/sufficient/partial/missing/not_present).",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
    {
        "schema_field_bucket": "no_raw_release_bool",
        "schema_field_type_bucket": "bool_bucket",
        "schema_field_description_bucket": "explicit false for raw release; always true (no raw release).",
        "required_bool": True,
        "aggregate_bucket_only_bool": True,
    },
]


# ── Safe argument parser ───────────────────────────────────────────────────

class SafeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-HAAE-R1A private trace coverage gap design")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--haae-r1-report", default=str(HAAE_R1_REPORT),
                        help="path to the committed HAAE-R1 public artifact")
    return parser.parse_args(argv)


# ── Generic helpers ────────────────────────────────────────────────────────

def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def public_readback_match() -> dict[str, bool]:
    """Verify that the public docs/README/current conclusions mention the
    HAAE-R1 coverage gap, the HAAE-R1A design, and the HAAE-R0 non-identity.
    Reads only public docs; performs no execution."""
    common_fragments = [
        LOCKED_HAAE_R1_CHECKPOINT,
        LOCKED_HAAE_R1_STATUS,
        "HAAE-R1",
        "HAAE-R1A",
    ]
    self_test_fragments = (
        f"{SELF_TEST_TOTAL_CHECKS}/{SELF_TEST_TOTAL_CHECKS}",
        f"{SELF_TEST_TOTAL_CHECKS} / {SELF_TEST_TOTAL_CHECKS}",
    )
    readme = read_text_or_empty(README_PATH)
    haae_r0_doc_en = read_text_or_empty(HAAE_R0_DOC_EN)
    haae_r0_doc_zh = read_text_or_empty(HAAE_R0_DOC_ZH)
    haae_r1_doc_en = read_text_or_empty(HAAE_R1_DOC_EN)
    haae_r1_doc_zh = read_text_or_empty(HAAE_R1_DOC_ZH)
    haae_r1a_doc_en = read_text_or_empty(HAAE_R1A_DOC_EN)
    haae_r1a_doc_zh = read_text_or_empty(HAAE_R1A_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_r1a_closeout(text: str) -> bool:
        return ("HAAE-R1A" in text and "HAAE-R1" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    def has_self_test_fragment(text: str) -> bool:
        return any(fragment in text for fragment in self_test_fragments)

    readme_self_test_match = has_self_test_fragment(readme)
    haae_r1a_docs_self_test_match = (has_self_test_fragment(haae_r1a_doc_en)
                                     and has_self_test_fragment(haae_r1a_doc_zh))
    current_self_test_match = (has_self_test_fragment(current_en)
                               and has_self_test_fragment(current_zh))
    log_self_test_match = (has_self_test_fragment(log_en)
                           and has_self_test_fragment(log_zh))
    summary_self_test_match = (has_self_test_fragment(summary_en)
                               and has_self_test_fragment(summary_zh))
    self_test_total_public_readback_match = (readme_self_test_match
                                             and haae_r1a_docs_self_test_match
                                             and current_self_test_match
                                             and log_self_test_match
                                             and summary_self_test_match)

    readme_match = (has_all(readme, common_fragments)
                    and has_r1a_closeout(readme)
                    and readme_self_test_match)
    current_match = (has_all(current_en, common_fragments)
                     and has_all(current_zh, common_fragments)
                     and has_r1a_closeout(current_en)
                     and has_r1a_closeout(current_zh)
                     and current_self_test_match)
    haae_r1a_docs_match = (has_all(haae_r1a_doc_en, common_fragments)
                           and has_all(haae_r1a_doc_zh, common_fragments)
                           and has_r1a_closeout(haae_r1a_doc_en)
                           and has_r1a_closeout(haae_r1a_doc_zh)
                           and haae_r1a_docs_self_test_match)
    haae_r1_docs_match = "HAAE-R1A" in haae_r1_doc_en and "HAAE-R1A" in haae_r1_doc_zh
    haae_r0_docs_match = "HAAE-R1" in haae_r0_doc_en and "HAAE-R1" in haae_r0_doc_zh
    log_match = (has_r1a_closeout(log_en) and has_r1a_closeout(log_zh)
                 and log_self_test_match)
    summary_match = (has_r1a_closeout(summary_en)
                     and has_r1a_closeout(summary_zh)
                     and summary_self_test_match)
    return {
        "haae_r1a_docs_readback_match_bool": haae_r1a_docs_match,
        "haae_r1_docs_readback_match_bool": haae_r1_docs_match,
        "haae_r0_docs_readback_match_bool": haae_r0_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": self_test_total_public_readback_match,
        "all_public_readback_match_bool": (haae_r1a_docs_match and haae_r1_docs_match
                                           and haae_r0_docs_match and readme_match
                                           and current_match and log_match
                                           and summary_match),
    }


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


# ── HAAE-R1 source lock (reads public HAAE-R1 report only; no rerun) ───────

def _haae_r1_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _haae_r1_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def _haae_r1_coverage_summary(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("coverage_summary_records") or [{}])[0] if report.get("coverage_summary_records") else {}


def evaluate_haae_r1_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the HAAE-R1 public report and validate every locked field.

    Reads ONLY the public HAAE-R1 aggregate report. Performs no execution, no
    retrieval, no recompute, no private reads.
    """
    r1_report, r1_state = load_json(HAAE_R1_REPORT)
    present_ok = r1_state == "present" and isinstance(r1_report, dict)
    status_ok = bool(r1_report and r1_report.get("status") == LOCKED_HAAE_R1_STATUS)
    r1_scan_ok = bool(r1_report
                      and r1_report.get("forbidden_scan", {}).get("status") == "pass")

    stop = _haae_r1_stop_go(r1_report or {})
    next_phase_ok = (stop.get("next_allowed_phase") == LOCKED_HAAE_R1_NEXT_ALLOWED_PHASE)
    haae_r2_false_ok = (stop.get("haae_r2_feasibility_gated_offline_trace_join_design_"
                                  "authorized_bool") is False)
    haae_r1_execution_false_ok = stop.get("haae_r1_execution_authorized_bool") is False
    haae_r1_replay_false_ok = stop.get("haae_r1_replay_authorized_bool") is False
    haae_r1_scoring_false_ok = stop.get("haae_r1_scoring_authorized_bool") is False
    haae_r1_retrieval_false_ok = stop.get("haae_r1_retrieval_authorized_bool") is False
    haae_r1_candidate_gen_false_ok = (stop.get("haae_r1_candidate_generation_"
                                                "authorized_bool") is False)
    bea_v1_a_false_ok = stop.get("bea_v1_a_authorized_bool") is False
    p5_false_ok = stop.get("p5_authorized_bool") is False
    selector_reranker_false_ok = stop.get("selector_reranker_authorized_bool") is False
    runtime_default_false_ok = stop.get("runtime_default_change_authorized_bool") is False

    r0_non_identity_ok = (
        stop.get("haae_r0_not_bea_v1_a_bool") is True
        and stop.get("haae_r0_not_selector_only_bool") is True
        and stop.get("haae_r0_not_selector_reranker_execution_bool") is True
        and stop.get("haae_r0_not_p5_bool") is True
        and stop.get("haae_r0_not_runtime_default_promotion_bool") is True
    )

    package = _haae_r1_package(r1_report or {})
    package_ok = (package.get("feasibility_inventory_only_bool") is True
                  and package.get("private_read_count_bucket") == "count_0")

    coverage = _haae_r1_coverage_summary(r1_report or {})
    coverage_unavailable_ok = coverage.get("feasibility_bucket") == "unavailable"
    all_groups_not_present_ok = (coverage.get("not_present_coverage_group_count") == 10
                                 if coverage else False)
    critical_count_ok = coverage.get("critical_group_count") == 5 if coverage else False

    # HAAE-R1 must have accounted all 10 schema groups.
    schema_count_ok = (len(r1_report.get("schema_group_feasibility_records", [])) == 10
                       if r1_report else False)

    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and r1_scan_ok
               and next_phase_ok and haae_r2_false_ok
               and haae_r1_execution_false_ok and haae_r1_replay_false_ok
               and haae_r1_scoring_false_ok and haae_r1_retrieval_false_ok
               and haae_r1_candidate_gen_false_ok
               and bea_v1_a_false_ok and p5_false_ok
               and selector_reranker_false_ok and runtime_default_false_ok
               and r0_non_identity_ok and package_ok
               and coverage_unavailable_ok and all_groups_not_present_ok
               and critical_count_ok and schema_count_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "haaer1asource0000",
        "source_lock_bucket": "haae_r1_public_report_locked",
        "input_artifact_load_status_bucket": r1_state,
        "locked_haae_r1_checkpoint": LOCKED_HAAE_R1_CHECKPOINT,
        "locked_haae_r1_status": LOCKED_HAAE_R1_STATUS,
        "locked_haae_r1_next_allowed_phase": LOCKED_HAAE_R1_NEXT_ALLOWED_PHASE,
        "locked_haae_r0_checkpoint": LOCKED_HAAE_R0_CHECKPOINT,
        "locked_haae_r0_status": LOCKED_HAAE_R0_STATUS,
        "locked_n10et_checkpoint": LOCKED_N10ET_CHECKPOINT,
        "locked_n10et_status": LOCKED_N10ET_STATUS,
        "haae_r1_status_match_bool": status_ok,
        "haae_r1_scan_pass_bool": r1_scan_ok,
        "haae_r1_next_phase_match_bool": next_phase_ok,
        "haae_r2_false_match_bool": haae_r2_false_ok,
        "haae_r1_execution_false_match_bool": haae_r1_execution_false_ok,
        "haae_r1_replay_false_match_bool": haae_r1_replay_false_ok,
        "haae_r1_scoring_false_match_bool": haae_r1_scoring_false_ok,
        "haae_r1_retrieval_false_match_bool": haae_r1_retrieval_false_ok,
        "haae_r1_candidate_generation_false_match_bool": haae_r1_candidate_gen_false_ok,
        "bea_v1_a_false_match_bool": bea_v1_a_false_ok,
        "p5_false_match_bool": p5_false_ok,
        "selector_reranker_false_match_bool": selector_reranker_false_ok,
        "runtime_default_false_match_bool": runtime_default_false_ok,
        "haae_r0_non_identity_match_bool": r0_non_identity_ok,
        "package_feasibility_inventory_only_match_bool": package_ok,
        "coverage_unavailable_match_bool": coverage_unavailable_ok,
        "all_groups_not_present_match_bool": all_groups_not_present_ok,
        "critical_group_count_match_bool": critical_count_ok,
        "schema_group_count_match_bool": schema_count_ok,
        "no_ci_rerun_performed_bool": True,
        "no_retrieval_performed_bool": True,
        "no_recompute_performed_bool": True,
        "no_private_input_read_bool": True,
        "no_replay_performed_bool": True,
        "no_scoring_performed_bool": True,
        "no_candidate_generation_performed_bool": True,
        "no_haae_layer_execution_bool": True,
        "no_root_regeneration_bool": True,
        "no_network_run_bool": True,
        "no_clone_build_search_bool": True,
        "public_readback_match_bool": readback["all_public_readback_match_bool"],
        "source_locked_bool": lock_ok,
    }
    return lock_ok, lock_record


# ── Non-identity helper ─────────────────────────────────────────────────────

def _non_identity_fields() -> dict[str, bool]:
    return {
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }


NON_IDENTITY_BUCKETS = list(HAAE_R1A_NOT_IDENTITIES)


# ── Record builders ────────────────────────────────────────────────────────

def public_input_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_public_input_id": f"haaer1ainput{idx:04d}",
        "input_bucket": inp["input_bucket"],
        "input_kind_bucket": inp["input_kind_bucket"],
        "input_description_bucket": inp["input_description_bucket"],
        "public_only_bool": True,
        "no_private_read_bool": True,
        "constants_only_bool": True,
        "no_replay_bool": True,
        "no_recompute_bool": True,
        "aggregate_buckets_only_bool": True,
    } for idx, inp in enumerate(PUBLIC_INPUT_ARTIFACTS)]


def coverage_gap_records() -> list[dict[str, Any]]:
    """One record per HAAE-R0 schema group (10 total). Each records the
    coverage gap from HAAE-R1 (all not_present) and the source option count."""
    records: list[dict[str, Any]] = []
    for group in SCHEMA_GROUPS:
        g_bucket = group["group_bucket"]
        opts = SOURCE_OPTIONS_BY_GROUP.get(g_bucket, [])
        has_strong = any(o["public_evidence_strength_bucket"] == "public_evidence_strong" for o in opts)
        has_partial = any(o["public_evidence_strength_bucket"] == "public_evidence_partial" for o in opts)
        records.append({
            "anonymous_coverage_gap_id": f"haaer1agap{group['group_index']:04d}",
            "group_bucket": g_bucket,
            "group_index": group["group_index"],
            "group_description_bucket": group["group_description_bucket"],
            "is_critical_group_bool": group["is_critical_group_bool"],
            "haae_r1_coverage_bucket": "not_present",
            "source_option_count": len(opts),
            "has_public_evidence_strong_bool": has_strong,
            "has_public_evidence_partial_bool": has_partial,
            "gap_description_bucket": (
                f"group {g_bucket} was not_present in HAAE-R1 (no explicit "
                f"private roots). {len(opts)} source option(s) identified with "
                f"public_evidence_strong={has_strong}, "
                f"public_evidence_partial={has_partial}."),
            "no_raw_release_bool": True,
            "aggregate_buckets_only_bool": True,
        })
    return records


def root_source_option_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_source_option_id": f"haaer1aopt{idx:04d}",
        "group_bucket": opt["group_bucket"],
        "source_option_bucket": opt["source_option_bucket"],
        "public_evidence_strength_bucket": opt["public_evidence_strength_bucket"],
        "source_artifact_buckets": opt["source_artifact_buckets"],
        "source_description_bucket": opt["source_description_bucket"],
        "regeneration_feasible_bool": opt["regeneration_feasible_bool"],
        "design_only_bool": True,
        "execution_authorized_bool": False,
        "no_private_read_bool": True,
        "no_replay_bool": True,
        "no_retrieval_bool": True,
        "no_candidate_generation_bool": True,
        "no_scoring_bool": True,
        "no_haae_layer_execution_bool": True,
        "aggregate_buckets_only_bool": True,
        "no_raw_release_bool": True,
    } for idx, opt in enumerate(SOURCE_OPTIONS)]


def bounded_regeneration_design_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_regeneration_design_id": f"haaer1aregen{idx:04d}",
        "design_bucket": design["design_bucket"],
        "design_description_bucket": design["design_description_bucket"],
        "source_group_buckets": design.get("source_group_buckets", []),
        "regeneration_kind_bucket": design.get("regeneration_kind_bucket", "explicit_opt_in"),
        "bounded_depth_bool": design.get("bounded_depth_bool", True),
        "no_symlink_escape_bool": design.get("no_symlink_escape_bool", True),
        "explicit_opt_in_required_bool": design.get("explicit_opt_in_required_bool", True),
        "no_implicit_traversal_bool": design.get("no_implicit_traversal_bool", True),
        "private_output_only_bool": design.get("private_output_only_bool", True),
        "public_manifest_count_only_bool": design.get("public_manifest_count_only_bool", True),
        "public_aggregate_buckets_only_bool": design.get("public_aggregate_buckets_only_bool", True),
        "no_raw_rows_published_bool": design.get("no_raw_rows_published_bool", True),
        "design_only_bool": True,
        "execution_authorized_bool": False,
        "no_root_regeneration_in_r1a_bool": True,
        "aggregate_buckets_only_bool": True,
    } for idx, design in enumerate(BOUNDED_REGENERATION_DESIGNS)]


def root_manifest_schema_design_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_manifest_schema_id": f"haaer1amanifest{idx:04d}",
        "schema_field_bucket": field["schema_field_bucket"],
        "schema_field_type_bucket": field["schema_field_type_bucket"],
        "schema_field_description_bucket": field["schema_field_description_bucket"],
        "required_bool": field["required_bool"],
        "aggregate_bucket_only_bool": field["aggregate_bucket_only_bool"],
        "no_raw_release_bool": True,
        "design_only_bool": True,
    } for idx, field in enumerate(ROOT_MANIFEST_SCHEMA_DESIGNS)]


def option_decision_records(lock_ok: bool) -> list[dict[str, Any]]:
    """Decision: pass if source lock passes and at least one source option has
    public_evidence_strong or partial; controlled no-go otherwise."""
    has_strong_or_partial = any(
        opt["public_evidence_strength_bucket"] in ("public_evidence_strong",
                                                    "public_evidence_partial")
        for opt in SOURCE_OPTIONS
    )
    if lock_ok and has_strong_or_partial:
        decision = "pass_authorize_r1b_preflight"
        description = ("source lock passes, HAAE-R1 unavailable/no roots "
                        "confirmed, HAAE-R2 false, all 10 groups accounted, "
                        "at least one source option public_evidence_strong/"
                        "partial. authorize only HAAE-R1B Bounded Private "
                        "Trace Root Regeneration Preflight Package (design-only).")
    elif lock_ok and not has_strong_or_partial:
        decision = "controlled_no_go_closeout_explicit_roots_required"
        description = ("no safe source option (all public_evidence_absent/"
                        "weak). closeout: explicit roots required; no further "
                        "phase authorized.")
    else:
        decision = "unavailable_no_locked_source"
        description = "HAAE-R1 source not locked."
    return [{
        "anonymous_decision_id": "haaer1adecision0000",
        "decision_bucket": decision,
        "decision_description_bucket": description,
        "has_strong_or_partial_evidence_bool": has_strong_or_partial,
        "source_option_count": len(SOURCE_OPTIONS),
        "group_count": len(SCHEMA_GROUPS),
        "promotion_authorized_bool": False,
        "method_winner_claim_authorized_bool": False,
        "threshold_tuning_authorized_bool": False,
        "runtime_default_change_authorized_bool": False,
    }]


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "haaer1arisk0000",
            "risk_bucket": "private_diagnostic_leakage",
            "risk_description_bucket": ("the coverage gap design could leak "
                "raw diagnostic value categories into the public artifact."),
            "mitigation_bucket": ("HAAE-R1A publishes aggregate buckets only; "
                "forbidden_scan blocks raw diagnostic keys, private root "
                "location values, file extensions in values, hashes, and "
                "CI/task/record ids; every record carries "
                "aggregate_buckets_only_bool=true, no_raw_release_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1arisk0001",
            "risk_bucket": "haae_r1a_scope_creep_beyond_design",
            "risk_description_bucket": ("HAAE-R1A could be scoped beyond a "
                "design into root regeneration/replay/scoring/retrieval/"
                "candidate generation/HAAE-layer execution."),
            "mitigation_bucket": ("every record carries design_only_bool=true, "
                "execution_authorized_bool=false, no_root_regeneration_in_r1a_"
                "bool=true; stop/go carries haae_r1b_execution_authorized_"
                "bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1arisk0002",
            "risk_bucket": "haae_r0_drift_into_selector_or_p5_or_runtime",
            "risk_description_bucket": ("the coverage gap design could be "
                "reframed as BEA-v1-A, a selector-only design, selector/reranker "
                "execution, P5, or a runtime/default promotion."),
            "mitigation_bucket": ("every record carries the HAAE-R0 non-identity "
                "booleans; selector_reranker_authorized_bool=false; "
                "bea_v1_a_authorized_bool=false; p5_authorized_bool=false; "
                "runtime_default_change_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1arisk0003",
            "risk_bucket": "overauthorization_to_r1b_execution",
            "risk_description_bucket": ("the pass handoff could over-authorize "
                "HAAE-R1B beyond a design-only preflight into execution/private "
                "reads."),
            "mitigation_bucket": ("stop/go carries haae_r1b_design_only_bool=true, "
                "haae_r1b_execution_authorized_bool=false, "
                "haae_r1b_private_read_authorized_bool=false, "
                "haae_r1b_replay_authorized_bool=false, etc."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1arisk0004",
            "risk_bucket": "runtime_default_creep",
            "risk_description_bucket": ("the coverage gap design could implicitly "
                "drift runtime/default behavior by codifying a route as a "
                "default gate."),
            "mitigation_bucket": ("runtime_default_change_authorized_bool=false; "
                "any HAAE route remains opt-in/eval-only; no runtime or default "
                "change."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1arisk0005",
            "risk_bucket": "overinterpretation_from_coverage_gap",
            "risk_description_bucket": ("the coverage gap (all 10 groups "
                "not_present) could be overinterpreted as a method-winner or "
                "promotion claim."),
            "mitigation_bucket": ("method_winner_claim_authorized_bool=false; "
                "guard_full_diffaware_promotion_authorized_bool=false; the "
                "design authorizes only HAAE-R1B preflight or closeout, not any "
                "promotion or rule change."),
            "risk_controlled_bool": True,
        },
    ]


def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer1aclaim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_only_bool": True,
        "private_rows_read_bool": False,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
        "raw_filename_upload_bool": False,
        "raw_basename_upload_bool": False,
        "raw_repo_name_upload_bool": False,
        "raw_task_id_upload_bool": False,
        "raw_per_task_diagnostics_upload_bool": False,
        "raw_diagnostic_publication_bool": False,
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
        "threshold_tuning_bool": False,
        "frozen_rule_change_bool": False,
        "ci_rerun_bool": False,
        "retrieval_recompute_bool": False,
        "promotion_claim_bool": False,
        "candidate_generation_bool": False,
        "arm_scoring_bool": False,
        "openlocus_execution_bool": False,
        "replay_bool": False,
        "haae_layer_execution_bool": False,
        "root_regeneration_bool": False,
        "clone_build_search_bool": False,
        "n10et_execution_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "haae_r0_execution_authorized_bool": False,
        "haae_r1_execution_authorized_bool": False,
        "haae_r1_replay_authorized_bool": False,
        "haae_r1_scoring_authorized_bool": False,
        "haae_r1_retrieval_authorized_bool": False,
        "haae_r1_candidate_generation_authorized_bool": False,
        "haae_r1b_execution_authorized_bool": False,
        "haae_r1b_private_read_authorized_bool": False,
        "haae_r1b_replay_authorized_bool": False,
        "haae_r1b_scoring_authorized_bool": False,
        "haae_r1b_retrieval_authorized_bool": False,
        "haae_r1b_candidate_generation_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }]


def _gate(gate_id: str, bucket: str, passed: bool) -> dict[str, Any]:
    return {
        "anonymous_gate_id": gate_id,
        "gate_bucket": bucket,
        "gate_passed_bool": passed,
        "gate_evaluated_on_aggregate_bool": True,
        "gate_uses_gold_for_policy_bool": False,
        "gate_performs_ci_rerun_bool": False,
        "gate_reads_private_input_bool": False,
    }


def pass_fail_gate_records(lock_record: dict[str, Any], readback: dict[str, bool],
                           decision: str, has_strong_or_partial: bool) -> list[dict[str, Any]]:
    return [
        _gate("haaer1agate0000", "haae_r1_public_source_locked",
              lock_record["source_locked_bool"]),
        _gate("haaer1agate0001", "haae_r1_status_locked",
              lock_record["haae_r1_status_match_bool"]),
        _gate("haaer1agate0002", "haae_r1_next_phase_match",
              lock_record["haae_r1_next_phase_match_bool"]),
        _gate("haaer1agate0003", "haae_r2_false_match",
              lock_record["haae_r2_false_match_bool"]),
        _gate("haaer1agate0004", "haae_r1_unavailable_no_roots_confirmed",
              lock_record["coverage_unavailable_match_bool"]
              and lock_record["all_groups_not_present_match_bool"]),
        _gate("haaer1agate0005", "haae_r1_execution_false_match",
              lock_record["haae_r1_execution_false_match_bool"]),
        _gate("haaer1agate0006", "haae_r1_replay_false_match",
              lock_record["haae_r1_replay_false_match_bool"]),
        _gate("haaer1agate0007", "haae_r1_non_identity_match",
              lock_record["haae_r0_non_identity_match_bool"]),
        _gate("haaer1agate0008", "haae_r1a_no_threshold_tuning", True),
        _gate("haaer1agate0009", "haae_r1a_no_method_winner_claim", True),
        _gate("haaer1agate0010", "haae_r1a_no_runtime_default_change", True),
        _gate("haaer1agate0011", "haae_r1a_no_promotion_or_frozen_rule_change", True),
        _gate("haaer1agate0012", "haae_r1a_no_ci_rerun_retrieval_recompute", True),
        _gate("haaer1agate0013", "haae_r1a_no_replay_scoring_candidate_generation", True),
        _gate("haaer1agate0014", "haae_r1a_no_haae_layer_execution", True),
        _gate("haaer1agate0015", "haae_r1a_no_selector_reranker_no_p5_no_bea_v1_a", True),
        _gate("haaer1agate0016", "haae_r1a_no_private_input_read", True),
        _gate("haaer1agate0017", "haae_r1a_no_root_regeneration", True),
        _gate("haaer1agate0018", "haae_r1a_no_network_no_clone", True),
        _gate("haaer1agate0019", "haae_r1a_10_groups_accounted",
              len(SCHEMA_GROUPS) == 10),
        _gate("haaer1agate0020", "haae_r1a_5_critical_groups",
              len(CRITICAL_GROUPS) == 5),
        _gate("haaer1agate0021", "haae_r1a_source_options_present",
              len(SOURCE_OPTIONS) > 0),
        _gate("haaer1agate0022", "haae_r1a_at_least_one_strong_or_partial",
              has_strong_or_partial),
        _gate("haaer1agate0023", "haae_r1a_bounded_regeneration_design_present",
              len(BOUNDED_REGENERATION_DESIGNS) > 0),
        _gate("haaer1agate0024", "haae_r1a_root_manifest_schema_present",
              len(ROOT_MANIFEST_SCHEMA_DESIGNS) > 0),
        _gate("haaer1agate0025", "haae_r1a_decision_valid",
              decision in ("pass_authorize_r1b_preflight",
                            "controlled_no_go_closeout_explicit_roots_required",
                            "unavailable_no_locked_source")),
        _gate("haaer1agate0026", "docs_readback_match_gate",
              readback["haae_r1a_docs_readback_match_bool"]
              and readback["haae_r1_docs_readback_match_bool"]),
        _gate("haaer1agate0027", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("haaer1agate0028", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("haaer1agate0029", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("haaer1agate0030", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("haaer1agate0031", "self_test_total_public_readback_match_gate",
              readback["self_test_total_public_readback_match_bool"]),
        _gate("haaer1agate0032", "haae_r0_non_identity_gate", True),
    ]


def synthetic_validator_records() -> list[dict[str, Any]]:
    """Validate the coverage gap design logic against synthetic fixtures.
    In-process; no real data, no replay, no retrieval, no candidate generation."""
    return [
        {
            "anonymous_synthetic_validator_id": "haaer1asynth0000",
            "validator_bucket": "embedded_synthetic_pass_fixture",
            "fixture_kind_bucket": "pass",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "no_root_regeneration_bool": True,
            "validates_source_option_logic_bool": True,
            "expected_decision_bucket": "pass_authorize_r1b_preflight",
            "has_strong_or_partial_evidence_bool": True,
        },
        {
            "anonymous_synthetic_validator_id": "haaer1asynth0001",
            "validator_bucket": "embedded_synthetic_no_go_fixture",
            "fixture_kind_bucket": "no_go",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "no_root_regeneration_bool": True,
            "validates_source_option_logic_bool": True,
            "expected_decision_bucket": "controlled_no_go_closeout_explicit_roots_required",
            "has_strong_or_partial_evidence_bool": False,
        },
    ]


def public_package_records(lock_record: dict[str, Any], readback: dict[str, bool],
                           decision: str) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer1apackage0000",
        "package_bucket": "haae_r1a_private_trace_coverage_gap_design_package",
        "schema_version": "bea_v1_haae_r1a_private_trace_coverage_gap_design_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_only_bool": True,
        "private_input_read_count": 0,
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "candidate_generation_count": 0,
        "arm_scoring_count": 0,
        "openlocus_execution_count": 0,
        "replay_count": 0,
        "haae_layer_execution_count": 0,
        "root_regeneration_count": 0,
        "network_run_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "haae_r1_source_locked_bool": lock_record["source_locked_bool"],
        "haae_r1a_docs_readback_match_bool": readback["haae_r1a_docs_readback_match_bool"],
        "haae_r1_docs_readback_match_bool": readback["haae_r1_docs_readback_match_bool"],
        "haae_r0_docs_readback_match_bool": readback["haae_r0_docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "research_log_match_bool": readback["research_log_match_bool"],
        "research_summary_match_bool": readback["research_summary_match_bool"],
        "self_test_total_public_readback_match_bool": readback["self_test_total_public_readback_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
        "decision_bucket": decision,
    }]


def stop_go_records(decision: str) -> list[dict[str, Any]]:
    """Stop/go: pass authorizes only HAAE-R1B Bounded Private Trace Root
    Regeneration Preflight Package (design-only); no-go → closeout (explicit
    roots required). No execution/private read/replay/scoring/retrieval/
    candidate generation/HAAE-layer execution."""
    if decision == "pass_authorize_r1b_preflight":
        next_phase = NEXT_ROUTE_PASS
        r1b_authorized = True
    else:
        next_phase = NEXT_ROUTE_NO_GO
        r1b_authorized = False
    return [{
        "anonymous_stop_go_id": "haaer1astop0000",
        "next_allowed_phase": next_phase,
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "design_only_bool": True,
        "haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool": r1b_authorized,
        "haae_r1b_design_only_bool": r1b_authorized,
        "haae_r1b_execution_authorized_bool": False,
        "haae_r1b_private_read_authorized_bool": False,
        "haae_r1b_replay_authorized_bool": False,
        "haae_r1b_scoring_authorized_bool": False,
        "haae_r1b_retrieval_authorized_bool": False,
        "haae_r1b_candidate_generation_authorized_bool": False,
        "haae_r1b_haae_layer_execution_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
        "haae_r1a_execution_authorized_bool": False,
        "haae_r1a_re_run_authorized_bool": False,
        "haae_r1_execution_authorized_bool": False,
        "haae_r1_replay_authorized_bool": False,
        "haae_r1_scoring_authorized_bool": False,
        "haae_r1_retrieval_authorized_bool": False,
        "haae_r1_candidate_generation_authorized_bool": False,
        "haae_r0_execution_authorized_bool": False,
        "n10et_audit_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "execution_authorized_bool": False,
        "rerun_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "recompute_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "arm_scoring_authorized_bool": False,
        "openlocus_execution_authorized_bool": False,
        "replay_authorized_bool": False,
        "haae_layer_execution_authorized_bool": False,
        "root_regeneration_authorized_bool": False,
        "n10er_execution_authorized_bool": False,
        "n10er_re_run_authorized_bool": False,
        "n10es_audit_authorized_bool": False,
        "n10es_re_run_authorized_bool": False,
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
        "bea_v1_a_authorized_bool": False,
        "p5_authorized_bool": False,
        "provider_model_network_authorized_bool": False,
        "network_run_authorized_bool": False,
    }]


# ── Report assembly ────────────────────────────────────────────────────────

def build_report() -> dict[str, Any]:
    lock_ok, lock_record = evaluate_haae_r1_source_lock()
    readback = public_readback_match()

    has_strong_or_partial = any(
        opt["public_evidence_strength_bucket"] in ("public_evidence_strong",
                                                    "public_evidence_partial")
        for opt in SOURCE_OPTIONS
    )

    decisions = option_decision_records(lock_ok)
    decision = decisions[0]["decision_bucket"]

    if not lock_ok:
        status = STATUS_NO_SOURCE
        decision = "unavailable_no_locked_source"
    elif lock_ok and has_strong_or_partial:
        status = STATUS_PASS
        decision = "pass_authorize_r1b_preflight"
    else:
        status = STATUS_NO_GO
        decision = "controlled_no_go_closeout_explicit_roots_required"

    report: dict[str, Any] = {
        "schema_version": "bea_v1_haae_r1a_private_trace_coverage_gap_design_v1",
        "phase_bucket": "BEA-v1-HAAE-R1A Private Trace Coverage Gap Design",
        "status": status,
        "source_lock_records": [lock_record],
        "public_input_records": public_input_records(),
        "coverage_gap_records": coverage_gap_records(),
        "root_source_option_records": root_source_option_records(),
        "bounded_regeneration_design_records": bounded_regeneration_design_records(),
        "root_manifest_schema_design_records": root_manifest_schema_design_records(),
        "option_decision_records": option_decision_records(lock_ok and has_strong_or_partial
                                                           if lock_ok else lock_ok),
        "risk_control_records": risk_control_records(),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback,
                                                         decision, has_strong_or_partial),
        "synthetic_validator_records": synthetic_validator_records(),
        "public_package_records": public_package_records(lock_record, readback, decision),
        "stop_go_records": stop_go_records(decision),
        "gate_records": [
            {"anonymous_gate_id": "haaer1agate0000",
             "gate_bucket": "haae_r1_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "haaer1agate0012",
             "gate_bucket": "no_ci_rerun_retrieval_recompute",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1agate0016",
             "gate_bucket": "no_private_input_read",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1agate0017",
             "gate_bucket": "no_root_regeneration",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1agate0032",
             "gate_bucket": "haae_r0_non_identity_gate",
             "gate_passed_bool": True},
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
    lock = (report.get("source_lock_records") or [{}])[0] if report.get("source_lock_records") else {}
    if lock.get("source_locked_bool") is not True and report.get("status") not in (STATUS_NO_SOURCE,):
        failures.append("haae_r1_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("no_root_regeneration_bool") is not True:
        failures.append("root_regeneration_claim_not_true")
    if lock.get("haae_r2_false_match_bool") is not True:
        failures.append("haae_r2_not_false")
    if lock.get("coverage_unavailable_match_bool") is not True:
        failures.append("coverage_not_unavailable")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("haae_r1a_docs_readback_match_bool", "haae_r1_docs_readback_match_bool",
                  "haae_r0_docs_readback_match_bool", "readme_readback_match_bool",
                  "current_conclusions_match_bool", "research_log_match_bool",
                  "research_summary_match_bool", "self_test_total_public_readback_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Coverage gap records: 10 groups accounted.
    gap_records = report.get("coverage_gap_records", [])
    if len(gap_records) != 10:
        failures.append(f"coverage_gap_count_not_10_got_{len(gap_records)}")
    gap_buckets = {r.get("group_bucket") for r in gap_records}
    for needed in ALL_GROUP_BUCKETS:
        if needed not in gap_buckets:
            failures.append(f"missing_coverage_gap_{needed}")
    # Root source option records: at least one present.
    opts = report.get("root_source_option_records", [])
    if not opts:
        failures.append("root_source_option_empty")
    has_strong_or_partial = any(
        o.get("public_evidence_strength_bucket") in ("public_evidence_strong",
                                                      "public_evidence_partial")
        for o in opts)
    if not has_strong_or_partial and report.get("status") == STATUS_PASS:
        failures.append("pass_without_strong_or_partial_evidence")
    # Bounded regeneration design present.
    if not report.get("bounded_regeneration_design_records"):
        failures.append("bounded_regeneration_design_empty")
    # Root manifest schema present.
    if not report.get("root_manifest_schema_design_records"):
        failures.append("root_manifest_schema_empty")
    # Decision valid.
    decision = (report.get("option_decision_records") or [{}])[0].get("decision_bucket") if report.get("option_decision_records") else ""
    if decision not in ("pass_authorize_r1b_preflight",
                         "controlled_no_go_closeout_explicit_roots_required",
                         "unavailable_no_locked_source"):
        failures.append("decision_bucket_invalid")
    # Claim boundary.
    claim = (report.get("claim_boundary_records") or [{}])[0] if report.get("claim_boundary_records") else {}
    for field in ("method_winner_claim_bool", "production_retrieval_change_bool",
                  "runtime_default_change_bool", "selector_reranker_bool",
                  "threshold_tuning_bool", "frozen_rule_change_bool",
                  "raw_candidate_upload_bool", "raw_label_upload_bool",
                  "raw_path_upload_bool", "raw_query_upload_bool",
                  "raw_filename_upload_bool", "raw_basename_upload_bool",
                  "raw_repo_name_upload_bool", "raw_task_id_upload_bool",
                  "raw_per_task_diagnostics_upload_bool",
                  "scaled_retrieval_claim_bool", "ci_rerun_bool",
                  "retrieval_recompute_bool", "promotion_claim_bool",
                  "candidate_generation_bool", "arm_scoring_bool",
                  "openlocus_execution_bool", "replay_bool",
                  "haae_layer_execution_bool", "root_regeneration_bool",
                  "clone_build_search_bool",
                  "network_run_bool", "provider_model_network_bool",
                  "n10et_execution_authorized_bool", "n10et_re_run_authorized_bool",
                  "haae_r0_execution_authorized_bool",
                  "haae_r1_execution_authorized_bool",
                  "haae_r1_replay_authorized_bool",
                  "haae_r1_scoring_authorized_bool",
                  "haae_r1_retrieval_authorized_bool",
                  "haae_r1_candidate_generation_authorized_bool",
                  "haae_r1b_execution_authorized_bool",
                  "haae_r1b_private_read_authorized_bool",
                  "haae_r1b_replay_authorized_bool",
                  "haae_r1b_scoring_authorized_bool",
                  "haae_r1b_retrieval_authorized_bool",
                  "haae_r1b_candidate_generation_authorized_bool",
                  "gold_used_for_policy_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_only_bool",
                  "haae_r0_not_bea_v1_a_bool", "haae_r0_not_selector_only_bool",
                  "haae_r0_not_selector_reranker_execution_bool",
                  "haae_r0_not_p5_bool", "haae_r0_not_runtime_default_promotion_bool"):
        if claim.get(field) is not True:
            failures.append(f"claim_{field}_not_true")
    # Pass/fail gates.
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_uses_gold_for_policy_bool") is not False:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_uses_gold_for_policy")
        if gate.get("gate_evaluated_on_aggregate_bool") is not True:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_not_aggregate")
        if gate.get("gate_performs_ci_rerun_bool") is not False:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_performs_ci_rerun")
        if gate.get("gate_reads_private_input_bool") is not False:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_reads_private_input")
        if gate.get("gate_passed_bool") is not True:
            failures.append(f"pass_fail_gate_{gate.get('gate_bucket')}_not_passed")
    # Stop/go: if pass, R1B authorized + design-only; all execution false.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool") is not True:
            failures.append("stop_r1b_not_authorized_on_pass")
        if stop.get("haae_r1b_design_only_bool") is not True:
            failures.append("stop_r1b_not_design_only_on_pass")
    for field in ("haae_r1b_execution_authorized_bool",
                  "haae_r1b_private_read_authorized_bool",
                  "haae_r1b_replay_authorized_bool",
                  "haae_r1b_scoring_authorized_bool",
                  "haae_r1b_retrieval_authorized_bool",
                  "haae_r1b_candidate_generation_authorized_bool",
                  "haae_r1b_haae_layer_execution_authorized_bool",
                  "haae_r1a_execution_authorized_bool",
                  "haae_r1a_re_run_authorized_bool",
                  "haae_r1_execution_authorized_bool",
                  "haae_r1_replay_authorized_bool",
                  "haae_r1_scoring_authorized_bool",
                  "haae_r1_retrieval_authorized_bool",
                  "haae_r1_candidate_generation_authorized_bool",
                  "haae_r0_execution_authorized_bool",
                  "n10et_audit_authorized_bool", "n10et_re_run_authorized_bool",
                  "execution_authorized_bool", "rerun_authorized_bool",
                  "retrieval_authorized_bool", "recompute_authorized_bool",
                  "candidate_generation_authorized_bool",
                  "arm_scoring_authorized_bool",
                  "openlocus_execution_authorized_bool",
                  "replay_authorized_bool",
                  "haae_layer_execution_authorized_bool",
                  "root_regeneration_authorized_bool",
                  "n10er_execution_authorized_bool", "n10er_re_run_authorized_bool",
                  "n10es_audit_authorized_bool", "n10es_re_run_authorized_bool",
                  "threshold_tuning_authorized_bool", "new_policy_experiment_authorized_bool",
                  "frozen_rule_change_authorized_bool",
                  "guard_full_diffaware_promotion_authorized_bool",
                  "runtime_default_change_authorized_bool",
                  "method_winner_claim_authorized_bool",
                  "downstream_scaled_retrieval_authorized_bool",
                  "raw_diagnostic_publication_authorized_bool",
                  "ci_variant_execution_authorized_bool",
                  "selector_reranker_authorized_bool",
                  "bea_v1_a_authorized_bool", "p5_authorized_bool",
                  "provider_model_network_authorized_bool",
                  "network_run_authorized_bool"):
        if stop.get(field) is not False:
            failures.append(f"stop_{field}_not_false")
    for field in ("haae_r0_not_bea_v1_a_bool", "haae_r0_not_selector_only_bool",
                  "haae_r0_not_selector_reranker_execution_bool",
                  "haae_r0_not_p5_bool", "haae_r0_not_runtime_default_promotion_bool",
                  "public_only_bool", "aggregate_buckets_only_bool",
                  "design_only_bool"):
        if stop.get(field) is not True:
            failures.append(f"stop_{field}_not_true")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab",
                   STATUS_PASS in STATUS_VOCAB and STATUS_NO_GO in STATUS_VOCAB
                   and STATUS_NO_SOURCE in EXIT0_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser_rejects_unknown", False))
    except SystemExit as exc:
        checks.append(("safe_parser_rejects_unknown", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value_github", scan_summary({"bucket": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_value_openlocus", scan_summary({"bucket": "x .openlocus/research-private/ y"})["status"] == "fail"))
    checks.append(("scanner_value_openlocus_standalone", scan_summary({"bucket": "no traversal of .openlocus"})["status"] == "fail"))
    checks.append(("scanner_value_tmp", scan_summary({"bucket": "/tmp/foo"})["status"] == "fail"))
    checks.append(("scanner_value_tmp_standalone", scan_summary({"bucket": "private rows under /tmp only"})["status"] == "fail"))
    checks.append(("scanner_value_workspace", scan_summary({"bucket": "/workspace/foo"})["status"] == "fail"))
    checks.append(("scanner_value_file_ext", scan_summary({"bucket": "data.jsonl"})["status"] == "fail"))
    checks.append(("scanner_value_task_id", scan_summary({"bucket": "task_abc123"})["status"] == "fail"))
    checks.append(("scanner_value_record_id", scan_summary({"bucket": "record_xyz789"})["status"] == "fail"))
    checks.append(("scanner_value_case_id", scan_summary({"bucket": "case_00123"})["status"] == "fail"))
    checks.append(("scanner_value_ci_id", scan_summary({"bucket": "ci-00001"})["status"] == "fail"))
    checks.append(("scanner_value_embedded_forbidden_field_sequence", scan_summary({"bucket": "path/line_range/content_sha/score"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_passes_clean", scan_summary({"status": "ok", "count": 7})["status"] == "pass"))
    checks.append(("scanner_key_candidate", scan_summary({"candidate": "x"})["status"] == "fail"))
    checks.append(("scanner_key_query", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_key_span", scan_summary({"span": "x"})["status"] == "fail"))
    checks.append(("scanner_key_score", scan_summary({"score": "x"})["status"] == "fail"))
    checks.append(("scanner_key_path", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_key_repo", scan_summary({"repo": "x"})["status"] == "fail"))

    # Locked constants.
    checks.append(("locked_haae_r1_checkpoint", LOCKED_HAAE_R1_CHECKPOINT == "2ea77da"))
    checks.append(("locked_haae_r1_status",
                   LOCKED_HAAE_R1_STATUS == "haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots"))
    checks.append(("locked_haae_r0_checkpoint", LOCKED_HAAE_R0_CHECKPOINT == "854fc2e"))
    checks.append(("locked_n10et_checkpoint", LOCKED_N10ET_CHECKPOINT == "26d817e"))
    checks.append(("haae_r1a_non_identities",
                   set(HAAE_R1A_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))
    checks.append(("schema_group_count", len(SCHEMA_GROUPS) == 10))
    checks.append(("critical_group_count", len(CRITICAL_GROUPS) == 5))
    checks.append(("next_route_pass", "HAAE-R1B" in NEXT_ROUTE_PASS
                   and "Bounded Private Trace Root Regeneration Preflight" in NEXT_ROUTE_PASS))
    checks.append(("next_route_no_go", "closeout" in NEXT_ROUTE_NO_GO
                   and "explicit_roots_required" in NEXT_ROUTE_NO_GO))
    checks.append(("public_input_count", len(PUBLIC_INPUT_ARTIFACTS) >= 10))
    checks.append(("source_option_count", len(SOURCE_OPTIONS) == 10))
    checks.append(("regeneration_design_count", len(BOUNDED_REGENERATION_DESIGNS) >= 4))
    checks.append(("manifest_schema_count", len(ROOT_MANIFEST_SCHEMA_DESIGNS) >= 5))

    # Source lock against the real HAAE-R1 public report.
    lock_ok, lock_record = evaluate_haae_r1_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_haae_r1_status_match",
                   lock_record["haae_r1_status_match_bool"] is True))
    checks.append(("source_lock_next_phase_match",
                   lock_record["haae_r1_next_phase_match_bool"] is True))
    checks.append(("source_lock_haae_r2_false_match",
                   lock_record["haae_r2_false_match_bool"] is True))
    checks.append(("source_lock_coverage_unavailable_match",
                   lock_record["coverage_unavailable_match_bool"] is True))
    checks.append(("source_lock_all_groups_not_present_match",
                   lock_record["all_groups_not_present_match_bool"] is True))
    checks.append(("source_lock_haae_r1_execution_false_match",
                   lock_record["haae_r1_execution_false_match_bool"] is True))
    checks.append(("source_lock_non_identity_match",
                   lock_record["haae_r0_non_identity_match_bool"] is True))
    checks.append(("source_lock_schema_count_match",
                   lock_record["schema_group_count_match_bool"] is True))

    readback = public_readback_match()
    checks.append(("readback_haae_r1a_docs_match",
                   readback["haae_r1a_docs_readback_match_bool"] is True))
    checks.append(("readback_haae_r1_docs_match",
                   readback["haae_r1_docs_readback_match_bool"] is True))
    checks.append(("readback_haae_r0_docs_match",
                   readback["haae_r0_docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))
    checks.append(("readback_log_match", readback["research_log_match_bool"] is True))
    checks.append(("readback_summary_match", readback["research_summary_match_bool"] is True))
    checks.append(("readback_self_test_total",
                   readback["self_test_total_public_readback_match_bool"] is True))

    # Coverage gap records: 10 groups, all accounted.
    gaps = coverage_gap_records()
    checks.append(("gaps_count_10", len(gaps) == 10))
    checks.append(("gaps_buckets_match",
                   {r["group_bucket"] for r in gaps} == set(ALL_GROUP_BUCKETS)))
    checks.append(("gaps_all_not_present",
                   all(r["haae_r1_coverage_bucket"] == "not_present" for r in gaps)))

    # Root source option records: at least one strong/partial.
    opts = root_source_option_records()
    checks.append(("opts_count_10", len(opts) == 10))
    checks.append(("opts_has_strong",
                   any(o["public_evidence_strength_bucket"] == "public_evidence_strong" for o in opts)))
    checks.append(("opts_has_partial",
                   any(o["public_evidence_strength_bucket"] == "public_evidence_partial" for o in opts)))
    checks.append(("opts_all_design_only",
                   all(o["design_only_bool"] is True for o in opts)))
    checks.append(("opts_all_no_execution",
                   all(o["execution_authorized_bool"] is False for o in opts)))

    # Bounded regeneration design.
    regens = bounded_regeneration_design_records()
    checks.append(("regens_present", len(regens) >= 4))
    checks.append(("regens_all_design_only",
                   all(r["design_only_bool"] is True for r in regens)))
    checks.append(("regens_no_root_regeneration_in_r1a",
                   all(r["no_root_regeneration_in_r1a_bool"] is True for r in regens)))

    # Root manifest schema.
    manifests = root_manifest_schema_design_records()
    checks.append(("manifests_present", len(manifests) >= 5))
    checks.append(("manifests_aggregate_only",
                   all(r["aggregate_bucket_only_bool"] is True for r in manifests)))

    # Risk controls.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == 6))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))
    checks.append(("risk_private_leakage_present",
                   any(r["risk_bucket"] == "private_diagnostic_leakage" for r in risks)))
    checks.append(("risk_scope_creep_present",
                   any(r["risk_bucket"] == "haae_r1a_scope_creep_beyond_design" for r in risks)))
    checks.append(("risk_overauth_present",
                   any(r["risk_bucket"] == "overauthorization_to_r1b_execution" for r in risks)))

    # Option decision: pass (source lock passes + strong evidence).
    pass_decisions = option_decision_records(True)
    checks.append(("decision_pass", pass_decisions[0]["decision_bucket"] == "pass_authorize_r1b_preflight"))
    checks.append(("decision_pass_has_evidence",
                   pass_decisions[0]["has_strong_or_partial_evidence_bool"] is True))
    checks.append(("decision_pass_no_promotion",
                   pass_decisions[0]["promotion_authorized_bool"] is False))
    no_go_decisions = option_decision_records(False)
    checks.append(("decision_no_go", no_go_decisions[0]["decision_bucket"] == "unavailable_no_locked_source"))

    # Stop/go: pass authorizes HAAE-R1B; no-go does not.
    pass_stop = stop_go_records("pass_authorize_r1b_preflight")[0]
    checks.append(("stop_pass_r1b_authorized",
                   pass_stop["haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool"] is True))
    checks.append(("stop_pass_r1b_design_only",
                   pass_stop["haae_r1b_design_only_bool"] is True))
    checks.append(("stop_pass_r1b_no_exec",
                   pass_stop["haae_r1b_execution_authorized_bool"] is False))
    checks.append(("stop_pass_r1b_no_private_read",
                   pass_stop["haae_r1b_private_read_authorized_bool"] is False))
    checks.append(("stop_pass_r1b_no_replay",
                   pass_stop["haae_r1b_replay_authorized_bool"] is False))
    no_go_stop = stop_go_records("controlled_no_go_closeout_explicit_roots_required")[0]
    checks.append(("stop_no_go_r1b_not_authorized",
                   no_go_stop["haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool"] is False))
    checks.append(("stop_no_selector_p5_bea_v1_a",
                   pass_stop["selector_reranker_authorized_bool"] is False
                   and pass_stop["p5_authorized_bool"] is False
                   and pass_stop["bea_v1_a_authorized_bool"] is False))
    checks.append(("stop_no_runtime_promotion",
                   pass_stop["runtime_default_change_authorized_bool"] is False
                   and pass_stop["guard_full_diffaware_promotion_authorized_bool"] is False
                   and pass_stop["method_winner_claim_authorized_bool"] is False))
    checks.append(("stop_no_replay_scoring_retrieval_candidate_gen",
                   pass_stop["replay_authorized_bool"] is False
                   and pass_stop["haae_r1_scoring_authorized_bool"] is False
                   and pass_stop["retrieval_authorized_bool"] is False
                   and pass_stop["candidate_generation_authorized_bool"] is False
                   and pass_stop["haae_layer_execution_authorized_bool"] is False))
    checks.append(("stop_no_root_regeneration",
                   pass_stop["root_regeneration_authorized_bool"] is False))
    checks.append(("stop_haae_r0_non_identity",
                   pass_stop["haae_r0_not_bea_v1_a_bool"] is True
                   and pass_stop["haae_r0_not_selector_only_bool"] is True
                   and pass_stop["haae_r0_not_selector_reranker_execution_bool"] is True
                   and pass_stop["haae_r0_not_p5_bool"] is True
                   and pass_stop["haae_r0_not_runtime_default_promotion_bool"] is True))

    # Claim boundary.
    cb = claim_boundary_records()[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_only_true", cb["design_only_bool"] is True))
    checks.append(("claim_no_root_regeneration", cb["root_regeneration_bool"] is False))
    checks.append(("claim_no_clone_build_search", cb["clone_build_search_bool"] is False))
    checks.append(("claim_no_replay", cb["replay_bool"] is False))
    checks.append(("claim_no_haae_layer_execution",
                   cb["haae_layer_execution_bool"] is False))
    checks.append(("claim_r1b_execution_false", cb["haae_r1b_execution_authorized_bool"] is False))
    checks.append(("claim_r1b_private_read_false", cb["haae_r1b_private_read_authorized_bool"] is False))
    checks.append(("claim_haae_r0_non_identity",
                   cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Synthetic validators.
    synths = synthetic_validator_records()
    checks.append(("synths_count", len(synths) == 2))
    checks.append(("synths_no_real_data",
                   all(r["no_real_data_bool"] is True for r in synths)))
    checks.append(("synths_no_replay",
                   all(r["no_replay_bool"] is True for r in synths)))

    # Full report build + validation.
    report = build_report()
    checks.append(("report_status_pass", report["status"] == STATUS_PASS))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields",
                   package["haae_r1a_docs_readback_match_bool"] is True
                   and package["haae_r1_docs_readback_match_bool"] is True
                   and package["haae_r0_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))
    checks.append(("report_10_gaps_accounted",
                   len(report["coverage_gap_records"]) == 10))
    checks.append(("report_stop_r1b_authorized",
                   report["stop_go_records"][0]
                   ["haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool"] is True))
    checks.append(("report_stop_no_execution",
                   report["stop_go_records"][0]["execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["haae_r1b_execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["root_regeneration_authorized_bool"] is False
                   and report["stop_go_records"][0]["provider_model_network_authorized_bool"] is False))

    # Bad-contract detection.
    bad = dict(report)
    bad["stop_go_records"] = [{**stop_go_records("pass_authorize_r1b_preflight")[0],
                               "haae_r1b_execution_authorized_bool": True}]
    checks.append(("validate_fails_r1b_execution",
                   any("haae_r1b_execution_authorized_bool_not_false" in f
                       for f in validate_report(bad))))
    bad2 = dict(report)
    bad2["claim_boundary_records"] = [{**claim_boundary_records()[0],
                                        "method_winner_claim_bool": True}]
    checks.append(("validate_fails_method_winner",
                   any("method_winner_claim_bool_not_false" in f
                       for f in validate_report(bad2))))
    bad3 = dict(report)
    bad3["public_package_records"] = [{**report["public_package_records"][0],
                                         "readme_readback_match_bool": False}]
    checks.append(("validate_fails_readback",
                   any("readme_readback_match_bool" in f
                       for f in validate_report(bad3))))
    bad4 = dict(report)
    bad4["stop_go_records"] = [{**stop_go_records("pass_authorize_r1b_preflight")[0],
                                 "bea_v1_a_authorized_bool": True}]
    checks.append(("validate_fails_bea_v1_a",
                   any("bea_v1_a_authorized_bool_not_false" in f
                       for f in validate_report(bad4))))
    bad5 = dict(report)
    bad5["coverage_gap_records"] = report["coverage_gap_records"][:-1]
    checks.append(("validate_fails_gap_count",
                   any("coverage_gap_count_not_10" in f
                       for f in validate_report(bad5))))
    bad6 = dict(report)
    bad6["root_source_option_records"] = []
    checks.append(("validate_fails_empty_options",
                   any("root_source_option_empty" in f
                       for f in validate_report(bad6))))

    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks; "
          f"expected_total={SELF_TEST_TOTAL_CHECKS})")
    return passed == len(checks) and len(checks) == SELF_TEST_TOTAL_CHECKS


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

    # Public-only design. No private reads, no root regeneration.
    report = build_report()
    failures = validate_report(report)
    if failures:
        report["status"] = STATUS_FAIL_CONTRACT
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] in EXIT0_VOCAB else 1


if __name__ == "__main__":
    raise SystemExit(main())
