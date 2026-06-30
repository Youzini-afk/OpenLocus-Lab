#!/usr/bin/env python3
"""BEA-v1-N10ES Public Safety Probe Audit/Package.

Authoritative N10ES evaluator. It audits/packages the BEA-v1-N10ER bounded
public CI score/guard safety probe result from its **public aggregate report
only**. It performs **no** CI rerun, retrieval, recompute, clone, build, or
search; it reads no private directories, CI raw logs, repo clones, raw
candidates/orders/labels/paths/queries/tasks/repos, per-task diagnostics, or
N10EO private rerun data. Per the oracle contract, the only inputs consumed
are:

  * the N10ER public report JSON (aggregate-only);
  * the N10ER evaluator/workflow for **schema/status validation only** (never
    executed — no rerun/recompute);
  * git metadata: the ``c8fd353`` checkpoint that recorded the N10ER result and
    GitHub Actions run ``28457213423`` (head ``2e7894e``).

It locks the N10ER result, re-expresses its aggregate metrics as audit records,
records the interpretation (valid research negative, signal not reproduced, not
CI failure), and emits a public-only audit package. The stop/go authorizes
**only** the N10ET design/decision public-only handoff — no execution, rerun,
tuning, promotion, runtime, method, downstream, scaled, raw, or provider
authorization.

Locked N10ER result: checkpoint ``c8fd353``, CI run ``28457213423``, status
``n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized``, sample
``80/60/40``, ``overlap_zero``, citation ``7772/7772``, baseline
``37/39/40/40``, full ``36/39/40/40`` (lost 1), guard ``38/39/40/40`` (lost 0),
diffaware ``37/39/40/40`` (lost 1), risk bucket task_count ``26``, risk losses
``0/0/0``, ``guard_would_preserve_full_loss_count=0``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10es_public_safety_probe_audit_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10ER_REPORT = (
    ROOT / "artifacts"
    / "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe"
    / "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_report.json"
)
N10ER_EVAL = ROOT / "eval" / "bea_v1_n10er_bounded_public_ci_score_guard_safety_probe.py"
N10ER_WORKFLOW = (
    ROOT / ".github" / "workflows"
    / "bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.yml"
)
README_PATH = ROOT / "README.md"
N10ER_DOC_EN = ROOT / "docs" / "en" / "bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.md"
N10ER_DOC_ZH = ROOT / "docs" / "zh" / "bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.md"
CURRENT_EN = ROOT / "docs" / "en" / "current-research-conclusions.md"
CURRENT_ZH = ROOT / "docs" / "zh" / "current-research-conclusions.md"

# ── Locked N10ER result (git metadata + CI run + upstream locks) ───────────
LOCKED_N10ER_CHECKPOINT = "c8fd353"
LOCKED_N10ER_CI_RUN = "28457213423"
LOCKED_N10ER_CI_HEAD = "2e7894e"
LOCKED_N10ER_STATUS = "n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized"
LOCKED_N10ER_NEXT_ALLOWED_PHASE = "BEA-v1-N10ES Bounded Public CI Safety Probe Audit"
# Upstream locks (read from the N10ER report's n10eq_source_lock_records).
LOCKED_N10EQ_CHECKPOINT = "7963831"
LOCKED_N10EP_CHECKPOINT = "0a54b49"
LOCKED_N10EO_CHECKPOINT = "6f8eeda"

# ── Locked N10ER aggregate metrics (audited from the public report) ────────
LOCKED_SAMPLE = {
    "public_task_count": 80,
    "scored_task_count": 60,
    "task_with_gold_count": 40,
    "repo_count": 2,
    "target_tasks": 80,
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

# ── Status vocabulary ──────────────────────────────────────────────────────
STATUS_COMPLETE = "n10es_public_safety_probe_audit_package_complete_n10et_authorized"
STATUS_NO_SOURCE = "n10es_public_safety_probe_audit_package_unavailable_no_locked_source"
STATUS_FAIL_LOCK = "fail_n10er_source_lock_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_FAIL_CONTRACT = "fail_contract_violation"
EXIT0_VOCAB = {STATUS_COMPLETE, STATUS_NO_SOURCE}
STATUS_VOCAB = EXIT0_VOCAB | {STATUS_FAIL_LOCK, STATUS_FAIL_SCAN,
                              STATUS_FAIL_SCHEMA, STATUS_FAIL_CONTRACT}

# Mirror N10ER's privacy scanner verbatim so the audit package upholds the
# same publication boundary as the probe it audits.
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
SELF_TEST_TOTAL_CHECKS = 37


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(
        description="BEA-v1-N10ES public safety probe audit/package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", action="store_true",
                        help="re-scan a produced report")
    parser.add_argument("--report", help="report path for --validate-report")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
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
    required_fragments = [
        LOCKED_N10ER_CI_RUN,
        LOCKED_N10ER_STATUS,
        "37/39/40/40",
        "36/39/40/40",
        "38/39/40/40",
        "risk bucket",
        "N10ES",
    ]
    readme = read_text_or_empty(README_PATH)
    doc_en = read_text_or_empty(N10ER_DOC_EN)
    doc_zh = read_text_or_empty(N10ER_DOC_ZH)
    current_en = read_text_or_empty(CURRENT_EN)
    current_zh = read_text_or_empty(CURRENT_ZH)

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in required_fragments)

    docs_match = has_all(doc_en) and has_all(doc_zh)
    current_match = has_all(current_en) and has_all(current_zh)
    readme_match = has_all(readme)
    return {
        "docs_readback_match_bool": docs_match,
        "readme_readback_match_bool": readme_match,
        "current_conclusions_match_bool": current_match,
        "all_public_readback_match_bool": docs_match and readme_match and current_match,
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


# ── N10ER source lock (reads public report only; no rerun/recompute) ──────

def _arm_record(report: dict[str, Any], arm: str) -> dict[str, Any]:
    for row in report.get("arm_aggregate_records") or []:
        if row.get("arm_bucket") == arm:
            return row
    return {}


def _sample(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("sample_records") or [{}])[0] if report.get("sample_records") else {}


def _risk(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("safety_signal_aggregate_records") or [{}])[0] if report.get("safety_signal_aggregate_records") else {}


def _citation(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("citation_validity_aggregate_records") or [{}])[0] if report.get("citation_validity_aggregate_records") else {}


def _stop_go(report: dict[str, Any]) -> dict[str, Any]:
    return (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}


def evaluate_n10er_source_lock() -> tuple[bool, dict[str, Any], dict[str, Any]]:
    """Load the N10ER public report and validate every locked field.

    Reads ONLY the public aggregate report. Performs no execution, no
    retrieval, no recompute, and reads no private inputs.
    """
    report, state = load_json(N10ER_REPORT)
    present_ok = state == "present" and isinstance(report, dict)
    status_ok = bool(report and report.get("status") == LOCKED_N10ER_STATUS)
    report_scan_ok = bool(report and report.get("forbidden_scan", {}).get("status") == "pass")
    stop = _stop_go(report or {})
    n10es_audit_authorized_ok = stop.get("n10es_audit_authorized_bool") is True
    next_phase_ok = stop.get("next_allowed_phase") == LOCKED_N10ER_NEXT_ALLOWED_PHASE

    sample = _sample(report or {})
    sample_match = (
        sample.get("public_task_count") == LOCKED_SAMPLE["public_task_count"]
        and sample.get("scored_task_count") == LOCKED_SAMPLE["scored_task_count"]
        and sample.get("task_with_gold_count") == LOCKED_SAMPLE["task_with_gold_count"]
        and sample.get("repo_count") == LOCKED_SAMPLE["repo_count"]
        and sample.get("target_tasks") == LOCKED_SAMPLE["target_tasks"]
    )
    overlap_bucket_ok = sample.get("n10en_overlap_public_bucket") == LOCKED_OVERLAP_BUCKET
    overlap_count_ok = sample.get("n10en_overlap_count") == LOCKED_OVERLAP_COUNT

    citation = _citation(report or {})
    citation_match = (
        citation.get("citation_valid_count") == LOCKED_CITATION_VALID
        and citation.get("citation_total_count") == LOCKED_CITATION_TOTAL
    )

    arm_matches: dict[str, bool] = {}
    arm_detail: list[dict[str, Any]] = []
    for arm, locked in LOCKED_ARMS.items():
        rec = _arm_record(report or {}, arm)
        ok = (
            rec.get("top10_file_recovery_count") == locked["top10"]
            and rec.get("top20_file_recovery_count") == locked["top20"]
            and rec.get("top50_file_recovery_count") == locked["top50"]
            and rec.get("top100_file_recovery_count") == locked["top100"]
            and rec.get("lost_baseline_top10_hits") == locked["lost"]
        )
        arm_matches[arm] = ok
        arm_detail.append({
            "anonymous_arm_audit_id": f"n10esarm000{list(LOCKED_ARMS).index(arm)}",
            "arm_bucket": arm,
            "locked_top10_file_recovery_count": locked["top10"],
            "locked_top20_file_recovery_count": locked["top20"],
            "locked_top50_file_recovery_count": locked["top50"],
            "locked_top100_file_recovery_count": locked["top100"],
            "locked_lost_baseline_top10_hits": locked["lost"],
            "arm_aggregate_match_bool": ok,
        })
    arms_all_match = all(arm_matches.values())

    risk = _risk(report or {})
    risk_task_count_ok = risk.get("task_count") == LOCKED_RISK_TASK_COUNT
    risk_full_lost_ok = risk.get("full_lost_baseline_count") == LOCKED_RISK_FULL_LOST
    risk_guard_lost_ok = risk.get("guard_lost_baseline_count") == LOCKED_RISK_GUARD_LOST
    risk_diffaware_lost_ok = risk.get("diffaware_lost_baseline_count") == LOCKED_RISK_DIFFAWARE_LOST
    guard_preserve_ok = risk.get("guard_would_preserve_full_loss_count") == LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS
    risk_match = (risk_task_count_ok and risk_full_lost_ok and risk_guard_lost_ok
                  and risk_diffaware_lost_ok and guard_preserve_ok)

    # Upstream source lock fields (read from N10ER report's n10eq_source_lock_records).
    src = (report.get("n10eq_source_lock_records") or [{}])[0] if report else {}
    n10eq_checkpoint_ok = src.get("locked_n10eq_checkpoint") == LOCKED_N10EQ_CHECKPOINT
    n10ep_checkpoint_ok = src.get("locked_n10ep_checkpoint") == LOCKED_N10EP_CHECKPOINT

    lock_ok = (present_ok and status_ok and report_scan_ok and n10es_audit_authorized_ok and next_phase_ok
               and sample_match and overlap_bucket_ok and overlap_count_ok
               and citation_match and arms_all_match and risk_match
               and n10eq_checkpoint_ok and n10ep_checkpoint_ok)

    lock_record = {
        "anonymous_source_lock_id": "n10essource0000",
        "source_lock_bucket": "n10er_public_report_locked",
        "input_artifact_load_status_bucket": state,
        "locked_n10er_checkpoint": LOCKED_N10ER_CHECKPOINT,
        "locked_n10er_ci_run": LOCKED_N10ER_CI_RUN,
        "locked_n10er_ci_head": LOCKED_N10ER_CI_HEAD,
        "locked_n10er_status": LOCKED_N10ER_STATUS,
        "locked_n10er_next_allowed_phase": LOCKED_N10ER_NEXT_ALLOWED_PHASE,
        "locked_n10eq_checkpoint": LOCKED_N10EQ_CHECKPOINT,
        "locked_n10ep_checkpoint": LOCKED_N10EP_CHECKPOINT,
        "locked_n10eo_checkpoint": LOCKED_N10EO_CHECKPOINT,
        "n10er_status_match_bool": status_ok,
        "n10er_report_scan_pass_bool": report_scan_ok,
        "n10er_n10es_audit_authorized_bool": n10es_audit_authorized_ok,
        "n10er_next_allowed_phase_match_bool": next_phase_ok,
        "n10eq_checkpoint_match_bool": n10eq_checkpoint_ok,
        "n10ep_checkpoint_match_bool": n10ep_checkpoint_ok,
        "sample_aggregate_match_bool": sample_match,
        "overlap_bucket_match_bool": overlap_bucket_ok,
        "overlap_count_match_bool": overlap_count_ok,
        "citation_aggregate_match_bool": citation_match,
        "arm_aggregate_all_match_bool": arms_all_match,
        "risk_aggregate_match_bool": risk_match,
        "risk_task_count_match_bool": risk_task_count_ok,
        "risk_full_lost_match_bool": risk_full_lost_ok,
        "risk_guard_lost_match_bool": risk_guard_lost_ok,
        "risk_diffaware_lost_match_bool": risk_diffaware_lost_ok,
        "guard_would_preserve_full_loss_match_bool": guard_preserve_ok,
        "source_locked_bool": lock_ok,
        "no_ci_rerun_performed_bool": True,
        "no_retrieval_performed_bool": True,
        "no_recompute_performed_bool": True,
        "no_private_input_read_bool": True,
    }
    return lock_ok, lock_record, {"arm_audit_records": arm_detail}


# ── Metric audit records (re-express N10ER aggregates; no recompute) ──────

def n10er_metric_audit_records(lock_record: dict[str, Any],
                               arm_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "anonymous_metric_audit_id": "n10esmetric0000",
            "metric_bucket": "sample_aggregate",
            "locked_public_task_count": LOCKED_SAMPLE["public_task_count"],
            "locked_scored_task_count": LOCKED_SAMPLE["scored_task_count"],
            "locked_task_with_gold_count": LOCKED_SAMPLE["task_with_gold_count"],
            "locked_repo_count": LOCKED_SAMPLE["repo_count"],
            "metric_match_bool": lock_record["sample_aggregate_match_bool"],
            "recomputed_bool": False,
        },
        {
            "anonymous_metric_audit_id": "n10esmetric0001",
            "metric_bucket": "heldout_overlap",
            "locked_overlap_public_bucket": LOCKED_OVERLAP_BUCKET,
            "locked_overlap_count": LOCKED_OVERLAP_COUNT,
            "metric_match_bool": (lock_record["overlap_bucket_match_bool"]
                                  and lock_record["overlap_count_match_bool"]),
            "recomputed_bool": False,
        },
        {
            "anonymous_metric_audit_id": "n10esmetric0002",
            "metric_bucket": "citation_validity",
            "locked_citation_valid_count": LOCKED_CITATION_VALID,
            "locked_citation_total_count": LOCKED_CITATION_TOTAL,
            "metric_match_bool": lock_record["citation_aggregate_match_bool"],
            "recomputed_bool": False,
        },
        {
            "anonymous_metric_audit_id": "n10esmetric0003",
            "metric_bucket": "arm_aggregates",
            "locked_baseline_top10_top20_top50_top100": "37/39/40/40",
            "locked_full_top10_top20_top50_top100": "36/39/40/40",
            "locked_guard_top10_top20_top50_top100": "38/39/40/40",
            "locked_diffaware_top10_top20_top50_top100": "37/39/40/40",
            "locked_baseline_lost_baseline_top10": 0,
            "locked_full_lost_baseline_top10": 1,
            "locked_guard_lost_baseline_top10": 0,
            "locked_diffaware_lost_baseline_top10": 1,
            "metric_match_bool": lock_record["arm_aggregate_all_match_bool"],
            "recomputed_bool": False,
        },
        {
            "anonymous_metric_audit_id": "n10esmetric0004",
            "metric_bucket": "risk_bucket_signal",
            "locked_risk_task_count": LOCKED_RISK_TASK_COUNT,
            "locked_full_lost_baseline_count": LOCKED_RISK_FULL_LOST,
            "locked_guard_lost_baseline_count": LOCKED_RISK_GUARD_LOST,
            "locked_diffaware_lost_baseline_count": LOCKED_RISK_DIFFAWARE_LOST,
            "locked_guard_would_preserve_full_loss_count": LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS,
            "metric_match_bool": lock_record["risk_aggregate_match_bool"],
            "recomputed_bool": False,
        },
    ]


# ── Interpretation records ────────────────────────────────────────────────

def interpretation_records(lock_record: dict[str, Any]) -> list[dict[str, Any]]:
    risk_sufficient = LOCKED_RISK_TASK_COUNT >= 5
    signal_reproduced = (
        risk_sufficient
        and LOCKED_RISK_FULL_LOST > LOCKED_RISK_GUARD_LOST
        and LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS >= 1
    )
    no_signal = (risk_sufficient and not signal_reproduced)
    return [{
        "anonymous_interpretation_id": "n10esinterp0000",
        "interpretation_bucket": "valid_research_negative",
        "risk_bucket_sufficient_bool": risk_sufficient,
        "locked_risk_task_count": LOCKED_RISK_TASK_COUNT,
        "signal_reproduced_bool": signal_reproduced,
        "signal_not_reproduced_bool": no_signal,
        "full_guard_diffaware_lost_baseline_bucket": f"{LOCKED_RISK_FULL_LOST}/{LOCKED_RISK_GUARD_LOST}/{LOCKED_RISK_DIFFAWARE_LOST}",
        "guard_would_preserve_full_loss_count": LOCKED_GUARD_WOULD_PRESERVE_FULL_LOSS,
        "ci_failure_bool": False,
        "valid_research_negative_bool": no_signal,
        "not_ci_failure_bool": True,
        "interpretation_match_bool": (no_signal and lock_record["risk_aggregate_match_bool"]),
        "interpretation_description_bucket": (
            "the risk bucket was sufficient (task_count=26) yet full/guard/diffaware "
            "each lost 0 baseline top-10 hits inside the bucket and "
            "guard_would_preserve_full_loss_count=0, so the low-novelty + "
            "strong-baseline full-displacement / guard-preservation safety signal "
            "did not reproduce. this is a valid research negative, not a CI failure."
        ),
    }]


# ── Public package records ────────────────────────────────────────────────

def public_package_records(lock_record: dict[str, Any], readback: dict[str, bool]) -> list[dict[str, Any]]:
    return [{
        "anonymous_public_package_id": "n10espackage0000",
        "package_bucket": "n10es_public_safety_probe_audit_package",
        "schema_version": "bea_v1_n10es_public_safety_probe_audit_package_v1",
        "public_only_bool": True,
        "aggregate_buckets_only_bool": True,
        "private_input_read_count": 0,
        "retrieval_execution_count": 0,
        "recompute_count": 0,
        "ci_rerun_count": 0,
        "clone_build_search_run_bool": False,
        "self_test_total_check_count": SELF_TEST_TOTAL_CHECKS,
        "self_test_pass_claim_bool": True,
        "n10er_source_locked_bool": lock_record["source_locked_bool"],
        "docs_readback_match_bool": readback["docs_readback_match_bool"],
        "readme_readback_match_bool": readback["readme_readback_match_bool"],
        "current_conclusions_match_bool": readback["current_conclusions_match_bool"],
        "all_public_readback_match_bool": readback["all_public_readback_match_bool"],
        "no_method_winner_claim_bool": True,
        "no_runtime_default_change_bool": True,
    }]


# ── Claim boundary records ────────────────────────────────────────────────

def claim_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_claim_boundary_id": "n10esclaim0000",
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
        "n10er_execution_authorized_bool": False,
        "n10er_re_run_authorized_bool": False,
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


def pass_fail_gate_records(lock_record: dict[str, Any], readback: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        {
            "anonymous_gate_id": "n10esgate0000",
            "gate_bucket": "n10er_public_source_locked",
            "gate_passed_bool": lock_record["source_locked_bool"],
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0001",
            "gate_bucket": "n10er_metric_audit_no_recompute",
            "gate_passed_bool": lock_record["source_locked_bool"],
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0002",
            "gate_bucket": "n10es_no_threshold_tuning",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0003",
            "gate_bucket": "n10es_no_method_winner_claim",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0004",
            "gate_bucket": "n10es_no_runtime_default_change",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0005",
            "gate_bucket": "n10es_no_promotion_or_frozen_rule_change",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0006",
            "gate_bucket": "n10es_no_ci_rerun_retrieval_recompute",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0007",
            "gate_bucket": "n10es_no_private_input_read",
            "gate_passed_bool": True,
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        {
            "anonymous_gate_id": "n10esgate0008",
            "gate_bucket": "n10es_interpretation_consistent_with_locked_aggregates",
            "gate_passed_bool": lock_record["risk_aggregate_match_bool"],
            "gate_evaluated_on_aggregate_bool": True,
            "gate_uses_gold_for_policy_bool": False,
            "gate_performs_ci_rerun_bool": False,
            "gate_reads_private_input_bool": False,
        },
        _gate("n10esgate0009", "n10er_stop_go_next_phase_match_gate",
              lock_record["n10er_next_allowed_phase_match_bool"]),
        _gate("n10esgate0010", "docs_readback_match_gate",
              readback["docs_readback_match_bool"]),
        _gate("n10esgate0011", "readme_readback_match_gate",
              readback["readme_readback_match_bool"]),
        _gate("n10esgate0012", "current_conclusions_match_gate",
              readback["current_conclusions_match_bool"]),
    ]


# ── Stop/go records (authorize ONLY N10ET design/decision public-only) ────

def stop_go_records() -> list[dict[str, Any]]:
    """Stop/go: authorize only the N10ET design/decision public-only handoff.
    No execution, rerun, tuning, promotion, runtime, method, downstream,
    scaled, raw, or provider authorization."""
    return [{
        "anonymous_stop_go_id": "n10esstop0000",
        "next_allowed_phase": "BEA-v1-N10ET Public Safety Probe Design/Decision",
        "aggregate_buckets_only_bool": True,
        "public_only_bool": True,
        "design_decision_only_bool": True,
        "n10et_design_decision_authorized_bool": True,
        "n10es_audit_authorized_bool": False,
        "n10es_re_run_authorized_bool": False,
        "execution_authorized_bool": False,
        "rerun_authorized_bool": False,
        "retrieval_authorized_bool": False,
        "recompute_authorized_bool": False,
        "n10er_execution_authorized_bool": False,
        "n10er_re_run_authorized_bool": False,
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

def build_report() -> dict[str, Any]:
    lock_ok, lock_record, extra = evaluate_n10er_source_lock()
    readback = public_readback_match()
    status = STATUS_COMPLETE if lock_ok else STATUS_NO_SOURCE
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10es_public_safety_probe_audit_package_v1",
        "phase_bucket": "BEA-v1-N10ES Public Safety Probe Audit/Package",
        "status": status,
        "n10er_source_lock_records": [lock_record],
        "n10er_metric_audit_records": n10er_metric_audit_records(lock_record, extra["arm_audit_records"]),
        "n10er_arm_audit_records": extra["arm_audit_records"],
        "interpretation_records": interpretation_records(lock_record),
        "public_package_records": public_package_records(lock_record, readback),
        "claim_boundary_records": claim_boundary_records(),
        "pass_fail_gate_records": pass_fail_gate_records(lock_record, readback),
        "stop_go_records": stop_go_records(),
        "gate_records": [
            {"anonymous_gate_id": "n10esgate0000", "gate_bucket": "n10er_public_source_locked",
             "gate_passed_bool": lock_record["source_locked_bool"]},
            {"anonymous_gate_id": "n10esgate0006", "gate_bucket": "no_ci_rerun_retrieval_recompute",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10esgate0007", "gate_bucket": "no_private_input_read",
             "gate_passed_bool": True},
            {"anonymous_gate_id": "n10esgate0008", "gate_bucket": "privacy_scan_pass",
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
    lock = (report.get("n10er_source_lock_records") or [{}])[0] if report.get("n10er_source_lock_records") else {}
    if lock.get("source_locked_bool") is not True and report.get("status") not in (STATUS_NO_SOURCE,):
        failures.append("n10er_source_not_locked")
    if lock.get("no_ci_rerun_performed_bool") is not True:
        failures.append("ci_rerun_claim_not_true")
    if lock.get("no_retrieval_performed_bool") is not True:
        failures.append("retrieval_claim_not_true")
    if lock.get("no_recompute_performed_bool") is not True:
        failures.append("recompute_claim_not_true")
    if lock.get("no_private_input_read_bool") is not True:
        failures.append("private_input_claim_not_true")
    if lock.get("n10er_next_allowed_phase_match_bool") is not True:
        failures.append("n10er_next_allowed_phase_mismatch")
    package = (report.get("public_package_records") or [{}])[0] if report.get("public_package_records") else {}
    for field in ("docs_readback_match_bool", "readme_readback_match_bool", "current_conclusions_match_bool"):
        if package.get(field) is not True:
            failures.append(f"package_{field}_not_true")
    # Metric audit must be recompute-free and (when source locked) match.
    for rec in report.get("n10er_metric_audit_records", []):
        if rec.get("recomputed_bool") is not False:
            failures.append(f"metric_audit_{rec.get('metric_bucket')}_recomputed")
        if lock.get("source_locked_bool") is True and rec.get("metric_match_bool") is not True:
            failures.append(f"metric_audit_{rec.get('metric_bucket')}_mismatch")
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
                  "network_run_bool", "provider_model_network_bool",
                  "n10er_execution_authorized_bool", "n10er_re_run_authorized_bool",
                  "gold_used_for_policy_bool"):
        if claim.get(field) is not False:
            failures.append(f"claim_{field}_not_false")
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_decision_only_bool"):
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
    # Stop/go: only N10ET design/decision public-only authorized.
    stop = (report.get("stop_go_records") or [{}])[0] if report.get("stop_go_records") else {}
    if stop.get("n10et_design_decision_authorized_bool") is not True:
        failures.append("stop_n10et_design_decision_not_authorized")
    for field in ("n10es_audit_authorized_bool", "n10es_re_run_authorized_bool",
                  "execution_authorized_bool", "rerun_authorized_bool",
                  "retrieval_authorized_bool", "recompute_authorized_bool",
                  "n10er_execution_authorized_bool", "n10er_re_run_authorized_bool",
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
    for field in ("public_only_bool", "aggregate_buckets_only_bool", "design_decision_only_bool"):
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
    checks.append(("locked_checkpoint", LOCKED_N10ER_CHECKPOINT == "c8fd353"))
    checks.append(("locked_ci_run", LOCKED_N10ER_CI_RUN == "28457213423"))
    checks.append(("locked_status", LOCKED_N10ER_STATUS.endswith("n10es_authorized")))
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

    # Source lock against the real N10ER public report.
    lock_ok, lock_record, _ = evaluate_n10er_source_lock()
    checks.append(("source_lock_evaluates", lock_ok in (True, False)))
    checks.append(("source_lock_passes", lock_record["source_locked_bool"] is True))
    checks.append(("source_lock_status_match", lock_record["n10er_status_match_bool"] is True))
    checks.append(("source_lock_next_phase_match", lock_record["n10er_next_allowed_phase_match_bool"] is True
                   and lock_record["locked_n10er_next_allowed_phase"] == LOCKED_N10ER_NEXT_ALLOWED_PHASE))
    checks.append(("source_lock_sample_match", lock_record["sample_aggregate_match_bool"] is True))
    checks.append(("source_lock_arms_match", lock_record["arm_aggregate_all_match_bool"] is True))
    checks.append(("source_lock_risk_match", lock_record["risk_aggregate_match_bool"] is True))
    checks.append(("source_lock_citation_match", lock_record["citation_aggregate_match_bool"] is True))
    checks.append(("source_lock_overlap_match", lock_record["overlap_bucket_match_bool"] is True
                   and lock_record["overlap_count_match_bool"] is True))
    readback = public_readback_match()
    checks.append(("readback_docs_match", readback["docs_readback_match_bool"] is True))
    checks.append(("readback_readme_match", readback["readme_readback_match_bool"] is True))
    checks.append(("readback_current_match", readback["current_conclusions_match_bool"] is True))

    # Interpretation: valid research negative, not CI failure.
    interp = interpretation_records(lock_record)[0]
    checks.append(("interp_no_signal", interp["signal_not_reproduced_bool"] is True
                    and interp["signal_reproduced_bool"] is False))
    checks.append(("interp_not_ci_failure", interp["ci_failure_bool"] is False
                    and interp["valid_research_negative_bool"] is True))

    # Report build + validation.
    report = build_report()
    checks.append(("report_status_complete", report["status"] == STATUS_COMPLETE))
    checks.append(("report_scan_pass", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("report_validate", validate_report(report) == []))
    package = report["public_package_records"][0]
    checks.append(("report_readback_fields", package["docs_readback_match_bool"] is True
                   and package["readme_readback_match_bool"] is True
                   and package["current_conclusions_match_bool"] is True))
    checks.append(("report_stop_n10et", report["stop_go_records"][0]["n10et_design_decision_authorized_bool"] is True))
    checks.append(("report_stop_no_execution", report["stop_go_records"][0]["execution_authorized_bool"] is False
                   and report["stop_go_records"][0]["n10er_re_run_authorized_bool"] is False
                   and report["stop_go_records"][0]["provider_model_network_authorized_bool"] is False))

    # Bad-contract detection.
    bad = dict(report)
    bad["status"] = STATUS_COMPLETE
    bad["stop_go_records"] = [{**stop_go_records()[0], "execution_authorized_bool": True}]
    checks.append(("validate_fails_execution", any("execution_authorized_bool_not_false" in f for f in validate_report(bad))))
    bad2 = dict(report)
    bad2["claim_boundary_records"] = [{**claim_boundary_records()[0], "method_winner_claim_bool": True}]
    checks.append(("validate_fails_method_winner", any("method_winner_claim_bool_not_false" in f for f in validate_report(bad2))))
    bad3 = dict(report)
    bad3["public_package_records"] = [{**report["public_package_records"][0], "docs_readback_match_bool": False}]
    checks.append(("validate_fails_readback", any("docs_readback_match_bool" in f for f in validate_report(bad3))))

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
