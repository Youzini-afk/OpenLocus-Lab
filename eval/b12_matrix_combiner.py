#!/usr/bin/env python3
"""B12 mechanism decomposition official matrix aggregate combiner (C2/B12).

This is a **bounded derived aggregate rollup**. It combines the already-
downloaded public ``b12-mechanism-decomposition-report-v0`` aggregate JSON
artifacts produced by a finished C2/B12 official integrated matrix run into a
single derived aggregate. It performs:

* **no** per-task / per-repo / per-candidate / source-record reads (it reads
  only the already-published per-run B12 aggregate reports);
* **no** provider calls (``new_provider_calls == 0``);
* **no** policy search, rule generation, retuning, or winner selection;
* **no** promotion / default / runtime-clean / EvidenceCore-semantics claim.

The only inputs are the already-downloaded aggregate-only public B12 reports
under an artifacts directory, plus an optional final manifest that records
which (repo × model) cells were analyzable (``included``) and which were
excluded for coverage insufficiency (``excluded`` — the 4 ``ts_vite`` cells
that did not exercise remote LLM snippets even at ``max_tasks=24``).

The output preserves the ``aggregate_only_public_artifact`` contract: no run
IDs, task IDs, raw repo IDs, paths, spans, content hashes, prompts, responses,
snippets, provider URLs, or provider keys. It MAY publish public repo slice
IDs (e.g. ``py_fastapi``) and public model-family names (e.g. ``kimi``,
``deepseek_pro``) — but only as **public slice IDs from the manifest**, never
as run IDs. Counts by (public repo slice, model family) are emitted for the
coverage exclusions, with no run IDs.

This is a **mechanism decomposition aggregate**, not a promotion step. The C2
B12 official matrix verdict is ``partial_with_coverage_exclusions`` (28 of 32
cells analyzable; 4 ``ts_vite`` cells excluded for
``coverage_insufficient_no_remote_llm_snippet``).

Run::

    python3 eval/b12_matrix_combiner.py --self-test
    python3 eval/b12_matrix_combiner.py \\
        --artifacts-dir /tmp/b12_official_artifacts \\
        --manifest /tmp/b12_official_matrix_final_manifest.json \\
        --out artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402

SCHEMA_VERSION = "b12-mechanism-matrix-aggregate-report-v0"
GENERATED_BY = "b12_matrix_combiner"
CLAIM_LEVEL = "derived_aggregate_of_b12_mechanism_decomposition_reports"
INPUT_B12_SCHEMA = "b12-mechanism-decomposition-report-v0"
BASELINE_FOR_DELTAS = "p25"
POLICY_UNDER_ANALYSIS = "balanced_v1"

ABLATION_VARIANT_UNDER_ANALYSIS = "A_full_balanced"
HYPOTHESES = (
    "H1_ambiguous_routing",
    "H2_llm_call_reduction",
    "H3_p25_fallback_sufficiency",
    "H4_model_specific",
)
# Metrics aggregated as record-weighted means of the per-run A-vs-{D,E,B}
# overall-mean deltas. ``robust_utility`` is aggregated separately as a
# record-weighted mean of the per-run top-level ``robust_utility`` scalar (A's
# overall robust utility); it is included "if present".
DELTA_METRICS = (
    "gold_span",
    "span_f0_5",
    "false_span",
    "primary_false_positive_rate",
    "model_calls",
)

# Public repo slice IDs and model-family names are already published by the
# per-run B12 reports under ``repos`` and ``model_families``; we re-publish only
# the public slice IDs that also appear in the manifest.
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

CELL_COUNT_TARGET = 32
EXPECTED_ANALYZABLE_CELL_COUNT = 28
EXPECTED_EXCLUDED_CELL_COUNT = 4
EXPECTED_EXCLUDED_REASON = "coverage_insufficient_no_remote_llm_snippet"

# Expected matrix shape, built from the official B11/B12 plan: 8 public repo
# slices x 4 public model families = 32 cells. The 4 ``ts_vite`` cells are
# coverage-insufficient (no remote LLM snippet even at max_tasks=24); the
# remaining 28 cells are the analyzable included set.
EXPECTED_REPOS = PUBLIC_REPO_SLICE_IDS
EXPECTED_MODEL_FAMILIES = PUBLIC_MODEL_FAMILY_NAMES
EXPECTED_EXCLUDED_CELLS = frozenset(
    (repo, model)
    for repo in ("ts_vite",)
    for model in EXPECTED_MODEL_FAMILIES
)
EXPECTED_INCLUDED_CELLS = frozenset(
    (repo, model)
    for repo in EXPECTED_REPOS
    for model in EXPECTED_MODEL_FAMILIES
) - EXPECTED_EXCLUDED_CELLS

DEFAULT_OUT = Path(
    "artifacts/b12_mechanism_decomposition/"
    "b12_matrix_aggregate_report.json"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "public_repo_slice_ids_in_artifact": True,
        "raw_repo_ids_in_artifact": False,
        "run_ids_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "runtime_clean_policy_supported": False,
        "new_provider_calls": 0,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "winner_declared": False,
        "derived_aggregate_rollup": True,
        "input_b12_schema_version": INPUT_B12_SCHEMA,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "ablation_variant_under_analysis": ABLATION_VARIANT_UNDER_ANALYSIS,
        "hypotheses": list(HYPOTHESES),
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the shared forbidden-key scan on the public output and record it."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b12-matrix public output would contain forbidden keys/values; "
            f"first violations: {violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Discovery + manifest reconciliation
# ---------------------------------------------------------------------------


def _extract_run_id(path: Path) -> str | None:
    """Extract the run_id from a discovered B12 report path.

    The canonical layout is
    ``<artifacts_dir>/<run_id>/real-provider-p21_llm_rich-<run_id>/artifacts/
    real_provider_ci/b12_mechanism_decomposition_report.json``. We look for a
    ``real-provider-p21_llm_rich-<run_id>`` path component and take the
    suffix as the run_id. Returns ``None`` if no such component is present.
    """
    for part in path.parts:
        marker = "real-provider-p21_llm_rich-"
        if part.startswith(marker):
            return part[len(marker):]
    return None


def _load_manifest(manifest_path: Path | None) -> dict[str, Any] | None:
    if manifest_path is None:
        return None
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _manifest_cell_key(repo_id: str, model_key: str) -> str:
    """Public slice key for a manifest cell (no run id)."""
    return f"{repo_id}::{model_key}"


def _discover_reports(
    artifacts_dir: Path,
) -> list[dict[str, Any]]:
    """Find every per-run B12 aggregate report under ``artifacts_dir``."""
    pattern = str(
        artifacts_dir / "**" / "b12_mechanism_decomposition_report.json"
    )
    found = sorted(glob.glob(pattern, recursive=True))
    discovered: list[dict[str, Any]] = []
    for f in found:
        p = Path(f)
        run_id = _extract_run_id(p)
        if run_id is None:
            raise ValueError(
                f"discovered B12 report does not match the expected "
                f"real-provider-p21_llm_rich-<run_id> layout: {p}"
            )
        discovered.append({"run_id": run_id, "path": str(p)})
    return discovered


def _validate_b12_report(report: dict[str, Any]) -> None:
    """Validate a per-run B12 aggregate report against the public contract."""
    if report.get("schema_version") != INPUT_B12_SCHEMA:
        raise ValueError(
            f"unexpected B12 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("B12 input must be aggregate_only_public_artifact=true")
    if report.get("promotion_ready") is not False:
        raise ValueError("B12 input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError("B12 input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError("B12 input must have evidencecore_semantics_changed=false")
    if report.get("replay_source") != "ci_ephemeral_records":
        raise ValueError(
            "B12 input must have replay_source=ci_ephemeral_records for a "
            "real official-matrix combine"
        )
    replay = report.get("replay_counts", {}) or {}
    complete = _as_int(replay.get("complete_records", 0))
    incomplete = _as_int(replay.get("incomplete_record_count", 0))
    if complete <= 0:
        raise ValueError("B12 input must have complete_records > 0")
    if incomplete != 0:
        raise ValueError(
            "B12 input must have incomplete_record_count == 0 for an included "
            "official-matrix cell"
        )
    violations = b6lite._walk_forbidden(report)
    if violations:
        raise ValueError(
            "B12 input contains forbidden public keys/values; first "
            f"violations: {violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Aggregation mechanics
# ---------------------------------------------------------------------------


def _weighted_mean(pairs: list[tuple[int, float]]) -> float:
    """Record-weighted mean over (weight, value) pairs (unrounded)."""
    total_w = sum(w for w, _ in pairs)
    if total_w <= 0:
        return 0.0
    return float(sum(w * v for w, v in pairs)) / float(total_w)


def _weighted_delta_dict(
    acc: dict[str, list[tuple[int, float]]],
) -> dict[str, float]:
    return {m: _round6(_weighted_mean(acc[m])) for m in DELTA_METRICS}


def _reconcile_manifest(
    discovered: list[dict[str, Any]],
    manifest: dict[str, Any] | None,
    *,
    self_test: bool,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]], dict[str, bool]]:
    """Reconcile discovered reports with the manifest and enforce matrix shape.

    Returns ``(included_cell_meta, excluded_cells_public, validation_flags)``
    where ``included_cell_meta`` maps ``run_id -> {repo_slice_id, model_family}``,
    ``excluded_cells_public`` is the sanitized exclusion list (no run ids), and
    ``validation_flags`` records which oracle checks passed.

    Validation (enforced whenever a manifest is provided):

    * Every manifest cell (included + excluded) has a public repo_id and
      model_key drawn from the expected universe.
    * No duplicate ``(repo, model)`` cell in the included list.
    * No duplicate ``(repo, model)`` cell in the excluded list.
    * No overlap between the included and excluded cell sets.
    * **Exclusion identity (always enforced):** every excluded cell must be
      one of ``EXPECTED_EXCLUDED_CELLS`` (the 4 ``ts_vite`` cells) and its
      reason/status must be ``EXPECTED_EXCLUDED_REASON``. Any other excluded
      repo/model or reason is rejected.
    * Included cells must all be in ``EXPECTED_INCLUDED_CELLS`` (i.e. none of
      the 4 ``ts_vite`` excluded cells may appear in the included set).
    * **Full 8x4 matrix shape (enforced on the real path, ``self_test=False``):**
      the included set must be exactly ``EXPECTED_INCLUDED_CELLS`` (28 cells)
      and the excluded set must be exactly ``EXPECTED_EXCLUDED_CELLS`` (4
      cells). The synthetic self-test fixture uses a 3+1 subset, so the exact
      set-equality check is gated on ``not self_test``.
    """
    included_cell_meta: dict[str, dict[str, str]] = {}
    excluded_cells_public: list[dict[str, str]] = []
    validation_flags = {
        "official_matrix_shape_validated": False,
        "exclusion_identity_validated": False,
        "manifest_report_labels_validated": False,  # set later in combine()
    }

    if manifest is None:
        # No manifest: only the self-test "no manifest" path is allowed to
        # reach here (and it raises earlier for the real path). Synthesize
        # unknown labels so the loop does not crash; full validation is off.
        for entry in discovered:
            included_cell_meta[entry["run_id"]] = {
                "repo_slice_id": "unknown",
                "model_family": "unknown",
            }
        return included_cell_meta, excluded_cells_public, validation_flags

    included = manifest.get("included") or []
    excluded = manifest.get("excluded") or []

    def _cell_pair(cell: dict[str, Any]) -> tuple[str, str]:
        repo_id = str(cell.get("repo_id"))
        model_key = str(cell.get("model_key"))
        if repo_id not in EXPECTED_REPOS:
            raise ValueError(
                f"manifest cell has non-public repo_id: {repo_id!r}"
            )
        if model_key not in EXPECTED_MODEL_FAMILIES:
            raise ValueError(
                f"manifest cell has non-public model_key: {model_key!r}"
            )
        return repo_id, model_key

    # Parse + universe-validate included cells.
    included_pairs: list[tuple[str, str]] = []
    run_id_to_meta: dict[str, dict[str, str]] = {}
    seen_included: set[tuple[str, str]] = set()
    for cell in included:
        repo_id, model_key = _cell_pair(cell)
        pair = (repo_id, model_key)
        if pair in seen_included:
            raise ValueError(
                f"duplicate included cell: {pair!r}"
            )
        seen_included.add(pair)
        included_pairs.append(pair)
        # An included cell must NOT be one of the expected excluded cells.
        if pair in EXPECTED_EXCLUDED_CELLS:
            raise ValueError(
                f"included cell {pair!r} is in the expected excluded set "
                "(ts_vite coverage-insufficient cells)"
            )
        run_id = str(cell.get("run_id"))
        run_id_to_meta[run_id] = {
            "repo_slice_id": repo_id,
            "model_family": model_key,
        }

    # Parse + universe-validate excluded cells + enforce exclusion identity.
    excluded_pairs: list[tuple[str, str]] = []
    seen_excluded: set[tuple[str, str]] = set()
    for cell in excluded:
        repo_id, model_key = _cell_pair(cell)
        pair = (repo_id, model_key)
        if pair in seen_excluded:
            raise ValueError(
                f"duplicate excluded cell: {pair!r}"
            )
        seen_excluded.add(pair)
        reason = str(cell.get("status") or cell.get("reason") or "")
        if reason != EXPECTED_EXCLUDED_REASON:
            raise ValueError(
                f"excluded cell {pair!r} has reason {reason!r}; expected "
                f"{EXPECTED_EXCLUDED_REASON!r}"
            )
        if pair not in EXPECTED_EXCLUDED_CELLS:
            raise ValueError(
                f"excluded cell {pair!r} is not one of the expected "
                "ts_vite coverage-insufficient cells; only ts_vite x "
                "{kimi,qwen,deepseek_flash,deepseek_pro} may be excluded"
            )
        excluded_pairs.append(pair)
        excluded_cells_public.append(
            {
                "repo_slice_id": repo_id,
                "model_family": model_key,
                "reason": reason,
            }
        )

    validation_flags["exclusion_identity_validated"] = True

    # No overlap between included and excluded.
    overlap = seen_included & seen_excluded
    if overlap:
        raise ValueError(
            f"included/excluded cell overlap: {sorted(overlap)!r}"
        )

    # Included cells must all be drawn from the expected included universe.
    bad_included = seen_included - EXPECTED_INCLUDED_CELLS
    if bad_included:
        raise ValueError(
            f"included cells outside the expected included universe: "
            f"{sorted(bad_included)!r}"
        )

    # Full 8x4 matrix shape: enforced on the real (non-self-test) path. The
    # synthetic self-test fixture is a 3+1 subset, so exact set equality is
    # only asserted for real combines.
    if not self_test:
        if seen_included != EXPECTED_INCLUDED_CELLS:
            missing = EXPECTED_INCLUDED_CELLS - seen_included
            extra = seen_included - EXPECTED_INCLUDED_CELLS
            raise ValueError(
                f"official-matrix included set does not match expected "
                f"{len(EXPECTED_INCLUDED_CELLS)} cells; "
                f"missing={sorted(missing)!r} extra={sorted(extra)!r}"
            )
        if seen_excluded != EXPECTED_EXCLUDED_CELLS:
            missing = EXPECTED_EXCLUDED_CELLS - seen_excluded
            extra = seen_excluded - EXPECTED_EXCLUDED_CELLS
            raise ValueError(
                f"official-matrix excluded set does not match expected "
                f"{len(EXPECTED_EXCLUDED_CELLS)} cells; "
                f"missing={sorted(missing)!r} extra={sorted(extra)!r}"
            )
        if len(seen_included) != EXPECTED_ANALYZABLE_CELL_COUNT:
            raise ValueError(
                f"expected {EXPECTED_ANALYZABLE_CELL_COUNT} analyzable cells, "
                f"got {len(seen_included)}"
            )
        if len(seen_excluded) != EXPECTED_EXCLUDED_CELL_COUNT:
            raise ValueError(
                f"expected {EXPECTED_EXCLUDED_CELL_COUNT} excluded cells, "
                f"got {len(seen_excluded)}"
            )
        validation_flags["official_matrix_shape_validated"] = True

    # Reconcile discovered reports: every discovered run_id must be in the
    # manifest included set; every manifest included run_id must have a
    # discovered report.
    for entry in discovered:
        rid = entry["run_id"]
        if rid not in run_id_to_meta:
            raise ValueError(
                f"discovered B12 report run_id {rid!r} is not in the "
                f"manifest included set"
            )
        included_cell_meta[rid] = run_id_to_meta[rid]

    discovered_run_ids = {e["run_id"] for e in discovered}
    missing_included = [
        rid for rid in run_id_to_meta if rid not in discovered_run_ids
    ]
    if missing_included:
        raise ValueError(
            f"manifest included {len(missing_included)} run_id(s) but no "
            f"matching B12 report was discovered: {sorted(missing_included)}"
        )

    return included_cell_meta, excluded_cells_public, validation_flags


def _cross_check_report_labels(
    b12: dict[str, Any],
    repo_slice: str,
    model_family: str,
) -> None:
    """Cross-check manifest cell labels against the per-run report's public
    preregistered universe (``repos`` / ``model_families``).

    The per-run B12 report carries the FULL preregistered ``repos`` and
    ``model_families`` lists (the 8x4 universe), not the cell's own identity.
    We therefore validate membership: the manifest's ``repo_slice`` must appear
    in the report's ``repos`` list, and the manifest's ``model_family`` must
    appear in the report's ``model_families`` list. A mismatch means the
    manifest is labelling a run with a repo/model the run's own report does not
    even acknowledge in its preregistered universe.
    """
    report_repos = b12.get("repos")
    report_models = b12.get("model_families")
    if isinstance(report_repos, list) and repo_slice not in report_repos:
        raise ValueError(
            f"manifest repo_slice {repo_slice!r} not in per-run report's "
            f"repos list {report_repos!r}"
        )
    if isinstance(report_models, list) and model_family not in report_models:
        raise ValueError(
            f"manifest model_family {model_family!r} not in per-run report's "
            f"model_families list {report_models!r}"
        )


def combine(
    artifacts_dir: Path,
    manifest_path: Path | None = None,
    self_test: bool = False,
) -> dict[str, Any]:
    """Combine the per-run B12 public aggregate reports into one rollup."""
    # Fail closed: a real (non-self-test) combine REQUIRES a manifest so the
    # official-matrix shape and exclusion identity can be enforced.
    if not self_test and manifest_path is None:
        raise ValueError(
            "--manifest is required for a real (non-self-test) combine; the "
            "official B12 matrix shape (28 analyzable + 4 ts_vite excluded) "
            "must be enforced"
        )

    discovered = _discover_reports(artifacts_dir)
    if not discovered:
        raise ValueError(
            f"no B12 aggregate reports discovered under {artifacts_dir}"
        )
    manifest = _load_manifest(manifest_path)
    included_cell_meta, excluded_cells_public, validation_flags = (
        _reconcile_manifest(
            discovered, manifest, self_test=self_test
        )
    )

    report = _base_report(self_test)
    report["source_artifacts_dir_public_note"] = (
        "already-downloaded aggregate-only public B12 mechanism decomposition "
        "reports; no raw records, paths, prompts, responses, snippets, or "
        "labels read"
    )

    integrity: dict[str, Any] = {
        "all_inputs_aggregate_only_public_artifact": True,
        "all_inputs_promotion_ready_false": True,
        "all_inputs_default_should_change_false": True,
        "all_inputs_evidencecore_semantics_changed_false": True,
        "all_inputs_replay_source_ci_ephemeral_records": True,
        "all_inputs_complete_records_positive": True,
        "all_inputs_incomplete_record_count_zero": True,
        "all_inputs_forbidden_public_scan_clean": True,
        "manifest_reconciled": manifest is not None,
        "official_matrix_shape_validated": validation_flags[
            "official_matrix_shape_validated"
        ],
        "exclusion_identity_validated": validation_flags[
            "exclusion_identity_validated"
        ],
        "manifest_report_labels_validated": False,  # set after the loop
    }

    record_count_total = 0
    verdict_counts: Counter = Counter()
    hypothesis_status_counts: dict[str, Counter] = {
        h: Counter() for h in HYPOTHESES
    }
    per_model_records: dict[str, int] = defaultdict(int)
    per_model_verdicts: dict[str, Counter] = defaultdict(Counter)
    per_repo_records: dict[str, int] = defaultdict(int)

    replay_totals: Counter = Counter()
    public_repo_slices_seen: set[str] = set()
    public_model_families_seen: set[str] = set()

    delta_acc: dict[str, dict[str, list[tuple[int, float]]]] = {
        "vs_d": {m: [] for m in DELTA_METRICS},
        "vs_e": {m: [] for m in DELTA_METRICS},
        "vs_b": {m: [] for m in DELTA_METRICS},
    }
    robust_utility_pairs: list[tuple[int, float]] = []

    labels_validated = True
    for entry in discovered:
        b12 = json.loads(Path(entry["path"]).read_text(encoding="utf-8"))
        _validate_b12_report(b12)

        meta = included_cell_meta.get(entry["run_id"], {})
        repo_slice = meta.get("repo_slice_id", "unknown")
        model_family = meta.get("model_family", "unknown")

        # Cross-check manifest labels against the per-run report's public
        # preregistered universe (repos / model_families).
        try:
            _cross_check_report_labels(b12, repo_slice, model_family)
        except ValueError:
            labels_validated = False
            raise

        public_repo_slices_seen.add(repo_slice)
        public_model_families_seen.add(model_family)

        replay = b12.get("replay_counts", {}) or {}
        complete = _as_int(replay.get("complete_records", 0))
        record_count_total += complete
        replay_totals["balanced_branch_count"] += _as_int(
            replay.get("balanced_branch_count", 0)
        )
        replay_totals["p25_llm_eligible_count"] += _as_int(
            replay.get("p25_llm_eligible_count", 0)
        )
        replay_totals["actual_call_avoided_count"] += _as_int(
            replay.get("actual_call_avoided_count", 0)
        )
        replay_totals["random_selected_count"] += _as_int(
            replay.get("random_selected_count", 0)
        )

        verdict = b12.get("verdict", "unknown")
        verdict_counts[verdict] += 1
        per_model_verdicts[model_family][verdict] += 1
        per_model_records[model_family] += complete
        per_repo_records[repo_slice] += complete

        for h in HYPOTHESES:
            blk = (b12.get("hypothesis_results") or {}).get(h, {}) or {}
            hypothesis_status_counts[h][str(blk.get("status", "unknown"))] += 1

        for m in DELTA_METRICS:
            delta_acc["vs_d"][m].append(
                (complete, _as_float(b12.get("variant_deltas_vs_d", {}).get(m, 0.0)))
            )
            delta_acc["vs_e"][m].append(
                (complete, _as_float(b12.get("variant_deltas_vs_e", {}).get(m, 0.0)))
            )
            delta_acc["vs_b"][m].append(
                (complete, _as_float(b12.get("variant_deltas_vs_b", {}).get(m, 0.0)))
            )
        robust_utility_pairs.append(
            (complete, _as_float(b12.get("robust_utility", 0.0)))
        )

    weighted_mean_deltas_vs_d = _weighted_delta_dict(delta_acc["vs_d"])
    weighted_mean_deltas_vs_e = _weighted_delta_dict(delta_acc["vs_e"])
    weighted_mean_deltas_vs_b = _weighted_delta_dict(delta_acc["vs_b"])
    weighted_mean_robust_utility_a = _round6(
        _weighted_mean(robust_utility_pairs)
    )

    integrity["manifest_report_labels_validated"] = labels_validated

    analyzable_cell_count = len(discovered)
    excluded_cell_count = len(excluded_cells_public)

    # Coverage exclusions summary by (repo slice, model family, reason), counts
    # only, no run ids.
    cov_counter: Counter = Counter()
    for cell in excluded_cells_public:
        cov_counter[
            (cell["repo_slice_id"], cell["model_family"], cell["reason"])
        ] += 1
    coverage_exclusions_summary = [
        {
            "repo_slice_id": repo,
            "model_family": model,
            "reason": reason,
            "count": count,
        }
        for (repo, model, reason), count in sorted(cov_counter.items())
    ]

    # Per-model summary (counts only; no run ids).
    per_model_summary: dict[str, Any] = {}
    for family in sorted(per_model_records):
        per_model_summary[family] = {
            "record_count": per_model_records[family],
            "cell_count": sum(
                1
                for e in discovered
                if included_cell_meta.get(e["run_id"], {}).get(
                    "model_family", "unknown"
                )
                == family
            ),
            "verdict_counts": dict(per_model_verdicts[family]),
        }
    per_repo_summary: dict[str, Any] = {
        repo: {"record_count": n} for repo, n in sorted(per_repo_records.items())
    }

    # -----------------------------------------------------------------------
    # Overall verdict logic (conservative)
    # -----------------------------------------------------------------------
    # Never emit a global `supported`. With 4 coverage exclusions the matrix
    # is not complete, so the verdict is `partial_with_coverage_exclusions`
    # unless a severe mechanical failure (a `failure`/`not_implemented`/
    # `insufficient_data` verdict on any included cell) is present, in which
    # case the verdict is `partial_with_mechanical_or_coverage_gaps`.
    non_partial_verdicts = {
        v for v in verdict_counts if v not in {"partial", "supported"}
    }
    severe_mechanical_failure = bool(non_partial_verdicts)

    coverage_excluded = excluded_cell_count > 0
    cells_below_target = analyzable_cell_count < CELL_COUNT_TARGET

    if severe_mechanical_failure:
        aggregate_verdict = "partial_with_mechanical_or_coverage_gaps"
        aggregate_verdict_reason = (
            "at least one included cell returned a non-partial/non-supported "
            f"verdict ({sorted(non_partial_verdicts)})"
        )
    elif coverage_excluded or cells_below_target:
        aggregate_verdict = "partial_with_coverage_exclusions"
        aggregate_verdict_reason = (
            f"{analyzable_cell_count}/{CELL_COUNT_TARGET} cells analyzable; "
            f"{excluded_cell_count} cell(s) excluded for coverage "
            "insufficiency (coverage_insufficient_no_remote_llm_snippet); "
            "not a global supported verdict"
        )
    else:
        # 32/32 analyzable, no coverage exclusions, all cells partial: still
        # not a global supported verdict (do not overclaim H1/H2/H3).
        aggregate_verdict = "partial"
        aggregate_verdict_reason = (
            "all cells analyzable but per-cell verdicts are partial; no "
            "global supported verdict by conservative B12 matrix policy"
        )

    # Mechanism summary (conservative interpretation; no overclaim).
    h1_supported_cells = hypothesis_status_counts["H1_ambiguous_routing"].get(
        "supported", 0
    )
    h2_supported_cells = hypothesis_status_counts["H2_llm_call_reduction"].get(
        "supported", 0
    )
    h3_supported_cells = hypothesis_status_counts[
        "H3_p25_fallback_sufficiency"
    ].get("supported", 0)
    h4_insufficient_cells = hypothesis_status_counts[
        "H4_model_specific"
    ].get("insufficient_data", 0)

    mechanism_summary = {
        "claim_boundary": (
            "B12 mechanism decomposition aggregate; NOT a promotion step, NOT "
            "a runtime-clean general algorithm claim, NOT a default change, "
            "NOT an EvidenceCore semantics change"
        ),
        "coverage_note": (
            f"{excluded_cell_count} ts_vite cell(s) excluded as "
            "coverage_insufficient_no_remote_llm_snippet; these failed the "
            "old P21 privacy gate (no remote LLM snippets even at "
            "max_tasks=24) and are NOT B12 mechanism failures. Mechanism "
            "claims are scoped to the analyzable cells only."
        ),
        "h1_interpretation": (
            f"ambiguous-routing H1 supported on {h1_supported_cells}/"
            f"{analyzable_cell_count} analyzable cells; mixed support — do "
            "NOT read as a global H1 supported verdict"
        ),
        "h2_interpretation": (
            f"llm-call-reduction H2 supported on {h2_supported_cells}/"
            f"{analyzable_cell_count} analyzable cells; mixed support — "
            "single frozen E seed per cell, causal attribution remains limited"
        ),
        "h3_interpretation": (
            f"p25-fallback-sufficiency H3 supported on {h3_supported_cells}/"
            f"{analyzable_cell_count} analyzable cells (all analyzable cells) "
            "— consistent with primary-quality parity vs D, but NOT a global "
            "supported verdict because of the coverage exclusions"
        ),
        "h4_interpretation": (
            f"model-specific H4 insufficient_data on {h4_insufficient_cells}/"
            f"{analyzable_cell_count} analyzable cells (every cell is a "
            "single-model-family slice, so H4 needs multi-model aggregation "
            "across cells; H4 insufficient_data does NOT block H1-H3)"
        ),
        "weighted_a_vs_d_summary": {
            "model_calls_delta": weighted_mean_deltas_vs_d["model_calls"],
            "false_span_delta": weighted_mean_deltas_vs_d["false_span"],
            "primary_false_positive_rate_delta": (
                weighted_mean_deltas_vs_d["primary_false_positive_rate"]
            ),
            "gold_span_delta": weighted_mean_deltas_vs_d["gold_span"],
            "span_f0_5_delta": weighted_mean_deltas_vs_d["span_f0_5"],
        },
        "weighted_mean_robust_utility_a": weighted_mean_robust_utility_a,
        "recommended_next_step": (
            "B13 distributionally robust policy search WITH CAUTION (B13 "
            "must not be treated as authorized by a B12 supported verdict); "
            "or a future B12 matrix rerun that closes the ts_vite coverage gap"
        ),
    }

    report.update(
        {
            "status": "ok" if not self_test else "self_test_only",
            "cell_count_target": CELL_COUNT_TARGET,
            "analyzable_cell_count": analyzable_cell_count,
            "excluded_cell_count": excluded_cell_count,
            "run_count": len(discovered),
            "record_count_total": record_count_total,
            "public_repo_slice_count": len(public_repo_slices_seen),
            "public_repo_slice_ids": sorted(public_repo_slices_seen),
            "public_model_family_count": len(public_model_families_seen),
            "public_model_family_names": sorted(public_model_families_seen),
            "metric_names": list(DELTA_METRICS),
            "verdict_counts": dict(verdict_counts),
            "hypothesis_status_counts": {
                h: dict(hypothesis_status_counts[h]) for h in HYPOTHESES
            },
            "weighted_mean_deltas_vs_d": weighted_mean_deltas_vs_d,
            "weighted_mean_deltas_vs_e": weighted_mean_deltas_vs_e,
            "weighted_mean_deltas_vs_b": weighted_mean_deltas_vs_b,
            "weighted_mean_robust_utility_a": weighted_mean_robust_utility_a,
            "replay_count_totals": dict(replay_totals),
            "coverage_exclusions": excluded_cells_public,
            "coverage_exclusions_summary": coverage_exclusions_summary,
            "per_model_family": per_model_summary,
            "per_repo_slice": per_repo_summary,
            "aggregate_verdict": aggregate_verdict,
            "aggregate_verdict_reason": aggregate_verdict_reason,
            "mechanism_summary": mechanism_summary,
            "integrity": integrity,
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "evidencecore_semantics_changed_false": True,
                "policy_search_performed_false": True,
                "runtime_clean_policy_supported_false": True,
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
                "runtime_clean_general_algorithm_claimed": False,
                "signal_strength": (
                    "mechanism_decomposition_partial_with_coverage_exclusions"
                ),
                "recommended_next_step": "B13_with_caution_or_ts_vite_rerun",
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _synthetic_b12_report(
    run_id: str,
    complete_records: int,
    verdict: str,
    *,
    a_vs_d: dict[str, float],
    a_vs_e: dict[str, float],
    a_vs_b: dict[str, float],
    robust_utility: float,
    h1_status: str = "refuted",
    h2_status: str = "refuted",
    h3_status: str = "supported",
    h4_status: str = "insufficient_data",
) -> dict[str, Any]:
    """Build a minimal synthetic per-run B12 aggregate report for self-test.

    Only the fields read by the combiner are populated; the report is still a
    valid aggregate-only public artifact under the combiner's own contract
    (it is NOT a real per-run B12 report and is only ever materialized inside a
    temporary self-test directory).
    """
    return {
        "schema_version": INPUT_B12_SCHEMA,
        "generated_by": "b12_mechanism_decomposition",
        "generated_at": "2026-06-19T00:00:00+00:00",
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "replay_source": "ci_ephemeral_records",
        "verdict": verdict,
        "replay_counts": {
            "complete_records": complete_records,
            "incomplete_record_count": 0,
            "total_records": complete_records,
            "balanced_branch_count": 4,
            "p25_llm_eligible_count": 10,
            "actual_call_avoided_count": 4,
            "random_selected_count": 4,
            "missing_required_outcome_count": 0,
        },
        "variant_deltas_vs_d": dict(a_vs_d),
        "variant_deltas_vs_e": dict(a_vs_e),
        "variant_deltas_vs_b": dict(a_vs_b),
        "robust_utility": robust_utility,
        "hypothesis_results": {
            "H1_ambiguous_routing": {"status": h1_status, "supported": h1_status == "supported"},
            "H2_llm_call_reduction": {"status": h2_status, "supported": h2_status == "supported"},
            "H3_p25_fallback_sufficiency": {"status": h3_status, "supported": h3_status == "supported"},
            "H4_model_specific": {"status": h4_status, "supported": False},
        },
        # Public slice labels only (already public); no run id is referenced
        # inside the per-run report body.
        "repos": ["py_fastapi"],
        "model_families": ["kimi"],
    }


def _build_self_test_artifacts(root: Path) -> tuple[Path, Path]:
    """Materialize a tiny synthetic B12 matrix tree (3 cells + 1 exclusion)."""
    artifacts = root / "artifacts"

    # 3 analyzable cells, each with 12 complete records. Use distinct public
    # repo/model slices and deterministic deltas so the self-test can assert
    # weighted means exactly.
    cells = [
        # (run_id, repo, model, complete, verdict,
        #  a_vs_d, a_vs_e, a_vs_b, robust, h1, h2, h3, h4)
        (
            "90000000001", "py_fastapi", "kimi", 12, "partial",
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.10,
             "primary_false_positive_rate": -0.02, "model_calls": -0.5},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.20,
             "primary_false_positive_rate": -0.01, "model_calls": 0.0},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.05,
             "primary_false_positive_rate": -0.01, "model_calls": 0.0},
            -0.01,
            "refuted", "refuted", "supported", "insufficient_data",
        ),
        (
            "90000000002", "py_pytest", "qwen", 12, "partial",
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.05,
             "primary_false_positive_rate": -0.01, "model_calls": -0.25},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.10,
             "primary_false_positive_rate": -0.005, "model_calls": 0.0},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.02,
             "primary_false_positive_rate": -0.005, "model_calls": 0.0},
            0.02,
            "supported", "refuted", "supported", "insufficient_data",
        ),
        (
            "90000000003", "ts_hono", "deepseek_pro", 12, "partial",
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.08,
             "primary_false_positive_rate": -0.015, "model_calls": -0.25},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.15,
             "primary_false_positive_rate": -0.005, "model_calls": 0.0},
            {"gold_span": 0.0, "span_f0_5": 0.0, "false_span": -0.04,
             "primary_false_positive_rate": -0.005, "model_calls": 0.0},
            0.04,
            "refuted", "supported", "supported", "insufficient_data",
        ),
    ]
    for (
        run_id, repo, model, complete, verdict,
        a_vs_d, a_vs_e, a_vs_b, robust, h1, h2, h3, h4,
    ) in cells:
        run_top = run_id
        run_dir = f"real-provider-p21_llm_rich-{run_id}"
        ci_dir = artifacts / run_top / run_dir / "artifacts" / "real_provider_ci"
        ci_dir.mkdir(parents=True, exist_ok=True)
        report = _synthetic_b12_report(
            run_id, complete, verdict,
            a_vs_d=a_vs_d, a_vs_e=a_vs_e, a_vs_b=a_vs_b,
            robust_utility=robust,
            h1_status=h1, h2_status=h2, h3_status=h3, h4_status=h4,
        )
        report["repos"] = [repo]
        report["model_families"] = [model]
        (ci_dir / "b12_mechanism_decomposition_report.json").write_text(
            json.dumps(report, sort_keys=True), encoding="utf-8"
        )

    # Manifest: 3 included + 1 excluded.
    manifest = {
        "included": [
            {"repo_id": "py_fastapi", "model_key": "kimi",
             "llm_model": "[mk]Kimi-K2.7-Code", "llm_output_mode": "tool_call",
             "run_id": int(c[0]), "source": "self_test"}
            for c in [cells[0]]
        ] + [
            {"repo_id": "py_pytest", "model_key": "qwen",
             "llm_model": "[mk]Qwen3.6-27B", "llm_output_mode": "json_schema_strict",
             "run_id": int(c[0]), "source": "self_test"}
            for c in [cells[1]]
        ] + [
            {"repo_id": "ts_hono", "model_key": "deepseek_pro",
             "llm_model": "[mk]DeepSeek-V4-Pro", "llm_output_mode": "json_schema_strict",
             "run_id": int(c[0]), "source": "self_test"}
            for c in [cells[2]]
        ],
        "excluded": [
            {"repo_id": "ts_vite", "model_key": "kimi",
             "llm_model": "[mk]Kimi-K2.7-Code", "llm_output_mode": "tool_call",
             "run_id": 90000000004, "source": "self_test",
             "status": EXPECTED_EXCLUDED_REASON,
             "failed_run_ids": [90000000004]},
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return artifacts, manifest_path


def _self_test_happy_path() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        report = combine(artifacts, manifest_path=manifest, self_test=True)

    assert report["status"] == "self_test_only", report["status"]
    assert report["schema_version"] == SCHEMA_VERSION, report["schema_version"]
    assert report["analyzable_cell_count"] == 3, report["analyzable_cell_count"]
    assert report["excluded_cell_count"] == 1, report["excluded_cell_count"]
    assert report["cell_count_target"] == 32, report["cell_count_target"]
    assert report["run_count"] == 3, report["run_count"]
    assert report["record_count_total"] == 36, report["record_count_total"]
    assert report["verdict_counts"] == {"partial": 3}, report["verdict_counts"]
    assert report["hypothesis_status_counts"]["H1_ambiguous_routing"] == {
        "supported": 1, "refuted": 2
    }, report["hypothesis_status_counts"]["H1_ambiguous_routing"]
    assert report["hypothesis_status_counts"]["H2_llm_call_reduction"] == {
        "supported": 1, "refuted": 2
    }, report["hypothesis_status_counts"]["H2_llm_call_reduction"]
    assert report["hypothesis_status_counts"]["H3_p25_fallback_sufficiency"] == {
        "supported": 3
    }, report["hypothesis_status_counts"]["H3_p25_fallback_sufficiency"]
    assert report["hypothesis_status_counts"]["H4_model_specific"] == {
        "insufficient_data": 3
    }, report["hypothesis_status_counts"]["H4_model_specific"]
    assert report["replay_count_totals"] == {
        "balanced_branch_count": 12,
        "p25_llm_eligible_count": 30,
        "actual_call_avoided_count": 12,
        "random_selected_count": 12,
    }, report["replay_count_totals"]

    # Weighted A vs D false_span: each cell 12 records, equal weight.
    # (-0.10 + -0.05 + -0.08) / 3 = -0.076667
    d = report["weighted_mean_deltas_vs_d"]
    assert d["false_span"] == -0.076667, d
    assert d["model_calls"] == round((-0.5 + -0.25 + -0.25) / 3, 6), d
    # Robust utility weighted mean: (-0.01 + 0.02 + 0.04) / 3
    assert report["weighted_mean_robust_utility_a"] == round(
        (-0.01 + 0.02 + 0.04) / 3, 6
    ), report["weighted_mean_robust_utility_a"]

    # Coverage exclusion sanitized: no run id, public slice only.
    cov = report["coverage_exclusions"]
    assert len(cov) == 1, cov
    assert cov[0] == {
        "repo_slice_id": "ts_vite",
        "model_family": "kimi",
        "reason": EXPECTED_EXCLUDED_REASON,
    }, cov
    assert report["coverage_exclusions_summary"][0]["count"] == 1

    # Aggregate verdict: coverage exclusions present -> partial_with_coverage_exclusions
    assert (
        report["aggregate_verdict"] == "partial_with_coverage_exclusions"
    ), report["aggregate_verdict"]
    # No promotion / default / runtime-clean / semantics claims.
    assert report["promotion_ready"] is False
    assert report["default_should_change"] is False
    assert report["evidencecore_semantics_changed"] is False
    assert report["policy_search_performed"] is False
    assert report["runtime_clean_policy_supported"] is False
    assert report["new_provider_calls"] == 0
    assert report["candidate_not_fact"] is True
    # Forbidden scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # Manifest reconciled.
    assert report["integrity"]["manifest_reconciled"] is True
    # Exclusion identity always validated (even on self-test).
    assert report["integrity"]["exclusion_identity_validated"] is True
    # Manifest/report label cross-check passed.
    assert report["integrity"]["manifest_report_labels_validated"] is True
    # Full 8x4 matrix shape is NOT validated on the self-test path (3+1
    # synthetic fixture, not 28+4); it IS validated on the real path.
    assert report["integrity"]["official_matrix_shape_validated"] is False
    # Public slice IDs emitted; no run IDs.
    assert report["public_repo_slice_ids_in_artifact"] is True
    assert report["run_ids_in_artifact"] is False
    # Excluded slice appears in coverage_exclusions (not in public_repo_slice_ids).
    assert report["coverage_exclusions"][0]["repo_slice_id"] == "ts_vite"
    assert "py_fastapi" in report["public_repo_slice_ids"]
    print("self-test happy path: ok")
    return report


def _self_test_forbidden_scan_catches_bad_input() -> None:
    """Inject a forbidden key into a per-run report and confirm rejection."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        # Overwrite one report with a forbidden `repo_id` key.
        bad_path = (
            artifacts / "90000000001" / "real-provider-p21_llm_rich-90000000001"
            / "artifacts" / "real_provider_ci"
            / "b12_mechanism_decomposition_report.json"
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        bad["repo_id"] = "py_fastapi"  # forbidden public key
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "forbidden" in str(exc).lower(), exc
            print("self-test forbidden-scan catches bad input: ok")
            return
    raise AssertionError("combine should have rejected a forbidden input key")


def _self_test_no_inputs_blocks() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            combine(Path(tmp), self_test=True)
        except ValueError as exc:
            assert "no B12 aggregate reports discovered" in str(exc), exc
            print("self-test no-inputs block: ok")
            return
    raise AssertionError("combine should have raised on empty input")


def _self_test_manifest_run_id_mismatch_blocks() -> None:
    """A discovered run_id not in manifest included must raise."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        # Drop one included cell from the manifest so a discovered run is now
        # unaccounted for.
        m = json.loads(manifest.read_text(encoding="utf-8"))
        m["included"] = m["included"][:-1]
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "not in the manifest included set" in str(exc), exc
            print("self-test manifest run_id mismatch block: ok")
            return
    raise AssertionError("combine should have raised on manifest mismatch")


def _self_test_missing_manifest_blocks_real_path() -> None:
    """A real (non-self-test) combine without --manifest must fail closed."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, _ = _build_self_test_artifacts(root)
        try:
            combine(artifacts, manifest_path=None, self_test=False)
        except ValueError as exc:
            assert "--manifest is required" in str(exc), exc
            print("self-test missing-manifest real-path block: ok")
            return
    raise AssertionError("combine should have failed closed without --manifest")


def _self_test_wrong_excluded_repo_blocks() -> None:
    """An excluded cell with a non-ts_vite repo must be rejected."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        m = json.loads(manifest.read_text(encoding="utf-8"))
        # Mutate the excluded cell repo from ts_vite to ts_hono (which is NOT
        # in EXPECTED_EXCLUDED_CELLS).
        m["excluded"][0]["repo_id"] = "ts_hono"
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "not one of the expected" in str(exc), exc
            print("self-test wrong-excluded-repo block: ok")
            return
    raise AssertionError("combine should have rejected a wrong excluded repo")


def _self_test_wrong_excluded_reason_blocks() -> None:
    """An excluded cell with a wrong reason/status must be rejected."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        m = json.loads(manifest.read_text(encoding="utf-8"))
        m["excluded"][0]["status"] = "some_other_reason"
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "has reason" in str(exc), exc
            print("self-test wrong-excluded-reason block: ok")
            return
    raise AssertionError("combine should have rejected a wrong excluded reason")


def _self_test_duplicate_included_cell_blocks() -> None:
    """A duplicate included (repo, model) cell must be rejected."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        m = json.loads(manifest.read_text(encoding="utf-8"))
        # Duplicate the first included cell with a fresh run_id.
        dup = dict(m["included"][0])
        dup["run_id"] = 99900000099
        m["included"].append(dup)
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "duplicate included cell" in str(exc), exc
            print("self-test duplicate-included-cell block: ok")
            return
    raise AssertionError("combine should have rejected a duplicate included cell")


def _self_test_label_mismatch_blocks() -> None:
    """A per-run report whose repos/model_families lists omit the manifest's
    cell labels must be rejected."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        # Overwrite one report's `repos` list to omit py_fastapi (which the
        # manifest labels for run 90000000001).
        bad_path = (
            artifacts / "90000000001" / "real-provider-p21_llm_rich-90000000001"
            / "artifacts" / "real_provider_ci"
            / "b12_mechanism_decomposition_report.json"
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        bad["repos"] = ["py_pytest", "ts_hono"]  # py_fastapi absent
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "not in per-run report's repos list" in str(exc), exc
            print("self-test manifest/report label mismatch block: ok")
            return
    raise AssertionError("combine should have rejected a label mismatch")


def run_self_tests() -> dict[str, Any]:
    _self_test_happy_path()
    _self_test_forbidden_scan_catches_bad_input()
    _self_test_no_inputs_blocks()
    _self_test_manifest_run_id_mismatch_blocks()
    _self_test_missing_manifest_blocks_real_path()
    _self_test_wrong_excluded_repo_blocks()
    _self_test_wrong_excluded_reason_blocks()
    _self_test_duplicate_included_cell_blocks()
    _self_test_label_mismatch_blocks()
    return {"self_test_passed": True}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run synthetic-fixture self-test (no real artifact reads).",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Directory of already-downloaded public B12 aggregate reports. "
        "Required for a real combine (ignored by --self-test).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Final manifest JSON with `included` and `excluded` cell lists. "
        "REQUIRED for a real (non-self-test) combine so the official B12 "
        "matrix shape (28 analyzable + 4 ts_vite excluded) and exclusion "
        "identity can be enforced. Optional only for --self-test.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output aggregate report path (default: {DEFAULT_OUT}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
        return 0
    if args.artifacts_dir is None:
        raise SystemExit(
            "--artifacts-dir is required for a real combine (or use --self-test)"
        )
    if args.manifest is None:
        raise SystemExit(
            "--manifest is required for a real combine (the official B12 "
            "matrix shape must be enforced); or use --self-test"
        )
    report = combine(
        args.artifacts_dir, manifest_path=args.manifest, self_test=False
    )
    _write_json(args.out, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim_level": report["claim_level"],
                "schema_version": report["schema_version"],
                "cell_count_target": report["cell_count_target"],
                "analyzable_cell_count": report["analyzable_cell_count"],
                "excluded_cell_count": report["excluded_cell_count"],
                "run_count": report["run_count"],
                "record_count_total": report["record_count_total"],
                "verdict_counts": report["verdict_counts"],
                "hypothesis_status_counts": report["hypothesis_status_counts"],
                "aggregate_verdict": report["aggregate_verdict"],
                "promotion_ready": report["promotion_ready"],
                "default_should_change": report["default_should_change"],
                "runtime_clean_policy_supported": (
                    report["runtime_clean_policy_supported"]
                ),
                "evidencecore_semantics_changed": (
                    report["evidencecore_semantics_changed"]
                ),
                "new_provider_calls": report["new_provider_calls"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
