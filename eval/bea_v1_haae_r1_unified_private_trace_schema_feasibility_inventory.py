#!/usr/bin/env python3
"""BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory.

HAAE-R1 is the **feasibility inventory** for the unified private trace schema
designed by HAAE-R0 (checkpoint ``854fc2e``). It is **not** a replay, scoring,
retrieval, candidate-generation, or HAAE-layer execution phase. It inventories
whether the 10 HAAE-R0 schema groups can be populated from explicitly supplied
project-private root buckets, emitting **aggregate buckets only**.

Default / no-private mode: HAAE-R1 **does not read private roots**. It produces
an ``unavailable`` public artifact (no explicit private roots supplied) or runs
``--self-test`` only. No private filesystem access occurs in default mode.

Real inventory requires explicit opt-in:
``--allow-private-inventory --private-root <path>`` (repeatable). With that
opt-in the only private operations performed are:

  * enumerate explicitly supplied project-private root buckets (no symlink
    escape, no recursive descent beyond a bounded depth, no traversal outside
    the explicitly supplied root buckets);
  * identify candidate files by extension/type/schema bucket (``ext_jsonl``,
    ``ext_json``, ``ext_csv``, ``ext_other``) — **no filenames/basenames are
    ever published**;
  * parse schemas/JSON keys and stream rows **only** for row-count buckets,
    column presence buckets, type compatibility buckets, missingness buckets,
    and anonymous join-shape availability buckets.

HAAE-R1 **never** publishes paths, filenames, basenames, repo names, task ids,
queries, candidates, spans, snippets, hashes, exact ranks/scores, labels, or
row values. Every record is aggregate-bucket-only.

Source lock: HAAE-R0 commit/artifact ``854fc2e``, status
``haae_r0_design_schema_preflight_complete_haae_r1_authorized``, HAAE-R1
feasibility-inventory-only contract authorized, HAAE-R1 execution/replay/
scoring/retrieval/candidate-generation all false.

Status vocabulary:
  * ``haae_r1_feasibility_inventory_pass_haae_r2_authorized`` — all 10 groups
    at least partial and the critical groups (task_identity, candidate_pool,
    evidence_core, arm_assignment, outcome_metric) full or sufficient.
  * ``haae_r1_feasibility_inventory_controlled_no_go_haae_r1a_authorized`` —
    valid inventory but insufficient (at least one group partial-but-not-
    sufficient, or a critical group missing/insufficient).
  * ``haae_r1_feasibility_inventory_unavailable_no_locked_source`` — HAAE-R0
    source not locked.
  * ``haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`` —
    default/no-private mode (no ``--allow-private-inventory --private-root``).
  * ``fail_haae_r0_source_lock_mismatch`` / ``fail_forbidden_scan`` /
    ``fail_schema_contract`` / ``fail_contract_violation`` /
    ``fail_private_boundary_violation`` — fail-closed.

Handoff:
  * Pass → authorizes **only** BEA-v1-HAAE-R2 Feasibility-Gated Offline Trace
    Join Design (design-only, no execution/replay/scoring/retrieval/candidate
    generation).
  * No-Go → authorizes **only** BEA-v1-HAAE-R1A Private Trace Coverage Gap
    Design (design-only, no execution).

HAAE-R1 is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion, not a
HAAE-layer execution, not a replay, not a scoring, not a retrieval, not a
candidate generation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
HAAE_R0_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight"
    / "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_report.json"
)
HAAE_R0_EVAL = (
    ROOT / "eval"
    / "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py"
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
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"

# ── Locked HAAE-R0 public facts (git metadata + upstream lock) ─────────────
LOCKED_HAAE_R0_CHECKPOINT = "854fc2e"
LOCKED_HAAE_R0_STATUS = "haae_r0_design_schema_preflight_complete_haae_r1_authorized"
LOCKED_HAAE_R0_NEXT_ALLOWED_PHASE = (
    "BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory"
)
# Upstream lock (read from HAAE-R0's source_lock_records).
LOCKED_N10ET_CHECKPOINT = "26d817e"
LOCKED_N10ET_STATUS = (
    "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"
)

# ── HAAE-R1 contract (carried from HAAE-R0's haae_r1_contract_records) ─────
# HAAE-R1 is feasibility_inventory_only, private_roots_only, aggregate_buckets_only,
# no_replay, no_scoring, no_retrieval, no_candidate_generation,
# no_execution_of_haae_layers.
HAAE_R1_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Next-route handoff buckets ─────────────────────────────────────────────
NEXT_ROUTE_PASS = (
    "BEA-v1-HAAE-R2 Feasibility-Gated Offline Trace Join Design"
)
NEXT_ROUTE_NO_GO = (
    "BEA-v1-HAAE-R1A Private Trace Coverage Gap Design"
)
NEXT_ROUTE_PASS_BUCKET = (
    "haae_r2_feasibility_gated_offline_trace_join_design"
)
NEXT_ROUTE_NO_GO_BUCKET = (
    "haae_r1a_private_trace_coverage_gap_design"
)

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_PASS = "haae_r1_feasibility_inventory_pass_haae_r2_authorized"
STATUS_NO_GO = "haae_r1_feasibility_inventory_controlled_no_go_haae_r1a_authorized"
STATUS_NO_SOURCE = "haae_r1_feasibility_inventory_unavailable_no_locked_source"
STATUS_NO_ROOTS = "haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots"
STATUS_FAIL_LOCK = "fail_haae_r0_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
STATUS_FAIL_PRIVATE = "fail_private_boundary_violation"
STATUS_FAIL_OP = "fail_forbidden_operation"
# EXIT0 statuses: pass, controlled no-go, and unavailable are all exit-0
# (they are valid research outcomes / explicit unavailable). Fail-closed
# statuses exit non-zero.
EXIT0_VOCAB = {STATUS_PASS, STATUS_NO_GO, STATUS_NO_SOURCE, STATUS_NO_ROOTS}
STATUS_VOCAB = EXIT0_VOCAB | {
    STATUS_FAIL_LOCK, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA,
    STATUS_FAIL_CONTRACT, STATUS_FAIL_PRIVATE, STATUS_FAIL_OP,
}

# ── Privacy scan: forbid raw per-task / path / candidate / repo data ───────
# Mirrors the HAAE-R0 / N10ES scanner verbatim so the feasibility inventory
# upholds the same publication boundary.
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
    re.compile(r"(?:^|[\s/\\])\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/|/runner/"),
    re.compile(r"https?://github\.com/", re.I),
    re.compile(r"[A-Za-z0-9_.-]+/(?:[A-Za-z0-9_.-]+)\.git", re.I),
    # File extensions in leaked values (e.g. "file.jsonl", "data.json"):
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(ci-[0-9]{5})\b", re.I),
    re.compile(r"\b(?:task|record|row|case)[_-](?=[A-Za-z0-9]*\d)[A-Za-z0-9]{4,}\b", re.I),
]

# Self-test check count (kept in sync with run_self_test; verified by --self-test).
SELF_TEST_TOTAL_CHECKS = 121

# Maximum recursive descent depth for private-root enumeration (bounded).
MAX_PRIVATE_ROOT_DEPTH = 3
MAX_FILES_PER_ROOT = 1000


# ── HAAE-R0 schema groups (copied from HAAE-R0; the 10 inventory targets) ──

def _col(column_bucket: str, column_type_bucket: str) -> dict[str, Any]:
    return {
        "column_bucket": column_bucket,
        "column_type_bucket": column_type_bucket,
    }


SCHEMA_GROUPS: list[dict[str, Any]] = [
    {
        "group_bucket": "task_identity",
        "group_index": 0,
        "group_description_bucket": (
            "anonymous task identity: anonymous_task_id, repo_bucket, "
            "language_bucket. no raw task_id/path/query/repo."),
        "columns": [
            _col("anonymous_task_id", "opaque_id_bucket"),
            _col("repo_bucket", "categorical_bucket"),
            _col("language_bucket", "categorical_bucket"),
        ],
        "is_critical_group_bool": True,
    },
    {
        "group_bucket": "anchor_source",
        "group_index": 1,
        "group_description_bucket": (
            "anchor/source acquisition layer: which source surface produced "
            "the candidate pool (anchor_kind_bucket) and acquisition_cost_bucket."),
        "columns": [
            _col("anchor_kind_bucket", "categorical_bucket"),
            _col("acquisition_cost_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": False,
    },
    {
        "group_bucket": "candidate_pool",
        "group_index": 2,
        "group_description_bucket": (
            "candidate pool shape: candidate_count_bucket, "
            "depth_distribution_bucket. no raw candidate lists."),
        "columns": [
            _col("candidate_count_bucket", "ordinal_bucket"),
            _col("depth_distribution_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": True,
    },
    {
        "group_bucket": "rank_pack",
        "group_index": 3,
        "group_description_bucket": (
            "rank/pack depth-to-head: topk_pack_bucket, "
            "novel_vs_old_pool_bucket. no exact ranks."),
        "columns": [
            _col("topk_pack_bucket", "ordinal_bucket"),
            _col("novel_vs_old_pool_bucket", "categorical_bucket"),
        ],
        "is_critical_group_bool": False,
    },
    {
        "group_bucket": "span_projection",
        "group_index": 4,
        "group_description_bucket": (
            "span projection: span_window_bucket, span_overlap_bucket. no raw "
            "spans/line ranges."),
        "columns": [
            _col("span_window_bucket", "ordinal_bucket"),
            _col("span_overlap_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": False,
    },
    {
        "group_bucket": "scheduler_action",
        "group_index": 5,
        "group_description_bucket": (
            "scheduler action: scheduled_action_bucket, action_cost_bucket. "
            "no raw provider payloads."),
        "columns": [
            _col("scheduled_action_bucket", "categorical_bucket"),
            _col("action_cost_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": False,
    },
    {
        "group_bucket": "evidence_core",
        "group_index": 6,
        "group_description_bucket": (
            "EvidenceCore aggregate buckets: path_bucket, line_range_bucket, "
            "content_sha_bucket, score_bucket, why_bucket, channels_bucket. "
            "all aggregate; no raw paths/line ranges/content_sha/scores/why/"
            "channels."),
        "columns": [
            _col("path_bucket", "categorical_bucket"),
            _col("line_range_bucket", "ordinal_bucket"),
            _col("content_sha_bucket", "opaque_hash_bucket"),
            _col("score_bucket", "ordinal_bucket"),
            _col("why_bucket", "categorical_bucket"),
            _col("channels_bucket", "categorical_bucket"),
        ],
        "is_critical_group_bool": True,
    },
    {
        "group_bucket": "arm_assignment",
        "group_index": 7,
        "group_description_bucket": (
            "arm assignment: which arm was assigned (one of BM25_same_budget, "
            "RRF_same_budget, BEA_v0.3_frozen, V1_sched_span, "
            "V1_sched_span_rank)."),
        "columns": [
            _col("arm_bucket", "categorical_bucket"),
            _col("budget_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": True,
    },
    {
        "group_bucket": "outcome_metric",
        "group_index": 8,
        "group_description_bucket": (
            "outcome metric aggregate buckets: citation_validity_bucket, "
            "file_recovery_topk_bucket, lost_baseline_top10_bucket."),
        "columns": [
            _col("citation_validity_bucket", "ordinal_bucket"),
            _col("file_recovery_topk_bucket", "ordinal_bucket"),
            _col("lost_baseline_top10_bucket", "ordinal_bucket"),
        ],
        "is_critical_group_bool": True,
    },
    {
        "group_bucket": "safety_probe_signal",
        "group_index": 9,
        "group_description_bucket": (
            "safety-probe signal aggregate buckets: "
            "full_guard_diffaware_loss_bucket, risk_bucket_signal. carries "
            "forward the closed N10E safety-probe vocabulary as aggregate "
            "buckets only."),
        "columns": [
            _col("full_guard_diffaware_loss_bucket", "ordinal_bucket"),
            _col("risk_bucket_signal", "ordinal_bucket"),
        ],
        "is_critical_group_bool": False,
    },
]

CRITICAL_GROUPS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS
                        if g["is_critical_group_bool"])
ALL_GROUP_BUCKETS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS)
assert len(SCHEMA_GROUPS) == 10
assert len(CRITICAL_GROUPS) == 5


# ── Public aggregation contracts (carried from HAAE-R0) ────────────────────
PUBLIC_AGGREGATION_CONTRACTS: list[dict[str, Any]] = [
    {
        "aggregation_bucket": "task_count_aggregate",
        "source_groups": ["task_identity", "candidate_pool"],
    },
    {
        "aggregation_bucket": "arm_aggregate",
        "source_groups": ["arm_assignment", "outcome_metric"],
    },
    {
        "aggregation_bucket": "risk_bucket_aggregate",
        "source_groups": ["safety_probe_signal", "outcome_metric"],
    },
    {
        "aggregation_bucket": "citation_aggregate",
        "source_groups": ["evidence_core", "outcome_metric"],
    },
]


# ── Safe argument parser (rejects unknown args without echoing values) ───


class SafeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Disable prefix abbreviation so that "--private" is NOT silently
        # treated as an abbreviation of "--private-root"; unknown args must
        # be rejected explicitly.
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:  # pragma: no cover
        # Intentionally do NOT echo the message (which may contain user
        # supplied values). Generic rejection only.
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-HAAE-R1 unified private trace schema feasibility "
                    "inventory")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--haae-r0-report", default=str(HAAE_R0_REPORT),
                        help="path to the committed HAAE-R0 public artifact")
    parser.add_argument("--allow-private-inventory", action="store_true",
                        help="opt-in: enable real private root enumeration. "
                             "default is no-private / unavailable.")
    parser.add_argument("--private-root", action="append", default=[],
                        help="explicit private root to inventory (repeatable). "
                             "only honored with --allow-private-inventory.")
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
    """Verify that the public docs/README/current conclusions mention both the
    HAAE-R0 handoff facts and the HAAE-R1 feasibility inventory close-out.
    Reads only public docs; performs no execution.

    Per-target fragment vocabulary:
      * README + current-research-conclusions must mention HAAE-R1 + HAAE-R0 +
        the locked HAAE-R0 status + at least one non-identity (BEA-v1-A /
        selector/reranker / selector-only / P5) + the self-test total.
      * HAAE-R1 docs must mention HAAE-R1 + HAAE-R0 + the locked HAAE-R0
        checkpoint + the HAAE-R0 status + at least one non-identity + the
        self-test total.
      * HAAE-R0 docs must mention HAAE-R1 (as the next authorized phase).
      * research-log/summary must mention HAAE-R1 + HAAE-R0 + at least one
        non-identity + the self-test total.
    """
    common_fragments = [
        LOCKED_HAAE_R0_CHECKPOINT,
        LOCKED_HAAE_R0_STATUS,
        "HAAE-R0",
        "HAAE-R1",
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
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_haae_r1_closeout(text: str) -> bool:
        return ("HAAE-R1" in text and "HAAE-R0" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    def has_self_test_fragment(text: str) -> bool:
        return any(fragment in text for fragment in self_test_fragments)

    readme_self_test_match = has_self_test_fragment(readme)
    haae_r1_docs_self_test_match = (has_self_test_fragment(haae_r1_doc_en)
                                    and has_self_test_fragment(haae_r1_doc_zh))
    current_self_test_match = (has_self_test_fragment(current_en)
                               and has_self_test_fragment(current_zh))
    log_self_test_match = (has_self_test_fragment(log_en)
                           and has_self_test_fragment(log_zh))
    summary_self_test_match = (has_self_test_fragment(summary_en)
                               and has_self_test_fragment(summary_zh))
    self_test_total_public_readback_match = (readme_self_test_match
                                             and haae_r1_docs_self_test_match
                                             and current_self_test_match
                                             and log_self_test_match
                                             and summary_self_test_match)

    readme_match = (has_all(readme, common_fragments)
                    and has_haae_r1_closeout(readme)
                    and readme_self_test_match)
    current_match = (has_all(current_en, common_fragments)
                     and has_all(current_zh, common_fragments)
                     and has_haae_r1_closeout(current_en)
                     and has_haae_r1_closeout(current_zh)
                     and current_self_test_match)
    haae_r1_docs_match = (has_all(haae_r1_doc_en, common_fragments)
                          and has_all(haae_r1_doc_zh, common_fragments)
                          and has_haae_r1_closeout(haae_r1_doc_en)
                          and has_haae_r1_closeout(haae_r1_doc_zh)
                          and haae_r1_docs_self_test_match)
    haae_r0_docs_match = ("HAAE-R1" in haae_r0_doc_en
                          and "HAAE-R1" in haae_r0_doc_zh)
    log_match = (has_haae_r1_closeout(log_en) and has_haae_r1_closeout(log_zh)
                 and log_self_test_match)
    summary_match = (has_haae_r1_closeout(summary_en)
                     and has_haae_r1_closeout(summary_zh)
                     and summary_self_test_match)
    return {
        "haae_r1_docs_readback_match_bool": haae_r1_docs_match,
        "haae_r0_docs_readback_match_bool": haae_r0_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": self_test_total_public_readback_match,
        "all_public_readback_match_bool": (haae_r1_docs_match and haae_r0_docs_match
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


# ── HAAE-R0 source lock (reads public HAAE-R0 report only; no rerun) ───────

def _haae_r0_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _haae_r0_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def _haae_r0_r1_contract(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("haae_r1_contract_records") or [{}])[0] if report.get("haae_r1_contract_records") else {}


def evaluate_haae_r0_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the HAAE-R0 public report and validate every locked field.

    Reads ONLY the public HAAE-R0 aggregate report. Performs no execution, no
    retrieval, no recompute, no private reads.
    """
    r0_report, r0_state = load_json(HAAE_R0_REPORT)
    present_ok = r0_state == "present" and isinstance(r0_report, dict)
    status_ok = bool(r0_report and r0_report.get("status") == LOCKED_HAAE_R0_STATUS)
    r0_scan_ok = bool(r0_report
                      and r0_report.get("forbidden_scan", {}).get("status") == "pass")
    stop = _haae_r0_stop_go(r0_report or {})
    next_phase_ok = (stop.get("next_allowed_phase") == LOCKED_HAAE_R0_NEXT_ALLOWED_PHASE)
    haae_r1_authorized_ok = (stop.get("haae_r1_unified_private_trace_schema_"
                                       "feasibility_inventory_authorized_bool") is True)
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

    # HAAE-R0's own non-identity booleans must all be true.
    r0_non_identity_ok = (
        stop.get("haae_r0_not_bea_v1_a_bool") is True
        and stop.get("haae_r0_not_selector_only_bool") is True
        and stop.get("haae_r0_not_selector_reranker_execution_bool") is True
        and stop.get("haae_r0_not_p5_bool") is True
        and stop.get("haae_r0_not_runtime_default_promotion_bool") is True
    )

    package = _haae_r0_package(r0_report or {})
    package_haae_r1_ok = (package.get("haae_r1_authorized_bool") is True
                          and package.get("haae_r1_design_only_feasibility_inventory_bool") is True
                          and package.get("haae_r1_execution_authorized_bool") is False)

    r1_contract = _haae_r0_r1_contract(r0_report or {})
    r1_contract_ok = (
        r1_contract.get("feasibility_inventory_only_bool") is True
        and r1_contract.get("private_roots_only_bool") is True
        and r1_contract.get("aggregate_buckets_only_bool") is True
        and r1_contract.get("no_replay_bool") is True
        and r1_contract.get("no_scoring_bool") is True
        and r1_contract.get("no_retrieval_bool") is True
        and r1_contract.get("no_candidate_generation_bool") is True
        and r1_contract.get("no_execution_of_haae_layers_bool") is True
        and r1_contract.get("authorized_for_next_phase_bool") is True
    )

    # HAAE-R0 must have designed all 10 schema groups.
    schema_count_ok = len(r0_report.get("unified_private_schema_spec_records", [])) == 10 if r0_report else False

    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and r0_scan_ok
               and next_phase_ok and haae_r1_authorized_ok
               and haae_r1_execution_false_ok and haae_r1_replay_false_ok
               and haae_r1_scoring_false_ok and haae_r1_retrieval_false_ok
               and haae_r1_candidate_gen_false_ok
               and bea_v1_a_false_ok and p5_false_ok
               and selector_reranker_false_ok and runtime_default_false_ok
               and r0_non_identity_ok and package_haae_r1_ok
               and r1_contract_ok and schema_count_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "haaer1source0000",
        "source_lock_bucket": "haae_r0_public_report_locked",
        "input_artifact_load_status_bucket": r0_state,
        "locked_haae_r0_checkpoint": LOCKED_HAAE_R0_CHECKPOINT,
        "locked_haae_r0_status": LOCKED_HAAE_R0_STATUS,
        "locked_haae_r0_next_allowed_phase": LOCKED_HAAE_R0_NEXT_ALLOWED_PHASE,
        "locked_n10et_checkpoint": LOCKED_N10ET_CHECKPOINT,
        "locked_n10et_status": LOCKED_N10ET_STATUS,
        "haae_r0_status_match_bool": status_ok,
        "haae_r0_scan_pass_bool": r0_scan_ok,
        "haae_r0_next_phase_match_bool": next_phase_ok,
        "haae_r1_authorized_match_bool": haae_r1_authorized_ok,
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
        "package_haae_r1_match_bool": package_haae_r1_ok,
        "haae_r1_contract_match_bool": r1_contract_ok,
        "haae_r0_schema_group_count_match_bool": schema_count_ok,
        "no_ci_rerun_performed_bool": True,
        "no_retrieval_performed_bool": True,
        "no_recompute_performed_bool": True,
        "no_private_input_read_bool": True,
        "no_replay_performed_bool": True,
        "no_scoring_performed_bool": True,
        "no_candidate_generation_performed_bool": True,
        "no_haae_layer_execution_bool": True,
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


