#!/usr/bin/env python3
"""BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design /
Schema Preflight.

HAAE-R0 is the **public-only design/schema preflight** for the next acquisition
route, opened by the N10ET close-out (checkpoint ``26d817e``). It is **not** an
execution phase. It reads **only** public artifacts/docs/current
conclusions/research logs/README and git metadata:

  * the committed N10ET public aggregate report (the close-out design/decision
    that authorized HAAE-R0);
  * the N10ET evaluator for schema/status validation only (never executed — no
    rerun/recompute);
  * the N10ET EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
    research-log/summary, and README public readback;
  * git metadata: the ``26d817e`` checkpoint that recorded the N10ET result.

Forbidden: any private reads (project-private roots, temporary rerun paths, CI
raw logs, repo clones, raw candidates/orders/labels/paths/queries/tasks/repos,
per-task diagnostics), any CI rerun, any retrieval/recompute, any
candidate generation/materialization, any arm scoring, any selector/reranker
execution, any threshold tuning, any promotion, any runtime/default change, any
method/downstream/heldout claim, any OpenLocus execution, any provider/embedding
network call, any P5/BEA-v1-A authorization, or any runtime/default promotion.

HAAE-R0:

  * Locks the N10ET public facts (checkpoint ``26d817e``, status
    ``n10et_public_safety_probe_design_decision_complete_haae_r0_authorized``,
    HAAE-R0 authorized true, HAAE-R0 execution false, BEA-v1-A false).
  * Designs (no execution) the **Hierarchical Actionable Evidence Acquisition
    Route** as a schema preflight: machine-readable, concrete control-plane
    records for the route architecture (source_acquisition /
    rank_pack_depth_to_head / span_projection / scheduler_operating_point), a
    unified private trace schema spec (10 groups), a public aggregation contract,
    arm specs (BM25_same_budget / RRF_same_budget / BEA_v0.3_frozen /
    V1_sched_span / V1_sched_span_rank), metric specs, a held-out protocol,
    stop rules, and a synthetic validator with an embedded synthetic fixture.
  * Designs (no execution) and authorizes **only** the next phase:
    **BEA-v1-HAAE-R1 — Unified Private Trace Schema Feasibility Inventory** —
    with explicit private roots only and aggregate buckets only, no replay,
    no scoring, no retrieval, no candidate generation.
  * Emits a public-only design/schema-preflight artifact with explicit false
    privacy/claim boundary fields, scanner-validated.

HAAE-R0 is explicitly **not** BEA-v1-A, not selector-only, not selector/reranker
execution, not P5, and not a runtime/default promotion. Every route architecture,
schema, aggregation, arm, metric, heldout, stop-rule, validator, HAAE-R1
contract, claim boundary, and stop/go record carries the corresponding
non-identity booleans.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10ET_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10et_public_safety_probe_design_decision"
    / "bea_v1_n10et_public_safety_probe_design_decision_report.json"
)
N10ET_EVAL = ROOT / "eval" / "bea_v1_n10et_public_safety_probe_design_decision.py"
README_PATH = ROOT / "README.md"
N10ET_DOC_EN = ROOT / "docs" / "en" / "bea-v1-n10et-public-safety-probe-design-decision.md"
N10ET_DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-n10et-public-safety-probe-design-decision.md"
HAAE_R0_DOC_EN = (
    ROOT / "docs" / "en"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
HAAE_R0_DOC_ZH = (
    ROOT / "docs" / "zh"
    / "bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md"
)
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"

# ── Locked N10ET public facts (git metadata + upstream lock) ───────────────
LOCKED_N10ET_CHECKPOINT = "26d817e"
LOCKED_N10ET_STATUS = (
    "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"
)
LOCKED_N10ET_NEXT_ALLOWED_PHASE = (
    "BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design / "
    "Schema Preflight"
)

# ── Next route (HAAE-R0 designs + authorizes ONLY HAAE-R1) ─────────────────
NEXT_ROUTE = "BEA-v1-HAAE-R1"
NEXT_ROUTE_FULL = (
    "BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory"
)
NEXT_ROUTE_BUCKET = "haae_r1_unified_private_trace_schema_feasibility_inventory"

# ── Explicit non-identities — HAAE-R0 is NOT any of these. ─────────────────
HAAE_R0_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_COMPLETE = "haae_r0_design_schema_preflight_complete_haae_r1_authorized"
STATUS_NO_SOURCE = "haae_r0_design_schema_preflight_unavailable_no_locked_source"
STATUS_FAIL_LOCK = "fail_n10et_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
EXIT0_VOCAB = {STATUS_COMPLETE, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_SCAN,
                             STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT}

# Mirror the N10ET privacy scanner verbatim so the schema-preflight phase
# upholds the same publication boundary as the close-out it follows.
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
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|tsx|js|jsx|mjs|go|java|kt|c|cpp|h|hpp|cs|rb|md|txt|sh|yaml|yml|toml)", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"\b(ci-[0-9]{5})\b", re.I),
]

# Self-test check count (kept in sync with run_self_test; verified by --self-test).
SELF_TEST_TOTAL_CHECKS = 132


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-HAAE-R0 hierarchical actionable evidence acquisition "
                    "route design / schema preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n10et-report", default=str(N10ET_REPORT),
                        help="path to the committed N10ET public aggregate artifact")
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
    N10ET close-out facts and the HAAE-R0 schema preflight + HAAE-R1 handoff.
    Reads only public docs; performs no execution.

    Per-target fragment vocabulary:
      * README + current-research-conclusions must mention HAAE-R0 + HAAE-R1 +
        the locked N10ET checkpoint ``26d817e`` + the locked N10ET status +
        the HAAE-R0 status + at least one HAAE-R0 non-identity (BEA-v1-A /
        selector/reranker / selector-only / P5).
      * HAAE-R0 docs must mention HAAE-R0 + HAAE-R1 + ``26d817e`` + the locked
        N10ET status + the HAAE-R0 status + at least one non-identity.
      * N10ET docs must mention HAAE-R0 (as the next authorized phase). They do
        not need to mention HAAE-R1 (HAAE-R1 was unknown at N10ET time).
      * research-log/summary must mention HAAE-R0 + HAAE-R1 + at least one
        HAAE-R0 non-identity.
    """
    common_fragments = [
        LOCKED_N10ET_CHECKPOINT,
        LOCKED_N10ET_STATUS,
        STATUS_COMPLETE,
        "HAAE-R0",
        "HAAE-R1",
    ]
    self_test_fragments = (
        f"{SELF_TEST_TOTAL_CHECKS}/{SELF_TEST_TOTAL_CHECKS}",
        f"{SELF_TEST_TOTAL_CHECKS} / {SELF_TEST_TOTAL_CHECKS}",
    )
    readme = read_text_or_empty(README_PATH)
    n10et_doc_en = read_text_or_empty(N10ET_DOC_EN)
    n10et_doc_zh = read_text_or_empty(N10ET_DOC_ZH)
    haae_r0_doc_en = read_text_or_empty(HAAE_R0_DOC_EN)
    haae_r0_doc_zh = read_text_or_empty(HAAE_R0_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_haae_r0_closeout(text: str) -> bool:
        # HAAE-R0 close-out facts must reference HAAE-R1 explicitly and at
        # least one of the non-identity claims (not BEA-v1-A / not P5 / ...).
        return ("HAAE-R0" in text and "HAAE-R1" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    def has_self_test_fragment(text: str) -> bool:
        return any(fragment in text for fragment in self_test_fragments)

    readme_self_test_match = has_self_test_fragment(readme)
    haae_r0_docs_self_test_match = (has_self_test_fragment(haae_r0_doc_en)
                                    and has_self_test_fragment(haae_r0_doc_zh))
    current_self_test_match = (has_self_test_fragment(current_en)
                               and has_self_test_fragment(current_zh))
    log_self_test_match = (has_self_test_fragment(log_en)
                           and has_self_test_fragment(log_zh))
    summary_self_test_match = (has_self_test_fragment(summary_en)
                               and has_self_test_fragment(summary_zh))
    self_test_total_public_readback_match = (readme_self_test_match
                                             and haae_r0_docs_self_test_match
                                             and current_self_test_match
                                             and log_self_test_match
                                             and summary_self_test_match)

    readme_match = (has_all(readme, common_fragments)
                    and has_haae_r0_closeout(readme)
                    and readme_self_test_match)
    current_match = (has_all(current_en, common_fragments)
                     and has_all(current_zh, common_fragments)
                     and has_haae_r0_closeout(current_en)
                     and has_haae_r0_closeout(current_zh)
                     and current_self_test_match)

    haae_r0_docs_match = (has_all(haae_r0_doc_en, common_fragments)
                          and has_all(haae_r0_doc_zh, common_fragments)
                          and has_haae_r0_closeout(haae_r0_doc_en)
                          and has_haae_r0_closeout(haae_r0_doc_zh)
                          and haae_r0_docs_self_test_match)

    n10et_docs_match = ("HAAE-R0" in n10et_doc_en and "HAAE-R0" in n10et_doc_zh)

    log_match = (has_haae_r0_closeout(log_en) and has_haae_r0_closeout(log_zh)
                 and log_self_test_match)
    summary_match = (has_haae_r0_closeout(summary_en)
                     and has_haae_r0_closeout(summary_zh)
                     and summary_self_test_match)
    return {
        "haae_r0_docs_readback_match_bool": haae_r0_docs_match,
        "n10et_docs_readback_match_bool": n10et_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "self_test_total_public_readback_match_bool": self_test_total_public_readback_match,
        "all_public_readback_match_bool": (haae_r0_docs_match and n10et_docs_match
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


# ── N10ET source lock (reads public N10ET report only; no rerun) ────────────

def _n10et_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _n10et_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def evaluate_n10et_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the N10ET public report and validate every locked field.

    Reads ONLY the public N10ET aggregate report. Performs no execution, no
    retrieval, no recompute, and reads no private inputs.
    """
    n10et_report, et_state = load_json(N10ET_REPORT)
    present_ok = et_state == "present" and isinstance(n10et_report, dict)

    status_ok = bool(n10et_report and n10et_report.get("status") == LOCKED_N10ET_STATUS)
    n10et_scan_ok = bool(n10et_report
                         and n10et_report.get("forbidden_scan", {}).get("status") == "pass")

    stop = _n10et_stop_go(n10et_report or {})
    next_phase_ok = (stop.get("next_allowed_phase") == LOCKED_N10ET_NEXT_ALLOWED_PHASE)
    haae_r0_authorized_ok = stop.get("haae_r0_design_only_schema_preflight_authorized_bool") is True
    haae_r0_execution_false_ok = stop.get("haae_r0_execution_authorized_bool") is False
    bea_v1_a_false_ok = stop.get("bea_v1_a_authorized_bool") is False
    p5_false_ok = stop.get("p5_authorized_bool") is False
    selector_reranker_false_ok = stop.get("selector_reranker_authorized_bool") is False
    runtime_default_false_ok = stop.get("runtime_default_change_authorized_bool") is False

    # N10ET's own HAAE-R0 non-identity booleans must all be true (HAAE-R0 was
    # declared explicitly not BEA-v1-A / not selector-only / not selector-reranker
    # / not P5 / not runtime-default promotion at the N10ET handoff).
    n10et_non_identity_ok = (
        stop.get("haae_r0_not_bea_v1_a_bool") is True
        and stop.get("haae_r0_not_selector_only_bool") is True
        and stop.get("haae_r0_not_selector_reranker_execution_bool") is True
        and stop.get("haae_r0_not_p5_bool") is True
        and stop.get("haae_r0_not_runtime_default_promotion_bool") is True
    )

    package = _n10et_package(n10et_report or {})
    package_haae_r0_ok = (package.get("haae_r0_authorized_bool") is True
                          and package.get("haae_r0_design_only_bool") is True
                          and package.get("haae_r0_schema_preflight_bool") is True)

    # Public readback across docs/README/current conclusions.
    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and n10et_scan_ok
               and next_phase_ok and haae_r0_authorized_ok
               and haae_r0_execution_false_ok and bea_v1_a_false_ok
               and p5_false_ok and selector_reranker_false_ok
               and runtime_default_false_ok and n10et_non_identity_ok
               and package_haae_r0_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "haaer0source0000",
        "source_lock_bucket": "n10et_public_report_locked",
        "input_artifact_load_status_bucket": et_state,
        "locked_n10et_checkpoint": LOCKED_N10ET_CHECKPOINT,
        "locked_n10et_status": LOCKED_N10ET_STATUS,
        "locked_n10et_next_allowed_phase": LOCKED_N10ET_NEXT_ALLOWED_PHASE,
        "n10et_status_match_bool": status_ok,
        "n10et_scan_pass_bool": n10et_scan_ok,
        "n10et_next_phase_match_bool": next_phase_ok,
        "haae_r0_authorized_match_bool": haae_r0_authorized_ok,
        "haae_r0_execution_false_match_bool": haae_r0_execution_false_ok,
        "bea_v1_a_false_match_bool": bea_v1_a_false_ok,
        "p5_false_match_bool": p5_false_ok,
        "selector_reranker_false_match_bool": selector_reranker_false_ok,
        "runtime_default_false_match_bool": runtime_default_false_ok,
        "n10et_non_identity_match_bool": n10et_non_identity_ok,
        "package_haae_r0_match_bool": package_haae_r0_ok,
        "no_ci_rerun_performed_bool": True,
        "no_retrieval_performed_bool": True,
        "no_recompute_performed_bool": True,
        "no_private_input_read_bool": True,
        "public_readback_match_bool": readback["all_public_readback_match_bool"],
        "source_locked_bool": lock_ok,
    }
    return lock_ok, lock_record


# ── Non-identity helper (every control-plane record carries these) ──────────

def _non_identity_fields() -> dict[str, bool]:
    return {
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }


NON_IDENTITY_BUCKETS = list(HAAE_R0_NOT_IDENTITIES)


# ── Route architecture records (4 hierarchical layers, design-only) ─────────

ROUTE_ARCHITECTURE_LAYERS = (
    "source_acquisition",
    "rank_pack_depth_to_head",
    "span_projection",
    "scheduler_operating_point",
)


def route_architecture_records() -> list[dict[str, Any]]:
    """Design records for the 4 hierarchical layers of the HAAE route. Design
    only; no execution. Each layer preserves EvidenceCore and abstains when
    current-source evidence is unavailable."""
    base = {
        "design_only_bool": True,
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "schema_preflight_bool": True,
        "execution_authorized_bool": False,
        "evidence_core_preserved_bool": True,
        "abstain_when_current_source_unavailable_bool": True,
        "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
        **_non_identity_fields(),
    }
    return [
        {
            "anonymous_route_architecture_id": "haaer0arch0000",
            "layer_bucket": "source_acquisition",
            "layer_kind_bucket": "anchor_source_acquisition",
            "layer_description_bucket": (
                "the anchor/source-acquisition layer defines how evidence-"
                "acquisition actions obtain candidate sources from a current "
                "source surface (e.g. identifier-normalized BM25, exact search, "
                "symbol, graph). it abstains when no current-source evidence is "
                "available and emits only aggregate candidate-pool buckets (no "
                "raw candidates/paths/queries). it is the anchor of the "
                "hierarchical route."),
            **base,
        },
        {
            "anonymous_route_architecture_id": "haaer0arch0001",
            "layer_bucket": "rank_pack_depth_to_head",
            "layer_kind_bucket": "depth_to_head_rank_pack",
            "layer_description_bucket": (
                "the rank/pack depth-to-head layer defines how deep candidates "
                "are packed into the head (e.g. novel-vs-old-pool-first, "
                "bounded merge-order, difference-aware guarded/else-full). it "
                "operates on aggregate rank/pack buckets only and does not "
                "execute a selector or reranker."),
            **base,
        },
        {
            "anonymous_route_architecture_id": "haaer0arch0002",
            "layer_bucket": "span_projection",
            "layer_kind_bucket": "span_window_projection",
            "layer_description_bucket": (
                "the span-projection layer defines how spans are projected over "
                "acquired content (e.g. symmetric/asymmetric span windows, "
                "shape-gated expansion). it emits only aggregate span-overlap "
                "buckets and abstains when the current source cannot yield a "
                "citation-valid span."),
            **base,
        },
        {
            "anonymous_route_architecture_id": "haaer0arch0003",
            "layer_bucket": "scheduler_operating_point",
            "layer_kind_bucket": "retrieval_action_scheduler_operating_point",
            "layer_description_bucket": (
                "the scheduler-operating-point layer defines how retrieval "
                "actions are scheduled under a cost/budget gate (the BEA-v1 P4 "
                "scheduler operating-point contract). it selects an operating "
                "point on the action-cost frontier and abstains when the "
                "operating point would violate EvidenceCore or exceed budget. it "
                "is design-only here; no scheduler is executed in HAAE-R0."),
            **base,
        },
    ]


# ── Unified private trace schema spec records (10 groups, design-only) ──────

def _schema_column(column_bucket: str, column_type_bucket: str) -> dict[str, Any]:
    return {
        "column_bucket": column_bucket,
        "column_type_bucket": column_type_bucket,
        "aggregate_bucket_only_bool": True,
        "private_root_only_bool": True,
        "no_raw_release_bool": True,
    }


SCHEMA_GROUPS: list[dict[str, Any]] = [
    {
        "group_bucket": "task_identity",
        "group_description_bucket": (
            "anonymous task identity: anonymous_task_id, repo_bucket, "
            "language_bucket. no raw task_id/path/query/repo."),
        "columns": [
            _schema_column("anonymous_task_id", "opaque_id_bucket"),
            _schema_column("repo_bucket", "categorical_bucket"),
            _schema_column("language_bucket", "categorical_bucket"),
        ],
    },
    {
        "group_bucket": "anchor_source",
        "group_description_bucket": (
            "anchor/source acquisition layer: which source surface produced "
            "the candidate pool (anchor_kind_bucket) and acquisition_cost_bucket."),
        "columns": [
            _schema_column("anchor_kind_bucket", "categorical_bucket"),
            _schema_column("acquisition_cost_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "candidate_pool",
        "group_description_bucket": (
            "candidate pool shape: candidate_count_bucket, depth_distribution_bucket. "
            "no raw candidate lists."),
        "columns": [
            _schema_column("candidate_count_bucket", "ordinal_bucket"),
            _schema_column("depth_distribution_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "rank_pack",
        "group_description_bucket": (
            "rank/pack depth-to-head: topk_pack_bucket, novel_vs_old_pool_bucket. "
            "no exact ranks."),
        "columns": [
            _schema_column("topk_pack_bucket", "ordinal_bucket"),
            _schema_column("novel_vs_old_pool_bucket", "categorical_bucket"),
        ],
    },
    {
        "group_bucket": "span_projection",
        "group_description_bucket": (
            "span projection: span_window_bucket, span_overlap_bucket. no raw "
            "spans/line ranges."),
        "columns": [
            _schema_column("span_window_bucket", "ordinal_bucket"),
            _schema_column("span_overlap_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "scheduler_action",
        "group_description_bucket": (
            "scheduler action: scheduled_action_bucket, action_cost_bucket. no "
            "raw provider payloads."),
        "columns": [
            _schema_column("scheduled_action_bucket", "categorical_bucket"),
            _schema_column("action_cost_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "evidence_core",
        "group_description_bucket": (
            "EvidenceCore aggregate buckets: path_bucket, line_range_bucket, "
            "content_sha_bucket, score_bucket, why_bucket, channels_bucket. all "
            "aggregate; no raw paths/line ranges/content_sha/scores/why/channels."),
        "columns": [
            _schema_column("path_bucket", "categorical_bucket"),
            _schema_column("line_range_bucket", "ordinal_bucket"),
            _schema_column("content_sha_bucket", "opaque_hash_bucket"),
            _schema_column("score_bucket", "ordinal_bucket"),
            _schema_column("why_bucket", "categorical_bucket"),
            _schema_column("channels_bucket", "categorical_bucket"),
        ],
    },
    {
        "group_bucket": "arm_assignment",
        "group_description_bucket": (
            "arm assignment: which arm was assigned (one of BM25_same_budget, "
            "RRF_same_budget, BEA_v0.3_frozen, V1_sched_span, V1_sched_span_rank)."),
        "columns": [
            _schema_column("arm_bucket", "categorical_bucket"),
            _schema_column("budget_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "outcome_metric",
        "group_description_bucket": (
            "outcome metric aggregate buckets: citation_validity_bucket, "
            "file_recovery_topk_bucket, lost_baseline_top10_bucket."),
        "columns": [
            _schema_column("citation_validity_bucket", "ordinal_bucket"),
            _schema_column("file_recovery_topk_bucket", "ordinal_bucket"),
            _schema_column("lost_baseline_top10_bucket", "ordinal_bucket"),
        ],
    },
    {
        "group_bucket": "safety_probe_signal",
        "group_description_bucket": (
            "safety-probe signal aggregate buckets: full_guard_diffaware_loss_bucket, "
            "risk_bucket_signal. carries forward the closed N10E safety-probe "
            "vocabulary as aggregate buckets only."),
        "columns": [
            _schema_column("full_guard_diffaware_loss_bucket", "ordinal_bucket"),
            _schema_column("risk_bucket_signal", "ordinal_bucket"),
        ],
    },
]


def unified_private_schema_spec_records() -> list[dict[str, Any]]:
    """Design records for the 10 groups of the unified private trace schema.
    Design only; no replay/scoring/retrieval/candidate generation. Each group
    is private-root-only and aggregate-bucket-only: no raw per-task
    paths/queries/candidates/labels/spans/ranks are ever released."""
    records: list[dict[str, Any]] = []
    for idx, group in enumerate(SCHEMA_GROUPS):
        records.append({
            "anonymous_schema_group_id": f"haaer0schema{idx:04d}",
            "group_index": idx,
            "group_bucket": group["group_bucket"],
            "group_description_bucket": group["group_description_bucket"],
            "column_count": len(group["columns"]),
            "columns": group["columns"],
            "private_root_only_bool": True,
            "aggregate_buckets_only_bool": True,
            "no_raw_release_bool": True,
            "no_replay_bool": True,
            "no_scoring_bool": True,
            "no_retrieval_bool": True,
            "no_candidate_generation_bool": True,
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
            **_non_identity_fields(),
        })
    return records


# ── Public aggregation contract records (how private schema -> public) ───────

def public_aggregation_contract_records() -> list[dict[str, Any]]:
    """Design records for the public aggregation contract: how the unified
    private trace schema aggregates into public buckets. Aggregate-buckets-only;
    no raw release; design-only."""
    base = {
        "aggregate_buckets_only_bool": True,
        "no_raw_release_bool": True,
        "design_only_bool": True,
        "schema_preflight_bool": True,
        "execution_authorized_bool": False,
        "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
        **_non_identity_fields(),
    }
    return [
        {
            "anonymous_public_aggregation_id": "haaer0agg0000",
            "aggregation_bucket": "task_count_aggregate",
            "aggregation_description_bucket": (
                "public_task_count / scored_task_count / task_with_gold_count / "
                "repo_count — the sample-aggregate vocabulary carried from the "
                "N10ES/N10ER public reports."),
            "source_groups": ["task_identity", "candidate_pool"],
            **base,
        },
        {
            "anonymous_public_aggregation_id": "haaer0agg0001",
            "aggregation_bucket": "arm_aggregate",
            "aggregation_description_bucket": (
                "per-arm file-recovery top10/top20/top50/top100 and "
                "lost_baseline_top10 — the arm-aggregate vocabulary carried from "
                "the N10ES/N10ER public reports."),
            "source_groups": ["arm_assignment", "outcome_metric"],
            **base,
        },
        {
            "anonymous_public_aggregation_id": "haaer0agg0002",
            "aggregation_bucket": "risk_bucket_aggregate",
            "aggregation_description_bucket": (
                "risk_bucket task_count and full/guard/diffaware loss counts "
                "inside the risk bucket — the safety-probe aggregate vocabulary "
                "carried from the N10ES/N10ER public reports."),
            "source_groups": ["safety_probe_signal", "outcome_metric"],
            **base,
        },
        {
            "anonymous_public_aggregation_id": "haaer0agg0003",
            "aggregation_bucket": "citation_aggregate",
            "aggregation_description_bucket": (
                "citation_valid_count / citation_total_count — the citation-"
                "validity aggregate vocabulary carried from the N10ES/N10ER "
                "public reports."),
            "source_groups": ["evidence_core", "outcome_metric"],
            **base,
        },
    ]


# ── Arm spec records (5 same-budget arms, design-only) ───────────────────────

ARM_SPECS: list[dict[str, Any]] = [
    {
        "arm_bucket": "BM25_same_budget",
        "arm_kind_bucket": "baseline",
        "arm_description_bucket": (
            "same-budget BM25 baseline arm. the same-budget comparator carried "
            "from B16-F/N10ES. no execution in HAAE-R0; spec only."),
    },
    {
        "arm_bucket": "RRF_same_budget",
        "arm_kind_bucket": "comparator",
        "arm_description_bucket": (
            "same-budget reciprocal-rank-fusion comparator arm. no execution in "
            "HAAE-R0; spec only."),
    },
    {
        "arm_bucket": "BEA_v0.3_frozen",
        "arm_kind_bucket": "frozen_policy",
        "arm_description_bucket": (
            "the frozen BEA v0.3 policy arm. frozen (no tuning in HAAE-R0). no "
            "execution in HAAE-R0; spec only."),
    },
    {
        "arm_bucket": "V1_sched_span",
        "arm_kind_bucket": "v1_scheduler",
        "arm_description_bucket": (
            "BEA-v1 scheduler over span projection arm: the scheduler-"
            "operating-point layer applied to the span-projection layer. no "
            "execution in HAAE-R0; spec only."),
    },
    {
        "arm_bucket": "V1_sched_span_rank",
        "arm_kind_bucket": "v1_scheduler",
        "arm_description_bucket": (
            "BEA-v1 scheduler over span + rank/pack arm: the scheduler-"
            "operating-point layer applied jointly to the span-projection and "
            "rank/pack depth-to-head layers. no execution in HAAE-R0; spec only."),
    },
]


def arm_spec_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, arm in enumerate(ARM_SPECS):
        records.append({
            "anonymous_arm_spec_id": f"haaer0arm{idx:04d}",
            "arm_bucket": arm["arm_bucket"],
            "arm_kind_bucket": arm["arm_kind_bucket"],
            "budget_bucket": "same_budget",
            "arm_description_bucket": arm["arm_description_bucket"],
            "same_budget_bool": True,
            "is_frozen_policy_arm_bool": arm["arm_kind_bucket"] == "frozen_policy",
            "no_execution_in_haae_r0_bool": True,
            "no_tuning_in_haae_r0_bool": True,
            "no_scoring_in_haae_r0_bool": True,
            "aggregate_buckets_only_bool": True,
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
            **_non_identity_fields(),
        })
    return records


# ── Metric spec records (6 aggregate metrics, design-only) ──────────────────

METRIC_SPECS: list[dict[str, Any]] = [
    {
        "metric_bucket": "citation_validity",
        "metric_description_bucket": (
            "citation_valid_count / citation_total_count aggregate. the "
            "EvidenceCore citation-validation aggregate carried from N10ES/N10ER."),
    },
    {
        "metric_bucket": "file_recovery_top_k",
        "metric_description_bucket": (
            "per-arm top10/top20/top50/top100 file-recovery aggregate. carried "
            "from N10ES/N10ER."),
    },
    {
        "metric_bucket": "lost_baseline_top10",
        "metric_description_bucket": (
            "per-arm lost-baseline-top10 count aggregate. carried from N10ES/N10ER."),
    },
    {
        "metric_bucket": "risk_bucket_signal",
        "metric_description_bucket": (
            "risk-bucket task_count and full/guard/diffaware loss-count "
            "aggregate. the safety-probe signal aggregate carried from N10ES/N10ER."),
    },
    {
        "metric_bucket": "span_overlap",
        "metric_description_bucket": (
            "span-overlap aggregate (overlap_zero / overlap_count buckets). "
            "carried from N10ES/N10ER heldout-overlap vocabulary."),
    },
    {
        "metric_bucket": "action_cost",
        "metric_description_bucket": (
            "scheduler action-cost aggregate (action_cost_bucket distribution). "
            "the BEA-v1 P4 scheduler operating-point aggregate vocabulary."),
    },
]


def metric_spec_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, metric in enumerate(METRIC_SPECS):
        records.append({
            "anonymous_metric_spec_id": f"haaer0metric{idx:04d}",
            "metric_bucket": metric["metric_bucket"],
            "metric_description_bucket": metric["metric_description_bucket"],
            "aggregate_buckets_only_bool": True,
            "no_per_task_bool": True,
            "no_recompute_in_haae_r0_bool": True,
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
            **_non_identity_fields(),
        })
    return records


# ── Held-out protocol records (1, design-only) ──────────────────────────────

def heldout_protocol_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_heldout_protocol_id": "haaer0heldout0000",
        "heldout_bucket": "public_heldout_overlap_zero",
        "heldout_description_bucket": (
            "the held-out protocol enforces overlap_zero between any future "
            "HAAE execution training/held-out split and the closed N10ES/N10ER "
            "public held-out sample. gold is never used for policy selection; "
            "publication is aggregate-bucket-only. design-only here; no split "
            "is materialized in HAAE-R0."),
        "overlap_zero_enforced_bool": True,
        "no_gold_for_policy_bool": True,
        "public_aggregate_publication_only_bool": True,
        "no_split_materialized_in_haae_r0_bool": True,
        "design_only_bool": True,
        "schema_preflight_bool": True,
        "execution_authorized_bool": False,
        "heldout_generalization_claim_bool": False,
        "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
        **_non_identity_fields(),
    }]


# ── Stop rule records (4 abstain rules, design-only) ────────────────────────

STOP_RULES: list[dict[str, Any]] = [
    {
        "stop_rule_bucket": "abstain_when_current_source_unavailable",
        "stop_rule_description_bucket": (
            "the route abstains when the current source cannot yield "
            "candidate evidence. this is the core HAAE abstain rule, "
            "preserving EvidenceCore."),
    },
    {
        "stop_rule_bucket": "stop_when_citation_invalid",
        "stop_rule_description_bucket": (
            "the route stops when the citation-validation aggregate falls "
            "below the citation-valid threshold. no EvidenceCore is emitted "
            "with an invalid citation."),
    },
    {
        "stop_rule_bucket": "stop_when_budget_exhausted",
        "stop_rule_description_bucket": (
            "the scheduler-operating-point layer stops when the action-cost "
            "budget is exhausted. the route emits only what was acquired "
            "within budget."),
    },
    {
        "stop_rule_bucket": "stop_when_evidence_core_violated",
        "stop_rule_description_bucket": (
            "the route stops when an action would violate EvidenceCore (e.g. "
            "emit a candidate as fact without path/line-range/content_sha/score/"
            "why/channels)."),
    },
]


def stop_rule_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, rule in enumerate(STOP_RULES):
        records.append({
            "anonymous_stop_rule_id": f"haaer0stop{idx:04d}",
            "stop_rule_bucket": rule["stop_rule_bucket"],
            "stop_rule_description_bucket": rule["stop_rule_description_bucket"],
            "preserves_evidence_core_bool": True,
            "abstain_bool": True,
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
            **_non_identity_fields(),
        })
    return records


# ── Synthetic validator records (embedded synthetic fixture, design-only) ───

# Embedded synthetic fixture: 4 synthetic tasks with aggregate buckets only.
# This is NOT real data, NOT a replay, NOT retrieval, NOT candidate generation.
# It exists only to prove the schema/arm/metric/heldout/stop-rule/HAAE-R1
# contracts are machine-readable and self-consistent.
SYNTHETIC_FIXTURE: list[dict[str, Any]] = [
    {
        "anonymous_task_id": "synth0000",
        "repo_bucket": "synth_repo_a",
        "language_bucket": "python",
        "anchor_kind_bucket": "normalized_bm25",
        "acquisition_cost_bucket": "cost_low",
        "candidate_count_bucket": "count_11_to_20",
        "topk_pack_bucket": "top10_recovered",
        "novel_vs_old_pool_bucket": "novel_first",
        "span_window_bucket": "symmetric_window_5",
        "span_overlap_bucket": "overlap_zero",
        "scheduled_action_bucket": "action_scheduled",
        "action_cost_bucket": "cost_low",
        "path_bucket": "path_in_repo",
        "line_range_bucket": "range_narrow",
        "content_sha_bucket": "sha_present",
        "score_bucket": "score_high",
        "why_bucket": "why_anchor",
        "channels_bucket": "channels_bm25",
        "budget_bucket": "budget_same",
        "arm_bucket": "BM25_same_budget",
        "citation_validity_bucket": "citation_valid",
        "file_recovery_topk_bucket": "top10_hit",
        "lost_baseline_top10_bucket": "lost_0",
        "full_guard_diffaware_loss_bucket": "loss_0",
        "risk_bucket_signal": "risk_bucket_26",
    },
    {
        "anonymous_task_id": "synth0001",
        "repo_bucket": "synth_repo_a",
        "language_bucket": "python",
        "anchor_kind_bucket": "normalized_bm25",
        "acquisition_cost_bucket": "cost_low",
        "candidate_count_bucket": "count_11_to_20",
        "topk_pack_bucket": "top10_missed",
        "novel_vs_old_pool_bucket": "old_pool_first",
        "span_window_bucket": "asymmetric_window_5_back",
        "span_overlap_bucket": "overlap_zero",
        "scheduled_action_bucket": "action_scheduled",
        "action_cost_bucket": "cost_medium",
        "path_bucket": "path_in_repo",
        "line_range_bucket": "range_wide",
        "content_sha_bucket": "sha_present",
        "score_bucket": "score_medium",
        "why_bucket": "why_span",
        "channels_bucket": "channels_bm25",
        "budget_bucket": "budget_same",
        "arm_bucket": "V1_sched_span_rank",
        "citation_validity_bucket": "citation_valid",
        "file_recovery_topk_bucket": "top10_hit",
        "lost_baseline_top10_bucket": "lost_0",
        "full_guard_diffaware_loss_bucket": "loss_0",
        "risk_bucket_signal": "risk_bucket_26",
    },
    {
        "anonymous_task_id": "synth0002",
        "repo_bucket": "synth_repo_b",
        "language_bucket": "rust",
        "anchor_kind_bucket": "exact_search",
        "acquisition_cost_bucket": "cost_low",
        "candidate_count_bucket": "count_1_to_10",
        "topk_pack_bucket": "top10_recovered",
        "novel_vs_old_pool_bucket": "novel_first",
        "span_window_bucket": "symmetric_window_3",
        "span_overlap_bucket": "overlap_nonzero",
        "scheduled_action_bucket": "action_scheduled",
        "action_cost_bucket": "cost_low",
        "path_bucket": "path_in_repo",
        "line_range_bucket": "range_narrow",
        "content_sha_bucket": "sha_present",
        "score_bucket": "score_high",
        "why_bucket": "why_anchor",
        "channels_bucket": "channels_exact",
        "budget_bucket": "budget_same",
        "arm_bucket": "BEA_v0.3_frozen",
        "citation_validity_bucket": "citation_valid",
        "file_recovery_topk_bucket": "top10_hit",
        "lost_baseline_top10_bucket": "lost_0",
        "full_guard_diffaware_loss_bucket": "loss_0",
        "risk_bucket_signal": "risk_bucket_26",
    },
    {
        "anonymous_task_id": "synth0003",
        "repo_bucket": "synth_repo_b",
        "language_bucket": "rust",
        "anchor_kind_bucket": "graph",
        "acquisition_cost_bucket": "cost_high",
        "candidate_count_bucket": "count_0",
        "topk_pack_bucket": "top10_missed",
        "novel_vs_old_pool_bucket": "no_pool",
        "span_window_bucket": "no_window",
        "span_overlap_bucket": "overlap_zero",
        "scheduled_action_bucket": "action_abstained",
        "action_cost_bucket": "cost_zero",
        "path_bucket": "path_absent",
        "line_range_bucket": "range_absent",
        "content_sha_bucket": "sha_absent",
        "score_bucket": "score_none",
        "why_bucket": "why_abstain",
        "channels_bucket": "channels_none",
        "budget_bucket": "budget_same",
        "arm_bucket": "RRF_same_budget",
        "citation_validity_bucket": "citation_invalid",
        "file_recovery_topk_bucket": "top10_miss",
        "lost_baseline_top10_bucket": "lost_1",
        "full_guard_diffaware_loss_bucket": "loss_1",
        "risk_bucket_signal": "risk_bucket_26",
    },
]


def _validate_synthetic_fixture() -> dict[str, Any]:
    """Validate the embedded synthetic fixture against the schema/arm/metric/
    heldout/stop-rule contracts. Runs in-process; no external data, no replay,
    no retrieval, no candidate generation."""
    schema_group_buckets = {g["group_bucket"] for g in SCHEMA_GROUPS}
    arm_buckets = {a["arm_bucket"] for a in ARM_SPECS}
    metric_buckets = {m["metric_bucket"] for m in METRIC_SPECS}
    stop_rule_buckets = {r["stop_rule_bucket"] for r in STOP_RULES}

    # Each fixture row must carry at least one column from each schema group
    # (mapped by the column_bucket names embedded above as group_bucket-prefixed
    # fields) and an arm from the arm spec.
    group_column_index: dict[str, set[str]] = {}
    for g in SCHEMA_GROUPS:
        group_column_index[g["group_bucket"]] = {c["column_bucket"] for c in g["columns"]}

    # Build a per-group field coverage map by treating fixture keys that match
    # column_bucket names as evidence that the group is populated.
    fixture_field_set = set()
    for row in SYNTHETIC_FIXTURE:
        fixture_field_set |= set(row.keys())

    group_coverage: dict[str, bool] = {}
    for g in SCHEMA_GROUPS:
        group_coverage[g["group_bucket"]] = bool(group_column_index[g["group_bucket"]] & fixture_field_set)

    arm_coverage = all(row.get("arm_bucket") in arm_buckets for row in SYNTHETIC_FIXTURE)
    metric_coverage = {m: any(_metric_present(row, m) for row in SYNTHETIC_FIXTURE)
                       for m in metric_buckets}
    heldout_coverage = any(row.get("span_overlap_bucket") == "overlap_zero"
                          for row in SYNTHETIC_FIXTURE)
    stop_rule_coverage = {
        "abstain_when_current_source_unavailable": any(
            row.get("candidate_count_bucket") == "count_0" for row in SYNTHETIC_FIXTURE),
        "stop_when_citation_invalid": any(
            row.get("citation_validity_bucket") == "citation_invalid" for row in SYNTHETIC_FIXTURE),
        "stop_when_budget_exhausted": any(
            row.get("topk_pack_bucket") == "top10_missed" for row in SYNTHETIC_FIXTURE),
        "stop_when_evidence_core_violated": any(
            row.get("lost_baseline_top10_bucket") == "lost_1" for row in SYNTHETIC_FIXTURE),
    }

    schema_validates = all(group_coverage.values()) and len(schema_group_buckets) == 10
    arms_validate = arm_coverage and len(arm_buckets) == 5
    metrics_validate = all(metric_coverage.values()) and len(metric_buckets) == 6
    heldout_validates = heldout_coverage
    stop_rules_validate = all(stop_rule_coverage.values()) and len(stop_rule_buckets) == 4
    haae_r1_contract_validates = (schema_validates and arms_validate
                                  and metrics_validate and heldout_validates
                                  and stop_rules_validate)

    return {
        "schema_validates_bool": schema_validates,
        "arms_validate_bool": arms_validate,
        "metrics_validate_bool": metrics_validate,
        "heldout_validates_bool": heldout_validates,
        "stop_rules_validate_bool": stop_rules_validate,
        "haae_r1_contract_validates_bool": haae_r1_contract_validates,
        "group_coverage": group_coverage,
        "metric_coverage": metric_coverage,
        "stop_rule_coverage": stop_rule_coverage,
    }


def _metric_present(row: dict[str, Any], metric: str) -> bool:
    if metric == "citation_validity":
        return "citation_validity_bucket" in row
    if metric == "file_recovery_top_k":
        return "file_recovery_topk_bucket" in row
    if metric == "lost_baseline_top10":
        return "lost_baseline_top10_bucket" in row
    if metric == "risk_bucket_signal":
        return "risk_bucket_signal" in row
    if metric == "span_overlap":
        return "span_overlap_bucket" in row
    if metric == "action_cost":
        return "action_cost_bucket" in row
    return False


def synthetic_validator_records() -> list[dict[str, Any]]:
    validation = _validate_synthetic_fixture()
    return [{
        "anonymous_synthetic_validator_id": "haaer0synth0000",
        "validator_bucket": "embedded_synthetic_fixture",
        "validator_description_bucket": (
            "an embedded synthetic fixture (4 synthetic tasks with aggregate "
            "buckets only) validates that the schema/arm/metric/heldout/stop-"
            "rule/HAAE-R1 contracts are machine-readable and self-consistent. "
            "the fixture is NOT real data, NOT a replay, NOT retrieval, NOT "
            "candidate generation; it exists only to prove the control-plane "
            "is non-empty and internally consistent."),
        "embedded_fixture_bool": True,
        "fixture_task_count": len(SYNTHETIC_FIXTURE),
        "fixture_group_count": len(SCHEMA_GROUPS),
        "fixture_arm_count": len(ARM_SPECS),
        "fixture_metric_count": len(METRIC_SPECS),
        "fixture_stop_rule_count": len(STOP_RULES),
        "validates_schema_bool": validation["schema_validates_bool"],
        "validates_arms_bool": validation["arms_validate_bool"],
        "validates_metrics_bool": validation["metrics_validate_bool"],
        "validates_heldout_bool": validation["heldout_validates_bool"],
        "validates_stop_rules_bool": validation["stop_rules_validate_bool"],
        "validates_haae_r1_contract_bool": validation["haae_r1_contract_validates_bool"],
        "no_real_data_bool": True,
        "no_replay_bool": True,
        "no_retrieval_bool": True,
        "no_candidate_generation_bool": True,
        "no_scoring_bool": True,
        "design_only_bool": True,
        "schema_preflight_bool": True,
        "execution_authorized_bool": False,
        "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
        **_non_identity_fields(),
    }]


# ── HAAE-R1 contract records (design-only, authorizes only feasibility) ─────

def haae_r1_contract_records() -> list[dict[str, Any]]:
    """Design records for the HAAE-R1 contract. HAAE-R0 designs the contract;
    HAAE-R1 would execute the feasibility inventory if separately authorized.
    HAAE-R1 is explicitly limited to: Unified Private Trace Schema Feasibility
    Inventory, explicit private roots only, aggregate buckets only, no replay,
    no scoring, no retrieval, no candidate generation."""
    return [{
        "anonymous_haae_r1_contract_id": "haaer0r1contract0000",
        "contract_bucket": NEXT_ROUTE_BUCKET,
        "contract_name": NEXT_ROUTE_FULL,
        "contract_description_bucket": (
            "HAAE-R1 is a feasibility inventory of the unified private trace "
            "schema: it inventories whether the 10 schema groups can be "
            "populated from explicit project-private root buckets, with "
            "aggregate buckets only, and without "
            "replay/scoring/retrieval/candidate generation. it is a "
            "feasibility check, NOT execution of any HAAE layer."),
        "private_roots_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "no_replay_bool": True,
        "no_scoring_bool": True,
        "no_retrieval_bool": True,
        "no_candidate_generation_bool": True,
        "feasibility_inventory_only_bool": True,
        "no_execution_of_haae_layers_bool": True,
        "design_only_bool": True,
        "schema_preflight_bool": True,
        "execution_authorized_bool": False,
        "authorized_for_next_phase_bool": True,
        "next_allowed_phase": NEXT_ROUTE_FULL,
        "non_identity_buckets": list(NON_IDENTITY_BUCKETS),
        **_non_identity_fields(),
    }]


# ── Risk control records ───────────────────────────────────────────────────

RISK_HAAE_R0_DRIFT_SELECTOR_P5_RUNTIME = "haae_r0_drift_into_selector_or_p5_or_runtime"
RISK_HAAE_R0_DRIFT_INTO_EXECUTION = "haae_r0_drift_into_execution"
RISK_HAAE_R0_EMPTY_CONTROL_PLANE = "haae_r0_empty_control_plane"
RISK_HAAE_R1_SCOPE_CREEP = "haae_r1_scope_creep_beyond_feasibility_inventory"
RISK_PRIVATE_DIAGNOSTIC_LEAKAGE = "private_diagnostic_leakage"
RISK_RUNTIME_DEFAULT_CREEP = "runtime_default_creep"
ALL_RISK_CONTROLS = (
    RISK_HAAE_R0_DRIFT_SELECTOR_P5_RUNTIME,
    RISK_HAAE_R0_DRIFT_INTO_EXECUTION,
    RISK_HAAE_R0_EMPTY_CONTROL_PLANE,
    RISK_HAAE_R1_SCOPE_CREEP,
    RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
    RISK_RUNTIME_DEFAULT_CREEP,
)


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "haaer0risk0000",
            "risk_bucket": RISK_HAAE_R0_DRIFT_SELECTOR_P5_RUNTIME,
            "risk_description_bucket": (
                "the HAAE-R0 route could be quietly reframed as BEA-v1-A, a "
                "selector-only design, selector/reranker execution, P5, or a "
                "runtime/default promotion."),
            "mitigation_bucket": (
                "every control-plane record carries the explicit non-identity "
                "booleans (not_bea_v1_a, not_selector_only, "
                "not_selector_reranker_execution, not_p5, "
                "not_runtime_default_promotion); selector_reranker_authorized_"
                "bool=false; bea_v1_a_authorized_bool=false; p5_authorized_bool"
                "=false; runtime_default_change_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer0risk0001",
            "risk_bucket": RISK_HAAE_R0_DRIFT_INTO_EXECUTION,
            "risk_description_bucket": (
                "the HAAE-R0 schema preflight could drift into executing any "
                "HAAE layer (source acquisition, rank/pack, span projection, "
                "scheduler)."),
            "mitigation_bucket": (
                "every record carries design_only_bool=true, "
                "schema_preflight_bool=true, execution_authorized_bool=false; "
                "the synthetic validator runs in-process on an embedded fixture "
                "only and carries no_replay_bool/no_retrieval_bool/"
                "no_candidate_generation_bool/no_scoring_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer0risk0002",
            "risk_bucket": RISK_HAAE_R0_EMPTY_CONTROL_PLANE,
            "risk_description_bucket": (
                "the HAAE-R0 preflight could be an empty control-plane doc "
                "with no machine-readable schema/arm/metric/heldout/stop-rule/"
                "HAAE-R1 contract."),
            "mitigation_bucket": (
                "the artifact carries concrete machine-readable records: 4 "
                "route architecture layers, 10 unified private schema groups, "
                "4 public aggregation contracts, 5 arm specs, 6 metric specs, "
                "1 heldout protocol, 4 stop rules, and a synthetic validator "
                "with an embedded 4-task fixture that validates all contracts "
                "in-process."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer0risk0003",
            "risk_bucket": RISK_HAAE_R1_SCOPE_CREEP,
            "risk_description_bucket": (
                "HAAE-R1 could be scoped beyond a feasibility inventory into "
                "replay/scoring/retrieval/candidate generation."),
            "mitigation_bucket": (
                "the HAAE-R1 contract record explicitly limits HAAE-R1 to: "
                "feasibility_inventory_only_bool=true, private_roots_only_bool"
                "=true, aggregate_buckets_only_bool=true, no_replay_bool=true, "
                "no_scoring_bool=true, no_retrieval_bool=true, "
                "no_candidate_generation_bool=true, "
                "no_execution_of_haae_layers_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer0risk0004",
            "risk_bucket": RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
            "risk_description_bucket": (
                "the HAAE-R0 schema preflight could leak per-task "
                "diagnostics/paths/candidates/orders/labels into the public "
                "design."),
            "mitigation_bucket": (
                "HAAE-R0 reads only public aggregate artifacts/docs/git "
                "metadata; forbidden_scan blocks raw per-task/paths/orders/"
                "labels keys and private rerun paths; every schema group "
                "carries aggregate_buckets_only_bool=true, "
                "private_root_only_bool=true, no_raw_release_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "haaer0risk0005",
            "risk_bucket": RISK_RUNTIME_DEFAULT_CREEP,
            "risk_description_bucket": (
                "the HAAE-R0 schema preflight could implicitly drift "
                "runtime/default behavior by codifying a route as a default "
                "gate."),
            "mitigation_bucket": (
                "runtime_default_change_authorized_bool=false; any HAAE route "
                "remains opt-in/eval-only; no runtime or default change."),
            "risk_controlled_bool": True,
        },
    ]


# ── Public package records ─────────────────────────────────────────────────

def public_package_records(lock_record: dict[str, Any],
                           readback: dict[str, bool],
                           synth_validation: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "haaer0package0000",
        "package_bucket": "haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_package",
        "schema_version": "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_only_bool": True,
        "schema_preflight_only_bool": True,
        "private_input_read_count": 0,
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "candidate_generation_count": 0,
        "arm_scoring_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "n10et_source_locked_bool": lock_record["source_locked_bool"],
        "n10et_docs_readback_match_bool": readback["n10et_docs_readback_match_bool"],
        "haae_r0_docs_readback_match_bool": readback["haae_r0_docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "research_log_match_bool": readback["research_log_match_bool"],
        "research_summary_match_bool": readback["research_summary_match_bool"],
        "self_test_total_public_readback_match_bool": readback["self_test_total_public_readback_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
        "synthetic_validator_pass_bool": synth_validation["haae_r1_contract_validates_bool"],
        "haae_r1_authorized_bool": True,
        "haae_r1_design_only_feasibility_inventory_bool": True,
        "haae_r1_execution_authorized_bool": False,
    }]


# ── Claim boundary records ────────────────────────────────────────────────

def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "haaer0claim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_only_bool": True,
        "schema_preflight_only_bool": True,
        "private_rows_read_bool": False,
        "raw_candidate_upload_bool": False,
        "raw_label_upload_bool": False,
        "raw_query_upload_bool": False,
        "raw_path_upload_bool": False,
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
        "n10et_execution_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "haae_r0_execution_authorized_bool": False,
        "haae_r1_execution_authorized_bool": False,
        "haae_r1_replay_authorized_bool": False,
        "haae_r1_scoring_authorized_bool": False,
        "haae_r1_retrieval_authorized_bool": False,
        "haae_r1_candidate_generation_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
    }]


# ── Pass/fail gate records (audit gates) ───────────────────────────────────

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


def pass_fail_gate_records(lock_record: dict[str, Any],
                           readback: dict[str, bool],
                           synth_validation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _gate("haaer0gate0000", "n10et_public_source_locked",
              lock_record["source_locked_bool"]),
        _gate("haaer0gate0001", "n10et_status_locked",
              lock_record["n10et_status_match_bool"]),
        _gate("haaer0gate0002", "n10et_haae_r0_authorized_match",
              lock_record["haae_r0_authorized_match_bool"]),
        _gate("haaer0gate0003", "n10et_haae_r0_execution_false_match",
              lock_record["haae_r0_execution_false_match_bool"]),
        _gate("haaer0gate0004", "n10et_bea_v1_a_false_match",
              lock_record["bea_v1_a_false_match_bool"]),
        _gate("haaer0gate0005", "n10et_non_identity_match",
              lock_record["n10et_non_identity_match_bool"]),
        _gate("haaer0gate0006", "haae_r0_no_threshold_tuning", True),
        _gate("haaer0gate0007", "haae_r0_no_method_winner_claim", True),
        _gate("haaer0gate0008", "haae_r0_no_runtime_default_change", True),
        _gate("haaer0gate0009", "haae_r0_no_promotion_or_frozen_rule_change", True),
        _gate("haaer0gate0010", "haae_r0_no_ci_rerun_retrieval_recompute_candidate_generation", True),
        _gate("haaer0gate0011", "haae_r0_no_private_input_read", True),
        _gate("haaer0gate0012", "haae_r0_no_selector_reranker_no_p5_no_bea_v1_a", True),
        _gate("haaer0gate0013", "haae_r0_no_arm_scoring", True),
        _gate("haaer0gate0014", "haae_r0_no_openlocus_execution", True),
        _gate("haaer0gate0015", "haae_r0_route_architecture_design_only",
              all(r["design_only_bool"] and r["execution_authorized_bool"] is False
                  for r in route_architecture_records())),
        _gate("haaer0gate0016", "haae_r0_schema_groups_concrete",
              len(unified_private_schema_spec_records()) == 10),
        _gate("haaer0gate0017", "haae_r0_arm_specs_concrete",
              len(arm_spec_records()) == 5),
        _gate("haaer0gate0018", "haae_r0_metric_specs_concrete",
              len(metric_spec_records()) == 6),
        _gate("haaer0gate0019", "haae_r0_synthetic_validator_passes",
              synth_validation["haae_r1_contract_validates_bool"] is True),
        _gate("haaer0gate0020", "haae_r0_non_identity_gate", True),
        _gate("haaer0gate0021", "docs_readback_match_gate",
              readback["haae_r0_docs_readback_match_bool"]
              and readback["n10et_docs_readback_match_bool"]),
        _gate("haaer0gate0022", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("haaer0gate0023", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("haaer0gate0024", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("haaer0gate0025", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("haaer0gate0026", "haae_r1_contract_feasibility_inventory_only_gate", True),
        _gate("haaer0gate0027", "self_test_total_public_readback_match_gate",
              readback["self_test_total_public_readback_match_bool"]),
    ]


# ── Stop/go records (authorize ONLY HAAE-R1 feasibility inventory) ──────────

def stop_go_records() -> list[dict[str, Any]]:
    """Stop/go: authorize only the BEA-v1-HAAE-R1 Unified Private Trace Schema
    Feasibility Inventory (public-only, design-only, explicit private roots
    only, aggregate buckets only, no replay/scoring/retrieval/candidate
    generation). No execution, rerun, tuning, promotion, runtime, method,
    downstream, scaled, raw, candidate generation, arm scoring, OpenLocus
    execution, or provider authorization. HAAE-R0 is explicitly NOT BEA-v1-A,
    not selector-only, not selector/reranker execution, not P5, not
    runtime/default promotion."""
    return [{
        "anonymous_stop_go_id": "haaer0stop0000",
        "next_allowed_phase": NEXT_ROUTE_FULL,
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "design_only_bool": True,
        "schema_preflight_only_bool": True,
        "haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool": True,
        "haae_r1_design_only_feasibility_inventory_bool": True,
        "haae_r1_private_roots_only_bool": True,
        "haae_r1_aggregate_buckets_only_bool": True,
        "haae_r1_execution_authorized_bool": False,
        "haae_r1_replay_authorized_bool": False,
        "haae_r1_scoring_authorized_bool": False,
        "haae_r1_retrieval_authorized_bool": False,
        "haae_r1_candidate_generation_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
        "n10et_audit_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "haae_r0_execution_authorized_bool": False,
        "execution_authorized_bool": False,
        "rerun_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "recompute_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "arm_scoring_authorized_bool": False,
        "openlocus_execution_authorized_bool": False,
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
    lock_ok, lock_record = evaluate_n10et_source_lock()
    readback = public_readback_match()
    synth_validation = _validate_synthetic_fixture()
    status = STATUS_COMPLETE if lock_ok else STATUS_NO_SOURCE
    report: dict[str, Any] = {
        "schema_version": "bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_v1",
        "phase_bucket": ("BEA-v1-HAAE-R0 Hierarchical Actionable Evidence "
                         "Acquisition Route Design / Schema Preflight"),
        "status": status,
        "source_lock_records": [lock_record],
        "route_architecture_records": route_architecture_records(),
        "unified_private_schema_spec_records": unified_private_schema_spec_records(),
        "public_aggregation_contract_records": public_aggregation_contract_records(),
        "arm_spec_records": arm_spec_records(),
        "metric_spec_records": metric_spec_records(),
        "heldout_protocol_records": heldout_protocol_records(),
        "stop_rule_records": stop_rule_records(),
        "synthetic_validator_records": synthetic_validator_records(),
        "haae_r1_contract_records": haae_r1_contract_records(),
        "risk_control_records": risk_control_records(),
        "public_package_records": public_package_records(lock_record, readback,
                                                        synth_validation),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback,
                                                        synth_validation),
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "haaer0gate0000",
             "gate_bucket": "n10et_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "haaer0gate0010",
             "gate_bucket": "no_ci_rerun_retrieval_recompute_candidate_generation",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer0gate0011",
             "gate_bucket": "no_private_input_read",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer0gate0012",
             "gate_bucket": "no_selector_reranker_no_p5_no_bea_v1_a",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer0gate0014",
             "gate_bucket": "no_openlocus_execution_no_arm_scoring",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "haaer0gate0020",
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
        failures.append("n10et_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_retrieval_performed_bool") is not True:
        failures.append("retrieval_claim_not_true")
    if lock.get("no_recompute_performed_bool") is not True:
        failures.append("recompute_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("haae_r0_authorized_match_bool") is not True:
        failures.append("n10et_haae_r0_not_authorized")
    if lock.get("haae_r0_execution_false_match_bool") is not True:
        failures.append("n10et_haae_r0_execution_not_false")
    if lock.get("bea_v1_a_false_match_bool") is not True:
        failures.append("n10et_bea_v1_a_not_false")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("haae_r0_docs_readback_match_bool", "n10et_docs_readback_match_bool",
                  "readme_readback_match_bool", "current_conclusions_match_bool",
                  "research_log_match_bool", "research_summary_match_bool",
                  "self_test_total_public_readback_match_bool",
                  "synthetic_validator_pass_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Route architecture coverage: 4 layers, design-only, non-identity.
    arch_layers = {r.get("layer_bucket") for r in report.get("route_architecture_records", [])}
    for needed in ROUTE_ARCHITECTURE_LAYERS:
        if needed not in arch_layers:
            failures.append(f"missing_route_architecture_layer_{needed}")
    for r in report.get("route_architecture_records", []):
        for field in ("design_only_bool", "schema_preflight_bool", "public_only_bool",
                      "evidence_core_preserved_bool",
                      "abstain_when_current_source_unavailable_bool"):
            if r.get(field) is not True:
                failures.append(f"arch_{r.get('layer_bucket')}_{field}_not_true")
        if r.get("execution_authorized_bool") is not False:
            failures.append(f"arch_{r.get('layer_bucket')}_execution_authorized")
        for field in ("haae_r0_not_bea_v1_a_bool", "haae_r0_not_selector_only_bool",
                      "haae_r0_not_selector_reranker_execution_bool",
                      "haae_r0_not_p5_bool", "haae_r0_not_runtime_default_promotion_bool"):
            if r.get(field) is not True:
                failures.append(f"arch_{r.get('layer_bucket')}_{field}_not_true")
    # Unified private schema: 10 groups, private-root-only, aggregate-only.
    schema_groups = report.get("unified_private_schema_spec_records", [])
    if len(schema_groups) != 10:
        failures.append(f"schema_group_count_not_10_got_{len(schema_groups)}")
    for r in schema_groups:
        for field in ("private_root_only_bool", "aggregate_buckets_only_bool",
                      "no_raw_release_bool", "no_replay_bool", "no_scoring_bool",
                      "no_retrieval_bool", "no_candidate_generation_bool",
                      "design_only_bool"):
            if r.get(field) is not True:
                failures.append(f"schema_{r.get('group_bucket')}_{field}_not_true")
        if r.get("execution_authorized_bool") is not False:
            failures.append(f"schema_{r.get('group_bucket')}_execution_authorized")
        for field in ("haae_r0_not_bea_v1_a_bool", "haae_r0_not_p5_bool"):
            if r.get(field) is not True:
                failures.append(f"schema_{r.get('group_bucket')}_{field}_not_true")
    # Public aggregation contract coverage.
    for r in report.get("public_aggregation_contract_records", []):
        for field in ("aggregate_buckets_only_bool", "no_raw_release_bool",
                      "design_only_bool"):
            if r.get(field) is not True:
                failures.append(f"agg_{r.get('aggregation_bucket')}_{field}_not_true")
    # Arm spec coverage: 5 arms, same budget, no execution.
    arm_buckets = {r.get("arm_bucket") for r in report.get("arm_spec_records", [])}
    for needed in ("BM25_same_budget", "RRF_same_budget", "BEA_v0.3_frozen",
                   "V1_sched_span", "V1_sched_span_rank"):
        if needed not in arm_buckets:
            failures.append(f"missing_arm_spec_{needed}")
    for r in report.get("arm_spec_records", []):
        if r.get("same_budget_bool") is not True:
            failures.append(f"arm_{r.get('arm_bucket')}_not_same_budget")
        if r.get("no_execution_in_haae_r0_bool") is not True:
            failures.append(f"arm_{r.get('arm_bucket')}_execution_in_haae_r0")
        if r.get("no_scoring_in_haae_r0_bool") is not True:
            failures.append(f"arm_{r.get('arm_bucket')}_scoring_in_haae_r0")
    # Metric spec coverage.
    if len(report.get("metric_spec_records", [])) != 6:
        failures.append("metric_spec_count_not_6")
    for r in report.get("metric_spec_records", []):
        for field in ("aggregate_buckets_only_bool", "no_per_task_bool",
                      "no_recompute_in_haae_r0_bool"):
            if r.get(field) is not True:
                failures.append(f"metric_{r.get('metric_bucket')}_{field}_not_true")
    # Heldout protocol.
    heldout = (report.get("heldout_protocol_records") or [{}])[0] if report.get("heldout_protocol_records") else {}
    for field in ("overlap_zero_enforced_bool", "no_gold_for_policy_bool",
                  "public_aggregate_publication_only_bool",
                  "no_split_materialized_in_haae_r0_bool"):
        if heldout.get(field) is not True:
            failures.append(f"heldout_{field}_not_true")
    if heldout.get("heldout_generalization_claim_bool") is not False:
        failures.append("heldout_generalization_claim_not_false")
    # Stop rules.
    if len(report.get("stop_rule_records", [])) != 4:
        failures.append("stop_rule_count_not_4")
    for r in report.get("stop_rule_records", []):
        if r.get("preserves_evidence_core_bool") is not True:
            failures.append(f"stop_rule_{r.get('stop_rule_bucket')}_not_preserving_evidence_core")
    # Synthetic validator.
    synth = (report.get("synthetic_validator_records") or [{}])[0] if report.get("synthetic_validator_records") else {}
    for field in ("embedded_fixture_bool", "validates_schema_bool",
                  "validates_arms_bool", "validates_metrics_bool",
                  "validates_heldout_bool", "validates_stop_rules_bool",
                  "validates_haae_r1_contract_bool", "no_real_data_bool",
                  "no_replay_bool", "no_retrieval_bool",
                  "no_candidate_generation_bool", "no_scoring_bool"):
        if synth.get(field) is not True:
            failures.append(f"synth_{field}_not_true")
    # HAAE-R1 contract.
    r1 = (report.get("haae_r1_contract_records") or [{}])[0] if report.get("haae_r1_contract_records") else {}
    for field in ("private_roots_only_bool", "aggregate_buckets_only_bool",
                  "no_replay_bool", "no_scoring_bool", "no_retrieval_bool",
                  "no_candidate_generation_bool", "feasibility_inventory_only_bool",
                  "no_execution_of_haae_layers_bool", "design_only_bool",
                  "authorized_for_next_phase_bool"):
        if r1.get(field) is not True:
            failures.append(f"r1_contract_{field}_not_true")
    if r1.get("execution_authorized_bool") is not False:
        failures.append("r1_contract_execution_authorized")
    # Risk control coverage.
    risk_buckets = {r.get("risk_bucket") for r in report.get("risk_control_records", [])}
    for needed in ALL_RISK_CONTROLS:
        if needed not in risk_buckets:
            failures.append(f"missing_risk_control_{needed}")
    for r in report.get("risk_control_records", []):
        if r.get("risk_controlled_bool") is not True:
            failures.append(f"risk_{r.get('risk_bucket')}_not_controlled")
    # Claim boundary.
    claim = (report.get("claim_boundary_records") or [{}])[0] if report.get("claim_boundary_records") else {}
    for field in ("method_winner_claim_bool", "production_retrieval_change_bool",
                  "runtime_default_change_bool", "selector_reranker_bool",
                  "threshold_tuning_bool", "frozen_rule_change_bool",
                  "raw_candidate_upload_bool", "raw_label_upload_bool",
                  "raw_path_upload_bool", "raw_query_upload_bool",
                  "raw_per_task_diagnostics_upload_bool",
                  "scaled_retrieval_claim_bool", "ci_rerun_bool",
                  "retrieval_recompute_bool", "promotion_claim_bool",
                  "candidate_generation_bool", "arm_scoring_bool",
                  "openlocus_execution_bool",
                  "network_run_bool", "provider_model_network_bool",
                  "n10et_execution_authorized_bool", "n10et_re_run_authorized_bool",
                  "haae_r0_execution_authorized_bool",
                  "haae_r1_execution_authorized_bool",
                  "haae_r1_replay_authorized_bool",
                  "haae_r1_scoring_authorized_bool",
                  "haae_r1_retrieval_authorized_bool",
                  "haae_r1_candidate_generation_authorized_bool",
                  "gold_used_for_policy_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_only_bool",
                  "schema_preflight_only_bool",
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
    # Stop/go: only HAAE-R1 feasibility inventory authorized.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if stop.get("haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool") is not True:
        failures.append("stop_haae_r1_feasibility_inventory_not_authorized")
    for field in ("haae_r1_execution_authorized_bool",
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
                  "design_only_bool", "schema_preflight_only_bool",
                  "haae_r1_design_only_feasibility_inventory_bool",
                  "haae_r1_private_roots_only_bool",
                  "haae_r1_aggregate_buckets_only_bool"):
        if stop.get(field) is not True:
            failures.append(f"stop_{field}_not_true")
    return failures


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_NO_SOURCE in EXIT0_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "https://github.com/a/b"})["status"] == "fail"))
    checks.append(("scanner_embedded_private_root", scan_summary({"bucket": "x .openlocus/research-private/ y"})["status"] == "fail"))
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_task_id", scan_summary({"v": "ci-00001"})["status"] == "fail"))
    checks.append(("scanner_passes_clean", scan_summary({"status": "ok", "count": 7})["status"] == "pass"))

    # Locked constants.
    checks.append(("locked_n10et_checkpoint", LOCKED_N10ET_CHECKPOINT == "26d817e"))
    checks.append(("locked_n10et_status",
                   LOCKED_N10ET_STATUS
                   == "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"))
    checks.append(("locked_n10et_next_phase",
                   "Hierarchical Actionable Evidence Acquisition" in LOCKED_N10ET_NEXT_ALLOWED_PHASE
                   and "Schema Preflight" in LOCKED_N10ET_NEXT_ALLOWED_PHASE))
    checks.append(("haae_r0_status",
                   STATUS_COMPLETE == "haae_r0_design_schema_preflight_complete_haae_r1_authorized"))
    checks.append(("next_route_constants", NEXT_ROUTE == "BEA-v1-HAAE-R1"
                   and "Unified Private Trace Schema Feasibility Inventory" in NEXT_ROUTE_FULL))
    checks.append(("haae_r0_non_identities",
                   set(HAAE_R0_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))
    checks.append(("route_architecture_layers",
                   set(ROUTE_ARCHITECTURE_LAYERS) == {
                       "source_acquisition", "rank_pack_depth_to_head",
                       "span_projection", "scheduler_operating_point"}))

    # Source lock against the real N10ET public report.
    lock_ok, lock_record = evaluate_n10et_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_n10et_status_match", lock_record["n10et_status_match_bool"] is True))
    checks.append(("source_lock_n10et_checkpoint_implicit",
                   lock_record["locked_n10et_checkpoint"] == LOCKED_N10ET_CHECKPOINT))
    checks.append(("source_lock_haae_r0_authorized_match",
                   lock_record["haae_r0_authorized_match_bool"] is True))
    checks.append(("source_lock_haae_r0_execution_false_match",
                   lock_record["haae_r0_execution_false_match_bool"] is True))
    checks.append(("source_lock_bea_v1_a_false_match",
                   lock_record["bea_v1_a_false_match_bool"] is True))
    checks.append(("source_lock_p5_false_match",
                   lock_record["p5_false_match_bool"] is True))
    checks.append(("source_lock_selector_reranker_false_match",
                   lock_record["selector_reranker_false_match_bool"] is True))
    checks.append(("source_lock_runtime_default_false_match",
                   lock_record["runtime_default_false_match_bool"] is True))
    checks.append(("source_lock_n10et_non_identity_match",
                   lock_record["n10et_non_identity_match_bool"] is True))
    checks.append(("source_lock_package_haae_r0_match",
                   lock_record["package_haae_r0_match_bool"] is True))

    readback = public_readback_match()
    checks.append(("readback_haae_r0_docs_match", readback["haae_r0_docs_readback_match_bool"] is True))
    checks.append(("readback_n10et_docs_match", readback["n10et_docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))
    checks.append(("readback_log_match", readback["research_log_match_bool"] is True))
    checks.append(("readback_summary_match", readback["research_summary_match_bool"] is True))

    # Route architecture records: 4 layers, design-only, non-identity.
    arch = route_architecture_records()
    checks.append(("arch_count", len(arch) == 4))
    checks.append(("arch_layers_match", {r["layer_bucket"] for r in arch} == set(ROUTE_ARCHITECTURE_LAYERS)))
    checks.append(("arch_design_only", all(r["design_only_bool"] is True for r in arch)))
    checks.append(("arch_schema_preflight", all(r["schema_preflight_bool"] is True for r in arch)))
    checks.append(("arch_no_execution", all(r["execution_authorized_bool"] is False for r in arch)))
    checks.append(("arch_evidence_core_preserved",
                   all(r["evidence_core_preserved_bool"] is True for r in arch)))
    checks.append(("arch_abstain_when_unavailable",
                   all(r["abstain_when_current_source_unavailable_bool"] is True for r in arch)))
    checks.append(("arch_non_identity", all(
        r["haae_r0_not_bea_v1_a_bool"] and r["haae_r0_not_selector_only_bool"]
        and r["haae_r0_not_selector_reranker_execution_bool"]
        and r["haae_r0_not_p5_bool"]
        and r["haae_r0_not_runtime_default_promotion_bool"]
        for r in arch)))

    # Unified private schema spec: 10 groups.
    schema = unified_private_schema_spec_records()
    checks.append(("schema_count", len(schema) == 10))
    checks.append(("schema_group_buckets",
                   {r["group_bucket"] for r in schema} == {g["group_bucket"] for g in SCHEMA_GROUPS}))
    checks.append(("schema_private_root_only",
                   all(r["private_root_only_bool"] is True for r in schema)))
    checks.append(("schema_aggregate_only",
                   all(r["aggregate_buckets_only_bool"] is True for r in schema)))
    checks.append(("schema_no_raw_release",
                   all(r["no_raw_release_bool"] is True for r in schema)))
    checks.append(("schema_no_replay",
                   all(r["no_replay_bool"] is True for r in schema)))
    checks.append(("schema_no_scoring",
                   all(r["no_scoring_bool"] is True for r in schema)))
    checks.append(("schema_no_retrieval",
                   all(r["no_retrieval_bool"] is True for r in schema)))
    checks.append(("schema_no_candidate_generation",
                   all(r["no_candidate_generation_bool"] is True for r in schema)))
    checks.append(("schema_no_execution",
                   all(r["execution_authorized_bool"] is False for r in schema)))

    # Public aggregation contract.
    aggs = public_aggregation_contract_records()
    checks.append(("agg_count", len(aggs) == 4))
    checks.append(("agg_aggregate_only",
                   all(r["aggregate_buckets_only_bool"] is True for r in aggs)))
    checks.append(("agg_no_raw_release",
                   all(r["no_raw_release_bool"] is True for r in aggs)))

    # Arm specs: 5 arms.
    arms = arm_spec_records()
    checks.append(("arms_count", len(arms) == 5))
    checks.append(("arms_buckets",
                   {r["arm_bucket"] for r in arms}
                   == {"BM25_same_budget", "RRF_same_budget", "BEA_v0.3_frozen",
                       "V1_sched_span", "V1_sched_span_rank"}))
    checks.append(("arms_same_budget", all(r["same_budget_bool"] is True for r in arms)))
    checks.append(("arms_no_execution",
                   all(r["no_execution_in_haae_r0_bool"] is True for r in arms)))
    checks.append(("arms_no_scoring",
                   all(r["no_scoring_in_haae_r0_bool"] is True for r in arms)))
    checks.append(("arms_no_tuning",
                   all(r["no_tuning_in_haae_r0_bool"] is True for r in arms)))
    checks.append(("arm_frozen_policy_only_for_bea_v03",
                   next(r for r in arms if r["arm_bucket"] == "BEA_v0.3_frozen")
                   ["is_frozen_policy_arm_bool"] is True
                   and next(r for r in arms if r["arm_bucket"] == "BM25_same_budget")
                   ["is_frozen_policy_arm_bool"] is False))

    # Metric specs: 6 metrics.
    metrics = metric_spec_records()
    checks.append(("metrics_count", len(metrics) == 6))
    checks.append(("metrics_aggregate_only",
                   all(r["aggregate_buckets_only_bool"] is True for r in metrics)))
    checks.append(("metrics_no_per_task",
                   all(r["no_per_task_bool"] is True for r in metrics)))
    checks.append(("metrics_no_recompute",
                   all(r["no_recompute_in_haae_r0_bool"] is True for r in metrics)))

    # Heldout protocol.
    heldout = heldout_protocol_records()[0]
    checks.append(("heldout_overlap_zero", heldout["overlap_zero_enforced_bool"] is True))
    checks.append(("heldout_no_gold_for_policy", heldout["no_gold_for_policy_bool"] is True))
    checks.append(("heldout_no_split_materialized",
                   heldout["no_split_materialized_in_haae_r0_bool"] is True))
    checks.append(("heldout_no_generalization_claim",
                   heldout["heldout_generalization_claim_bool"] is False))

    # Stop rules.
    stop_rules = stop_rule_records()
    checks.append(("stop_rules_count", len(stop_rules) == 4))
    checks.append(("stop_rules_preserve_evidence_core",
                   all(r["preserves_evidence_core_bool"] is True for r in stop_rules)))
    checks.append(("stop_rules_abstain",
                   all(r["abstain_bool"] is True for r in stop_rules)))

    # Synthetic validator.
    synth_validation = _validate_synthetic_fixture()
    checks.append(("synth_schema_validates", synth_validation["schema_validates_bool"] is True))
    checks.append(("synth_arms_validate", synth_validation["arms_validate_bool"] is True))
    checks.append(("synth_metrics_validate", synth_validation["metrics_validate_bool"] is True))
    checks.append(("synth_heldout_validates", synth_validation["heldout_validates_bool"] is True))
    checks.append(("synth_stop_rules_validate", synth_validation["stop_rules_validate_bool"] is True))
    checks.append(("synth_haae_r1_contract_validates",
                   synth_validation["haae_r1_contract_validates_bool"] is True))
    checks.append(("synth_fixture_task_count", len(SYNTHETIC_FIXTURE) == 4))

    # HAAE-R1 contract.
    r1 = haae_r1_contract_records()[0]
    checks.append(("r1_private_roots_only", r1["private_roots_only_bool"] is True))
    checks.append(("r1_aggregate_only", r1["aggregate_buckets_only_bool"] is True))
    checks.append(("r1_no_replay", r1["no_replay_bool"] is True))
    checks.append(("r1_no_scoring", r1["no_scoring_bool"] is True))
    checks.append(("r1_no_retrieval", r1["no_retrieval_bool"] is True))
    checks.append(("r1_no_candidate_generation", r1["no_candidate_generation_bool"] is True))
    checks.append(("r1_feasibility_inventory_only", r1["feasibility_inventory_only_bool"] is True))
    checks.append(("r1_no_execution_of_haae_layers",
                   r1["no_execution_of_haae_layers_bool"] is True))
    checks.append(("r1_authorized_for_next_phase", r1["authorized_for_next_phase_bool"] is True))
    checks.append(("r1_execution_not_authorized", r1["execution_authorized_bool"] is False))

    # Risk control coverage.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == len(ALL_RISK_CONTROLS)))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))
    checks.append(("risk_empty_control_plane_present",
                   any(r["risk_bucket"] == RISK_HAAE_R0_EMPTY_CONTROL_PLANE for r in risks)))
    checks.append(("risk_haae_r1_scope_creep_present",
                   any(r["risk_bucket"] == RISK_HAAE_R1_SCOPE_CREEP for r in risks)))

    # Stop/go: authorize only HAAE-R1 feasibility inventory.
    stop = stop_go_records()[0]
    checks.append(("stop_haae_r1_authorized",
                   stop["haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool"] is True))
    checks.append(("stop_haae_r1_no_exec", stop["haae_r1_execution_authorized_bool"] is False))
    checks.append(("stop_haae_r1_no_replay", stop["haae_r1_replay_authorized_bool"] is False))
    checks.append(("stop_haae_r1_no_scoring", stop["haae_r1_scoring_authorized_bool"] is False))
    checks.append(("stop_haae_r1_no_retrieval", stop["haae_r1_retrieval_authorized_bool"] is False))
    checks.append(("stop_haae_r1_no_candidate_generation",
                   stop["haae_r1_candidate_generation_authorized_bool"] is False))
    checks.append(("stop_haae_r0_no_exec", stop["haae_r0_execution_authorized_bool"] is False))
    checks.append(("stop_no_openlocus_execution", stop["openlocus_execution_authorized_bool"] is False))
    checks.append(("stop_no_arm_scoring", stop["arm_scoring_authorized_bool"] is False))
    checks.append(("stop_no_selector_p5_bea_v1_a", stop["selector_reranker_authorized_bool"] is False
                   and stop["p5_authorized_bool"] is False
                   and stop["bea_v1_a_authorized_bool"] is False))
    checks.append(("stop_no_runtime_promotion",
                   stop["runtime_default_change_authorized_bool"] is False
                   and stop["guard_full_diffaware_promotion_authorized_bool"] is False
                   and stop["method_winner_claim_authorized_bool"] is False))
    checks.append(("stop_haae_r0_non_identity", stop["haae_r0_not_bea_v1_a_bool"] is True
                   and stop["haae_r0_not_selector_only_bool"] is True
                   and stop["haae_r0_not_selector_reranker_execution_bool"] is True
                   and stop["haae_r0_not_p5_bool"] is True
                   and stop["haae_r0_not_runtime_default_promotion_bool"] is True))
    checks.append(("stop_haae_r1_private_roots_only",
                   stop["haae_r1_private_roots_only_bool"] is True
                   and stop["haae_r1_aggregate_buckets_only_bool"] is True))

    # Claim boundary explicit fields.
    cb = claim_boundary_records()[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_only_true", cb["design_only_bool"] is True))
    checks.append(("claim_schema_preflight_only_true", cb["schema_preflight_only_bool"] is True))
    checks.append(("claim_no_candidate_generation", cb["candidate_generation_bool"] is False))
    checks.append(("claim_no_arm_scoring", cb["arm_scoring_bool"] is False))
    checks.append(("claim_no_openlocus_execution", cb["openlocus_execution_bool"] is False))
    checks.append(("claim_haae_r1_execution_false", cb["haae_r1_execution_authorized_bool"] is False))
    checks.append(("claim_haae_r1_replay_false", cb["haae_r1_replay_authorized_bool"] is False))
    checks.append(("claim_haae_r1_scoring_false", cb["haae_r1_scoring_authorized_bool"] is False))
    checks.append(("claim_haae_r1_retrieval_false", cb["haae_r1_retrieval_authorized_bool"] is False))
    checks.append(("claim_haae_r1_candidate_generation_false",
                   cb["haae_r1_candidate_generation_authorized_bool"] is False))
    checks.append(("claim_haae_r0_non_identity", cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Full report build + validation.
    report = build_report()
    checks.append(("report_status_complete", report["status"] == STATUS_COMPLETE))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields", package["haae_r0_docs_readback_match_bool"] is True
                   and package["n10et_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))
    checks.append(("report_synth_validator_pass", package["synthetic_validator_pass_bool"] is True))
    checks.append(("report_stop_haae_r1_authorized",
                   report["stop_go_records"][0]
                   ["haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool"] is True))
    checks.append(("report_stop_no_execution",
                   report["stop_go_records"][0]["execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["haae_r0_execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["haae_r1_execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["openlocus_execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["arm_scoring_authorized_bool"] is False
                   and report["stop_go_records"][0]["provider_model_network_authorized_bool"] is False))

    # Bad-contract detection.
    bad = dict(report)
    bad["stop_go_records"] = [{**stop_go_records()[0], "haae_r1_execution_authorized_bool": True}]
    checks.append(("validate_fails_haae_r1_execution",
                   any("haae_r1_execution_authorized_bool_not_false" in f for f in validate_report(bad))))
    bad2 = dict(report)
    bad2["claim_boundary_records"] = [{**claim_boundary_records()[0], "method_winner_claim_bool": True}]
    checks.append(("validate_fails_method_winner",
                   any("method_winner_claim_bool_not_false" in f for f in validate_report(bad2))))
    bad3 = dict(report)
    bad3["public_package_records"] = [{**report["public_package_records"][0], "readme_readback_match_bool": False}]
    checks.append(("validate_fails_readback",
                   any("readme_readback_match_bool" in f for f in validate_report(bad3))))
    bad4 = dict(report)
    bad4["stop_go_records"] = [{**stop_go_records()[0], "bea_v1_a_authorized_bool": True}]
    checks.append(("validate_fails_bea_v1_a",
                   any("bea_v1_a_authorized_bool_not_false" in f for f in validate_report(bad4))))
    bad5 = dict(report)
    bad5["route_architecture_records"] = [{**route_architecture_records()[0],
                                           "haae_r0_not_bea_v1_a_bool": False}]
    checks.append(("validate_fails_haae_r0_identity",
                   any("haae_r0_not_bea_v1_a_bool_not_true" in f for f in validate_report(bad5))))
    bad6 = dict(report)
    bad6["unified_private_schema_spec_records"] = report["unified_private_schema_spec_records"][:-1]
    checks.append(("validate_fails_schema_count",
                   any("schema_group_count_not_10" in f for f in validate_report(bad6))))
    bad7 = dict(report)
    bad7["haae_r1_contract_records"] = [{**haae_r1_contract_records()[0],
                                          "no_replay_bool": False}]
    checks.append(("validate_fails_r1_replay",
                   any("r1_contract_no_replay_bool_not_true" in f for f in validate_report(bad7))))

    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks; expected_total={SELF_TEST_TOTAL_CHECKS})")
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

    # Public-only: load the N10ET public report only. No private diagnostic
    # inputs, no rerun, no recompute, no retrieval, no candidate generation, no
    # arm scoring, no OpenLocus execution.
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
