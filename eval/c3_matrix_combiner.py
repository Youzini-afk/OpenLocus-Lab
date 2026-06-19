#!/usr/bin/env python3
"""C3 Budgeted Evidence Acquisition official matrix aggregate combiner.

This is a **bounded derived aggregate rollup**. It combines the already-
downloaded public ``c3-budgeted-evidence-acquisition-report-v0`` aggregate
JSON artifacts produced by a finished C3 official matrix run (28 analyzable
cells + 4 ``ts_vite`` coverage exclusions) into a single derived aggregate.

It performs:

* **no** per-task / per-repo / per-candidate / source-record reads (it reads
  only the already-published per-run C3 aggregate reports);
* **no** provider calls (``remote_calls_by_combiner == 0``,
  ``model_calls_by_combiner == 0``);
* **no** policy search, rule generation, retuning, or winner selection;
* **no** promotion / default / runtime-clean / EvidenceCore-semantics claim;
* **no** per-cell winner freeze. The diagnostic rank is ordering-only and
  ``candidate_selected=false`` for every policy; selection is deferred to a
  future preregistered matrix.

The only inputs are the already-downloaded aggregate-only public C3 reports
under an artifacts directory, plus a flat-list manifest of the 32 planned
cells (4 ``ts_vite`` cells are marked
``status=planned_exclusion_coverage_insufficient`` with no ``run_id`` and are
included as coverage exclusions).

The output preserves the ``aggregate_only_public_artifact`` contract: no run
IDs, task IDs, raw repo IDs, paths, spans, content hashes, prompts, responses,
snippets, provider URLs, or provider keys. It MAY publish public repo slice
IDs (e.g. ``py_fastapi``) and public model-family names (e.g. ``kimi``,
``deepseek_pro``) — but only as **public slice IDs derived from the
manifest**, never as run IDs. Counts by (public repo slice, model family) are
emitted for the coverage exclusions, with no run IDs.

This is a **diagnostic-rank-only aggregate**, NOT a promotion step. No
winner is declared; no candidate is selected; no default is changed.

Run::

    python3 eval/c3_matrix_combiner.py --self-test
    python3 eval/c3_matrix_combiner.py \\
        --artifacts-dir /tmp/c3_official_artifacts \\
        --manifest /tmp/c3_official_matrix_manifest.json \\
        --out artifacts/c3_budgeted_evidence_acquisition/c3_matrix_aggregate_report.json
"""

from __future__ import annotations

import argparse
import glob
import hashlib
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
import c3_budgeted_evidence_acquisition as c3bea  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / framing constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c3-budgeted-evidence-acquisition-matrix-report-v0"
GENERATED_BY = "c3_matrix_combiner"
CLAIM_LEVEL = "budgeted_matrix_aggregate_public_v0"
INPUT_C3_SCHEMA = "c3-budgeted-evidence-acquisition-report-v0"
INPUT_C3_GENERATED_BY = "c3_budgeted_evidence_acquisition"

# Exact frozen candidate policy ids and action set, copied from the C3 spec
# (eval/c3_budgeted_evidence_acquisition.py CANDIDATE_POLICY_IDS /
# ALLOWED_CANDIDATE_ACTIONS). The combiner asserts every per-cell report
# matches these byte-for-byte.
CANDIDATE_POLICY_IDS: tuple[str, ...] = (
    "local_only",
    "weak_on_noise_else_local",
    "span_narrow_on_anchor_else_local",
    "filter_on_noise_else_span_narrow_on_anchor_else_local",
    "abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local",
    "weak_on_disagreement_span_on_anchor_else_local",
)
ALLOWED_CANDIDATE_ACTIONS: tuple[str, ...] = (
    "candidate_baseline",
    "weak_candidate_only",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
)
ALLOWED_RUNTIME_FEATURES: tuple[str, ...] = (
    "query_noise",
    "candidate_support_exists",
    "local_anchor",
    "rrf_backed_by_anchor",
    "candidate_count",
    "symbol_regex_agree_file",
    "symbol_regex_agree_span",
    "rrf_anchor_agree_file",
    "rrf_anchor_agree_span",
    "dense_support_present",
)
METRIC_NAMES: tuple[str, ...] = (
    "span_f0_5",
    "added_gold_span",
    "added_false_span",
    "primary_false_positive_rate",
    "model_calls",
    "utility",
)
BASELINES: tuple[str, ...] = ("p25", "balanced_v1")

# Frozen objective constants (mirrors c3_budgeted_evidence_acquisition.py).
# The combiner only asserts these IF the per-cell report carries an
# ``objective_constants`` block; absence is not treated as a validation
# failure (older reports may omit it), but presence+inconsistency is.
OBJECTIVE_CONSTANTS = {
    "lambda": 1.0,
    "mu": 1.0,
    "cost_weight": 0.1,
}
# Tolerance for ``abs(sum - mean * n_records)`` rounding checks.
_SUM_MEAN_TOL = 1e-3

# Public repo slice IDs and model-family names are already public per the
# B11/B12 aggregate convention (they are emitted as ``repo_slice_id``, not
# the raw forbidden ``repo_id`` key). We re-publish only the public slice IDs
# that appear in the manifest.
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
EXCLUSION_STATUS = "planned_exclusion_coverage_insufficient"

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
    "artifacts/c3_budgeted_evidence_acquisition/"
    "c3_matrix_aggregate_report.json"
)

_REPORT_FILENAME = "c3_budgeted_evidence_acquisition_report.json"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


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


