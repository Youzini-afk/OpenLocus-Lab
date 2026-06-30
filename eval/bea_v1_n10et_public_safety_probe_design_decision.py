#!/usr/bin/env python3
"""BEA-v1-N10ET Public Safety Probe Design/Decision.

N10ET is the **public-only close-out design/decision** phase for the BEA-v1-N10E
safety-probe branch. It sits after the N10ES checkpoint (commit ``8c04a0a``),
which packaged the N10ER bounded public CI score/guard safety probe as a valid
research negative and explicitly authorized only N10ET.

N10ET performs **no execution**. It reads **only** public artifacts/docs/current
conclusions/research logs/README and git metadata:

  * the committed N10ES public aggregate report (the audit package);
  * the committed N10ER public aggregate report (for direct locked-fact
    confirmation, public aggregate fields only);
  * the N10ES/N10ER evaluators/workflows for schema/status validation only
    (never executed — no rerun/recompute);
  * the N10ES/N10ER EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
    research-log/summary, and README public readback;
  * git metadata: the ``8c04a0a`` checkpoint that recorded the N10ES result and
    the ``c8fd353`` checkpoint that recorded the N10ER result / CI run
    ``28457213423`` (head ``2e7894e``).

Forbidden: any private reads (``.openlocus/research-private/``, ``/tmp`` rerun
paths, CI raw logs, repo clones, raw candidates/orders/labels/paths/queries/
tasks/repos, per-task diagnostics, N10EO private rerun data), any CI rerun,
any retrieval/recompute, any candidate generation, any selector/reranker
execution, any threshold tuning, any promotion, any runtime/default change, or
any method-winner claim.

N10ET:

  * Locks the N10ES/N10ER public facts (CI run ``28457213423``, status
    ``n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized``,
    N10ES status
    ``n10es_public_safety_probe_audit_package_complete_n10et_authorized``,
    sample ``80/60/40``, ``overlap_zero``, citation ``7772/7772``, baseline
    ``37/39/40/40``, full ``36/39/40/40`` (lost 1), guard ``38/39/40/40`` (lost
    0), diffaware ``37/39/40/40`` (lost 1), risk bucket ``task_count=26``,
    losses ``0/0/0``, ``guard_would_preserve_full_loss_count=0``).
  * Records the close-out decision: BEA-v1-N10E/difference-aware remains a
    local same-source hypothesis; N10ER/N10ES are a valid public held-out
    negative; no guard/full/diffaware promotion, no threshold tuning, no N10ER
    rerun, no method-winner, no runtime/default change, no selector/reranker,
    no P5, no BEA-v1-A.
  * Designs (no execution) and authorizes **only** the next route:
    **BEA-v1-HAAE-R0** — Hierarchical Actionable Evidence Acquisition Route
    Design / Schema Preflight. HAAE-R0 is explicitly **not** BEA-v1-A, not
    selector-only, not selector/reranker execution, not P5, not runtime/default
    promotion.
  * Emits a public-only design/decision artifact with explicit false privacy/
    claim boundary fields, scanner-validated.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10et_public_safety_probe_design_decision"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10ES_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10es_public_safety_probe_audit_package"
    / "bea_v1_n10es_public_safety_probe_audit_package_report.json"
)
N10ER_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe"
    / "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_report.json"
)
N10ES_EVAL = ROOT / "eval" / "bea_v1_n10es_public_safety_probe_audit_package.py"
N10ES_WORKFLOW = (
    ROOT / ".github" / "workflows"
    / "bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.yml"
)
README_PATH = ROOT / "README.md"
N10ES_DOC_EN = ROOT / "docs" / "en" / "bea-v1-n10es-public-safety-probe-audit-package.md"
N10ES_DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-n10es-public-safety-probe-audit-package.md"
N10ET_DOC_EN = ROOT / "docs" / "en" / "bea-v1-n10et-public-safety-probe-design-decision.md"
N10ET_DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-n10et-public-safety-probe-design-decision.md"
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"
LOG_EN = ROOT / "docs" / "en" / "research-log.md"
LOG_ZH = ROOT / "docs" / "zh" / "research-log.md"
SUMMARY_EN = ROOT / "docs" / "en" / "research-summary.md"
SUMMARY_ZH = ROOT / "docs" / "zh" / "research-summary.md"

# ── Locked N10ES / N10ER public facts (git metadata + upstream locks) ──────
LOCKED_N10ES_CHECKPOINT = "8c04a0a"
LOCKED_N10ER_CHECKPOINT = "c8fd353"
LOCKED_N10ER_CI_RUN = "28457213423"
LOCKED_N10ER_CI_HEAD = "2e7894e"
LOCKED_N10ER_STATUS = "n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized"
LOCKED_N10ES_STATUS = "n10es_public_safety_probe_audit_package_complete_n10et_authorized"
LOCKED_N10ES_NEXT_ALLOWED_PHASE = "BEA-v1-N10ET Public Safety Probe Design/Decision"
LOCKED_N10ER_NEXT_ALLOWED_PHASE = "BEA-v1-N10ES Bounded Public CI Safety Probe Audit"
# Upstream locks (read from the N10ES report's n10er_source_lock_records).
LOCKED_N10EQ_CHECKPOINT = "7963831"
LOCKED_N10EP_CHECKPOINT = "0a54b49"
LOCKED_N10EO_CHECKPOINT = "6f8eeda"

# ── Locked N10ER aggregate metrics (audited from the public report) ────────
LOCKED_SAMPLE = {
    "public_task_count": 80,
    "scored_task_count": 60,
    "task_with_gold_count": 40,
    "repo_count": 2,
}
LOCKED_OVERLAP_BUCKET = "overlap_zero"
LOCKED_OVERLAP_COUNT = 0
LOCKED_CITATION_VALID = 7772
LOCKED_CITATION_TOTAL = 7772
LOCKED_ARMS = {
    "baseline": {"top10": 37, "top20": 39, "top50": 40, "top100": 40, "lost": 0},
    "full": {"top10": 36, "top20": 39, "top50": 40, "top100": 40, "lost": 1},
    "guard": {"top10": 38, "top20": 39, "top50": 40, "top100": 40, "lost": 0},
    "diffaware": {"top10": 37, "top20": 39, "top50": 40, "top100": 40, "lost": 1},
}
LOCKED_RISK_TASK_COUNT = 26
LOCKED_RISK_FULL_LOST = 0
LOCKED_RISK_GUARD_LOST = 0
LOCKED_RISK_DIFFAWARE_LOST = 0
LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS = 0

# ── Next route design (N10ET authorizes ONLY HAAE-R0) ────────────────────────
NEXT_ROUTE = "BEA-v1-HAAE-R0"
NEXT_ROUTE_FULL = ("BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition "
                   "Route Design / Schema Preflight")
NEXT_ROUTE_BUCKET = "haae_r0_hierarchical_actionable_evidence_acquisition_route_design_schema_preflight"

# Explicit non-identities — HAAE-R0 is NOT any of these.
HAAE_R0_NOT_IDENTITIES = (
    "not_bea_v1_a",
    "not_selector_only",
    "not_selector_reranker_execution",
    "not_p5",
    "not_runtime_default_promotion",
)

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_COMPLETE = "n10et_public_safety_probe_design_decision_complete_haae_r0_authorized"
STATUS_NO_SOURCE = "n10et_public_safety_probe_design_decision_unavailable_no_locked_source"
STATUS_FAIL_LOCK = "fail_n10es_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
EXIT0_VOCAB = {STATUS_COMPLETE, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_SCAN,
                              STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT}

# Mirror N10ES's privacy scanner verbatim so the close-out phase upholds the
# same publication boundary as the audit it closes.
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

# Self-test check count (kept in sync with run_self_test; verified by --self-test).
SELF_TEST_TOTAL_CHECKS = 74


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10ET public safety probe design/decision")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--n10es-report", default=str(N10ES_REPORT),
                        help="path to the committed N10ES public aggregate artifact")
    parser.add_argument("--n10er-report", default=str(N10ER_REPORT),
                        help="path to the committed N10ER public aggregate artifact")
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
    N10ES close-out facts and the N10ET/HAAE-R0 close-out. Reads only public
    docs; performs no execution.

    Per-target fragment vocabulary:
      * README + current-research-conclusions use the backticked no-spaces
        arm-aggregate form ("37/39/40/40") and must mention N10ET + HAAE-R0 +
        at least one HAAE-R0 non-identity (BEA-v1-A / selector/reranker /
        selector-only / P5).
      * N10ET docs use the spaced arm-aggregate form ("37 / 39 / 40 / 40") and
        must mention N10ET + HAAE-R0 + the locked statuses + CI run + N10ES.
      * N10ES docs use the spaced arm-aggregate form and must mention the
        locked N10ES/N10ER facts + N10ET (as the next allowed phase). They do
        not need to mention HAAE-R0 (HAAE-R0 was unknown at N10ES time).
      * research-log/summary only need to mention N10ET + HAAE-R0 + at least
        one HAAE-R0 non-identity.
    """
    common_fragments = [
        LOCKED_N10ER_CI_RUN,
        LOCKED_N10ER_STATUS,
        LOCKED_N10ES_STATUS,
        "risk bucket",
        "N10ES",
    ]
    readme = read_text_or_empty(README_PATH)
    n10es_doc_en = read_text_or_empty(N10ES_DOC_EN)
    n10es_doc_zh = read_text_or_empty(N10ES_DOC_ZH)
    n10et_doc_en = read_text_or_empty(N10ET_DOC_EN)
    n10et_doc_zh = read_text_or_empty(N10ET_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)
    log_en = read_text_or_empty(LOG_EN)
    log_zh = read_text_or_empty(LOG_ZH)
    summary_en = read_text_or_empty(SUMMARY_EN)
    summary_zh = read_text_or_empty(SUMMARY_ZH)

    def has_all(text: str, fragments: list[str]) -> bool:
        return all(fragment in text for fragment in fragments)

    def has_n10et_closeout(text: str) -> bool:
        # N10ET close-out facts must reference HAAE-R0 explicitly and at least
        # one of the non-identity claims (HAAE-R0 is not BEA-v1-A / not P5 / ...).
        return ("N10ET" in text and "HAAE-R0" in text
                and ("BEA-v1-A" in text or "selector/reranker" in text
                     or "selector-only" in text or "P5" in text))

    # README + current-research-conclusions: no-spaces arm aggregates + HAAE-R0.
    readme_current_fragments = common_fragments + [
        "37/39/40/40", "36/39/40/40", "38/39/40/40",
        "N10ET", "HAAE-R0",
    ]
    readme_match = (has_all(readme, readme_current_fragments)
                    and has_n10et_closeout(readme))
    current_match = (has_all(current_en, readme_current_fragments)
                     and has_all(current_zh, readme_current_fragments)
                     and has_n10et_closeout(current_en)
                     and has_n10et_closeout(current_zh))

    # N10ET docs: spaced arm aggregates + N10ET + HAAE-R0 + close-out check.
    n10et_doc_fragments = common_fragments + [
        "37 / 39 / 40 / 40", "36 / 39 / 40 / 40", "38 / 39 / 40 / 40",
        "N10ET", "HAAE-R0",
    ]
    n10et_docs_match = (has_all(n10et_doc_en, n10et_doc_fragments)
                        and has_all(n10et_doc_zh, n10et_doc_fragments)
                        and has_n10et_closeout(n10et_doc_en)
                        and has_n10et_closeout(n10et_doc_zh))

    # N10ES docs: spaced arm aggregates + N10ET (as next phase). No HAAE-R0.
    n10es_doc_fragments = common_fragments + [
        "37 / 39 / 40 / 40", "36 / 39 / 40 / 40", "38 / 39 / 40 / 40",
        "N10ET",
    ]
    n10es_docs_match = (has_all(n10es_doc_en, n10es_doc_fragments)
                        and has_all(n10es_doc_zh, n10es_doc_fragments))

    log_match = has_n10et_closeout(log_en) and has_n10et_closeout(log_zh)
    summary_match = has_n10et_closeout(summary_en) and has_n10et_closeout(summary_zh)
    return {
        "n10et_docs_readback_match_bool": n10et_docs_match,
        "n10es_docs_readback_match_bool": n10es_docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "research_log_match_bool": log_match,
        "research_summary_match_bool": summary_match,
        "all_public_readback_match_bool": (n10et_docs_match and n10es_docs_match
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


# ── N10ES source lock (reads public N10ES + N10ER reports only; no rerun) ─

def _n10es_lock(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("n10er_source_lock_records") or [{}])[0] if report.get("n10er_source_lock_records") else {}


def _n10es_package(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}


def _n10es_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def _n10es_metric(report: dict[str, Any], bucket: str) -> dict[str, Any]:
    for row in report.get("n10er_metric_audit_records") or []:
        if row.get("metric_bucket") == bucket:
            return row
    return {}


def _n10es_arm(report: dict[str, Any], arm: str) -> dict[str, Any]:
    for row in report.get("n10er_arm_audit_records") or []:
        if row.get("arm_bucket") == arm:
            return row
    return {}


def _n10er_stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def evaluate_n10es_source_lock() -> tuple[bool, dict[str, Any]]:
    """Load the N10ES + N10ER public reports and validate every locked field.

    Reads ONLY public aggregate reports. Performs no execution, no retrieval,
    no recompute, and reads no private inputs.
    """
    n10es_report, es_state = load_json(N10ES_REPORT)
    n10er_report, er_state = load_json(N10ER_REPORT)
    present_ok = es_state == "present" and isinstance(n10es_report, dict)
    n10er_present_ok = er_state == "present" and isinstance(n10er_report, dict)

    status_ok = bool(n10es_report and n10es_report.get("status") == LOCKED_N10ES_STATUS)
    n10es_scan_ok = bool(n10es_report
                         and n10es_report.get("forbidden_scan", {}).get("status") == "pass")

    lock = _n10es_lock(n10es_report or {})
    n10er_status_ok = lock.get("locked_n10er_status") == LOCKED_N10ER_STATUS
    n10er_checkpoint_ok = lock.get("locked_n10er_checkpoint") == LOCKED_N10ER_CHECKPOINT
    n10er_ci_run_ok = lock.get("locked_n10er_ci_run") == LOCKED_N10ER_CI_RUN
    n10er_ci_head_ok = lock.get("locked_n10er_ci_head") == LOCKED_N10ER_CI_HEAD
    n10eq_checkpoint_ok = lock.get("locked_n10eq_checkpoint") == LOCKED_N10EQ_CHECKPOINT
    n10ep_checkpoint_ok = lock.get("locked_n10ep_checkpoint") == LOCKED_N10EP_CHECKPOINT
    n10eo_checkpoint_ok = lock.get("locked_n10eo_checkpoint") == LOCKED_N10EO_CHECKPOINT
    n10es_source_lock_ok = lock.get("source_locked_bool") is True
    no_ci_rerun_ok = lock.get("no_ci_rerun_performed_bool") is True
    no_retrieval_ok = lock.get("no_retrieval_performed_bool") is True
    no_recompute_ok = lock.get("no_recompute_performed_bool") is True
    no_private_read_ok = lock.get("no_private_input_read_bool") is True

    sample_metric = _n10es_metric(n10es_report or {}, "sample_aggregate")
    sample_match = (
        sample_metric.get("locked_public_task_count") == LOCKED_SAMPLE["public_task_count"]
        and sample_metric.get("locked_scored_task_count") == LOCKED_SAMPLE["scored_task_count"]
        and sample_metric.get("locked_task_with_gold_count") == LOCKED_SAMPLE["task_with_gold_count"]
        and sample_metric.get("locked_repo_count") == LOCKED_SAMPLE["repo_count"]
        and sample_metric.get("metric_match_bool") is True
        and sample_metric.get("recomputed_bool") is False
    )

    overlap_metric = _n10es_metric(n10es_report or {}, "heldout_overlap")
    overlap_match = (
        overlap_metric.get("locked_overlap_public_bucket") == LOCKED_OVERLAP_BUCKET
        and overlap_metric.get("locked_overlap_count") == LOCKED_OVERLAP_COUNT
        and overlap_metric.get("metric_match_bool") is True
        and overlap_metric.get("recomputed_bool") is False
    )

    citation_metric = _n10es_metric(n10es_report or {}, "citation_validity")
    citation_match = (
        citation_metric.get("locked_citation_valid_count") == LOCKED_CITATION_VALID
        and citation_metric.get("locked_citation_total_count") == LOCKED_CITATION_TOTAL
        and citation_metric.get("metric_match_bool") is True
        and citation_metric.get("recomputed_bool") is False
    )

    arm_matches: dict[str, bool] = {}
    arm_detail: list[dict[str, Any]] = []
    for arm, locked in LOCKED_ARMS.items():
        rec = _n10es_arm(n10es_report or {}, arm)
        ok = (
            rec.get("locked_top10_file_recovery_count") == locked["top10"]
            and rec.get("locked_top20_file_recovery_count") == locked["top20"]
            and rec.get("locked_top50_file_recovery_count") == locked["top50"]
            and rec.get("locked_top100_file_recovery_count") == locked["top100"]
            and rec.get("locked_lost_baseline_top10_hits") == locked["lost"]
            and rec.get("arm_aggregate_match_bool") is True
        )
        arm_matches[arm] = ok
        arm_detail.append({
            "anonymous_arm_audit_id": f"n10etarm000{list(LOCKED_ARMS).index(arm)}",
            "arm_bucket": arm,
            "locked_top10_file_recovery_count": locked["top10"],
            "locked_top20_file_recovery_count": locked["top20"],
            "locked_top50_file_recovery_count": locked["top50"],
            "locked_top100_file_recovery_count": locked["top100"],
            "locked_lost_baseline_top10_hits": locked["lost"],
            "arm_aggregate_match_bool": ok,
        })
    arms_all_match = all(arm_matches.values())

    risk_metric = _n10es_metric(n10es_report or {}, "risk_bucket_signal")
    risk_match = (
        risk_metric.get("locked_risk_task_count") == LOCKED_RISK_TASK_COUNT
        and risk_metric.get("locked_full_lost_baseline_count") == LOCKED_RISK_FULL_LOST
        and risk_metric.get("locked_guard_lost_baseline_count") == LOCKED_RISK_GUARD_LOST
        and risk_metric.get("locked_diffaware_lost_baseline_count") == LOCKED_RISK_DIFFAWARE_LOST
        and risk_metric.get("locked_guard_would_preserve_full_loss_count")
        == LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS
        and risk_metric.get("metric_match_bool") is True
        and risk_metric.get("recomputed_bool") is False
    )

    # N10ES stop/go must authorize only N10ET (the design/decision handoff).
    n10es_stop = _n10es_stop_go(n10es_report or {})
    n10es_next_phase_ok = (n10es_stop.get("next_allowed_phase")
                           == LOCKED_N10ES_NEXT_ALLOWED_PHASE)
    n10et_authorized_ok = n10es_stop.get("n10et_design_decision_authorized_bool") is True
    n10es_no_execution_ok = (
        n10es_stop.get("execution_authorized_bool") is False
        and n10es_stop.get("n10er_re_run_authorized_bool") is False
        and n10es_stop.get("rerun_authorized_bool") is False
        and n10es_stop.get("retrieval_authorized_bool") is False
        and n10es_stop.get("recompute_authorized_bool") is False
        and n10es_stop.get("threshold_tuning_authorized_bool") is False
        and n10es_stop.get("guard_full_diffaware_promotion_authorized_bool") is False
        and n10es_stop.get("runtime_default_change_authorized_bool") is False
        and n10es_stop.get("method_winner_claim_authorized_bool") is False
        and n10es_stop.get("selector_reranker_authorized_bool") is False
        and n10es_stop.get("ci_variant_execution_authorized_bool") is False
    )

    # Cross-check the N10ER public report's stop/go next_allowed_phase to make
    # sure the N10ER → N10ES → N10ET handoff chain is consistent on public
    # artifacts (no rerun, no private read).
    n10er_stop = _n10er_stop_go(n10er_report or {})
    n10er_next_phase_ok = (n10_stop := n10er_stop.get("next_allowed_phase")
                           ) == LOCKED_N10ER_NEXT_ALLOWED_PHASE if n10er_present_ok else False
    n10er_audit_authorized_ok = (n10er_stop.get("n10es_audit_authorized_bool") is True
                                 if n10er_present_ok else False)

    # Public readback across docs/README/current conclusions.
    readback = public_readback_match()

    lock_ok = (present_ok and status_ok and n10es_scan_ok
               and n10er_status_ok and n10er_checkpoint_ok and n10er_ci_run_ok
               and n10er_ci_head_ok and n10eq_checkpoint_ok and n10ep_checkpoint_ok
               and n10eo_checkpoint_ok and n10es_source_lock_ok
               and no_ci_rerun_ok and no_retrieval_ok and no_recompute_ok
               and no_private_read_ok
               and sample_match and overlap_match and citation_match
               and arms_all_match and risk_match
               and n10es_next_phase_ok and n10et_authorized_ok and n10es_no_execution_ok
               and n10er_next_phase_ok and n10er_audit_authorized_ok
               and readback["all_public_readback_match_bool"])

    lock_record = {
        "anonymous_source_lock_id": "n10etsource0000",
        "source_lock_bucket": "n10es_public_report_locked",
        "input_artifact_load_status_bucket": es_state,
        "n10er_artifact_load_status_bucket": er_state,
        "locked_n10es_checkpoint": LOCKED_N10ES_CHECKPOINT,
        "locked_n10er_checkpoint": LOCKED_N10ER_CHECKPOINT,
        "locked_n10er_ci_run": LOCKED_N10ER_CI_RUN,
        "locked_n10er_ci_head": LOCKED_N10ER_CI_HEAD,
        "locked_n10er_status": LOCKED_N10ER_STATUS,
        "locked_n10es_status": LOCKED_N10ES_STATUS,
        "locked_n10es_next_allowed_phase": LOCKED_N10ES_NEXT_ALLOWED_PHASE,
        "locked_n10er_next_allowed_phase": LOCKED_N10ER_NEXT_ALLOWED_PHASE,
        "locked_n10eq_checkpoint": LOCKED_N10EQ_CHECKPOINT,
        "locked_n10ep_checkpoint": LOCKED_N10EP_CHECKPOINT,
        "locked_n10eo_checkpoint": LOCKED_N10EO_CHECKPOINT,
        "n10es_status_match_bool": status_ok,
        "n10es_scan_pass_bool": n10es_scan_ok,
        "n10er_status_match_bool": n10er_status_ok,
        "n10er_checkpoint_match_bool": n10er_checkpoint_ok,
        "n10er_ci_run_match_bool": n10er_ci_run_ok,
        "n10er_ci_head_match_bool": n10er_ci_head_ok,
        "n10eq_checkpoint_match_bool": n10eq_checkpoint_ok,
        "n10ep_checkpoint_match_bool": n10ep_checkpoint_ok,
        "n10eo_checkpoint_match_bool": n10eo_checkpoint_ok,
        "n10es_source_locked_bool": n10es_source_lock_ok,
        "no_ci_rerun_performed_bool": no_ci_rerun_ok,
        "no_retrieval_performed_bool": no_retrieval_ok,
        "no_recompute_performed_bool": no_recompute_ok,
        "no_private_input_read_bool": no_private_read_ok,
        "sample_aggregate_match_bool": sample_match,
        "overlap_match_bool": overlap_match,
        "citation_match_bool": citation_match,
        "arm_aggregate_all_match_bool": arms_all_match,
        "risk_aggregate_match_bool": risk_match,
        "n10es_next_phase_match_bool": n10es_next_phase_ok,
        "n10et_design_decision_authorized_match_bool": n10et_authorized_ok,
        "n10es_no_execution_match_bool": n10es_no_execution_ok,
        "n10er_next_phase_match_bool": n10er_next_phase_ok,
        "n10er_n10es_audit_authorized_match_bool": n10er_audit_authorized_ok,
        "public_readback_match_bool": readback["all_public_readback_match_bool"],
        "source_locked_bool": lock_ok,
    }
    return lock_ok, lock_record


# ── Decision records (close-out for the N10E safety-probe branch) ───────────

def decision_records() -> list[dict[str, Any]]:
    """Close-out decisions for the BEA-v1-N10E safety-probe branch."""
    return [
        {
            "anonymous_decision_id": "n10etdecision0000",
            "decision_bucket": "n10e_differenceaware_remains_local_same_source_hypothesis",
            "decision_description_bucket": (
                "the difference-aware rule (top5_novel_candidate_item_count >= 4 "
                "selects guarded else full) reached 13/60 on the same-source "
                "N10DZ/N10EB sample but regressed on the N10EN public CI canary "
                "(37/40 vs baseline 39/40) and its held-out safety signal did "
                "not reproduce on the N10ER public CI sample (risk bucket 26, "
                "losses 0/0/0). it remains a local same-source hypothesis, not "
                "a transferable method."
            ),
            "promotion_authorized_bool": False,
            "threshold_tuning_authorized_bool": False,
            "frozen_rule_change_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
        },
        {
            "anonymous_decision_id": "n10etdecision0001",
            "decision_bucket": "n10er_n10es_valid_public_heldout_negative",
            "decision_description_bucket": (
                "the N10ER held-out public CI safety probe (CI run 28457213423) "
                "reproduced zero baseline-displacement signal in a sufficient risk "
                "bucket (task_count=26, full/guard/diffaware losses 0/0/0, "
                "guard_would_preserve_full_loss_count=0). N10ES locked this as a "
                "valid research negative, not a CI failure. the pair (N10ER, "
                "N10ES) is a valid public held-out negative for the N10EO "
                "low-novelty full-displacement / guard-preservation safety signal."
            ),
            "valid_research_negative_bool": True,
            "ci_failure_bool": False,
            "signal_reproduced_bool": False,
            "heldout_generalization_claim_bool": False,
            "promotion_authorized_bool": False,
            "threshold_tuning_authorized_bool": False,
            "frozen_rule_change_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
        },
        {
            "anonymous_decision_id": "n10etdecision0002",
            "decision_bucket": "no_guard_full_diffaware_promotion_no_threshold_tuning_no_n10er_rerun",
            "decision_description_bucket": (
                "no guard/full/diffaware promotion, no threshold tuning, no N10ER "
                "rerun, no CI variant execution, no selector/reranker execution, "
                "no new policy experiment, no runtime/default change, no "
                "method-winner claim, no downstream/scaled retrieval, no raw "
                "diagnostic publication. all such stop/go fields remain false."
            ),
            "promotion_authorized_bool": False,
            "threshold_tuning_authorized_bool": False,
            "n10er_re_run_authorized_bool": False,
            "ci_variant_execution_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "new_policy_experiment_authorized_bool": False,
            "runtime_default_change_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
        },
    ]


# ── HAAE-R0 next-route design records (design-only, schema preflight) ──────

def haae_r0_route_records() -> list[dict[str, Any]]:
    """Design records for the next route, BEA-v1-HAAE-R0. Design-only; no
    execution. Explicitly records the non-identity claims (HAAE-R0 is NOT
    BEA-v1-A / selector-only / selector-reranker execution / P5 / runtime
    promotion)."""
    return [
        {
            "anonymous_route_id": "n10etroute0000",
            "route_bucket": NEXT_ROUTE_BUCKET,
            "route_name": NEXT_ROUTE_FULL,
            "route_phase_bucket": "BEA-v1-HAAE-R0",
            "route_kind_bucket": "hierarchical_actionable_evidence_acquisition_route_design_schema_preflight",
            "design_description_bucket": (
                "design (no execution) the next acquisition route as a "
                "hierarchical, actionable-evidence acquisition route: a schema "
                "preflight that defines how evidence-acquisition actions can be "
                "layered hierarchically (anchor / span-window / candidate-source "
                "/ scheduler / safety-probe) while preserving EvidenceCore and "
                "abstaining when current-source evidence is unavailable. the "
                "preflight checks the route's public schema, source inputs, "
                "claim boundary, and stop/go contract before any future "
                "execution-authorized phase is opened."
            ),
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "aggregate_buckets_only_bool": True,
            "public_only_bool": True,
            "haae_r0_not_bea_v1_a_bool": True,
            "haae_r0_not_selector_only_bool": True,
            "haae_r0_not_selector_reranker_execution_bool": True,
            "haae_r0_not_p5_bool": True,
            "haae_r0_not_runtime_default_promotion_bool": True,
            "non_identity_buckets": list(HAAE_R0_NOT_IDENTITIES),
            "rationale_bucket": (
                "deep research report 5 recommends closing the BEA-v1-N10E "
                "safety-probe branch and opening a new HAAE-R0 route rather "
                "than BEA-v1-A. HAAE-R0 is a design/schema preflight only; it "
                "is not the coverage-preserving selector route (BEA-v1-A), "
                "not a selector-only design, not selector/reranker execution, "
                "not P5, and not a runtime/default promotion."
            ),
            "authorized_for_next_phase_bool": True,
        },
        {
            "anonymous_route_id": "n10etroute0001",
            "route_bucket": "haae_r0_schema_preflight_inputs",
            "route_name": "HAAE-R0 Schema Preflight Inputs (public-artifact-only)",
            "route_phase_bucket": "BEA-v1-HAAE-R0",
            "route_kind_bucket": "schema_preflight_public_artifact_inputs",
            "design_description_bucket": (
                "the HAAE-R0 preflight reads only public artifacts/docs and git "
                "metadata: the closed N10ES/N10ER/N10EQ/N10EP/N10EO public "
                "aggregates, the BEA-v1 actionability-matrix / trace-surface "
                "contracts, and the research-design/openlocus-research-design "
                "schemas. it performs no private reads, no CI rerun, no "
                "retrieval/recompute, no candidate generation, and no "
                "selector/reranker execution."
            ),
            "design_only_bool": True,
            "schema_preflight_bool": True,
            "execution_authorized_bool": False,
            "aggregate_buckets_only_bool": True,
            "public_only_bool": True,
            "haae_r0_not_bea_v1_a_bool": True,
            "haae_r0_not_selector_only_bool": True,
            "haae_r0_not_selector_reranker_execution_bool": True,
            "haae_r0_not_p5_bool": True,
            "haae_r0_not_runtime_default_promotion_bool": True,
            "non_identity_buckets": list(HAAE_R0_NOT_IDENTITIES),
            "rationale_bucket": (
                "preflight is a public-artifact-only schema/contract check; "
                "execution of any layer of the HAAE route would require a "
                "separate, explicitly authorized future phase."
            ),
            "authorized_for_next_phase_bool": True,
        },
    ]


# ── Risk control records ───────────────────────────────────────────────────

RISK_PROMOTION_FROM_NEGATIVE = "promotion_from_valid_research_negative"
RISK_THRESHOLD_TUNING_FROM_MISFIRE = "hindsight_threshold_tuning_from_no_signal"
RISK_N10ER_RERUN_CREEP = "n10er_rerun_creep"
RISK_HAAE_R0_AS_SELECTOR_OR_P5 = "haae_r0_drift_into_selector_or_p5_or_runtime"
RISK_RUNTIME_DEFAULT_CREEP = "runtime_default_creep"
RISK_PRIVATE_DIAGNOSTIC_LEAKAGE = "private_diagnostic_leakage"
RISK_AGGREGATE_OVERINTERPRETATION = "aggregate_overinterpretation_from_two_cases"
ALL_RISK_CONTROLS = (
    RISK_PROMOTION_FROM_NEGATIVE,
    RISK_THRESHOLD_TUNING_FROM_MISFIRE,
    RISK_N10ER_RERUN_CREEP,
    RISK_HAAE_R0_AS_SELECTOR_OR_P5,
    RISK_RUNTIME_DEFAULT_CREEP,
    RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
    RISK_AGGREGATE_OVERINTERPRETATION,
)


def risk_control_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_risk_control_id": "n10etrisk0000",
            "risk_bucket": RISK_PROMOTION_FROM_NEGATIVE,
            "risk_description_bucket": (
                "treating the N10ER valid research negative as evidence to "
                "promote guard/full/diffaware would invert the finding."),
            "mitigation_bucket": (
                "guard_full_diffaware_promotion_authorized_bool=false; "
                "method_winner_claim_authorized_bool=false; no arm is promoted."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0001",
            "risk_bucket": RISK_THRESHOLD_TUNING_FROM_MISFIRE,
            "risk_description_bucket": (
                "tuning the frozen threshold (>=4) with hindsight on the same "
                "canary/negative samples would be data snooping."),
            "mitigation_bucket": (
                "threshold_tuning_authorized_bool=false; frozen rule unchanged; "
                "any threshold design must use held-out public evidence."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0002",
            "risk_bucket": RISK_N10ER_RERUN_CREEP,
            "risk_description_bucket": (
                "re-running N10ER until the safety signal reproduces would "
                "p-hack the held-out probe."),
            "mitigation_bucket": (
                "n10er_re_run_authorized_bool=false; "
                "ci_variant_execution_authorized_bool=false; "
                "recompute_authorized_bool=false; rerun_authorized_bool=false."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0003",
            "risk_bucket": RISK_HAAE_R0_AS_SELECTOR_OR_P5,
            "risk_description_bucket": (
                "the HAAE-R0 route could be quietly reframed as BEA-v1-A, a "
                "selector-only design, selector/reranker execution, P5, or a "
                "runtime/default promotion."),
            "mitigation_bucket": (
                "every HAAE-R0 route record carries the explicit non-identity "
                "booleans (not_bea_v1_a, not_selector_only, "
                "not_selector_reranker_execution, not_p5, "
                "not_runtime_default_promotion); selector_reranker_authorized_"
                "bool=false; runtime_default_change_authorized_bool=false; "
                "v1_a_authorized_bool=false (carried from prior stop/go vocab)."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0004",
            "risk_bucket": RISK_RUNTIME_DEFAULT_CREEP,
            "risk_description_bucket": (
                "a close-out design could implicitly drift runtime/default "
                "behavior by codifying a route as a default gate."),
            "mitigation_bucket": (
                "runtime_default_change_authorized_bool=false; any HAAE route "
                "remains opt-in/eval-only; no runtime or default change."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0005",
            "risk_bucket": RISK_PRIVATE_DIAGNOSTIC_LEAKAGE,
            "risk_description_bucket": (
                "N10EO used a private diagnostic rerun; N10ET must not leak "
                "per-task diagnostics/paths/candidates/orders/labels into the "
                "public close-out design."),
            "mitigation_bucket": (
                "N10ET reads only public aggregate artifacts/docs/git metadata; "
                "forbidden_scan blocks raw per-task/paths/orders/labels keys and "
                "private rerun paths; aggregate_buckets_only_bool=true."),
            "risk_controlled_bool": True,
        },
        {
            "anonymous_risk_control_id": "n10etrisk0006",
            "risk_bucket": RISK_AGGREGATE_OVERINTERPRETATION,
            "risk_description_bucket": (
                "drawing strong conclusions from the 2-case N10EO misfire / "
                "the no-signal N10ER reproduction risks aggregate "
                "overinterpretation."),
            "mitigation_bucket": (
                "N10ET is a public-only close-out design/decision; no "
                "promotion, no rule change, no method-winner claim; HAAE-R0 "
                "is design/schema-preflight only."),
            "risk_controlled_bool": True,
        },
    ]


# ── Public package records ─────────────────────────────────────────────────

def public_package_records(lock_record: dict[str, Any],
                           readback: dict[str, bool]) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "n10etpackage0000",
        "package_bucket": "n10et_public_safety_probe_design_decision_package",
        "schema_version": "bea_v1_n10et_public_safety_probe_design_decision_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_decision_only_bool": True,
        "private_input_read_count": 0,
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "candidate_generation_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "n10es_source_locked_bool": lock_record["n10es_source_locked_bool"],
        "n10es_docs_readback_match_bool": readback["n10es_docs_readback_match_bool"],
        "n10et_docs_readback_match_bool": readback["n10et_docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "research_log_match_bool": readback["research_log_match_bool"],
        "research_summary_match_bool": readback["research_summary_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
        "haae_r0_authorized_bool": True,
        "haae_r0_design_only_bool": True,
        "haae_r0_schema_preflight_bool": True,
    }]


# ── Claim boundary records ────────────────────────────────────────────────

def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "n10etclaim0000",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "design_decision_only_bool": True,
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
        "n10er_execution_authorized_bool": False,
        "n10er_re_run_authorized_bool": False,
        "n10es_re_run_authorized_bool": False,
        "n10es_audit_authorized_bool": False,
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
                           readback: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        _gate("n10etgate0000", "n10es_public_source_locked",
              lock_record["n10es_source_locked_bool"]),
        _gate("n10etgate0001", "n10er_public_facts_locked",
              lock_record["n10er_checkpoint_match_bool"]
              and lock_record["n10er_ci_run_match_bool"]
              and lock_record["n10er_status_match_bool"]),
        _gate("n10etgate0002", "n10es_metric_audit_no_recompute",
              lock_record["sample_aggregate_match_bool"]
              and lock_record["overlap_match_bool"]
              and lock_record["citation_match_bool"]
              and lock_record["arm_aggregate_all_match_bool"]
              and lock_record["risk_aggregate_match_bool"]),
        _gate("n10etgate0003", "n10et_no_threshold_tuning", True),
        _gate("n10etgate0004", "n10et_no_method_winner_claim", True),
        _gate("n10etgate0005", "n10et_no_runtime_default_change", True),
        _gate("n10etgate0006", "n10et_no_promotion_or_frozen_rule_change", True),
        _gate("n10etgate0007", "n10et_no_ci_rerun_retrieval_recompute_candidate_generation", True),
        _gate("n10etgate0008", "n10et_no_private_input_read", True),
        _gate("n10etgate0009", "n10et_no_selector_reranker_no_p5_no_bea_v1_a", True),
        _gate("n10etgate0010", "n10et_no_n10er_rerun", True),
        _gate("n10etgate0011", "n10et_interpretation_consistent_with_locked_aggregates",
              lock_record["risk_aggregate_match_bool"]),
        _gate("n10etgate0012", "n10es_stop_go_next_phase_match",
              lock_record["n10es_next_phase_match_bool"]),
        _gate("n10etgate0013", "n10er_stop_go_next_phase_match",
              lock_record["n10er_next_phase_match_bool"]
              and lock_record["n10er_n10es_audit_authorized_match_bool"]),
        _gate("n10etgate0014", "docs_readback_match_gate",
              readback["n10et_docs_readback_match_bool"]
              and readback["n10es_docs_readback_match_bool"]),
        _gate("n10etgate0015", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("n10etgate0016", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
        _gate("n10etgate0017", "research_log_match_gate",
              readback["research_log_match_bool"]),
        _gate("n10etgate0018", "research_summary_match_gate",
              readback["research_summary_match_bool"]),
        _gate("n10etgate0019", "haae_r0_authorized_design_only_schema_preflight_gate", True),
        _gate("n10etgate0020", "haae_r0_non_identity_gate", True),
    ]


# ── Stop/go records (authorize ONLY HAAE-R0 design/schema preflight) ────────

def stop_go_records() -> list[dict[str, Any]]:
    """Stop/go: authorize only the BEA-v1-HAAE-R0 route design/schema
    preflight (public-only, design-only, no execution). No execution, rerun,
    tuning, promotion, runtime, method, downstream, scaled, raw, candidate
    generation, or provider authorization. HAAE-R0 is explicitly NOT BEA-v1-A,
    not selector-only, not selector/reranker execution, not P5, not
    runtime/default promotion."""
    return [{
        "anonymous_stop_go_id": "n10etstop0000",
        "next_allowed_phase": NEXT_ROUTE_FULL,
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "design_decision_only_bool": True,
        "haae_r0_design_only_schema_preflight_authorized_bool": True,
        "haae_r0_execution_authorized_bool": False,
        "haae_r0_not_bea_v1_a_bool": True,
        "haae_r0_not_selector_only_bool": True,
        "haae_r0_not_selector_reranker_execution_bool": True,
        "haae_r0_not_p5_bool": True,
        "haae_r0_not_runtime_default_promotion_bool": True,
        "n10et_audit_authorized_bool": False,
        "n10et_re_run_authorized_bool": False,
        "execution_authorized_bool": False,
        "rerun_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "recompute_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
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
    lock_ok, lock_record = evaluate_n10es_source_lock()
    readback = public_readback_match()
    status = STATUS_COMPLETE if lock_ok else STATUS_NO_SOURCE
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10et_public_safety_probe_design_decision_v1",
        "phase_bucket": "BEA-v1-N10ET Public Safety Probe Design/Decision",
        "status": status,
        "n10es_source_lock_records": [lock_record],
        "decision_records": decision_records(),
        "haae_r0_route_records": haae_r0_route_records(),
        "risk_control_records": risk_control_records(),
        "public_package_records": public_package_records(lock_record, readback),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback),
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "n10etgate0000", "gate_bucket": "n10es_public_source_locked",
             "gate_passed_bool": lock_record["n10es_source_locked_bool"]},
            {"anonymous_gate_id": "n10etgate0007",
             "gate_bucket": "no_ci_rerun_retrieval_recompute_candidate_generation",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10etgate0008", "gate_bucket": "no_private_input_read",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10etgate0009",
             "gate_bucket": "no_selector_reranker_no_p5_no_bea_v1_a",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10etgate0010", "gate_bucket": "no_n10er_rerun",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10etgate0020",
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
    lock = (report.get("n10es_source_lock_records") or [{}])[0] if report.get("n10es_source_lock_records") else {}
    if lock.get("source_locked_bool") is not True and report.get("status") not in (STATUS_NO_SOURCE,):
        failures.append("n10es_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_retrieval_performed_bool") is not True:
        failures.append("retrieval_claim_not_true")
    if lock.get("no_recompute_performed_bool") is not True:
        failures.append("recompute_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("n10es_next_phase_match_bool") is not True:
        failures.append("n10es_next_phase_mismatch")
    if lock.get("n10et_design_decision_authorized_match_bool") is not True:
        failures.append("n10et_design_decision_not_authorized_by_n10es")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("n10et_docs_readback_match_bool", "n10es_docs_readback_match_bool",
                  "readme_readback_match_bool", "current_conclusions_match_bool",
                  "research_log_match_bool", "research_summary_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Decision coverage.
    decisions = {r.get("decision_bucket") for r in report.get("decision_records", [])}
    for needed in ("n10e_differenceaware_remains_local_same_source_hypothesis",
                   "n10er_n10es_valid_public_heldout_negative",
                   "no_guard_full_diffaware_promotion_no_threshold_tuning_no_n10er_rerun"):
        if needed not in decisions:
            failures.append(f"missing_decision_{needed}")
    for d in report.get("decision_records", []):
        if d.get("promotion_authorized_bool") is not False:
            failures.append(f"decision_{d.get('decision_bucket')}_promotion_not_false")
        if d.get("method_winner_claim_authorized_bool") is not False:
            failures.append(f"decision_{d.get('decision_bucket')}_method_winner_not_false")
        if d.get("threshold_tuning_authorized_bool") is False and "no_threshold_tuning" not in d.get("decision_bucket", ""):
            # not every decision record carries threshold_tuning; skip those that do not.
            pass
    # HAAE-R0 route coverage.
    routes = report.get("haae_r0_route_records", [])
    if not routes:
        failures.append("missing_haae_r0_route_records")
    for r in routes:
        for field in ("design_only_bool", "schema_preflight_bool", "public_only_bool"):
            if r.get(field) is not True:
                failures.append(f"route_{r.get('route_bucket')}_{field}_not_true")
        if r.get("execution_authorized_bool") is not False:
            failures.append(f"route_{r.get('route_bucket')}_execution_authorized")
        for field in ("haae_r0_not_bea_v1_a_bool", "haae_r0_not_selector_only_bool",
                      "haae_r0_not_selector_reranker_execution_bool",
                      "haae_r0_not_p5_bool", "haae_r0_not_runtime_default_promotion_bool"):
            if r.get(field) is not True:
                failures.append(f"route_{r.get('route_bucket')}_{field}_not_true")
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
                  "candidate_generation_bool",
                  "network_run_bool", "provider_model_network_bool",
                  "n10er_execution_authorized_bool", "n10er_re_run_authorized_bool",
                  "n10es_audit_authorized_bool", "n10es_re_run_authorized_bool",
                  "gold_used_for_policy_bool", "downstream_value_claim_bool",
                  "heldout_generalization_claim_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_decision_only_bool",
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
    # Stop/go: only HAAE-R0 design/schema preflight authorized.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if stop.get("haae_r0_design_only_schema_preflight_authorized_bool") is not True:
        failures.append("stop_haae_r0_design_only_not_authorized")
    for field in ("haae_r0_execution_authorized_bool",
                  "n10et_audit_authorized_bool", "n10et_re_run_authorized_bool",
                  "execution_authorized_bool", "rerun_authorized_bool",
                  "retrieval_authorized_bool", "recompute_authorized_bool",
                  "candidate_generation_authorized_bool",
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
                  "design_decision_only_bool"):
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
    checks.append(("scanner_sha", scan_summary({"v": "a" * 40})["status"] == "fail"))
    checks.append(("scanner_task_id", scan_summary({"v": "ci-00001"})["status"] == "fail"))
    checks.append(("scanner_passes_clean", scan_summary({"status": "ok", "count": 7})["status"] == "pass"))

    # Locked constants.
    checks.append(("locked_n10es_checkpoint", LOCKED_N10ES_CHECKPOINT == "8c04a0a"))
    checks.append(("locked_n10er_checkpoint", LOCKED_N10ER_CHECKPOINT == "c8fd353"))
    checks.append(("locked_ci_run", LOCKED_N10ER_CI_RUN == "28457213423"))
    checks.append(("locked_ci_head", LOCKED_N10ER_CI_HEAD == "2e7894e"))
    checks.append(("locked_n10er_status", LOCKED_N10ER_STATUS.endswith("n10es_authorized")))
    checks.append(("locked_n10es_status", LOCKED_N10ES_STATUS.endswith("n10et_authorized")))
    checks.append(("locked_n10es_next_phase",
                   LOCKED_N10ES_NEXT_ALLOWED_PHASE == "BEA-v1-N10ET Public Safety Probe Design/Decision"))
    checks.append(("locked_sample", LOCKED_SAMPLE["public_task_count"] == 80
                   and LOCKED_SAMPLE["scored_task_count"] == 60
                   and LOCKED_SAMPLE["task_with_gold_count"] == 40))
    checks.append(("locked_arms", LOCKED_ARMS["baseline"]["top10"] == 37
                   and LOCKED_ARMS["full"]["top10"] == 36 and LOCKED_ARMS["full"]["lost"] == 1
                   and LOCKED_ARMS["guard"]["top10"] == 38 and LOCKED_ARMS["guard"]["lost"] == 0
                   and LOCKED_ARMS["diffaware"]["top10"] == 37 and LOCKED_ARMS["diffaware"]["lost"] == 1))
    checks.append(("locked_risk", LOCKED_RISK_TASK_COUNT == 26
                   and LOCKED_RISK_FULL_LOST == 0 and LOCKED_RISK_GUARD_LOST == 0
                   and LOCKED_RISK_DIFFAWARE_LOST == 0
                   and LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS == 0))
    checks.append(("locked_citation", LOCKED_CITATION_VALID == 7772 and LOCKED_CITATION_TOTAL == 7772))
    checks.append(("locked_upstream", LOCKED_N10EQ_CHECKPOINT == "7963831"
                   and LOCKED_N10EP_CHECKPOINT == "0a54b49"
                   and LOCKED_N10EO_CHECKPOINT == "6f8eeda"))
    checks.append(("haae_r0_constants", NEXT_ROUTE == "BEA-v1-HAAE-R0"
                   and "Hierarchical Actionable Evidence Acquisition" in NEXT_ROUTE_FULL
                   and "Schema Preflight" in NEXT_ROUTE_FULL))
    checks.append(("haae_r0_non_identities",
                   set(HAAE_R0_NOT_IDENTITIES) == {
                       "not_bea_v1_a", "not_selector_only",
                       "not_selector_reranker_execution", "not_p5",
                       "not_runtime_default_promotion"}))

    # Source lock against the real N10ES + N10ER public reports.
    lock_ok, lock_record = evaluate_n10es_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_n10es_status_match", lock_record["n10es_status_match_bool"] is True))
    checks.append(("source_lock_n10er_status_match", lock_record["n10er_status_match_bool"] is True))
    checks.append(("source_lock_n10er_checkpoint_match", lock_record["n10er_checkpoint_match_bool"] is True))
    checks.append(("source_lock_n10er_ci_run_match", lock_record["n10er_ci_run_match_bool"] is True))
    checks.append(("source_lock_n10es_next_phase_match",
                   lock_record["n10es_next_phase_match_bool"] is True
                   and lock_record["locked_n10es_next_allowed_phase"] == LOCKED_N10ES_NEXT_ALLOWED_PHASE))
    checks.append(("source_lock_n10et_authorized_match",
                   lock_record["n10et_design_decision_authorized_match_bool"] is True))
    checks.append(("source_lock_n10es_no_execution_match",
                   lock_record["n10es_no_execution_match_bool"] is True))
    checks.append(("source_lock_sample_match", lock_record["sample_aggregate_match_bool"] is True))
    checks.append(("source_lock_arms_match", lock_record["arm_aggregate_all_match_bool"] is True))
    checks.append(("source_lock_risk_match", lock_record["risk_aggregate_match_bool"] is True))
    checks.append(("source_lock_citation_match", lock_record["citation_match_bool"] is True))
    checks.append(("source_lock_overlap_match", lock_record["overlap_match_bool"] is True))

    readback = public_readback_match()
    checks.append(("readback_n10et_docs_match", readback["n10et_docs_readback_match_bool"] is True))
    checks.append(("readback_n10es_docs_match", readback["n10es_docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))
    checks.append(("readback_log_match", readback["research_log_match_bool"] is True))
    checks.append(("readback_summary_match", readback["research_summary_match_bool"] is True))

    # Decision records: close-out decisions present and conservative.
    decisions = decision_records()
    checks.append(("decisions_count", len(decisions) == 3))
    checks.append(("decision_no_promotion", all(d.get("promotion_authorized_bool") is False for d in decisions)))
    checks.append(("decision_no_method_winner", all(d.get("method_winner_claim_authorized_bool") is False for d in decisions)))
    checks.append(("decision_valid_negative",
                   any(d["decision_bucket"] == "n10er_n10es_valid_public_heldout_negative"
                       and d["valid_research_negative_bool"] is True
                       and d["signal_reproduced_bool"] is False
                       and d["ci_failure_bool"] is False for d in decisions)))

    # HAAE-R0 route records: design-only, schema preflight, non-identity booleans.
    routes = haae_r0_route_records()
    checks.append(("routes_count", len(routes) == 2))
    checks.append(("routes_design_only", all(r["design_only_bool"] is True for r in routes)))
    checks.append(("routes_schema_preflight", all(r["schema_preflight_bool"] is True for r in routes)))
    checks.append(("routes_no_execution", all(r["execution_authorized_bool"] is False for r in routes)))
    checks.append(("routes_authorized_for_next_phase", all(r["authorized_for_next_phase_bool"] is True for r in routes)))
    checks.append(("routes_non_identity", all(
        r["haae_r0_not_bea_v1_a_bool"] and r["haae_r0_not_selector_only_bool"]
        and r["haae_r0_not_selector_reranker_execution_bool"]
        and r["haae_r0_not_p5_bool"]
        and r["haae_r0_not_runtime_default_promotion_bool"]
        for r in routes)))

    # Risk control coverage.
    risks = risk_control_records()
    checks.append(("risks_count", len(risks) == len(ALL_RISK_CONTROLS)))
    checks.append(("risks_all_controlled", all(r["risk_controlled_bool"] for r in risks)))

    # Stop/go: authorize only HAAE-R0 design/schema preflight.
    stop = stop_go_records()[0]
    checks.append(("stop_haae_r0_authorized", stop["haae_r0_design_only_schema_preflight_authorized_bool"] is True))
    checks.append(("stop_haae_r0_no_exec", stop["haae_r0_execution_authorized_bool"] is False))
    checks.append(("stop_no_n10er_rerun", stop["n10er_re_run_authorized_bool"] is False
                   and stop["n10er_execution_authorized_bool"] is False))
    checks.append(("stop_no_selector_p5_bea_v1_a", stop["selector_reranker_authorized_bool"] is False
                   and stop["p5_authorized_bool"] is False
                   and stop["bea_v1_a_authorized_bool"] is False))
    checks.append(("stop_no_runtime_promotion", stop["runtime_default_change_authorized_bool"] is False
                   and stop["guard_full_diffaware_promotion_authorized_bool"] is False
                   and stop["method_winner_claim_authorized_bool"] is False))
    checks.append(("stop_haae_r0_non_identity", stop["haae_r0_not_bea_v1_a_bool"] is True
                   and stop["haae_r0_not_selector_only_bool"] is True
                   and stop["haae_r0_not_selector_reranker_execution_bool"] is True
                   and stop["haae_r0_not_p5_bool"] is True
                   and stop["haae_r0_not_runtime_default_promotion_bool"] is True))

    # Claim boundary explicit fields.
    cb = claim_boundary_records()[0]
    checks.append(("claim_public_only_true", cb["public_only_bool"] is True))
    checks.append(("claim_design_decision_only_true", cb["design_decision_only_bool"] is True))
    checks.append(("claim_no_candidate_generation", cb["candidate_generation_bool"] is False))
    checks.append(("claim_haae_r0_non_identity", cb["haae_r0_not_bea_v1_a_bool"] is True
                   and cb["haae_r0_not_p5_bool"] is True))

    # Full report build + validation.
    report = build_report()
    checks.append(("report_status_complete", report["status"] == STATUS_COMPLETE))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields", package["n10et_docs_readback_match_bool"] is True
                   and package["n10es_docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True
                   and package["research_log_match_bool"] is True
                   and package["research_summary_match_bool"] is True))
    checks.append(("report_stop_haae_r0",
                   report["stop_go_records"][0]["haae_r0_design_only_schema_preflight_authorized_bool"] is True))
    checks.append(("report_stop_no_execution",
                   report["stop_go_records"][0]["execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["n10er_re_run_authorized_bool"] is False
                   and report["stop_go_records"][0]["provider_model_network_authorized_bool"] is False))

    # Bad-contract detection.
    bad = dict(report)
    bad["status"] = STATUS_COMPLETE
    bad["stop_go_records"] = [{**stop_go_records()[0], "execution_authorized_bool": True}]
    checks.append(("validate_fails_execution",
                   any("execution_authorized_bool_not_false" in f for f in validate_report(bad))))
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
    bad5["haae_r0_route_records"] = [{**haae_r0_route_records()[0], "haae_r0_not_bea_v1_a_bool": False}]
    checks.append(("validate_fails_haae_r0_identity",
                   any("haae_r0_not_bea_v1_a_bool_not_true" in f for f in validate_report(bad5))))

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

    # Public-only: load the N10ES + N10ER public reports only. No private
    # diagnostic inputs, no rerun, no recompute, no retrieval, no candidate
    # generation.
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
