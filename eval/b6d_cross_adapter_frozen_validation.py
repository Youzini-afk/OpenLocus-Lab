#!/usr/bin/env python3
"""B6D cross-adapter frozen-policy validation.

B6D validates the same two policies frozen by B6B and reused by B6C, but on a
DIFFERENT model adapter: ``[mk]GLM-5.2`` with ``json_schema_strict`` output mode.
It performs **no** policy search, rule generation, or winner selection, and it is
explicitly a cross-adapter smoke check, not a fresh validation or model-robust
claim. The public artifact is aggregate-only and never emits repo IDs, task IDs,
candidate IDs, paths, spans, digests, snippets, prompts, responses, labels, or
gold spans.

B6D reuses B6C's frozen candidate loading and policy evaluation logic, but
parameterizes the allowed adapter and adds GLM-specific noise / infra handling
through the P21 ``call_summary`` schema-valid and infra-failure rates.

Routing uses only public RUN-phase fields: ``task_bucket``, ``task_risk_tags``,
and allowlisted ``route_features`` booleans. SCORE-phase fields such as
``has_gold`` and ``score_group`` are used only after policies are frozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite
import b6b_combined_policy_search as b6b
import b6c_frozen_policy_validation as b6c

SCHEMA_VERSION = "b6d-cross-adapter-frozen-validation-v0"
GENERATED_BY = "b6d_cross_adapter_frozen_validation"
DEFAULT_OUT = Path(
    "artifacts/b6d_cross_adapter_frozen_validation/b6d_cross_adapter_frozen_validation_report.json"
)
DEFAULT_DOC = Path("docs/real-provider-ci/b6d-cross-adapter-frozen-validation.md")

B6D_CONTRACT_VERSION = "b6d-cross-adapter-frozen-validation-contract-v0"

# B6D is a cross-adapter smoke check on GLM-5.2 + json_schema_strict only.
ALLOWED_MODEL = "[mk]GLM-5.2"
ALLOWED_OUTPUT_MODE = "json_schema_strict"
ALLOWED_PLAIN_PACK_LAYOUT = "topk_plain_v0"
ALLOWED_HARD_PACK_LAYOUT = "hard_distractor_contrast_v0"

ALLOWED_ADAPTERS = {
    (ALLOWED_MODEL, ALLOWED_OUTPUT_MODE),
}

# Reuse the B6B/B6C frozen policy spec exactly. B6D must not introduce a new
# frozen candidates file; the same frozen policies are re-evaluated.
EXPECTED_FROZEN_POLICY_SPECS = b6c.EXPECTED_FROZEN_POLICY_SPECS
EXPECTED_FROZEN_SPEC_SHA256 = b6c.EXPECTED_FROZEN_SPEC_SHA256
EXPECTED_FROZEN_NAMES = b6c.EXPECTED_FROZEN_NAMES

# Sanitized adapter identifier for the public report.
MODEL_ADAPTER = "glm_5_2_json_schema_strict"

# Quality thresholds for an interpretable cross-adapter smoke.
SCHEMA_VALID_RATE_MIN = 0.95
INFRA_FAILURE_RATE_MAX = 0.05

# Manifest record keys. B6D extends the B6B manifest with the P21 summary paths
# so the evaluator can read the GLM call_summary without persisting private
# per-task call diagnostics.
B6D_MANIFEST_RECORD_KEYS = tuple(
    list(b6c.MANIFEST_RECORD_KEYS) + ["plain_summary_path", "hard_summary_path"]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


# ---------------------------------------------------------------------------
# Frozen candidate loading (reuse B6C)
# ---------------------------------------------------------------------------


def _load_frozen_candidates(path: Path | None = None) -> list[b6lite.Policy]:
    return b6c._load_frozen_candidates(path)


def _build_p25_baseline() -> b6lite.Policy:
    return b6c._build_p25_baseline()


def _evaluate_policies_on_tasks(
    policies: list[b6lite.Policy],
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return b6c._evaluate_policies_on_tasks(policies, plain_tasks, hard_by_task)


# ---------------------------------------------------------------------------
# Manifest handling (B6B schema + B6D summary paths)
# ---------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = b6b._load_manifest(path)
    records = manifest.get("records") or []
    for i, rec in enumerate(records):
        for key in ("plain_summary_path", "hard_summary_path"):
            if key not in rec:
                raise ValueError(f"manifest.records[{i}] missing {key}")
    return manifest


def _load_p21_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"p21 summary not found: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"p21 summary must be a JSON object: {path}")
    return obj


def _validate_manifest_records(
    records: list[dict[str, Any]],
) -> tuple[str | None, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]]:
    """Return (status_block_reason_or_None, loaded_repo_plain_hard_pairs).

    Mirrors b6b._validate_manifest_records but enforces the B6D adapter:
    ``[mk]GLM-5.2`` / ``json_schema_strict`` and the same pack layouts used by
    B6B/B6C.
    """
    if len(records) < b6b.REQUIRED_REPO_COUNT:
        return ("blocked_insufficient_repos", [])

    def _first(key: str) -> str:
        return str(records[0].get(key, ""))

    for key in ("model", "output_mode", "plain_pack_layout", "hard_pack_layout"):
        expected = _first(key)
        for rec in records[1:]:
            if str(rec.get(key, "")) != expected:
                return ("blocked_mixed_model_mode_pack", [])
    if _first("model") != ALLOWED_MODEL:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("output_mode") != ALLOWED_OUTPUT_MODE:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("plain_pack_layout") != ALLOWED_PLAIN_PACK_LAYOUT:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("hard_pack_layout") != ALLOWED_HARD_PACK_LAYOUT:
        return ("blocked_mixed_model_mode_pack", [])

    loaded: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = []
    for rec in records:
        plain, hard = b6b._load_repo_records(rec)
        if not b6b._same_task_set(plain, hard):
            return ("blocked_task_set_mismatch", [])
        repo_id = str(rec["repo_id"])
        for row in plain:
            row["task_id"] = f"{repo_id}::{row['task_id']}"
        for row in hard:
            row["task_id"] = f"{repo_id}::{row['task_id']}"
        loaded.append((repo_id, plain, hard))

    for _rid, plain, hard in loaded:
        if not plain or not hard:
            return ("blocked_task_set_mismatch", [])

    return (None, loaded)


# ---------------------------------------------------------------------------
# Freshness contract (B6D version)
# ---------------------------------------------------------------------------


def _freshness_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = manifest.get("b6d_fresh_validation_contract")
    if not isinstance(contract, dict):
        return {"present": False, "valid": False, "reason": "missing"}
    valid = (
        contract.get("schema_version") == B6D_CONTRACT_VERSION
        and contract.get("frozen_spec_sha256") == EXPECTED_FROZEN_SPEC_SHA256
        and contract.get("policy_search_performed_for_b6d") is False
        and contract.get("fresh_records_generated_after_freeze") is True
        and contract.get("no_b6d_result_driven_retuning") is True
        and contract.get("record_paths_private_runner_temp_only") is True
        and contract.get("model") == ALLOWED_MODEL
        and contract.get("output_mode") == ALLOWED_OUTPUT_MODE
    )
    return {
        "present": True,
        "valid": valid,
        "schema_version_ok": contract.get("schema_version") == B6D_CONTRACT_VERSION,
        "frozen_spec_hash_matched": contract.get("frozen_spec_sha256") == EXPECTED_FROZEN_SPEC_SHA256,
        "model_matched": contract.get("model") == ALLOWED_MODEL,
        "output_mode_matched": contract.get("output_mode") == ALLOWED_OUTPUT_MODE,
        "policy_search_performed_for_b6d": contract.get("policy_search_performed_for_b6d"),
        "fresh_records_generated_after_freeze": contract.get("fresh_records_generated_after_freeze"),
        "no_b6d_result_driven_retuning": contract.get("no_b6d_result_driven_retuning"),
        "record_paths_private_runner_temp_only": contract.get("record_paths_private_runner_temp_only"),
    }


def _with_valid_freshness_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    out = dict(manifest)
    out["b6d_fresh_validation_contract"] = {
        "schema_version": B6D_CONTRACT_VERSION,
        "frozen_spec_sha256": EXPECTED_FROZEN_SPEC_SHA256,
        "model": ALLOWED_MODEL,
        "output_mode": ALLOWED_OUTPUT_MODE,
        "policy_search_performed_for_b6d": False,
        "fresh_records_generated_after_freeze": True,
        "no_b6d_result_driven_retuning": True,
        "record_paths_private_runner_temp_only": True,
    }
    return out


# ---------------------------------------------------------------------------
# P21 call_summary aggregation (GLM-specific noise / infra handling)
# ---------------------------------------------------------------------------


def _aggregate_call_summaries(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate the GLM P21 call_summary across all manifest records.

    Returns counts that back ``schema_valid_rate`` and
    ``infra_failure_rate``.  ``infra_failure_rate`` counts calls that did not
    succeed at the infra layer (rate-limit / bad-response fallbacks); it is
    derived from ``tasks_scored - successful_calls`` per P21 summary, which is
    the public-call-level infra fallback surface.
    """
    total_calls = 0
    successful_calls = 0
    schema_valid_calls = 0
    schema_error_count = 0
    fallback_used_count = 0
    summaries_seen = 0
    adapter_mismatch_count = 0
    for rec in records:
        for key in ("plain_summary_path", "hard_summary_path"):
            path = Path(rec[key])
            summary = _load_p21_summary(path)
            summaries_seen += 1
            # Cross-check: P21 summary's actual model/output_mode must match
            # the B6D allowed adapter, not just the manifest declaration.
            actual_model = str(summary.get("llm_model") or "")
            actual_mode = str(summary.get("requested_output_mode") or "")
            if actual_model != ALLOWED_MODEL or actual_mode != ALLOWED_OUTPUT_MODE:
                adapter_mismatch_count += 1
            tasks_scored = int(summary.get("tasks_scored") or 0)
            sc = int(summary.get("successful_calls") or 0)
            sv = int(summary.get("schema_valid_calls") or 0)
            cs = summary.get("call_summary") or {}
            total_calls += tasks_scored
            successful_calls += sc
            schema_valid_calls += sv
            schema_error_count += int(cs.get("schema_error_count") or 0)
            fallback_used_count += int(cs.get("fallback_used_count") or 0)
    schema_valid_rate = _safe_div(float(schema_valid_calls), float(total_calls))
    # Infra failure = calls that did not succeed at the provider / transport
    # layer PLUS fallback events.  If json_schema_strict was rejected and P21
    # fell back to json_object/prompt_only, that is a strict-mode infra failure
    # even if the fallback call succeeded.
    transport_failures = max(0, total_calls - successful_calls)
    infra_failure_count = transport_failures + fallback_used_count
    infra_failure_rate = _safe_div(float(infra_failure_count), float(total_calls))
    return {
        "summaries_seen": summaries_seen,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "schema_valid_calls": schema_valid_calls,
        "schema_error_count": schema_error_count,
        "fallback_used_count": fallback_used_count,
        "transport_failure_count": transport_failures,
        "infra_failure_count": infra_failure_count,
        "adapter_mismatch_count": adapter_mismatch_count,
        "adapter_mismatch": adapter_mismatch_count > 0,
        "schema_valid_rate": schema_valid_rate,
        "infra_failure_rate": infra_failure_rate,
    }