def _weighted_mean(pairs: list[tuple[int, float]]) -> float:
    total_w = sum(w for w, _ in pairs)
    if total_w <= 0:
        return 0.0
    return float(sum(w * v for w, v in pairs)) / float(total_w)


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "aggregate_only_public_artifact": True,
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
        "winner_declared": False,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "derived_aggregate_rollup": True,
        "input_c3_schema_version": INPUT_C3_SCHEMA,
        "input_c3_generated_by": INPUT_C3_GENERATED_BY,
        "candidate_policy_ids": list(CANDIDATE_POLICY_IDS),
        "action_set": list(ALLOWED_CANDIDATE_ACTIONS),
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "metric_names": list(METRIC_NAMES),
        "baselines": list(BASELINES),
        "remote_calls_by_combiner": 0,
        "model_calls_by_combiner": 0,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the FULL C3 forbidden-field scan on the public output and record it.

    Uses ``c3bea._recursive_key_scan`` (C3's own scanner with C3's full
    forbidden-key contract: ``run_id``, ``route_features``, ``task_bucket``,
    etc.), NOT B6's weaker scanner. The C3 scanner's ``/`` value-pattern is
    safe here because the aggregate uses ``module::symbol``-style provenance
    and public ``repo_slice_id`` / ``model_family`` strings, never raw
    filesystem paths.
    """
    violations = c3bea._recursive_key_scan(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "c3-matrix public output would contain forbidden keys/values "
            "(C3 scanner); first violations: "
            f"{violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Discovery + manifest reconciliation
# ---------------------------------------------------------------------------


def _extract_run_id(path: Path) -> str | None:
    """Extract the run_id from a discovered C3 report path.

    Canonical layout:
    ``<artifacts_dir>/<run_id>/real-provider-p21_llm_rich-<run_id>/artifacts/
    real_provider_ci/c3_budgeted_evidence_acquisition_report.json``
    """
    for part in path.parts:
        marker = "real-provider-p21_llm_rich-"
        if part.startswith(marker):
            return part[len(marker):]
    return None


def _load_manifest(manifest_path: Path | None) -> list[dict[str, Any]] | None:
    if manifest_path is None:
        return None
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            "C3 manifest must be a flat JSON list of cell entries "
            "(included + excluded)"
        )
    return data


def _discover_reports(
    artifacts_dir: Path,
) -> list[dict[str, Any]]:
    """Find every per-run C3 aggregate report under ``artifacts_dir``."""
    pattern = str(artifacts_dir / "**" / _REPORT_FILENAME)
    found = sorted(glob.glob(pattern, recursive=True))
    discovered: list[dict[str, Any]] = []
    for f in found:
        p = Path(f)
        run_id = _extract_run_id(p)
        if run_id is None:
            raise ValueError(
                f"discovered C3 report does not match the expected "
                f"real-provider-p21_llm_rich-<run_id> layout: {p}"
            )
        discovered.append({"run_id": run_id, "path": str(p)})
    return discovered


def _cell_pair(cell: dict[str, Any]) -> tuple[str, str]:
    repo_id = str(cell.get("repo_id"))
    model_key = str(cell.get("model_key"))
    if repo_id not in EXPECTED_REPOS:
        raise ValueError(f"manifest cell has non-public repo_id: {repo_id!r}")
    if model_key not in EXPECTED_MODEL_FAMILIES:
        raise ValueError(
            f"manifest cell has non-public model_key: {model_key!r}"
        )
    return repo_id, model_key


def _reconcile_manifest(
    discovered: list[dict[str, Any]],
    manifest: list[dict[str, Any]] | None,
    *,
    self_test: bool,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]], dict[str, bool]]:
    """Reconcile discovered reports with the flat-list manifest.

    The manifest is a flat list of 32 cell entries. An entry is an
    **exclusion** iff ``status == planned_exclusion_coverage_insufficient``
    (with ``run_id`` null); every other entry is an **included** cell with a
    real ``run_id``.

    Returns ``(included_cell_meta, excluded_cells_public, validation_flags)``
    where ``included_cell_meta`` maps ``run_id -> {repo_slice_id,
    model_family}``, ``excluded_cells_public`` is the sanitized exclusion list
    (no run ids), and ``validation_flags`` records oracle checks.

    Validation (enforced whenever a manifest is provided):

    * Every manifest cell (included + excluded) has a public repo_id and
      model_key drawn from the expected universe.
    * No duplicate ``(repo, model)`` cell in the included list.
    * No duplicate ``(repo, model)`` cell in the excluded list.
    * No duplicate ``run_id`` in the manifest included set.
    * No duplicate discovered report run_ids.
    * No overlap between the included and excluded cell sets.
    * Exclusion entries MUST have a null ``run_id`` (exclusions carry no run).
    * **Exclusion identity (always enforced):** every excluded cell must be
      one of ``EXPECTED_EXCLUDED_CELLS`` (the 4 ``ts_vite`` cells).
    * Included cells must all be in ``EXPECTED_INCLUDED_CELLS``.
    * **Full 8x4 matrix shape (enforced on the real path, ``self_test=False``):**
      the included set must be exactly the 28 ``EXPECTED_INCLUDED_CELLS`` and
      the excluded set exactly the 4 ``EXPECTED_EXCLUDED_CELLS``.
    """
    included_cell_meta: dict[str, dict[str, str]] = {}
    excluded_cells_public: list[dict[str, str]] = []
    validation_flags = {
        "official_matrix_shape_validated": False,
        "exclusion_identity_validated": False,
        "manifest_shape_and_exclusion_identity_validated": False,
        # The combiner does NOT validate per-cell report labels (repo/model
        # identity) against the per-cell report body; it only validates the
        # manifest shape + per-cell report contract. This flag is always
        # False and is emitted for transparency.
        "manifest_report_labels_validated": False,
    }

    if manifest is None:
        for entry in discovered:
            included_cell_meta[entry["run_id"]] = {
                "repo_slice_id": "unknown",
                "model_family": "unknown",
            }
        return included_cell_meta, excluded_cells_public, validation_flags

    seen_included: set[tuple[str, str]] = set()
    seen_included_run_ids: set[str] = set()
    run_id_to_meta: dict[str, dict[str, str]] = {}
    for cell in manifest:
        status = str(cell.get("status") or "")
        if status == EXCLUSION_STATUS:
            continue
        repo_id, model_key = _cell_pair(cell)
        pair = (repo_id, model_key)
        if pair in seen_included:
            raise ValueError(f"duplicate included cell: {pair!r}")
        seen_included.add(pair)
        if pair in EXPECTED_EXCLUDED_CELLS:
            raise ValueError(
                f"included cell {pair!r} is in the expected excluded set "
                "(ts_vite coverage-insufficient cells)"
            )
        run_id_raw = cell.get("run_id")
        if run_id_raw is None:
            raise ValueError(
                f"included cell {pair!r} has null run_id; only exclusions "
                "may omit run_id"
            )
        run_id = str(run_id_raw)
        if run_id in seen_included_run_ids:
            raise ValueError(
                f"duplicate included run_id {run_id!r} in manifest"
            )
        seen_included_run_ids.add(run_id)
        run_id_to_meta[run_id] = {
            "repo_slice_id": repo_id,
            "model_family": model_key,
        }

    seen_excluded: set[tuple[str, str]] = set()
    for cell in manifest:
        status = str(cell.get("status") or "")
        if status != EXCLUSION_STATUS:
            continue
        repo_id, model_key = _cell_pair(cell)
        pair = (repo_id, model_key)
        if pair in seen_excluded:
            raise ValueError(f"duplicate excluded cell: {pair!r}")
        seen_excluded.add(pair)
        # Exclusion entries MUST have a null run_id (exclusions carry no run).
        if cell.get("run_id") is not None:
            raise ValueError(
                f"excluded cell {pair!r} has non-null run_id "
                f"{cell.get('run_id')!r}; exclusions must omit run_id"
            )
        if pair not in EXPECTED_EXCLUDED_CELLS:
            raise ValueError(
                f"excluded cell {pair!r} is not one of the expected "
                "ts_vite coverage-insufficient cells; only ts_vite x "
                "{kimi,qwen,deepseek_flash,deepseek_pro} may be excluded"
            )
        excluded_cells_public.append(
            {
                "repo_slice_id": repo_id,
                "model_family": model_key,
                "reason": EXPECTED_EXCLUDED_REASON,
            }
        )

    validation_flags["exclusion_identity_validated"] = True
    validation_flags["manifest_shape_and_exclusion_identity_validated"] = True

    overlap = seen_included & seen_excluded
    if overlap:
        raise ValueError(
            f"included/excluded cell overlap: {sorted(overlap)!r}"
        )

    bad_included = seen_included - EXPECTED_INCLUDED_CELLS
    if bad_included:
        raise ValueError(
            f"included cells outside the expected included universe: "
            f"{sorted(bad_included)!r}"
        )

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
                f"expected {EXPECTED_ANALYZABLE_CELL_COUNT} analyzable "
                f"cells, got {len(seen_included)}"
            )
        if len(seen_excluded) != EXPECTED_EXCLUDED_CELL_COUNT:
            raise ValueError(
                f"expected {EXPECTED_EXCLUDED_CELL_COUNT} excluded cells, "
                f"got {len(seen_excluded)}"
            )
        validation_flags["official_matrix_shape_validated"] = True

    # Reconcile discovered reports against the manifest included set: every
    # discovered run_id must be in the manifest included set; every manifest
    # included run_id must have a discovered report (hard fail on a missing
    # expected report unless the manifest marks it coverage-insufficient —
    # but coverage-insufficient cells are excluded above and have no run_id,
    # so any included run_id missing a report is a hard failure).
    discovered_run_ids: set[str] = set()
    for entry in discovered:
        rid = entry["run_id"]
        if rid in discovered_run_ids:
            raise ValueError(
                f"duplicate discovered C3 report run_id {rid!r}"
            )
        discovered_run_ids.add(rid)
        if rid not in run_id_to_meta:
            raise ValueError(
                f"discovered C3 report run_id {rid!r} is not in the "
                f"manifest included set"
            )
        included_cell_meta[rid] = run_id_to_meta[rid]

    missing_included = [
        rid for rid in run_id_to_meta if rid not in discovered_run_ids
    ]
    if missing_included:
        raise ValueError(
            f"manifest included {len(missing_included)} run_id(s) but no "
            f"matching C3 report was discovered: {sorted(missing_included)}"
        )

    return included_cell_meta, excluded_cells_public, validation_flags


# ---------------------------------------------------------------------------
# Per-cell report validation
# ---------------------------------------------------------------------------

_C3_REQUIRED_FLAGS_FALSE = (
    "winner_declared",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
)
_C3_REQUIRED_FLAGS_TRUE = (
    "empirical_algorithm_experiment_performed",
    "cell_diagnostic_rank_only",
    "candidate_selection_deferred_to_matrix_combiner",
    "runtime_clean_policy_inputs_only",
    "selected_actions_invariant_under_private_field_permutation",
    "aggregate_only_public_artifact",
)


def _require_numeric(value: Any, ctx: str) -> float:
    """Fail-closed numeric coercion. Raises ``ValueError`` if not numeric."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{ctx} must be numeric; got {value!r}")
    return float(value)


