from __future__ import annotations

from typing import Any, Mapping


_FORBIDDEN_PUBLIC_KEYS = (
    "path",
    "file_path",
    "source_path",
    "exact_path",
    "exact_span",
    "repo",
    "repo_id",
    "repo_name",
    "repo_url",
    "task_id",
    "span",
    "line",
    "snippet",
    "content",
    "content_sha",
    "candidate",
    "candidate_list",
    "rank_list",
    "provider",
    "prompt",
    "response",
    "payload",
    "hash",
    "private_id",
    "queue_item_id",
    "anonymous_design_id",
)


def _schema(surface: str) -> str:
    return "bea_v1_" + surface + "_trace_capture.v1"


def _required_private_fields(surface: str) -> tuple[str, ...]:
    if surface == "support_link":
        return (
            "anonymous_trace_id",
            "support_relation_bucket",
            "target_hit_bucket",
            "support_hit_bucket",
            "conjunction_bucket",
            "support_evidence_role_bucket",
            "leakage_risk_bucket",
            "source_context_available_bucket",
            "capture_phase_bucket",
            "trace_logger_version_bucket",
            "validation_status_bucket",
        )
    if surface == "scheduler_action_cost":
        return (
            "anonymous_trace_id",
            "arm_bucket",
            "action_sequence_bucket",
            "latency_bucket",
            "pool_size_bucket",
            "pool_delta_bucket",
            "hard_cap_bucket",
            "file_reach_bucket",
            "cost_state_bucket",
            "scheduler_state_bucket",
            "capture_phase_bucket",
            "trace_logger_version_bucket",
            "validation_status_bucket",
            "replay_freeze_bucket",
        )
    if surface == "ordered_prefix_stop":
        return (
            "anonymous_trace_id",
            "arm_bucket",
            "prefix_position_bucket",
            "prefix_cost_bucket",
            "budget_remaining_bucket",
            "marginal_gain_bucket",
            "stop_policy_bucket",
            "continue_reference_bucket",
            "early_stop_signal_bucket",
            "capture_phase_bucket",
            "trace_logger_version_bucket",
            "validation_status_bucket",
            "replay_freeze_bucket",
        )
    if surface == "same_file_redundancy":
        return (
            "anonymous_trace_id",
            "action_layer_bucket",
            "action_arm_bucket",
            "duplicate_pressure_bucket",
            "same_file_candidate_count_bucket",
            "topk_file_diversity_bucket",
            "gold_file_displacement_bucket",
            "marginal_utility_bucket",
            "capture_phase_bucket",
            "trace_logger_version_bucket",
            "validation_status_bucket",
            "replay_freeze_bucket",
        )
    if surface == "risk_penalty":
        return (
            "anonymous_trace_id",
            "action_layer_bucket",
            "action_arm_bucket",
            "risk_class_bucket",
            "risk_policy_bucket",
            "removed_gold_bucket",
            "replacement_bucket",
            "topk_effect_bucket",
            "counterfactual_keep_bucket",
            "capture_phase_bucket",
            "trace_logger_version_bucket",
            "validation_status_bucket",
        )
    return ()


def _public_field_pairs(surface: str) -> tuple[tuple[str, str], ...]:
    if surface == "support_link":
        return (
            ("relation_bucket", "support_relation_bucket"),
            ("target_hit_bucket", "target_hit_bucket"),
            ("support_hit_bucket", "support_hit_bucket"),
            ("conjunction_bucket", "conjunction_bucket"),
            ("role_bucket", "support_evidence_role_bucket"),
            ("risk_bucket", "leakage_risk_bucket"),
        )
    if surface == "scheduler_action_cost":
        return (
            ("arm_bucket", "arm_bucket"),
            ("latency_bucket", "latency_bucket"),
            ("pool_delta_bucket", "pool_delta_bucket"),
            ("hard_cap_bucket", "hard_cap_bucket"),
            ("file_reach_bucket", "file_reach_bucket"),
            ("cost_state_bucket", "cost_state_bucket"),
            ("replay_freeze_bucket", "replay_freeze_bucket"),
        )
    if surface == "ordered_prefix_stop":
        return (
            ("arm_bucket", "arm_bucket"),
            ("prefix_position_bucket", "prefix_position_bucket"),
            ("prefix_cost_bucket", "prefix_cost_bucket"),
            ("budget_remaining_bucket", "budget_remaining_bucket"),
            ("marginal_gain_bucket", "marginal_gain_bucket"),
            ("stop_policy_bucket", "stop_policy_bucket"),
            ("continue_bucket", "continue_reference_bucket"),
        )
    if surface == "same_file_redundancy":
        return (
            ("action_layer_bucket", "action_layer_bucket"),
            ("action_arm_bucket", "action_arm_bucket"),
            ("duplicate_pressure_bucket", "duplicate_pressure_bucket"),
            ("same_file_count_bucket", "same_file_candidate_count_bucket"),
            ("diversity_bucket", "topk_file_diversity_bucket"),
            ("gold_effect_bucket", "gold_file_displacement_bucket"),
        )
    if surface == "risk_penalty":
        return (
            ("action_layer_bucket", "action_layer_bucket"),
            ("action_arm_bucket", "action_arm_bucket"),
            ("risk_class_bucket", "risk_class_bucket"),
            ("risk_policy_bucket", "risk_policy_bucket"),
            ("removed_gold_bucket", "removed_gold_bucket"),
            ("replacement_bucket", "replacement_bucket"),
            ("counterfactual_keep_bucket", "counterfactual_keep_bucket"),
        )
    return ()


