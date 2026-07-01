#!/usr/bin/env python3
"""BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package.

HAAE-R1B is the **public-only, design-only preflight package** for bounded
private trace root regeneration, opened by the HAAE-R1A coverage gap design
(checkpoint ``e54d1b4``, status
``haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized``).

R1B is **not** an execution phase. It must **not**:
  * read private data;
  * write private data;
  * regenerate roots;
  * execute replay/scoring/retrieval/candidate generation/HAAE layers;
  * run CI/network/clone/build/search;
  * authorize BEA-v1-A/P5/selector/runtime/default.

Allowed public inputs:
  * the committed HAAE-R1A public aggregate report (the coverage gap design
    that authorized R1B);
  * the HAAE-R1/R0/N10ET public aggregate reports (upstream locks);
  * the HAAE-R1A/R1/R0/N10ET evaluators for constants only (never executed);
  * public aggregate artifacts/docs used by R1A (FD1, P4L, N1, N2, N10-series
    / mechanism synthesis) for recipe classification;
  * the README/current-research-conclusions/research-log/research-summary
    public readback;
  * git metadata: the ``e54d1b4`` checkpoint that recorded the HAAE-R1A result.

R1B packages a machine-readable, non-empty preflight control-plane:
  * recipe catalog records (covering all 10 HAAE-R0 schema groups);
  * operator checklist records (the safe operators for R1C smoke);
  * private output contract records (private output only, public manifest only);
  * public manifest schema records (the manifest schema for R1C output);
  * R1C contract records (the bounded contract for the R1C smoke);
  * risk control records, claim boundary, pass/fail gates, synthetic
    validators, public package, stop/go.

Handoff: pass → authorizes **only** BEA-v1-HAAE-R1C Bounded Private Trace Root
Regeneration Smoke (separately implemented/reviewed). R1B itself executes
nothing. The R1C boundary must require explicit opt-in, private output only,
public manifest only, bounded recipe only; unbounded replay/retrieval/candidate
generation/scoring/selector/BEA-v1-A/P5/runtime must all be false.

Status vocabulary:
  * ``haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized``
    — source lock passes, R1B authorized/design-only by R1A, public input
    matrix non-empty, recipe catalog covers all 10 groups, operator checklist/
    private output contract/public manifest schema/R1C bounded contract
    present, scanner/docs/readback pass, no private/execution/root
    regeneration.
  * ``haae_r1b_..._controlled_no_go_no_safe_bounded_r1c_recipe_set`` — no safe
    bounded R1C recipe set.
  * ``haae_r1b_..._unavailable_no_locked_source`` — HAAE-R1A source not locked.
  * ``fail_haae_r1a_source_lock_mismatch`` / ``fail_forbidden_scan`` /
    ``fail_schema_contract`` / ``fail_contract_violation`` — fail-closed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
HAAE_R1A_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_haae_r1a_private_trace_coverage_gap_design"
    / "bea_v1_haae_r1a_private_trace_coverage_gap_design_report.json"
)
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
HAAE_R1A_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1a-private-trace-coverage-gap-design.md"
)
HAAE_R1A_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1a-private-trace-coverage-gap-design.md"
)
HAAE_R1_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md"
)
HAAE_R1_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md"
)
HAAE_R0_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
HAAE_R0_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
HAAE_R1B_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md"
)
HAAE_R1B_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md"
)
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"

# ── Locked HAAE-R1A public facts (git metadata + upstream locks) ──────────
LOCKED_HAAE_R1A_CHECKPOINT = "e54d1b4"
LOCKED_HAAE_R1A_STATUS = (
    "haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized"
)
LOCKED_HAAE_R1A_NEXT_ALLOWED_PHASE = (
    "BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package"
)
# Upstream locks (read from HAAE-R1A's source_lock_records).
LOCKED_HAAE_R1_CHECKPOINT = "2ea77da"
LOCKED_HAAE_R1_STATUS = (
    "haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots"
)
LOCKED_HAAE_R0_CHECKPOINT = "854fc2e"
LOCKED_HAAE_R0_STATUS = "haae_r0_design_schema_preflight_complete_haae_r1_authorized"
LOCKED_N10ET_CHECKPOINT = "26d817e"
LOCKED_N10ET_STATUS = (
    "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"
)

# ── Non-identities (carried from HAAE-R0) ──────────────────────────────────
HAAE_R1B_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Next-route handoff ─────────────────────────────────────────────────────
NEXT_ROUTE_PASS = "BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke"
NEXT_ROUTE_NO_GO = "closeout_no_safe_bounded_r1c_recipe_set"

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_PASS = ("haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
               "_complete_r1c_smoke_authorized")
STATUS_NO_GO = ("haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
                "_controlled_no_go_no_safe_bounded_r1c_recipe_set")
STATUS_NO_SOURCE = ("haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
                    "_unavailable_no_locked_source")
STATUS_FAIL_LOCK = "fail_haae_r1a_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
EXIT0_VOCAB = {STATUS_PASS, STATUS_NO_GO, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_SCAN,
                              STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT}

# ── Privacy scan ───────────────────────────────────────────────────────────
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
SELF_TEST_TOTAL_CHECKS = 108

# ── HAAE-R0 schema groups (the 10 recipe targets) ─────────────────────────

SCHEMA_GROUPS: list[dict[str, Any]] = [
    {"group_bucket": "task_identity", "group_index": 0,
     "is_critical_group_bool": True,
     "group_description_bucket": "anonymous task identity."},
    {"group_bucket": "anchor_source", "group_index": 1,
     "is_critical_group_bool": False,
     "group_description_bucket": "anchor/source acquisition layer."},
    {"group_bucket": "candidate_pool", "group_index": 2,
     "is_critical_group_bool": True,
     "group_description_bucket": "candidate pool shape."},
    {"group_bucket": "rank_pack", "group_index": 3,
     "is_critical_group_bool": False,
     "group_description_bucket": "rank/pack depth-to-head."},
    {"group_bucket": "span_projection", "group_index": 4,
     "is_critical_group_bool": False,
     "group_description_bucket": "span projection."},
    {"group_bucket": "scheduler_action", "group_index": 5,
     "is_critical_group_bool": False,
     "group_description_bucket": "scheduler action."},
    {"group_bucket": "evidence_core", "group_index": 6,
     "is_critical_group_bool": True,
     "group_description_bucket": "EvidenceCore aggregate buckets."},
    {"group_bucket": "arm_assignment", "group_index": 7,
     "is_critical_group_bool": True,
     "group_description_bucket": "arm assignment."},
    {"group_bucket": "outcome_metric", "group_index": 8,
     "is_critical_group_bool": True,
     "group_description_bucket": "outcome metric aggregate buckets."},
    {"group_bucket": "safety_probe_signal", "group_index": 9,
     "is_critical_group_bool": False,
     "group_description_bucket": "safety-probe signal aggregate buckets."},
]

CRITICAL_GROUPS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS
                        if g["is_critical_group_bool"])
ALL_GROUP_BUCKETS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS)
assert len(SCHEMA_GROUPS) == 10
assert len(CRITICAL_GROUPS) == 5

# ── Public input artifacts (explicit public paths, read for constants only) ─
PUBLIC_INPUT_ARTIFACTS: list[dict[str, str]] = [
    {"input_bucket": "haae_r1a_coverage_gap_design",
     "input_kind_bucket": "haae_r1a_public_aggregate_report",
     "input_description_bucket": "the HAAE-R1A coverage gap design that authorized R1B."},
    {"input_bucket": "haae_r1_feasibility_inventory",
     "input_kind_bucket": "haae_r1_public_aggregate_report",
     "input_description_bucket": "the HAAE-R1 feasibility inventory confirming all 10 groups not_present."},
    {"input_bucket": "haae_r0_schema_preflight",
     "input_kind_bucket": "haae_r0_public_aggregate_report",
     "input_description_bucket": "the HAAE-R0 schema preflight designing the 10 schema groups."},
    {"input_bucket": "n10et_public_safety_probe_design_decision",
     "input_kind_bucket": "n10et_public_aggregate_report",
     "input_description_bucket": "the N10ET close-out design/decision."},
    {"input_bucket": "fd1_failure_decomposition",
     "input_kind_bucket": "fd1_public_aggregate_artifact",
     "input_description_bucket": "FD1 failure decomposition (86040 private decomposition rows, 239 composite record groups)."},
    {"input_bucket": "p4l_locked_non_python_scheduler_validation",
     "input_kind_bucket": "p4l_public_aggregate_artifact",
     "input_description_bucket": "P4L locked non-Python scheduler validation (272-record denominator, 1088 private arm-outcome rows)."},
    {"input_bucket": "n1_frozen_p4_span_refiner_smoke",
     "input_kind_bucket": "n1_public_aggregate_artifact",
     "input_description_bucket": "N1 frozen P4 span refiner smoke (rank-blocked denominator)."},
    {"input_bucket": "n2_rank_pack_actionability_decomposition",
     "input_kind_bucket": "n2_public_aggregate_artifact",
     "input_description_bucket": "N2 rank/pack actionability decomposition (40 rank-blocked records)."},
    {"input_bucket": "n10eo_difference_aware_ci_regression_failure_analysis",
     "input_kind_bucket": "n10eo_public_aggregate_artifact",
     "input_description_bucket": "N10EO difference-aware CI regression failure analysis (mechanism buckets)."},
    {"input_bucket": "n10er_bounded_public_ci_score_guard_safety_probe",
     "input_kind_bucket": "n10er_public_aggregate_artifact",
     "input_description_bucket": "N10ER bounded public CI score/guard safety probe (80/60/40 sample, arm aggregates)."},
    {"input_bucket": "n10es_public_safety_probe_audit_package",
     "input_kind_bucket": "n10es_public_aggregate_artifact",
     "input_description_bucket": "N10ES public safety probe audit package (locked N10ER aggregates)."},
    {"input_bucket": "n10em_difference_aware_winner_public_replication_package",
     "input_kind_bucket": "n10em_public_aggregate_artifact",
     "input_description_bucket": "N10EM difference-aware winner public replication package (13/16/20/26 chain)."},
]

# ── Recipe catalog (one recipe per schema group, covers all 10) ─────────────
RECIPE_CATALOG: list[dict[str, Any]] = [
    {
        "recipe_bucket": "fd1_decomposition_replay_recipe",
        "group_bucket": "task_identity",
        "recipe_description_bucket": (
            "replay the FD1 decomposition under explicit opt-in to regenerate "
            "task_identity rows. private output only; public manifest count "
            "buckets only. bounded by the 239 composite record groups."),
        "source_artifact_buckets": ["fd1_failure_decomposition"],
        "recipe_kind_bucket": "decomposition_replay",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "normalized_bm25_anchor_recovery_recipe",
        "group_bucket": "anchor_source",
        "recipe_description_bucket": (
            "derive anchor_kind and acquisition_cost buckets from the "
            "normalized BM25 recovery mechanism classification. public aggregate "
            "buckets only; no private rows required."),
        "source_artifact_buckets": ["n10dw_normalized_bm25_recovery_mechanism_analysis",
                                     "n10dz_normalized_bm25_expanded_canary",
                                     "n10ea_normalized_bm25_expanded_canary_public_package"],
        "recipe_kind_bucket": "public_aggregate_derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "public_manifest_count_only_bool": False,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "n10eo_diagnostic_rerun_recipe",
        "group_bucket": "candidate_pool",
        "recipe_description_bucket": (
            "replay the N10EO private diagnostic rerun under explicit opt-in "
            "to regenerate candidate_pool buckets. private output only; public "
            "aggregate mechanism buckets only."),
        "source_artifact_buckets": ["n10eo_difference_aware_ci_regression_failure_analysis"],
        "recipe_kind_bucket": "diagnostic_rerun",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": False,
        "public_aggregate_buckets_only_bool": True,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "n2_rank_pack_decomposition_recipe",
        "group_bucket": "rank_pack",
        "recipe_description_bucket": (
            "derive topk_pack and novel_vs_old_pool buckets from the N2 rank/"
            "pack actionability decomposition. public aggregate buckets only."),
        "source_artifact_buckets": ["n2_rank_pack_actionability_decomposition",
                                     "n10ej_full_guard_difference_analysis"],
        "recipe_kind_bucket": "public_aggregate_derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "public_manifest_count_only_bool": False,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "span_window_repair_branch_recipe",
        "group_bucket": "span_projection",
        "recipe_description_bucket": (
            "derive span_window and span_overlap buckets from the N10AA-N10BN "
            "span window repair branch. public aggregate buckets only."),
        "source_artifact_buckets": ["n10aa_span_window_repair_preflight",
                                     "n10ae_fixed_span_window_repair_replication_package"],
        "recipe_kind_bucket": "public_aggregate_derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "public_manifest_count_only_bool": False,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "p4l_scheduler_replay_recipe",
        "group_bucket": "scheduler_action",
        "recipe_description_bucket": (
            "replay the frozen P4 scheduler on the locked 272-record non-Python "
            "denominator under explicit opt-in to regenerate scheduler_action "
            "rows. private output only; public manifest count buckets only."),
        "source_artifact_buckets": ["p4l_locked_non_python_scheduler_validation"],
        "recipe_kind_bucket": "scheduler_replay",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "fd1_plus_n10er_evidence_core_recipe",
        "group_bucket": "evidence_core",
        "recipe_description_bucket": (
            "replay the FD1 decomposition under explicit opt-in for evidence "
            "core buckets; carry citation validity from N10ER public aggregates. "
            "private output for FD1 rows; public citation aggregate only."),
        "source_artifact_buckets": ["fd1_failure_decomposition",
                                     "n10er_bounded_public_ci_score_guard_safety_probe"],
        "recipe_kind_bucket": "hybrid_decomposition_replay_plus_public_aggregate",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "p4l_arm_outcome_5_arms_recipe",
        "group_bucket": "arm_assignment",
        "recipe_description_bucket": (
            "replay the frozen P4 scheduler to regenerate 1088 private arm-"
            "outcome rows with 5 arms. private output only; public manifest "
            "count buckets only."),
        "source_artifact_buckets": ["p4l_locked_non_python_scheduler_validation"],
        "recipe_kind_bucket": "arm_outcome_replay",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "n10er_n10es_outcome_metric_recipe",
        "group_bucket": "outcome_metric",
        "recipe_description_bucket": (
            "derive citation validity, file recovery top-k, and lost baseline "
            "top-10 from N10ER/N10ES public aggregates. public aggregate only."),
        "source_artifact_buckets": ["n10er_bounded_public_ci_score_guard_safety_probe",
                                     "n10es_public_safety_probe_audit_package"],
        "recipe_kind_bucket": "public_aggregate_derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "public_manifest_count_only_bool": False,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "recipe_bucket": "safety_probe_lineage_recipe",
        "group_bucket": "safety_probe_signal",
        "recipe_description_bucket": (
            "derive full_guard_diffaware_loss and risk_bucket_signal from the "
            "N10EQ/N10ER/N10ES/N10ET safety probe lineage. public aggregate only."),
        "source_artifact_buckets": ["n10eq_score_guard_safety_probe_design",
                                     "n10er_bounded_public_ci_score_guard_safety_probe",
                                     "n10es_public_safety_probe_audit_package"],
        "recipe_kind_bucket": "public_aggregate_derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "public_manifest_count_only_bool": False,
        "bounded_recipe_bool": True,
        "no_raw_release_bool": True,
    },
]

# ── Operator checklist (safe operators for R1C smoke) ───────────────────────
OPERATOR_CHECKLIST: list[dict[str, Any]] = [
    {
        "operator_bucket": "explicit_opt_in_private_root_enumeration",
        "operator_description_bucket": (
            "enumerate explicitly supplied private root buckets under explicit "
            "opt-in. bounded depth, no symlink escape, no traversal of ignored "
            "namespaces."),
        "operator_kind_bucket": "enumeration",
        "explicit_opt_in_required_bool": True,
        "bounded_depth_bool": True,
        "no_symlink_escape_bool": True,
        "no_implicit_traversal_bool": True,
        "safe_operator_bool": True,
    },
    {
        "operator_bucket": "fd1_decomposition_replay_operator",
        "operator_description_bucket": (
            "replay the FD1 decomposition to regenerate private decomposition "
            "rows. private output only; public manifest count buckets only."),
        "operator_kind_bucket": "replay",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_only_bool": True,
        "safe_operator_bool": True,
    },
    {
        "operator_bucket": "p4l_scheduler_replay_operator",
        "operator_description_bucket": (
            "replay the frozen P4 scheduler to regenerate private arm-outcome "
            "rows. private output only; public manifest count buckets only."),
        "operator_kind_bucket": "replay",
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_only_bool": True,
        "safe_operator_bool": True,
    },
    {
        "operator_bucket": "public_aggregate_derivation_operator",
        "operator_description_bucket": (
            "derive public aggregate buckets from existing public artifacts. "
            "no private reads, no replay."),
        "operator_kind_bucket": "derivation",
        "explicit_opt_in_required_bool": False,
        "private_output_only_bool": False,
        "no_private_read_bool": True,
        "no_replay_bool": True,
        "safe_operator_bool": True,
    },
    {
        "operator_bucket": "public_manifest_writer_operator",
        "operator_description_bucket": (
            "write the public manifest (aggregate count buckets only) from "
            "private output. no raw release."),
        "operator_kind_bucket": "manifest_writing",
        "explicit_opt_in_required_bool": True,
        "public_manifest_count_only_bool": True,
        "no_raw_release_bool": True,
        "safe_operator_bool": True,
    },
]

# ── Private output contract ────────────────────────────────────────────────
PRIVATE_OUTPUT_CONTRACT: list[dict[str, Any]] = [
    {
        "contract_bucket": "private_output_only",
        "contract_description_bucket": (
            "all private rows produced by R1C recipes must be written to "
            "explicit opt-in private output only. no raw rows published."),
        "private_output_only_bool": True,
        "no_raw_release_bool": True,
        "explicit_opt_in_required_bool": True,
    },
    {
        "contract_bucket": "public_manifest_count_only",
        "contract_description_bucket": (
            "the public artifact from R1C carries manifest count buckets only. "
            "no raw counts, no raw rows, no raw keys."),
        "public_manifest_count_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "no_raw_release_bool": True,
    },
    {
        "contract_bucket": "bounded_recipe_only",
        "contract_description_bucket": (
            "R1C recipes must be bounded by the recipe catalog from R1B. no "
            "unbounded replay, retrieval, or candidate generation."),
        "bounded_recipe_only_bool": True,
        "no_unbounded_replay_bool": True,
        "no_unbounded_retrieval_bool": True,
        "no_unbounded_candidate_generation_bool": True,
    },
]

# ── Public manifest schema ─────────────────────────────────────────────────
PUBLIC_MANIFEST_SCHEMA: list[dict[str, Any]] = [
    {"schema_field_bucket": "anonymous_recipe_id",
     "schema_field_type_bucket": "opaque_id_bucket",
     "schema_field_description_bucket": "anonymous recipe identifier.",
     "required_bool": True, "aggregate_bucket_only_bool": True},
    {"schema_field_bucket": "private_row_count_bucket",
     "schema_field_type_bucket": "ordinal_bucket",
     "schema_field_description_bucket": "bucketized private row count.",
     "required_bool": True, "aggregate_bucket_only_bool": True},
    {"schema_field_bucket": "group_coverage_map_bucket",
     "schema_field_type_bucket": "categorical_bucket",
     "schema_field_description_bucket": "which schema groups are populated.",
     "required_bool": True, "aggregate_bucket_only_bool": True},
    {"schema_field_bucket": "manifest_hash_bucket",
     "schema_field_type_bucket": "opaque_hash_bucket",
     "schema_field_description_bucket": "bucketized manifest hash (not raw).",
     "required_bool": True, "aggregate_bucket_only_bool": True},
    {"schema_field_bucket": "no_raw_release_bool",
     "schema_field_type_bucket": "bool_bucket",
     "schema_field_description_bucket": "explicit no-raw-release flag.",
     "required_bool": True, "aggregate_bucket_only_bool": True},
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
        description="BEA-v1-HAAE-R1B bounded private trace root regeneration "
                    "preflight package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--haae-r1a-report", default=str(HAAE_R1A_REPORT),
                        help="path to the committed HAAE-R1A public artifact")
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
    HAAE-R1B preflight package and the HAAE-R1A coverage gap design."""
    common_fragments = [
        LOCKED_HAAE_R1A_CHECKPOINT,
        LOCKED_HAAE_R1A_STATUS,
        "HAAE-R1A",
        "HAAE-R1B",
    ]
    self_test_fragments = (
        f"{SELF_TEST_TOTAL_CHECKS}/{SELF_TEST_TOTAL_CHECKS}",
        f"{SELF_TEST_TOTAL_CHECKS} / {SELF_TEST_TOTAL_CHECKS}",
    )
    readme = read_text_or_empty(README_PATH)
    haae_r1a_doc_en = read_text_or_empty(HAAE_R1A_DOC_EN)
    haae_r1a_doc_zh = read_text_or_empty(HAAE_R1A_DOC_ZH)
    haae_r1_doc_en = read_text_or_empty(HAAE_R1_DOC_EN)
    haae_r1_doc_zh = read_text_or_empty(HAAE_R1_DOC_ZH)
    haae_r0_doc_en = read_text_or_empty(HAAE_R0_DOC_EN)
    haae_r0_doc_zh = read_text_or_empty(HAAE_R0_DOC_ZH)
    haae_r1b_doc_en = read_text_or_empty(HAAE_R1B_DOC_EN)
    haae_r1b_doc_zh = read_text_or_empty(HAAE_R1B_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_r1b_closeout(text: str) -> bool:
        return ("HAAE-R1B" in text and "HAAE-R1A" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    def has_self_test_fragment(text: str) -> bool:
        return any(fragment in text for fragment in self_test_fragments)

    readme_self_test_match = has_self_test_fragment(readme)
    haae_r1b_docs_self_test_match = (has_self_test_fragment(haae_r1b_doc_en)
                                     and has_self_test_fragment(haae_r1b_doc_zh))
    current_self_test_match = (has_self_test_fragment(current_en)
                               and has_self_test_fragment(current_zh))
    log_self_test_match = (has_self_test_fragment(log_en)
                           and has_self_test_fragment(log_zh))
    summary_self_test_match = (has_self_test_fragment(summary_en)
                               and has_self_test_fragment(summary_zh))
    self_test_total_public_readback_match = (readme_self_test_match
                                             and haae_r1b_docs_self_test_match
                                             and current_self_test_match
                                             and log_self_test_match
                                             and summary_self_test_match)

    readme_match = (has_all(readme, common_fragments)
                    and has_r1b_closeout(readme)
                    and readme_self_test_match)
    current_match = (has_all(current_en, common_fragments)
                     and has_all(current_zh, common_fragments)
                     and has_r1b_closeout(current_en)
                     and has_r1b_closeout(current_zh)
                     and current_self_test_match)
    haae_r1b_docs_match = (has_all(haae_r1b_doc_en, common_fragments)
                           and has_all(haae_r1b_doc_zh, common_fragments)
                           and has_r1b_closeout(haae_r1b_doc_en)
                           and has_r1b_closeout(haae_r1b_doc_zh)
                           and haae_r1b_docs_self_test_match)
    haae_r1a_docs_match = "HAAE-R1B" in haae_r1a_doc_en and "HAAE-R1B" in haae_r1a_doc_zh
    haae_r1_docs_match = "HAAE-R1A" in haae_r1_doc_en and "HAAE-R1A" in haae_r1_doc_zh
    haae_r0_docs_match = "HAAE-R1" in haae_r0_doc_en and "HAAE-R1" in haae_r0_doc_zh
    log_match = (has_r1b_closeout(log_en) and has_r1b_closeout(log_zh)
                 and log_self_test_match)
    summary_match = (has_r1b_closeout(summary_en)
                     and has_r1b_closeout(summary_zh)
                     and summary_self_test_match)
    return {
        "haae_r1b_docs_readback_match_bool": haae_r1b_docs_match,
        "haae_r1a_docs_readback_match_bool": haae_r1a_docs_match,
        "haae_r1_docs_readback_match_bool": haae_r1_docs_match,
        "haae_r0_docs_readback_match_bool": haae_r0_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": self_test_total_public_readback_match,
        "all_public_readback_match_bool": (haae_r1b_docs_match and haae_r1a_docs_match
                                           and haae_r1_docs_match and haae_r0_docs_match
                                           and readme_match and current_match
                                           and log_match and summary_match),
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


# ── HAAE-R1A source lock ───────────────────────────────────────────────────

def _haae_r1a_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _haae_r1a_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def evaluate_haae_r1a_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the HAAE-R1A public report and validate every locked field."""
    r1a_report, r1a_state = load_json(HAAE_R1A_REPORT)
    present_ok = r1a_state == "present" and isinstance(r1a_report, dict)
    status_ok = bool(r1a_report and r1a_report.get("status") == LOCKED_HAAE_R1A_STATUS)
    r1a_scan_ok = bool(r1a_report
                       and r1a_report.get("forbidden_scan", {}).get("status") == "pass")
    stop = _haae_r1a_stop_go(r1a_report or {})
    next_phase_ok = (stop.get("next_allowed_phase") == LOCKED_HAAE_R1A_NEXT_ALLOWED_PHASE)
    r1b_authorized_ok = (stop.get("haae_r1b_bounded_private_trace_root_regeneration_"
                                    "preflight_authorized_bool") is True)
    r1b_design_only_ok = stop.get("haae_r1b_design_only_bool") is True
    r1b_execution_false_ok = stop.get("haae_r1b_execution_authorized_bool") is False
    r1b_private_read_false_ok = stop.get("haae_r1b_private_read_authorized_bool") is False
    r1b_replay_false_ok = stop.get("haae_r1b_replay_authorized_bool") is False
    r1b_scoring_false_ok = stop.get("haae_r1b_scoring_authorized_bool") is False
    r1b_retrieval_false_ok = stop.get("haae_r1b_retrieval_authorized_bool") is False
    r1b_candidate_gen_false_ok = (stop.get("haae_r1b_candidate_generation_"
                                            "authorized_bool") is False)
    r1b_haae_layer_exec_false_ok = (stop.get("haae_r1b_haae_layer_execution_"
                                               "authorized_bool") is False)
    bea_v1_a_false_ok = stop.get("bea_v1_a_authorized_bool") is False
    p5_false_ok = stop.get("p5_authorized_bool") is False
    selector_reranker_false_ok = stop.get("selector_reranker_authorized_bool") is False
    runtime_default_false_ok = stop.get("runtime_default_change_authorized_bool") is False
    root_regeneration_false_ok = stop.get("root_regeneration_authorized_bool") is False

    r0_non_identity_ok = (
        stop.get("haae_r0_not_bea_v1_a_bool") is True
        and stop.get("haae_r0_not_selector_only_bool") is True
        and stop.get("haae_r0_not_selector_reranker_execution_bool") is True
        and stop.get("haae_r0_not_p5_bool") is True
        and stop.get("haae_r0_not_runtime_default_promotion_bool") is True
    )

    package = _haae_r1a_package(r1a_report or {})
    package_ok = (package.get("design_only_bool") is True
                  and package.get("private_input_read_count") == 0)

    gap_count_ok = (len(r1a_report.get("coverage_gap_records", [])) == 10
                     if r1a_report else False)
    opts_count_ok = (len(r1a_report.get("root_source_option_records", [])) >= 10
                      if r1a_report else False)

    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and r1a_scan_ok
               and next_phase_ok and r1b_authorized_ok and r1b_design_only_ok
               and r1b_execution_false_ok and r1b_private_read_false_ok
               and r1b_replay_false_ok and r1b_scoring_false_ok
               and r1b_retrieval_false_ok and r1b_candidate_gen_false_ok
               and r1b_haae_layer_exec_false_ok
               and bea_v1_a_false_ok and p5_false_ok
               and selector_reranker_false_ok and runtime_default_false_ok
               and root_regeneration_false_ok
               and r0_non_identity_ok and package_ok
               and gap_count_ok and opts_count_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "haaer1bsource0000",
        "source_lock_bucket": "haae_r1a_public_report_locked",
        "input_artifact_load_status_bucket": r1a_state,
        "locked_haae_r1a_checkpoint": LOCKED_HAAE_R1A_CHECKPOINT,
        "locked_haae_r1a_status": LOCKED_HAAE_R1A_STATUS,
        "locked_haae_r1a_next_allowed_phase": LOCKED_HAAE_R1A_NEXT_ALLOWED_PHASE,
        "locked_haae_r1_checkpoint": LOCKED_HAAE_R1_CHECKPOINT,
        "locked_haae_r1_status": LOCKED_HAAE_R1_STATUS,
        "locked_haae_r0_checkpoint": LOCKED_HAAE_R0_CHECKPOINT,
        "locked_haae_r0_status": LOCKED_HAAE_R0_STATUS,
        "locked_n10et_checkpoint": LOCKED_N10ET_CHECKPOINT,
        "locked_n10et_status": LOCKED_N10ET_STATUS,
        "haae_r1a_status_match_bool": status_ok,
        "haae_r1a_scan_pass_bool": r1a_scan_ok,
        "haae_r1a_next_phase_match_bool": next_phase_ok,
        "haae_r1b_authorized_match_bool": r1b_authorized_ok,
        "haae_r1b_design_only_match_bool": r1b_design_only_ok,
        "haae_r1b_execution_false_match_bool": r1b_execution_false_ok,
        "haae_r1b_private_read_false_match_bool": r1b_private_read_false_ok,
        "haae_r1b_replay_false_match_bool": r1b_replay_false_ok,
        "haae_r1b_scoring_false_match_bool": r1b_scoring_false_ok,
        "haae_r1b_retrieval_false_match_bool": r1b_retrieval_false_ok,
        "haae_r1b_candidate_generation_false_match_bool": r1b_candidate_gen_false_ok,
        "haae_r1b_haae_layer_execution_false_match_bool": r1b_haae_layer_exec_false_ok,
        "bea_v1_a_false_match_bool": bea_v1_a_false_ok,
        "p5_false_match_bool": p5_false_ok,
        "selector_reranker_false_match_bool": selector_reranker_false_ok,
        "runtime_default_false_match_bool": runtime_default_false_ok,
        "root_regeneration_false_match_bool": root_regeneration_false_ok,
        "haae_r0_non_identity_match_bool": r0_non_identity_ok,
        "package_design_only_match_bool": package_ok,
        "coverage_gap_count_match_bool": gap_count_ok,
        "source_option_count_match_bool": opts_count_ok,
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


NON_IDENTITY_BUCKETS = list(HAAE_R1B_NOT_IDENTITIES)


# ── Record builders ────────────────────────────────────────────────────────

def public_input_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_public_input_id": f"haaer1binput{idx:04d}",
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


def recipe_catalog_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_recipe_id": f"haaer1brecipe{idx:04d}",
        "recipe_bucket": recipe["recipe_bucket"],
        "group_bucket": recipe["group_bucket"],
        "recipe_description_bucket": recipe["recipe_description_bucket"],
        "source_artifact_buckets": recipe["source_artifact_buckets"],
        "recipe_kind_bucket": recipe["recipe_kind_bucket"],
        "explicit_opt_in_required_bool": recipe.get("explicit_opt_in_required_bool", True),
        "private_output_only_bool": recipe.get("private_output_only_bool", True),
        "public_manifest_count_only_bool": recipe.get("public_manifest_count_only_bool", True),
        "public_aggregate_buckets_only_bool": recipe.get("public_aggregate_buckets_only_bool", False),
        "bounded_recipe_bool": recipe["bounded_recipe_bool"],
        "no_raw_release_bool": recipe["no_raw_release_bool"],
        "design_only_bool": True,
        "execution_authorized_bool": False,
        "aggregate_buckets_only_bool": True,
    } for idx, recipe in enumerate(RECIPE_CATALOG)]


def operator_checklist_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_operator_id": f"haaer1bop{idx:04d}",
        "operator_bucket": op["operator_bucket"],
        "operator_description_bucket": op["operator_description_bucket"],
        "operator_kind_bucket": op["operator_kind_bucket"],
        "explicit_opt_in_required_bool": op.get("explicit_opt_in_required_bool", True),
        "bounded_depth_bool": op.get("bounded_depth_bool", True),
        "no_symlink_escape_bool": op.get("no_symlink_escape_bool", True),
        "no_implicit_traversal_bool": op.get("no_implicit_traversal_bool", True),
        "private_output_only_bool": op.get("private_output_only_bool", True),
        "public_manifest_count_only_bool": op.get("public_manifest_count_only_bool", True),
        "bounded_recipe_only_bool": op.get("bounded_recipe_only_bool", True),
        "no_private_read_bool": op.get("no_private_read_bool", False),
        "no_replay_bool": op.get("no_replay_bool", False),
        "no_raw_release_bool": op.get("no_raw_release_bool", True),
        "safe_operator_bool": op["safe_operator_bool"],
        "design_only_bool": True,
        "execution_authorized_bool": False,
    } for idx, op in enumerate(OPERATOR_CHECKLIST)]


def private_output_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_contract_id": f"haaer1bcontract{idx:04d}",
        "contract_bucket": c["contract_bucket"],
        "contract_description_bucket": c["contract_description_bucket"],
        "private_output_only_bool": c.get("private_output_only_bool", True),
        "public_manifest_count_only_bool": c.get("public_manifest_count_only_bool", True),
        "aggregate_buckets_only_bool": c.get("aggregate_buckets_only_bool", True),
        "bounded_recipe_only_bool": c.get("bounded_recipe_only_bool", True),
        "no_unbounded_replay_bool": c.get("no_unbounded_replay_bool", True),
        "no_unbounded_retrieval_bool": c.get("no_unbounded_retrieval_bool", True),
        "no_unbounded_candidate_generation_bool": c.get("no_unbounded_candidate_generation_bool", True),
        "no_raw_release_bool": c.get("no_raw_release_bool", True),
        "explicit_opt_in_required_bool": c.get("explicit_opt_in_required_bool", True),
        "design_only_bool": True,
        "execution_authorized_bool": False,
    } for idx, c in enumerate(PRIVATE_OUTPUT_CONTRACT)]


def public_manifest_schema_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_manifest_schema_id": f"haaer1bmanifest{idx:04d}",
        "schema_field_bucket": field["schema_field_bucket"],
        "schema_field_type_bucket": field["schema_field_type_bucket"],
        "schema_field_description_bucket": field["schema_field_description_bucket"],
        "required_bool": field["required_bool"],
        "aggregate_bucket_only_bool": field["aggregate_bucket_only_bool"],
        "no_raw_release_bool": True,
        "design_only_bool": True,
    } for idx, field in enumerate(PUBLIC_MANIFEST_SCHEMA)]


def r1c_contract_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_r1c_contract_id": "haaer1br1ccontract0000",
        "contract_bucket": "haae_r1c_bounded_private_trace_root_regeneration_smoke",
        "contract_name": NEXT_ROUTE_PASS,
        "contract_description_bucket": (
            "R1C is a bounded private trace root regeneration smoke. it requires "
            "explicit opt-in, produces private output only, publishes public "
            "manifest count buckets only, and is bounded by the recipe catalog "
            "from R1B. unbounded replay/retrieval/candidate generation/scoring/"
            "selector/BEA-v1-A/P5/runtime are all false."),
        "explicit_opt_in_required_bool": True,
        "private_output_only_bool": True,
        "public_manifest_count_only_bool": True,
        "bounded_recipe_only_bool": True,
        "unbounded_replay_authorized_bool": False,
        "unbounded_retrieval_authorized_bool": False,
        "unbounded_candidate_generation_authorized_bool": False,
        "scoring_authorized_bool": False,
        "selector_authorized_bool": False,
        "bea_v1_a_authorized_bool": False,
        "p5_authorized_bool": False,
        "runtime_default_authorized_bool": False,
        "design_only_bool": True,
        "execution_authorized_bool": False,
        "authorized_for_next_phase_bool": True,
        "next_allowed_phase": NEXT_ROUTE_PASS,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }]


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "haaer1brisk0000",
            "risk_bucket": "private_diagnostic_leakage",
            "risk_description_bucket": ("the preflight package could leak private "
                "per-task diagnostics or raw identifiers into the public artifact."),
            "mitigation_bucket": ("forbidden_scan blocks raw per-task identifiers, "
                "private-root tokens, temporary locations, GitHub URLs, "
                "filenames and extensions, hashes, and task or record or case "
                "ids; every record carries aggregate_buckets_only_bool=true, "
                "no_raw_release_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1brisk0001",
            "risk_bucket": "haae_r1b_scope_creep_beyond_preflight",
            "risk_description_bucket": ("R1B could be scoped beyond a preflight "
                "into root regeneration or replay or scoring or retrieval or "
                "candidate generation or HAAE-layer execution."),
            "mitigation_bucket": ("every record carries design_only_bool=true, "
                "execution_authorized_bool=false, no_root_regeneration_bool=true; "
                "stop/go carries haae_r1c_execution_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1brisk0002",
            "risk_bucket": "haae_r0_drift_into_selector_or_p5_or_runtime",
            "risk_description_bucket": ("the preflight could be reframed as "
                "BEA-v1-A, selector-only, selector or reranker, P5, or runtime "
                "or default promotion."),
            "mitigation_bucket": ("every record carries the HAAE-R0 non-identity "
                "booleans; selector_reranker_authorized_bool=false; "
                "bea_v1_a_authorized_bool=false; p5_authorized_bool=false; "
                "runtime_default_change_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1brisk0003",
            "risk_bucket": "overauthorization_to_r1c_execution",
            "risk_description_bucket": ("the pass handoff could over-authorize "
                "R1C beyond a bounded smoke into unbounded replay or retrieval "
                "or candidate generation or scoring."),
            "mitigation_bucket": ("stop/go carries haae_r1c_design_only_bool=true, "
                "haae_r1c_execution_authorized_bool=false; r1c_contract carries "
                "bounded_recipe_only_bool=true, unbounded_replay_authorized_bool"
                "=false, etc."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1brisk0004",
            "risk_bucket": "runtime_default_creep",
            "risk_description_bucket": ("the preflight could drift runtime or "
                "default behavior."),
            "mitigation_bucket": ("runtime_default_change_authorized_bool=false; "
                "any HAAE route remains opt-in or eval-only."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1brisk0005",
            "risk_bucket": "empty_control_plane",
            "risk_description_bucket": ("the preflight could be an empty "
                "control-plane doc with no machine-readable records."),
            "mitigation_bucket": ("the artifact carries concrete records: 12 "
                "public inputs, 10 recipes, 5 operators, 3 private output "
                "contracts, 5 manifest schema fields, 1 R1C contract."),
            "risk_controlled_bool": True,
        },
    ]


def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer1bclaim0000",
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
        "haae_r1a_execution_authorized_bool": False,
        "haae_r1b_execution_authorized_bool": False,
        "haae_r1c_execution_authorized_bool": False,
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
                           recipe_covers_all: bool) -> list[dict[str, Any]]:
    return [
        _gate("haaer1bgate0000", "haae_r1a_public_source_locked",
              lock_record["source_locked_bool"]),
        _gate("haaer1bgate0001", "haae_r1a_status_locked",
              lock_record["haae_r1a_status_match_bool"]),
        _gate("haaer1bgate0002", "haae_r1b_authorized_by_r1a",
              lock_record["haae_r1b_authorized_match_bool"]),
        _gate("haaer1bgate0003", "haae_r1b_design_only_by_r1a",
              lock_record["haae_r1b_design_only_match_bool"]),
        _gate("haaer1bgate0004", "haae_r1b_execution_false_by_r1a",
              lock_record["haae_r1b_execution_false_match_bool"]),
        _gate("haaer1bgate0005", "haae_r1b_private_read_false_by_r1a",
              lock_record["haae_r1b_private_read_false_match_bool"]),
        _gate("haaer1bgate0006", "haae_r1b_non_identity_match",
              lock_record["haae_r0_non_identity_match_bool"]),
        _gate("haaer1bgate0007", "haae_r1b_no_threshold_tuning", True),
        _gate("haaer1bgate0008", "haae_r1b_no_method_winner_claim", True),
        _gate("haaer1bgate0009", "haae_r1b_no_runtime_default_change", True),
        _gate("haaer1bgate0010", "haae_r1b_no_promotion_or_frozen_rule_change", True),
        _gate("haaer1bgate0011", "haae_r1b_no_ci_rerun_retrieval_recompute", True),
        _gate("haaer1bgate0012", "haae_r1b_no_replay_scoring_candidate_generation", True),
        _gate("haaer1bgate0013", "haae_r1b_no_haae_layer_execution", True),
        _gate("haaer1bgate0014", "haae_r1b_no_selector_reranker_no_p5_no_bea_v1_a", True),
        _gate("haaer1bgate0015", "haae_r1b_no_private_input_read", True),
        _gate("haaer1bgate0016", "haae_r1b_no_root_regeneration", True),
        _gate("haaer1bgate0017", "haae_r1b_no_network_no_clone", True),
        _gate("haaer1bgate0018", "haae_r1b_public_input_matrix_non_empty",
              len(PUBLIC_INPUT_ARTIFACTS) > 0),
        _gate("haaer1bgate0019", "haae_r1b_recipe_catalog_covers_10_groups",
              recipe_covers_all),
        _gate("haaer1bgate0020", "haae_r1b_operator_checklist_present",
              len(OPERATOR_CHECKLIST) > 0),
        _gate("haaer1bgate0021", "haae_r1b_private_output_contract_present",
              len(PRIVATE_OUTPUT_CONTRACT) > 0),
        _gate("haaer1bgate0022", "haae_r1b_public_manifest_schema_present",
              len(PUBLIC_MANIFEST_SCHEMA) > 0),
        _gate("haaer1bgate0023", "haae_r1b_r1c_bounded_contract_present",
              len(r1c_contract_records()) > 0),
        _gate("haaer1bgate0024", "docs_readback_match_gate",
              readback["haae_r1b_docs_readback_match_bool"]
              and readback["haae_r1a_docs_readback_match_bool"]),
        _gate("haaer1bgate0025", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("haaer1bgate0026", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("haaer1bgate0027", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("haaer1bgate0028", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("haaer1bgate0029", "self_test_total_public_readback_match_gate",
              readback["self_test_total_public_readback_match_bool"]),
        _gate("haaer1bgate0030", "haae_r0_non_identity_gate", True),
    ]


def synthetic_validator_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_synthetic_validator_id": "haaer1bsynth0000",
            "validator_bucket": "embedded_synthetic_recipe_coverage_fixture",
            "fixture_kind_bucket": "recipe_coverage",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "no_root_regeneration_bool": True,
            "validates_recipe_coverage_bool": True,
            "expected_recipe_group_count": 10,
        },
        {
            "anonymous_synthetic_validator_id": "haaer1bsynth0001",
            "validator_bucket": "embedded_synthetic_r1c_contract_fixture",
            "fixture_kind_bucket": "r1c_contract",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "no_root_regeneration_bool": True,
            "validates_r1c_contract_bool": True,
            "expected_bounded_recipe_only_bool": True,
        },
    ]


def public_package_records(lock_record: dict[str, Any], readback: dict[str, bool],
                           recipe_covers_all: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer1bpackage0000",
        "package_bucket": "haae_r1b_bounded_private_trace_root_regeneration_preflight_package",
        "schema_version": "bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_v1",
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
        "haae_r1a_source_locked_bool": lock_record["source_locked_bool"],
        "haae_r1b_docs_readback_match_bool": readback["haae_r1b_docs_readback_match_bool"],
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
        "recipe_covers_all_groups_bool": recipe_covers_all,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "haaer1bstop0000",
        "next_allowed_phase": NEXT_ROUTE_PASS,
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "design_only_bool": True,
        "haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool": True,
        "haae_r1c_design_only_bool": True,
        "haae_r1c_execution_authorized_bool": False,
        "haae_r1c_private_read_authorized_bool": False,
        "haae_r1c_replay_authorized_bool": False,
        "haae_r1c_scoring_authorized_bool": False,
        "haae_r1c_retrieval_authorized_bool": False,
        "haae_r1c_candidate_generation_authorized_bool": False,
        "haae_r1c_haae_layer_execution_authorized_bool": False,
        "haae_r1c_bounded_recipe_only_bool": True,
        "haae_r1c_unbounded_replay_authorized_bool": False,
        "haae_r1c_unbounded_retrieval_authorized_bool": False,
        "haae_r1c_unbounded_candidate_generation_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
        "haae_r1b_execution_authorized_bool": False,
        "haae_r1b_re_run_authorized_bool": False,
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
    lock_ok, lock_record = evaluate_haae_r1a_source_lock()
    readback = public_readback_match()

    recipe_groups = {r["group_bucket"] for r in RECIPE_CATALOG}
    recipe_covers_all = recipe_groups == set(ALL_GROUP_BUCKETS)

    if not lock_ok:
        status = STATUS_NO_SOURCE
    elif lock_ok and recipe_covers_all:
        status = STATUS_PASS
    else:
        status = STATUS_NO_GO

    report: dict[str, Any] = {
        "schema_version": "bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_v1",
        "phase_bucket": "BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package",
        "status": status,
        "source_lock_records": [lock_record],
        "public_input_records": public_input_records(),
        "recipe_catalog_records": recipe_catalog_records(),
        "operator_checklist_records": operator_checklist_records(),
        "private_output_contract_records": private_output_contract_records(),
        "public_manifest_schema_records": public_manifest_schema_records(),
        "r1c_contract_records": r1c_contract_records(),
        "risk_control_records": risk_control_records(),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback, recipe_covers_all),
        "synthetic_validator_records": synthetic_validator_records(),
        "public_package_records": public_package_records(lock_record, readback, recipe_covers_all),
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "haaer1bgate0000",
             "gate_bucket": "haae_r1a_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "haaer1bgate0011",
             "gate_bucket": "no_ci_rerun_retrieval_recompute",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1bgate0015",
             "gate_bucket": "no_private_input_read",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1bgate0016",
             "gate_bucket": "no_root_regeneration",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1bgate0030",
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
        failures.append("haae_r1a_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("no_root_regeneration_bool") is not True:
        failures.append("root_regeneration_claim_not_true")
    if lock.get("haae_r1b_authorized_match_bool") is not True:
        failures.append("haae_r1b_not_authorized_by_r1a")
    if lock.get("haae_r1b_design_only_match_bool") is not True:
        failures.append("haae_r1b_not_design_only_by_r1a")
    if lock.get("haae_r1b_execution_false_match_bool") is not True:
        failures.append("haae_r1b_execution_not_false_by_r1a")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("haae_r1b_docs_readback_match_bool", "haae_r1a_docs_readback_match_bool",
                  "haae_r1_docs_readback_match_bool", "haae_r0_docs_readback_match_bool",
                  "readme_readback_match_bool", "current_conclusions_match_bool",
                  "research_log_match_bool", "research_summary_match_bool",
                  "self_test_total_public_readback_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Recipe catalog covers all 10 groups.
    recipes = report.get("recipe_catalog_records", [])
    recipe_groups = {r.get("group_bucket") for r in recipes}
    for needed in ALL_GROUP_BUCKETS:
        if needed not in recipe_groups:
            failures.append(f"missing_recipe_for_group_{needed}")
    # Operator checklist present.
    if not report.get("operator_checklist_records"):
        failures.append("operator_checklist_empty")
    # Private output contract present.
    if not report.get("private_output_contract_records"):
        failures.append("private_output_contract_empty")
    # Public manifest schema present.
    if not report.get("public_manifest_schema_records"):
        failures.append("public_manifest_schema_empty")
    # R1C contract present.
    r1c = (report.get("r1c_contract_records") or [{}])[0] if report.get("r1c_contract_records") else {}
    for field in ("explicit_opt_in_required_bool", "private_output_only_bool",
                  "public_manifest_count_only_bool", "bounded_recipe_only_bool",
                  "authorized_for_next_phase_bool"):
        if r1c.get(field) is not True:
            failures.append(f"r1c_contract_{field}_not_true")
    for field in ("unbounded_replay_authorized_bool",
                  "unbounded_retrieval_authorized_bool",
                  "unbounded_candidate_generation_authorized_bool",
                  "scoring_authorized_bool", "selector_authorized_bool",
                  "bea_v1_a_authorized_bool", "p5_authorized_bool",
                  "runtime_default_authorized_bool", "execution_authorized_bool"):
        if r1c.get(field) is not False:
            failures.append(f"r1c_contract_{field}_not_false")
    # Claim boundary.
    claim = (report.get("claim_boundary_records") or [{}])[0] if report.get("claim_boundary_records") else {}
    for field in ("method_winner_claim_bool", "runtime_default_change_bool",
                  "selector_reranker_bool", "threshold_tuning_bool",
                  "frozen_rule_change_bool", "raw_candidate_upload_bool",
                  "raw_label_upload_bool", "raw_path_upload_bool",
                  "raw_query_upload_bool", "raw_filename_upload_bool",
                  "raw_basename_upload_bool", "raw_repo_name_upload_bool",
                  "raw_task_id_upload_bool", "raw_per_task_diagnostics_upload_bool",
                  "scaled_retrieval_claim_bool", "ci_rerun_bool",
                  "retrieval_recompute_bool", "promotion_claim_bool",
                  "candidate_generation_bool", "arm_scoring_bool",
                  "openlocus_execution_bool", "replay_bool",
                  "haae_layer_execution_bool", "root_regeneration_bool",
                  "clone_build_search_bool", "network_run_bool",
                  "provider_model_network_bool",
                  "n10et_execution_authorized_bool", "n10et_re_run_authorized_bool",
                  "haae_r0_execution_authorized_bool",
                  "haae_r1_execution_authorized_bool",
                  "haae_r1a_execution_authorized_bool",
                  "haae_r1b_execution_authorized_bool",
                  "haae_r1c_execution_authorized_bool",
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
    # Stop/go: R1C authorized + design-only; all execution false.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool") is not True:
            failures.append("stop_r1c_not_authorized_on_pass")
        if stop.get("haae_r1c_design_only_bool") is not True:
            failures.append("stop_r1c_not_design_only_on_pass")
    for field in ("haae_r1c_execution_authorized_bool",
                  "haae_r1c_private_read_authorized_bool",
                  "haae_r1c_replay_authorized_bool",
                  "haae_r1c_scoring_authorized_bool",
                  "haae_r1c_retrieval_authorized_bool",
                  "haae_r1c_candidate_generation_authorized_bool",
                  "haae_r1c_haae_layer_execution_authorized_bool",
                  "haae_r1c_unbounded_replay_authorized_bool",
                  "haae_r1c_unbounded_retrieval_authorized_bool",
                  "haae_r1c_unbounded_candidate_generation_authorized_bool",
                  "haae_r1b_execution_authorized_bool",
                  "haae_r1a_execution_authorized_bool",
                  "haae_r1_execution_authorized_bool",
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
                  "design_only_bool", "haae_r1c_design_only_bool",
                  "haae_r1c_bounded_recipe_only_bool"):
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
    checks.append(("scanner_value_tmp", scan_summary({"bucket": "/tmp/foo"})["status"] == "fail"))
    checks.append(("scanner_value_workspace", scan_summary({"bucket": "/workspace/foo"})["status"] == "fail"))
    checks.append(("scanner_value_file_ext", scan_summary({"bucket": "data.jsonl"})["status"] == "fail"))
    checks.append(("scanner_value_task_id", scan_summary({"bucket": "task_abc123"})["status"] == "fail"))
    checks.append(("scanner_value_record_id", scan_summary({"bucket": "record_xyz789"})["status"] == "fail"))
    checks.append(("scanner_value_case_id", scan_summary({"bucket": "case_00123"})["status"] == "fail"))
    checks.append(("scanner_value_ci_id", scan_summary({"bucket": "ci-00001"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_passes_clean", scan_summary({"status": "ok", "count": 7})["status"] == "pass"))
    checks.append(("scanner_key_candidate", scan_summary({"candidate": "x"})["status"] == "fail"))
    checks.append(("scanner_key_query", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_key_span", scan_summary({"span": "x"})["status"] == "fail"))
    checks.append(("scanner_key_score", scan_summary({"score": "x"})["status"] == "fail"))
    checks.append(("scanner_key_repo", scan_summary({"repo": "x"})["status"] == "fail"))
    checks.append(("scanner_forbidden_sequence", scan_summary({"bucket": "path line_range content_sha score"})["status"] == "fail"))

    # Locked constants.
    checks.append(("locked_haae_r1a_checkpoint", LOCKED_HAAE_R1A_CHECKPOINT == "e54d1b4"))
    checks.append(("locked_haae_r1a_status",
                   LOCKED_HAAE_R1A_STATUS == "haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized"))
    checks.append(("locked_haae_r1_checkpoint", LOCKED_HAAE_R1_CHECKPOINT == "2ea77da"))
    checks.append(("locked_haae_r0_checkpoint", LOCKED_HAAE_R0_CHECKPOINT == "854fc2e"))
    checks.append(("locked_n10et_checkpoint", LOCKED_N10ET_CHECKPOINT == "26d817e"))
    checks.append(("haae_r1b_non_identities",
                   set(HAAE_R1B_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))
    checks.append(("schema_group_count", len(SCHEMA_GROUPS) == 10))
    checks.append(("critical_group_count", len(CRITICAL_GROUPS) == 5))
    checks.append(("next_route_pass", "HAAE-R1C" in NEXT_ROUTE_PASS
                   and "Bounded Private Trace Root Regeneration Smoke" in NEXT_ROUTE_PASS))
    checks.append(("public_input_count", len(PUBLIC_INPUT_ARTIFACTS) >= 10))
    checks.append(("recipe_count", len(RECIPE_CATALOG) == 10))
    checks.append(("operator_count", len(OPERATOR_CHECKLIST) >= 5))
    checks.append(("private_output_contract_count", len(PRIVATE_OUTPUT_CONTRACT) >= 3))
    checks.append(("manifest_schema_count", len(PUBLIC_MANIFEST_SCHEMA) >= 5))

    # Recipe covers all 10 groups.
    recipe_groups = {r["group_bucket"] for r in RECIPE_CATALOG}
    checks.append(("recipe_covers_all_10_groups", recipe_groups == set(ALL_GROUP_BUCKETS)))

    # Source lock.
    lock_ok, lock_record = evaluate_haae_r1a_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_haae_r1a_status_match",
                   lock_record["haae_r1a_status_match_bool"] is True))
    checks.append(("source_lock_r1b_authorized_match",
                   lock_record["haae_r1b_authorized_match_bool"] is True))
    checks.append(("source_lock_r1b_design_only_match",
                   lock_record["haae_r1b_design_only_match_bool"] is True))
    checks.append(("source_lock_r1b_execution_false_match",
                   lock_record["haae_r1b_execution_false_match_bool"] is True))
    checks.append(("source_lock_r1b_private_read_false_match",
                   lock_record["haae_r1b_private_read_false_match_bool"] is True))
    checks.append(("source_lock_non_identity_match",
                   lock_record["haae_r0_non_identity_match_bool"] is True))
    checks.append(("source_lock_gap_count_match",
                   lock_record["coverage_gap_count_match_bool"] is True))

    readback = public_readback_match()
    checks.append(("readback_r1b_docs_match",
                   readback["haae_r1b_docs_readback_match_bool"] is True))
    checks.append(("readback_r1a_docs_match",
                   readback["haae_r1a_docs_readback_match_bool"] is True))
    checks.append(("readback_r1_docs_match",
                   readback["haae_r1_docs_readback_match_bool"] is True))
    checks.append(("readback_r0_docs_match",
                   readback["haae_r0_docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))
    checks.append(("readback_log_match", readback["research_log_match_bool"] is True))
    checks.append(("readback_summary_match", readback["research_summary_match_bool"] is True))
    checks.append(("readback_self_test_total",
                   readback["self_test_total_public_readback_match_bool"] is True))

    # Recipe catalog records.
    recipes = recipe_catalog_records()
    checks.append(("recipes_count_10", len(recipes) == 10))
    checks.append(("recipes_all_design_only",
                   all(r["design_only_bool"] is True for r in recipes)))
    checks.append(("recipes_all_bounded",
                   all(r["bounded_recipe_bool"] is True for r in recipes)))
    checks.append(("recipes_all_no_raw_release",
                   all(r["no_raw_release_bool"] is True for r in recipes)))

    # Operator checklist.
    ops = operator_checklist_records()
    checks.append(("ops_present", len(ops) >= 5))
    checks.append(("ops_all_safe", all(o["safe_operator_bool"] is True for o in ops)))
    checks.append(("ops_all_design_only", all(o["design_only_bool"] is True for o in ops)))

    # Private output contract.
    contracts = private_output_contract_records()
    checks.append(("contracts_present", len(contracts) >= 3))
    checks.append(("contracts_no_raw_release",
                   all(c["no_raw_release_bool"] is True for c in contracts)))

    # Public manifest schema.
    manifests = public_manifest_schema_records()
    checks.append(("manifests_present", len(manifests) >= 5))
    checks.append(("manifests_aggregate_only",
                   all(r["aggregate_bucket_only_bool"] is True for r in manifests)))

    # R1C contract.
    r1c = r1c_contract_records()[0]
    checks.append(("r1c_explicit_opt_in", r1c["explicit_opt_in_required_bool"] is True))
    checks.append(("r1c_private_output_only", r1c["private_output_only_bool"] is True))
    checks.append(("r1c_public_manifest_only", r1c["public_manifest_count_only_bool"] is True))
    checks.append(("r1c_bounded_recipe_only", r1c["bounded_recipe_only_bool"] is True))
    checks.append(("r1c_no_unbounded_replay", r1c["unbounded_replay_authorized_bool"] is False))
    checks.append(("r1c_no_unbounded_retrieval", r1c["unbounded_retrieval_authorized_bool"] is False))
    checks.append(("r1c_no_unbounded_candidate_gen", r1c["unbounded_candidate_generation_authorized_bool"] is False))
    checks.append(("r1c_no_scoring", r1c["scoring_authorized_bool"] is False))
    checks.append(("r1c_no_selector", r1c["selector_authorized_bool"] is False))
    checks.append(("r1c_no_bea_v1_a", r1c["bea_v1_a_authorized_bool"] is False))
    checks.append(("r1c_no_p5", r1c["p5_authorized_bool"] is False))
    checks.append(("r1c_no_runtime", r1c["runtime_default_authorized_bool"] is False))
    checks.append(("r1c_authorized_for_next_phase", r1c["authorized_for_next_phase_bool"] is True))

    # Risk controls.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == 6))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))

    # Stop/go.
    stop = stop_go_records()[0]
    checks.append(("stop_r1c_authorized",
                   stop["haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool"] is True))
    checks.append(("stop_r1c_design_only", stop["haae_r1c_design_only_bool"] is True))
    checks.append(("stop_r1c_no_exec", stop["haae_r1c_execution_authorized_bool"] is False))
    checks.append(("stop_r1c_no_private_read", stop["haae_r1c_private_read_authorized_bool"] is False))
    checks.append(("stop_r1c_no_unbounded_replay", stop["haae_r1c_unbounded_replay_authorized_bool"] is False))
    checks.append(("stop_no_selector_p5_bea_v1_a",
                   stop["selector_reranker_authorized_bool"] is False
                   and stop["p5_authorized_bool"] is False
                   and stop["bea_v1_a_authorized_bool"] is False))
    checks.append(("stop_no_root_regeneration",
                   stop["root_regeneration_authorized_bool"] is False))
    checks.append(("stop_haae_r0_non_identity",
                   stop["haae_r0_not_bea_v1_a_bool"] is True
                   and stop["haae_r0_not_p5_bool"] is True))

    # Claim boundary.
    cb = claim_boundary_records()[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_only_true", cb["design_only_bool"] is True))
    checks.append(("claim_no_root_regeneration", cb["root_regeneration_bool"] is False))
    checks.append(("claim_no_clone_build_search", cb["clone_build_search_bool"] is False))
    checks.append(("claim_r1c_execution_false", cb["haae_r1c_execution_authorized_bool"] is False))
    checks.append(("claim_haae_r0_non_identity",
                   cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Synthetic validators.
    synths = synthetic_validator_records()
    checks.append(("synths_count", len(synths) == 2))
    checks.append(("synths_no_real_data",
                   all(r["no_real_data_bool"] is True for r in synths)))

    # Full report build + validation.
    report = build_report()
    checks.append(("report_status_pass", report["status"] == STATUS_PASS))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields",
                   package["haae_r1b_docs_readback_match_bool"] is True
                   and package["haae_r1a_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))
    checks.append(("report_recipe_covers_all",
                   package["recipe_covers_all_groups_bool"] is True))
    checks.append(("report_stop_r1c_authorized",
                   report["stop_go_records"][0]
                   ["haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool"] is True))
    checks.append(("report_stop_no_execution",
                   report["stop_go_records"][0]["execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["haae_r1c_execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["root_regeneration_authorized_bool"] is False))

    # Bad-contract detection.
    bad = dict(report)
    bad["stop_go_records"] = [{**stop_go_records()[0],
                               "haae_r1c_execution_authorized_bool": True}]
    checks.append(("validate_fails_r1c_execution",
                   any("haae_r1c_execution_authorized_bool_not_false" in f
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
    bad4["stop_go_records"] = [{**stop_go_records()[0],
                                 "bea_v1_a_authorized_bool": True}]
    checks.append(("validate_fails_bea_v1_a",
                   any("bea_v1_a_authorized_bool_not_false" in f
                       for f in validate_report(bad4))))
    bad5 = dict(report)
    bad5["recipe_catalog_records"] = report["recipe_catalog_records"][:-1]
    checks.append(("validate_fails_recipe_count",
                   any("missing_recipe_for_group_" in f
                       for f in validate_report(bad5))))
    bad6 = dict(report)
    bad6["r1c_contract_records"] = [{**r1c_contract_records()[0],
                                       "unbounded_replay_authorized_bool": True}]
    checks.append(("validate_fails_r1c_unbounded",
                   any("r1c_contract_unbounded_replay_authorized_bool_not_false" in f
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