def _require_metric_block(
    block: Any,
    complete_records: int,
    *,
    kind: str,
    key: str,
) -> dict[str, float]:
    """Validate a per-policy / baseline metric block fail-closed.

    Requires ``n_records == complete_records``, every ``mean_<metric>`` and
    ``sum_<metric>`` present and numeric for all ``METRIC_NAMES``, and
    ``abs(sum - mean * n_records)`` within ``_SUM_MEAN_TOL``. Returns the
    dict of means keyed by metric name.
    """
    if not isinstance(block, dict):
        raise ValueError(f"{kind} {key!r} is not a dict: {block!r}")
    n = _require_numeric(block.get("n_records"), f"{kind} {key!r} n_records")
    if int(n) != complete_records:
        raise ValueError(
            f"{kind} {key!r} n_records={n!r} != complete_records="
            f"{complete_records}"
        )
    means: dict[str, float] = {}
    for m in METRIC_NAMES:
        mean = _require_numeric(
            block.get(f"mean_{m}"), f"{kind} {key!r} mean_{m}"
        )
        total = _require_numeric(
            block.get(f"sum_{m}"), f"{kind} {key!r} sum_{m}"
        )
        # Rounding tolerance: the per-cell report rounds means to 6 decimals,
        # so sum may differ from mean*n_records by up to ~n_records*5e-7.
        if abs(total - mean * n) > max(_SUM_MEAN_TOL, abs(n) * 1e-5):
            raise ValueError(
                f"{kind} {key!r} metric {m!r} inconsistent: "
                f"sum={total!r} != mean*n_records={mean * n!r} "
                f"(n={n})"
            )
        means[m] = mean
    return means


def _require_delta_block(
    deltas_block: Any,
    baseline: str,
    *,
    policy_id: str,
) -> dict[str, float]:
    """Validate a per-policy delta block fail-closed.

    Requires the ``deltas[policy][baseline]`` block to be a dict containing a
    numeric ``mean_<metric>`` for every metric. Returns means keyed by metric.
    """
    if not isinstance(deltas_block, dict):
        raise ValueError(
            f"delta block for policy {policy_id!r} vs {baseline!r} is not a "
            f"dict: {deltas_block!r}"
        )
    means: dict[str, float] = {}
    for m in METRIC_NAMES:
        means[m] = _require_numeric(
            deltas_block.get(f"mean_{m}"),
            f"delta {policy_id!r} vs {baseline!r} mean_{m}",
        )
    return means


