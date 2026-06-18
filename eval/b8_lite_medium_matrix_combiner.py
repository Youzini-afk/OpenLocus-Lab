#!/usr/bin/env python3
"""B8-lite medium matrix combiner.

B8-lite is a **derived aggregate rollup**. It combines exactly two
B6C / B6F ``b6c-frozen-policy-validation-v0`` aggregate JSON reports into a
single derived aggregate. It performs:

* **no** per-task / per-repo / per-candidate / source-record reads;
* **no** provider calls (``new_provider_calls == 0``);
* **no** policy search, rule generation, retuning, or winner selection;
* **no** promotion / default / model-robust claim.

The only inputs are two committed aggregate JSON reports (plus optional source
run IDs). The output is a single aggregate rollup that preserves the
``aggregate_only_public_artifact`` contract: no repo IDs, repo names, repo paths,
task IDs, candidate IDs, digests, hashes, or per-repo rows are emitted. Source
run IDs (workflow run IDs only) may be echoed when supplied, because workflow
run IDs are not repo/path identifiers.

The combiner refuses ``status=ok`` unless the caller explicitly asserts
``--private-disjointness-verified``. Without that assertion the output is
``blocked_disjointness`` (the combiner cannot itself prove the two source runs
did not share tasks/repos). Input-contract or cross-report-spec mismatches
produce ``blocked_input_contract``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite

SCHEMA_VERSION = "b8-lite-medium-matrix-combiner-v0"
GENERATED_BY = "b8_lite_medium_matrix_combiner"
CLAIM_LEVEL = "derived_aggregate_of_frozen_policy_validations"
INPUT_SCHEMA_VERSION = "b6c-frozen-policy-validation-v0"
INPUT_CLAIM_LEVEL = "frozen_policy_fresh_validation"

DEFAULT_OUT = Path(
    "artifacts/b8_lite_medium_matrix_combiner/b8_lite_medium_matrix_combiner_report.json"
)
DEFAULT_DOC = Path("docs/en/b8-lite-medium-matrix-combiner.md")

EXPECTED_FROZEN_NAMES = {
    "ambiguous_query_weak_only_default_use_p25_action",
    "negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action",
}

# Counts that are summed directly across the two input reports (per policy family).
SUMMED_FAMILY_INT_FIELDS = (
    "task_count",
    "comparable_task_count",
    "positive_task_count",
    "no_gold_task_count",
    "excluded_task_count",
    "added_gold_span",
    "added_false_span",
    "effective_llm_action_count",
    "provider_call_estimate",
    "fallback_to_baseline_count",
    "missing_action_outcome_count",
    "gold_kill_vs_p25",
    "false_reduction_vs_p25",
)

# Mean-like fields recomputed as task_count-weighted averages across inputs.
TASK_WEIGHTED_MEAN_FIELDS = (
    "mean_span_f05",
    "mean_primary_false_positive_rate",
)

# no_gold_task_count-weighted mean fields.
NO_GOLD_WEIGHTED_MEAN_FIELDS = (
    "no_gold_false_primary_rate",
)

# Frozen-manifest-integrity safety booleans that must all be true on each input.
REQUIRED_INTEGRITY_TRUE = (
    "manifest_schema_version_ok",
    "record_required_fields_present",
    "model_mode_pack_uniform",
    "allowed_model_mode_pack",
    "task_sets_matched",
    "paired_records_loadable",
    "freshness_contract_valid",
    "frozen_spec_hash_matched",
    "forbidden_public_key_scan_clean",
)

# Comparability scalar fields that must match across both input reports.
COMPARABILITY_MATCH_FIELDS = (
    "model",
    "output_mode",
    "plain_pack_layout",
    "hard_pack_layout",
)

ACTION_KEYS = (
    "use_p25_action",
    "candidate_baseline",
    "plain_span_narrow",
    "hard_distractor_filter",
    "abstain_filter",
    "weak_only",
)

BLOCK_STATUSES = {"blocked_disjointness", "blocked_input_contract"}
RUN_ID_RE = re.compile(r"^[0-9]+$")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"input report not found: {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"input report is not valid JSON: {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"input report must be a JSON object: {path}")
    return obj


# ---------------------------------------------------------------------------
# Input contract validation
# ---------------------------------------------------------------------------


def _validate_input_report(report: dict[str, Any], label: str) -> None:
    """Validate a single B6C/B6F aggregate report against the combiner contract.

    Self-test synthetic inputs handled separately by the combiner; this function
    enforces the real-input contract.
    """
    if report.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError(
            f"{label}: schema_version must be {INPUT_SCHEMA_VERSION!r}, got "
            f"{report.get('schema_version')!r}"
        )
    if report.get("status") != "ok":
        raise ValueError(
            f"{label}: status must be 'ok' for combiner input, got "
            f"{report.get('status')!r}"
        )
    if report.get("claim_level") != INPUT_CLAIM_LEVEL:
        raise ValueError(
            f"{label}: claim_level must be {INPUT_CLAIM_LEVEL!r}, got "
            f"{report.get('claim_level')!r}"
        )
    if report.get("self_test") is not False:
        raise ValueError(f"{label}: self_test must be false for combiner input")
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(f"{label}: aggregate_only_public_artifact must be true")
    for key in (
        "repo_ids_in_artifact",
        "task_ids_in_artifact",
        "candidate_ids_in_artifact",
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
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
    ):
        if report.get(key) is not False:
            raise ValueError(f"{label}: {key} must be false")
    if report.get("remote_calls_by_policy_search") != 0:
        raise ValueError(f"{label}: remote_calls_by_policy_search must be 0")

    integrity = report.get("frozen_manifest_integrity")
    if not isinstance(integrity, dict):
        raise ValueError(f"{label}: frozen_manifest_integrity must be an object")
    for key in REQUIRED_INTEGRITY_TRUE:
        if integrity.get(key) is not True:
            raise ValueError(f"{label}: frozen_manifest_integrity.{key} must be true")

    families = report.get("policy_families")
    if not isinstance(families, dict) or not families:
        raise ValueError(f"{label}: policy_families must be a non-empty object")

    names = set(report.get("frozen_policy_names") or [])
    if names != EXPECTED_FROZEN_NAMES:
        raise ValueError(f"{label}: frozen_policy_names mismatch: {sorted(names)}")
    if report.get("frozen_policy_count") != len(EXPECTED_FROZEN_NAMES):
        raise ValueError(f"{label}: frozen_policy_count mismatch")

    # Every frozen family plus the P25 baseline must be present.
    expected_family_names = EXPECTED_FROZEN_NAMES | {"p25_bucket_routed_v0_plain"}
    missing = expected_family_names - set(families.keys())
    if missing:
        raise ValueError(f"{label}: missing policy_families: {sorted(missing)}")

    for name, metrics in families.items():
        if not isinstance(metrics, dict):
            raise ValueError(f"{label}: family {name} must be an object")
        for field in SUMMED_FAMILY_INT_FIELDS:
            if field not in metrics:
                raise ValueError(f"{label}: family {name} missing {field}")
        if "action_counts" not in metrics or not isinstance(
            metrics["action_counts"], dict
        ):
            raise ValueError(f"{label}: family {name} missing action_counts")
        if "policy_rules" not in metrics or not isinstance(
            metrics.get("policy_rules"), list
        ):
            raise ValueError(f"{label}: family {name} missing policy_rules")


def _validate_cross_report(reports: list[dict[str, Any]]) -> None:
    """Validate that the two reports share the same frozen policy spec,
    policy_rules, and comparability model/output/pack fields."""
    if len(reports) != 2:
        raise ValueError("combiner requires exactly two input reports")

    a, b = reports[0], reports[1]

    # Comparability scalars must match exactly.
    comp_a = a.get("comparability") or {}
    comp_b = b.get("comparability") or {}
    if not isinstance(comp_a, dict) or not isinstance(comp_b, dict):
        raise ValueError("comparability must be an object on both inputs")
    for field in COMPARABILITY_MATCH_FIELDS:
        if comp_a.get(field) != comp_b.get(field):
            raise ValueError(
                f"comparability.{field} mismatch: {comp_a.get(field)!r} vs "
                f"{comp_b.get(field)!r}"
            )

    families_a = a.get("policy_families") or {}
    families_b = b.get("policy_families") or {}
    # policy_rules must match per family.
    shared = set(families_a.keys()) & set(families_b.keys())
    expected = EXPECTED_FROZEN_NAMES | {"p25_bucket_routed_v0_plain"}
    if shared != expected:
        raise ValueError(
            f"family set mismatch: expected {sorted(expected)}, got {sorted(shared)}"
        )
    for name in expected:
        rules_a = families_a[name].get("policy_rules")
        rules_b = families_b[name].get("policy_rules")
        if rules_a != rules_b:
            raise ValueError(f"policy_rules mismatch for family {name}")
        # source must match too.
        if families_a[name].get("source") != families_b[name].get("source"):
            raise ValueError(f"source mismatch for family {name}")

    # frozen_policy_names / count must match.
    if a.get("frozen_policy_names") != b.get("frozen_policy_names"):
        raise ValueError("frozen_policy_names mismatch across inputs")
    if a.get("frozen_policy_count") != b.get("frozen_policy_count"):
        raise ValueError("frozen_policy_count mismatch across inputs")


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------


def _sum_action_counts(families: list[dict[str, Any]]) -> dict[str, int]:
    out = {k: 0 for k in ACTION_KEYS}
    for fam in families:
        counts = fam.get("action_counts") or {}
        for k in ACTION_KEYS:
            out[k] += _as_int(counts.get(k, 0))
    return out


def _combine_family(
    name: str, families: list[dict[str, Any]]
) -> dict[str, Any]:
    summed: dict[str, int] = {}
    for field in SUMMED_FAMILY_INT_FIELDS:
        summed[field] = sum(_as_int(fam.get(field, 0)) for fam in families)

    task_count = summed["task_count"]
    no_gold_task_count = summed["no_gold_task_count"]
    added_gold = summed["added_gold_span"]
    added_false = summed["added_false_span"]

    action_counts = _sum_action_counts(families)
    action_rates: dict[str, float] = {
        k: round(count / task_count, 6) for k, count in action_counts.items()
    } if task_count else {k: 0.0 for k in ACTION_KEYS}

    effective_llm = summed["effective_llm_action_count"]
    effective_llm_action_rate = _safe_div(effective_llm, task_count)

    false_per_gold = _safe_div(added_false, added_gold)
    net_span_value_2x = added_gold - 2 * added_false

    # Task-weighted means.
    weighted_means: dict[str, float | None] = {}
    for field in TASK_WEIGHTED_MEAN_FIELDS:
        num = 0.0
        den = 0
        for fam in families:
            tc = _as_int(fam.get("task_count", 0))
            val = _as_float(fam.get(field))
            if val is None:
                continue
            num += val * tc
            den += tc
        weighted_means[field] = _safe_div(num, den) if den else None

    # no_gold_task_count-weighted means.
    no_gold_weighted: dict[str, float | None] = {}
    for field in NO_GOLD_WEIGHTED_MEAN_FIELDS:
        num = 0.0
        den = 0
        for fam in families:
            ng = _as_int(fam.get("no_gold_task_count", 0))
            val = _as_float(fam.get(field))
            if val is None:
                continue
            num += val * ng
            den += ng
        no_gold_weighted[field] = _safe_div(num, den) if den else None

    out: dict[str, Any] = {
        "source": families[0].get("source", "unknown"),
        "policy_rules": families[0].get("policy_rules", []),
        "task_count": task_count,
        "comparable_task_count": summed["comparable_task_count"],
        "positive_task_count": summed["positive_task_count"],
        "no_gold_task_count": no_gold_task_count,
        "excluded_task_count": summed["excluded_task_count"],
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "action_counts": action_counts,
        "action_rates": action_rates,
        "effective_llm_action_count": effective_llm,
        "effective_llm_action_rate": effective_llm_action_rate,
        "provider_call_estimate": summed["provider_call_estimate"],
        "provider_call_estimate_not_measured": True,
        "fallback_to_baseline_count": summed["fallback_to_baseline_count"],
        "missing_action_outcome_count": summed["missing_action_outcome_count"],
        "gold_kill_vs_p25": summed["gold_kill_vs_p25"],
        "false_reduction_vs_p25": summed["false_reduction_vs_p25"],
        "false_per_gold": false_per_gold,
        "net_span_value_2x": net_span_value_2x,
        "mean_span_f05": weighted_means["mean_span_f05"],
        "mean_primary_false_positive_rate": weighted_means[
            "mean_primary_false_positive_rate"
        ],
        "no_gold_false_primary_rate": no_gold_weighted["no_gold_false_primary_rate"],
    }
    return out


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "status": status,
        "self_test": bool(self_test),
        "claim_level": CLAIM_LEVEL,
        "live_quality_experiment": False,
        "diagnostic_policy_search": True,
        "aggregate_only_public_artifact": True,
        "public_per_task_rows": False,
        "public_per_repo_rows": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "policy_search_not_admission": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "remote_calls_by_policy_search": 0,
        "new_provider_calls": 0,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "repo_ids_in_artifact": False,
        "repo_names_in_artifact": False,
        "repo_set_hash_in_artifact": False,
        "winner_declared": False,
        "default_recommendation_declared": False,
        "promotion_declared": False,
        "frozen_policy_validation": True,
        "derived_aggregate_rollup": True,
        "single_model_only": True,
    }
    return report


def _blocked_report(
    status: str,
    self_test: bool,
    source_run_ids: list[str] | None,
    reason: str,
    detail: str | None = None,
) -> dict[str, Any]:
    report = _base_report(status, self_test)
    report.update(
        {
            "included_source_report_count": 0,
            "comparable_task_count": 0,
            "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
            "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
            "sample_freshness_protocol": (
                "b8_lite_derived_aggregate_blocked; new_provider_calls=0; "
                "not a new validation run"
            ),
            "frozen_manifest_integrity": {
                "forbidden_public_key_scan_clean": True,
                "block_reason": reason,
            },
            "policy_families": {},
            "comparability": {},
            "routing_invariance": {
                "selected_actions_invariant": False,
                "changed_policy_count": 0,
                "changed_policy_examples": [],
            },
            "private_disjointness_verified": False,
            "disjointness_block_reason": reason,
        }
    )
    if detail:
        report["frozen_manifest_integrity"]["block_detail"] = detail
    if source_run_ids:
        report["source_run_ids"] = list(source_run_ids)
    _finalize_safety(report)
    return report


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run forbidden-key scan on the public output and record the result."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("frozen_manifest_integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b8-lite public output would contain forbidden keys/values; "
            f"first violations: {violations[:5]}"
        )


def _validate_source_run_ids(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    if len(values) != 2:
        raise ValueError("source_run_ids must contain exactly two workflow run IDs")
    sanitized: list[str] = []
    for value in values:
        text = str(value)
        if not RUN_ID_RE.fullmatch(text):
            raise ValueError("source_run_ids must be decimal GitHub workflow run IDs")
        sanitized.append(text)
    return sanitized


def combine(
    reports: list[dict[str, Any]],
    source_run_ids: list[str] | None,
    private_disjointness_verified: bool,
    self_test: bool,
) -> dict[str, Any]:
    """Combine validated input reports into a derived aggregate rollup.

    Inputs must already pass ``_validate_input_report`` and
    ``_validate_cross_report``. The caller is responsible for gating
    ``status=ok`` on ``private_disjointness_verified``.
    """
    if not private_disjointness_verified and not self_test:
        return _blocked_report(
            "blocked_disjointness",
            self_test,
            source_run_ids,
            reason="private_disjointness_not_verified",
            detail=(
                "combiner cannot prove the two source runs did not share "
                "tasks and repos; pass --private-disjointness-verified after "
                "confirming disjoint task and repo universes out-of-band"
            ),
        )

    families_a = reports[0].get("policy_families") or {}
    families_b = reports[1].get("policy_families") or {}
    family_names = sorted(
        EXPECTED_FROZEN_NAMES | {"p25_bucket_routed_v0_plain"}
    )

    combined_families: dict[str, dict[str, Any]] = {}
    for name in family_names:
        combined_families[name] = _combine_family(
            name, [families_a[name], families_b[name]]
        )

    total_task_count = combined_families["p25_bucket_routed_v0_plain"]["task_count"]
    total_comparable = combined_families["p25_bucket_routed_v0_plain"][
        "comparable_task_count"
    ]

    # Routing invariance: AND across both source reports (only meaningful if
    # both sources report invariance).
    inv_a = reports[0].get("routing_invariance") or {}
    inv_b = reports[1].get("routing_invariance") or {}
    invariant_a = inv_a.get("selected_actions_invariant") is True
    invariant_b = inv_b.get("selected_actions_invariant") is True
    changed_count = _as_int(inv_a.get("changed_policy_count")) + _as_int(
        inv_b.get("changed_policy_count")
    )

    comp = reports[0].get("comparability") or {}

    status = "self_test_only" if self_test else "ok"
    report = _base_report(status, self_test)
    report.update(
        {
            "included_source_report_count": len(reports),
            "comparable_task_count": total_comparable,
            "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
            "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
            "sample_freshness_protocol": (
                "b8_lite_derived_aggregate_of_frozen_policy_validations; "
                "new_provider_calls=0; not a new validation run; not "
                "promotion or default; single model"
            ),
            "frozen_manifest_integrity": {
                "manifest_schema_version_ok": True,
                "record_required_fields_present": True,
                "model_mode_pack_uniform": True,
                "allowed_model_mode_pack": True,
                "task_sets_matched": True,
                "paired_records_loadable": True,
                "freshness_contract_valid": True,
                "frozen_spec_hash_matched": True,
                "input_contract_valid": True,
                "cross_report_spec_consistent": True,
                "private_disjointness_verified": True,
            },
            "policy_families": combined_families,
            "comparability": {
                "model": comp.get("model"),
                "output_mode": comp.get("output_mode"),
                "plain_pack_layout": comp.get("plain_pack_layout"),
                "hard_pack_layout": comp.get("hard_pack_layout"),
                "same_model_required": True,
                "same_output_mode_required": True,
                "same_pack_layout_required": True,
                "same_model_observed": True,
                "same_task_set_within_repo_required": True,
                "same_task_set_within_repo_observed": True,
                "fresh_aggregate_evaluation": False,
                "derived_aggregate_rollup": True,
                "search_performed": False,
                "single_model_only": True,
            },
            "routing_invariance": {
                "selected_actions_invariant": bool(invariant_a and invariant_b),
                "changed_policy_count": changed_count,
                "changed_policy_examples": [],
            },
            "private_disjointness_verified": True,
            "total_task_count": total_task_count,
        }
    )
    if source_run_ids:
        report["source_run_ids"] = list(source_run_ids)
    _finalize_safety(report)
    return report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    self_test = bool(args.self_test)

    if self_test:
        reports = _build_self_test_inputs()
        source_run_ids = ["10000000001", "10000000002"]
    else:
        if not args.reports or len(args.reports) != 2:
            raise SystemExit(
                "b8-lite combiner requires exactly two --reports (B6C/B6F aggregate JSON)"
            )
        reports = []
        for idx, path in enumerate(args.reports):
            report = _load_report(Path(path))
            _validate_input_report(report, f"report[{idx}]({path})")
            reports.append(report)
        try:
            _validate_cross_report(reports)
        except ValueError as exc:
            return _blocked_report(
                "blocked_input_contract",
                self_test,
                None,
                reason="cross_report_spec_mismatch",
                detail=str(exc),
            )
        try:
            source_run_ids = _validate_source_run_ids(
                list(args.source_run_ids) if args.source_run_ids else None
            )
        except ValueError as exc:
            return _blocked_report(
                "blocked_input_contract",
                self_test,
                None,
                reason="bad_source_run_ids",
                detail=str(exc),
            )

    return combine(
        reports,
        source_run_ids=source_run_ids,
        private_disjointness_verified=bool(args.private_disjointness_verified),
        self_test=self_test,
    )


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
    lines.append("# B8-lite Medium Matrix Combiner")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append(f"Claim level: `{report['claim_level']}`")
    lines.append("")
    lines.append(
        "B8-lite is a **derived aggregate rollup** of two "
        "`b6c-frozen-policy-validation-v0` aggregate reports (B6C / B6F). "
        "It performs no per-task, per-repo, per-candidate, or source-record "
        "reads, makes no provider calls (`new_provider_calls=0`), performs no "
        "policy search, and declares no winner / default / promotion. It is "
        "**not** a new validation run and **not** a model-robust claim; it is "
        "single-model only."
    )
    lines.append("")
    if report.get("self_test") is True:
        lines.append(
            "This artifact is a committed self-test / synthetic protocol check; "
            "it merges two synthetic B6C-format reports and must not be read as "
            "a live derived aggregate."
        )
        lines.append("")

    if report.get("status") in BLOCK_STATUSES:
        integrity = report.get("frozen_manifest_integrity") or {}
        lines.append(
            f"Combination was blocked (`{report['status']}`). "
            f"Reason: `{integrity.get('block_reason', 'unknown')}`."
        )
        if integrity.get("block_detail"):
            lines.append("")
            lines.append(f"Detail: {integrity['block_detail']}")
        lines.append("")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("## Source contract")
    lines.append("")
    lines.append(
        "- Inputs: exactly two `b6c-frozen-policy-validation-v0` aggregate reports."
    )
    lines.append(
        "- Each input must have `status=ok`, "
        "`claim_level=frozen_policy_fresh_validation`, `self_test=false`, "
        "`aggregate_only_public_artifact=true`, all raw/repo/task/candidate "
        "flags false, `policy_search_performed=false`, and "
        "`promotion_ready/default_should_change/evidencecore_semantics_changed=false`."
    )
    lines.append(
        "- Cross-report: `frozen_policy_names`, `policy_rules`, and "
        "`comparability.{model,output_mode,plain_pack_layout,hard_pack_layout}` "
        "must match exactly."
    )
    lines.append(
        "- `status=ok` requires `--private-disjointness-verified`; otherwise the "
        "combiner emits `blocked_disjointness` because it cannot itself prove "
        "the two source runs did not share tasks/repos."
    )
    lines.append("")

    lines.append("## Aggregate policy families")
    lines.append("")
    header = (
        "| Policy family | source | +gold | +false | F/G | SpanF0.5 | PFP | "
        "LLM calls | net 2x | gold kill vs P25 | false reduction vs P25 |"
    )
    lines.append(header)
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(report.get("policy_families", {})):
        m = report["policy_families"][name]
        lines.append(
            f"| `{name}` | {m.get('source', '')} | {m.get('added_gold_span', '')} | "
            f"{m.get('added_false_span', '')} | {_fmt(m.get('false_per_gold'))} | "
            f"{_fmt(m.get('mean_span_f05'))} | "
            f"{_fmt(m.get('mean_primary_false_positive_rate'))} | "
            f"{m.get('effective_llm_action_count', '')} | "
            f"{m.get('net_span_value_2x', '')} | "
            f"{m.get('gold_kill_vs_p25', '')} | "
            f"{m.get('false_reduction_vs_p25', '')} |"
        )
    lines.append("")

    lines.append("## Combination rules")
    lines.append("")
    lines.append(
        "- Counts summed directly: task / comparable / positive / no_gold / "
        "excluded / added_gold / added_false / action_counts / "
        "effective_llm_action_count / provider_call_estimate / "
        "fallback_to_baseline_count / missing_action_outcome_count / "
        "gold_kill_vs_p25 / false_reduction_vs_p25."
    )
    lines.append(
        "- `false_per_gold` recomputed as added_false / added_gold."
    )
    lines.append(
        "- `net_span_value_2x` recomputed as added_gold - 2 * added_false."
    )
    lines.append(
        "- `mean_span_f05` and `mean_primary_false_positive_rate` recomputed as "
        "task_count-weighted means."
    )
    lines.append(
        "- `no_gold_false_primary_rate` recomputed as a "
        "no_gold_task_count-weighted mean."
    )
    lines.append(
        "- `action_rates` and `effective_llm_action_rate` recomputed against the "
        "summed task_count."
    )
    lines.append("")

    lines.append("## Safety invariants")
    lines.append("")
    lines.append("```text")
    lines.append(f"claim_level={report['claim_level']}")
    lines.append("policy_search_performed=false")
    lines.append("new_provider_calls=0")
    lines.append("derived_aggregate_rollup=true")
    lines.append("single_model_only=true")
    lines.append("promotion_ready=false")
    lines.append("default_should_change=false")
    lines.append("evidencecore_semantics_changed=false")
    lines.append("remote_calls_by_policy_search=0")
    lines.append("aggregate_only_public_artifact=true")
    lines.append("public_per_repo_rows=false")
    lines.append("public_per_task_rows=false")
    lines.append("repo_ids_in_artifact=false")
    lines.append("repo_names_in_artifact=false")
    lines.append("repo_set_hash_in_artifact=false")
    lines.append("winner_declared=false")
    lines.append("default_recommendation_declared=false")
    lines.append("promotion_declared=false")
    lines.append("```")
    lines.append("")
    lines.append(
        "The public artifact does not emit input paths, repo names, repo IDs, "
        "task IDs, candidate IDs, digests, hashes, per-repo rows, or a repo-set "
        "hash. Source workflow run IDs may be echoed when supplied (run IDs are "
        "not repo/path identifiers)."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _common_family(
    source: str,
    rules: list[dict[str, Any]],
    task_count: int,
    positive_task_count: int,
    no_gold_task_count: int,
    added_gold: int,
    added_false: int,
    action_counts: dict[str, int],
    effective_llm: int,
    mean_span_f05: float,
    mean_pfp: float,
    no_gold_false_primary_rate: float,
) -> dict[str, Any]:
    total_actions = sum(action_counts.values())
    return {
        "source": source,
        "policy_rules": rules,
        "task_count": task_count,
        "comparable_task_count": task_count,
        "positive_task_count": positive_task_count,
        "no_gold_task_count": no_gold_task_count,
        "excluded_task_count": 0,
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "action_counts": dict(action_counts),
        "action_rates": {
            k: round(v / task_count, 6) for k, v in action_counts.items()
        } if task_count else {},
        "effective_llm_action_count": effective_llm,
        "effective_llm_action_rate": round(effective_llm / task_count, 6)
        if task_count
        else 0.0,
        "provider_call_estimate": effective_llm,
        "provider_call_estimate_not_measured": True,
        "fallback_to_baseline_count": task_count - total_actions
        if source != "baseline"
        else 0,
        "missing_action_outcome_count": task_count - total_actions
        if source != "baseline"
        else 0,
        "gold_kill_vs_p25": 0,
        "false_reduction_vs_p25": 0,
        "false_per_gold": round(added_false / added_gold, 6) if added_gold else None,
        "net_span_value_2x": added_gold - 2 * added_false,
        "mean_span_f05": mean_span_f05,
        "mean_primary_false_positive_rate": mean_pfp,
        "no_gold_false_primary_rate": no_gold_false_primary_rate,
    }


_P25_RULES = [
    {
        "name": "p25_reference_default",
        "predicates": ["always_true"],
        "action": "use_p25_action",
        "is_default": True,
    }
]
_FROZEN1_RULES = [
    {
        "name": "ambiguous_query_weak_only",
        "predicates": ["ambiguous_or_query_noise"],
        "action": "weak_only",
        "is_default": False,
    },
    {
        "name": "default_use_p25",
        "predicates": ["always_true"],
        "action": "use_p25_action",
        "is_default": True,
    },
]
_FROZEN2_RULES = [
    {
        "name": "negative_weak_only",
        "predicates": ["hard_distractor_like"],
        "action": "weak_only",
        "is_default": False,
    },
    {
        "name": "ambiguous_query_use_p25_action",
        "predicates": ["ambiguous_or_query_noise"],
        "action": "use_p25_action",
        "is_default": False,
    },
    {
        "name": "default_use_p25",
        "predicates": ["always_true"],
        "action": "use_p25_action",
        "is_default": True,
    },
]


def _synthetic_b6c_report(
    task_count: int,
    positive_task_count: int,
    no_gold_task_count: int,
    p25_added_gold: int,
    p25_added_false: int,
    p25_actions: dict[str, int],
    p25_llm: int,
    f1_added_gold: int,
    f1_added_false: int,
    f1_actions: dict[str, int],
    f1_llm: int,
    f2_added_gold: int,
    f2_added_false: int,
    f2_actions: dict[str, int],
    f2_llm: int,
    mean_span_f05: float,
    mean_pfp_p25: float,
    mean_pfp_f1: float,
    mean_pfp_f2: float,
    ng_p25: float,
    ng_f1: float,
    ng_f2: float,
    run_id: str,
) -> dict[str, Any]:
    families = {
        "p25_bucket_routed_v0_plain": _common_family(
            "baseline",
            _P25_RULES,
            task_count,
            positive_task_count,
            no_gold_task_count,
            p25_added_gold,
            p25_added_false,
            p25_actions,
            p25_llm,
            mean_span_f05,
            mean_pfp_p25,
            ng_p25,
        ),
        "ambiguous_query_weak_only_default_use_p25_action": _common_family(
            "frozen",
            _FROZEN1_RULES,
            task_count,
            positive_task_count,
            no_gold_task_count,
            f1_added_gold,
            f1_added_false,
            f1_actions,
            f1_llm,
            mean_span_f05,
            mean_pfp_f1,
            ng_f1,
        ),
        "negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action": _common_family(
            "frozen",
            _FROZEN2_RULES,
            task_count,
            positive_task_count,
            no_gold_task_count,
            f2_added_gold,
            f2_added_false,
            f2_actions,
            f2_llm,
            mean_span_f05,
            mean_pfp_f2,
            ng_f2,
        ),
    }
    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "generated_by": "b6c_frozen_policy_validation",
        "generated_at": _now(),
        "status": "ok",
        "self_test": False,
        "claim_level": INPUT_CLAIM_LEVEL,
        "live_quality_experiment": True,
        "diagnostic_policy_search": True,
        "aggregate_only_public_artifact": True,
        "public_per_task_rows": False,
        "public_per_repo_rows": False,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "policy_search_not_admission": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "remote_calls_by_policy_search": 0,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "repo_ids_in_artifact": False,
        "frozen_policy_validation": True,
        "included_repo_count": 4,
        "manifest_record_count": 4,
        "comparable_task_count": task_count,
        "frozen_policy_count": 2,
        "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
        "sample_freshness_protocol": "b6c_fresh_validation_contract_checked",
        "comparability": {
            "model": "[mk]Kimi-K2.7-Code",
            "output_mode": "tool_call",
            "plain_pack_layout": "topk_plain_v0",
            "hard_pack_layout": "hard_distractor_contrast_v0",
            "same_model_required": True,
            "same_output_mode_required": True,
            "same_pack_layout_required": True,
            "same_model_observed": True,
            "same_task_set_within_repo_required": True,
            "same_task_set_within_repo_observed": True,
            "fresh_aggregate_evaluation": True,
            "search_performed": False,
        },
        "frozen_manifest_integrity": {
            "manifest_schema_version_ok": True,
            "record_required_fields_present": True,
            "model_mode_pack_uniform": True,
            "allowed_model_mode_pack": True,
            "task_sets_matched": True,
            "paired_records_loadable": True,
            "freshness_contract_present": True,
            "freshness_contract_valid": True,
            "frozen_spec_hash_matched": True,
            "forbidden_public_key_scan_clean": True,
        },
        "policy_families": families,
        "routing_invariance": {
            "selected_actions_invariant": True,
            "changed_policy_count": 0,
            "changed_policy_examples": [],
            "score_fields_removed_or_flipped": True,
        },
        "source_run_id": run_id,
    }


def _build_self_test_inputs() -> list[dict[str, Any]]:
    report_a = _synthetic_b6c_report(
        task_count=10,
        positive_task_count=6,
        no_gold_task_count=4,
        p25_added_gold=5,
        p25_added_false=8,
        p25_actions={"use_p25_action": 10, "weak_only": 0},
        p25_llm=8,
        f1_added_gold=5,
        f1_added_false=4,
        f1_actions={"use_p25_action": 6, "weak_only": 4},
        f1_llm=5,
        f2_added_gold=3,
        f2_added_false=2,
        f2_actions={"use_p25_action": 4, "weak_only": 6},
        f2_llm=3,
        mean_span_f05=0.10,
        mean_pfp_p25=0.05,
        mean_pfp_f1=0.02,
        mean_pfp_f2=0.01,
        ng_p25=0.20,
        ng_f1=0.10,
        ng_f2=0.05,
        run_id="b8-lite-self-test-run-a",
    )
    report_b = _synthetic_b6c_report(
        task_count=14,
        positive_task_count=9,
        no_gold_task_count=5,
        p25_added_gold=7,
        p25_added_false=12,
        p25_actions={"use_p25_action": 14, "weak_only": 0},
        p25_llm=11,
        f1_added_gold=7,
        f1_added_false=6,
        f1_actions={"use_p25_action": 8, "weak_only": 6},
        f1_llm=7,
        f2_added_gold=4,
        f2_added_false=3,
        f2_actions={"use_p25_action": 5, "weak_only": 9},
        f2_llm=4,
        mean_span_f05=0.20,
        mean_pfp_p25=0.04,
        mean_pfp_f1=0.03,
        mean_pfp_f2=0.02,
        ng_p25=0.15,
        ng_f1=0.05,
        ng_f2=0.10,
        run_id="b8-lite-self-test-run-b",
    )
    return [report_a, report_b]


def _expected_family(
    fam_a: dict[str, Any], fam_b: dict[str, Any]
) -> dict[str, Any]:
    """Independent re-derivation of expected combined family values, used to
    cross-check the combiner."""
    task_count = fam_a["task_count"] + fam_b["task_count"]
    added_gold = fam_a["added_gold_span"] + fam_b["added_gold_span"]
    added_false = fam_a["added_false_span"] + fam_b["added_false_span"]
    action_counts = {
        k: fam_a["action_counts"].get(k, 0) + fam_b["action_counts"].get(k, 0)
        for k in ACTION_KEYS
    }
    effective_llm = (
        fam_a["effective_llm_action_count"] + fam_b["effective_llm_action_count"]
    )
    no_gold = fam_a["no_gold_task_count"] + fam_b["no_gold_task_count"]

    def wmean(field: str, weight_field: str) -> float:
        num = 0.0
        den = 0
        for fam in (fam_a, fam_b):
            w = fam[weight_field]
            v = fam[field]
            num += v * w
            den += w
        assert den > 0, f"zero weight for {field}"
        return num / den

    return {
        "task_count": task_count,
        "comparable_task_count": task_count,
        "positive_task_count": fam_a["positive_task_count"]
        + fam_b["positive_task_count"],
        "no_gold_task_count": no_gold,
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "action_counts": action_counts,
        "action_rates": {
            k: round(action_counts[k] / task_count, 6) for k in ACTION_KEYS
        },
        "effective_llm_action_count": effective_llm,
        "effective_llm_action_rate": round(effective_llm / task_count, 6),
        "false_per_gold": round(added_false / added_gold, 6) if added_gold else None,
        "net_span_value_2x": added_gold - 2 * added_false,
        "mean_span_f05": round(wmean("mean_span_f05", "task_count"), 6),
        "mean_primary_false_positive_rate": round(
            wmean("mean_primary_false_positive_rate", "task_count"), 6
        ),
        "no_gold_false_primary_rate": round(
            wmean("no_gold_false_primary_rate", "no_gold_task_count"), 6
        ),
    }


def _assert_family_matches(
    name: str, combined: dict[str, Any], expected: dict[str, Any]
) -> None:
    for field in (
        "task_count",
        "comparable_task_count",
        "positive_task_count",
        "no_gold_task_count",
        "added_gold_span",
        "added_false_span",
        "effective_llm_action_count",
        "false_per_gold",
        "net_span_value_2x",
        "mean_span_f05",
        "mean_primary_false_positive_rate",
        "no_gold_false_primary_rate",
        "effective_llm_action_rate",
    ):
        got = combined.get(field)
        exp = expected[field]
        if exp is None:
            assert got is None, f"{name}.{field}: expected None, got {got}"
        elif isinstance(exp, float):
            assert got is not None, f"{name}.{field}: expected {exp}, got None"
            assert abs(round(got, 6) - round(exp, 6)) < 1e-9, (
                f"{name}.{field}: expected {exp}, got {got}"
            )
        else:
            assert got == exp, f"{name}.{field}: expected {exp}, got {got}"
    for k in ACTION_KEYS:
        assert (
            combined["action_counts"][k] == expected["action_counts"][k]
        ), f"{name}.action_counts.{k}: expected {expected['action_counts'][k]}, got {combined['action_counts'][k]}"
        assert (
            abs(round(combined["action_rates"][k], 6) - round(expected["action_rates"][k], 6))
            < 1e-9
        ), (
            f"{name}.action_rates.{k}: expected {expected['action_rates'][k]}, "
            f"got {combined['action_rates'][k]}"
        )


def _self_test_happy_path() -> dict[str, Any]:
    reports = _build_self_test_inputs()
    # Validate the synthetic inputs pass the real input contract.
    _validate_input_report(reports[0], "synthetic-a")
    _validate_input_report(reports[1], "synthetic-b")
    _validate_cross_report(reports)

    report = combine(
        reports,
        source_run_ids=["10000000001", "10000000002"],
        private_disjointness_verified=True,
        self_test=True,
    )
    assert report["status"] == "self_test_only", report["status"]
    assert report["claim_level"] == CLAIM_LEVEL
    assert report["policy_search_performed"] is False
    assert report["new_provider_calls"] == 0
    assert report["promotion_ready"] is False
    assert report["default_should_change"] is False
    assert report["evidencecore_semantics_changed"] is False
    assert report["derived_aggregate_rollup"] is True
    assert report["single_model_only"] is True
    assert report["winner_declared"] is False
    assert report["default_recommendation_declared"] is False
    assert report["promotion_declared"] is False
    assert report["repo_ids_in_artifact"] is False
    assert report["repo_names_in_artifact"] is False
    assert report["repo_set_hash_in_artifact"] is False

    fams_a = reports[0]["policy_families"]
    fams_b = reports[1]["policy_families"]
    combined = report["policy_families"]
    expected_names = sorted(
        EXPECTED_FROZEN_NAMES | {"p25_bucket_routed_v0_plain"}
    )
    assert sorted(combined.keys()) == expected_names, sorted(combined.keys())
    for name in expected_names:
        _assert_family_matches(
            name, combined[name], _expected_family(fams_a[name], fams_b[name])
        )

    # No forbidden keys in the public output.
    violations = b6lite._walk_forbidden(report)
    assert not violations, f"forbidden keys in output: {violations[:5]}"
    assert (
        report["frozen_manifest_integrity"]["forbidden_public_key_scan_clean"]
        is True
    )

    # No winner / default / promotion / repo-set hash keys.
    for forbidden in (
        "winner",
        "default_recommendation",
        "promotion",
        "repo_set_hash",
        "repo_names",
        "repo_ids",
        "task_ids",
        "candidate_ids",
        "input_paths",
    ):
        assert forbidden not in report, f"forbidden key present: {forbidden}"

    print("self-test happy path: ok")
    return report


def _self_test_disjointness_blocks() -> None:
    reports = _build_self_test_inputs()
    report = combine(
        reports,
        source_run_ids=None,
        private_disjointness_verified=False,
        self_test=False,
    )
    assert report["status"] == "blocked_disjointness", report["status"]
    assert report["claim_level"] == CLAIM_LEVEL
    assert report["policy_families"] == {}
    assert report["private_disjointness_verified"] is False
    violations = b6lite._walk_forbidden(report)
    assert not violations, f"forbidden keys in blocked output: {violations[:5]}"
    print("self-test disjointness blocks: ok")


def _self_test_input_contract_violation() -> None:
    reports = _build_self_test_inputs()
    # Corrupt one input: flip a required-false flag.
    reports[0]["policy_search_performed"] = True
    try:
        _validate_input_report(reports[0], "corrupted-a")
    except ValueError:
        pass
    else:
        raise AssertionError("expected input contract violation to be rejected")
    print("self-test input contract violation rejected: ok")


def _self_test_cross_report_mismatch() -> None:
    reports = _build_self_test_inputs()
    # Mutate comparability.model in the second report.
    reports[1] = json.loads(json.dumps(reports[1]))
    reports[1]["comparability"]["model"] = "[mk]GLM-5.2"
    try:
        _validate_cross_report(reports)
    except ValueError as exc:
        assert "comparability.model" in str(exc), str(exc)
    else:
        raise AssertionError("expected cross-report mismatch to be rejected")

    # Also test policy_rules mismatch path.
    reports2 = _build_self_test_inputs()
    reports2[1] = json.loads(json.dumps(reports2[1]))
    fam = reports2[1]["policy_families"][
        "ambiguous_query_weak_only_default_use_p25_action"
    ]
    fam["policy_rules"] = list(fam["policy_rules"]) + [
        {
            "name": "extra",
            "predicates": ["always_true"],
            "action": "use_p25_action",
            "is_default": False,
        }
    ]
    try:
        _validate_cross_report(reports2)
    except ValueError as exc:
        assert "policy_rules" in str(exc) or "family set" in str(exc), str(exc)
    else:
        raise AssertionError("expected policy_rules mismatch to be rejected")
    print("self-test cross-report mismatch rejected: ok")


def _self_test_forbidden_key_in_output_scan() -> None:
    """The combiner's own output scan must catch a forbidden key if one ever
    leaks into the public report (regression guard)."""
    reports = _build_self_test_inputs()
    report = combine(
        reports,
        source_run_ids=["10000000001", "10000000002"],
        private_disjointness_verified=True,
        self_test=True,
    )
    # Inject a forbidden key and confirm _walk_forbidden catches it.
    report["repo_id"] = "leaked"
    violations = b6lite._walk_forbidden(report)
    assert any("repo_id" in v for v in violations), violations
    print("self-test forbidden key in output scan: ok")


def _self_test_bad_source_run_ids_block() -> None:
    reports = _build_self_test_inputs()
    try:
        _validate_source_run_ids(["27717886432", "artifacts/private/path.json"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected non-numeric source run id to be rejected")
    report = _blocked_report(
        "blocked_input_contract",
        False,
        None,
        reason="bad_source_run_ids",
        detail="source_run_ids must be decimal GitHub workflow run IDs",
    )
    assert report["status"] == "blocked_input_contract"
    assert "source_run_ids" not in report
    _ = reports  # keep synthetic input path exercised without exposing it
    print("self-test bad source run ids blocked: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_input_contract_violation()
    _self_test_cross_report_mismatch()
    _self_test_disjointness_blocks()
    _self_test_forbidden_key_in_output_scan()
    _self_test_bad_source_run_ids_block()
    report = _self_test_happy_path()
    print("all b8-lite self-tests passed")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reports",
        nargs="+",
        type=Path,
        help="Exactly two b6c-frozen-policy-validation-v0 aggregate JSON report paths.",
    )
    parser.add_argument(
        "--source-run-ids",
        nargs="+",
        default=None,
        help="Optional workflow run IDs for the two source B6E/B6F runs.",
    )
    parser.add_argument(
        "--private-disjointness-verified",
        action="store_true",
        help="Assert that the two source runs used disjoint task/repo universes. "
        "Required for status=ok; otherwise blocked_disjointness.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if not args.self_test:
        if not args.reports or len(args.reports) != 2:
            parser.error(
                "b8-lite combiner requires exactly two --reports (B6C/B6F aggregate JSON)"
            )
        if args.source_run_ids and len(args.source_run_ids) != 2:
            parser.error(
                "--source-run-ids must provide exactly two run IDs (B6E/B6F)"
            )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
        report = combine(
            _build_self_test_inputs(),
            source_run_ids=["10000000001", "10000000002"],
            private_disjointness_verified=True,
            self_test=True,
        )
    else:
        report = build_report(args)
    _write_json(args.out, report)
    _write_markdown(report, args.doc)
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim_level": report["claim_level"],
                "included_source_report_count": report.get(
                    "included_source_report_count"
                ),
                "comparable_task_count": report.get("comparable_task_count"),
                "frozen_policy_count": report.get("frozen_policy_count"),
                "policy_search_performed": report.get("policy_search_performed"),
                "new_provider_calls": report.get("new_provider_calls"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
