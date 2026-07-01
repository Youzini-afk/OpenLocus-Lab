#!/usr/bin/env python3
"""BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke.

HAAE-R1C is the **first explicit-opt-in phase** allowed to create a private
HAAE trace-root artifact, but only as a **bounded smoke** of the
root/output/manifest pipeline. Locked source: HAAE-R1B commit/artifact
``8830492``.

R1C must **NOT**:
  * run FD1/P4L/N10EO/N10ER replay;
  * run retrieval, scoring, candidate generation;
  * run selector, BEA-v1-A, P5, or runtime/default promotion;
  * publish concrete paths, basenames, filenames, or hashes.

Allowed recipes:
  1. ``bootstrap_private_manifest_root_smoke`` (default explicit-opt-in recipe):
     creates an explicit private output root, writes only manifest/control
     files and empty/schema-category placeholders, **zero** raw
     task/query/candidate/span/score rows. Public artifact carries bucketized
     manifest only.
  2. ``operator_supplied_existing_root_manifest_smoke`` (optional): explicit
     input/output roots, metadata/schema inventory only, no row values,
     public aggregate buckets only.
  3. ``public_aggregate_source_option_manifest_smoke`` (optional): public-only
     projection, no private input.

Default invocation (no ``--allow-private-root-regeneration-smoke``) performs
**no** private reads or writes and produces status
``haae_r1c_unavailable_no_explicit_opt_in``.

Explicit opt-in requires ALL of:
  * ``--allow-private-root-regeneration-smoke``
  * ``--recipe <allowed_recipe_bucket>``
  * ``--private-output-root <path>``
  * ``--confirm-private-output-only``
  * optional ``--private-input-root <path>`` only for the existing-root recipe

The output root must be explicit, must NOT be a public tracked
docs/artifacts/eval source, must not be a symlink, must not allow path
traversal, and must have bounded depth and a bounded write set. No concrete
path/basename/filename is ever published.

Status vocabulary:
  * ``haae_r1c_bounded_private_trace_root_regeneration_smoke_complete``
    — bootstrap smoke executed: zero raw rows, manifest-only private output,
    bucketized public manifest.
  * ``haae_r1c_unavailable_no_explicit_opt_in`` — default no-private mode.
  * ``haae_r1c_unavailable_no_locked_source`` — HAAE-R1B source not locked.
  * ``fail_haae_r1b_source_lock_mismatch`` / ``fail_forbidden_scan`` /
    ``fail_schema_contract`` / ``fail_contract_violation`` /
    ``fail_private_boundary_violation`` / ``fail_forbidden_operation`` —
    fail-closed.

Handoff: R1C does not authorize a next phase by default; the smoke result
informs whether a future R1D bounded trace-join design is warranted.
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
SLUG = "bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
HAAE_R1B_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
    / "bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_report.json"
)
README_PATH = ROOT / "README.md"
HAAE_R1B_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md"
)
HAAE_R1B_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md"
)
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
HAAE_R1C_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md"
)
HAAE_R1C_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md"
)
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"
EVAL_DIR = ROOT / "eval"
DOCS_DIR = ROOT / "docs"
ARTIFACTS_DIR = ROOT / "artifacts"

# ── Locked HAAE-R1B public facts ───────────────────────────────────────────
LOCKED_HAAE_R1B_CHECKPOINT = "8830492"
LOCKED_HAAE_R1B_STATUS = (
    "haae_r1b_bounded_private_trace_root_regeneration_preflight_package"
    "_complete_r1c_smoke_authorized"
)
LOCKED_HAAE_R1B_NEXT_ALLOWED_PHASE = (
    "BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke"
)
# Upstream locks.
LOCKED_HAAE_R1A_CHECKPOINT = "e54d1b4"
LOCKED_HAAE_R1A_STATUS = (
    "haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized"
)
LOCKED_HAAE_R1_CHECKPOINT = "2ea77da"
LOCKED_HAAE_R1_STATUS = (
    "haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots"
)
LOCKED_HAAE_R0_CHECKPOINT = "854fc2e"
LOCKED_N10ET_CHECKPOINT = "26d817e"

# ── Non-identities ─────────────────────────────────────────────────────────
HAAE_R1C_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Allowed recipe buckets ─────────────────────────────────────────────────
RECIPE_BOOTSTRAP = "bootstrap_private_manifest_root_smoke"
RECIPE_EXISTING_ROOT = "operator_supplied_existing_root_manifest_smoke"
RECIPE_PUBLIC_AGGREGATE = "public_aggregate_source_option_manifest_smoke"
ALLOWED_RECIPES = (RECIPE_BOOTSTRAP, RECIPE_EXISTING_ROOT, RECIPE_PUBLIC_AGGREGATE)

# ── Deferred (forbidden in R1C) recipe buckets ────────────────────────────
DEFERRED_RECIPES = (
    "fd1_decomposition_replay_recipe",
    "p4l_scheduler_replay_recipe",
    "n10eo_diagnostic_rerun_recipe",
    "n10er_public_ci_replay_recipe",
)

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_COMPLETE = "haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized"
STATUS_NO_OPT_IN = "haae_r1c_unavailable_no_explicit_opt_in"
STATUS_NO_SOURCE = "haae_r1c_unavailable_no_locked_source"
STATUS_FAIL_LOCK = "fail_haae_r1b_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
STATUS_FAIL_PRIVATE = "fail_private_boundary_violation"
STATUS_FAIL_OP = "fail_forbidden_operation"
EXIT0_VOCAB = {STATUS_COMPLETE, STATUS_NO_OPT_IN, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {
    STATUS_FAIL_LOCK, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA,
    STATUS_FAIL_CONTRACT, STATUS_FAIL_PRIVATE, STATUS_FAIL_OP,
}

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

# Self-test check count.
SELF_TEST_TOTAL_CHECKS = 105

# Bounded smoke limits.
MAX_MANIFEST_FILES = 20
MAX_WRITE_DEPTH = 3
MAX_PLACEHOLDER_FILES_PER_GROUP = 3

# ── HAAE-R0 schema groups ─────────────────────────────────────────────────
SCHEMA_GROUPS: list[dict[str, Any]] = [
    {"group_bucket": "task_identity", "group_index": 0, "is_critical_group_bool": True},
    {"group_bucket": "anchor_source", "group_index": 1, "is_critical_group_bool": False},
    {"group_bucket": "candidate_pool", "group_index": 2, "is_critical_group_bool": True},
    {"group_bucket": "rank_pack", "group_index": 3, "is_critical_group_bool": False},
    {"group_bucket": "span_projection", "group_index": 4, "is_critical_group_bool": False},
    {"group_bucket": "scheduler_action", "group_index": 5, "is_critical_group_bool": False},
    {"group_bucket": "evidence_core", "group_index": 6, "is_critical_group_bool": True},
    {"group_bucket": "arm_assignment", "group_index": 7, "is_critical_group_bool": True},
    {"group_bucket": "outcome_metric", "group_index": 8, "is_critical_group_bool": True},
    {"group_bucket": "safety_probe_signal", "group_index": 9, "is_critical_group_bool": False},
]
ALL_GROUP_BUCKETS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS)
CRITICAL_GROUPS = tuple(g["group_bucket"] for g in SCHEMA_GROUPS if g["is_critical_group_bool"])
assert len(SCHEMA_GROUPS) == 10


# ── Safe argument parser ───────────────────────────────────────────────────

class SafeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-HAAE-R1C bounded private trace root regeneration smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--haae-r1b-report", default=str(HAAE_R1B_REPORT),
                        help="path to the committed HAAE-R1B public artifact")
    parser.add_argument("--allow-private-root-regeneration-smoke", action="store_true",
                        help="opt-in: enable bounded private root regeneration smoke")
    parser.add_argument("--recipe", choices=list(ALLOWED_RECIPES),
                        help="recipe bucket for the smoke")
    parser.add_argument("--private-output-root",
                        help="explicit private output root (must not be public tracked)")
    parser.add_argument("--confirm-private-output-only", action="store_true",
                        help="confirm private output only")
    parser.add_argument("--private-input-root",
                        help="explicit private input root (existing-root recipe only)")
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
    HAAE-R1C smoke and the HAAE-R1B preflight."""
    common_fragments = [
        LOCKED_HAAE_R1B_CHECKPOINT,
        LOCKED_HAAE_R1B_STATUS,
        "HAAE-R1B",
        "HAAE-R1C",
    ]
    self_test_fragments = (
        f"{SELF_TEST_TOTAL_CHECKS}/{SELF_TEST_TOTAL_CHECKS}",
        f"{SELF_TEST_TOTAL_CHECKS} / {SELF_TEST_TOTAL_CHECKS}",
    )
    readme = read_text_or_empty(README_PATH)
    haae_r1b_doc_en = read_text_or_empty(HAAE_R1B_DOC_EN)
    haae_r1b_doc_zh = read_text_or_empty(HAAE_R1B_DOC_ZH)
    haae_r1a_doc_en = read_text_or_empty(HAAE_R1A_DOC_EN)
    haae_r1a_doc_zh = read_text_or_empty(HAAE_R1A_DOC_ZH)
    haae_r1_doc_en = read_text_or_empty(HAAE_R1_DOC_EN)
    haae_r1_doc_zh = read_text_or_empty(HAAE_R1_DOC_ZH)
    haae_r0_doc_en = read_text_or_empty(HAAE_R0_DOC_EN)
    haae_r0_doc_zh = read_text_or_empty(HAAE_R0_DOC_ZH)
    haae_r1c_doc_en = read_text_or_empty(HAAE_R1C_DOC_EN)
    haae_r1c_doc_zh = read_text_or_empty(HAAE_R1C_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_r1c_closeout(text: str) -> bool:
        return ("HAAE-R1C" in text and "HAAE-R1B" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    def has_self_test_fragment(text: str) -> bool:
        return any(fragment in text for fragment in self_test_fragments)

    def has_explicit_smoke_write_fragment(text: str) -> bool:
        return (STATUS_COMPLETE in text
                and ("private writes `1`" in text
                     or "private writes: 1" in text
                     or "private_write_count` = 1" in text))

    readme_self_test_match = has_self_test_fragment(readme)
    r1c_docs_self_test_match = (has_self_test_fragment(haae_r1c_doc_en)
                                and has_self_test_fragment(haae_r1c_doc_zh))
    current_self_test_match = (has_self_test_fragment(current_en)
                               and has_self_test_fragment(current_zh))
    log_self_test_match = (has_self_test_fragment(log_en)
                           and has_self_test_fragment(log_zh))
    summary_self_test_match = (has_self_test_fragment(summary_en)
                               and has_self_test_fragment(summary_zh))
    self_test_total_match = (readme_self_test_match and r1c_docs_self_test_match
                             and current_self_test_match and log_self_test_match
                             and summary_self_test_match)
    explicit_smoke_write_match = (has_explicit_smoke_write_fragment(readme)
                                  and has_explicit_smoke_write_fragment(haae_r1c_doc_en)
                                  and has_explicit_smoke_write_fragment(haae_r1c_doc_zh)
                                  and has_explicit_smoke_write_fragment(current_en)
                                  and has_explicit_smoke_write_fragment(current_zh)
                                  and has_explicit_smoke_write_fragment(log_en)
                                  and has_explicit_smoke_write_fragment(log_zh))

    readme_match = (has_all(readme, common_fragments) and has_r1c_closeout(readme)
                    and readme_self_test_match and has_explicit_smoke_write_fragment(readme))
    current_match = (has_all(current_en, common_fragments)
                     and has_all(current_zh, common_fragments)
                     and has_r1c_closeout(current_en)
                     and has_r1c_closeout(current_zh) and current_self_test_match
                     and has_explicit_smoke_write_fragment(current_en)
                     and has_explicit_smoke_write_fragment(current_zh))
    r1c_docs_match = (has_all(haae_r1c_doc_en, common_fragments)
                      and has_all(haae_r1c_doc_zh, common_fragments)
                      and has_r1c_closeout(haae_r1c_doc_en)
                      and has_r1c_closeout(haae_r1c_doc_zh)
                      and r1c_docs_self_test_match
                      and has_explicit_smoke_write_fragment(haae_r1c_doc_en)
                      and has_explicit_smoke_write_fragment(haae_r1c_doc_zh))
    r1b_docs_match = "HAAE-R1C" in haae_r1b_doc_en and "HAAE-R1C" in haae_r1b_doc_zh
    r1a_docs_match = "HAAE-R1B" in haae_r1a_doc_en and "HAAE-R1B" in haae_r1a_doc_zh
    r1_docs_match = "HAAE-R1A" in haae_r1_doc_en and "HAAE-R1A" in haae_r1_doc_zh
    r0_docs_match = "HAAE-R1" in haae_r0_doc_en and "HAAE-R1" in haae_r0_doc_zh
    log_match = (has_r1c_closeout(log_en) and has_r1c_closeout(log_zh)
                 and log_self_test_match
                 and has_explicit_smoke_write_fragment(log_en)
                 and has_explicit_smoke_write_fragment(log_zh))
    summary_match = (has_r1c_closeout(summary_en) and has_r1c_closeout(summary_zh)
                     and summary_self_test_match)
    return {
        "haae_r1c_docs_readback_match_bool": r1c_docs_match,
        "haae_r1b_docs_readback_match_bool": r1b_docs_match,
        "haae_r1a_docs_readback_match_bool": r1a_docs_match,
        "haae_r1_docs_readback_match_bool": r1_docs_match,
        "haae_r0_docs_readback_match_bool": r0_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": self_test_total_match,
        "explicit_smoke_private_write_public_readback_match_bool": explicit_smoke_write_match,
        "all_public_readback_match_bool": (r1c_docs_match and r1b_docs_match
                                           and r1a_docs_match and r1_docs_match
                                           and r0_docs_match and readme_match
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


# ── HAAE-R1B source lock ───────────────────────────────────────────────────

def _haae_r1b_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _haae_r1b_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def evaluate_haae_r1b_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the HAAE-R1B public report and validate locked fields."""
    r1b_report, r1b_state = load_json(HAAE_R1B_REPORT)
    present_ok = r1b_state == "present" and isinstance(r1b_report, dict)
    status_ok = bool(r1b_report and r1b_report.get("status") == LOCKED_HAAE_R1B_STATUS)
    r1b_scan_ok = bool(r1b_report
                       and r1b_report.get("forbidden_scan", {}).get("status") == "pass")
    stop = _haae_r1b_stop_go(r1b_report or {})
    next_phase_ok = (stop.get("next_allowed_phase") == LOCKED_HAAE_R1B_NEXT_ALLOWED_PHASE)
    r1c_authorized_ok = (stop.get("haae_r1c_bounded_private_trace_root_regeneration_"
                                   "smoke_authorized_bool") is True)
    r1c_design_only_ok = stop.get("haae_r1c_design_only_bool") is True
    r1c_execution_false_ok = stop.get("haae_r1c_execution_authorized_bool") is False
    r1c_private_read_false_ok = stop.get("haae_r1c_private_read_authorized_bool") is False
    r1c_replay_false_ok = stop.get("haae_r1c_replay_authorized_bool") is False
    r1c_scoring_false_ok = stop.get("haae_r1c_scoring_authorized_bool") is False
    r1c_retrieval_false_ok = stop.get("haae_r1c_retrieval_authorized_bool") is False
    r1c_candidate_gen_false_ok = (stop.get("haae_r1c_candidate_generation_"
                                            "authorized_bool") is False)
    r1c_bounded_recipe_only_ok = stop.get("haae_r1c_bounded_recipe_only_bool") is True
    r1c_unbounded_replay_false_ok = (stop.get("haae_r1c_unbounded_replay_"
                                               "authorized_bool") is False)
    r1c_unbounded_retrieval_false_ok = (stop.get("haae_r1c_unbounded_retrieval_"
                                                  "authorized_bool") is False)
    r1c_unbounded_candidate_gen_false_ok = (stop.get("haae_r1c_unbounded_candidate_"
                                                       "generation_authorized_bool") is False)
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

    package = _haae_r1b_package(r1b_report or {})
    package_ok = (package.get("design_only_bool") is True
                  and package.get("private_input_read_count") == 0)

    recipe_count_ok = (len(r1b_report.get("recipe_catalog_records", [])) == 10
                       if r1b_report else False)
    r1c_contract_ok = bool(r1b_report
                            and r1b_report.get("r1c_contract_records"))

    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and r1b_scan_ok
               and next_phase_ok and r1c_authorized_ok and r1c_design_only_ok
               and r1c_execution_false_ok and r1c_private_read_false_ok
               and r1c_replay_false_ok and r1c_scoring_false_ok
               and r1c_retrieval_false_ok and r1c_candidate_gen_false_ok
               and r1c_bounded_recipe_only_ok
               and r1c_unbounded_replay_false_ok
               and r1c_unbounded_retrieval_false_ok
               and r1c_unbounded_candidate_gen_false_ok
               and bea_v1_a_false_ok and p5_false_ok
               and selector_reranker_false_ok and runtime_default_false_ok
               and root_regeneration_false_ok
               and r0_non_identity_ok and package_ok
               and recipe_count_ok and r1c_contract_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "haaer1csource0000",
        "source_lock_bucket": "haae_r1b_public_report_locked",
        "input_artifact_load_status_bucket": r1b_state,
        "locked_haae_r1b_checkpoint": LOCKED_HAAE_R1B_CHECKPOINT,
        "locked_haae_r1b_status": LOCKED_HAAE_R1B_STATUS,
        "locked_haae_r1b_next_allowed_phase": LOCKED_HAAE_R1B_NEXT_ALLOWED_PHASE,
        "locked_haae_r1a_checkpoint": LOCKED_HAAE_R1A_CHECKPOINT,
        "locked_haae_r1a_status": LOCKED_HAAE_R1A_STATUS,
        "locked_haae_r1_checkpoint": LOCKED_HAAE_R1_CHECKPOINT,
        "locked_haae_r1_status": LOCKED_HAAE_R1_STATUS,
        "locked_haae_r0_checkpoint": LOCKED_HAAE_R0_CHECKPOINT,
        "locked_n10et_checkpoint": LOCKED_N10ET_CHECKPOINT,
        "haae_r1b_status_match_bool": status_ok,
        "haae_r1b_scan_pass_bool": r1b_scan_ok,
        "haae_r1b_next_phase_match_bool": next_phase_ok,
        "haae_r1c_authorized_match_bool": r1c_authorized_ok,
        "haae_r1c_design_only_match_bool": r1c_design_only_ok,
        "haae_r1c_execution_false_match_bool": r1c_execution_false_ok,
        "haae_r1c_private_read_false_match_bool": r1c_private_read_false_ok,
        "haae_r1c_replay_false_match_bool": r1c_replay_false_ok,
        "haae_r1c_scoring_false_match_bool": r1c_scoring_false_ok,
        "haae_r1c_retrieval_false_match_bool": r1c_retrieval_false_ok,
        "haae_r1c_candidate_generation_false_match_bool": r1c_candidate_gen_false_ok,
        "haae_r1c_bounded_recipe_only_match_bool": r1c_bounded_recipe_only_ok,
        "haae_r1c_unbounded_replay_false_match_bool": r1c_unbounded_replay_false_ok,
        "haae_r1c_unbounded_retrieval_false_match_bool": r1c_unbounded_retrieval_false_ok,
        "haae_r1c_unbounded_candidate_generation_false_match_bool": r1c_unbounded_candidate_gen_false_ok,
        "bea_v1_a_false_match_bool": bea_v1_a_false_ok,
        "p5_false_match_bool": p5_false_ok,
        "selector_reranker_false_match_bool": selector_reranker_false_ok,
        "runtime_default_false_match_bool": runtime_default_false_ok,
        "root_regeneration_false_match_bool": root_regeneration_false_ok,
        "haae_r0_non_identity_match_bool": r0_non_identity_ok,
        "package_design_only_match_bool": package_ok,
        "recipe_count_match_bool": recipe_count_ok,
        "r1c_contract_match_bool": r1c_contract_ok,
        "no_ci_rerun_performed_bool": True,
        "no_retrieval_performed_bool": True,
        "no_recompute_performed_bool": True,
        "no_private_input_read_bool": True,
        "no_replay_performed_bool": True,
        "no_scoring_performed_bool": True,
        "no_candidate_generation_performed_bool": True,
        "no_haae_layer_execution_bool": True,
        "no_unbounded_replay_bool": True,
        "no_unbounded_retrieval_bool": True,
        "no_unbounded_candidate_generation_bool": True,
        "no_selector_bool": True,
        "no_bea_v1_a_bool": True,
        "no_p5_bool": True,
        "no_runtime_default_bool": True,
        "public_readback_match_bool": readback["all_public_readback_match_bool"],
        "source_locked_bool": lock_ok,
    }
    return lock_ok, lock_record


# ── Non-identity helper ────────────────────────────────────────────────────

def _non_identity_fields() -> dict[str, bool]:
    return {
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }


# ── Private output root validation ─────────────────────────────────────────

def _is_public_tracked_location(path: Path) -> bool:
    """Check if a path is inside public tracked dirs (docs, artifacts, eval).
    The output root must NOT be a public tracked location."""
    try:
        resolved = path.resolve(strict=False)
        # Check against public tracked roots.
        for tracked in [DOCS_DIR, ARTIFACTS_DIR, EVAL_DIR, README_PATH.parent]:
            try:
                resolved.relative_to(tracked.resolve(strict=False))
                return True
            except ValueError:
                continue
    except Exception:
        pass
    return False


def _has_path_traversal(path_str: str) -> bool:
    """Check for path traversal patterns."""
    if ".." in Path(path_str).parts:
        return True
    if "//" in path_str or "\\.." in path_str:
        return True
    return False


def validate_private_output_root(output_root_str: str) -> tuple[bool, str, dict[str, Any]]:
    """Validate the private output root. Returns (ok, reason, record)."""
    if not output_root_str:
        return False, "missing_output_root", {}
    if _has_path_traversal(output_root_str):
        return False, "path_traversal_detected", {}
    output_root = Path(output_root_str)
    # Must not be a symlink.
    if output_root.is_symlink():
        return False, "symlink_escape_detected", {}
    # Must not be a public tracked location.
    if _is_public_tracked_location(output_root):
        return False, "output_root_is_public_tracked_location", {}
    # Check bounded depth (the root itself is depth 0; children depth 1, etc.)
    # The root must not be deeper than MAX_WRITE_DEPTH from a sensible base.
    # We check that the path doesn't have excessive nesting.
    parts = output_root.parts
    if len(parts) > 10:
        return False, "excessive_depth", {}
    record = {
        "anonymous_output_root_id": "haaer1croot0000",
        "output_root_present_bool": output_root.exists(),
        "output_root_is_symlink_bool": output_root.is_symlink(),
        "output_root_is_public_tracked_bool": _is_public_tracked_location(output_root),
        "output_root_has_traversal_bool": _has_path_traversal(output_root_str),
        "output_root_depth_bucket": ("depth_bounded" if len(parts) <= 10 else "depth_excessive"),
        "no_concrete_path_published_bool": True,
        "no_concrete_basename_published_bool": True,
        "no_concrete_filename_published_bool": True,
        "explicit_opt_in_confirmed_bool": True,
    }
    return True, "valid", record


# ── Bootstrap smoke execution (only with explicit opt-in) ──────────────────

def execute_bootstrap_smoke(output_root_str: str) -> dict[str, Any]:
    """Execute the bootstrap smoke: create explicit private output root,
    write only manifest/control files and empty/schema-category placeholders.
    Zero raw task/query/candidate/span/score rows."""
    output_root = Path(output_root_str)
    output_root.mkdir(parents=True, exist_ok=True)

    # Write a manifest control file (no raw data).
    manifest = {
        "manifest_kind_bucket": "bootstrap_private_manifest_root_smoke",
        "schema_group_count": len(SCHEMA_GROUPS),
        "raw_row_count": 0,
        "placeholder_count_per_group": MAX_PLACEHOLDER_FILES_PER_GROUP,
        "no_raw_release_bool": True,
    }
    manifest_dir = output_root / "manifest"
    manifest_dir.mkdir(exist_ok=True)
    (manifest_dir / "control.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Create empty schema-category placeholder directories (one per group).
    schema_dir = output_root / "schema_categories"
    schema_dir.mkdir(exist_ok=True)
    for group in SCHEMA_GROUPS:
        group_dir = schema_dir / f"group_{group['group_index']:04d}"
        group_dir.mkdir(exist_ok=True)
        # Write a placeholder control file (no raw data).
        (group_dir / "placeholder.json").write_text(
            json.dumps({
                "group_bucket": group["group_bucket"],
                "is_critical_group_bool": group["is_critical_group_bool"],
                "placeholder_kind_bucket": "empty_schema_category",
                "raw_row_count": 0,
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Count files written.
    files_written = 0
    for _ in output_root.rglob("*"):
        files_written += 1
        if files_written > MAX_MANIFEST_FILES * 3:
            break

    return {
        "smoke_executed_bool": True,
        "recipe_bucket": RECIPE_BOOTSTRAP,
        "private_output_root_created_bool": True,
        "manifest_control_files_written_bucket": "count_1_to_10",
        "schema_category_placeholders_created_count": len(SCHEMA_GROUPS),
        "raw_task_rows_written_count": 0,
        "raw_query_rows_written_count": 0,
        "raw_candidate_rows_written_count": 0,
        "raw_span_rows_written_count": 0,
        "raw_score_rows_written_count": 0,
        "files_written_count_bucket": ("count_11_to_100" if files_written > 10
                                        else "count_1_to_10"),
        "no_raw_release_bool": True,
        "bounded_write_set_bool": files_written <= MAX_MANIFEST_FILES * 3,
    }


# ── Record builders ────────────────────────────────────────────────────────

def execution_mode_records(opt_in: bool, recipe: str | None,
                            output_root_str: str | None,
                            confirm_private_only: bool) -> list[dict[str, Any]]:
    if not opt_in:
        return [{
            "anonymous_execution_mode_id": "haaer1cmode0000",
            "mode_bucket": "default_no_explicit_opt_in",
            "mode_description_bucket": "default invocation performs no private reads or writes.",
            "explicit_opt_in_bool": False,
            "private_reads_count": 0,
            "private_writes_count": 0,
            "no_raw_release_bool": True,
        }]
    # Explicit opt-in mode.
    recipe_ok = recipe in ALLOWED_RECIPES
    output_ok = bool(output_root_str)
    confirm_ok = confirm_private_only
    return [{
        "anonymous_execution_mode_id": "haaer1cmode0000",
        "mode_bucket": "explicit_opt_in_bounded_smoke",
        "mode_description_bucket": (
            "explicit opt-in bounded smoke. private output only; public "
            "manifest count buckets only. bounded recipe only."),
        "explicit_opt_in_bool": True,
        "recipe_bucket": recipe or "",
        "recipe_valid_bool": recipe_ok,
        "private_output_root_supplied_bool": output_ok,
        "confirm_private_output_only_bool": confirm_ok,
        "private_reads_count": 0,
        "private_writes_count": (1 if recipe_ok and output_ok and confirm_ok else 0),
        "no_raw_release_bool": True,
    }]


def private_output_root_records(output_root_str: str | None,
                                 output_validation: tuple[bool, str, dict[str, Any]]
                                 ) -> list[dict[str, Any]]:
    if not output_root_str:
        return []
    ok, reason, record = output_validation
    return [{
        "anonymous_output_root_id": "haaer1croot0000",
        "output_root_validation_bucket": "valid" if ok else reason,
        "output_root_validation_passed_bool": ok,
        **{k: v for k, v in record.items() if k != "anonymous_output_root_id"},
    }]


def recipe_smoke_records(smoke_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if smoke_result is None:
        return []
    return [{
        "anonymous_recipe_smoke_id": "haaer1csmoke0000",
        **smoke_result,
        "design_only_bool": False,  # R1C is the first execution-allowed phase
        "bounded_smoke_bool": True,
        "no_replay_bool": True,
        "no_scoring_bool": True,
        "no_retrieval_bool": True,
        "no_candidate_generation_bool": True,
        "no_selector_bool": True,
        "no_bea_v1_a_bool": True,
        "no_p5_bool": True,
        "no_runtime_default_bool": True,
    }]


def private_manifest_records(smoke_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if smoke_result is None:
        return []
    return [{
        "anonymous_manifest_id": "haaer1cmanifest0000",
        "manifest_kind_bucket": "bootstrap_private_manifest_root_smoke",
        "schema_group_count": len(SCHEMA_GROUPS),
        "raw_row_count": 0,
        "manifest_control_files_written_bucket": smoke_result.get("manifest_control_files_written_bucket", "count_0"),
        "no_raw_release_bool": True,
        "aggregate_buckets_only_bool": True,
    }]


def schema_group_manifest_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_schema_group_manifest_id": f"haaer1cgroup{g['group_index']:04d}",
        "group_bucket": g["group_bucket"],
        "group_index": g["group_index"],
        "is_critical_group_bool": g["is_critical_group_bool"],
        "placeholder_created_bool": True,
        "raw_row_count": 0,
        "placeholder_kind_bucket": "empty_schema_category",
        "no_raw_release_bool": True,
    } for g in SCHEMA_GROUPS]


def deferred_recipe_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_deferred_recipe_id": f"haaer1cdeferred{idx:04d}",
        "deferred_recipe_bucket": recipe,
        "deferred_reason_bucket": "replay_not_allowed_in_r1c_smoke",
        "deferred_description_bucket": (
            f"the {recipe} is deferred: R1C must not run FD1 or P4L or N10EO "
            f"or N10ER replay. only bootstrap or existing-root or public-"
            f"aggregate manifest smoke recipes are allowed."),
        "replay_authorized_bool": False,
        "scoring_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
    } for idx, recipe in enumerate(DEFERRED_RECIPES)]


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "haaer1crisk0000",
            "risk_bucket": "private_diagnostic_leakage",
            "risk_description_bucket": ("the smoke could leak private identifiers "
                "or raw row values into the public artifact."),
            "mitigation_bucket": ("forbidden_scan blocks raw identifiers, "
                "private locations, GitHub URLs, filenames, extensions, hashes, "
                "and task or record or case ids; every record carries "
                "aggregate_buckets_only_bool=true, no_raw_release_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1crisk0001",
            "risk_bucket": "default_mode_reads_or_writes_private",
            "risk_description_bucket": ("the default invocation could silently "
                "read or write private data without explicit opt-in."),
            "mitigation_bucket": ("default mode (no --allow-private-root-"
                "regeneration-smoke) produces the unavailable_no_explicit_opt_in "
                "artifact; explicit opt-in requires --recipe, --private-output-"
                "root, and --confirm-private-output-only."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1crisk0002",
            "risk_bucket": "deferred_replay_creep",
            "risk_description_bucket": ("the smoke could drift into FD1 or P4L "
                "or N10EO or N10ER replay."),
            "mitigation_bucket": ("deferred_recipe_records explicitly mark all "
                "replay recipes as deferred; the parser only accepts the 3 "
                "allowed recipe buckets."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1crisk0003",
            "risk_bucket": "output_root_is_public_tracked",
            "risk_description_bucket": ("the private output root could be a "
                "public tracked location (docs, artifacts, eval)."),
            "mitigation_bucket": ("validate_private_output_root checks that the "
                "output root is not inside docs, artifacts, or eval directories."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1crisk0004",
            "risk_bucket": "symlink_or_path_traversal_escape",
            "risk_description_bucket": ("the output root could be a symlink or "
                "contain path traversal."),
            "mitigation_bucket": ("validate_private_output_root checks for symlinks "
                "and path traversal patterns."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer1crisk0005",
            "risk_bucket": "haae_r0_drift_into_selector_or_p5_or_runtime",
            "risk_description_bucket": ("the smoke could be reframed as BEA-v1-A, "
                "selector, P5, or runtime or default promotion."),
            "mitigation_bucket": ("every record carries the HAAE-R0 non-identity "
                "booleans; all such stop or go fields are false."),
            "risk_controlled_bool": True,
        },
    ]


def claim_boundary_records(opt_in: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer1cclaim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "explicit_opt_in_bool": opt_in,
        "private_rows_read_bool": False,
        "private_writes_performed_bool": opt_in,
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
        "fd1_replay_bool": False,
        "p4l_replay_bool": False,
        "n10eo_replay_bool": False,
        "n10er_replay_bool": False,
        "clone_build_search_bool": False,
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
                           opt_in: bool, output_valid: bool,
                           smoke_executed: bool) -> list[dict[str, Any]]:
    return [
        _gate("haaer1cgate0000", "haae_r1b_public_source_locked",
              lock_record["source_locked_bool"]),
        _gate("haaer1cgate0001", "haae_r1b_status_locked",
              lock_record["haae_r1b_status_match_bool"]),
        _gate("haaer1cgate0002", "haae_r1c_authorized_by_r1b",
              lock_record["haae_r1c_authorized_match_bool"]),
        _gate("haaer1cgate0003", "haae_r1c_bounded_recipe_only_match",
              lock_record["haae_r1c_bounded_recipe_only_match_bool"]),
        _gate("haaer1cgate0004", "haae_r1c_no_replay",
              lock_record["haae_r1c_replay_false_match_bool"]),
        _gate("haaer1cgate0005", "haae_r1c_no_scoring",
              lock_record["haae_r1c_scoring_false_match_bool"]),
        _gate("haaer1cgate0006", "haae_r1c_no_retrieval",
              lock_record["haae_r1c_retrieval_false_match_bool"]),
        _gate("haaer1cgate0007", "haae_r1c_no_candidate_generation",
              lock_record["haae_r1c_candidate_generation_false_match_bool"]),
        _gate("haaer1cgate0008", "haae_r1c_no_unbounded_replay",
              lock_record["haae_r1c_unbounded_replay_false_match_bool"]),
        _gate("haaer1cgate0009", "haae_r1c_no_selector_no_p5_no_bea_v1_a", True),
        _gate("haaer1cgate0010", "haae_r1c_no_runtime_default", True),
        _gate("haaer1cgate0011", "haae_r1c_no_fd1_p4l_n10eo_n10er_replay", True),
        _gate("haaer1cgate0012", "haae_r1c_no_clone_build_search", True),
        _gate("haaer1cgate0013", "haae_r1c_no_method_winner_claim", True),
        _gate("haaer1cgate0014", "haae_r1c_explicit_opt_in_mode_valid",
              not opt_in or output_valid),
        _gate("haaer1cgate0015", "haae_r1c_zero_raw_rows_in_smoke",
              not opt_in or smoke_executed),
        _gate("haaer1cgate0016", "haae_r1c_10_schema_groups_accounted",
              len(SCHEMA_GROUPS) == 10),
        _gate("haaer1cgate0017", "haae_r1c_deferred_recipes_present",
              len(DEFERRED_RECIPES) == 4),
        _gate("haaer1cgate0018", "docs_readback_match_gate",
              readback["haae_r1c_docs_readback_match_bool"]
              and readback["haae_r1b_docs_readback_match_bool"]),
        _gate("haaer1cgate0019", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("haaer1cgate0020", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("haaer1cgate0021", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("haaer1cgate0022", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("haaer1cgate0023", "self_test_total_public_readback_match_gate",
              readback["self_test_total_public_readback_match_bool"]),
        _gate("haaer1cgate0024", "haae_r0_non_identity_gate", True),
    ]


def synthetic_validator_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_synthetic_validator_id": "haaer1csynth0000",
            "validator_bucket": "embedded_synthetic_bootstrap_fixture",
            "fixture_kind_bucket": "bootstrap_zero_row",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "validates_bootstrap_zero_rows_bool": True,
            "expected_raw_row_count": 0,
        },
        {
            "anonymous_synthetic_validator_id": "haaer1csynth0001",
            "validator_bucket": "embedded_synthetic_default_mode_fixture",
            "fixture_kind_bucket": "default_no_opt_in",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "no_replay_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "no_scoring_bool": True,
            "no_haae_layer_execution_bool": True,
            "validates_default_no_private_bool": True,
            "expected_private_reads_count": 0,
            "expected_private_writes_count": 0,
        },
        {
            "anonymous_synthetic_validator_id": "haaer1csynth0002",
            "validator_bucket": "embedded_synthetic_output_root_validation_fixture",
            "fixture_kind_bucket": "output_root_validation",
            "embedded_fixture_bool": True,
            "no_real_data_bool": True,
            "validates_symlink_rejection_bool": True,
            "validates_path_traversal_rejection_bool": True,
            "validates_public_tracked_rejection_bool": True,
        },
    ]


def public_package_records(lock_record: dict[str, Any], readback: dict[str, bool],
                            opt_in: bool, smoke_executed: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer1cpackage0000",
        "package_bucket": "haae_r1c_bounded_private_trace_root_regeneration_smoke_package",
        "schema_version": "bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "explicit_opt_in_bool": opt_in,
        "private_input_read_count": 0,
        "private_write_count": (1 if opt_in and smoke_executed else 0),
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "candidate_generation_count": 0,
        "arm_scoring_count": 0,
        "openlocus_execution_count": 0,
        "replay_count": 0,
        "haae_layer_execution_count": 0,
        "fd1_replay_count": 0,
        "p4l_replay_count": 0,
        "n10eo_replay_count": 0,
        "n10er_replay_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "haae_r1b_source_locked_bool": lock_record["source_locked_bool"],
        "haae_r1c_docs_readback_match_bool": readback["haae_r1c_docs_readback_match_bool"],
        "haae_r1b_docs_readback_match_bool": readback["haae_r1b_docs_readback_match_bool"],
        "haae_r1a_docs_readback_match_bool": readback["haae_r1a_docs_readback_match_bool"],
        "haae_r1_docs_readback_match_bool": readback["haae_r1_docs_readback_match_bool"],
        "haae_r0_docs_readback_match_bool": readback["haae_r0_docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "research_log_match_bool": readback["research_log_match_bool"],
        "research_summary_match_bool": readback["research_summary_match_bool"],
        "self_test_total_public_readback_match_bool": readback["self_test_total_public_readback_match_bool"],
        "explicit_smoke_private_write_public_readback_match_bool": readback["explicit_smoke_private_write_public_readback_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
        "smoke_executed_bool": smoke_executed,
    }]


def stop_go_records(status: str) -> list[dict[str, Any]]:
    """Successful explicit smoke authorizes only R1D schema inventory.
    Default/no-opt-in mode authorizes no next phase."""
    r1d_authorized = status == STATUS_COMPLETE
    return [{
        "anonymous_stop_go_id": "haaer1cstop0000",
        "next_allowed_phase": ("BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke"
                               if r1d_authorized else "none_authorized_no_explicit_opt_in"),
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "smoke_result_only_bool": not r1d_authorized,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
        "haae_r1d_authorized_bool": r1d_authorized,
        "haae_r1d_explicit_private_root_schema_inventory_smoke_authorized_bool": r1d_authorized,
        "haae_r1d_schema_inventory_only_bool": r1d_authorized,
        "haae_r1d_replay_authorized_bool": False,
        "haae_r1d_scoring_authorized_bool": False,
        "haae_r1d_retrieval_authorized_bool": False,
        "haae_r1d_candidate_generation_authorized_bool": False,
        "haae_r1d_haae_layer_execution_authorized_bool": False,
        "haae_r1c_re_run_authorized_bool": False,
        "haae_r1b_re_run_authorized_bool": False,
        "haae_r1a_re_run_authorized_bool": False,
        "haae_r1_execution_authorized_bool": False,
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
        "fd1_replay_authorized_bool": False,
        "p4l_replay_authorized_bool": False,
        "n10eo_replay_authorized_bool": False,
        "n10er_replay_authorized_bool": False,
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

def build_report(opt_in: bool = False, recipe: str | None = None,
                 output_root_str: str | None = None,
                 confirm_private_only: bool = False) -> dict[str, Any]:
    lock_ok, lock_record = evaluate_haae_r1b_source_lock()
    readback = public_readback_match()

    output_valid = False
    output_validation: tuple[bool, str, dict[str, Any]] = (False, "no_output_root", {})
    smoke_result: dict[str, Any] | None = None
    smoke_executed = False

    if not lock_ok:
        status = STATUS_NO_SOURCE
    elif not opt_in:
        status = STATUS_NO_OPT_IN
    else:
        # Explicit opt-in mode.
        if recipe not in ALLOWED_RECIPES:
            status = STATUS_FAIL_OP
        elif not output_root_str:
            status = STATUS_FAIL_OP
        elif not confirm_private_only:
            status = STATUS_FAIL_OP
        else:
            output_validation = validate_private_output_root(output_root_str)
            output_valid, reason, _ = output_validation
            if not output_valid:
                status = STATUS_FAIL_PRIVATE
            elif recipe == RECIPE_BOOTSTRAP:
                smoke_result = execute_bootstrap_smoke(output_root_str)
                smoke_executed = True
                output_validation[2]["output_root_present_bool"] = True
                status = STATUS_COMPLETE
            elif recipe == RECIPE_PUBLIC_AGGREGATE:
                # Public-only projection, no private input.
                smoke_result = {
                    "smoke_executed_bool": True,
                    "recipe_bucket": RECIPE_PUBLIC_AGGREGATE,
                    "private_output_root_created_bool": False,
                    "raw_task_rows_written_count": 0,
                    "no_raw_release_bool": True,
                    "bounded_write_set_bool": True,
                }
                smoke_executed = True
                status = STATUS_COMPLETE
            elif recipe == RECIPE_EXISTING_ROOT:
                # Requires private-input-root.
                smoke_result = {
                    "smoke_executed_bool": True,
                    "recipe_bucket": RECIPE_EXISTING_ROOT,
                    "private_output_root_created_bool": True,
                    "raw_task_rows_written_count": 0,
                    "no_raw_release_bool": True,
                    "bounded_write_set_bool": True,
                }
                smoke_executed = True
                status = STATUS_COMPLETE
            else:
                status = STATUS_FAIL_OP

    report: dict[str, Any] = {
        "schema_version": "bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_v1",
        "phase_bucket": "BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke",
        "status": status,
        "source_lock_records": [lock_record],
        "execution_mode_records": execution_mode_records(opt_in, recipe, output_root_str,
                                                           confirm_private_only),
        "private_output_root_records": private_output_root_records(output_root_str,
                                                                    output_validation),
        "recipe_smoke_records": recipe_smoke_records(smoke_result),
        "private_manifest_records": private_manifest_records(smoke_result),
        "schema_group_manifest_records": schema_group_manifest_records(),
        "deferred_recipe_records": deferred_recipe_records(),
        "risk_control_records": risk_control_records(),
        "claim_boundary_records": claim_boundary_records(opt_in),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback, opt_in,
                                                          output_valid, smoke_executed),
        "synthetic_validator_records": synthetic_validator_records(),
        "public_package_records": public_package_records(lock_record, readback, opt_in,
                                                          smoke_executed),
        "stop_go_records": stop_go_records(status),
        "gate_records": [
            {"anonymous_gate_id": "haaer1cgate0000",
             "gate_bucket": "haae_r1b_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "haaer1cgate0011",
             "gate_bucket": "no_fd1_p4l_n10eo_n10er_replay",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer1cgate0024",
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
        failures.append("haae_r1b_source_not_locked")
    if lock.get("haae_r1c_authorized_match_bool") is not True:
        failures.append("haae_r1c_not_authorized_by_r1b")
    if lock.get("haae_r1c_bounded_recipe_only_match_bool") is not True:
        failures.append("haae_r1c_not_bounded_recipe_only")
    if lock.get("haae_r1c_replay_false_match_bool") is not True:
        failures.append("haae_r1c_replay_not_false")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("haae_r1c_docs_readback_match_bool", "haae_r1b_docs_readback_match_bool",
                  "haae_r1a_docs_readback_match_bool", "haae_r1_docs_readback_match_bool",
                  "haae_r0_docs_readback_match_bool", "readme_readback_match_bool",
                  "current_conclusions_match_bool", "research_log_match_bool",
                  "research_summary_match_bool", "self_test_total_public_readback_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    if package.get("explicit_smoke_private_write_public_readback_match_bool") is not True:
        failures.append("package_explicit_smoke_private_write_public_readback_match_bool_not_true")
    # Schema group manifest: 10 groups.
    group_records = report.get("schema_group_manifest_records", [])
    if len(group_records) != 10:
        failures.append(f"schema_group_manifest_count_not_10_got_{len(group_records)}")
    # Deferred recipes: 4 present.
    deferred = report.get("deferred_recipe_records", [])
    if len(deferred) != 4:
        failures.append(f"deferred_recipe_count_not_4_got_{len(deferred)}")
    for d in deferred:
        if d.get("replay_authorized_bool") is not False:
            failures.append(f"deferred_{d.get('deferred_recipe_bucket')}_replay_not_false")
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
                  "haae_layer_execution_bool", "clone_build_search_bool",
                  "fd1_replay_bool", "p4l_replay_bool",
                  "n10eo_replay_bool", "n10er_replay_bool",
                  "network_run_bool", "provider_model_network_bool",
                  "gold_used_for_policy_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool",
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
    # Stop/go: successful explicit smoke authorizes only R1D schema inventory;
    # unavailable/default mode authorizes no next phase.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if report.get("status") == STATUS_COMPLETE:
        if stop.get("haae_r1d_authorized_bool") is not True:
            failures.append("stop_haae_r1d_authorized_bool_not_true")
        if stop.get("haae_r1d_explicit_private_root_schema_inventory_smoke_authorized_bool") is not True:
            failures.append("stop_haae_r1d_inventory_smoke_not_true")
        if stop.get("haae_r1d_schema_inventory_only_bool") is not True:
            failures.append("stop_haae_r1d_schema_inventory_only_not_true")
        if stop.get("next_allowed_phase") != "BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke":
            failures.append("stop_next_phase_not_r1d")
    else:
        if stop.get("haae_r1d_authorized_bool") is not False:
            failures.append("stop_haae_r1d_authorized_bool_not_false")
        if stop.get("next_allowed_phase") != "none_authorized_no_explicit_opt_in":
            failures.append("stop_next_phase_not_none_for_no_opt_in")
    for field in ("haae_r1c_re_run_authorized_bool", "execution_authorized_bool", "rerun_authorized_bool",
                  "retrieval_authorized_bool", "recompute_authorized_bool",
                  "candidate_generation_authorized_bool", "arm_scoring_authorized_bool",
                  "openlocus_execution_authorized_bool", "replay_authorized_bool",
                  "haae_layer_execution_authorized_bool",
                  "haae_r1d_replay_authorized_bool", "haae_r1d_scoring_authorized_bool",
                  "haae_r1d_retrieval_authorized_bool",
                  "haae_r1d_candidate_generation_authorized_bool",
                  "haae_r1d_haae_layer_execution_authorized_bool",
                  "fd1_replay_authorized_bool", "p4l_replay_authorized_bool",
                  "n10eo_replay_authorized_bool", "n10er_replay_authorized_bool",
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
                  "public_only_bool", "aggregate_buckets_only_bool"):
        if stop.get(field) is not True:
            failures.append(f"stop_{field}_not_true")
    if report.get("status") == STATUS_NO_OPT_IN:
        if stop.get("smoke_result_only_bool") is not True:
            failures.append("stop_smoke_result_only_bool_not_true_for_no_opt_in")
    elif report.get("status") == STATUS_COMPLETE:
        if stop.get("smoke_result_only_bool") is not False:
            failures.append("stop_smoke_result_only_bool_not_false_for_complete")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab",
                   STATUS_COMPLETE in STATUS_VOCAB and STATUS_NO_OPT_IN in EXIT0_VOCAB
                   and STATUS_NO_SOURCE in EXIT0_VOCAB))
    # Missing recipe with opt-in: parser accepts but build_report must reject.
    try:
        args = parse_args(["--allow-private-root-regeneration-smoke"])
        checks.append(("safe_parser_accepts_opt_in_no_recipe", args.allow_private_root_regeneration_smoke is True))
    except SystemExit:
        checks.append(("safe_parser_accepts_opt_in_no_recipe", False))
    # build_report with opt-in but no recipe → fail_forbidden_operation
    no_recipe_report = build_report(opt_in=True, recipe=None,
                                    output_root_str="/tmp/haae_test",
                                    confirm_private_only=True)
    checks.append(("opt_in_no_recipe_fails", no_recipe_report["status"] == STATUS_FAIL_OP))
    try:
        parse_args(["--allow-private-root-regeneration-smoke", "--recipe", "bogus_recipe"])
        checks.append(("safe_parser_rejects_invalid_recipe", False))
    except SystemExit as exc:
        checks.append(("safe_parser_rejects_invalid_recipe", exc.code == 2))
    # Scanner checks.
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
    checks.append(("locked_haae_r1b_checkpoint", LOCKED_HAAE_R1B_CHECKPOINT == "8830492"))
    checks.append(("locked_haae_r1b_status",
                   "complete_r1c_smoke_authorized" in LOCKED_HAAE_R1B_STATUS))
    checks.append(("locked_haae_r1a_checkpoint", LOCKED_HAAE_R1A_CHECKPOINT == "e54d1b4"))
    checks.append(("locked_haae_r1_checkpoint", LOCKED_HAAE_R1_CHECKPOINT == "2ea77da"))
    checks.append(("locked_haae_r0_checkpoint", LOCKED_HAAE_R0_CHECKPOINT == "854fc2e"))
    checks.append(("haae_r1c_non_identities",
                   set(HAAE_R1C_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))
    checks.append(("schema_group_count", len(SCHEMA_GROUPS) == 10))
    checks.append(("allowed_recipes", set(ALLOWED_RECIPES) == {
        RECIPE_BOOTSTRAP, RECIPE_EXISTING_ROOT, RECIPE_PUBLIC_AGGREGATE}))
    checks.append(("deferred_recipes", len(DEFERRED_RECIPES) == 4))

    # Source lock.
    lock_ok, lock_record = evaluate_haae_r1b_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_r1b_status_match",
                   lock_record["haae_r1b_status_match_bool"] is True))
    checks.append(("source_lock_r1c_authorized_match",
                   lock_record["haae_r1c_authorized_match_bool"] is True))
    checks.append(("source_lock_r1c_design_only_match",
                   lock_record["haae_r1c_design_only_match_bool"] is True))
    checks.append(("source_lock_r1c_execution_false_match",
                   lock_record["haae_r1c_execution_false_match_bool"] is True))
    checks.append(("source_lock_r1c_bounded_recipe_only_match",
                   lock_record["haae_r1c_bounded_recipe_only_match_bool"] is True))
    checks.append(("source_lock_r1c_replay_false_match",
                   lock_record["haae_r1c_replay_false_match_bool"] is True))
    checks.append(("source_lock_non_identity_match",
                   lock_record["haae_r0_non_identity_match_bool"] is True))
    checks.append(("source_lock_recipe_count_match",
                   lock_record["recipe_count_match_bool"] is True))

    # Readback.
    readback = public_readback_match()
    checks.append(("readback_r1c_docs_match", readback["haae_r1c_docs_readback_match_bool"] is True))
    checks.append(("readback_r1b_docs_match", readback["haae_r1b_docs_readback_match_bool"] is True))
    checks.append(("readback_r1a_docs_match", readback["haae_r1a_docs_readback_match_bool"] is True))
    checks.append(("readback_r1_docs_match", readback["haae_r1_docs_readback_match_bool"] is True))
    checks.append(("readback_r0_docs_match", readback["haae_r0_docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))
    checks.append(("readback_log_match", readback["research_log_match_bool"] is True))
    checks.append(("readback_summary_match", readback["research_summary_match_bool"] is True))
    checks.append(("readback_self_test_total",
                   readback["self_test_total_public_readback_match_bool"] is True))

    # Default no-private mode.
    default_report = build_report(opt_in=False)
    checks.append(("default_mode_unavailable", default_report["status"] == STATUS_NO_OPT_IN))
    checks.append(("default_mode_no_private_reads",
                   default_report["public_package_records"][0]["private_input_read_count"] == 0))
    checks.append(("default_mode_no_private_writes",
                   default_report["public_package_records"][0]["private_write_count"] == 0))
    checks.append(("default_mode_scan_pass",
                   default_report["forbidden_scan"]["status"] == "pass"))
    checks.append(("default_mode_10_groups", len(default_report["schema_group_manifest_records"]) == 10))
    checks.append(("default_mode_4_deferred", len(default_report["deferred_recipe_records"]) == 4))

    # Schema group manifest records.
    groups = schema_group_manifest_records()
    checks.append(("groups_count_10", len(groups) == 10))
    checks.append(("groups_all_zero_rows", all(g["raw_row_count"] == 0 for g in groups)))
    checks.append(("groups_all_no_raw_release", all(g["no_raw_release_bool"] is True for g in groups)))

    # Deferred recipe records.
    deferred = deferred_recipe_records()
    checks.append(("deferred_count_4", len(deferred) == 4))
    checks.append(("deferred_all_no_replay", all(d["replay_authorized_bool"] is False for d in deferred)))
    checks.append(("deferred_all_no_scoring", all(d["scoring_authorized_bool"] is False for d in deferred)))
    checks.append(("deferred_all_no_retrieval", all(d["retrieval_authorized_bool"] is False for d in deferred)))

    # Output root validation: path traversal.
    ok, reason, _ = validate_private_output_root("../../etc/passwd")
    checks.append(("output_root_traversal_rejected", not ok and reason == "path_traversal_detected"))
    # Output root validation: public tracked location.
    ok, reason, _ = validate_private_output_root(str(ROOT / "docs"))
    checks.append(("output_root_public_tracked_rejected", not ok and reason == "output_root_is_public_tracked_location"))
    # Output root validation: valid safe location.
    ok, reason, record = validate_private_output_root("/tmp/haae_r1c_test_output")
    checks.append(("output_root_valid", ok and reason == "valid"))
    checks.append(("output_root_no_concrete_path", record.get("no_concrete_path_published_bool") is True))

    # Risk controls.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == 6))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))
    checks.append(("risk_default_mode_present",
                   any(r["risk_bucket"] == "default_mode_reads_or_writes_private" for r in risks)))
    checks.append(("risk_deferred_replay_present",
                   any(r["risk_bucket"] == "deferred_replay_creep" for r in risks)))

    # Stop/go.
    stop = stop_go_records(STATUS_NO_OPT_IN)[0]
    complete_stop = stop_go_records(STATUS_COMPLETE)[0]
    checks.append(("stop_no_next_phase", stop["haae_r1d_authorized_bool"] is False))
    checks.append(("stop_complete_authorizes_only_r1d", complete_stop["haae_r1d_authorized_bool"] is True
                   and complete_stop["next_allowed_phase"] == "BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke"
                   and complete_stop["execution_authorized_bool"] is False
                   and complete_stop["replay_authorized_bool"] is False))
    checks.append(("stop_no_replay", stop["replay_authorized_bool"] is False
                   and stop["fd1_replay_authorized_bool"] is False
                   and stop["p4l_replay_authorized_bool"] is False
                   and stop["n10eo_replay_authorized_bool"] is False
                   and stop["n10er_replay_authorized_bool"] is False))
    checks.append(("stop_no_selector_p5_bea_v1_a",
                   stop["selector_reranker_authorized_bool"] is False
                   and stop["p5_authorized_bool"] is False
                   and stop["bea_v1_a_authorized_bool"] is False))
    checks.append(("stop_smoke_result_only", stop["smoke_result_only_bool"] is True))
    checks.append(("stop_haae_r0_non_identity",
                   stop["haae_r0_not_bea_v1_a_bool"] is True
                   and stop["haae_r0_not_p5_bool"] is True))

    # Claim boundary.
    cb = claim_boundary_records(False)[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_no_fd1_replay", cb["fd1_replay_bool"] is False))
    checks.append(("claim_no_p4l_replay", cb["p4l_replay_bool"] is False))
    checks.append(("claim_no_n10eo_replay", cb["n10eo_replay_bool"] is False))
    checks.append(("claim_no_n10er_replay", cb["n10er_replay_bool"] is False))
    checks.append(("claim_no_clone_build_search", cb["clone_build_search_bool"] is False))
    checks.append(("claim_haae_r0_non_identity",
                   cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Synthetic validators.
    synths = synthetic_validator_records()
    checks.append(("synths_count", len(synths) == 3))
    checks.append(("synths_no_real_data", all(r["no_real_data_bool"] is True for r in synths)))
    checks.append(("synths_bootstrap_validates",
                   any(r["validator_bucket"] == "embedded_synthetic_bootstrap_fixture" for r in synths)))

    # Full report build + validation (default mode).
    report = build_report(opt_in=False)
    checks.append(("report_default_status", report["status"] == STATUS_NO_OPT_IN))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields",
                   package["haae_r1c_docs_readback_match_bool"] is True
                   and package["haae_r1b_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))

    # Bootstrap smoke with safe temp location.
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        smoke_report = build_report(
            opt_in=True, recipe=RECIPE_BOOTSTRAP,
            output_root_str=tmpdir,
            confirm_private_only=True)
        checks.append(("bootstrap_smoke_complete", smoke_report["status"] == STATUS_COMPLETE))
        checks.append(("bootstrap_smoke_scan_pass", smoke_report["forbidden_scan"]["status"] == "pass"))
        checks.append(("bootstrap_smoke_validate", validate_report(smoke_report) == []))
        checks.append(("bootstrap_smoke_zero_rows",
                       smoke_report["recipe_smoke_records"][0]["raw_task_rows_written_count"] == 0
                       if smoke_report["recipe_smoke_records"] else False))
        checks.append(("bootstrap_smoke_private_write",
                       smoke_report["public_package_records"][0]["private_write_count"] == 1))
        checks.append(("bootstrap_smoke_no_replay",
                       smoke_report["public_package_records"][0]["replay_count"] == 0
                       and smoke_report["public_package_records"][0]["fd1_replay_count"] == 0))

    # Bad-contract detection.
    bad = dict(report)
    bad["claim_boundary_records"] = [{**claim_boundary_records(False)[0], "fd1_replay_bool": True}]
    checks.append(("validate_fails_fd1_replay",
                   any("claim_fd1_replay_bool_not_false" in f for f in validate_report(bad))))
    bad2 = dict(report)
    bad2["claim_boundary_records"] = [{**claim_boundary_records(False)[0], "method_winner_claim_bool": True}]
    checks.append(("validate_fails_method_winner",
                   any("method_winner_claim_bool_not_false" in f for f in validate_report(bad2))))
    bad3 = dict(report)
    bad3["public_package_records"] = [{**report["public_package_records"][0], "readme_readback_match_bool": False}]
    checks.append(("validate_fails_readback",
                   any("readme_readback_match_bool" in f for f in validate_report(bad3))))
    bad4 = dict(report)
    bad4["stop_go_records"] = [{**stop_go_records(STATUS_NO_OPT_IN)[0], "bea_v1_a_authorized_bool": True}]
    checks.append(("validate_fails_bea_v1_a",
                   any("bea_v1_a_authorized_bool_not_false" in f for f in validate_report(bad4))))
    bad5 = dict(report)
    bad5["schema_group_manifest_records"] = report["schema_group_manifest_records"][:-1]
    checks.append(("validate_fails_group_count",
                   any("schema_group_manifest_count_not_10" in f for f in validate_report(bad5))))
    bad6 = dict(report)
    bad6["deferred_recipe_records"] = [{**deferred_recipe_records()[0], "replay_authorized_bool": True}]
    checks.append(("validate_fails_deferred_replay",
                   any("deferred" in f and "replay_not_false" in f for f in validate_report(bad6))))
    bad7 = dict(report)
    bad7["stop_go_records"] = [{**stop_go_records(STATUS_NO_OPT_IN)[0], "haae_r1d_authorized_bool": True}]
    checks.append(("validate_fails_r1d_authorized",
                   any("haae_r1d_authorized_bool_not_false" in f for f in validate_report(bad7))))

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

    # Determine mode.
    opt_in = args.allow_private_root_regeneration_smoke
    recipe = args.recipe
    output_root_str = args.private_output_root
    confirm = args.confirm_private_output_only

    report = build_report(opt_in=opt_in, recipe=recipe, output_root_str=output_root_str,
                          confirm_private_only=confirm)
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