def _validate_c3_report(report: dict[str, Any]) -> None:
    """Validate a per-run C3 aggregate report against the public contract.

    Fail-closed: every required field must be present and well-formed. Missing
    or malformed per-policy / baseline / delta metric blocks raise rather than
    being silently defaulted to 0.
    """
    if report.get("schema_version") != INPUT_C3_SCHEMA:
        raise ValueError(
            f"unexpected C3 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("generated_by") != INPUT_C3_GENERATED_BY:
        raise ValueError(
            f"unexpected C3 generated_by: {report.get('generated_by')!r}"
        )
    if report.get("replay_source") != "ci_ephemeral_records":
        raise ValueError(
            "C3 input must have replay_source=ci_ephemeral_records for a "
            "real official-matrix combine"
        )
    # Per-cell scientific status must be ok_cell_stats for an included cell.
    if report.get("status") != "ok_cell_stats":
        raise ValueError(
            f"C3 input status must be ok_cell_stats; got {report.get('status')!r}"
        )
    # Frozen metric_names / allowed_runtime_features must match the spec
    # byte-for-byte.
    if tuple(report.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError(
            "C3 input metric_names does not match the frozen C3 spec"
        )
    if tuple(report.get("allowed_runtime_features") or ()) != ALLOWED_RUNTIME_FEATURES:
        raise ValueError(
            "C3 input allowed_runtime_features does not match the frozen C3 spec"
        )
    for flag in _C3_REQUIRED_FLAGS_TRUE:
        if report.get(flag) is not True:
            raise ValueError(
                f"C3 input must have {flag}=true; got {report.get(flag)!r}"
            )
    for flag in _C3_REQUIRED_FLAGS_FALSE:
        if report.get(flag) is not False:
            raise ValueError(
                f"C3 input must have {flag}=false; got {report.get(flag)!r}"
            )
    if _as_int(report.get("remote_calls_by_c3")) != 0:
        raise ValueError(
            "C3 input must have remote_calls_by_c3=0; got "
            f"{report.get('remote_calls_by_c3')!r}"
        )
    if _as_int(report.get("model_calls_by_replay")) != 0:
        raise ValueError(
            "C3 input must have model_calls_by_replay=0; got "
            f"{report.get('model_calls_by_replay')!r}"
        )
    # Frozen candidate policy ids + action set must match the C3 spec.
    if tuple(report.get("candidate_policy_ids") or ()) != CANDIDATE_POLICY_IDS:
        raise ValueError(
            "C3 input candidate_policy_ids does not match the frozen C3 spec"
        )
    if tuple(report.get("action_set") or ()) != ALLOWED_CANDIDATE_ACTIONS:
        raise ValueError(
            "C3 input action_set does not match the frozen C3 spec"
        )
    # Algorithm spec sha256 must be matched and stable.
    if report.get("algorithm_spec_sha256_matched") is not True:
        raise ValueError(
            "C3 input algorithm_spec_sha256_matched must be true"
        )
    if report.get("algorithm_spec_sha256_stable") is not True:
        raise ValueError(
            "C3 input algorithm_spec_sha256_stable must be true"
        )
    # Objective constants: fail if present and inconsistent; absence is NOT
    # claimed as validated.
    obj = report.get("objective_constants")
    if isinstance(obj, dict) and obj:
        for k, expected in OBJECTIVE_CONSTANTS.items():
            if k in obj:
                v = obj.get(k)
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(
                        f"C3 input objective_constants.{k} must be numeric; "
                        f"got {v!r}"
                    )
                if abs(float(v) - expected) > 1e-9:
                    raise ValueError(
                        f"C3 input objective_constants.{k}={v!r} != frozen "
                        f"value {expected!r}"
                    )
    # Per-cell safety invariants must confirm a clean forbidden scan and no
    # raw path/digest/provider strings.
    si = report.get("safety_invariants", {}) or {}
    if si.get("forbidden_public_keys_scanned") is not True:
        raise ValueError(
            "C3 input safety_invariants.forbidden_public_keys_scanned "
            "must be true"
        )
    if si.get("no_raw_path_digest_provider_strings") is not True:
        raise ValueError(
            "C3 input safety_invariants.no_raw_path_digest_provider_strings"
            " must be true"
        )
    if _as_int(report.get("complete_records", 0)) <= 0:
        raise ValueError(
            "C3 input must have complete_records > 0 for an included "
            "official-matrix cell"
        )
    if _as_int(report.get("incomplete_record_count", 0)) != 0:
        raise ValueError(
            "C3 input must have incomplete_record_count == 0 for an "
            "included official-matrix cell"
        )
    complete_records = _as_int(report.get("complete_records", 0))

    # Fail-closed per-policy / baseline / delta metric validation.
    per_policy = report.get("per_policy")
    if not isinstance(per_policy, dict):
        raise ValueError("C3 input per_policy must be a dict")
    for pid in CANDIDATE_POLICY_IDS:
        if pid not in per_policy:
            raise ValueError(
                f"C3 input per_policy missing candidate policy {pid!r}"
            )
        _require_metric_block(
            per_policy[pid], complete_records,
            kind="per_policy", key=pid,
        )

    baselines = report.get("baselines")
    if not isinstance(baselines, dict):
        raise ValueError("C3 input baselines must be a dict")
    for b in BASELINES:
        if b not in baselines:
            raise ValueError(
                f"C3 input baselines missing baseline {b!r}"
            )
        _require_metric_block(
            baselines[b], complete_records,
            kind="baseline", key=b,
        )

    deltas = report.get("deltas")
    if not isinstance(deltas, dict):
        raise ValueError("C3 input deltas must be a dict")
    for pid in CANDIDATE_POLICY_IDS:
        if pid not in deltas:
            raise ValueError(
                f"C3 input deltas missing candidate policy {pid!r}"
            )
        dp = deltas[pid]
        if not isinstance(dp, dict):
            raise ValueError(
                f"C3 input deltas[{pid!r}] must be a dict"
            )
        for baseline_key in ("vs_p25", "vs_balanced_v1"):
            blk = dp.get(baseline_key)
            _require_delta_block(
                blk, baseline_key.split("vs_", 1)[1],
                policy_id=pid,
            )

    # Re-run the FULL C3 forbidden-field scan on the input itself (defence in
    # depth). This uses c3bea._recursive_key_scan, which enforces C3's full
    # forbidden-key contract (run_id, route_features, etc.), not B6's weaker
    # scanner.
    violations = c3bea._recursive_key_scan(report)
    if violations:
        raise ValueError(
            "C3 input contains forbidden public keys/values (C3 scanner); "
            f"first violations: {violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Aggregation mechanics
# ---------------------------------------------------------------------------


def _per_policy_means(
    block: dict[str, Any],
    complete_records: int,
    *,
    kind: str,
    key: str,
) -> dict[str, float]:
    """Return validated means for a policy/baseline metric block.

    Delegates to ``_require_metric_block`` (fail-closed). The combiner only
    reads validated means and re-derives sums from ``mean * n_records``;
    it never silently defaults missing/malformed blocks to 0.
    """
    return _require_metric_block(
        block, complete_records, kind=kind, key=key,
    )


def _delta_means(
    deltas_block: dict[str, Any],
    baseline: str,
    *,
    policy_id: str,
) -> dict[str, float]:
    """Return validated delta means for ``deltas[policy][baseline]``.

    Delegates to ``_require_delta_block`` (fail-closed).
    """
    return _require_delta_block(
        deltas_block, baseline, policy_id=policy_id,
    )


def combine(
    artifacts_dir: Path,
    manifest_path: Path | None = None,
    self_test: bool = False,
) -> dict[str, Any]:
    """Combine the per-run C3 public aggregate reports into one rollup."""
    if not self_test and manifest_path is None:
        raise ValueError(
            "--manifest is required for a real (non-self-test) combine; the "
            "official C3 matrix shape (28 analyzable + 4 ts_vite excluded) "
            "must be enforced"
        )

    discovered = _discover_reports(artifacts_dir)
    if not discovered:
        raise ValueError(
            f"no C3 aggregate reports discovered under {artifacts_dir}"
        )
    manifest = _load_manifest(manifest_path)
    included_cell_meta, excluded_cells_public, validation_flags = (
        _reconcile_manifest(
            discovered, manifest, self_test=self_test
        )
    )

    report = _base_report(self_test)
    report["source_artifacts_dir_public_note"] = (
        "already-downloaded aggregate-only public C3 budgeted evidence "
        "acquisition reports; no raw records, paths, prompts, responses, "
        "snippets, or labels read"
    )

    integrity: dict[str, Any] = {
        "all_inputs_aggregate_only_public_artifact": True,
        "all_inputs_replay_source_ci_ephemeral_records": True,
        "all_inputs_winner_declared_false": True,
        "all_inputs_promotion_ready_false": True,
        "all_inputs_default_should_change_false": True,
        "all_inputs_evidencecore_semantics_changed_false": True,
        "all_inputs_cell_diagnostic_rank_only_true": True,
        "all_inputs_candidate_selection_deferred_to_matrix_combiner": True,
        "all_inputs_runtime_clean_policy_inputs_only": True,
        "all_inputs_selected_actions_invariant_under_permutation": True,
        "all_inputs_remote_calls_by_c3_zero": True,
        "all_inputs_model_calls_by_replay_zero": True,
        "all_inputs_complete_records_positive": True,
        "all_inputs_incomplete_record_count_zero": True,
        "all_inputs_status_ok_cell_stats": True,
        "all_inputs_metric_names_match_spec": True,
        "all_inputs_allowed_runtime_features_match_spec": True,
        "all_inputs_algorithm_spec_sha256_matched_and_stable": True,
        "all_inputs_per_policy_metric_blocks_complete_and_consistent": True,
        "all_inputs_baseline_metric_blocks_complete_and_consistent": True,
        "all_inputs_delta_metric_blocks_complete": True,
        "all_inputs_candidate_policy_ids_match_spec": True,
        "all_inputs_action_set_match_spec": True,
        "all_inputs_forbidden_public_scan_clean_c3_scanner": True,
        "all_inputs_no_raw_path_digest_provider_strings": True,
        "manifest_reconciled": manifest is not None,
        "manifest_shape_and_exclusion_identity_validated": validation_flags[
            "manifest_shape_and_exclusion_identity_validated"
        ],
        "official_matrix_shape_validated": validation_flags[
            "official_matrix_shape_validated"
        ],
        "exclusion_identity_validated": validation_flags[
            "exclusion_identity_validated"
        ],
        # The combiner does NOT validate per-cell report labels (repo/model
        # identity) against the per-cell report body; it only validates the
        # manifest shape, exclusion identity, and per-cell report contract.
        # This is always False and is emitted for transparency.
        "manifest_report_labels_validated": False,
    }

    # Aggregation accumulators.
    # per-policy: weight-accumulators for mean, sum-accumulators for sums.
    per_policy_mean_acc: dict[str, dict[str, list[tuple[int, float]]]] = {
        pid: {m: [] for m in METRIC_NAMES} for pid in CANDIDATE_POLICY_IDS
    }
    per_policy_sum_acc: dict[str, dict[str, float]] = {
        pid: {m: 0.0 for m in METRIC_NAMES} for pid in CANDIDATE_POLICY_IDS
    }
    per_policy_records: dict[str, int] = {
        pid: 0 for pid in CANDIDATE_POLICY_IDS
    }

    baseline_mean_acc: dict[str, dict[str, list[tuple[int, float]]]] = {
        b: {m: [] for m in METRIC_NAMES} for b in BASELINES
    }
    baseline_sum_acc: dict[str, dict[str, float]] = {
        b: {m: 0.0 for m in METRIC_NAMES} for b in BASELINES
    }
    baseline_records: dict[str, int] = {b: 0 for b in BASELINES}

    # Delta accumulators: deltas_vs_p25[policy][metric], deltas_vs_balanced_v1.
    delta_acc: dict[str, dict[str, dict[str, list[tuple[int, float]]]]] = {
        "vs_p25": {
            pid: {m: [] for m in METRIC_NAMES} for pid in CANDIDATE_POLICY_IDS
        },
        "vs_balanced_v1": {
            pid: {m: [] for m in METRIC_NAMES} for pid in CANDIDATE_POLICY_IDS
        },
    }

    feature_acc: Counter = Counter()
    for feat in ALLOWED_RUNTIME_FEATURES:
        feature_acc[feat] = 0

    total_records_sum = 0
    complete_records_sum = 0
    cell_complete_records: list[int] = []

    # Per (repo_slice, model_family) record-count rollups (counts only).
    per_repo_records: dict[str, int] = defaultdict(int)
    per_model_records: dict[str, int] = defaultdict(int)
    per_repo_cell_count: Counter = Counter()
    per_model_cell_count: Counter = Counter()

    public_repo_slices_seen: set[str] = set()
    public_model_families_seen: set[str] = set()

    included_report_files: list[str] = []

    for entry in discovered:
        c3 = json.loads(Path(entry["path"]).read_text(encoding="utf-8"))
        _validate_c3_report(c3)

        meta = included_cell_meta.get(entry["run_id"], {})
        repo_slice = meta.get("repo_slice_id", "unknown")
        model_family = meta.get("model_family", "unknown")

        # Cross-check the manifest slice labels against the cell's public
        # language_counts / model_family_counts presence (defence in depth:
        # the per-cell report does not carry its own repo_id, so we only
        # require the manifest slice to be in the expected universe, which
        # _reconcile_manifest already enforced).
        public_repo_slices_seen.add(repo_slice)
        public_model_families_seen.add(model_family)
        per_repo_cell_count[repo_slice] += 1
        per_model_cell_count[model_family] += 1

        n_complete = _as_int(c3.get("complete_records", 0))
        n_total = _as_int(c3.get("total_records", n_complete))
        cell_complete_records.append(n_complete)
        complete_records_sum += n_complete
        total_records_sum += n_total
        per_repo_records[repo_slice] += n_complete
        per_model_records[model_family] += n_complete

        # Fail-closed per-policy / baseline / delta reads: _validate_c3_report
        # already asserted every required block exists, n_records ==
        # complete_records, every mean_/sum_ is numeric, and sum ~ mean*n. We
        # re-read through _per_policy_means / _delta_means (which re-validate)
        # so the aggregation path can never silently default to 0.
        per_policy = c3.get("per_policy", {}) or {}
        for pid in CANDIDATE_POLICY_IDS:
            blk = per_policy.get(pid, {}) or {}
            means = _per_policy_means(
                blk, n_complete, kind="per_policy", key=pid,
            )
            for m in METRIC_NAMES:
                mean = means[m]
                per_policy_mean_acc[pid][m].append((n_complete, mean))
                # Re-derive the per-cell sum from the validated mean (the
                # report's own sum_<m> is checked for consistency in
                # _require_metric_block, but the mean*n form avoids
                # rounding drift accumulating into the aggregate sum).
                per_policy_sum_acc[pid][m] += mean * n_complete
            per_policy_records[pid] += n_complete

        bblk = c3.get("baselines", {}) or {}
        for b in BASELINES:
            bb = bblk.get(b, {}) or {}
            means = _per_policy_means(
                bb, n_complete, kind="baseline", key=b,
            )
            for m in METRIC_NAMES:
                mean = means[m]
                baseline_mean_acc[b][m].append((n_complete, mean))
                baseline_sum_acc[b][m] += mean * n_complete
            baseline_records[b] += n_complete

        deltas = c3.get("deltas", {}) or {}
        for pid in CANDIDATE_POLICY_IDS:
            dp = deltas.get(pid, {}) or {}
            d_p25 = _delta_means(
                dp.get("vs_p25", {}) or {}, "p25", policy_id=pid,
            )
            d_bal = _delta_means(
                dp.get("vs_balanced_v1", {}) or {}, "balanced_v1",
                policy_id=pid,
            )
            for m in METRIC_NAMES:
                delta_acc["vs_p25"][pid][m].append((n_complete, d_p25[m]))
                delta_acc["vs_balanced_v1"][pid][m].append(
                    (n_complete, d_bal[m])
                )

        fpc = c3.get("feature_presence_counts", {}) or {}
        for feat in ALLOWED_RUNTIME_FEATURES:
            feature_acc[feat] += _as_int(fpc.get(feat, 0))

        included_report_files.append(entry["path"])

    # Note: the combiner does NOT validate per-cell report labels (repo/model
    # identity) against the per-cell report body; it only validates the
    # manifest shape, exclusion identity, and per-cell report contract.
    # ``manifest_report_labels_validated`` is always False (set in the
    # integrity dict init) and is emitted for transparency.

    # ------------------------------------------------------------------
    # Build aggregate metric blocks.
    # ------------------------------------------------------------------
    per_candidate_policy: dict[str, dict[str, Any]] = {}
    for pid in CANDIDATE_POLICY_IDS:
        means = {
            m: _round6(_weighted_mean(per_policy_mean_acc[pid][m]))
            for m in METRIC_NAMES
        }
        sums = {
            m: _round6(per_policy_sum_acc[pid][m]) for m in METRIC_NAMES
        }
        per_candidate_policy[pid] = {
            "n_records": per_policy_records[pid],
            "mean": means,
            "sum": sums,
        }

    baseline_aggregates: dict[str, dict[str, Any]] = {}
    for b in BASELINES:
        means = {
            m: _round6(_weighted_mean(baseline_mean_acc[b][m]))
            for m in METRIC_NAMES
        }
        sums = {
            m: _round6(baseline_sum_acc[b][m]) for m in METRIC_NAMES
        }
        baseline_aggregates[b] = {
            "n_records": baseline_records[b],
            "mean": means,
            "sum": sums,
        }

    deltas_vs_p25: dict[str, dict[str, float]] = {}
    deltas_vs_balanced_v1: dict[str, dict[str, float]] = {}
    for pid in CANDIDATE_POLICY_IDS:
        deltas_vs_p25[pid] = {
            m: _round6(_weighted_mean(delta_acc["vs_p25"][pid][m]))
            for m in METRIC_NAMES
        }
        deltas_vs_balanced_v1[pid] = {
            m: _round6(_weighted_mean(delta_acc["vs_balanced_v1"][pid][m]))
            for m in METRIC_NAMES
        }

    # ------------------------------------------------------------------
    # Diagnostic rank (ordering ONLY; no winner, no selection).
    # ------------------------------------------------------------------
    # Sort candidate policy ids by aggregate mean utility descending. Ties
    # broken by policy id for determinism. This is a DIAGNOSTIC ordering; it
    # does NOT declare a winner, does NOT freeze, does NOT select.
    diagnostic_rank_only_global = sorted(
        CANDIDATE_POLICY_IDS,
        key=lambda pid: (
            -per_candidate_policy[pid]["mean"]["utility"],
            pid,
        ),
    )
    candidate_selected = {pid: False for pid in CANDIDATE_POLICY_IDS}

    # ------------------------------------------------------------------
    # Coverage exclusions summary (counts only; no run ids).
    # ------------------------------------------------------------------
    cov_counter: Counter = Counter()
    for cell in excluded_cells_public:
        cov_counter[
            (cell["repo_slice_id"], cell["model_family"], cell["reason"])
        ] += 1
    coverage_exclusion_summary = [
        {
            "repo_slice_id": repo,
            "model_family": model,
            "reason": reason,
            "count": count,
        }
        for (repo, model, reason), count in sorted(cov_counter.items())
    ]
    reason_counts: Counter = Counter()
    for cell in excluded_cells_public:
        reason_counts[cell["reason"]] += 1

    # Per-(repo_slice, model_family) record/cell rollups (counts only).
    per_repo_summary: dict[str, Any] = {
        repo: {
            "record_count": per_repo_records[repo],
            "cell_count": per_repo_cell_count[repo],
        }
        for repo in sorted(per_repo_records)
    }
    per_model_summary: dict[str, Any] = {
        family: {
            "record_count": per_model_records[family],
            "cell_count": per_model_cell_count[family],
        }
        for family in sorted(per_model_records)
    }

    # ------------------------------------------------------------------
    # Status / verdict logic.
    # ------------------------------------------------------------------
    analyzable_cell_count = len(discovered)
    excluded_cell_count = len(excluded_cells_public)

    if excluded_cell_count > 0 and analyzable_cell_count > 0:
        status = "matrix_aggregate_ok_with_exclusions"
    elif excluded_cell_count == 0 and analyzable_cell_count > 0:
        status = "matrix_aggregate_ok"
    else:
        status = "insufficient_reports"

    # artifact manifest summary: count-only (no digests, to avoid any hash-
    # leakage confusion under the forbidden-value scan).
    artifact_manifest_summary = {
        "included_report_file_count": len(included_report_files),
        "digest_emitted": False,
        "note": (
            "count-only manifest summary; sha256 digests of included public "
            "C3 report files are intentionally omitted to avoid hash-shaped "
            "values under the public forbidden-value scan"
        ),
    }

    report.update(
        {
            "status": status,
            "planned_cells": CELL_COUNT_TARGET,
            "included_cells": analyzable_cell_count,
            "coverage_excluded_cells": excluded_cell_count,
            "analyzable_cell_count": analyzable_cell_count,
            "run_count": len(discovered),
            "total_records": total_records_sum,
            "complete_records": complete_records_sum,
            "public_repo_slice_count": len(public_repo_slices_seen),
            "public_repo_slice_ids": sorted(public_repo_slices_seen),
            "public_model_family_count": len(public_model_families_seen),
            "public_model_family_names": sorted(public_model_families_seen),
            "per_candidate_policy": per_candidate_policy,
            "baseline_aggregates": baseline_aggregates,
            "deltas_vs_p25": deltas_vs_p25,
            "deltas_vs_balanced_v1": deltas_vs_balanced_v1,
            "diagnostic_rank_only_global": diagnostic_rank_only_global,
            "winner_declared": False,
            "candidate_selected": candidate_selected,
            "candidate_selection_deferred_to_future_preregistered_matrix": (
                True
            ),
            "runtime_feature_coverage": dict(
                sorted(feature_acc.items())
            ),
            "coverage_exclusions": excluded_cells_public,
            "coverage_exclusion_summary": coverage_exclusion_summary,
            "coverage_exclusion_reason_counts": dict(reason_counts),
            "per_repo_slice": per_repo_summary,
            "per_model_family": per_model_summary,
            "artifact_manifest_summary": artifact_manifest_summary,
            "integrity": integrity,
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "evidencecore_semantics_changed_false": True,
                "runtime_clean_candidate_evaluated": True,
                "policy_search_performed_false": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_task_ids_in_artifact": True,
                "no_paths_spans_hashes_snippets_prompts_responses": True,
                "no_forbidden_public_keys": True,
                "no_raw_path_digest_provider_strings": True,
                "remote_calls_by_combiner": 0,
                "model_calls_by_combiner": 0,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "winner_declared": False,
                "runtime_clean_general_algorithm_claimed": False,
                "signal_strength": "diagnostic_rank_only_matrix_aggregate",
                "claim_boundary": (
                    "C3 budgeted evidence acquisition matrix aggregate; "
                    "diagnostic-rank-only. NOT a promotion step, NOT a "
                    "default change, NOT an EvidenceCore semantics change. "
                    "No winner declared; no candidate selected; selection "
                    "deferred to a future preregistered matrix."
                ),
                "recommended_next_step": (
                    "future_preregistered_matrix_or_ts_vite_coverage_rerun"
                ),
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _synthetic_c3_report(
    complete_records: int,
    *,
    per_policy_means: dict[str, dict[str, float]],
    p25_means: dict[str, float],
    balanced_means: dict[str, float],
    feature_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a minimal synthetic per-run C3 aggregate report for self-test.

    Only the fields read by the combiner are populated; the report still
    satisfies the combiner's own per-cell validation contract. It is NOT a
    real per-run C3 report and is only ever materialized inside a temporary
    self-test directory.
    """
    n = float(complete_records)
    per_policy: dict[str, dict[str, Any]] = {}
    deltas: dict[str, dict[str, dict[str, float]]] = {}
    for pid in CANDIDATE_POLICY_IDS:
        means = per_policy_means[pid]
        per_policy[pid] = {
            "n_records": n,
        }
        for m in METRIC_NAMES:
            v = means[m]
            per_policy[pid][f"mean_{m}"] = v
            per_policy[pid][f"sum_{m}"] = v * n
        deltas[pid] = {
            "vs_p25": {
                f"mean_{m}": means[m] - p25_means[m] for m in METRIC_NAMES
            },
            "vs_balanced_v1": {
                f"mean_{m}": means[m] - balanced_means[m]
                for m in METRIC_NAMES
            },
        }

    baselines: dict[str, dict[str, Any]] = {}
    for b, means in (("p25", p25_means), ("balanced_v1", balanced_means)):
        blk: dict[str, Any] = {"n_records": n}
        for m in METRIC_NAMES:
            v = means[m]
            blk[f"mean_{m}"] = v
            blk[f"sum_{m}"] = v * n
        baselines[b] = blk

    return {
        "schema_version": INPUT_C3_SCHEMA,
        "generated_by": INPUT_C3_GENERATED_BY,
        "generated_at": "2026-06-19T00:00:00+00:00",
        "claim_level": "budgeted_replay_policy_experiment_v0",
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_or_enumeration_performed": True,
        "empirical_algorithm_experiment_performed": True,
        "replay_source": "ci_ephemeral_records",
        "replay_only": True,
        "remote_calls_by_c3": 0,
        "model_calls_by_replay": 0,
        "winner_declared": False,
        "cell_diagnostic_rank_only": True,
        "candidate_selection_deferred_to_matrix_combiner": True,
        "runtime_clean_policy_inputs_only": True,
        "selected_actions_invariant_under_private_field_permutation": True,
        "candidate_policy_ids": list(CANDIDATE_POLICY_IDS),
        "action_set": list(ALLOWED_CANDIDATE_ACTIONS),
        "allowed_runtime_features": list(ALLOWED_RUNTIME_FEATURES),
        "metric_names": list(METRIC_NAMES),
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "objective_constants": dict(OBJECTIVE_CONSTANTS),
        "policy_count": len(CANDIDATE_POLICY_IDS),
        "total_records": complete_records,
        "complete_records": complete_records,
        "incomplete_record_count": 0,
        "status": "ok_cell_stats",
        "self_test": False,
        "per_policy": per_policy,
        "baselines": baselines,
        "deltas": deltas,
        "feature_presence_counts": dict(feature_counts),
        "safety_invariants": {
            "aggregate_only_public_artifact": True,
            "default_should_change_false": True,
            "forbidden_public_keys_scanned": True,
            "no_evidencecore_semantics_change": True,
            "no_live_llm_calls": True,
            "no_per_cell_winner": True,
            "no_policy_tuning_from_outcomes": True,
            "no_raw_path_digest_provider_strings": True,
            "no_threshold_tuning": True,
            "promotion_ready_false": True,
            "replay_only_no_live_runs_in_evaluator": True,
        },
    }


def _build_self_test_artifacts(root: Path) -> tuple[Path, Path]:
    """Materialize a tiny synthetic C3 matrix tree (2 cells + 1 exclusion)."""
    artifacts = root / "artifacts"

    # 2 analyzable cells. Use distinct repo/model slices and deterministic
    # per-policy means so the self-test can assert weighted means exactly.
    zero_means = {m: 0.0 for m in METRIC_NAMES}
    cell_specs = [
        # (run_id, repo, model, complete, per_policy_means, p25, balanced, fpc)
        (
            "91000000001", "py_fastapi", "kimi", 12,
            {
                "local_only": {
                    "span_f0_5": 0.1, "added_gold_span": 1.0,
                    "added_false_span": 2.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.0, "utility": -1.9,
                },
                "weak_on_noise_else_local": {
                    "span_f0_5": 0.1, "added_gold_span": 1.0,
                    "added_false_span": 2.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.0, "utility": -1.9,
                },
                "span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 1.0, "utility": -0.1,
                },
                "filter_on_noise_else_span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.5, "utility": -0.05,
                },
                "abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.5, "utility": -0.05,
                },
                "weak_on_disagreement_span_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.5, "utility": -0.05,
                },
            },
            {
                "span_f0_5": 0.0, "added_gold_span": 0.0,
                "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                "model_calls": 1.0, "utility": -0.1,
            },
            {
                "span_f0_5": 0.0, "added_gold_span": 0.0,
                "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                "model_calls": 1.0, "utility": -0.1,
            },
            {"local_anchor": 10, "rrf_backed_by_anchor": 7, "query_noise": 1},
        ),
        (
            "91000000002", "py_pytest", "qwen", 12,
            {
                "local_only": {
                    "span_f0_5": 0.2, "added_gold_span": 0.5,
                    "added_false_span": 1.5, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.0, "utility": -1.3,
                },
                "weak_on_noise_else_local": {
                    "span_f0_5": 0.2, "added_gold_span": 0.5,
                    "added_false_span": 1.5, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.0, "utility": -1.3,
                },
                "span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.5, "utility": -0.05,
                },
                "filter_on_noise_else_span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.25, "utility": -0.025,
                },
                "abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.25, "utility": -0.025,
                },
                "weak_on_disagreement_span_on_anchor_else_local": {
                    "span_f0_5": 0.0, "added_gold_span": 0.0,
                    "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                    "model_calls": 0.25, "utility": -0.025,
                },
            },
            {
                "span_f0_5": 0.0, "added_gold_span": 0.0,
                "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                "model_calls": 1.0, "utility": -0.1,
            },
            {
                "span_f0_5": 0.0, "added_gold_span": 0.0,
                "added_false_span": 0.0, "primary_false_positive_rate": 0.0,
                "model_calls": 1.0, "utility": -0.1,
            },
            {"local_anchor": 8, "rrf_backed_by_anchor": 5, "query_noise": 2},
        ),
    ]

    for (
        run_id, repo, model, complete, pp_means, p25, balanced, fpc,
    ) in cell_specs:
        run_dir = f"real-provider-p21_llm_rich-{run_id}"
        ci_dir = artifacts / run_id / run_dir / "artifacts" / "real_provider_ci"
        ci_dir.mkdir(parents=True, exist_ok=True)
        report = _synthetic_c3_report(
            complete,
            per_policy_means=pp_means,
            p25_means=p25,
            balanced_means=balanced,
            feature_counts=fpc,
        )
        (ci_dir / _REPORT_FILENAME).write_text(
            json.dumps(report, sort_keys=True), encoding="utf-8"
        )

    # Flat-list manifest: 2 included + 1 excluded.
    manifest = [
        {
            "repo_id": "py_fastapi", "model_key": "kimi",
            "llm_model": "[mk]Kimi-K2.7-Code", "llm_output_mode": "tool_call",
            "run_id": 91000000001, "source": "self_test",
            "status": "queued",
        },
        {
            "repo_id": "py_pytest", "model_key": "qwen",
            "llm_model": "[mk]Qwen3.6-27B", "llm_output_mode": "json_schema_strict",
            "run_id": 91000000002, "source": "self_test",
            "status": "queued",
        },
        {
            "repo_id": "ts_vite", "model_key": "kimi",
            "llm_model": "[mk]Kimi-K2.7-Code", "llm_output_mode": "tool_call",
            "run_id": None, "source": "self_test",
            "status": EXCLUSION_STATUS,
            "exclusion_reason": "self_test_coverage_insufficient",
        },
    ]
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return artifacts, manifest_path


def _self_test_happy_path() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        report = combine(artifacts, manifest_path=manifest, self_test=True)

    assert report["status"] == "matrix_aggregate_ok_with_exclusions", report["status"]
    assert report["schema_version"] == SCHEMA_VERSION, report["schema_version"]
    assert report["planned_cells"] == 32, report["planned_cells"]
    assert report["included_cells"] == 2, report["included_cells"]
    assert report["coverage_excluded_cells"] == 1, report["coverage_excluded_cells"]
    assert report["analyzable_cell_count"] == 2
    assert report["run_count"] == 2
    assert report["complete_records"] == 24, report["complete_records"]
    assert report["total_records"] == 24

    # Frozen spec echoed back.
    assert report["candidate_policy_ids"] == list(CANDIDATE_POLICY_IDS)
    assert report["action_set"] == list(ALLOWED_CANDIDATE_ACTIONS)

    # Per-policy weighted mean check for `local_only.utility`:
    # (-1.9 + -1.3) / 2 = -1.6 (equal weight 12 each).
    lo = report["per_candidate_policy"]["local_only"]
    assert lo["mean"]["utility"] == -1.6, lo
    assert lo["sum"]["utility"] == round((-1.9 + -1.3) * 12, 6), lo

    # Deltas vs p25 for span_narrow_on_anchor_else_local.utility:
    # cell1: -0.1 - (-0.1) = 0.0 ; cell2: -0.05 - (-0.1) = 0.05 ;
    # weighted mean (equal weight) = 0.025.
    d_p25 = report["deltas_vs_p25"]["span_narrow_on_anchor_else_local"]
    assert d_p25["utility"] == 0.025, d_p25

    # Baseline p25/balanced aggregate utility: (-0.1 + -0.1)/2 = -0.1.
    assert report["baseline_aggregates"]["p25"]["mean"]["utility"] == -0.1
    assert report["baseline_aggregates"]["balanced_v1"]["mean"]["utility"] == -0.1

    # Diagnostic rank: highest mean utility first.
    # local_only / weak_on_noise_else_local tie at mean utility -1.6; the
    # LLM-costing candidates (span_narrow / filter / abstain /
    # weak_on_disagreement) have higher (less negative) mean utility
    # (~-0.075 / ~-0.0375), so they rank above local_only.
    rank = report["diagnostic_rank_only_global"]
    assert rank == sorted(
        CANDIDATE_POLICY_IDS,
        key=lambda pid: (-report["per_candidate_policy"][pid]["mean"]["utility"], pid),
    ), rank
    # No winner, no candidate selected.
    assert report["winner_declared"] is False
    assert report["candidate_selection_deferred_to_future_preregistered_matrix"] is True
    assert all(v is False for v in report["candidate_selected"].values())

    # Coverage exclusions sanitized: no run id, public slice only.
    cov = report["coverage_exclusions"]
    assert len(cov) == 1, cov
    assert cov[0] == {
        "repo_slice_id": "ts_vite",
        "model_family": "kimi",
        "reason": EXPECTED_EXCLUDED_REASON,
    }, cov
    assert report["coverage_exclusion_summary"][0]["count"] == 1
    assert report["coverage_exclusion_reason_counts"] == {
        EXPECTED_EXCLUDED_REASON: 1
    }

    # Runtime feature coverage = sum across cells.
    rfc = report["runtime_feature_coverage"]
    assert rfc["local_anchor"] == 18, rfc
    assert rfc["rrf_backed_by_anchor"] == 12, rfc
    assert rfc["query_noise"] == 3, rfc

    # Safety invariants.
    assert report["promotion_ready"] is False
    assert report["default_should_change"] is False
    assert report["evidencecore_semantics_changed"] is False
    assert report["remote_calls_by_combiner"] == 0
    assert report["model_calls_by_combiner"] == 0
    assert report["safety_invariants"]["no_run_ids_emitted"] is True
    assert report["safety_invariants"]["no_task_ids_in_artifact"] is True
    assert report["safety_invariants"]["no_paths_spans_hashes_snippets_prompts_responses"] is True
    assert report["safety_invariants"]["runtime_clean_candidate_evaluated"] is True

    # Forbidden scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    assert report["integrity"]["manifest_reconciled"] is True
    assert report["integrity"]["exclusion_identity_validated"] is True
    assert report["integrity"]["manifest_shape_and_exclusion_identity_validated"] is True
    # Full 8x4 shape NOT validated on self-test path (2+1 fixture).
    assert report["integrity"]["official_matrix_shape_validated"] is False
    # The combiner does NOT validate per-cell report labels; the flag is
    # always False (emitted for transparency).
    assert report["integrity"]["manifest_report_labels_validated"] is False
    # Fail-closed per-cell validation flags are surfaced.
    assert report["integrity"]["all_inputs_status_ok_cell_stats"] is True
    assert report["integrity"]["all_inputs_metric_names_match_spec"] is True
    assert report["integrity"]["all_inputs_allowed_runtime_features_match_spec"] is True
    assert report["integrity"]["all_inputs_algorithm_spec_sha256_matched_and_stable"] is True
    assert report["integrity"]["all_inputs_per_policy_metric_blocks_complete_and_consistent"] is True
    assert report["integrity"]["all_inputs_baseline_metric_blocks_complete_and_consistent"] is True
    assert report["integrity"]["all_inputs_delta_metric_blocks_complete"] is True
    assert report["integrity"]["all_inputs_forbidden_public_scan_clean_c3_scanner"] is True

    # Artifact manifest summary is count-only (no digests).
    ams = report["artifact_manifest_summary"]
    assert ams["included_report_file_count"] == 2, ams
    assert ams["digest_emitted"] is False, ams

    # No run-id-shaped numeric strings leaked anywhere in the serialized
    # output (the 91000000001-style synthetic run ids must NOT appear).
    blob = json.dumps(report, sort_keys=True)
    assert "91000000001" not in blob, "synthetic run id leaked into output"
    assert "91000000002" not in blob, "synthetic run id leaked into output"
    print("self-test happy path: ok")
    return report


def _self_test_forbidden_scan_catches_bad_input() -> None:
    """Inject a forbidden key into a per-run report and confirm rejection."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
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


def _self_test_missing_report_blocks() -> None:
    """Drop one included cell's report: combine must hard-fail (missing
    expected included report that is NOT marked coverage-insufficient)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        # Remove one report entirely so a manifest-included run has no report.
        gone = (
            artifacts / "91000000002"
            / "real-provider-p21_llm_rich-91000000002"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        gone.unlink()
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "no matching C3 report" in str(exc), exc
            print("self-test missing-report hard-fail: ok")
            return
    raise AssertionError("combine should have raised on missing report")


def _self_test_no_manifest_blocks_real_path() -> None:
    """A real (non-self-test) combine without --manifest must fail closed."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, _ = _build_self_test_artifacts(root)
        try:
            combine(artifacts, manifest_path=None, self_test=False)
        except ValueError as exc:
            assert "--manifest is required" in str(exc), exc
            print("self-test no-manifest real-path block: ok")
            return
    raise AssertionError("combine should have raised without manifest")


def _self_test_no_inputs_blocks() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            combine(Path(tmp), manifest_path=None, self_test=True)
        except ValueError as exc:
            assert "no C3 aggregate reports discovered" in str(exc), exc
            print("self-test no-inputs block: ok")
            return
    raise AssertionError("combine should have raised on empty input")


def _self_test_malformed_metric_block_blocks() -> None:
    """A per-policy block missing a mean_<metric> must hard-fail (not
    silently default to 0)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        # Remove a required mean field from one candidate policy.
        del bad["per_policy"]["local_only"]["mean_utility"]
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "mean_utility" in str(exc) or "must be numeric" in str(exc), exc
            print("self-test malformed-metric-block hard-fail: ok")
            return
    raise AssertionError("combine should have raised on a missing mean field")


def _self_test_inconsistent_sum_mean_blocks() -> None:
    """A per-policy block where sum != mean*n_records must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        # Corrupt the sum so it no longer matches mean*n_records.
        bad["per_policy"]["local_only"]["sum_utility"] = 999.0
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "inconsistent" in str(exc).lower(), exc
            print("self-test sum!=mean*n_records hard-fail: ok")
            return
    raise AssertionError("combine should have raised on sum/mean inconsistency")


def _self_test_missing_delta_blocks() -> None:
    """A per-policy delta block missing a mean_<metric> must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        del bad["deltas"]["local_only"]["vs_p25"]["mean_utility"]
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "mean_utility" in str(exc) or "must be numeric" in str(exc), exc
            print("self-test missing-delta-block hard-fail: ok")
            return
    raise AssertionError("combine should have raised on a missing delta field")


def _self_test_n_records_mismatch_blocks() -> None:
    """A per-policy n_records != complete_records must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        bad["per_policy"]["local_only"]["n_records"] = 999
        # Re-align sum to the bad n_records so the failure is specifically the
        # n_records != complete_records check, not the sum/mean check.
        bad["per_policy"]["local_only"]["sum_utility"] = (
            bad["per_policy"]["local_only"]["mean_utility"] * 999
        )
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "n_records" in str(exc), exc
            print("self-test n_records!=complete_records hard-fail: ok")
            return
    raise AssertionError("combine should have raised on n_records mismatch")


def _self_test_non_ok_cell_status_blocks() -> None:
    """A per-cell report with status != ok_cell_stats must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        bad_path = (
            artifacts / "91000000001"
            / "real-provider-p21_llm_rich-91000000001"
            / "artifacts" / "real_provider_ci" / _REPORT_FILENAME
        )
        bad = json.loads(bad_path.read_text(encoding="utf-8"))
        bad["status"] = "coverage_insufficient"
        bad_path.write_text(json.dumps(bad, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "ok_cell_stats" in str(exc), exc
            print("self-test non-ok_cell_stats status hard-fail: ok")
            return
    raise AssertionError("combine should have raised on non-ok status")


def _self_test_duplicate_run_id_in_manifest_blocks() -> None:
    """Duplicate included run_id in the manifest must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        m = json.loads(manifest.read_text(encoding="utf-8"))
        # Copy the second included cell's run_id onto the first.
        m[0]["run_id"] = m[1]["run_id"]
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "duplicate included run_id" in str(exc), exc
            print("self-test duplicate manifest run_id hard-fail: ok")
            return
    raise AssertionError("combine should have raised on duplicate manifest run_id")


def _self_test_non_null_exclusion_run_id_blocks() -> None:
    """An exclusion entry with a non-null run_id must hard-fail."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifacts, manifest = _build_self_test_artifacts(root)
        m = json.loads(manifest.read_text(encoding="utf-8"))
        # Give the exclusion a non-null run_id.
        m[2]["run_id"] = 91000000003
        manifest.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        try:
            combine(artifacts, manifest_path=manifest, self_test=True)
        except ValueError as exc:
            assert "non-null run_id" in str(exc), exc
            print("self-test non-null exclusion run_id hard-fail: ok")
            return
    raise AssertionError("combine should have raised on non-null exclusion run_id")


def _self_test() -> int:
    _self_test_happy_path()
    _self_test_forbidden_scan_catches_bad_input()
    _self_test_missing_report_blocks()
    _self_test_no_manifest_blocks_real_path()
    _self_test_no_inputs_blocks()
    _self_test_malformed_metric_block_blocks()
    _self_test_inconsistent_sum_mean_blocks()
    _self_test_missing_delta_blocks()
    _self_test_n_records_mismatch_blocks()
    _self_test_non_ok_cell_status_blocks()
    _self_test_duplicate_run_id_in_manifest_blocks()
    _self_test_non_null_exclusion_run_id_blocks()
    print("ALL C3 MATRIX COMBINER SELF-TESTS PASSED")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="C3 budgeted evidence acquisition matrix aggregate combiner"
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="directory containing per-run C3 aggregate reports",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="flat-list manifest of the 32 planned C3 matrix cells",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run synthetic self-test (no private records, no real combine)",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if args.artifacts_dir is None:
        parser.error("--artifacts-dir is required (or use --self-test)")
    report = combine(
        args.artifacts_dir, manifest_path=args.manifest, self_test=False
    )
    _write_json(args.out, report)
    print(f"wrote {args.out}")
    print(
        f"  status={report['status']} "
        f"included={report['included_cells']} "
        f"excluded={report['coverage_excluded_cells']} "
        f"complete_records={report['complete_records']}"
    )
    rank = report["diagnostic_rank_only_global"]
    if rank:
        top = rank[0]
        top_mean = report["per_candidate_policy"][top]["mean"]
        print(
            f"  diagnostic_rank_only_global[0]={top} "
            f"(mean_utility={top_mean['utility']}, "
            f"mean_model_calls={top_mean['model_calls']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