def _bucket_value(source: Mapping[str, Any], key: str) -> Any:
    value = source.get(key)
    if value is None or value == "":
        return "unknown_not_captured"
    return value


def _build_private(surface: str, event: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": _schema(surface),
        "surface_bucket": surface,
        "trace_completeness_bucket": _bucket_value(event, "trace_completeness_bucket"),
    }
    for key in _required_private_fields(surface):
        row[key] = _bucket_value(event, key)
    return row


def _sanitize_public(surface: str, private_row: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "anonymous_public_trace_id": _bucket_value(private_row, "anonymous_public_trace_id") if private_row.get("anonymous_public_trace_id") not in (None, "") else _bucket_value(private_row, "anonymous_trace_id"),
        "surface_bucket": surface,
        "schema_version_bucket": _bucket_value(private_row, "schema_version"),
        "trace_completeness_bucket": _bucket_value(private_row, "trace_completeness_bucket"),
    }
    for public_key, private_key in _public_field_pairs(surface):
        row[public_key] = _bucket_value(private_row, private_key)
    return row


def _contains_forbidden_public_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, inner in value.items():
            if str(key) in _FORBIDDEN_PUBLIC_KEYS:
                return True
            if _contains_forbidden_public_key(inner):
                return True
    if isinstance(value, (list, tuple)):
        for inner in value:
            if _contains_forbidden_public_key(inner):
                return True
    return False


def _validate_private(surface: str, private_row: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if private_row.get("schema_version") != _schema(surface):
        errors.append("schema_version_mismatch")
    if private_row.get("surface_bucket") != surface:
        errors.append("surface_bucket_mismatch")
    if not private_row.get("trace_completeness_bucket"):
        errors.append("trace_completeness_missing")
    for key in _required_private_fields(surface):
        if key not in private_row or private_row.get(key) in (None, ""):
            errors.append("missing_" + key)
    return {"validation_status": "pass" if not errors else "fail", "errors": errors}


def _validate_public(surface: str, public_row: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if _contains_forbidden_public_key(public_row):
        errors.append("forbidden_public_key_present")
    required = (
        "anonymous_public_trace_id",
        "surface_bucket",
        "schema_version_bucket",
        "trace_completeness_bucket",
    ) + tuple(pair[0] for pair in _public_field_pairs(surface))
    for key in required:
        if key not in public_row or public_row.get(key) in (None, ""):
            errors.append("missing_" + key)
    if public_row.get("surface_bucket") != surface:
        errors.append("surface_bucket_mismatch")
    if public_row.get("schema_version_bucket") != _schema(surface):
        errors.append("schema_version_bucket_mismatch")
    return {"validation_status": "pass" if not errors else "fail", "errors": errors}


def build_support_link_trace_capture_row_private(event: Mapping[str, Any]) -> dict[str, Any]:
    return _build_private("support_link", event)


def sanitize_support_link_trace_capture_row_public(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_public("support_link", private_row)


def validate_support_link_trace_capture_row_private(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_private("support_link", private_row)


def validate_support_link_trace_capture_row_public_projection(public_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_public("support_link", public_row)


def build_scheduler_action_cost_trace_capture_row_private(event: Mapping[str, Any]) -> dict[str, Any]:
    return _build_private("scheduler_action_cost", event)


def sanitize_scheduler_action_cost_trace_capture_row_public(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_public("scheduler_action_cost", private_row)


def validate_scheduler_action_cost_trace_capture_row_private(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_private("scheduler_action_cost", private_row)


def validate_scheduler_action_cost_trace_capture_row_public_projection(public_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_public("scheduler_action_cost", public_row)


def build_ordered_prefix_stop_trace_capture_row_private(event: Mapping[str, Any]) -> dict[str, Any]:
    return _build_private("ordered_prefix_stop", event)


def sanitize_ordered_prefix_stop_trace_capture_row_public(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_public("ordered_prefix_stop", private_row)


def validate_ordered_prefix_stop_trace_capture_row_private(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_private("ordered_prefix_stop", private_row)


def validate_ordered_prefix_stop_trace_capture_row_public_projection(public_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_public("ordered_prefix_stop", public_row)


def build_same_file_redundancy_trace_capture_row_private(event: Mapping[str, Any]) -> dict[str, Any]:
    return _build_private("same_file_redundancy", event)


def sanitize_same_file_redundancy_trace_capture_row_public(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_public("same_file_redundancy", private_row)


def validate_same_file_redundancy_trace_capture_row_private(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_private("same_file_redundancy", private_row)


def validate_same_file_redundancy_trace_capture_row_public_projection(public_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_public("same_file_redundancy", public_row)


def build_risk_penalty_trace_capture_row_private(event: Mapping[str, Any]) -> dict[str, Any]:
    return _build_private("risk_penalty", event)


def sanitize_risk_penalty_trace_capture_row_public(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize_public("risk_penalty", private_row)


def validate_risk_penalty_trace_capture_row_private(private_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_private("risk_penalty", private_row)


def validate_risk_penalty_trace_capture_row_public_projection(public_row: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_public("risk_penalty", public_row)