def _quality_interpretable(call_agg: dict[str, Any]) -> bool:
    if call_agg.get("adapter_mismatch"):
        return False
    svr = call_agg.get("schema_valid_rate")
    ifr = call_agg.get("infra_failure_rate")
    if svr is None or ifr is None:
        return False
    return svr >= SCHEMA_VALID_RATE_MIN and ifr <= INFRA_FAILURE_RATE_MAX


def _direction_consistency(
    metrics_by_name: dict[str, dict[str, Any]],
    quality_interpretable: bool,
) -> str:
    """Compare GLM effect direction with the B6C (Kimi) frozen-policy direction.

    B6C froze policies that were selected to reduce false spans versus P25. A
    cross-adapter smoke is "consistent_with_kimi" only if every frozen policy
    still produces ``false_reduction_vs_p25 >= 0`` on the GLM adapter. If the
    GLM data is not interpretable, direction is not determinable.
    """
    if not quality_interpretable:
        return "not_determinable"
    for name in EXPECTED_FROZEN_NAMES:
        metrics = metrics_by_name.get(name) or {}
        delta = metrics.get("false_reduction_vs_p25")
        if delta is None or delta < 0:
            return "inconsistent_with_kimi"
    return "consistent_with_kimi"


# ---------------------------------------------------------------------------
# Report assembly and safety
# ---------------------------------------------------------------------------


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    report = b6lite._base_report(status, self_test)
    report["schema_version"] = SCHEMA_VERSION
    report["generated_by"] = GENERATED_BY
    report["claim_level"] = "cross_adapter_smoke_only"
    report["model_adapter"] = MODEL_ADAPTER
    report["policy_search_performed"] = False
    report["frozen_policy_validation"] = True
    report["cross_adapter_smoke"] = True
    report["public_per_repo_rows"] = False
    return report


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bad schema_version")
    if report.get("status") not in {
        "ok",
        "self_test_only",
        "not_quality_interpretable",
        "blocked_insufficient_repos",
        "blocked_mixed_model_mode_pack",
        "blocked_task_set_mismatch",
        "blocked_freshness_contract",
    }:
        raise ValueError("bad status")

    must_be_true = [
        "not_evidence",
        "llm_output_not_evidence",
        "aggregate_only_public_artifact",
        "candidate_not_fact",
        "policy_search_not_admission",
        "diagnostic_policy_search",
        "frozen_policy_validation",
        "cross_adapter_smoke",
    ]
    for key in must_be_true:
        if report.get(key) is not True:
            raise ValueError(f"{key} must be true")

    must_be_false = [
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "task_ids_in_artifact",
        "candidate_ids_in_artifact",
        "repo_ids_in_artifact",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "private_labels_committed",
        "gold_spans_in_artifact",
        "public_per_task_rows",
        "public_per_repo_rows",
        "policy_search_performed",
    ]
    for key in must_be_false:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")

    if report.get("remote_calls_by_policy_search") != 0:
        raise ValueError("remote_calls_by_policy_search must be 0")
    if report.get("claim_level") != "cross_adapter_smoke_only":
        raise ValueError("claim_level must be cross_adapter_smoke_only")
    if report.get("model_adapter") != MODEL_ADAPTER:
        raise ValueError("model_adapter must be glm_5_2_json_schema_strict")

    violations = b6lite._walk_forbidden(report)
    if violations:
        raise ValueError(
            "public report contains forbidden fields: " + ", ".join(violations[:5])
        )

    if report.get("status") == "ok":
        families = report.get("policy_families") or {}
        if "p25_bucket_routed_v0_plain" not in families:
            raise ValueError("P25 baseline missing from policy_families")
        frozen_names = set(report.get("frozen_policy_names") or [])
        if frozen_names != EXPECTED_FROZEN_NAMES:
            raise ValueError(f"frozen_policy_names mismatch: {frozen_names}")
        if report.get("frozen_policy_count") != len(EXPECTED_FROZEN_NAMES):
            raise ValueError("frozen_policy_count mismatch")

        integrity = report.get("frozen_manifest_integrity") or {}
        for key in (
            "manifest_schema_version_ok",
            "record_required_fields_present",
            "model_mode_pack_uniform",
            "allowed_model_mode_pack",
            "task_sets_matched",
            "paired_records_loadable",
            "freshness_contract_valid",
            "frozen_spec_hash_matched",
            "forbidden_public_key_scan_clean",
        ):
            if integrity.get(key) is not True:
                raise ValueError(f"frozen_manifest_integrity.{key} must be true")

        routing = report.get("routing_invariance") or {}
        if routing.get("selected_actions_invariant") is not True:
            raise ValueError("routing changed when SCORE/gold fields were mutated")

        for name, metrics in families.items():
            tc = metrics.get("task_count")
            if not isinstance(tc, int) or tc <= 0:
                raise ValueError(f"{name} has invalid task_count")
            if sum((metrics.get("action_counts") or {}).values()) != tc:
                raise ValueError(f"{name} action counts do not sum to {tc}")
            if "policy_rules" not in metrics:
                raise ValueError(f"{name} missing policy_rules")

        if report.get("quality_interpretable") is not True:
            raise ValueError("status=ok requires quality_interpretable=true")
        if report.get("direction_consistency") not in {
            "consistent_with_kimi",
            "inconsistent_with_kimi",
        }:
            raise ValueError("status=ok requires a determinable direction_consistency")

        if "winner" in report or "default_recommendation" in report:
            raise ValueError("report must not declare a winner or default recommendation")

    if report.get("status") == "not_quality_interpretable":
        if report.get("quality_interpretable") is not False:
            raise ValueError("not_quality_interpretable requires quality_interpretable=false")
        if report.get("direction_consistency") != "not_determinable":
            raise ValueError("not_quality_interpretable must not claim direction consistency")
        call_agg = report.get("call_summary_aggregate") or {}
        if call_agg.get("infra_failure_count") is None:
            raise ValueError("not_quality_interpretable must include infra_failure_count")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    self_test = bool(args.self_test or getattr(args, "mark_self_test", False))

    if args.self_test:
        manifest_path, repo_pairs = _write_self_test_manifest()
        records = json.loads(manifest_path.read_text(encoding="utf-8"))["records"]
        freshness = {"present": False, "valid": False, "self_test_synthetic": True}
    else:
        manifest = _load_manifest(args.paired_records_manifest)
        freshness = _freshness_contract(manifest)
        records = manifest["records"]
        if not bool(args.mark_self_test) and not freshness.get("valid"):
            report = _base_report("blocked_freshness_contract", self_test)
            report.update(
                {
                    "included_repo_count": len(records),
                    "manifest_record_count": len(records),
                    "comparable_task_count": 0,
                    "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
                    "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
                    "schema_valid_rate": None,
                    "infra_failure_rate": None,
                    "quality_interpretable": False,
                    "direction_consistency": "not_determinable",
                    "sample_freshness_protocol": "blocked_missing_or_invalid_b6d_fresh_validation_contract",
                    "frozen_manifest_integrity": {
                        "manifest_schema_version_ok": True,
                        "record_required_fields_present": True,
                        "freshness_contract_present": freshness.get("present") is True,
                        "freshness_contract_valid": False,
                        "frozen_spec_hash_matched": freshness.get("frozen_spec_hash_matched") is True,
                        "forbidden_public_key_scan_clean": True,
                        "block_reason": "blocked_freshness_contract",
                    },
                    "policy_families": {},
                }
            )
            validate_report(report)
            return report
        block_status, repo_pairs = _validate_manifest_records(records)
        if block_status:
            report = _base_report(block_status, self_test)
            report.update(
                {
                    "included_repo_count": len(records),
                    "manifest_record_count": len(records),
                    "comparable_task_count": 0,
                    "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
                    "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
                    "schema_valid_rate": None,
                    "infra_failure_rate": None,
                    "quality_interpretable": False,
                    "direction_consistency": "not_determinable",
                    "sample_freshness_protocol": "blocked_manifest_precondition",
                    "frozen_manifest_integrity": {
                        "manifest_schema_version_ok": True,
                        "record_required_fields_present": True,
                        "model_mode_pack_uniform": block_status != "blocked_mixed_model_mode_pack",
                        "allowed_model_mode_pack": block_status != "blocked_mixed_model_mode_pack",
                        "task_sets_matched": block_status != "blocked_task_set_mismatch",
                        "paired_records_loadable": True,
                        "freshness_contract_present": freshness.get("present") is True,
                        "freshness_contract_valid": bool(args.mark_self_test) or freshness.get("valid") is True,
                        "frozen_spec_hash_matched": bool(args.mark_self_test) or freshness.get("frozen_spec_hash_matched") is True,
                        "forbidden_public_key_scan_clean": True,
                        "block_reason": block_status,
                    },
                    "policy_families": {},
                }
            )
            if block_status == "blocked_insufficient_repos":
                report["required_repo_count"] = b6b.REQUIRED_REPO_COUNT
            validate_report(report)
            return report

    # Load frozen candidates and P25 baseline.
    frozen_policies = _load_frozen_candidates()
    p25_policy = _build_p25_baseline()
    policies = [p25_policy] + frozen_policies

    all_plain = [t for _rid, plain, _hard in repo_pairs for t in plain]
    all_hard_by_task = {
        str(t["task_id"]): t for _rid, _plain, hard in repo_pairs for t in hard
    }

    metrics_by_name = _evaluate_policies_on_tasks(policies, all_plain, all_hard_by_task)
    for metrics in metrics_by_name.values():
        metrics["task_count"] = len(all_plain)

    routing_invariance = b6lite._routing_invariance_check(policies, all_plain)

    # Aggregate GLM P21 call summaries for the noise / infra quality gate.
    call_agg = _aggregate_call_summaries(records)
    quality_interpretable = _quality_interpretable(call_agg)
    direction_consistency = _direction_consistency(metrics_by_name, quality_interpretable)

    integrity: dict[str, Any] = {
        "manifest_schema_version_ok": True,
        "record_required_fields_present": True,
        "model_mode_pack_uniform": True,
        "allowed_model_mode_pack": True,
        "task_sets_matched": True,
        "paired_records_loadable": True,
        "forbidden_public_key_scan_clean": True,
    }

    output_status = "self_test_only" if self_test else (
        "ok" if quality_interpretable else "not_quality_interpretable"
    )
    report = _base_report(output_status, self_test)
    report.update(
        {
            "included_repo_count": len(repo_pairs),
            "manifest_record_count": len(repo_pairs),
            "comparable_task_count": len(all_plain),
            "sample_freshness_protocol": (
                "self_test_synthetic_sample_not_cross_adapter_validation"
                if self_test
                else "b6d_fresh_validation_contract_checked; policies frozen before evaluation; no search on fresh records; glm_5_2_json_schema_strict adapter"
            ),
            "frozen_manifest_integrity": integrity,
            "frozen_policy_count": len(frozen_policies),
            "frozen_policy_names": sorted(p.name for p in frozen_policies),
            "policy_families": metrics_by_name,
            "routing_invariance": routing_invariance,
            "schema_valid_rate": call_agg.get("schema_valid_rate"),
            "infra_failure_rate": call_agg.get("infra_failure_rate"),
            "quality_interpretable": quality_interpretable,
            "direction_consistency": direction_consistency,
            "call_summary_aggregate": {
                "summaries_seen": call_agg.get("summaries_seen"),
                "total_calls": call_agg.get("total_calls"),
                "successful_calls": call_agg.get("successful_calls"),
                "schema_valid_calls": call_agg.get("schema_valid_calls"),
                "schema_error_count": call_agg.get("schema_error_count"),
                "fallback_used_count": call_agg.get("fallback_used_count"),
                "infra_failure_count": call_agg.get("infra_failure_count"),
            },
            "comparability": {
                "model": ALLOWED_MODEL,
                "output_mode": ALLOWED_OUTPUT_MODE,
                "model_adapter": MODEL_ADAPTER,
                "plain_pack_layout": ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": ALLOWED_HARD_PACK_LAYOUT,
                "same_model_required": True,
                "same_output_mode_required": True,
                "same_pack_layout_required": True,
                "same_model_observed": True,
                "same_task_set_within_repo_required": True,
                "same_task_set_within_repo_observed": True,
                "fresh_aggregate_evaluation": not self_test,
                "search_performed": False,
                "cross_adapter_smoke": True,
                "reference_adapter_for_frozen_policies": "b6c_kimi_k2_7_code_tool_call",
            },
        }
    )

    report_violations = b6lite._walk_forbidden(report)
    report["frozen_manifest_integrity"]["forbidden_public_key_scan_clean"] = not report_violations
    report["frozen_manifest_integrity"]["freshness_contract_present"] = freshness.get("present") is True
    report["frozen_manifest_integrity"]["freshness_contract_valid"] = bool(self_test) or freshness.get("valid") is True
    report["frozen_manifest_integrity"]["frozen_spec_hash_matched"] = bool(self_test) or freshness.get("frozen_spec_hash_matched") is True
    if report_violations:
        report["frozen_manifest_integrity"]["forbidden_public_key_violations"] = report_violations[:5]

    validate_report(report)
    return report


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B6D Cross-Adapter Frozen-Policy Validation")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    lines.append(
        "B6D re-evaluates the two policies frozen by B6B (and reused by B6C) on a "
        "DIFFERENT model adapter: `[mk]GLM-5.2` with `json_schema_strict` output "
        "mode. No search, rule generation, or winner selection is performed. "
        "B6D is a cross-adapter smoke check, not a fresh validation or "
        "model-robust claim. The public artifact is aggregate-only; per-task / "
        "per-repo details stay in `$RUNNER_TEMP`."
    )
    if report.get("self_test") is True:
        lines.append("")
        lines.append(
            "This is a self-test / synthetic protocol check, not a live cross-adapter run."
        )
    lines.append("")

    if report.get("status") not in {"ok", "self_test_only"}:
        lines.append("Evaluation was blocked; no policies were scored.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("## Adapter")
    lines.append(f"- model_adapter: `{report.get('model_adapter')}`")
    lines.append(f"- model: `{ALLOWED_MODEL}`")
    lines.append(f"- output_mode: `{ALLOWED_OUTPUT_MODE}`")
    lines.append(
        f"- quality_interpretable: `{report.get('quality_interpretable')}` "
        f"(schema_valid_rate >= {SCHEMA_VALID_RATE_MIN} AND "
        f"infra_failure_rate <= {INFRA_FAILURE_RATE_MAX})"
    )
    lines.append(f"- direction_consistency: `{report.get('direction_consistency')}`")
    lines.append("")

    call_agg = report.get("call_summary_aggregate") or {}
    lines.append("## GLM P21 call summary aggregate")
    lines.append(f"- summaries_seen: {call_agg.get('summaries_seen')}")
    lines.append(f"- total_calls: {call_agg.get('total_calls')}")
    lines.append(f"- successful_calls: {call_agg.get('successful_calls')}")
    lines.append(f"- schema_valid_calls: {call_agg.get('schema_valid_calls')}")
    lines.append(f"- schema_error_count: {call_agg.get('schema_error_count')}")
    lines.append(f"- fallback_used_count: {call_agg.get('fallback_used_count')}")
    lines.append(f"- infra_failure_count: {call_agg.get('infra_failure_count')}")
    lines.append(f"- schema_valid_rate: `{_fmt(report.get('schema_valid_rate'))}`")
    lines.append(f"- infra_failure_rate: `{_fmt(report.get('infra_failure_rate'))}`")
    lines.append("")

    lines.append("## Frozen policies")
    lines.append(f"- Count: {report['frozen_policy_count']}")
    lines.append(
        "- Names: " + ", ".join(f"`{n}`" for n in sorted(report.get("frozen_policy_names", [])))
    )
    lines.append(
        "- Sample freshness protocol: "
        f"{report.get('sample_freshness_protocol', '')}"
    )
    lines.append("")

    lines.append("## Aggregate policy families")
    header = (
        "| Policy family | source | +gold | +false | F/G | SpanF0.5 | PFP | "
        "LLM calls | net 2x | gold kill vs P25 | false reduction vs P25 |"
    )
    lines.append(header)
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(report.get("policy_families", {})):
        m = report["policy_families"][name]
        source = m.get("source", "unknown")
        lines.append(
            f"| `{name}` | {source} | {m.get('added_gold_span', '')} | "
            f"{m.get('added_false_span', '')} | {_fmt(m.get('false_per_gold'))} | "
            f"{_fmt(m.get('mean_span_f05'))} | {_fmt(m.get('mean_primary_false_positive_rate'))} | "
            f"{m.get('effective_llm_action_count', '')} | {m.get('net_span_value_2x', '')} | "
            f"{m.get('gold_kill_vs_p25', '')} | {m.get('false_reduction_vs_p25', '')} |"
        )
    lines.append("")

    lines.append("## Routing invariance")
    inv = report.get("routing_invariance", {})
    lines.append(
        f"- SCORE-field routing invariance: {inv.get('selected_actions_invariant')} "
        f"(changed policies: {inv.get('changed_policy_count')})"
    )
    lines.append("")

    lines.append("## Safety notes")
    lines.append(
        "- `claim_level=cross_adapter_smoke_only`: never `model_robust` or "
        "`fresh_validation`."
    )
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, "
        "`evidencecore_semantics_changed=false`, `policy_search_performed=false`."
    )
    lines.append(
        "- `remote_calls_by_policy_search=0`; P21 makes calls, this evaluator does not."
    )
    lines.append(
        "- `quality_interpretable` gates whether direction is comparable to "
        "the B6C Kimi reference."
    )
    lines.append(
        "- Routing uses only public `task_bucket`, `task_risk_tags`, and allowlisted "
        "`route_features`."
    )
    lines.append(
        "- The public artifact is aggregate-only: no task IDs, repo IDs, paths, "
        "candidates, snippets, prompts, responses, or gold spans."
    )
    lines.append(
        "- B6D reuses `eval/b6c_frozen_candidates.json`; it does not introduce a "
        "new frozen candidates file."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test inputs and assertions
# ---------------------------------------------------------------------------


def _write_synthetic_p21_summary(path: Path, tasks_scored: int, schema_valid: int, successful: int) -> None:
    """Write a minimal synthetic P21 summary with the public call_summary fields."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "p21-g3l-llm-rich-candidate-v0",
        "tasks_scored": int(tasks_scored),
        "successful_calls": int(successful),
        "schema_valid_calls": int(schema_valid),
        "call_summary": {
            "schema_error_count": int(tasks_scored - schema_valid),
            "fallback_used_count": int(tasks_scored - successful),
            "schema_repair_attempted_count": 0,
            "schema_repair_success_count": 0,
            "actual_output_modes": ["json_schema_strict"],
            "fallback_event_count": 0,
            "fallback_events": {},
            "packed_candidates_total": 0,
        },
        "provider_status": "ok" if successful == tasks_scored and schema_valid == tasks_scored else "degraded",
        "requested_output_mode": "json_schema_strict",
        "llm_model": ALLOWED_MODEL,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_self_test_manifest(
    tmp: Path | None = None,
    *,
    healthy_call_summary: bool = True,
) -> tuple[Path, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]]:
    """Build a synthetic GLM-5.2/json_schema_strict manifest + summaries."""
    if tmp is None:
        tmp = Path("/tmp/opencode/b6d-combined-self-test")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    repos = ["py_flask", "js_express", "go_gin", "rust_ripgrep"]
    repo_pairs: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = []
    manifest_records: list[dict[str, Any]] = []

    for offset, repo_id in enumerate(repos):
        plain_rows, hard_rows, plain_path, hard_path = b6b._build_repo_pair(
            tmp, repo_id, base_tasks, offset
        )
        plain_norm = b6lite._load_records(plain_path)
        hard_norm = b6lite._load_records(hard_path)
        repo_pairs.append((repo_id, plain_norm, hard_norm))

        # Synthetic P21 summaries for the GLM adapter.
        plain_summary = tmp / repo_id / "plain_summary.json"
        hard_summary = tmp / repo_id / "hard_summary.json"
        tasks_n = len(plain_norm)
        if healthy_call_summary:
            _write_synthetic_p21_summary(plain_summary, tasks_scored=tasks_n, schema_valid=tasks_n, successful=tasks_n)
            _write_synthetic_p21_summary(hard_summary, tasks_scored=tasks_n, schema_valid=tasks_n, successful=tasks_n)
        else:
            # Half of calls fail schema validation; this drops quality_interpretable.
            half = max(1, tasks_n // 2)
            _write_synthetic_p21_summary(plain_summary, tasks_scored=tasks_n, schema_valid=half, successful=tasks_n)
            _write_synthetic_p21_summary(hard_summary, tasks_scored=tasks_n, schema_valid=half, successful=tasks_n)

        manifest_records.append(
            {
                "repo_id": repo_id,
                "model": ALLOWED_MODEL,
                "output_mode": ALLOWED_OUTPUT_MODE,
                "plain_pack_layout": ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": ALLOWED_HARD_PACK_LAYOUT,
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
                "plain_summary_path": str(plain_summary),
                "hard_summary_path": str(hard_summary),
            }
        )

    manifest = {
        "schema_version": "b6b-paired-records-manifest-v0",
        "not_artifact_for_commit": True,
        "records": manifest_records,
    }
    manifest_path = tmp / "b6d_paired_records_manifest.private.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path, repo_pairs


def _self_test_frozen_policies_present() -> dict[str, Any]:
    policies = _load_frozen_candidates()
    names = {p.name for p in policies}
    assert names == EXPECTED_FROZEN_NAMES, names
    print("self-test frozen policies present: ok")
    return {p.name: [r["name"] for r in p.rules] for p in policies}


def _self_test_wrong_adapter_kimi_blocked() -> None:
    """Kimi/tool_call records must be rejected by the GLM adapter gate."""
    tmp = Path("/tmp/opencode/b6d-test-kimi-adapter")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        _, _, plain_path, hard_path = b6b._build_repo_pair(tmp, repo_id, base_tasks, offset)
        plain_summary = tmp / repo_id / "plain_summary.json"
        hard_summary = tmp / repo_id / "hard_summary.json"
        _write_synthetic_p21_summary(plain_summary, tasks_scored=4, schema_valid=4, successful=4)
        _write_synthetic_p21_summary(hard_summary, tasks_scored=4, schema_valid=4, successful=4)
        records.append(
            {
                "repo_id": repo_id,
                "model": "[mk]Kimi-K2.7-Code",  # wrong adapter for B6D
                "output_mode": "tool_call",
                "plain_pack_layout": ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": ALLOWED_HARD_PACK_LAYOUT,
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
                "plain_summary_path": str(plain_summary),
                "hard_summary_path": str(hard_summary),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_mixed_model_mode_pack", report["status"]
    assert report["model_adapter"] == MODEL_ADAPTER
    assert report["quality_interpretable"] is False
    assert report["direction_consistency"] == "not_determinable"
    print("self-test kimi adapter blocked: ok")


def _self_test_missing_freshness_contract_blocks() -> None:
    tmp = Path("/tmp/opencode/b6d-test-missing-freshness")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, _repo_pairs = _write_self_test_manifest(tmp)
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_freshness_contract", report["status"]
    assert report["claim_level"] == "cross_adapter_smoke_only"
    assert report["quality_interpretable"] is False
    print("self-test missing freshness contract blocks: ok")


def _self_test_low_schema_valid_rate_blocks_quality() -> None:
    tmp = Path("/tmp/opencode/b6d-test-low-schema")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, _repo_pairs = _write_self_test_manifest(tmp, healthy_call_summary=False)
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=True,
    )
    report = build_report(args)
    # status=self_test_only because we mark_self_test, but quality_interpretable
    # must be False and direction must be not_determinable.
    assert report["status"] == "self_test_only", report["status"]
    assert report["schema_valid_rate"] is not None and report["schema_valid_rate"] < SCHEMA_VALID_RATE_MIN, report
    assert report["quality_interpretable"] is False, report
    assert report["direction_consistency"] == "not_determinable", report
    print("self-test low schema_valid_rate blocks quality_interpretable: ok")


def _self_test_insufficient_repos() -> None:
    tmp = Path("/tmp/opencode/b6d-test-insufficient")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express"]):
        _, _, plain_path, hard_path = b6b._build_repo_pair(tmp, repo_id, base_tasks, offset)
        plain_summary = tmp / repo_id / "plain_summary.json"
        hard_summary = tmp / repo_id / "hard_summary.json"
        _write_synthetic_p21_summary(plain_summary, tasks_scored=4, schema_valid=4, successful=4)
        _write_synthetic_p21_summary(hard_summary, tasks_scored=4, schema_valid=4, successful=4)
        records.append(
            {
                "repo_id": repo_id,
                "model": ALLOWED_MODEL,
                "output_mode": ALLOWED_OUTPUT_MODE,
                "plain_pack_layout": ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": ALLOWED_HARD_PACK_LAYOUT,
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
                "plain_summary_path": str(plain_summary),
                "hard_summary_path": str(hard_summary),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_insufficient_repos", report["status"]
    assert report["policy_search_performed"] is False
    print("self-test insufficient repos: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_frozen_policies_present()
    _self_test_wrong_adapter_kimi_blocked()
    _self_test_missing_freshness_contract_blocks()
    _self_test_low_schema_valid_rate_blocks_quality()
    _self_test_insufficient_repos()
    print("all b6d self-tests passed")

    # Final happy-path report for caller validation.
    tmp = Path("/tmp/opencode/b6d-test-happy")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, _repo_pairs = _write_self_test_manifest(tmp)
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=True,
    )
    report = build_report(args)
    assert report["status"] == "self_test_only", report["status"]
    assert report["policy_search_performed"] is False
    assert report.get("frozen_policy_count") == 2
    assert set(report.get("frozen_policy_names", [])) == EXPECTED_FROZEN_NAMES
    assert "p25_bucket_routed_v0_plain" in report["policy_families"]
    for name in EXPECTED_FROZEN_NAMES:
        assert name in report["policy_families"], name
    inv = report.get("routing_invariance", {})
    assert inv.get("selected_actions_invariant") is True, inv
    integrity = report.get("frozen_manifest_integrity", {})
    assert integrity.get("forbidden_public_key_scan_clean") is True, integrity
    assert report.get("model_adapter") == MODEL_ADAPTER, report
    assert report.get("schema_valid_rate") == 1.0, report
    assert report.get("quality_interpretable") is True, report
    assert report.get("direction_consistency") == "consistent_with_kimi", report
    print("self-test happy path: ok")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-records-manifest", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--mark-self-test",
        action="store_true",
        help="Process the provided manifest but mark the public report self_test_only.",
    )
    args = parser.parse_args(argv)
    if not args.self_test and not args.paired_records_manifest:
        parser.error("--paired-records-manifest is required unless --self-test")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
    report = build_report(args)
    _write_json(args.out, report)
    _write_markdown(report, args.doc)
    print(
        json.dumps(
            {
                "status": report["status"],
                "included_repo_count": report.get("included_repo_count"),
                "comparable_task_count": report.get("comparable_task_count"),
                "frozen_policy_count": report.get("frozen_policy_count"),
                "model_adapter": report.get("model_adapter"),
                "schema_valid_rate": report.get("schema_valid_rate"),
                "infra_failure_rate": report.get("infra_failure_rate"),
                "quality_interpretable": report.get("quality_interpretable"),
                "direction_consistency": report.get("direction_consistency"),
                "policy_search_performed": report.get("policy_search_performed"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
