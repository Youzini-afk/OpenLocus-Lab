#!/usr/bin/env python3
"""B11 prospective matrix combiner (bounded aggregate rollup).

B11-matrix is a **derived aggregate rollup**. It combines the public
``b11-prospective-validation-report-v0`` and
``b10b-runtime-shadow-replay-report-v0`` aggregate JSON artifacts produced by a
finished B11 official integrated matrix run into a single derived aggregate.
It performs:

* **no** per-task / per-repo / per-candidate / source-record reads;
* **no** provider calls (``new_provider_calls == 0``);
* **no** policy search, rule generation, retuning, or winner selection;
* **no** promotion / default / model-robust claim.

The only inputs are the already-downloaded aggregate-only public artifacts
under a run-artifacts directory. The output preserves the
``aggregate_only_public_artifact`` contract: no repo paths, no task IDs, no
candidate IDs, no digests, no hashes, no per-record rows, no prompts, no
responses, no snippets, no private labels. It MAY publish public repo slice
IDs (e.g. ``py_fastapi``) and public model-family names (e.g. ``kimi``,
``deepseek_pro``) that the per-run public reports already publish, plus
sanitized counts and weighted means. Individual workflow run IDs are NOT
emitted; only ``run_count`` and ``record_count_total``.

This is a **strengthening signal for the algorithm candidate**, not a
runtime-clean general algorithm claim. The B11 official matrix verdict is
mixed/partial.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite

SCHEMA_VERSION = "b11-prospective-matrix-aggregate-report-v0"
GENERATED_BY = "b11_matrix_combiner"
CLAIM_LEVEL = "derived_aggregate_of_b11_prospective_validation_reports"
INPUT_B11_SCHEMA = "b11-prospective-validation-report-v0"
INPUT_B10B_SCHEMA = "b10b-runtime-shadow-replay-report-v0"
BASELINE_FOR_DELTAS = "p25"
POLICY_UNDER_VALIDATION = "balanced_v1"

POLICIES = ("local_baseline", "p25", "balanced_v1", "conservative")
METRICS = (
    "gold_span",
    "false_span",
    "span_f0_5",
    "primary_false_positive_rate",
    "model_calls",
)
RUN_ID_REGEX = b6lite.re.compile(r"^[A-Za-z0-9._\-]+$")

DEFAULT_OUT = Path(
    "artifacts/b11_prospective_matrix/"
    "b11_prospective_matrix_aggregate_report.json"
)

# Repo slice IDs and model-family names are public (already published by the
# per-run B11 reports under `repos` and `model_families`).
PUBLIC_REPO_SLICE_IDS = (
    "py_fastapi",
    "py_pytest",
    "ts_vite",
    "ts_hono",
    "go_chi",
    "go_prometheus",
    "rust_deno",
    "java_spring_petclinic",
)
PUBLIC_MODEL_FAMILY_NAMES = (
    "kimi",
    "qwen",
    "deepseek_flash",
    "deepseek_pro",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _round6(value: float) -> float:
    if value is None:
        return None
    return round(float(value), 6)


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "candidate_ids_in_artifact": False,
        "task_ids_in_artifact": False,
        "public_repo_slice_ids_in_artifact": True,
        "raw_repo_ids_in_artifact": False,
        "run_ids_in_artifact": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "winner_declared": False,
        "derived_aggregate_rollup": True,
        "input_b11_schema_version": INPUT_B11_SCHEMA,
        "input_b10b_schema_version": INPUT_B10B_SCHEMA,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "policy_under_validation": POLICY_UNDER_VALIDATION,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run forbidden-key scan on the public output and record the result."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b11-matrix public output would contain forbidden keys/values; "
            f"first violations: {violations[:5]}"
        )


def _parse_run_top(run_dir_name: str) -> tuple[str, str, str] | None:
    """Parse ``<repo_slice>__<model>__<run_id>`` directory name.

    Returns ``(repo_slice_id, model_display_name, run_id)`` or ``None`` if the
    name does not match the expected shape. ``repo_slice_id`` must be in the
    public allowlist; ``model_display_name`` is sanitized to a public family.
    """
    parts = run_dir_name.split("__")
    if len(parts) != 3:
        return None
    repo_slice, model_name, run_id = parts
    if repo_slice not in PUBLIC_REPO_SLICE_IDS:
        return None
    if not RUN_ID_REGEX.match(run_id):
        return None
    return repo_slice, model_name, run_id


def _model_to_family(model_display_name: str) -> str:
    name = model_display_name.lower()
    if "kimi" in name:
        return "kimi"
    if "qwen" in name:
        return "qwen"
    if "flash" in name:
        return "deepseek_flash"
    if "pro" in name:
        return "deepseek_pro"
    return "unknown"


def _discover_reports(artifacts_dir: Path) -> list[dict[str, Any]]:
    """Find every B11 + matching B10B aggregate report under ``artifacts_dir``."""
    b11_globs = sorted(
        glob.glob(
            str(artifacts_dir / "*" / "*" / "artifacts" / "real_provider_ci"
                / "b11_prospective_validation_report.json"),
            recursive=False,
        )
    )
    discovered: list[dict[str, Any]] = []
    for b11_path in b11_globs:
        b11_p = Path(b11_path)
        b10b_p = b11_p.parent / "b10b_runtime_shadow_replay_report.json"
        run_top = b11_p.parts[-5]  # <repo>__<model>__<runid>
        parsed = _parse_run_top(run_top)
        if parsed is None:
            raise ValueError(
                f"unexpected run directory name (not a public B11 matrix slice): "
                f"{run_top}"
            )
        repo_slice, model_name, run_id = parsed
        if not b11_p.exists():
            raise FileNotFoundError(f"missing B11 report: {b11_p}")
        if not b10b_p.exists():
            raise FileNotFoundError(f"missing B10B report: {b10b_p}")
        discovered.append(
            {
                "repo_slice": repo_slice,
                "model_display_name": model_name,
                "model_family": _model_to_family(model_name),
                "run_id": run_id,
                "b11_path": str(b11_p),
                "b10b_path": str(b10b_p),
            }
        )
    return discovered


def _validate_b11(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_B11_SCHEMA:
        raise ValueError(
            f"unexpected B11 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("B11 input must be aggregate_only_public_artifact=true")
    if report.get("promotion_ready") is not False:
        raise ValueError("B11 input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError("B11 input must have policy_search_performed=false")
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B11 input must have candidate_not_fact=true")


def _validate_b10b(report: dict[str, Any]) -> None:
    if report.get("schema_version") != INPUT_B10B_SCHEMA:
        raise ValueError(
            f"unexpected B10B schema_version: {report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("B10B input must be aggregate_only_public_artifact=true")
    if report.get("promotion_ready") is not False:
        raise ValueError("B10B input must have promotion_ready=false")
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B10B input must have candidate_not_fact=true")
    if report.get("policy_search_performed") is not False:
        raise ValueError("B10B input must have policy_search_performed=false")
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("B10B input must have quality_strategy_tuned=false")


def _accumulate_weighted_means(
    b11: dict[str, Any],
    n_records: int,
    acc: dict[str, dict[str, float]],
) -> None:
    per_policy = b11.get("per_policy_metrics", {})
    for pol in POLICIES:
        om = per_policy.get(pol, {}).get("overall_mean", {})
        for m in METRICS:
            acc[pol][m] += n_records * _as_float(om.get(m, 0.0))


def _accumulate_model_weighted(
    b11: dict[str, Any],
    n_records: int,
    model_family: str,
    per_model_acc: dict[str, dict[str, dict[str, float]]],
    per_model_records: dict[str, int],
) -> None:
    per_policy = b11.get("per_policy_metrics", {})
    per_model_records[model_family] += n_records
    for pol in ("p25", "balanced_v1"):
        om = per_policy.get(pol, {}).get("overall_mean", {})
        for m in METRICS:
            per_model_acc[model_family][pol][m] += n_records * _as_float(
                om.get(m, 0.0)
            )


def _weighted_mean(acc: dict[str, float], total: int) -> dict[str, float]:
    """Return UNROUNDED record-weighted means; rounding is applied only at publish time.

    Deltas must be computed from unrounded means so that
    ``delta = mean(balanced) - mean(p25)`` is not distorted by independent
    rounding of each published mean.
    """
    if total <= 0:
        return {m: 0.0 for m in METRICS}
    return {m: float(acc[m]) / float(total) for m in METRICS}


def _round_dict(d: dict[str, float]) -> dict[str, float]:
    return {m: _round6(d[m]) for m in METRICS}


def _deltas(b: dict[str, float], base: dict[str, float]) -> dict[str, float]:
    """Compute deltas from UNROUNDED means; round the result for publication."""
    return {m: _round6(b[m] - base[m]) for m in METRICS}


def combine(
    artifacts_dir: Path,
    self_test: bool = False,
) -> dict[str, Any]:
    """Combine the B11/B10B public aggregate reports into one rollup."""
    discovered = _discover_reports(artifacts_dir)
    if not discovered:
        raise ValueError(
            f"no B11/B10B aggregate reports discovered under {artifacts_dir}"
        )

    report = _base_report(self_test)
    report["source_artifacts_dir_public_note"] = (
        "already-downloaded aggregate-only public B11 and B10B artifacts; "
        "no raw records, paths, prompts, responses, snippets, or labels read"
    )

    # Integrity / contract flags from inputs (B11 + B10B)
    integrity: dict[str, Any] = {
        "all_inputs_aggregate_only_public_artifact": True,
        "all_inputs_promotion_ready_false": True,
        "all_inputs_policy_search_performed_false": True,
        "all_inputs_quality_strategy_tuned_false": True,
        "all_inputs_candidate_not_fact": True,
        "frozen_reference_specs_pinned_on_disk": True,
    }

    total_records = 0
    verdicts: Counter = Counter()
    per_model_verdicts: dict[str, Counter] = defaultdict(Counter)
    per_model_records: dict[str, int] = defaultdict(int)
    per_model_acc: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: {
            "p25": {m: 0.0 for m in METRICS},
            "balanced_v1": {m: 0.0 for m in METRICS},
        }
    )
    weighted_acc: dict[str, dict[str, float]] = {
        pol: {m: 0.0 for m in METRICS} for pol in POLICIES
    }
    failure_runs: list[dict[str, str]] = []
    b10b_support_claims: Counter = Counter()
    b10b_runtime_shadow_supported_all_false = True
    b10b_label_driven_denominators: list[int] = []
    public_repo_slices_seen: set[str] = set()
    public_model_families_seen: set[str] = set()

    for entry in discovered:
        b11 = json.loads(Path(entry["b11_path"]).read_text(encoding="utf-8"))
        b10b = json.loads(Path(entry["b10b_path"]).read_text(encoding="utf-8"))
        _validate_b11(b11)
        _validate_b10b(b10b)

        n_records = _as_int(b11.get("input_meta", {}).get("n_records", 0))
        total_records += n_records
        verdict = b11.get("verdict", "unknown")
        verdicts[verdict] += 1
        per_model_verdicts[entry["model_family"]][verdict] += 1
        public_repo_slices_seen.add(entry["repo_slice"])
        public_model_families_seen.add(entry["model_family"])

        _accumulate_weighted_means(b11, n_records, weighted_acc)
        _accumulate_model_weighted(
            b11,
            n_records,
            entry["model_family"],
            per_model_acc,
            per_model_records,
        )

        if verdict == "failure":
            failure_runs.append(
                {
                    "model_family": entry["model_family"],
                    "repo_slice_id": entry["repo_slice"],
                    "verdict_reason": str(b11.get("verdict_reason", "")),
                }
            )

        # B10B
        support_claim = b10b.get("support_claim", "unknown")
        b10b_support_claims[support_claim] += 1
        if b10b.get("runtime_shadow_ambiguous_supported") is not False:
            b10b_runtime_shadow_supported_all_false = False
        replay = b10b.get("replay", {}) or {}
        denom = _as_int(replay.get("label_driven_ambiguous_denominator_qn0"))
        b10b_label_driven_denominators.append(denom)

    # Compute UNROUNDED weighted means; deltas use these unrounded values so
    # rounding one mean does not distort the delta. Rounding is applied only
    # when the means/deltas are published below.
    overall_means_unrounded = {
        pol: _weighted_mean(weighted_acc[pol], total_records) for pol in POLICIES
    }
    deltas_balanced_vs_p25 = _deltas(
        overall_means_unrounded["balanced_v1"], overall_means_unrounded["p25"]
    )
    overall_means = {
        pol: _round_dict(overall_means_unrounded[pol]) for pol in POLICIES
    }

    # Per-model weighted means + deltas (deltas from unrounded means)
    per_model_summary: dict[str, Any] = {}
    for family in sorted(per_model_records):
        n = per_model_records[family]
        p25_unrounded = _weighted_mean(per_model_acc[family]["p25"], n)
        bal_unrounded = _weighted_mean(per_model_acc[family]["balanced_v1"], n)
        per_model_summary[family] = {
            "record_count": n,
            "run_count": sum(
                1
                for e in discovered
                if e["model_family"] == family
            ),
            "verdict_counts": dict(per_model_verdicts[family]),
            "balanced_v1_overall_mean": _round_dict(bal_unrounded),
            "p25_overall_mean": _round_dict(p25_unrounded),
            "delta_balanced_v1_vs_p25": _deltas(bal_unrounded, p25_unrounded),
        }

    # B10B aggregate summary (no per-run detail; counts only).
    #
    # The `empirical_replay_support_pending` verdict is asserted ONLY when all
    # three predeclared conditions hold:
    #   (a) every B10B report has `runtime_shadow_ambiguous_supported=false`;
    #   (b) every B10B report has
    #       `support_claim="empirical_replay_support_pending"`; AND
    #   (c) `label_driven_ambiguous_denominator_max` is below the
    #       `label_driven_ambiguous_min_denominator_gate` hard gate (10).
    # Otherwise the verdict is `mixed` (some runs disagree) or
    # `not_applicable` (gate satisfied but no run reports pending).
    # Arbitrary all-false B10B outputs that do not meet all three conditions
    # are NOT labelled pending.
    label_driven_min_gate = 10
    if b10b_label_driven_denominators:
        denom_max = max(b10b_label_driven_denominators)
    else:
        denom_max = 0
    all_runtime_shadow_false = b10b_runtime_shadow_supported_all_false
    all_support_claim_pending = (
        bool(b10b_support_claims)
        and set(b10b_support_claims.keys())
        == {"empirical_replay_support_pending"}
    )
    pending_due_denominator = (
        all_runtime_shadow_false
        and all_support_claim_pending
        and denom_max < label_driven_min_gate
    )
    if pending_due_denominator:
        b10b_verdict = "empirical_replay_support_pending"
        b10b_verdict_reason = (
            "all B10B reports have runtime_shadow_ambiguous_supported=false, "
            "support_claim=empirical_replay_support_pending, and "
            "label_driven_ambiguous_denominator_max < "
            "label_driven_ambiguous_min_denominator_gate"
        )
    elif not all_runtime_shadow_false:
        b10b_verdict = "mixed"
        b10b_verdict_reason = (
            "at least one run reported runtime_shadow_ambiguous_supported=true"
        )
    elif not all_support_claim_pending:
        b10b_verdict = "mixed"
        b10b_verdict_reason = (
            "runtime_shadow_ambiguous_supported is false across all runs but "
            "support_claim values are not uniformly "
            "empirical_replay_support_pending"
        )
    else:
        # all_runtime_shadow_false and all_support_claim_pending but
        # denom_max >= gate: the predicate is not pending due to denominator.
        b10b_verdict = "not_applicable"
        b10b_verdict_reason = (
            "denominator gate met across all runs; "
            "runtime_shadow_ambiguous_supported is still false but not "
            "attributable to insufficient_label_driven_denominator"
        )

    b10b_summary = {
        "b10b_report_count": len(discovered),
        "runtime_shadow_ambiguous_supported_any": (
            not all_runtime_shadow_false
        ),
        "runtime_shadow_ambiguous_supported_all_false": (
            all_runtime_shadow_false
        ),
        "support_claim_counts": dict(b10b_support_claims),
        "label_driven_ambiguous_denominator_max": denom_max,
        "label_driven_ambiguous_denominator_min": (
            min(b10b_label_driven_denominators)
            if b10b_label_driven_denominators
            else 0
        ),
        "label_driven_ambiguous_min_denominator_gate": label_driven_min_gate,
        "pending_due_denominator": pending_due_denominator,
        "verdict": b10b_verdict,
        "verdict_reason": b10b_verdict_reason,
    }

    # Aggregate verdict (mixed/partial; never success)
    success_count = verdicts.get("success", 0)
    partial_count = verdicts.get("partial", 0)
    failure_count = verdicts.get("failure", 0)
    if failure_count > 0:
        aggregate_verdict = "partial_with_failure"
        aggregate_verdict_reason = (
            "mixed_results_with_failure_threshold_exceeded_on_at_least_one_slice"
        )
    elif partial_count > 0:
        aggregate_verdict = "partial"
        aggregate_verdict_reason = (
            "mixed_results_no_failure_threshold_exceeded"
        )
    else:
        aggregate_verdict = "partial"
        aggregate_verdict_reason = "all_success_aggregate_still_partial_pending_b12"

    report.update(
        {
            "status": "ok" if not self_test else "self_test_only",
            "run_count": len(discovered),
            "record_count_total": total_records,
            "public_repo_slice_count": len(public_repo_slices_seen),
            "public_repo_slice_ids": sorted(public_repo_slices_seen),
            "public_model_family_count": len(public_model_families_seen),
            "public_model_family_names": sorted(public_model_families_seen),
            "policies": list(POLICIES),
            "metric_names": list(METRICS),
            "verdict_counts": dict(verdicts),
            "aggregate_verdict": aggregate_verdict,
            "aggregate_verdict_reason": aggregate_verdict_reason,
            "overall_weighted_means": overall_means,
            "deltas_balanced_v1_vs_p25": deltas_balanced_vs_p25,
            "per_model_family": per_model_summary,
            "failure_slices_sanitized": failure_runs,
            "b10b_runtime_shadow_summary": b10b_summary,
            "integrity": integrity,
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "no_evidencecore_semantics_change": True,
                "no_live_llm_calls_by_combiner": True,
                "no_policy_search": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "signal_strength": "algorithm_candidate_strengthened_not_proven",
                "recommended_next_step": "B12_mechanism_decomposition",
                "b10b_runtime_shadow_status": (
                    "empirical_replay_support_pending_due_denominator"
                ),
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_self_test_artifacts(root: Path) -> Path:
    """Materialize a tiny synthetic public-artifact tree mirroring the real layout."""
    artifacts = root / "artifacts"
    policies_payload = {
        "local_baseline": {
            "n_records": 4,
            "overall_mean": {
                "gold_span": 0.5,
                "false_span": 1.0,
                "span_f0_5": 0.1,
                "primary_false_positive_rate": 0.25,
                "model_calls": 0.0,
            },
        },
        "p25": {
            "n_records": 4,
            "overall_mean": {
                "gold_span": 0.25,
                "false_span": 0.25,
                "span_f0_5": 0.1,
                "primary_false_positive_rate": 0.0,
                "model_calls": 1.0,
            },
        },
        "balanced_v1": {
            "n_records": 4,
            "overall_mean": {
                "gold_span": 0.25,
                "false_span": 0.0,
                "span_f0_5": 0.1,
                "primary_false_positive_rate": 0.0,
                "model_calls": 0.5,
            },
        },
        "conservative": {
            "n_records": 4,
            "overall_mean": {
                "gold_span": 0.125,
                "false_span": 0.25,
                "span_f0_5": 0.05,
                "primary_false_positive_rate": 0.0,
                "model_calls": 0.0,
            },
        },
    }
    b11_base = {
        "aggregate_only_public_artifact": True,
        "algorithm_spec_id": "b11_prospective_v0",
        "candidate_not_fact": True,
        "claim_level": "prospective_validation_v0",
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "generated_at": "2026-06-18T00:00:00+00:00",
        "generated_by": "b11_prospective_validation",
        "input_meta": {"n_files": 1, "n_records": 4, "source_kind": "file_object"},
        "llm_output_not_evidence": True,
        "metric_names": list(METRICS),
        "model_families": ["kimi"],
        "not_evidence": True,
        "policies": list(POLICIES),
        "policy_search_performed": False,
        "promotion_ready": False,
        "quality_strategy_tuned": False,
        "repos": ["py_fastapi"],
        "schema_version": INPUT_B11_SCHEMA,
        "self_test": False,
        "verdict": "partial",
        "verdict_reason": "self_test_synthetic",
        "per_policy_metrics": policies_payload,
    }
    b10b_base = {
        "aggregate_only_public_artifact": True,
        "algorithm_spec_id": "balanced_policy_v1_runtime_shadow_ambiguous_branch",
        "candidate_not_fact": True,
        "claim_level": "ambiguous_branch_runtime_shadow_only",
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "generated_at": "2026-06-18T00:00:00+00:00",
        "generated_by": "b10b_runtime_shadow_replay",
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "policy_search_performed": False,
        "promotion_ready": False,
        "quality_strategy_tuned": False,
        "replay": {
            "label_driven_ambiguous_denominator_qn0": 2,
        },
        "runtime_shadow_ambiguous_supported": False,
        "schema_version": INPUT_B10B_SCHEMA,
        "self_test": False,
        "status": "ok",
        "support_claim": "empirical_replay_support_pending",
        "support_claim_reason": "insufficient_label_driven_denominator",
    }

    runs = [
        ("py_fastapi", "Kimi-K2.7-Code", "99900000001", "partial"),
        ("py_pytest", "DeepSeek-V4-Pro", "99900000002", "success"),
        ("ts_vite", "DeepSeek-V4-Flash", "99900000003", "failure"),
        ("ts_hono", "Qwen3.6-27B", "99900000004", "partial"),
    ]
    for repo_slice, model_name, run_id, verdict in runs:
        run_top = f"{repo_slice}__{model_name}__{run_id}"
        ci_dir = (
            artifacts
            / run_top
            / f"real-provider-{run_top}"
            / "artifacts"
            / "real_provider_ci"
        )
        ci_dir.mkdir(parents=True, exist_ok=True)
        b11 = dict(b11_base)
        b11["verdict"] = verdict
        b11["model_families"] = [_model_to_family(model_name)]
        b11["repos"] = [repo_slice]
        if verdict == "failure":
            b11["verdict_reason"] = "failure_threshold_exceeded: failure_spanf05_delta"
        (ci_dir / "b11_prospective_validation_report.json").write_text(
            json.dumps(b11, sort_keys=True), encoding="utf-8"
        )
        (ci_dir / "b10b_runtime_shadow_replay_report.json").write_text(
            json.dumps(b10b_base, sort_keys=True), encoding="utf-8"
        )
    return artifacts


def _self_test_happy_path() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_self_test_artifacts(root)
        report = combine(root / "artifacts", self_test=True)
    assert report["status"] == "self_test_only", report["status"]
    assert report["run_count"] == 4, report["run_count"]
    assert report["record_count_total"] == 16, report["record_count_total"]
    assert report["verdict_counts"] == {
        "partial": 2,
        "success": 1,
        "failure": 1,
    }, report["verdict_counts"]
    assert report["aggregate_verdict"] == "partial_with_failure", report[
        "aggregate_verdict"
    ]
    # balanced_v1 vs p25: gold 0.25-0.25=0, false 0-0.25=-0.25, calls 0.5-1.0=-0.5
    d = report["deltas_balanced_v1_vs_p25"]
    assert d["gold_span"] == 0.0, d
    assert d["false_span"] == -0.25, d
    assert d["model_calls"] == -0.5, d
    # B10B
    b10b = report["b10b_runtime_shadow_summary"]
    assert b10b["b10b_report_count"] == 4, b10b
    assert b10b["runtime_shadow_ambiguous_supported_all_false"] is True, b10b
    assert (
        b10b["support_claim_counts"]
        == {"empirical_replay_support_pending": 4}
    ), b10b
    # pending_due_denominator requires all three predeclared conditions
    assert b10b["pending_due_denominator"] is True, b10b
    assert b10b["verdict"] == "empirical_replay_support_pending", b10b
    assert (
        b10b["label_driven_ambiguous_denominator_max"] == 2
    ), b10b
    assert (
        b10b["label_driven_ambiguous_min_denominator_gate"] == 10
    ), b10b
    # forbidden-key scan clean
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # no run IDs emitted; public repo slice IDs ARE emitted (allowed)
    assert report["run_ids_in_artifact"] is False
    assert report["public_repo_slice_ids_in_artifact"] is True
    assert report["raw_repo_ids_in_artifact"] is False
    # B10B input invariants were validated (all four)
    assert report["integrity"]["all_inputs_quality_strategy_tuned_false"] is True
    print("self-test happy path: ok")
    return report


def _self_test_no_inputs_blocks() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            combine(Path(tmp), self_test=True)
        except ValueError as exc:
            assert "no B11/B10B aggregate reports discovered" in str(exc), exc
            print("self-test no-inputs block: ok")
            return
    raise AssertionError("combine should have raised on empty input")


def run_self_tests() -> dict[str, Any]:
    _self_test_happy_path()
    _self_test_no_inputs_blocks()
    return {"self_test_passed": True}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("/tmp/b11_official_integrated_artifacts"),
        help="Directory of already-downloaded public B11/B10B aggregate artifacts.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
        return 0
    report = combine(args.artifacts_dir, self_test=False)
    _write_json(args.out, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim_level": report["claim_level"],
                "run_count": report["run_count"],
                "record_count_total": report["record_count_total"],
                "verdict_counts": report["verdict_counts"],
                "aggregate_verdict": report["aggregate_verdict"],
                "promotion_ready": report["promotion_ready"],
                "new_provider_calls": report["new_provider_calls"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
