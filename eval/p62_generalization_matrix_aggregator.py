#!/usr/bin/env python3
"""P62 Generalization Matrix Aggregator v0.

P62 is a deterministic, no-live-LLM, no-provider, aggregate-only tool that
combines multiple per-slice aggregate diagnostic report-sets (each slice = one
real-provider run) into a >=4-DISTINCT-slice generalization matrix, WITHOUT
leaking slice identity (no repo_id/dataset/paths/digests) and WITHOUT
fabricating diversity (the same slice counted 4x must NOT inflate
slice_count).

P62 produces BOTH:
  (a) its own diagnostic public report, and
  (b) a P57-compatible `--input-matrix` JSON containing only the DISTINCT
      ELIGIBLE slices, so P57 (unchanged) can consume it.

P62 NEVER reads source/gold/labels/ephemeral records, never calls providers,
never constructs prompts, never admits Evidence, never changes defaults, never
authorizes spend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p62-generalization-matrix-aggregator-v0"
GENERATED_BY = "p62_generalization_matrix_aggregator"
STAGE = "P62 Generalization Matrix Aggregator v0"

DEFAULT_OUT = Path("artifacts/p62_generalization_matrix_aggregator/p62_generalization_matrix_aggregator_report.json")
DEFAULT_DOC = Path("docs/en/p62-generalization-matrix-aggregator.md")
DEFAULT_P57_INPUT_MATRIX = Path("artifacts/p62_generalization_matrix_aggregator/p62_p57_input_matrix.json")

P62_REQUIRED_PHASES = ["p57", "p58", "p59", "p60", "p51b"]

P57_REQUIRED_PHASES = [
    "p46", "p47", "p48", "p49", "p50", "p52", "p52a", "p52b", "p52c", "p51b"
]
P57_OPTIONAL_PHASES = ["p51"]

P57_FIXED_FILENAMES = {
    "p46": "p46_candidate_reach_cost_map_report.json",
    "p47": "p47_request_more_context_report.json",
    "p48": "p48_diagnostic_policy_simulator_report.json",
    "p49": "p49_contrastive_candidate_pack_scaffold_report.json",
    "p50": "p50_fixed_suite_validation_report.json",
    "p52": "p52_metadata_local_verifier_scaffold_report.json",
    "p52a": "p52a_source_materialization_prerequisite_report.json",
    "p52b": "p52b_source_backed_local_verifier_feature_matrix_report.json",
    "p52c": "p52c_local_verifier_scoring_simulator_report.json",
    "p51": "p51_llm_span_narrow_2_diagnostic_report.json",
    "p51b": "p51b_llm_opt_in_contract_report.json",
}

P62_FIXED_FILENAMES = {
    "p57": "p57_generalization_gate_report.json",
    "p58": "p58_source_backed_verifier_calibration_report.json",
    "p59": "p59_contrastive_pack_coverage_counterfactual_report.json",
    "p60": "p60_rmc_policy_v2_report.json",
    "p51b": "p51b_llm_opt_in_contract_report.json",
}

REQUIRED_SLICE_COUNT = 4

ALLOWED_STATUS = {
    "self_test_only",
    "blocked_safety",
    "insufficient_matrix_inputs",
    "diagnostic_matrix_unstable",
    "diagnostic_matrix_complete",
}

ACCEPTABLE_STATUS = {
    "p57": {"insufficient_matrix", "diagnostic_matrix_complete", "diagnostic_matrix_unstable"},
    "p58": {"diagnostic_calibration_available"},
    "p59": {"diagnostic_coverage_available"},
    "p60": {"diagnostic_policy_matrix_available"},
    "p51b": {"ok"},
}

COMMON_SAFETY_FLAGS = {
    "promotion_ready": False,
    "default_should_change": False,
    "evidencecore_semantics_changed": False,
    "candidate_not_fact": True,
    "aggregate_only_public_artifact": True,
}

RAW_FLAGS = [
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
]

PHASE_SAFETY = {
    "p57": {
        "remote": "remote_calls_by_p57",
        "llm": "llm_calls_by_p57",
        "prompt": "prompt_construction_by_p57",
        "source_reads": "source_reads_attempted_by_p57",
    },
    "p58": {
        "remote": "remote_calls_by_p58",
        "llm": "llm_calls_by_p58",
        "remote_requests": "remote_requests_by_p58",
        "prompt": "prompt_construction_by_p58",
        "source_reads": "source_reads_attempted_by_p58",
        "provider_config": "provider_config_read_by_p58",
    },
    "p59": {
        "remote": "remote_calls_by_p59",
        "llm": "llm_calls_by_p59",
        "prompt": "prompt_construction_by_p59",
        "source_reads": "source_reads_attempted_by_p59",
        "provider_config": "provider_config_read_by_p59",
    },
    "p60": {
        "remote": "remote_calls_by_p60",
        "llm": "llm_calls_by_p60",
        "prompt": "prompt_construction_by_p60",
        "source_reads": "source_reads_attempted_by_p60",
        "provider_config": "provider_config_read_by_p60",
    },
    "p51b": {
        "remote": "remote_calls_by_p51b",
        "llm": "llm_calls_by_p51b",
        "remote_requests": "remote_requests_by_p51b",
        "prompt": "prompt_construction_by_p51b",
    },
}

P51B_EXTRA = {
    "remote_requests_by_p51b": 0,
    "dry_run_payload_validation_only": True,
    "p51b_live_calls_disabled": True,
}

P60_EXTRA = {
    "rmc_not_evidence": True,
    "rmc_not_admission": True,
    "rmc_next_action_only": True,
    "policy_comparison_not_ranking": True,
    "expected_cost_latency_are_estimates": True,
    "run_phase_gold_free": True,
    "gold_used_for_policy_selection": False,
}

P59_EXTRA = {
    "run_phase_gold_free": True,
    "gold_used_for_pack_construction": False,
}

FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "candidate_id",
    "repo_id",
    "dataset",
    "path",
    "start_line",
    "end_line",
    "span",
    "content_sha",
    "digest",
    "hash",
    "gold",
    "gold_spans",
    "private_label",
    "private_labels",
    "label",
    "labels",
    "query",
    "raw_query",
    "snippet",
    "source_text",
    "raw_source",
    "prompt",
    "response",
    "provider",
    "model",
    "base_url",
    "api_key",
    "api_token",
    "provider_key",
    "endpoint",
    "repo_lock",
    "source_root",
    "corpus_root",
    "tasks",
    "records",
    "per_task",
    "per_task_results",
    "per_candidate_results",
    "per_slice_rows",
    "decision_records",
    "candidate_pool",
    "raw_candidates",
    "candidates",
    "pack_items",
    "evidence",
    "Evidence",
    "winner",
    "best_policy",
    "recommended_policy",
    "promotable_policy",
    "default_policy",
    "promotion_decision",
    "default_decision",
    "admission_decision",
    "evidence_valid",
    "request_envelope",
    "raw_request_envelope",
    "raw_request_envelopes",
    "slice_dir",
    "slice_dirs",
    "slice_digest",
    "slice_digests",
    "fingerprint",
    "fingerprints",
    "signature",
    "signatures",
}

P62_SAFETY_FLAG_KEYS = {
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "precondition_report_only",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "aggregate_only_public_artifact",
    "remote_calls_by_p62",
    "llm_calls_by_p62",
    "remote_requests_by_p62",
    "provider_config_read_by_p62",
    "prompt_construction_by_p62",
    "source_reads_attempted_by_p62",
    "gold_used_by_p62",
    "private_labels_loaded_by_p62",
    "raw_text_stored",
    "raw_source_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_query_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
    "elapsed_ms",
    "input_summary",
    "distinctness",
    "generalization_matrix",
    "upstream_safety_gate",
    "p57_consumption_contract",
    "blockers",
    "warnings",
    "conclusion",
    "validation",
    "provided_input_count",
    "readable_input_count",
    "required_report_set_complete_input_count",
    "safe_input_count",
    "content_distinct_input_count",
    "eligible_distinct_slice_count",
    "required_distinct_slice_count",
    "self_test_input_count",
    "blocked_safety_input_count",
    "missing_required_report_input_count",
    "invalid_json_input_count",
    "duplicate_input_count",
    "matrix_requirement_summary",
    "distinctness_claim",
    "identity_fields_used",
    "identity_fields_published",
    "signature_values_published",
    "content_distinct_sanitized_aggregate_report_sets_only_not_repo_or_dataset_identity",
    "readiness_status",
    "required_slice_count",
    "observed_slice_count",
    "included_generalization_slice_count",
    "observed_repo_count",
    "per_stage_status_summary",
    "cross_slice_dispersion",
    "acceptable_rate",
    "blocked_safety_rate",
    "self_test_rate",
    "unstable_rate",
    "n",
    "min",
    "median",
    "max",
    "iqr",
    "safe_rates",
    "checked_count",
    "blocker_count",
    "warning_count",
    "by_phase",
    "report_present",
    "status",
    "safety_blocker",
    "safety_warnings",
    "promotion_default_false",
    "candidate_not_fact_true",
    "aggregate_only_true",
    "remote_calls_zero",
    "llm_calls_zero",
    "prompt_construction_false",
    "source_reads_not_attempted_or_bounded",
    "p57_may_consume_this_report",
    "requires_explicit_p57_support",
    "do_not_substitute_as_p57_report_without_validation",
    "p57_input_matrix_written",
    "p57_slice_count_field_source",
    "count",
    "rate",
    "value",
    "availability",
    "bucket",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] * (c - k) + s[c] * (k - f))


def _read_aggregate_report(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid_json": True, "status": "invalid_json"}
    if not isinstance(data, dict):
        return {"_invalid_json": True, "status": "invalid_json"}
    return data


def _safe_status(data: dict[str, Any] | None) -> str:
    if data is None:
        return "not_provided"
    if data.get("_invalid_json"):
        return "invalid_json"
    if data.get("_aggregate_contract_violation"):
        return "aggregate_contract_violation"
    status = data.get("status")
    if isinstance(status, str):
        return status
    return "not_provided"


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P62_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _scan_values_for_leaks(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_scan_values_for_leaks(value, prefix + str(key) + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_values_for_leaks(value, prefix + str(idx) + "."))
    elif isinstance(obj, str):
        text = obj.strip()
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
        elif "://" in text:
            violations.append(prefix + " looks like a URL")
        elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
        elif re.fullmatch(r"[0-9a-fA-F]{32,}", text):
            violations.append(prefix + " looks like a hex digest")
    return violations


def _load_slices_from_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("--slice-manifest must contain a JSON list of slice entries")
    slices: list[dict[str, Any]] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise SystemExit(f"slice entry {idx} must be an object")
        slice_dir: Path | None = None
        if "slice_dir" in entry:
            slice_dir = Path(entry["slice_dir"])
        slice_data: dict[str, Any] = {"_slice_dir": slice_dir, "_p57_paths": {}}
        for phase in P62_REQUIRED_PHASES:
            if slice_dir is not None:
                path = slice_dir / P62_FIXED_FILENAMES[phase]
            else:
                path_key = f"{phase}_report"
                path = Path(entry[path_key]) if entry.get(path_key) else None
            slice_data[phase] = _read_aggregate_report(path)
        # Collect P57-compatible report paths for the handoff file.
        for phase in P57_REQUIRED_PHASES + P57_OPTIONAL_PHASES:
            if slice_dir is not None:
                p57_path = slice_dir / P57_FIXED_FILENAMES[phase]
                if p57_path.exists():
                    slice_data["_p57_paths"][phase] = str(p57_path)
            else:
                path_key = f"{phase}_report"
                if entry.get(path_key):
                    slice_data["_p57_paths"][phase] = str(Path(entry[path_key]))
        slices.append(slice_data)
    return slices


def _verify_common_safety(data: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if data is None or data.get("_invalid_json"):
        return False, ["report_missing_or_invalid"]
    warnings: list[str] = []
    for flag, expected in COMMON_SAFETY_FLAGS.items():
        if flag in data:
            if data[flag] is not expected:
                return False, [f"{flag}_violation"]
        else:
            warnings.append(f"missing_{flag}")
    for flag in RAW_FLAGS:
        if flag in data and data[flag] is not False:
            return False, [f"{flag}_violation"]
    return True, warnings


def _verify_phase_safety(phase: str, data: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "report_present": data is not None and not data.get("_invalid_json"),
        "status": _safe_status(data),
        "safety_blocker": False,
        "safety_warnings": [],
        "promotion_default_false": None,
        "candidate_not_fact_true": None,
        "aggregate_only_true": None,
        "remote_calls_zero": None,
        "llm_calls_zero": None,
        "prompt_construction_false": None,
        "source_reads_not_attempted_or_bounded": None,
    }
    if data is None or data.get("_invalid_json"):
        result["safety_warnings"].append("report_missing_or_invalid")
        return result

    ok, warnings = _verify_common_safety(data)
    if not ok:
        result["safety_blocker"] = True
        result["safety_warnings"].extend(warnings)
        return result
    result["safety_warnings"].extend(warnings)

    cfg = PHASE_SAFETY.get(phase, {})

    def check(key: str | None, expected: Any, label: str, blocker: bool) -> None:
        if key is None:
            return
        if key in data:
            if data[key] is not expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{label}_violation")
            else:
                if label == "remote_calls_zero":
                    result["remote_calls_zero"] = True
                elif label == "llm_calls_zero":
                    result["llm_calls_zero"] = True
                elif label == "prompt_construction_false":
                    result["prompt_construction_false"] = True
                elif label == "source_reads_not_attempted_or_bounded":
                    result["source_reads_not_attempted_or_bounded"] = True
        else:
            result["safety_warnings"].append(f"missing_{label}")

    check(cfg.get("remote"), 0, "remote_calls_zero", blocker=True)
    check(cfg.get("llm"), 0, "llm_calls_zero", blocker=True)
    check(cfg.get("remote_requests"), 0, "remote_requests_zero", blocker=True)
    check(cfg.get("prompt"), False, "prompt_construction_false", blocker=True)

    source_reads_key = cfg.get("source_reads")
    if source_reads_key:
        attempted = data.get(source_reads_key)
        if attempted is not False:
            result["safety_blocker"] = True
            result["safety_warnings"].append("source_reads_unexpected")
        else:
            result["source_reads_not_attempted_or_bounded"] = True

    check(cfg.get("provider_config"), False, "provider_config_read_false", blocker=True)

    extra: dict[str, Any] = {}
    if phase == "p51b":
        extra = P51B_EXTRA
    elif phase == "p60":
        extra = P60_EXTRA
    elif phase == "p59":
        extra = P59_EXTRA
    for key, expected in extra.items():
        if key in data:
            if data[key] != expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{key}_violation")
        else:
            result["safety_warnings"].append(f"missing_{key}")

    if data.get("promotion_ready") is False and data.get("default_should_change") is False and data.get("evidencecore_semantics_changed") is False:
        result["promotion_default_false"] = True
    if data.get("candidate_not_fact") is True:
        result["candidate_not_fact_true"] = True
    if data.get("aggregate_only_public_artifact") is True:
        result["aggregate_only_true"] = True

    return result


def _evaluate_slice(slice_data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "required_present": [],
        "required_missing": [],
        "invalid_json": False,
        "self_test": False,
        "blocked_safety": False,
        "status_acceptable": False,
        "eligible": False,
        "safety_by_phase": {},
        "phase_status": {},
        "slice_dir": bool(slice_data.get("_slice_dir")),
    }
    for phase in P62_REQUIRED_PHASES:
        data = slice_data.get(phase)
        if data is None or data.get("_invalid_json"):
            result["required_missing"].append(phase)
            if data and data.get("_invalid_json"):
                result["invalid_json"] = True
        else:
            result["required_present"].append(phase)
        result["phase_status"][phase] = _safe_status(data)

    if result["required_missing"]:
        return result

    for phase in P62_REQUIRED_PHASES:
        data = slice_data.get(phase)
        if data and (data.get("self_test") is True or data.get("status") == "self_test_only"):
            result["self_test"] = True

    for phase in P62_REQUIRED_PHASES:
        v = _verify_phase_safety(phase, slice_data.get(phase))
        result["safety_by_phase"][phase] = v
        if v["safety_blocker"]:
            result["blocked_safety"] = True

    status_acceptable = True
    for phase in P62_REQUIRED_PHASES:
        data = slice_data.get(phase)
        status = data.get("status") if data else None
        if status not in ACCEPTABLE_STATUS.get(phase, set()):
            status_acceptable = False
    result["status_acceptable"] = status_acceptable

    result["eligible"] = (
        not result["required_missing"]
        and not result["invalid_json"]
        and not result["self_test"]
        and not result["blocked_safety"]
        and result["status_acceptable"]
    )
    return result


def _get_path(data: Any, path: list[str]) -> Any:
    value = data
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def _canonical_summary(slice_data: dict[str, Any]) -> dict[str, Any]:
    p57 = slice_data.get("p57") or {}
    p58 = slice_data.get("p58") or {}
    p59 = slice_data.get("p59") or {}
    p60 = slice_data.get("p60") or {}
    p51b = slice_data.get("p51b") or {}

    summary: dict[str, Any] = {}
    summary["schema_versions"] = {
        phase: (slice_data.get(phase) or {}).get("schema_version")
        for phase in P62_REQUIRED_PHASES
    }
    summary["statuses"] = {
        phase: (slice_data.get(phase) or {}).get("status")
        for phase in P62_REQUIRED_PHASES
    }
    summary["generated_by"] = {
        phase: (slice_data.get(phase) or {}).get("generated_by")
        for phase in P62_REQUIRED_PHASES
    }
    summary["stages"] = {
        phase: (slice_data.get(phase) or {}).get("stage")
        for phase in P62_REQUIRED_PHASES
    }

    for phase in P62_REQUIRED_PHASES:
        data = slice_data.get(phase)
        summary[f"{phase}_safety"] = {
            "promotion_ready": data.get("promotion_ready") if data else None,
            "default_should_change": data.get("default_should_change") if data else None,
            "evidencecore_semantics_changed": data.get("evidencecore_semantics_changed") if data else None,
            "candidate_not_fact": data.get("candidate_not_fact") if data else None,
            "aggregate_only_public_artifact": data.get("aggregate_only_public_artifact") if data else None,
        }

    p57_input = p57.get("input_summary") or {}
    summary["p57_input_summary"] = {
        "slice_count": p57_input.get("slice_count"),
        "slice_count_with_all_required_reports": p57_input.get("slice_count_with_all_required_reports"),
        "included_generalization_slice_count": p57_input.get("included_generalization_slice_count"),
        "self_test_slice_count": p57_input.get("self_test_slice_count"),
    }

    p58_cd = p58.get("calibration_denominators") or {}
    p58_sbc = p58.get("source_backed_coverage") or {}
    p58_rmc = p58.get("request_more_context_calibration") or {}
    p58_lv = p58.get("local_verifier_priority_calibration") or {}
    p58_p51c = p58.get("p51c_eligibility_calibration") or {}
    summary["p58_calibration"] = {
        "calibration_denominator_available": p58_cd.get("calibration_denominator_available"),
        "p48_selected_count": p58_cd.get("p48_selected_count"),
        "p48_request_more_context_count": p58_cd.get("p48_request_more_context_count"),
        "p51b_eligible_candidate_count": p58_cd.get("p51b_eligible_candidate_count"),
        "p52c_candidate_denominator": p58_cd.get("p52c_candidate_denominator"),
        "source_backed_coverage_bucket": p58_sbc.get("source_backed_coverage_bucket"),
        "p52c_score_availability": p58_sbc.get("p52c_score_availability"),
        "request_more_context_hint_bucket": p58_rmc.get("hint_bucket"),
        "local_verifier_priority_hint_bucket": p58_lv.get("hint_bucket"),
        "p51c_eligibility_hint_bucket": p58_p51c.get("hint_bucket"),
        "p51c_eligible_candidate_rate": p58_p51c.get("eligible_candidate_rate"),
    }

    p59_by_strategy = (p59.get("metrics") or {}).get("by_strategy") or {}
    p59_anchor = p59_by_strategy.get("anchor_contrast_pack_v0") or {}
    p59_cov = p59_anchor.get("contrastive_information_coverage") or {}
    p59_cf = p59_anchor.get("counterfactual_actionability") or {}
    p59_denom = p59_anchor.get("denominators") or {}
    summary["p59_coverage"] = {
        "task_count": p59_denom.get("task_count"),
        "positive_task_count": p59_denom.get("positive_task_count"),
        "no_gold_task_count": p59_denom.get("no_gold_task_count"),
        "pack_nonempty_count": p59_denom.get("pack_nonempty_count"),
        "hard_distractor_pack_rate": p59_cov.get("hard_distractor_pack_rate"),
        "cross_file_competitor_pack_rate": p59_cov.get("cross_file_competitor_pack_rate"),
        "path_kind_diverse_pack_rate": p59_cov.get("path_kind_diverse_pack_rate"),
        "llm_spend_actionability_bucket": p59_cf.get("llm_spend_actionability_bucket"),
    }

    p60_by_policy = (p60.get("metrics") or {}).get("by_policy") or {}
    p60_first = next(iter(p60_by_policy.values())) if p60_by_policy else {}
    p60_cmp = p60.get("comparison_frame") or {}
    summary["p60_matrix"] = {
        "comparison_denominator_aligned": p60_cmp.get("comparison_denominator_aligned"),
        "no_winner_selected": p60_cmp.get("no_winner_selected"),
        "no_default_recommendation": p60_cmp.get("no_default_recommendation"),
        "policy_comparison_not_ranking": p60_cmp.get("policy_comparison_not_ranking"),
        "candidate_denominator": p60_first.get("candidate_denominator"),
        "rmc_candidate_count": p60_first.get("rmc_candidate_count"),
        "next_action_counts": p60_first.get("next_action_counts"),
    }

    p51b_metrics = p51b.get("metrics") or {}
    p51b_elig = p51b_metrics.get("eligibility") or {}
    p51b_blueprint = p51b_metrics.get("request_envelope_blueprint") or {}
    p51b_schema = p51b_metrics.get("role_output_schema_validation") or {}
    p51b_gate = p51b_metrics.get("future_live_gate_readiness") or {}
    summary["p51b_contract"] = {
        "eligible_candidate_count": p51b_elig.get("eligible_candidate_count"),
        "eligible_candidate_rate": p51b_elig.get("eligible_candidate_rate"),
        "eligible_pack_count": p51b_elig.get("eligible_pack_count"),
        "eligibility_availability": p51b_elig.get("eligibility_availability"),
        "source_backed_live_eligibility_available": p51b_elig.get("source_backed_live_eligibility_available"),
        "request_envelope_blueprint_count": p51b_blueprint.get("request_envelope_blueprint_count"),
        "max_budget_violation_rate": p51b_blueprint.get("max_budget_violation_rate"),
        "redaction_required_rate": p51b_blueprint.get("redaction_required_rate"),
        "role_output_schema_valid_rate": p51b_schema.get("role_output_schema_valid_rate"),
        "p51b_live_gate_ready": p51b_gate.get("p51b_live_gate_ready"),
    }

    return summary


def _signature(summary: dict[str, Any]) -> str:
    payload = json.dumps(summary, indent=None, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_rates_for_dispersion(slices: list[dict[str, Any]]) -> list[float]:
    rates: list[float] = []
    for slice_data in slices:
        p58 = slice_data.get("p58") or {}
        p58_p51c = p58.get("p51c_eligibility_calibration") or {}
        r = _as_float(p58_p51c.get("eligible_candidate_rate"))
        if r is not None:
            rates.append(r)
        p59 = slice_data.get("p59") or {}
        p59_by_strategy = (p59.get("metrics") or {}).get("by_strategy") or {}
        p59_anchor = p59_by_strategy.get("anchor_contrast_pack_v0") or {}
        p59_cov = p59_anchor.get("contrastive_information_coverage") or {}
        for key in ("hard_distractor_pack_rate", "cross_file_competitor_pack_rate", "path_kind_diverse_pack_rate"):
            r = _as_float(p59_cov.get(key))
            if r is not None:
                rates.append(r)
        p51b = slice_data.get("p51b") or {}
        p51b_elig = (p51b.get("metrics") or {}).get("eligibility") or {}
        r = _as_float(p51b_elig.get("eligible_candidate_rate"))
        if r is not None:
            rates.append(r)
    return rates


def _dispersion(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None, "iqr": None}
    s = sorted(values)
    n = len(s)
    return {
        "n": n,
        "min": round(s[0], 6),
        "median": round(_percentile(s, 0.5) or 0.0, 6),
        "max": round(s[-1], 6),
        "iqr": round((_percentile(s, 0.75) or 0.0) - (_percentile(s, 0.25) or 0.0), 6),
    }


def _build_p57_input_matrix(eligible_slices: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    matrix: list[dict[str, Any]] = []
    excluded_count = 0
    for slice_data in eligible_slices:
        p57_paths = slice_data.get("_p57_paths") or {}
        if not p57_paths:
            excluded_count += 1
            continue
        if all(phase in p57_paths for phase in P57_REQUIRED_PHASES):
            entry: dict[str, Any] = {}
            for phase in P57_REQUIRED_PHASES:
                entry[f"{phase}_report"] = p57_paths[phase]
            for phase in P57_OPTIONAL_PHASES:
                if phase in p57_paths:
                    entry[f"{phase}_report"] = p57_paths[phase]
            matrix.append(entry)
        else:
            excluded_count += 1
    return matrix, excluded_count


def _determine_status(
    provided_input_count: int,
    eligible_distinct_slice_count: int,
    blocked_safety_input_count: int,
    self_test: bool,
    p57_statuses: list[str],
) -> str:
    if self_test:
        return "self_test_only"
    if blocked_safety_input_count > 0:
        return "blocked_safety"
    if eligible_distinct_slice_count < REQUIRED_SLICE_COUNT:
        return "insufficient_matrix_inputs"
    if all(status == "diagnostic_matrix_complete" for status in p57_statuses):
        return "diagnostic_matrix_complete"
    return "diagnostic_matrix_unstable"


def _build_report(
    slices: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    p57_matrix_out: Path | None,
) -> dict[str, Any]:
    provided_input_count = len(slices)
    readable_input_count = 0
    required_complete_input_count = 0
    safe_input_count = 0
    self_test_input_count = 0
    blocked_safety_input_count = 0
    missing_required_input_count = 0
    invalid_json_input_count = 0

    slice_meta: list[dict[str, Any]] = []
    all_signatures: dict[str, dict[str, Any]] = {}
    signature_eligible: dict[str, bool] = {}
    duplicate_input_count = 0

    for slice_data in slices:
        meta = _evaluate_slice(slice_data)
        readable_input_count += 1
        if meta["required_missing"]:
            missing_required_input_count += 1
        if meta["invalid_json"]:
            invalid_json_input_count += 1
        if not meta["required_missing"]:
            required_complete_input_count += 1
        if meta["self_test"]:
            self_test_input_count += 1
        if meta["blocked_safety"]:
            blocked_safety_input_count += 1
        if not meta["required_missing"] and not meta["invalid_json"] and not meta["self_test"] and not meta["blocked_safety"]:
            safe_input_count += 1
        slice_meta.append(meta)

        # Build canonical summary for every readable input (not only eligible) so
        # duplicate detection covers all provided aggregate report sets.
        summary = _canonical_summary(slice_data)
        sig = _signature(summary)
        if sig in all_signatures:
            duplicate_input_count += 1
        else:
            all_signatures[sig] = slice_data
            signature_eligible[sig] = bool(meta["eligible"])

    content_distinct_input_count = len(all_signatures)
    eligible_distinct_slices = [
        slice_data for sig, slice_data in all_signatures.items() if signature_eligible.get(sig)
    ]
    eligible_distinct_slice_count = len(eligible_distinct_slices)
    exact_duplicate_inputs_rejected_count = duplicate_input_count

    p57_statuses = [
        str((slice_data.get("p57") or {}).get("status"))
        for slice_data in eligible_distinct_slices
    ]

    status = _determine_status(
        provided_input_count,
        eligible_distinct_slice_count,
        blocked_safety_input_count,
        self_test,
        p57_statuses,
    )

    blockers: list[str] = []
    warnings: list[str] = []

    if provided_input_count < REQUIRED_SLICE_COUNT:
        blockers.append(f"provided_input_count={provided_input_count} < required {REQUIRED_SLICE_COUNT}.")
    if eligible_distinct_slice_count < REQUIRED_SLICE_COUNT:
        blockers.append(
            f"eligible_distinct_slice_count={eligible_distinct_slice_count} < required {REQUIRED_SLICE_COUNT}."
        )
    if blocked_safety_input_count > 0:
        blockers.append(f"blocked_safety_input_count={blocked_safety_input_count}.")
    if missing_required_input_count > 0:
        blockers.append(f"missing_required_report_input_count={missing_required_input_count}.")
    if invalid_json_input_count > 0:
        blockers.append(f"invalid_json_input_count={invalid_json_input_count}.")
    if self_test_input_count > 0:
        blockers.append(f"self_test_input_count={self_test_input_count}; real inputs required for generalization matrix.")
    if duplicate_input_count > 0:
        warnings.append(f"duplicate_input_count={duplicate_input_count}; duplicate sanitized aggregate signatures were collapsed.")

    per_stage_status_summary: dict[str, Any] = {}
    for phase in P62_REQUIRED_PHASES:
        total = provided_input_count
        acceptable = 0
        blocked = 0
        self_test_only_count = 0
        unstable = 0
        for meta in slice_meta:
            v = meta["safety_by_phase"].get(phase)
            phase_status = meta.get("phase_status", {}).get(phase, "not_provided")
            if v and v.get("safety_blocker"):
                blocked += 1
            elif phase_status == "self_test_only":
                self_test_only_count += 1
            elif phase_status in ACCEPTABLE_STATUS.get(phase, set()):
                acceptable += 1
                if phase == "p57" and phase_status in {"insufficient_matrix", "diagnostic_matrix_unstable"}:
                    unstable += 1
        per_stage_status_summary[phase] = {
            "acceptable_rate": round(acceptable / total, 6) if total > 0 else None,
            "blocked_safety_rate": round(blocked / total, 6) if total > 0 else None,
            "self_test_rate": round(self_test_only_count / total, 6) if total > 0 else None,
            "unstable_rate": round(unstable / total, 6) if total > 0 else None,
        }

    safe_rates = _safe_rates_for_dispersion(eligible_distinct_slices)
    cross_slice_dispersion = _dispersion(safe_rates)

    observed_slice_count = provided_input_count
    included_generalization_slice_count = eligible_distinct_slice_count

    if status == "diagnostic_matrix_complete":
        readiness_status = "matrix_complete"
    elif status == "diagnostic_matrix_unstable":
        readiness_status = "matrix_unstable"
    elif status == "insufficient_matrix_inputs":
        readiness_status = "insufficient_inputs"
    elif status == "blocked_safety":
        readiness_status = "blocked_safety"
    else:
        readiness_status = "self_test_only"

    matrix_requirement_summary = (
        "self_test_only" if self_test
        else "blocked_safety" if blocked_safety_input_count > 0
        else "insufficient_inputs" if eligible_distinct_slice_count < REQUIRED_SLICE_COUNT
        else "unstable_matrix" if status == "diagnostic_matrix_unstable"
        else "complete_matrix"
    )

    input_summary: dict[str, Any] = {
        "provided_input_count": provided_input_count,
        "readable_input_count": readable_input_count,
        "required_report_set_complete_input_count": required_complete_input_count,
        "safe_input_count": safe_input_count,
        "content_distinct_input_count": content_distinct_input_count,
        "eligible_distinct_slice_count": eligible_distinct_slice_count,
        "required_distinct_slice_count": REQUIRED_SLICE_COUNT,
        "self_test_input_count": self_test_input_count,
        "blocked_safety_input_count": blocked_safety_input_count,
        "missing_required_report_input_count": missing_required_input_count,
        "invalid_json_input_count": invalid_json_input_count,
        "duplicate_input_count": duplicate_input_count,
        "exact_duplicate_inputs_rejected_count": exact_duplicate_inputs_rejected_count,
        "matrix_requirement_summary": matrix_requirement_summary,
    }

    distinctness: dict[str, Any] = {
        "distinctness_claim": "content_distinct_sanitized_aggregate_report_sets_only_not_repo_or_dataset_identity",
        "identity_fields_used": False,
        "identity_fields_published": False,
        "signature_values_published": False,
    }

    generalization_matrix: dict[str, Any] = {
        "readiness_status": readiness_status,
        "required_slice_count": REQUIRED_SLICE_COUNT,
        "observed_slice_count": observed_slice_count,
        "included_generalization_slice_count": included_generalization_slice_count,
        "observed_repo_count": "not_collected_publicly",
        "per_stage_status_summary": per_stage_status_summary,
        "cross_slice_dispersion": cross_slice_dispersion,
    }

    by_phase: dict[str, Any] = {}
    safety_blocker_count = 0
    safety_warning_count = 0
    checked_count = 0
    for phase in P62_REQUIRED_PHASES:
        merged: dict[str, Any] = {
            "report_present": False,
            "status": "not_provided",
            "safety_blocker": False,
            "safety_warnings": [],
        }
        for meta in slice_meta:
            v = meta["safety_by_phase"].get(phase)
            if not v:
                continue
            if v["report_present"]:
                merged["report_present"] = True
                checked_count += 1
            if v["status"] and v["status"] != "not_provided":
                merged["status"] = v["status"]
            if v["safety_blocker"]:
                merged["safety_blocker"] = True
            merged["safety_warnings"] = list(set(merged["safety_warnings"]) | set(v["safety_warnings"]))
        if merged["safety_blocker"]:
            safety_blocker_count += 1
        safety_warning_count += len(merged["safety_warnings"])
        by_phase[phase] = merged

    upstream_safety_gate = {
        "checked_count": checked_count,
        "blocker_count": safety_blocker_count,
        "warning_count": safety_warning_count,
        "by_phase": by_phase,
    }

    p57_matrix, p57_excluded_count = _build_p57_input_matrix(eligible_distinct_slices)
    if p57_excluded_count > 0:
        warnings.append(f"{p57_excluded_count} eligible distinct slice(s) lacked all P57-required reports and were excluded from the P57 input-matrix handoff.")
    p57_input_matrix_written = eligible_distinct_slice_count >= REQUIRED_SLICE_COUNT and bool(p57_matrix)
    p57_consumption_contract: dict[str, Any] = {
        "p57_may_consume_this_report": True,
        "requires_explicit_p57_support": False,
        "do_not_substitute_as_p57_report_without_validation": True,
        "p57_input_matrix_written": p57_input_matrix_written,
        "p57_input_matrix_entry_count": len(p57_matrix),
        "p57_input_matrix_excluded_slice_count": p57_excluded_count,
        "p57_slice_count_field_source": "eligible_distinct_slice_count",
    }

    if p57_matrix_out is not None:
        if eligible_distinct_slice_count >= REQUIRED_SLICE_COUNT:
            _write_json(p57_matrix_out, p57_matrix)
        else:
            _write_json(p57_matrix_out, [])

    conclusion: list[str] = [
        "P62 Generalization Matrix Aggregator v0 is a deterministic, aggregate-only diagnostic that combines sanitized per-slice aggregate report sets.",
        "P62 does not read source files, gold labels, private labels, ephemeral records, candidate pools, prompts, responses, or provider configs.",
        "P62 does not call providers, construct prompts, admit Evidence, change defaults, or authorize spend.",
        "P62 reports only aggregate counts and internally-deduplicated sanitized signatures; it does not publish repo identities, datasets, paths, digests, or signatures.",
        "P62 does not claim that multiple distinct repositories, dataset diversity, proven generalization, research-quality findings, promotion readiness, default change, or provider spend authorization have been established.",
    ]
    if self_test:
        conclusion.append("This self-test exercised the distinctness-dedupe, missing-report, unsafe-slice, and insufficient-input paths with synthetic aggregate reports.")
    if blockers:
        conclusion.append(f"Generalization blocker(s): {len(blockers)}.")
    if warnings:
        conclusion.append(f"Warning(s): {len(warnings)}.")
    conclusion.append(
        f"Current status: {status}. "
        f"Distinct sanitized aggregate report sets observed: {content_distinct_input_count}; "
        f"eligible distinct slices included: {included_generalization_slice_count}."
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": "; ".join(blockers) if blockers else "aggregate generalization matrix evaluation complete",
        "self_test": self_test,
        "not_quality_evidence": True,
        "precondition_report_only": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "remote_calls_by_p62": 0,
        "llm_calls_by_p62": 0,
        "remote_requests_by_p62": 0,
        "provider_config_read_by_p62": False,
        "prompt_construction_by_p62": False,
        "source_reads_attempted_by_p62": False,
        "gold_used_by_p62": False,
        "private_labels_loaded_by_p62": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_query_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "private_labels_committed": False,
        "elapsed_ms": elapsed_ms,
        "input_summary": input_summary,
        "distinctness": distinctness,
        "generalization_matrix": generalization_matrix,
        "upstream_safety_gate": upstream_safety_gate,
        "p57_consumption_contract": p57_consumption_contract,
        "blockers": blockers,
        "warnings": warnings,
        "conclusion": conclusion,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P62 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        errors.append("generated_by mismatch")
    if report.get("stage") != STAGE:
        errors.append("stage mismatch")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")

    for flag, expected in [
        ("remote_calls_by_p62", 0),
        ("llm_calls_by_p62", 0),
        ("remote_requests_by_p62", 0),
    ]:
        if report.get(flag) != expected:
            errors.append(f"{flag} must be {expected}")

    for flag in [
        "provider_config_read_by_p62",
        "prompt_construction_by_p62",
        "source_reads_attempted_by_p62",
        "gold_used_by_p62",
        "private_labels_loaded_by_p62",
    ]:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    expected_true = {
        "not_quality_evidence",
        "precondition_report_only",
        "candidate_not_fact",
        "aggregate_only_public_artifact",
    }
    expected_false = {
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "raw_text_stored",
        "raw_source_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_snippets_sent_to_provider",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_query_stored",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "provider_keys_in_artifact",
        "gold_spans_in_artifact",
        "private_labels_committed",
    }
    for flag in expected_true:
        if report.get(flag) is not True:
            errors.append(f"{flag} must be true")
    for flag in expected_false:
        if report.get(flag) is not False:
            errors.append(f"{flag} must be false")

    if report.get("self_test") and report.get("status") != "self_test_only":
        errors.append("self_test must set status=self_test_only")
    if report.get("status") == "self_test_only" and report.get("self_test") is not True:
        errors.append("status self_test_only requires self_test=true")

    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "per_slice_rows", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))

    secret_patterns = [
        re.compile(r"(?i)(api_key|base_url)\s*[:=]"),
        re.compile(r"(?i)authorization\s*[:=]"),
    ]
    text_fields: list[str] = []
    for field in ("status_reason", "conclusion", "warnings", "blockers"):
        val = report.get(field)
        if isinstance(val, str):
            text_fields.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    text_fields.append(item)
    for text in text_fields:
        for pattern in secret_patterns:
            if pattern.search(text):
                errors.append(f"text field matches forbidden secret pattern: {pattern.pattern}")

    forbidden_claims = [
        "four distinct repos",
        "dataset diversity proven",
        "generalization proven",
        "quality evidence",
        "promotion ready",
        "default should change",
        "P51-C authorized",
        "provider spend authorized",
        "live-readiness proven",
    ]
    for text in text_fields:
        lower = text.lower()
        for claim in forbidden_claims:
            if claim in lower:
                errors.append(f"forbidden claim in text: {claim}")

    return errors


def _fmt_scalar(x: Any) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P62: {report['remote_calls_by_p62']}",
        f"- LLM calls by P62: {report['llm_calls_by_p62']}",
        f"- Prompt construction by P62: {report['prompt_construction_by_p62']}",
        f"- Source reads attempted by P62: {report['source_reads_attempted_by_p62']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P62 Generalization Matrix Aggregator v0 combines multiple per-slice aggregate diagnostic report-sets into a generalization matrix. ",
        "It is **not** quality evidence, **not** a promotion/default gate, **not** live-readiness evidence, and **not** provider authorization. ",
        "P62 emits only aggregate counts and internally deduplicated sanitized signatures; it never publishes repo identities, datasets, paths, digests, or signatures.",
        "",
        "## Methodology",
        "",
        "- Accept a JSON slice manifest. Each entry either points to a `slice_dir` with fixed aggregate report filenames, or supplies explicit paths for the five required reports.",
        "- Require all five reports per slice: P57, P58, P59, P60, and P51-B.",
        "- Reject self-test slices, invalid JSON, missing reports, safety-flag violations, and unacceptable statuses.",
        "- Build a canonical sanitized summary per eligible slice using only safe aggregate fields (schema versions, statuses, safety flags, aggregate counts/rates).",
        "- Deterministically serialize and SHA-256 the summary internally; collapse identical signatures so duplicate inputs cannot inflate slice_count.",
        "    - Publish only counts: `content_distinct_input_count`, `duplicate_input_count`, `eligible_distinct_slice_count`, `exact_duplicate_inputs_rejected_count`.",
        "- If four or more distinct eligible slices exist, write a P57-compatible `--input-matrix` JSON handoff containing only the P57-required report paths.",
        "",
        "## Safety notes",
        "",
        "- P62 makes no remote or LLM calls and does not construct prompts.",
        "- P62 does not read source files, gold labels, private labels, ephemeral records, candidate pools, or provider configs.",
        "- P62 does not publish task IDs, candidate IDs, repo IDs, datasets, paths, spans, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P62 output is not Evidence and does not support default, promotion, or provider-spend decisions.",
        "",
    ])

    inp = report["input_summary"]
    lines.extend([
        "## Input summary",
        "",
        f"- Provided inputs: {inp['provided_input_count']}",
        f"- Readable inputs: {inp['readable_input_count']}",
        f"- Required report-set complete: {inp['required_report_set_complete_input_count']}",
        f"- Safe inputs: {inp['safe_input_count']}",
        f"- Content-distinct sanitized inputs: {inp['content_distinct_input_count']}",
        f"- Eligible distinct slices: {inp['eligible_distinct_slice_count']}",
        f"- Required distinct slices: {inp['required_distinct_slice_count']}",
        f"- Self-test inputs: {inp['self_test_input_count']}",
        f"- Blocked-safety inputs: {inp['blocked_safety_input_count']}",
        f"- Missing required report inputs: {inp['missing_required_report_input_count']}",
        f"- Invalid JSON inputs: {inp['invalid_json_input_count']}",
        f"- Duplicate inputs collapsed: {inp['duplicate_input_count']}",
        f"- Exact duplicate inputs rejected: {inp['exact_duplicate_inputs_rejected_count']}",
        f"- Matrix requirement summary: `{inp['matrix_requirement_summary']}`",
        "",
    ])

    dist = report["distinctness"]
    lines.extend([
        "## Distinctness",
        "",
        f"- Distinctness claim: `{dist['distinctness_claim']}`",
        f"- Identity fields used: {dist['identity_fields_used']}",
        f"- Identity fields published: {dist['identity_fields_published']}",
        f"- Signature values published: {dist['signature_values_published']}",
        "",
    ])

    gm = report["generalization_matrix"]
    lines.extend([
        "## Generalization matrix",
        "",
        f"- Readiness status: `{gm['readiness_status']}`",
        f"- Required slice count: {gm['required_slice_count']}",
        f"- Observed slice count: {gm['observed_slice_count']}",
        f"- Included generalization slice count: {gm['included_generalization_slice_count']}",
        f"- Observed repo count: {gm['observed_repo_count']}",
        "",
        "### Per-stage status summary",
        "",
        "| Phase | Acceptable rate | Blocked safety rate | Self-test rate | Unstable rate |",
        "|---|---|---|---|---|",
    ])
    for phase in P62_REQUIRED_PHASES:
        s = gm["per_stage_status_summary"][phase]
        lines.append(
            f"| {phase} | {_fmt_scalar(s['acceptable_rate'])} | {_fmt_scalar(s['blocked_safety_rate'])} | "
            f"{_fmt_scalar(s['self_test_rate'])} | {_fmt_scalar(s['unstable_rate'])} |"
        )
    lines.append("")

    disp = gm["cross_slice_dispersion"]
    lines.extend([
        "### Cross-slice dispersion of safe aggregate rates",
        "",
        f"- n: {disp['n']}",
        f"- min: {_fmt_scalar(disp['min'])}",
        f"- median: {_fmt_scalar(disp['median'])}",
        f"- max: {_fmt_scalar(disp['max'])}",
        f"- iqr: {_fmt_scalar(disp['iqr'])}",
        "",
    ])

    sg = report["upstream_safety_gate"]
    lines.extend([
        "## Upstream safety gate",
        "",
        f"- Checked phase instances: {sg['checked_count']}",
        f"- Safety blocker phases: {sg['blocker_count']}",
        f"- Safety warning count: {sg['warning_count']}",
        "",
        "| Phase | Present | Status | Safety blocker | Warnings |",
        "|---|---|---|---|---|",
    ])
    for phase in P62_REQUIRED_PHASES:
        v = sg["by_phase"].get(phase, {})
        lines.append(
            f"| {phase} | {v.get('report_present', False)} | `{v.get('status', 'not_provided')}` | "
            f"{v.get('safety_blocker', False)} | {len(v.get('safety_warnings', []))} |"
        )
    lines.append("")

    pc = report["p57_consumption_contract"]
    lines.extend([
        "## P57 consumption contract",
        "",
        f"- P57 may consume this report: {pc['p57_may_consume_this_report']}",
        f"- Requires explicit P57 support: {pc['requires_explicit_p57_support']}",
        f"- Do not substitute as P57 report without validation: {pc['do_not_substitute_as_p57_report_without_validation']}",
        f"- P57 input matrix written: {pc['p57_input_matrix_written']}",
        f"- P57 input matrix entry count: {pc.get('p57_input_matrix_entry_count', 0)}",
        f"- P57 input matrix excluded slice count: {pc.get('p57_input_matrix_excluded_slice_count', 0)}",
        f"- P57 slice-count field source: `{pc['p57_slice_count_field_source']}`",
        "",
    ])

    lines.extend([
        "## Blockers",
        "",
    ])
    if report["blockers"]:
        for b in report["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Warnings",
        "",
    ])
    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend([
        "## Conclusion",
        "",
    ])
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def _make_safe_base_report(phase: str, status: str, self_test: bool = False) -> dict[str, Any]:
    cfg = PHASE_SAFETY.get(phase, {})
    report: dict[str, Any] = {
        "schema_version": f"{phase}-aggregate-report-v0",
        "status": status,
        "self_test": self_test,
        "not_quality_evidence": self_test,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
    }
    for flag in RAW_FLAGS:
        report[flag] = False
    remote_key = cfg.get("remote")
    if remote_key:
        report[remote_key] = 0
    llm_key = cfg.get("llm")
    if llm_key:
        report[llm_key] = 0
    remote_requests_key = cfg.get("remote_requests")
    if remote_requests_key:
        report[remote_requests_key] = 0
    prompt_key = cfg.get("prompt")
    if prompt_key:
        report[prompt_key] = False
    source_reads_key = cfg.get("source_reads")
    if source_reads_key:
        report[source_reads_key] = False
    provider_config_key = cfg.get("provider_config")
    if provider_config_key:
        report[provider_config_key] = False
    extra: dict[str, Any] = {}
    if phase == "p51b":
        extra = P51B_EXTRA
    elif phase == "p60":
        extra = P60_EXTRA
    elif phase == "p59":
        extra = P59_EXTRA
    for key, expected in extra.items():
        report[key] = expected
    return report


def _make_eligible_slice(seed: int) -> dict[str, Any]:
    slice_data: dict[str, Any] = {"_slice_dir": None, "_p57_paths": {}}
    p57 = _make_safe_base_report("p57", "diagnostic_matrix_complete")
    p57["input_summary"] = {
        "slice_count": 1,
        "slice_count_with_all_required_reports": 1,
        "included_generalization_slice_count": 1,
        "self_test_slice_count": 0,
        "required_present_count": 10,
        "required_missing": [],
    }
    p57["generalization_matrix"] = {
        "readiness_status": "diagnostic_matrix_complete",
        "required_slice_count": 4,
        "required_min_repo_count": 3,
        "observed_slice_count": 1,
        "observed_repo_count": "unavailable",
        "observed_task_count_aggregate": 10 + seed,
        "per_phase_availability": {p: "available" for p in [
            "p46", "p47", "p48", "p49", "p50", "p52", "p52a", "p52b", "p52c", "p51", "p51b"
        ]},
        "per_phase_status_summary": {p: "ok" for p in [
            "p46", "p47", "p48", "p49", "p50", "p52", "p52a", "p52b", "p52c", "p51", "p51b"
        ]},
        "dispersion": "unavailable",
        "worst_slice_task_count": "unavailable",
        "worst_slice_required_reports_missing": "unavailable",
        "coverage_summary": "positive=5 no_gold=2",
    }
    slice_data["p57"] = p57

    p58 = _make_safe_base_report("p58", "diagnostic_calibration_available")
    p58["calibration_denominators"] = {
        "calibration_denominator_available": "available",
        "p48_selected_count": 100 + seed,
        "p48_request_more_context_count": 20 + seed,
        "p51b_candidate_denominator": 100,
        "p51b_eligible_candidate_count": 40 + seed,
        "p52c_candidate_denominator": 100,
        "p52c_score_candidate_denominator": 95,
    }
    p58["source_backed_coverage"] = {
        "source_backed_coverage_bucket": "source_backed_available",
        "p52c_score_availability": "available_source_backed",
        "source_backed_score_candidate_denominator": 60,
        "metadata_only_candidate_denominator": 35,
        "score_unavailable_candidate_rate": 0.05,
    }
    p58["request_more_context_calibration"] = {"hint_bucket": "medium"}
    p58["local_verifier_priority_calibration"] = {"hint_bucket": "high"}
    p58["p51c_eligibility_calibration"] = {
        "hint_bucket": "p51c_planning_source_backed",
        "eligible_candidate_rate": round(0.40 + seed * 0.01, 6),
        "eligibility_availability": "available_source_backed",
        "source_backed_live_eligibility_available": True,
    }
    slice_data["p58"] = p58

    p59 = _make_safe_base_report("p59", "diagnostic_coverage_available")
    p59["metrics"] = {
        "by_strategy": {
            "anchor_contrast_pack_v0": {
                "denominators": {
                    "task_count": 8 + seed,
                    "positive_task_count": 7,
                    "no_gold_task_count": 1,
                    "pack_build_denominator": 8,
                    "pack_nonempty_count": 8,
                },
                "contrastive_information_coverage": {
                    "hard_distractor_pack_rate": round(0.25 + seed * 0.01, 6),
                    "cross_file_competitor_pack_rate": 0.875,
                    "path_kind_diverse_pack_rate": 0.5,
                },
                "counterfactual_actionability": {
                    "llm_spend_actionability_bucket": "actionable",
                },
            }
        }
    }
    slice_data["p59"] = p59

    p60 = _make_safe_base_report("p60", "diagnostic_policy_matrix_available")
    p60["comparison_frame"] = {
        "comparison_denominator_aligned": True,
        "same_input_records_for_all_policies": True,
        "no_winner_selected": True,
        "no_default_recommendation": True,
        "policy_comparison_not_ranking": True,
    }
    p60["metrics"] = {
        "by_policy": {
            "baseline_p25_bucket_routed_v0": {
                "candidate_denominator": 16 + seed,
                "rmc_candidate_count": 16,
                "next_action_counts": {
                    "local_verifier": 0,
                    "contrastive_pack": 9,
                    "p51c_span_narrow": 1,
                    "filter": 4,
                    "weak_candidate_only": 2,
                },
                "rmc_to_llm_eligibility": {
                    "eligible_count": 5 + seed,
                },
            }
        }
    }
    slice_data["p60"] = p60

    p51b = _make_safe_base_report("p51b", "ok")
    p51b["metrics"] = {
        "eligibility": {
            "candidate_denominator": 100,
            "eligible_candidate_count": 40 + seed,
            "eligible_candidate_rate": round(0.40 + seed * 0.01, 6),
            "eligible_pack_count": 10 + seed,
            "eligibility_availability": "available_source_backed",
            "source_backed_live_eligibility_available": True,
        },
        "request_envelope_blueprint": {
            "request_envelope_blueprint_count": 10,
            "max_budget_violation_rate": 0.0,
            "redaction_required_rate": 0.0,
        },
        "role_output_schema_validation": {
            "role_output_schema_valid_rate": 1.0,
        },
        "future_live_gate_readiness": {
            "p51b_live_gate_ready": True,
            "p51b_live_gate_ready_reason": "contract_valid_dry_run_only",
        },
    }
    slice_data["p51b"] = p51b

    return slice_data


def _make_missing_slice() -> dict[str, Any]:
    slice_data = _make_eligible_slice(0)
    slice_data["p60"] = None
    return slice_data


def _make_unsafe_slice() -> dict[str, Any]:
    slice_data = _make_eligible_slice(0)
    p57 = slice_data["p57"]
    p57["promotion_ready"] = True
    return slice_data


def _run_self_test_assertions() -> None:
    slices_a = [_make_eligible_slice(i) for i in range(4)]
    report_a = _build_report(slices_a, self_test=False, elapsed_ms=0, p57_matrix_out=None)
    assert report_a["status"] == "diagnostic_matrix_complete", report_a["status"]
    assert report_a["input_summary"]["content_distinct_input_count"] == 4
    assert report_a["input_summary"]["eligible_distinct_slice_count"] == 4
    assert report_a["input_summary"]["duplicate_input_count"] == 0

    base = _make_eligible_slice(0)
    slices_b = [base, base, base, base]
    report_b = _build_report(slices_b, self_test=False, elapsed_ms=0, p57_matrix_out=None)
    assert report_b["status"] == "insufficient_matrix_inputs", report_b["status"]
    assert report_b["input_summary"]["content_distinct_input_count"] == 1
    assert report_b["input_summary"]["duplicate_input_count"] == 3

    slices_c = [_make_eligible_slice(i) for i in range(3)] + [_make_missing_slice()]
    report_c = _build_report(slices_c, self_test=False, elapsed_ms=0, p57_matrix_out=None)
    assert report_c["status"] == "insufficient_matrix_inputs"
    assert report_c["input_summary"]["missing_required_report_input_count"] == 1

    slices_d = [_make_eligible_slice(i) for i in range(3)] + [_make_unsafe_slice()]
    report_d = _build_report(slices_d, self_test=False, elapsed_ms=0, p57_matrix_out=None)
    assert report_d["status"] == "blocked_safety", report_d["status"]
    assert report_d["input_summary"]["blocked_safety_input_count"] == 1

    slices_e = [_make_eligible_slice(i) for i in range(3)]
    report_e = _build_report(slices_e, self_test=False, elapsed_ms=0, p57_matrix_out=None)
    assert report_e["status"] == "insufficient_matrix_inputs"


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--slice-manifest", type=Path, default=None, help="JSON list of slice entries.")
    parser.add_argument("--p57-input-matrix-out", type=Path, default=DEFAULT_P57_INPUT_MATRIX, help="P57-compatible input matrix output path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()

    if args.self_test:
        _run_self_test_assertions()
        slices: list[dict[str, Any]] = []
    else:
        if args.slice_manifest is None:
            raise SystemExit("Specify --slice-manifest or --self-test")
        slices = _load_slices_from_manifest(args.slice_manifest)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = _build_report(slices, self_test=args.self_test, elapsed_ms=elapsed_ms, p57_matrix_out=args.p57_input_matrix_out)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P62 report written to {args.out}")
    print(f"P62 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