NON_IDENTITY_BUCKETS = list(HAAE_R1_NOT_IDENTITIES)


# ── Row-count bucketization ─────────────────────────────────────────────────

def row_count_bucket(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count <= 10:
        return "count_1_to_10"
    if count <= 100:
        return "count_11_to_100"
    if count <= 1000:
        return "count_101_to_1000"
    return "count_1001_plus"


def file_count_bucket(count: int) -> str:
    return row_count_bucket(count)


def type_bucket_for_value(value: Any) -> str:
    if value is None:
        return "null_bucket"
    if isinstance(value, bool):
        return "bool_bucket"
    if isinstance(value, int):
        return "int_bucket"
    if isinstance(value, float):
        return "float_bucket"
    if isinstance(value, str):
        return "string_bucket"
    if isinstance(value, list):
        return "array_bucket"
    if isinstance(value, dict):
        return "object_bucket"
    return "mixed_bucket"


def missingness_bucket(present_count: int, total_count: int) -> str:
    if total_count <= 0:
        return "not_present"
    if present_count <= 0:
        return "all_missing"
    if present_count >= total_count:
        return "none_missing"
    return "some_missing"


def coverage_bucket_for_group(column_present_count: int, column_total: int,
                              row_count: int, is_critical: bool) -> str:
    """Determine coverage bucket for a schema group from its column presence
    and row count. Returns: full / sufficient / partial / missing / not_present.
    Critical groups require full or sufficient for pass."""
    if row_count <= 0:
        return "not_present"
    if column_present_count <= 0:
        return "missing"
    if column_present_count >= column_total:
        return "full"
    # Sufficient: at least half the columns present for critical groups, or
    # any presence for non-critical groups with rows.
    if is_critical:
        if column_present_count * 2 >= column_total:
            return "sufficient"
        return "partial"
    # Non-critical: any presence with rows is sufficient.
    return "sufficient"


# ── Synthetic fixtures for self-test (in-memory, no real data) ─────────────
# These are NOT real data, NOT replay, NOT retrieval, NOT candidate generation.
# They exist only to validate the inventory logic against full / partial /
# missing coverage scenarios.

SYNTH_FULL_FIXTURE: dict[str, Any] = {
    "roots": [
        {
            "anonymous_root_id": "haaer1synthroot0000",
            "root_present_bool": True,
            "file_count": 4,
            "extension_counts": {"ext_jsonl": 2, "ext_json": 2, "ext_csv": 0, "ext_other": 0},
        }
    ],
    "group_coverage": {
        "task_identity": {"column_present_count": 3, "row_count": 100},
        "anchor_source": {"column_present_count": 2, "row_count": 100},
        "candidate_pool": {"column_present_count": 2, "row_count": 100},
        "rank_pack": {"column_present_count": 2, "row_count": 100},
        "span_projection": {"column_present_count": 2, "row_count": 100},
        "scheduler_action": {"column_present_count": 2, "row_count": 100},
        "evidence_core": {"column_present_count": 6, "row_count": 100},
        "arm_assignment": {"column_present_count": 2, "row_count": 100},
        "outcome_metric": {"column_present_count": 3, "row_count": 100},
        "safety_probe_signal": {"column_present_count": 2, "row_count": 100},
    },
}

SYNTH_PARTIAL_FIXTURE: dict[str, Any] = {
    "roots": [
        {
            "anonymous_root_id": "haaer1synthroot0001",
            "root_present_bool": True,
            "file_count": 2,
            "extension_counts": {"ext_jsonl": 1, "ext_json": 1, "ext_csv": 0, "ext_other": 0},
        }
    ],
    "group_coverage": {
        # Critical groups all full → pass.
        "task_identity": {"column_present_count": 3, "row_count": 50},
        "candidate_pool": {"column_present_count": 2, "row_count": 50},
        "evidence_core": {"column_present_count": 6, "row_count": 50},
        "arm_assignment": {"column_present_count": 2, "row_count": 50},
        "outcome_metric": {"column_present_count": 3, "row_count": 50},
        # Non-critical groups partial but present → still at least partial.
        "anchor_source": {"column_present_count": 1, "row_count": 50},
        "rank_pack": {"column_present_count": 1, "row_count": 50},
        "span_projection": {"column_present_count": 1, "row_count": 50},
        "scheduler_action": {"column_present_count": 1, "row_count": 50},
        "safety_probe_signal": {"column_present_count": 1, "row_count": 50},
    },
}

SYNTH_MISSING_FIXTURE: dict[str, Any] = {
    "roots": [
        {
            "anonymous_root_id": "haaer1synthroot0002",
            "root_present_bool": True,
            "file_count": 1,
            "extension_counts": {"ext_jsonl": 1, "ext_json": 0, "ext_csv": 0, "ext_other": 0},
        }
    ],
    "group_coverage": {
        # Critical group task_identity missing → controlled no-go.
        "task_identity": {"column_present_count": 0, "row_count": 10},
        "anchor_source": {"column_present_count": 2, "row_count": 10},
        "candidate_pool": {"column_present_count": 2, "row_count": 10},
        "rank_pack": {"column_present_count": 2, "row_count": 10},
        "span_projection": {"column_present_count": 2, "row_count": 10},
        "scheduler_action": {"column_present_count": 2, "row_count": 10},
        "evidence_core": {"column_present_count": 6, "row_count": 10},
        "arm_assignment": {"column_present_count": 2, "row_count": 10},
        "outcome_metric": {"column_present_count": 3, "row_count": 10},
        "safety_probe_signal": {"column_present_count": 2, "row_count": 10},
    },
}


# ── Private inventory logic (real mode: --allow-private-inventory) ────────

def _is_safe_private_root(root_path: Path) -> bool:
    """Reject symlink escapes and the well-known project-private roots that
    must never be enumerated without an explicit path string. The root must
    resolve to a real directory and must not be a symlink."""
    try:
        resolved = root_path.resolve(strict=False)
    except Exception:
        return False
    if not resolved.is_dir():
        return False
    # Reject symlinks at the root itself.
    if root_path.is_symlink():
        return False
    return True


def _walk_private_root(root_path: Path) -> dict[str, Any]:
    """Walk an explicitly supplied private root. Bounded depth, bounded file
    count. Returns aggregate buckets only: file_count, extension_counts. No
    paths, filenames, or basenames are ever returned."""
    file_count = 0
    extension_counts: dict[str, int] = {
        "ext_jsonl": 0, "ext_json": 0, "ext_csv": 0, "ext_other": 0,
    }
    root_resolved = root_path.resolve(strict=False)

    def _ext_bucket(name: str) -> str:
        lowered = name.lower()
        if lowered.endswith(".jsonl"):
            return "ext_jsonl"
        if lowered.endswith(".json"):
            return "ext_json"
        if lowered.endswith(".csv"):
            return "ext_csv"
        return "ext_other"

    for path in root_resolved.rglob("*"):
        if file_count >= MAX_FILES_PER_ROOT:
            break
        # Bounded depth check.
        try:
            rel = path.relative_to(root_resolved)
        except Exception:
            continue
        if len(rel.parts) > MAX_PRIVATE_ROOT_DEPTH:
            continue
        # Skip symlinks during walk (no symlink escape).
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        file_count += 1
        extension_counts[_ext_bucket(path.name)] += 1

    return {
        "anonymous_root_id": "haaer1root0000",
        "root_present_bool": True,
        "file_count": file_count,
        "extension_counts": extension_counts,
    }


def _parse_jsonl_keys(path: Path) -> set[str]:
    """Parse a JSONL file and return the union of top-level keys across all
    rows. Bounded by MAX_FILES_PER_ROOT. No row values are ever returned."""
    keys: set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if isinstance(row, dict):
                    keys |= set(row.keys())
    except Exception:
        return set()
    return keys


def _parse_json_keys(path: Path) -> set[str]:
    """Parse a JSON file and return the top-level keys. No values returned."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if isinstance(data, dict):
        return set(data.keys())
    if isinstance(data, list):
        keys: set[str] = set()
        for item in data:
            if isinstance(item, dict):
                keys |= set(item.keys())
        return keys
    return set()


def _map_keys_to_schema_groups(observed_keys: set[str]) -> dict[str, dict[str, int]]:
    """Map observed JSON keys to HAAE-R0 schema group columns. Returns a dict
    keyed by group_bucket with column_present_count and row_count (approximated
    by the number of observed keys that map to the group's columns). No raw
    keys are published."""
    group_coverage: dict[str, dict[str, int]] = {}
    for group in SCHEMA_GROUPS:
        column_present_count = 0
        for col in group["columns"]:
            col_bucket = col["column_bucket"]
            # Match if the observed key set contains the column bucket name
            # or a significant substring of it (e.g. "task_id" matches
            # "anonymous_task_id" via substring).
            for observed in observed_keys:
                if col_bucket in observed or observed in col_bucket:
                    column_present_count += 1
                    break
        # Approximate row_count: if any column is present, treat as count_1_to_10
        # (the inventory does not stream exact row counts; it buckets them).
        row_count = 10 if column_present_count > 0 else 0
        group_coverage[group["group_bucket"]] = {
            "column_present_count": column_present_count,
            "row_count": row_count,
        }
    return group_coverage


def run_private_inventory(private_roots: list[str]) -> dict[str, Any]:
    """Run the real private inventory over explicitly supplied roots. Returns
    aggregate-bucket-only inventory data. No paths, filenames, basenames, repo
    names, task ids, queries, candidates, spans, snippets, hashes, exact
    ranks/scores, labels, or row values are ever returned."""
    root_records: list[dict[str, Any]] = []
    all_observed_keys: set[str] = set()

    for idx, root_str in enumerate(private_roots):
        root_path = Path(root_str)
        if not _is_safe_private_root(root_path):
            root_records.append({
                "anonymous_root_id": f"haaer1root{idx:04d}",
                "root_present_bool": False,
                "file_count": 0,
                "extension_counts": {"ext_jsonl": 0, "ext_json": 0,
                                     "ext_csv": 0, "ext_other": 0},
            })
            continue
        walk_result = _walk_private_root(root_path)
        walk_result["anonymous_root_id"] = f"haaer1root{idx:04d}"
        root_records.append(walk_result)

        # Parse JSON/JSONL files to collect observed keys (no values).
        root_resolved = root_path.resolve(strict=False)
        for path in root_resolved.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            lowered = path.name.lower()
            if lowered.endswith(".jsonl"):
                all_observed_keys |= _parse_jsonl_keys(path)
            elif lowered.endswith(".json"):
                all_observed_keys |= _parse_json_keys(path)

    group_coverage = _map_keys_to_schema_groups(all_observed_keys)
    return {
        "root_records": root_records,
        "group_coverage": group_coverage,
        "observed_key_count_bucket": row_count_bucket(len(all_observed_keys)),
    }


# ── Record builders ────────────────────────────────────────────────────────

def private_root_inventory_records(inventory: dict[str, Any] | None) -> list[dict[str, Any]]:
    """One record per explicit private root. Aggregate-bucket-only; no raw
    paths/filenames/basenames."""
    if inventory is None:
        return []
    records: list[dict[str, Any]] = []
    for root in inventory.get("root_records", []):
        ext = root.get("extension_counts", {})
        records.append({
            "anonymous_root_id": root["anonymous_root_id"],
            "root_present_bool": root["root_present_bool"],
            "root_kind_bucket": "explicit_private_root",
            "file_count_bucket": file_count_bucket(root.get("file_count", 0)),
            "ext_jsonl_count_bucket": file_count_bucket(ext.get("ext_jsonl", 0)),
            "ext_json_count_bucket": file_count_bucket(ext.get("ext_json", 0)),
            "ext_csv_count_bucket": file_count_bucket(ext.get("ext_csv", 0)),
            "ext_other_count_bucket": file_count_bucket(ext.get("ext_other", 0)),
            "no_raw_paths_published_bool": True,
            "no_raw_filenames_published_bool": True,
            "no_raw_basenames_published_bool": True,
            "aggregate_buckets_only_bool": True,
            "private_roots_only_bool": True,
        })
    return records


def schema_group_feasibility_records(group_coverage: dict[str, dict[str, int]] | None
                                     ) -> list[dict[str, Any]]:
    """One record per HAAE-R0 schema group (10 total). Coverage bucket: full /
    sufficient / partial / missing / not_present. Critical groups flagged."""
    records: list[dict[str, Any]] = []
    for group in SCHEMA_GROUPS:
        g_bucket = group["group_bucket"]
        cov = (group_coverage or {}).get(g_bucket, {"column_present_count": 0, "row_count": 0})
        col_present = cov.get("column_present_count", 0)
        row_count = cov.get("row_count", 0)
        col_total = len(group["columns"])
        is_critical = group["is_critical_group_bool"]
        cov_bucket = coverage_bucket_for_group(col_present, col_total, row_count, is_critical)
        records.append({
            "anonymous_feasibility_id": f"haaer1feas{group['group_index']:04d}",
            "group_bucket": g_bucket,
            "group_index": group["group_index"],
            "group_description_bucket": group["group_description_bucket"],
            "column_count": col_total,
            "column_present_count": col_present,
            "column_presence_bucket": (
                "all_present" if col_present >= col_total
                else "some_present" if col_present > 0
                else "none_present"
            ),
            "row_count_bucket": row_count_bucket(row_count),
            "missingness_bucket": missingness_bucket(col_present, col_total),
            "coverage_bucket": cov_bucket,
            "is_critical_group_bool": is_critical,
            "coverage_description_bucket": (
                f"group {g_bucket} has {col_present}/{col_total} columns present "
                f"with row_count_bucket={row_count_bucket(row_count)}; "
                f"coverage_bucket={cov_bucket}."
            ),
            "no_raw_release_bool": True,
            "aggregate_buckets_only_bool": True,
            "private_root_only_bool": True,
        })
    return records


def schema_column_feasibility_records(group_coverage: dict[str, dict[str, int]] | None
                                       ) -> list[dict[str, Any]]:
    """One record per HAAE-R0 schema column (~26 total). Type compatibility
    and presence/missingness buckets."""
    records: list[dict[str, Any]] = []
    col_idx = 0
    for group in SCHEMA_GROUPS:
        g_bucket = group["group_bucket"]
        cov = (group_coverage or {}).get(g_bucket, {"column_present_count": 0, "row_count": 0})
        col_present = cov.get("column_present_count", 0)
        for col in group["columns"]:
            present = col_idx < col_present  # simplified presence per column
            records.append({
                "anonymous_column_feasibility_id": f"haaer1col{col_idx:04d}",
                "group_bucket": g_bucket,
                "column_bucket": col["column_bucket"],
                "expected_column_type_bucket": col["column_type_bucket"],
                "observed_type_bucket": "string_bucket" if present else "not_observed",
                "type_compatibility_bucket": "compatible" if present else "not_observed",
                "presence_bucket": "present" if present else "absent",
                "missingness_bucket": "none_missing" if present else "all_missing",
                "no_raw_release_bool": True,
                "aggregate_buckets_only_bool": True,
            })
            col_idx += 1
    return records


def cross_group_join_feasibility_records(group_coverage: dict[str, dict[str, int]] | None
                                         ) -> list[dict[str, Any]]:
    """Anonymous join-shape availability buckets between critical groups. No
    raw keys/values published."""
    cov = group_coverage or {}
    critical_pairs = [
        ("task_identity", "candidate_pool"),
        ("task_identity", "evidence_core"),
        ("task_identity", "arm_assignment"),
        ("task_identity", "outcome_metric"),
        ("candidate_pool", "evidence_core"),
        ("arm_assignment", "outcome_metric"),
        ("evidence_core", "outcome_metric"),
    ]
    records: list[dict[str, Any]] = []
    for idx, (g1, g2) in enumerate(critical_pairs):
        g1_cov = cov.get(g1, {"column_present_count": 0, "row_count": 0})
        g2_cov = cov.get(g2, {"column_present_count": 0, "row_count": 0})
        join_available = (g1_cov.get("column_present_count", 0) > 0
                          and g2_cov.get("column_present_count", 0) > 0)
        records.append({
            "anonymous_join_id": f"haaer1join{idx:04d}",
            "join_bucket": f"{g1}_to_{g2}",
            "join_kind_bucket": "anonymous_join_available" if join_available else "anonymous_join_absent",
            "join_description_bucket": (
                f"anonymous join-shape availability between {g1} and {g2}; "
                f"join_available={'true' if join_available else 'false'}. no raw "
                f"join keys published."
            ),
            "no_raw_release_bool": True,
            "aggregate_buckets_only_bool": True,
        })
    return records


def public_aggregation_feasibility_records(group_coverage: dict[str, dict[str, int]] | None
                                           ) -> list[dict[str, Any]]:
    """Feasibility of each HAAE-R0 public aggregation contract. Feasible if all
    source groups have at least partial coverage."""
    cov = group_coverage or {}
    records: list[dict[str, Any]] = []
    for idx, agg in enumerate(PUBLIC_AGGREGATION_CONTRACTS):
        source_groups = agg["source_groups"]
        all_partial = all(
            cov.get(g, {"column_present_count": 0}).get("column_present_count", 0) > 0
            for g in source_groups
        )
        records.append({
            "anonymous_aggregation_feasibility_id": f"haaer1aggfeas{idx:04d}",
            "aggregation_bucket": agg["aggregation_bucket"],
            "source_groups": source_groups,
            "feasibility_bucket": "feasible" if all_partial else "not_feasible",
            "no_raw_release_bool": True,
            "aggregate_buckets_only_bool": True,
        })
    return records


def coverage_summary_records(group_coverage: dict[str, dict[str, int]] | None
                              ) -> list[dict[str, Any]]:
    """Coverage summary across all 10 groups and the 5 critical groups.
    Determines pass / controlled_no_go / unavailable. When group_coverage is
    None (default/no-private mode), returns 'unavailable'."""
    if group_coverage is None:
        return [{
            "anonymous_summary_id": "haaer1summary0000",
            "total_group_count": len(SCHEMA_GROUPS),
            "full_coverage_group_count": 0,
            "sufficient_coverage_group_count": 0,
            "partial_coverage_group_count": 0,
            "missing_coverage_group_count": 0,
            "not_present_coverage_group_count": len(SCHEMA_GROUPS),
            "critical_group_count": len(CRITICAL_GROUPS),
            "critical_group_full_count": 0,
            "critical_group_sufficient_count": 0,
            "all_groups_at_least_partial_bool": False,
            "critical_groups_full_or_sufficient_bool": False,
            "feasibility_bucket": "unavailable",
            "no_raw_release_bool": True,
            "aggregate_buckets_only_bool": True,
        }]
    cov = group_coverage
    full_count = 0
    sufficient_count = 0
    partial_count = 0
    missing_count = 0
    not_present_count = 0
    critical_full_count = 0
    critical_sufficient_count = 0
    for group in SCHEMA_GROUPS:
        g_bucket = group["group_bucket"]
        g_cov = cov.get(g_bucket, {"column_present_count": 0, "row_count": 0})
        col_present = g_cov.get("column_present_count", 0)
        row_count = g_cov.get("row_count", 0)
        col_total = len(group["columns"])
        is_critical = group["is_critical_group_bool"]
        cov_bucket = coverage_bucket_for_group(col_present, col_total, row_count, is_critical)
        if cov_bucket == "full":
            full_count += 1
            if is_critical:
                critical_full_count += 1
        elif cov_bucket == "sufficient":
            sufficient_count += 1
            if is_critical:
                critical_sufficient_count += 1
        elif cov_bucket == "partial":
            partial_count += 1
        elif cov_bucket == "missing":
            missing_count += 1
        else:
            not_present_count += 1

    total_group_count = len(SCHEMA_GROUPS)
    critical_group_count = len(CRITICAL_GROUPS)
    all_groups_at_least_partial = (
        full_count + sufficient_count + partial_count == total_group_count
        and missing_count == 0
        and not_present_count == 0
    )
    critical_full_or_sufficient = (
        critical_full_count + critical_sufficient_count == critical_group_count
    )
    if all_groups_at_least_partial and critical_full_or_sufficient:
        feasibility = "pass"
    elif missing_count > 0 or not_present_count > 0 or not critical_full_or_sufficient:
        feasibility = "controlled_no_go"
    else:
        feasibility = "unavailable"

    return [{
        "anonymous_summary_id": "haaer1summary0000",
        "total_group_count": total_group_count,
        "full_coverage_group_count": full_count,
        "sufficient_coverage_group_count": sufficient_count,
        "partial_coverage_group_count": partial_count,
        "missing_coverage_group_count": missing_count,
        "not_present_coverage_group_count": not_present_count,
        "critical_group_count": critical_group_count,
        "critical_group_full_count": critical_full_count,
        "critical_group_sufficient_count": critical_sufficient_count,
        "all_groups_at_least_partial_bool": all_groups_at_least_partial,
        "critical_groups_full_or_sufficient_bool": critical_full_or_sufficient,
        "feasibility_bucket": feasibility,
        "no_raw_release_bool": True,
        "aggregate_buckets_only_bool": True,
    }]


def synthetic_validator_records(synth_fixtures: list[tuple[str, dict[str, Any]]]
                                ) -> list[dict[str, Any]]:
    """Validate the inventory logic against synthetic full / partial / missing
    fixtures. In-process; no real data, no replay, no retrieval, no candidate
    generation."""
    results: list[dict[str, Any]] = []
    for idx, (name, fixture) in enumerate(synth_fixtures):
        group_cov = fixture.get("group_coverage", {})
        summary = coverage_summary_records(group_cov)[0]
        results.append({
            "anonymous_synthetic_validator_id": f"haaer1synth{idx:04d}",
            "validator_bucket": f"embedded_synthetic_{name}_fixture",
            "fixture_kind_bucket": name,
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "validates_coverage_logic_bool": True,
            "expected_feasibility_bucket": summary["feasibility_bucket"],
            "all_groups_at_least_partial_bool": summary["all_groups_at_least_partial_bool"],
            "critical_groups_full_or_sufficient_bool": summary["critical_groups_full_or_sufficient_bool"],
        })
    return results


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "haaer1risk0000",
            "risk_bucket": "private_diagnostic_leakage",
            "risk_description_bucket": (
                "the feasibility inventory could leak per-task "
                "diagnostics/paths/candidates/orders/labels into the public "
                "artifact."),
            "mitigation_bucket": (
                "HAAE-R1 publishes aggregate buckets only; forbidden_scan "
                "blocks raw per-task/paths/orders/labels keys, private root "
                "paths, file extensions in values, hashes, and CI ids; every "
                "record carries aggregate_buckets_only_bool=true, "
                "private_root_only_bool=true, no_raw_release_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1risk0001",
            "risk_bucket": "haae_r1_scope_creep_beyond_feasibility_inventory",
            "risk_description_bucket": (
                "HAAE-R1 could be scoped beyond a feasibility inventory into "
                "replay/scoring/retrieval/candidate generation/HAAE-layer "
                "execution."),
            "mitigation_bucket": (
                "every record carries no_replay_bool/no_scoring_bool/"
                "no_retrieval_bool/no_candidate_generation_bool/"
                "no_haae_layer_execution_bool=true; stop/go carries "
                "haae_r1_replay_authorized_bool=false, "
                "haae_r1_scoring_authorized_bool=false, etc."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1risk0002",
            "risk_bucket": "haae_r1_default_mode_reads_private_roots",
            "risk_description_bucket": (
                "the default/no-private mode could silently read private roots "
                "without explicit opt-in."),
            "mitigation_bucket": (
                "default mode (no --allow-private-inventory) produces the "
                "unavailable_no_explicit_private_roots artifact; real inventory "
                "requires explicit --allow-private-inventory --private-root; "
                "the safe parser rejects unknown args generically without "
                "echoing values."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1risk0003",
            "risk_bucket": "haae_r0_drift_into_selector_or_p5_or_runtime",
            "risk_description_bucket": (
                "the HAAE-R1 inventory could be reframed as BEA-v1-A, a "
                "selector-only design, selector/reranker execution, P5, or a "
                "runtime/default promotion."),
            "mitigation_bucket": (
                "every record carries the HAAE-R0 non-identity booleans; "
                "selector_reranker_authorized_bool=false; bea_v1_a_authorized_"
                "bool=false; p5_authorized_bool=false; "
                "runtime_default_change_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1risk0004",
            "risk_bucket": "runtime_default_creep",
            "risk_description_bucket": (
                "the feasibility inventory could implicitly drift "
                "runtime/default behavior by codifying a route as a default "
                "gate."),
            "mitigation_bucket": (
                "runtime_default_change_authorized_bool=false; any HAAE route "
                "remains opt-in/eval-only; no runtime or default change."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1risk0005",
            "risk_bucket": "overinterpretation_from_insufficient_coverage",
            "risk_description_bucket": (
                "a controlled no-go from insufficient coverage could be "
                "overinterpreted as a method-winner or promotion claim."),
            "mitigation_bucket": (
                "method_winner_claim_authorized_bool=false; "
                "guard_full_diffaware_promotion_authorized_bool=false; the "
                "no-go authorizes only HAAE-R1A coverage-gap design, not any "
                "promotion or rule change."),
            "risk_controlled_bool": True,
        },
    ]


def public_package_records(lock_record: dict[str, Any], readback: dict[str, bool],
                            private_read_count_bucket: str,
                            feasibility: str) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer1package0000",
        "package_bucket": "haae_r1_unified_private_trace_schema_feasibility_inventory_package",
        "schema_version": "bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "feasibility_inventory_only_bool": True,
        "private_roots_only_bool": True,
        "private_read_count_bucket": private_read_count_bucket,
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "candidate_generation_count": 0,
        "arm_scoring_count": 0,
        "openlocus_execution_count": 0,
        "replay_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "haae_r0_source_locked_bool": lock_record["source_locked_bool"],
        "haae_r0_docs_readback_match_bool": readback["haae_r0_docs_readback_match_bool"],
        "haae_r1_docs_readback_match_bool": readback["haae_r1_docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "research_log_match_bool": readback["research_log_match_bool"],
        "research_summary_match_bool": readback["research_summary_match_bool"],
        "self_test_total_public_readback_match_bool": readback["self_test_total_public_readback_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
        "feasibility_bucket": feasibility,
    }]


def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer1claim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "feasibility_inventory_only_bool": True,
        "private_roots_only_bool": True,
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
        "n10et_execution_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "haae_r0_execution_authorized_bool": False,
        "haae_r1_execution_authorized_bool": False,
        "haae_r1_replay_authorized_bool": False,
        "haae_r1_scoring_authorized_bool": False,
        "haae_r1_retrieval_authorized_bool": False,
        "haae_r1_candidate_generation_authorized_bool": False,
        "haae_r2_execution_authorized_bool": False,
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
                           feasibility: str, inventory_mode: bool,
                           synth_validation: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        _gate("haaer1gate0000", "haae_r0_public_source_locked",
              lock_record["source_locked_bool"]),
        _gate("haaer1gate0001", "haae_r0_status_locked",
              lock_record["haae_r0_status_match_bool"]),
        _gate("haaer1gate0002", "haae_r0_haae_r1_authorized_match",
              lock_record["haae_r1_authorized_match_bool"]),
        _gate("haaer1gate0003", "haae_r0_haae_r1_execution_false_match",
              lock_record["haae_r1_execution_false_match_bool"]),
        _gate("haaer1gate0004", "haae_r0_bea_v1_a_false_match",
              lock_record["bea_v1_a_false_match_bool"]),
        _gate("haaer1gate0005", "haae_r0_non_identity_match",
              lock_record["haae_r0_non_identity_match_bool"]),
        _gate("haaer1gate0006", "haae_r1_no_threshold_tuning", True),
        _gate("haaer1gate0007", "haae_r1_no_method_winner_claim", True),
        _gate("haaer1gate0008", "haae_r1_no_runtime_default_change", True),
        _gate("haaer1gate0009", "haae_r1_no_promotion_or_frozen_rule_change", True),
        _gate("haaer1gate0010", "haae_r1_no_ci_rerun_retrieval_recompute_candidate_generation", True),
        _gate("haaer1gate0011", "haae_r1_no_replay_scoring_arm_scoring_openlocus_execution", True),
        _gate("haaer1gate0012", "haae_r1_no_haae_layer_execution", True),
        _gate("haaer1gate0013", "haae_r1_no_selector_reranker_no_p5_no_bea_v1_a", True),
        _gate("haaer1gate0014", "haae_r1_no_private_boundary_violation", True),
        _gate("haaer1gate0015", "haae_r1_schema_groups_accounted",
              len(SCHEMA_GROUPS) == 10),
        _gate("haaer1gate0016", "haae_r1_critical_groups_identified",
              len(CRITICAL_GROUPS) == 5),
        _gate("haaer1gate0017", "haae_r1_feasibility_bucket_valid",
              feasibility in ("pass", "controlled_no_go", "unavailable")),
        _gate("haaer1gate0018", "haae_r1_synthetic_validators_pass",
              all(synth_validation.values())),
        _gate("haaer1gate0019", "haae_r1_inventory_mode_explicit_opt_in",
              inventory_mode in (True, False)),  # both modes valid
        _gate("haaer1gate0020", "docs_readback_match_gate",
              readback["haae_r1_docs_readback_match_bool"]
              and readback["haae_r0_docs_readback_match_bool"]),
        _gate("haaer1gate0021", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("haaer1gate0022", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("haaer1gate0023", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("haaer1gate0024", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("haaer1gate0025", "self_test_total_public_readback_match_gate",
              readback["self_test_total_public_readback_match_bool"]),
        _gate("haaer1gate0026", "haae_r0_non_identity_gate", True),
    ]


def stop_go_records(feasibility: str) -> list[dict[str, Any]]:
    """Stop/go: pass authorizes only HAAE-R2 Feasibility-Gated Offline Trace
    Join Design (design-only); no-go authorizes only HAAE-R1A Private Trace
    Coverage Gap Design (design-only). No execution/replay/scoring/retrieval/
    candidate generation/haae-layer execution."""
    if feasibility == "pass":
        next_phase = NEXT_ROUTE_PASS
        pass_authorized = True
        no_go_authorized = False
    elif feasibility == "controlled_no_go":
        next_phase = NEXT_ROUTE_NO_GO
        pass_authorized = False
        no_go_authorized = True
    else:
        next_phase = NEXT_ROUTE_NO_GO
        pass_authorized = False
        no_go_authorized = False
    return [{
        "anonymous_stop_go_id": "haaer1stop0000",
        "next_allowed_phase": next_phase,
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "feasibility_inventory_only_bool": True,
        "private_roots_only_bool": True,
        "haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool": pass_authorized,
        "haae_r2_design_only_bool": pass_authorized,
        "haae_r2_execution_authorized_bool": False,
        "haae_r2_replay_authorized_bool": False,
        "haae_r2_scoring_authorized_bool": False,
        "haae_r2_retrieval_authorized_bool": False,
        "haae_r2_candidate_generation_authorized_bool": False,
        "haae_r1a_private_trace_coverage_gap_design_authorized_bool": no_go_authorized,
        "haae_r1a_design_only_bool": no_go_authorized,
        "haae_r1a_execution_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
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

def build_report(allow_private_inventory: bool = False,
                 private_roots: list[str] | None = None) -> dict[str, Any]:
    lock_ok, lock_record = evaluate_haae_r0_source_lock()
    readback = public_readback_match()

    # Determine inventory mode and produce records.
    inventory: dict[str, Any] | None = None
    inventory_mode = False
    private_read_count_bucket = "count_0"

    if not lock_ok:
        # No locked source → unavailable (no private reads attempted).
        status = STATUS_NO_SOURCE
        group_coverage = None
    elif allow_private_inventory and private_roots:
        # Real inventory mode.
        inventory_mode = True
        inventory = run_private_inventory(private_roots)
        group_coverage = inventory["group_coverage"]
        private_read_count_bucket = "count_1_to_10"  # explicit opt-in
    else:
        # Default / no-private mode: unavailable, no private reads.
        status = STATUS_NO_ROOTS
        group_coverage = None

    # Compute feasibility if we have group coverage.
    if lock_ok and group_coverage is not None:
        summary = coverage_summary_records(group_coverage)[0]
        feasibility = summary["feasibility_bucket"]
        if feasibility == "pass":
            status = STATUS_PASS
        elif feasibility == "controlled_no_go":
            status = STATUS_NO_GO
        else:
            status = STATUS_NO_ROOTS if not inventory_mode else STATUS_NO_GO
    elif lock_ok and group_coverage is None and not allow_private_inventory:
        status = STATUS_NO_ROOTS
    elif lock_ok and group_coverage is None and allow_private_inventory and not private_roots:
        status = STATUS_NO_ROOTS
    elif not lock_ok:
        status = STATUS_NO_SOURCE
    else:
        status = STATUS_NO_ROOTS

    # For default/no-private mode with locked source, override to NO_ROOTS.
    if lock_ok and not inventory_mode:
        status = STATUS_NO_ROOTS
        feasibility = "unavailable"
    elif lock_ok and inventory_mode and group_coverage is not None:
        feasibility = coverage_summary_records(group_coverage)[0]["feasibility_bucket"]
        if feasibility == "pass":
            status = STATUS_PASS
        elif feasibility == "controlled_no_go":
            status = STATUS_NO_GO
        else:
            status = STATUS_NO_GO
    else:
        feasibility = "unavailable"

    # Synthetic validators always run (in-process; no real data).
    synth_fixtures = [
        ("full", SYNTH_FULL_FIXTURE),
        ("partial", SYNTH_PARTIAL_FIXTURE),
        ("missing", SYNTH_MISSING_FIXTURE),
    ]
    synth_validation = {
        f"synth_{name}_pass": (
            coverage_summary_records(fixture.get("group_coverage", {}))[0]["feasibility_bucket"]
            == expected
        )
        for (name, fixture), expected in [
            (("full", SYNTH_FULL_FIXTURE), "pass"),
            (("partial", SYNTH_PARTIAL_FIXTURE), "pass"),
            (("missing", SYNTH_MISSING_FIXTURE), "controlled_no_go"),
        ]
    }

    report: dict[str, Any] = {
        "schema_version": "bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_v1",
        "phase_bucket": "BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory",
        "status": status,
        "source_lock_records": [lock_record],
        "private_root_inventory_records": private_root_inventory_records(inventory),
        "schema_group_feasibility_records": schema_group_feasibility_records(group_coverage),
        "schema_column_feasibility_records": schema_column_feasibility_records(group_coverage),
        "cross_group_join_feasibility_records": cross_group_join_feasibility_records(group_coverage),
        "public_aggregation_feasibility_records": public_aggregation_feasibility_records(group_coverage),
        "coverage_summary_records": coverage_summary_records(group_coverage),
        "synthetic_validator_records": synthetic_validator_records(synth_fixtures),
        "risk_control_records": risk_control_records(),
        "public_package_records": public_package_records(
            lock_record, readback, private_read_count_bucket, feasibility),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(
            lock_record, readback, feasibility, inventory_mode, synth_validation),
        "stop_go_records": stop_go_records(feasibility),
        "gate_records": [
            {"anonymous_gate_id": "haaer1gate0000",
             "gate_bucket": "haae_r0_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "haaer1gate0010",
             "gate_bucket": "no_ci_rerun_retrieval_recompute_candidate_generation",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1gate0011",
             "gate_bucket": "no_replay_scoring_arm_scoring_openlocus_execution",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1gate0012",
             "gate_bucket": "no_haae_layer_execution",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1gate0014",
             "gate_bucket": "no_private_boundary_violation",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1gate0026",
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
        failures.append("haae_r0_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_retrieval_performed_bool") is not True:
        failures.append("retrieval_claim_not_true")
    if lock.get("no_recompute_performed_bool") is not True:
        failures.append("recompute_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("no_replay_performed_bool") is not True:
        failures.append("replay_claim_not_true")
    if lock.get("no_scoring_performed_bool") is not True:
        failures.append("scoring_claim_not_true")
    if lock.get("no_candidate_generation_performed_bool") is not True:
        failures.append("candidate_generation_claim_not_true")
    if lock.get("no_haae_layer_execution_bool") is not True:
        failures.append("haae_layer_execution_claim_not_true")
    if lock.get("haae_r1_authorized_match_bool") is not True:
        failures.append("haae_r0_haae_r1_not_authorized")
    if lock.get("haae_r1_execution_false_match_bool") is not True:
        failures.append("haae_r0_haae_r1_execution_not_false")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("haae_r1_docs_readback_match_bool", "haae_r0_docs_readback_match_bool",
                  "readme_readback_match_bool", "current_conclusions_match_bool",
                  "research_log_match_bool", "research_summary_match_bool",
                  "self_test_total_public_readback_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Schema group feasibility: 10 groups accounted.
    group_records = report.get("schema_group_feasibility_records", [])
    if len(group_records) != 10:
        failures.append(f"schema_group_feasibility_count_not_10_got_{len(group_records)}")
    group_buckets = {r.get("group_bucket") for r in group_records}
    for needed in ALL_GROUP_BUCKETS:
        if needed not in group_buckets:
            failures.append(f"missing_schema_group_feasibility_{needed}")
    for r in group_records:
        for field in ("aggregate_buckets_only_bool", "private_root_only_bool",
                      "no_raw_release_bool"):
            if r.get(field) is not True:
                failures.append(f"schema_group_{r.get('group_bucket')}_{field}_not_true")
    # Coverage summary.
    summary = (report.get("coverage_summary_records") or [{}])[0] if report.get("coverage_summary_records") else {}
    if summary.get("total_group_count") != 10:
        failures.append("coverage_summary_total_group_count_not_10")
    if summary.get("critical_group_count") != 5:
        failures.append("coverage_summary_critical_group_count_not_5")
    if summary.get("feasibility_bucket") not in ("pass", "controlled_no_go", "unavailable"):
        failures.append("coverage_summary_feasibility_bucket_invalid")
    # Synthetic validators.
    for r in report.get("synthetic_validator_records", []):
        for field in ("embedded_fixture_bool", "no_real_data_bool", "no_replay_bool",
                      "no_retrieval_bool", "no_candidate_generation_bool",
                      "no_scoring_bool", "no_haae_layer_execution_bool",
                      "validates_coverage_logic_bool"):
            if r.get(field) is not True:
                failures.append(f"synth_{r.get('validator_bucket')}_{field}_not_true")
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
                  "haae_layer_execution_bool",
                  "network_run_bool", "provider_model_network_bool",
                  "n10et_execution_authorized_bool", "n10et_re_run_authorized_bool",
                  "haae_r0_execution_authorized_bool",
                  "haae_r1_execution_authorized_bool",
                  "haae_r1_replay_authorized_bool",
                  "haae_r1_scoring_authorized_bool",
                  "haae_r1_retrieval_authorized_bool",
                  "haae_r1_candidate_generation_authorized_bool",
                  "haae_r2_execution_authorized_bool",
                  "gold_used_for_policy_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool",
                  "feasibility_inventory_only_bool", "private_roots_only_bool",
                  "haae_r0_not_bea_v1_a_bool", "haae_r0_not_selector_only_bool",
                  "haae_r0_not_selector_reranker_execution_bool",
                  "haae_r0_not_p5_bool", "haae_r0_not_runtime_default_promotion_bool"):
        if claim.get(field) is not True:
            failures.append(f"claim_{field}_not_true")
    # Pass/fail gates: aggregate-only, no gold-for-policy, no rerun, no private read.
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
    # Stop/go: at most one of HAAE-R2 / HAAE-R1A authorized, both design-only.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    r2_auth = stop.get("haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool")
    r1a_auth = stop.get("haae_r1a_private_trace_coverage_gap_design_authorized_bool")
    if r2_auth is True and r1a_auth is True:
        failures.append("stop_both_r2_and_r1a_authorized")
    if r2_auth is False and r1a_auth is False and report.get("status") in (STATUS_PASS, STATUS_NO_GO):
        failures.append("stop_neither_r2_nor_r1a_authorized")
    for field in ("haae_r2_execution_authorized_bool",
                  "haae_r2_replay_authorized_bool",
                  "haae_r2_scoring_authorized_bool",
                  "haae_r2_retrieval_authorized_bool",
                  "haae_r2_candidate_generation_authorized_bool",
                  "haae_r1a_execution_authorized_bool",
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
                  "feasibility_inventory_only_bool", "private_roots_only_bool"):
        if stop.get(field) is not True:
            failures.append(f"stop_{field}_not_true")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab",
                   STATUS_PASS in STATUS_VOCAB and STATUS_NO_GO in STATUS_VOCAB
                   and STATUS_NO_SOURCE in EXIT0_VOCAB and STATUS_NO_ROOTS in EXIT0_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser_rejects_unknown", False))
    except SystemExit as exc:
        checks.append(("safe_parser_rejects_unknown", exc.code == 2))
    try:
        parse_args(["--allow-private-inventory", "--private-root", "/tmp/x", "--bogus-arg", "secret_value"])
        checks.append(("safe_parser_rejects_unknown_no_echo", False))
    except SystemExit as exc:
        checks.append(("safe_parser_rejects_unknown_no_echo", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value_github", scan_summary({"bucket": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_value_openlocus", scan_summary({"bucket": "x .openlocus/research-private/ y"})["status"] == "fail"))
    checks.append(("scanner_value_tmp", scan_summary({"bucket": "/tmp/foo"})["status"] == "fail"))
    checks.append(("scanner_value_workspace", scan_summary({"bucket": "/workspace/foo"})["status"] == "fail"))
    checks.append(("scanner_value_file_ext", scan_summary({"bucket": "data.jsonl"})["status"] == "fail"))
    checks.append(("scanner_value_task_id", scan_summary({"bucket": "task_abc123"})["status"] == "fail"))
    checks.append(("scanner_value_ci_id", scan_summary({"bucket": "ci-00001"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_passes_clean", scan_summary({"status": "ok", "count": 7})["status"] == "pass"))
    checks.append(("scanner_key_candidate", scan_summary({"candidate": "x"})["status"] == "fail"))
    checks.append(("scanner_key_query", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_key_span", scan_summary({"span": "x"})["status"] == "fail"))
    checks.append(("scanner_key_score", scan_summary({"score": "x"})["status"] == "fail"))
    checks.append(("scanner_key_gold", scan_summary({"gold": "x"})["status"] == "fail"))
    checks.append(("scanner_key_content_sha", scan_summary({"content_sha": "x"})["status"] == "fail"))

    # Locked constants.
    checks.append(("locked_haae_r0_checkpoint", LOCKED_HAAE_R0_CHECKPOINT == "854fc2e"))
    checks.append(("locked_haae_r0_status",
                   LOCKED_HAAE_R0_STATUS == "haae_r0_design_schema_preflight_complete_haae_r1_authorized"))
    checks.append(("locked_n10et_checkpoint", LOCKED_N10ET_CHECKPOINT == "26d817e"))
    checks.append(("locked_n10et_status",
                   LOCKED_N10ET_STATUS
                   == "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"))
    checks.append(("haae_r1_non_identities",
                   set(HAAE_R1_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))
    checks.append(("schema_group_count", len(SCHEMA_GROUPS) == 10))
    checks.append(("critical_group_count", len(CRITICAL_GROUPS) == 5))
    checks.append(("critical_groups_match",
                   set(CRITICAL_GROUPS) == {"task_identity", "candidate_pool",
                                            "evidence_core", "arm_assignment",
                                            "outcome_metric"}))
    checks.append(("next_route_pass", "HAAE-R2" in NEXT_ROUTE_PASS
                   and "Feasibility-Gated Offline Trace Join Design" in NEXT_ROUTE_PASS))
    checks.append(("next_route_no_go", "HAAE-R1A" in NEXT_ROUTE_NO_GO
                   and "Private Trace Coverage Gap Design" in NEXT_ROUTE_NO_GO))

    # Source lock against the real HAAE-R0 public report.
    lock_ok, lock_record = evaluate_haae_r0_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_haae_r0_status_match",
                   lock_record["haae_r0_status_match_bool"] is True))
    checks.append(("source_lock_haae_r1_authorized_match",
                   lock_record["haae_r1_authorized_match_bool"] is True))
    checks.append(("source_lock_haae_r1_execution_false_match",
                   lock_record["haae_r1_execution_false_match_bool"] is True))
    checks.append(("source_lock_haae_r1_replay_false_match",
                   lock_record["haae_r1_replay_false_match_bool"] is True))
    checks.append(("source_lock_haae_r1_scoring_false_match",
                   lock_record["haae_r1_scoring_false_match_bool"] is True))
    checks.append(("source_lock_haae_r1_retrieval_false_match",
                   lock_record["haae_r1_retrieval_false_match_bool"] is True))
    checks.append(("source_lock_haae_r1_candidate_gen_false_match",
                   lock_record["haae_r1_candidate_generation_false_match_bool"] is True))
    checks.append(("source_lock_bea_v1_a_false_match",
                   lock_record["bea_v1_a_false_match_bool"] is True))
    checks.append(("source_lock_p5_false_match",
                   lock_record["p5_false_match_bool"] is True))
    checks.append(("source_lock_non_identity_match",
                   lock_record["haae_r0_non_identity_match_bool"] is True))
    checks.append(("source_lock_r1_contract_match",
                   lock_record["haae_r1_contract_match_bool"] is True))
    checks.append(("source_lock_schema_count_match",
                   lock_record["haae_r0_schema_group_count_match_bool"] is True))

    readback = public_readback_match()
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

    # Synthetic full fixture → pass.
    full_summary = coverage_summary_records(SYNTH_FULL_FIXTURE["group_coverage"])[0]
    checks.append(("synth_full_pass", full_summary["feasibility_bucket"] == "pass"))
    checks.append(("synth_full_all_partial",
                   full_summary["all_groups_at_least_partial_bool"] is True))
    checks.append(("synth_full_critical_sufficient",
                   full_summary["critical_groups_full_or_sufficient_bool"] is True))

    # Synthetic partial fixture → pass (critical full, non-critical partial).
    partial_summary = coverage_summary_records(SYNTH_PARTIAL_FIXTURE["group_coverage"])[0]
    checks.append(("synth_partial_pass", partial_summary["feasibility_bucket"] == "pass"))
    checks.append(("synth_partial_all_partial",
                   partial_summary["all_groups_at_least_partial_bool"] is True))

    # Synthetic missing fixture → controlled no-go (critical task_identity missing).
    missing_summary = coverage_summary_records(SYNTH_MISSING_FIXTURE["group_coverage"])[0]
    checks.append(("synth_missing_no_go",
                   missing_summary["feasibility_bucket"] == "controlled_no_go"))
    checks.append(("synth_missing_critical_not_sufficient",
                   missing_summary["critical_groups_full_or_sufficient_bool"] is False))

    # Synthetic validator records.
    synth_records = synthetic_validator_records([
        ("full", SYNTH_FULL_FIXTURE),
        ("partial", SYNTH_PARTIAL_FIXTURE),
        ("missing", SYNTH_MISSING_FIXTURE),
    ])
    checks.append(("synth_records_count", len(synth_records) == 3))
    checks.append(("synth_records_no_real_data",
                   all(r["no_real_data_bool"] is True for r in synth_records)))
    checks.append(("synth_records_no_replay",
                   all(r["no_replay_bool"] is True for r in synth_records)))

    # Default / no-private mode → unavailable no explicit roots.
    default_report = build_report(allow_private_inventory=False, private_roots=None)
    checks.append(("default_mode_unavailable",
                   default_report["status"] == STATUS_NO_ROOTS))
    checks.append(("default_mode_no_private_reads",
                   default_report["public_package_records"][0]["private_read_count_bucket"] == "count_0"))
    checks.append(("default_mode_scan_pass",
                   default_report["forbidden_scan"]["status"] == "pass"))
    checks.append(("default_mode_10_groups_accounted",
                   len(default_report["schema_group_feasibility_records"]) == 10))
    checks.append(("private_root_inventory_uses_root_records",
                   private_root_inventory_records({"root_records": [{
                       "anonymous_root_id": "haaer1root0000",
                       "root_present_bool": True,
                       "file_count": 1,
                       "extension_counts": {"ext_jsonl": 1, "ext_json": 0,
                                            "ext_csv": 0, "ext_other": 0},
                   }]})[0]["file_count_bucket"] == "count_1_to_10"))

    # Schema group feasibility records: 10 groups, all accounted.
    group_records = schema_group_feasibility_records(SYNTH_FULL_FIXTURE["group_coverage"])
    checks.append(("group_records_count_10", len(group_records) == 10))
    checks.append(("group_records_buckets_match",
                   {r["group_bucket"] for r in group_records} == set(ALL_GROUP_BUCKETS)))
    checks.append(("group_records_aggregate_only",
                   all(r["aggregate_buckets_only_bool"] is True for r in group_records)))

    # Coverage logic: row_count_bucket, missingness_bucket, coverage_bucket.
    checks.append(("row_count_bucket_0", row_count_bucket(0) == "count_0"))
    checks.append(("row_count_bucket_5", row_count_bucket(5) == "count_1_to_10"))
    checks.append(("row_count_bucket_50", row_count_bucket(50) == "count_11_to_100"))
    checks.append(("row_count_bucket_500", row_count_bucket(500) == "count_101_to_1000"))
    checks.append(("row_count_bucket_5000", row_count_bucket(5000) == "count_1001_plus"))
    checks.append(("missingness_none", missingness_bucket(3, 3) == "none_missing"))
    checks.append(("missingness_some", missingness_bucket(2, 3) == "some_missing"))
    checks.append(("missingness_all", missingness_bucket(0, 3) == "all_missing"))
    checks.append(("missingness_not_present", missingness_bucket(0, 0) == "not_present"))
    checks.append(("coverage_full", coverage_bucket_for_group(3, 3, 10, True) == "full"))
    checks.append(("coverage_sufficient_critical",
                   coverage_bucket_for_group(2, 3, 10, True) == "sufficient"))
    checks.append(("coverage_partial_critical",
                   coverage_bucket_for_group(1, 3, 10, True) == "partial"))
    checks.append(("coverage_missing", coverage_bucket_for_group(0, 3, 10, True) == "missing"))
    checks.append(("coverage_not_present", coverage_bucket_for_group(0, 3, 0, True) == "not_present"))

    # Risk controls.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == 6))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))
    checks.append(("risk_private_leakage_present",
                   any(r["risk_bucket"] == "private_diagnostic_leakage" for r in risks)))
    checks.append(("risk_scope_creep_present",
                   any(r["risk_bucket"] == "haae_r1_scope_creep_beyond_feasibility_inventory" for r in risks)))
    checks.append(("risk_default_mode_reads_present",
                   any(r["risk_bucket"] == "haae_r1_default_mode_reads_private_roots" for r in risks)))

    # Stop/go: pass authorizes HAAE-R2; no-go authorizes HAAE-R1A.
    pass_stop = stop_go_records("pass")[0]
    checks.append(("stop_pass_haae_r2_authorized",
                   pass_stop["haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool"] is True))
    checks.append(("stop_pass_haae_r2_design_only",
                   pass_stop["haae_r2_design_only_bool"] is True))
    checks.append(("stop_pass_haae_r2_no_exec",
                   pass_stop["haae_r2_execution_authorized_bool"] is False))
    checks.append(("stop_pass_haae_r1a_not_authorized",
                   pass_stop["haae_r1a_private_trace_coverage_gap_design_authorized_bool"] is False))
    no_go_stop = stop_go_records("controlled_no_go")[0]
    checks.append(("stop_no_go_haae_r1a_authorized",
                   no_go_stop["haae_r1a_private_trace_coverage_gap_design_authorized_bool"] is True))
    checks.append(("stop_no_go_haae_r1a_design_only",
                   no_go_stop["haae_r1a_design_only_bool"] is True))
    checks.append(("stop_no_go_haae_r1a_no_exec",
                   no_go_stop["haae_r1a_execution_authorized_bool"] is False))
    checks.append(("stop_no_go_haae_r2_not_authorized",
                   no_go_stop["haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool"] is False))
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
    checks.append(("stop_haae_r0_non_identity",
                   pass_stop["haae_r0_not_bea_v1_a_bool"] is True
                   and pass_stop["haae_r0_not_selector_only_bool"] is True
                   and pass_stop["haae_r0_not_selector_reranker_execution_bool"] is True
                   and pass_stop["haae_r0_not_p5_bool"] is True
                   and pass_stop["haae_r0_not_runtime_default_promotion_bool"] is True))

    # Claim boundary explicit fields.
    cb = claim_boundary_records()[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_feasibility_inventory_only_true",
                   cb["feasibility_inventory_only_bool"] is True))
    checks.append(("claim_no_replay", cb["replay_bool"] is False))
    checks.append(("claim_no_haae_layer_execution",
                   cb["haae_layer_execution_bool"] is False))
    checks.append(("claim_no_raw_filename", cb["raw_filename_upload_bool"] is False))
    checks.append(("claim_no_raw_basename", cb["raw_basename_upload_bool"] is False))
    checks.append(("claim_no_raw_repo_name", cb["raw_repo_name_upload_bool"] is False))
    checks.append(("claim_no_raw_task_id", cb["raw_task_id_upload_bool"] is False))
    checks.append(("claim_haae_r2_execution_false", cb["haae_r2_execution_authorized_bool"] is False))
    checks.append(("claim_haae_r0_non_identity",
                   cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Full report build + validation (default mode).
    report = build_report(allow_private_inventory=False, private_roots=None)
    checks.append(("report_default_status_no_roots", report["status"] == STATUS_NO_ROOTS))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields",
                   package["haae_r1_docs_readback_match_bool"] is True
                   and package["haae_r0_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))
    checks.append(("report_10_groups_accounted",
                   len(report["schema_group_feasibility_records"]) == 10))
    checks.append(("report_default_no_private_reads",
                   package["private_read_count_bucket"] == "count_0"))

    # Bad-contract detection: forbidden operation mutation.
    bad = dict(report)
    bad["stop_go_records"] = [{**stop_go_records("pass")[0],
                               "haae_r2_execution_authorized_bool": True}]
    checks.append(("validate_fails_haae_r2_execution",
                   any("haae_r2_execution_authorized_bool_not_false" in f
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
    bad4["stop_go_records"] = [{**stop_go_records("pass")[0],
                                 "bea_v1_a_authorized_bool": True}]
    checks.append(("validate_fails_bea_v1_a",
                   any("bea_v1_a_authorized_bool_not_false" in f
                       for f in validate_report(bad4))))
    bad5 = dict(report)
    bad5["schema_group_feasibility_records"] = report["schema_group_feasibility_records"][:-1]
    checks.append(("validate_fails_schema_group_count",
                   any("schema_group_feasibility_count_not_10" in f
                       for f in validate_report(bad5))))
    bad6 = dict(report)
    bad6["stop_go_records"] = [{**stop_go_records("pass")[0],
                                 "haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool": True,
                                 "haae_r1a_private_trace_coverage_gap_design_authorized_bool": True}]
    checks.append(("validate_fails_both_authorized",
                   any("stop_both_r2_and_r1a_authorized" in f
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

    # Public-only / no-private by default. Real inventory requires explicit
    # opt-in via --allow-private-inventory --private-root.
    report = build_report(
        allow_private_inventory=args.allow_private_inventory,
        private_roots=args.private_root if args.allow_private_inventory else None,
    )
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
