#!/usr/bin/env python3
"""RPM-D1 bounded offline RPM-small learning smoke.

This phase reads private RPM-D0 state/action JSONL traces only after an explicit
private-input confirmation, validates every row with the Phase 1 schema, runs a
tiny deterministic stdlib-only learner in a leakage-safe offline split, and
writes an aggregate-only public report.  It is a pipeline/learning smoke only:
it never authorizes runtime/default promotion, provider/network/CI execution,
method/scale/winner claims, raw publication, or model scaling.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO / "artifacts" / "rpm_d1_learning_smoke" / "rpm_d1_learning_smoke_report.json"
PRIVATE_TRACE_GLOB = "rpm_d0_private_*/rpm_d0_state_action_traces.jsonl"

REPORT_SCHEMA_VERSION = "rpm_d1_learning_smoke_public_report_v1"
PHASE = "openlocus_v2_rpm_d1_bounded_offline_rpm_small_learning_smoke"
STATUS_INSUFFICIENT = "rpm_d1_learning_smoke_complete_insufficient_real_trace_diversity_no_training_claim"
STATUS_SIGNAL = "rpm_d1_learning_smoke_complete_unexpected_candidate_signal_d2_design_only_no_training_claim"
STATUS_NO_SIGNAL = "rpm_d1_learning_smoke_complete_no_signal_no_training_claim"

AUTHORIZED_D0B = "rpm_d0b_trace_capture_expansion_or_frk_product_workflow_trace_capture"
AUTHORIZED_D2 = "rpm_d2_larger_trace_capture_and_heldout_eval_design"

ALLOWED_FEATURES: tuple[tuple[str, str], ...] = (
    ("task_state", "task_type"),
    ("task_state", "objective_bucket"),
    ("state_features", "query_shape_bucket"),
    ("state_features", "repo_size_bucket"),
    ("state_features", "candidate_count_bucket"),
    ("state_features", "evidence_coverage_bucket"),
    ("state_features", "currentness_bucket"),
    ("state_features", "ambiguity_bucket"),
    ("state_features", "dirty_state_bucket"),
    ("action", "action_type"),
    ("action", "retrieval_budget_bucket"),
    ("action", "source_scan_scope"),
    ("action", "candidate_generation_policy"),
    ("action", "pack_policy"),
    ("policy_learning_support", "eligible_actions_bucket"),
)

FORBIDDEN_PUBLIC_OR_NEXT = {
    "rpm_runtime_default",
    "runtime_default",
    "runtime_default_claim",
    "provider_claim",
    "provider_default",
    "network_claim",
    "network_default",
    "ci_claim",
    "ci_default",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "default_claim",
    "model_scaling",
    "rpm_training",
    "rpm_runtime_or_default",
    "raw_publication",
    "broad_source_scan",
    "candidate_generation_expansion",
    "retrieval_pack_rerun_new_algorithm",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_selector_variants",
    "ldi_b_easy_continuation",
    "ldi_b_easy_slice_continuation",
    "haae_sg",
    "haae_t",
    "r2bv_static_support_repair",
}

REPORT_TOP_LEVEL_KEYS = {
    "schema_version",
    "phase",
    "status",
    "source_checkpoints",
    "execution_attestation",
    "private_input_summary",
    "schema_validation",
    "feature_contract",
    "split_leakage",
    "diversity_thresholds",
    "learning_smoke",
    "baseline_comparison",
    "privacy_scan",
    "self_test",
    "stop_go",
}


class D1Error(Exception):
    pass


@dataclass(frozen=True)
class Stump:
    feature: str | None
    value: str | None
    match_label: str
    other_label: str
    default_label: str

    def predict(self, features: dict[str, str]) -> str:
        if self.feature is None or self.value is None:
            return self.default_label
        return self.match_label if features.get(self.feature) == self.value else self.other_label


def bucket_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count == 1:
        return "count_1"
    if count <= 5:
        return "count_2_to_5"
    if count <= 20:
        return "count_6_to_20"
    if count <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def bucket_rate(numer: int, denom: int) -> str:
    if denom <= 0:
        return "rate_unavailable"
    rate = numer / denom
    if rate == 0:
        return "rate_0"
    if rate < 0.25:
        return "rate_low"
    if rate < 0.50:
        return "rate_low_mid"
    if rate < 0.75:
        return "rate_mid"
    if rate < 1.0:
        return "rate_high"
    return "rate_1"


def rate_rank(bucket: str) -> int:
    order = {
        "rate_unavailable": -1,
        "rate_0": 0,
        "rate_low": 1,
        "rate_low_mid": 2,
        "rate_mid": 3,
        "rate_high": 4,
        "rate_1": 5,
    }
    return order.get(bucket, -1)


def delta_bucket(model_correct: int, baseline_correct: int, total: int) -> str:
    if total <= 0:
        return "delta_unavailable"
    delta = (model_correct - baseline_correct) / total
    if delta <= 0:
        return "delta_non_positive"
    if delta < 0.10:
        return "delta_positive_tiny"
    if delta < 0.25:
        return "delta_positive_small"
    return "delta_positive_large"


def majority(labels: list[str]) -> str:
    if not labels:
        return "failure_safe"
    counts = Counter(labels)
    # Deterministic tie break: safer class first.
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def load_jsonl(path: Path, *, confirm_private_input: bool) -> list[dict[str, Any]]:
    if not confirm_private_input:
        raise D1Error("--confirm-private-input is required before reading private D0 trace JSONL")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise D1Error(f"private trace JSONL parse failed at line bucket {bucket_count(line_number)}") from exc
            if not isinstance(value, dict):
                raise D1Error("private trace JSONL rows must be objects")
            rows.append(value)
    if not rows:
        raise D1Error("private trace JSONL contained no rows")
    return rows


def latest_private_trace() -> Path:
    root = REPO / "runs"
    candidates = sorted(root.glob(PRIVATE_TRACE_GLOB), key=lambda p: (p.stat().st_mtime, str(p))) if root.exists() else []
    if not candidates:
        raise D1Error("no ignored RPM-D0 private trace JSONL found; pass --trace-jsonl or run RPM-D0 trace capture first")
    return candidates[-1]


def resolve_trace_path(path: Path | None) -> tuple[Path, str]:
    if path is not None:
        return path, "explicit_private_jsonl"
    return latest_private_trace(), "latest_ignored_d0_private_trace"


def feature_name(group: str, field: str) -> str:
    return f"{group}.{field}"


def extract_features(row: dict[str, Any]) -> dict[str, str]:
    features: dict[str, str] = {}
    for group, field in ALLOWED_FEATURES:
        value = row.get(group, {}).get(field)
        if not isinstance(value, str):
            raise D1Error(f"allowed feature missing or non-string: {feature_name(group, field)}")
        if group == "state_features" and field == "currentness_bucket" and value in {"stale_rejected", "drift_detected"}:
            raise D1Error("post-action currentness result leaked into pre-action feature")
        features[feature_name(group, field)] = value
    return features


def target_from_row(row: dict[str, Any]) -> str:
    outcome = row.get("outcome_label", {})
    observation = row.get("observation_result", {})
    if outcome.get("label_available_bool") is True:
        return "success" if outcome.get("outcome_bucket") == "success_bucket" else "failure_safe"
    if observation.get("failure_bucket") == "none" and observation.get("observation_status") == "observed":
        return "success"
    return "failure_safe"


def rows_to_examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for row in rows:
        trace_id = row["trace_identity"]["trace_id"]
        examples.append({"episode": trace_id, "features": extract_features(row), "target": target_from_row(row)})
    return examples


def train_stump(examples: list[dict[str, Any]], feature_subset: list[str] | None = None) -> Stump:
    labels = [ex["target"] for ex in examples]
    default = majority(labels)
    if not examples:
        return Stump(None, None, default, default, default)
    feature_keys = feature_subset or sorted(examples[0]["features"])
    best: tuple[int, str, str, Stump] | None = None
    for key in sorted(feature_keys):
        values = sorted({ex["features"].get(key, "") for ex in examples})
        for value in values:
            match_labels = [ex["target"] for ex in examples if ex["features"].get(key) == value]
            other_labels = [ex["target"] for ex in examples if ex["features"].get(key) != value]
            stump = Stump(key, value, majority(match_labels) if match_labels else default, majority(other_labels) if other_labels else default, default)
            correct = sum(1 for ex in examples if stump.predict(ex["features"]) == ex["target"])
            candidate = (correct, key, value, stump)
            if best is None or (candidate[0], candidate[1], candidate[2]) > (best[0], best[1], best[2]):
                best = candidate
    assert best is not None
    return best[3]


def evaluate_leave_one_episode_out(examples: list[dict[str, Any]]) -> dict[str, Any]:
    episodes = sorted({ex["episode"] for ex in examples})
    if len(episodes) < 2:
        return {
            "heldout_episode_count": len(episodes),
            "train_eval_overlap": False,
            "total_eval_rows": 0,
            "model_correct": 0,
            "majority_correct": 0,
            "fixed_action_correct": 0,
            "fixed_action_feasible": False,
            "model_family": "decision_stump_stdlib",
        }

    model_correct = 0
    majority_correct = 0
    fixed_action_correct = 0
    total = 0
    overlap = False
    fixed_feasible = False
    action_key = feature_name("action", "action_type")
    for heldout in episodes:
        train = [ex for ex in examples if ex["episode"] != heldout]
        eval_rows = [ex for ex in examples if ex["episode"] == heldout]
        train_episodes = {ex["episode"] for ex in train}
        eval_episodes = {ex["episode"] for ex in eval_rows}
        overlap = overlap or bool(train_episodes & eval_episodes)

        stump = train_stump(train)
        maj = majority([ex["target"] for ex in train])
        action_stump = train_stump(train, [action_key])
        fixed_feasible = fixed_feasible or len({ex["features"][action_key] for ex in train}) >= 1
        for ex in eval_rows:
            model_correct += int(stump.predict(ex["features"]) == ex["target"])
            majority_correct += int(maj == ex["target"])
            fixed_action_correct += int(action_stump.predict(ex["features"]) == ex["target"])
            total += 1
    return {
        "heldout_episode_count": len(episodes),
        "train_eval_overlap": overlap,
        "total_eval_rows": total,
        "model_correct": model_correct,
        "majority_correct": majority_correct,
        "fixed_action_correct": fixed_action_correct,
        "fixed_action_feasible": fixed_feasible,
        "model_family": "decision_stump_stdlib",
    }


def summarize_feature_coverage(rows: list[dict[str, Any]]) -> dict[str, str]:
    coverage: dict[str, str] = {}
    for group, field in ALLOWED_FEATURES:
        count = sum(1 for row in rows if isinstance(row.get(group, {}).get(field), str))
        coverage[feature_name(group, field)] = bucket_count(count)
    return coverage


def public_leak_errors(obj: Any) -> list[str]:
    sanitized = copy.deepcopy(obj)
    privacy = sanitized.get("privacy_scan") if isinstance(sanitized, dict) else None
    if isinstance(privacy, dict):
        for key in (
            "raw_paths_public",
            "task_ids_public",
            "snippets_public",
            "exact_private_features_or_rows_public",
            "private_trace_path_public",
        ):
            privacy.pop(key, None)
    errors = schema.public_leak_errors(sanitized)
    text = json.dumps(obj, sort_keys=True)
    forbidden_terms = [
        "private_ref_",
        "rpm_d0_private_",
        "rpm_d0_state_action_traces.jsonl",
        "private_evidence_",
        "content_sha",
    ]
    for term in forbidden_terms:
        if term in text:
            errors.append(f"public leak disallowed private term {term}")
    return errors


def aggregate_report(rows: list[dict[str, Any]], *, input_mode: str, self_test_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    schema_errors = schema.validate_trace_rows(rows)
    if schema_errors:
        raise D1Error("private rows failed Phase 1 schema validation: " + "; ".join(schema_errors[:5]))
    examples = rows_to_examples(rows)
    eval_summary = evaluate_leave_one_episode_out(examples)

    row_count = len(rows)
    episodes = {ex["episode"] for ex in examples}
    action_types = {row["action"]["action_type"] for row in rows}
    target_counts = Counter(ex["target"] for ex in examples)
    min_outcome_count = min(target_counts.values()) if len(target_counts) >= 2 else 0
    model_rate_bucket = bucket_rate(eval_summary["model_correct"], eval_summary["total_eval_rows"])
    majority_rate_bucket = bucket_rate(eval_summary["majority_correct"], eval_summary["total_eval_rows"])
    model_beats_majority = rate_rank(model_rate_bucket) > rate_rank(majority_rate_bucket)

    thresholds = {
        "real_rows_ge_30": row_count >= 30,
        "episodes_ge_10": len(episodes) >= 10,
        "action_types_ge_3": len(action_types) >= 3,
        "two_outcome_classes_each_ge_5": len(target_counts) >= 2 and min_outcome_count >= 5,
        "heldout_episodes_ge_3": eval_summary["heldout_episode_count"] >= 3,
        "no_train_eval_trace_overlap": not eval_summary["train_eval_overlap"],
        "model_beats_majority_by_bucketed_margin": model_beats_majority,
    }
    diversity_sufficient = all(thresholds.values())
    no_signal = not model_beats_majority
    status = STATUS_SIGNAL if diversity_sufficient and not no_signal else (STATUS_INSUFFICIENT if not diversity_sufficient else STATUS_NO_SIGNAL)
    authorized = AUTHORIZED_D2 if status == STATUS_SIGNAL else AUTHORIZED_D0B

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_checkpoints": {
            "phase1_schema_checkpoint": "0507508",
            "rpm_d0_trace_capture_checkpoint": "ffd5ea3",
            "d0_public_report_readback": "aggregate_only_available",
        },
        "execution_attestation": {
            "offline_private_trace_read_confirmed": True,
            "stdlib_only_local_learner": True,
            "network_access": "no_network",
            "ci_execution": "not_ci",
            "provider_or_model_call_executed": False,
            "runtime_or_default_change_executed": False,
            "rpm_training_claim_executed": False,
            "model_scaling_executed": False,
        },
        "private_input_summary": {
            "input_mode": input_mode,
            "storage_class": "ignored_repo_runs_private_jsonl_or_explicit_operator_private_jsonl",
            "private_input_path_public": False,
            "raw_rows_public": False,
            "row_count_bucket": bucket_count(row_count),
            "episode_count_bucket": bucket_count(len(episodes)),
        },
        "schema_validation": {
            "strict_phase1_trace_schema": "passed",
            "schema_error_bucket": bucket_count(len(schema_errors)),
            "all_rows_validated_before_learning": True,
        },
        "feature_contract": {
            "allowed_feature_fields": [feature_name(group, field) for group, field in ALLOWED_FEATURES],
            "feature_coverage_buckets": summarize_feature_coverage(rows),
            "forbidden_feature_sources": [
                "outcome_label_group",
                "observation_result_group",
                "task_identifiers",
                "raw_paths_or_queries_or_snippets",
                "hashes_or_private_references",
                "post_action_currentness_results",
            ],
            "label_blind_pre_action_features_only": True,
        },
        "split_leakage": {
            "split_policy": "deterministic_leave_one_episode_out",
            "heldout_episode_count_bucket": bucket_count(eval_summary["heldout_episode_count"]),
            "train_eval_trace_overlap": eval_summary["train_eval_overlap"],
            "leakage_status": "passed" if not eval_summary["train_eval_overlap"] else "failed",
        },
        "diversity_thresholds": {
            "real_row_count_bucket": bucket_count(row_count),
            "episode_count_bucket": bucket_count(len(episodes)),
            "action_type_count_bucket": bucket_count(len(action_types)),
            "binary_target_class_count_bucket": bucket_count(len(target_counts)),
            "minority_target_count_bucket": bucket_count(min_outcome_count),
            "threshold_results": thresholds,
            "diversity_status": "passed" if diversity_sufficient else "insufficient_real_trace_diversity",
        },
        "learning_smoke": {
            "learning_scope": "bounded_offline_pipeline_smoke_only",
            "model_family": eval_summary["model_family"],
            "target_source": "post_action_outcome_or_observation_success_vs_failure_safe",
            "evaluation_row_count_bucket": bucket_count(eval_summary["total_eval_rows"]),
            "training_claim_allowed": False,
            "method_scale_winner_default_claims_allowed": False,
        },
        "baseline_comparison": {
            "model_accuracy_bucket": model_rate_bucket,
            "majority_baseline_accuracy_bucket": majority_rate_bucket,
            "fixed_action_baseline_accuracy_bucket": bucket_rate(eval_summary["fixed_action_correct"], eval_summary["total_eval_rows"]),
            "fixed_action_baseline_feasible": eval_summary["fixed_action_feasible"],
            "model_vs_majority_delta_bucket": delta_bucket(eval_summary["model_correct"], eval_summary["majority_correct"], eval_summary["total_eval_rows"]),
            "candidate_signal_status": "unexpected_candidate_signal" if status == STATUS_SIGNAL else "no_training_signal_claim",
        },
        "privacy_scan": {
            "public_leak_scan": "pending",
            "aggregate_only_publication": True,
            "raw_paths_public": False,
            "queries_public": False,
            "task_ids_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "labels_public": False,
            "exact_private_features_or_rows_public": False,
            "private_trace_path_public": False,
        },
        "self_test": self_test_summary or {"status": "not_embedded", "checks_passed": 0, "checks_total": 0, "failed_checks": []},
        "stop_go": {
            "decision": "go_pipeline_smoke_only_no_training_claim",
            "authorized_next_phase": authorized,
            "if_insufficient_or_no_signal_authorized_only": AUTHORIZED_D0B,
            "if_unexpected_candidate_signal_authorized_only": AUTHORIZED_D2,
            "explicitly_not_authorized": sorted(FORBIDDEN_PUBLIC_OR_NEXT),
            "runtime_default_or_model_scaling_authorized": False,
            "raw_publication_authorized": False,
        },
    }
    report["privacy_scan"]["public_leak_scan"] = "passed" if not public_leak_errors(report) else "failed"
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != REPORT_TOP_LEVEL_KEYS:
        errors.append("report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema_version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") not in {STATUS_INSUFFICIENT, STATUS_SIGNAL, STATUS_NO_SIGNAL}:
        errors.append("bad status")
    attestation = report.get("execution_attestation", {})
    if attestation.get("offline_private_trace_read_confirmed") is not True:
        errors.append("private input confirmation readback missing")
    for field in ("provider_or_model_call_executed", "runtime_or_default_change_executed", "rpm_training_claim_executed", "model_scaling_executed"):
        if attestation.get(field) is not False:
            errors.append(f"execution_attestation.{field} must be false")
    if attestation.get("network_access") != "no_network":
        errors.append("network access must remain no_network")
    private_input = report.get("private_input_summary", {})
    if private_input.get("private_input_path_public") is not False or private_input.get("raw_rows_public") is not False:
        errors.append("private input path/raw rows must not be public")
    validation = report.get("schema_validation", {})
    if validation.get("strict_phase1_trace_schema") != "passed" or validation.get("schema_error_bucket") != "count_0":
        errors.append("strict schema validation must pass")
    contract = report.get("feature_contract", {})
    expected_features = [feature_name(group, field) for group, field in ALLOWED_FEATURES]
    if contract.get("allowed_feature_fields") != expected_features:
        errors.append("allowed feature field contract drift")
    if contract.get("label_blind_pre_action_features_only") is not True:
        errors.append("label-blind feature contract missing")
    coverage = contract.get("feature_coverage_buckets", {})
    if set(coverage) != set(expected_features):
        errors.append("feature coverage shape drift")
    forbidden_text = json.dumps(contract.get("forbidden_feature_sources", []), sort_keys=True)
    for required in ("outcome_label", "observation_result", "task_identifiers", "raw_paths", "hashes", "post_action_currentness"):
        if required not in forbidden_text:
            errors.append(f"forbidden feature source {required} missing")
    split = report.get("split_leakage", {})
    if split.get("split_policy") != "deterministic_leave_one_episode_out":
        errors.append("split policy drift")
    if split.get("train_eval_trace_overlap") is not False or split.get("leakage_status") != "passed":
        errors.append("train/eval trace overlap must be false")
    thresholds = report.get("diversity_thresholds", {})
    threshold_results = thresholds.get("threshold_results", {})
    for key in (
        "real_rows_ge_30",
        "episodes_ge_10",
        "action_types_ge_3",
        "two_outcome_classes_each_ge_5",
        "heldout_episodes_ge_3",
        "no_train_eval_trace_overlap",
        "model_beats_majority_by_bucketed_margin",
    ):
        if key not in threshold_results or not isinstance(threshold_results.get(key), bool):
            errors.append(f"diversity threshold {key} missing or non-boolean")
    if report.get("status") == STATUS_INSUFFICIENT and thresholds.get("diversity_status") != "insufficient_real_trace_diversity":
        errors.append("insufficient status requires insufficient diversity readback")
    learning = report.get("learning_smoke", {})
    if learning.get("model_family") != "decision_stump_stdlib":
        errors.append("model family drift")
    if learning.get("training_claim_allowed") is not False or learning.get("method_scale_winner_default_claims_allowed") is not False:
        errors.append("training/method/default claims must be false")
    baseline = report.get("baseline_comparison", {})
    for key in ("model_accuracy_bucket", "majority_baseline_accuracy_bucket", "fixed_action_baseline_accuracy_bucket", "model_vs_majority_delta_bucket"):
        if key not in baseline:
            errors.append(f"baseline comparison key {key} missing")
    privacy = report.get("privacy_scan", {})
    if privacy.get("public_leak_scan") != "passed":
        errors.append("privacy scan must pass")
    for field in ("raw_paths_public", "queries_public", "task_ids_public", "snippets_public", "hashes_public", "labels_public", "exact_private_features_or_rows_public", "private_trace_path_public"):
        if privacy.get(field) is not False:
            errors.append(f"privacy_scan.{field} must be false")
    self_test = report.get("self_test", {})
    if self_test.get("status") != "passed" or self_test.get("failed_checks") != []:
        errors.append("self-test must be embedded and passed")
    stop_go = report.get("stop_go", {})
    forbidden = set(stop_go.get("explicitly_not_authorized", []))
    if forbidden != FORBIDDEN_PUBLIC_OR_NEXT:
        errors.append("forbidden route set drift")
    allowed = stop_go.get("authorized_next_phase")
    if report.get("status") == STATUS_SIGNAL:
        if allowed != AUTHORIZED_D2:
            errors.append("candidate signal status may authorize only D2 design")
    elif allowed != AUTHORIZED_D0B:
        errors.append("insufficient/no-signal status may authorize only D0B/product trace capture")
    if allowed in forbidden:
        errors.append("forbidden phase appears as authorized next phase")
    if stop_go.get("runtime_default_or_model_scaling_authorized") is not False or stop_go.get("raw_publication_authorized") is not False:
        errors.append("runtime/default/model scaling/raw publication authorization must remain false")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    report = copy.deepcopy(report)
    report["privacy_scan"]["public_leak_scan"] = "passed" if not public_leak_errors(report) else "failed"
    errors = validate_public_report(report)
    if errors:
        raise D1Error("public report validation failed: " + "; ".join(errors[:6]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_offline_learning_smoke(trace_jsonl: Path | None, *, confirm_private_input: bool) -> dict[str, Any]:
    path, input_mode = resolve_trace_path(trace_jsonl)
    rows = load_jsonl(path, confirm_private_input=confirm_private_input)
    self_test_summary = run_self_tests()
    report = aggregate_report(rows, input_mode=input_mode, self_test_summary=self_test_summary)
    write_report(report)
    return report


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows = schema.valid_fixture_rows()
    checks.append(("phase1_schema_fixture_valid", not schema.validate_trace_rows(rows)))
    try:
        _ = aggregate_report(rows, input_mode="self_test_private_fixture", self_test_summary={"status": "passed", "checks_passed": 1, "checks_total": 1, "failed_checks": []})
        checks.append(("aggregate_fixture_report_builds", True))
    except D1Error:
        checks.append(("aggregate_fixture_report_builds", False))
    try:
        load_jsonl(REPO / "does_not_need_to_exist.jsonl", confirm_private_input=False)
        checks.append(("private_input_confirmation_required", False))
    except D1Error as exc:
        checks.append(("private_input_confirmation_required", "confirm-private-input" in str(exc)))
    features = extract_features(rows[0])
    checks.append(("features_use_allowed_fields_only", set(features) == {feature_name(g, f) for g, f in ALLOWED_FEATURES}))
    checks.append(("feature_excludes_outcome_observation_identity", not any(term in json.dumps(features) for term in ("outcome", "observation", "private_ref_"))))
    bad_feature_row = copy.deepcopy(rows[0])
    bad_feature_row["state_features"]["currentness_bucket"] = "stale_rejected"
    try:
        extract_features(bad_feature_row)
        checks.append(("post_action_currentness_feature_leak_rejected", False))
    except D1Error as exc:
        checks.append(("post_action_currentness_feature_leak_rejected", "currentness" in str(exc)))
    examples = rows_to_examples(rows)
    split = evaluate_leave_one_episode_out(examples)
    checks.append(("leave_one_episode_out_no_overlap", split["train_eval_overlap"] is False))
    report = aggregate_report(rows, input_mode="self_test_private_fixture", self_test_summary={"status": "passed", "checks_passed": 99, "checks_total": 99, "failed_checks": []})
    checks.append(("public_report_valid_fixture", not validate_public_report(report)))
    bad = copy.deepcopy(report)
    bad["stop_go"]["authorized_next_phase"] = "rpm_training"
    checks.append(("training_overauthorization_rejected", any("forbidden" in e or "D0B" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_scan"]["private_trace_path_public"] = True
    checks.append(("private_trace_path_public_rejected", any("private_trace_path_public" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["feature_contract"]["allowed_feature_fields"].append("outcome_label.outcome_bucket")
    checks.append(("feature_contract_drift_rejected", any("feature field" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["split_leakage"]["train_eval_trace_overlap"] = True
    checks.append(("split_overlap_rejected", any("overlap" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["privacy_scan"]["debug_private_ref"] = "private_ref_trace_a"
    checks.append(("public_private_ref_leak_rejected", bool(validate_public_report(bad))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["action"]["action_type"] = "rpm_training"
    try:
        aggregate_report(bad_rows, input_mode="self_test_private_fixture", self_test_summary={"status": "passed", "checks_passed": 99, "checks_total": 99, "failed_checks": []})
        checks.append(("schema_invalid_row_rejected", False))
    except D1Error:
        checks.append(("schema_invalid_row_rejected", True))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise D1Error("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run/validate RPM-D1 bounded offline RPM-small learning smoke")
    parser.add_argument("--self-test", action="store_true", help="run RPM-D1 mutation/readback self-tests")
    parser.add_argument("--run-offline-learning-smoke", action="store_true", help="read private D0 JSONL and run bounded offline learning smoke")
    parser.add_argument("--trace-jsonl", type=Path, help="private RPM-D0 trace JSONL; defaults to latest ignored runs/rpm_d0_private_*/ trace")
    parser.add_argument("--confirm-private-input", action="store_true", help="required explicit confirmation before reading private trace input")
    parser.add_argument("--validate-report", type=Path, help="validate aggregate-only RPM-D1 public report")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_tests(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_public_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"Validation passed: {args.validate_report}")
            return 0
        if args.run_offline_learning_smoke:
            report = run_offline_learning_smoke(args.trace_jsonl, confirm_private_input=args.confirm_private_input)
            print(
                json.dumps(
                    {
                        "status": report["status"],
                        "private_input_mode": report["private_input_summary"]["input_mode"],
                        "public_report": str(DEFAULT_REPORT),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        parser.error("choose --self-test, --run-offline-learning-smoke, or --validate-report")
    except (D1Error, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
