#!/usr/bin/env python3
"""C5-F RepoQA 10-Needle Method-Matrix Scale Smoke (Public Aggregate-Only).

This module implements the **C5-F RepoQA bounded 10-needle method-matrix
scale smoke** over the EvalPlus RepoQA/SNF release asset
(``repoqa-2024-06-23.json.gz`` from ``evalplus/repoqa_release``). It
scales C5-E (5-needle RepoQA method-matrix smoke) up to the hard cap of
10 needles per method, while preserving C5-E as a completed checkpoint
with separate artifact/docs/workflow.

C5-F is a thin wrapper around C5-E: it reuses all C5-E helpers (asset
download, gzip parse, needle extraction, transient repo clone/checkout,
score task/label/run generation, scanner/failure categories, method
parser/validators, deltas-vs-baseline, status semantics, fail-closed
guards) and only overrides the identity constants, the default
needle_limit (10 vs C5-E's 5), and the safe-true flag name
(``repoqa_method_matrix_scale_smoke_performed`` vs C5-E's
``repoqa_method_matrix_smoke_performed``).

C5-F is explicitly **not** a benchmark result, **not** a leaderboard
entry, **not** a performance claim, **not** a promotion, **not** a
default/policy change, and **not** a runtime/retriever/pack/backend/
EvidenceCore semantic change. The committed artifact records only
per-method aggregate retrieval metrics (records, NOT dynamic method-key
dicts) plus aggregate-only deltas vs the fixed `bm25` baseline,
computed by `eval/score.py` over a bounded 10-needle RepoQA Python
subset per method.

Claim boundary (binding):

* Claim level: `repoqa_retrieval_method_matrix_scale_smoke_only`.
* Status: `repoqa_method_matrix_scale_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`.
* Mode: `repoqa_bounded_10_needle_method_matrix_scale_smoke`;
  phase `C5-F`.
* This is **eval/diagnostic only**. It is NOT a benchmark result, NOT a
  leaderboard entry, NOT a performance claim, NOT a promotion, NOT a
  default change, NOT a runtime/retriever/pack/backend change, NOT an
  EvidenceCore semantic change, and NOT a downstream agent value claim.
* It does NOT emit `winner`, `best_method`, `recommended_default`, or
  anything implying a policy/default decision. The fixed
  `baseline_method` is `bm25` and `baseline_is_policy_candidate` is
  always `false`.

Privacy / license boundary (binding):

* The `repoqa-2024-06-23.json.gz` release asset is downloaded to
  in-memory bytes (transient; NEVER written to workspace or committed)
  and decompressed in memory.
* Raw repo records, repo names/URLs, commit SHAs, entrypoint paths,
  topics, content, dependency, needle names/descriptions/paths/start/
  end lines, generated task/label/run JSONL, evidence rows, cloned
  repos, and stdout/stderr are kept **transient only** under `/tmp` or
  CI ephemeral workspace. They are NEVER committed or uploaded.
* RepoQA dataset license is unknown
  (`unknown_dataset_license`); row-level redistribution is disabled
  and derived row-level publication is disabled. Aggregate metrics
  publication is allowed as aggregate-only smoke
  (`aggregate_metrics_publication=aggregate_only_smoke`).

Network / CI policy (binding):

* Default no-network self-test passes without GitHub/network.
* Real smoke requires public network access to GitHub (asset download +
  repo clones). CI must be a separate explicit `workflow_dispatch`
  job with `enable_external_benchmark_network=true`. It must NOT run on
  PR/push by default, must use no provider secrets/vars, no provider
  model environment, and must upload only the aggregate report.

Run::

    python3 -m py_compile eval/c5f_repoqa_method_matrix_scale_smoke.py
    python3 eval/c5f_repoqa_method_matrix_scale_smoke.py --self-test
    python3 eval/c5f_repoqa_method_matrix_scale_smoke.py \\
        --needle-limit 10 --language-filter python --methods bm25,regex,symbol \\
        --out artifacts/c5f_repoqa_method_matrix_scale/\\
c5f_repoqa_method_matrix_scale_report.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, NoReturn

# Reuse C5-E helpers (which themselves reuse C5-D and C5-A primitives).
# The ``eval`` directory has no ``__init__.py`` (it is a flat script
# directory), so we add this file's parent to ``sys.path`` and import
# the C5-E module directly. C5-F does NOT import or mutate C5-C or
# C5-D directly; it only goes through C5-E.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
import c5e_repoqa_method_matrix_smoke as c5e  # noqa: E402

# ---------------------------------------------------------------------------
# Schema / claim constants (C5-F owned; distinct from C5-E)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "c5f_repoqa_method_matrix_scale_smoke.v1"
GENERATED_BY = "eval/c5f_repoqa_method_matrix_scale_smoke.py"
CLAIM_LEVEL = "repoqa_retrieval_method_matrix_scale_smoke_only"
MODE = "repoqa_bounded_10_needle_method_matrix_scale_smoke"
PHASE = "C5-F"

# C5-F pass status enum is distinct from C5-E's
# `repoqa_method_matrix_smoke_pass`.
STATUS_PASS = "repoqa_method_matrix_scale_smoke_pass"
STATUS_PARTIAL = c5e.STATUS_PARTIAL  # "partial"
STATUS_UNAVAILABLE = c5e.STATUS_UNAVAILABLE  # "unavailable_with_reason"
STATUS_FAIL_FORBIDDEN_SCAN = c5e.STATUS_FAIL_FORBIDDEN_SCAN
STATUS_FAIL_SCHEMA_CONTRACT = c5e.STATUS_FAIL_SCHEMA_CONTRACT

DEFAULT_OUT = Path(
    "artifacts/c5f_repoqa_method_matrix_scale/"
    "c5f_repoqa_method_matrix_scale_report.json"
)

# Hard caps on needle limit. Default 10; max 10 (C5-F is the scale
# smoke: it uses the full RepoQA Python needle budget in one run,
# capped at 10 — the C5-D hard cap).
NEEDLE_LIMIT_DEFAULT = 10
NEEDLE_LIMIT_HARD_CAP = 10

# Methods / language filter / baseline / query mode / gold target mode
# reuse C5-E.
ALLOWED_METHODS = c5e.ALLOWED_METHODS
DEFAULT_METHODS = c5e.DEFAULT_METHODS
BASELINE_METHOD = c5e.BASELINE_METHOD
ALLOWED_LANGUAGE_FILTERS = c5e.ALLOWED_LANGUAGE_FILTERS
DEFAULT_LANGUAGE_FILTER = c5e.DEFAULT_LANGUAGE_FILTER
QUERY_MODE = c5e.QUERY_MODE
GOLD_TARGET_MODE = c5e.GOLD_TARGET_MODE

# RepoQA release identifiers (reuse C5-E).
BENCHMARK = c5e.BENCHMARK
DATASET_RELEASE = c5e.DATASET_RELEASE

# Delta / method metric allowlists / recommendation fields / failure
# categories reuse C5-E.
DELTA_METRIC_ALLOWLIST = c5e.DELTA_METRIC_ALLOWLIST
METHOD_METRIC_ALLOWLIST = c5e.METHOD_METRIC_ALLOWLIST
FORBIDDEN_RECOMMENDATION_FIELDS = c5e.FORBIDDEN_RECOMMENDATION_FIELDS
FAILURE_CATEGORIES = c5e.FAILURE_CATEGORIES
LICENSE_FIELDS = dict(c5e.LICENSE_FIELDS)

# ---------------------------------------------------------------------------
# Safe booleans true (only when actually true). C5-F uses
# `repoqa_method_matrix_scale_smoke_performed` (distinct from C5-E's
# `repoqa_method_matrix_smoke_performed`) to reflect the scale-smoke
# contract.
# ---------------------------------------------------------------------------

SAFE_TRUE_FLAGS: dict[str, bool] = {
    "repoqa_method_matrix_scale_smoke_performed": False,
    "asset_downloaded_transiently": False,
    "repoqa_needles_parsed_in_memory": False,
    "repositories_materialized_transiently": False,
    "openlocus_retrieval_executed": False,
    "score_py_metrics_computed": False,
    "aggregate_only_public_artifact": True,
    "diagnostic_only": True,
}

# No-claim / no-runtime-change flags reuse C5-E.
DEFAULT_FALSE_FLAGS: dict[str, bool] = dict(c5e.DEFAULT_FALSE_FLAGS)


# ---------------------------------------------------------------------------
# C5-F scanner: reuses C5-E scanner with C5-F-specific safe value path
# last keys (adds the C5-F scale-smoke-performed flag name and the
# scale-smoke status enum).
# ---------------------------------------------------------------------------


C5F_SAFE_VALUE_PATH_LAST_KEYS: frozenset[str] = frozenset(
    c5e.C5E_SAFE_VALUE_PATH_LAST_KEYS
    | {
        "repoqa_method_matrix_scale_smoke_performed",
    }
)


def _c5f_safe_value_path(path: str) -> bool:
    """Check if a JSON path is a C5-F-specific safe value path."""
    last = path.rsplit(".", 1)[-1]
    last_key = last.split("[")[0]
    return last_key in C5F_SAFE_VALUE_PATH_LAST_KEYS


def _scan_c5f(obj: Any) -> list[dict[str, Any]]:
    """Combined C5-F scanner: C5-E primitives + C5-F-specific safe value
    path filtering.

    The C5-E scanner is reused for raw key/value leak detection + C5-E-
    specific checks (method_results shape, recommendation fields, RepoQA
    forbidden keys). C5-F ADDS only the C5-F-specific safe value path
    last keys so that the C5-F scale-smoke-performed flag name and the
    C5-F status enum pass the forbidden_field_name_value check.
    """
    violations: list[dict[str, Any]] = []
    for v in c5e._scan_c5e(obj):
        # Suppress C5-E false positives where a legitimate C5-F-specific
        # safe value appears as a value under a C5-F-specific safe value
        # path.
        if v.get("category") == "forbidden_field_name_value" and _c5f_safe_value_path(
            v.get("path", "")
        ):
            continue
        violations.append(v)
    return violations


def _c5f_forbidden_scan_summary(obj: Any) -> dict[str, Any]:
    """Run the C5-F forbidden scanner and return a sanitized summary."""
    violations = _scan_c5f(obj)
    categories: dict[str, int] = {}
    for v in violations:
        cat = v["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "categories": categories,
    }


def _enforce_c5f_no_forbidden(obj: Any) -> None:
    """Fail-closed guard: raise SystemExit if any forbidden content leaks."""
    scan = _c5f_forbidden_scan_summary(obj)
    if scan["status"] != "pass":
        raise SystemExit(
            "forbidden content leak; refusing to write artifact"
        )


# ---------------------------------------------------------------------------
# Helpers (reuse C5-E)
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return c5e._now_iso()


def _write_json(path: Path, obj: Any) -> None:
    c5e._write_json(path, obj)


def _check(name: str, ok: bool) -> dict[str, bool | str]:
    return c5e._check(name, ok)


def _validate_needle_limit(needle_limit: int) -> int:
    """Validate and cap --needle-limit to the C5-F hard cap (10)."""
    if not isinstance(needle_limit, int):
        raise SystemExit("invalid arguments")
    if needle_limit < 1:
        raise SystemExit("invalid arguments")
    if needle_limit > NEEDLE_LIMIT_HARD_CAP:
        return NEEDLE_LIMIT_HARD_CAP
    return needle_limit


# ---------------------------------------------------------------------------
# C5-F-owned report builders (mirror C5-E but with C5-F identity and
# C5-F scanner). These wrap the C5-E builders by post-processing the
# C5-E report to swap identity fields, the safe-true flag name, and
# re-run the C5-F scanner.
# ---------------------------------------------------------------------------


def _c5fy_report(report: dict[str, Any]) -> dict[str, Any]:
    """Post-process a C5-E report into a C5-F report.

    Swaps identity fields (schema_version, generated_by, claim_level,
    mode, phase), the pass status enum, and the safe-true flag name
    (`repoqa_method_matrix_smoke_performed` ->
    `repoqa_method_matrix_scale_smoke_performed`). All other fields
    (metrics, deltas, failure counts, license fields, no-claim flags)
    are preserved unchanged.
    """
    out = dict(report)
    out["schema_version"] = SCHEMA_VERSION
    out["generated_by"] = GENERATED_BY
    out["claim_level"] = CLAIM_LEVEL
    out["mode"] = MODE
    out["phase"] = PHASE
    # Swap pass status enum.
    if out.get("status") == c5e.STATUS_PASS:
        out["status"] = STATUS_PASS
    # Swap per-method pass status enum for the public C5-F artifact. The
    # C5-E builder computes status/metrics before this post-processing step,
    # so this does not affect aggregation; it only avoids publishing C5-E's
    # phase-specific pass enum inside a C5-F report.
    method_results = out.get("method_results")
    if isinstance(method_results, list):
        converted_results: list[Any] = []
        for rec in method_results:
            if isinstance(rec, dict):
                rec2 = dict(rec)
                if rec2.get("status") == c5e.STATUS_PASS:
                    rec2["status"] = STATUS_PASS
                converted_results.append(rec2)
            else:
                converted_results.append(rec)
        out["method_results"] = converted_results
    # Swap safe-true flag name.
    if "repoqa_method_matrix_smoke_performed" in out:
        out["repoqa_method_matrix_scale_smoke_performed"] = out.pop(
            "repoqa_method_matrix_smoke_performed"
        )
    # Swap signal_strength strings.
    framing = out.get("framing", {})
    if isinstance(framing, dict):
        ss = framing.get("signal_strength", "")
        if isinstance(ss, str):
            if "repoqa_method_matrix_smoke_unavailable" in ss:
                framing["signal_strength"] = (
                    "repoqa_method_matrix_scale_smoke_unavailable"
                )
            elif "repoqa_method_matrix_smoke_schema_contract_failure" in ss:
                framing["signal_strength"] = (
                    "repoqa_method_matrix_scale_smoke_schema_contract_failure"
                )
            elif "repoqa_method_matrix_smoke_aggregate_only" in ss:
                framing["signal_strength"] = (
                    "repoqa_method_matrix_scale_smoke_aggregate_only"
                )
        out["framing"] = framing
    # Re-run C5-F scanner (fail-closed).
    scan = _c5f_forbidden_scan_summary(out)
    out["forbidden_scan"] = scan
    if scan["status"] != "pass":
        out["status"] = STATUS_FAIL_FORBIDDEN_SCAN
    return out


def _build_unavailable_report(
    failure_reason_category: str,
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    methods: list[str],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    needles_seen: int = 0,
    network_calls: int = 0,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a truthful `unavailable_with_reason` report (C5-F identity)."""
    c5e_report = c5e._build_unavailable_report(
        failure_reason_category,
        self_test_passed=self_test_passed,
        needle_limit_requested=needle_limit_requested,
        methods=methods,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        needles_seen=needles_seen,
        network_calls=network_calls,
        failure_category_counts=failure_category_counts,
    )
    return _c5fy_report(c5e_report)


def _build_schema_contract_failure(
    reason: str,
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    methods: list[str],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    failure_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a `fail_schema_contract` report (C5-F identity)."""
    c5e_report = c5e._build_schema_contract_failure(
        reason,
        self_test_passed=self_test_passed,
        needle_limit_requested=needle_limit_requested,
        methods=methods,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        failure_category_counts=failure_category_counts,
    )
    return _c5fy_report(c5e_report)


def _build_matrix_report(
    *,
    self_test_passed: bool,
    needle_limit_requested: int,
    needles_seen: int,
    methods: list[str],
    method_results: list[dict[str, Any]],
    language_filter: str,
    openlocus_binary_source: str,
    network_mode: str,
    network_calls: int,
    failure_category_counts: dict[str, int],
) -> dict[str, Any]:
    """Build a pass/partial matrix report (C5-F identity)."""
    c5e_report = c5e._build_matrix_report(
        self_test_passed=self_test_passed,
        needle_limit_requested=needle_limit_requested,
        needles_seen=needles_seen,
        methods=methods,
        method_results=method_results,
        language_filter=language_filter,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        network_calls=network_calls,
        failure_category_counts=failure_category_counts,
    )
    return _c5fy_report(c5e_report)


# ---------------------------------------------------------------------------
# Matrix network smoke runner (reuse C5-E runner, then C5-F-ify the
# report).
# ---------------------------------------------------------------------------


def _run_matrix_smoke(
    *,
    needle_limit: int,
    methods: list[str],
    language_filter: str,
    openlocus_bin: str,
    openlocus_binary_source: str,
    network_mode: str,
    eval_dir: Path,
    self_test_passed: bool,
) -> dict[str, Any]:
    """Run the real RepoQA matrix network smoke, then C5-F-ify the report."""
    c5e_report = c5e._run_matrix_smoke(
        needle_limit=needle_limit,
        methods=methods,
        language_filter=language_filter,
        openlocus_bin=openlocus_bin,
        openlocus_binary_source=openlocus_binary_source,
        network_mode=network_mode,
        eval_dir=eval_dir,
        self_test_passed=self_test_passed,
    )
    return _c5fy_report(c5e_report)


# ---------------------------------------------------------------------------
# Self-test (no network; synthetic data). Reuses C5-E self-test structure
# but with C5-F identity assertions.
# ---------------------------------------------------------------------------


def _build_synthetic_method_metrics(
    method: str = "bm25",
) -> dict[str, Any]:
    return c5e._build_synthetic_method_metrics(method)


def _status_from_method_results(method_results: list[dict[str, Any]]) -> str:
    """Return the C5-F top-level status for C5-F-shaped method records."""
    c5e_results: list[dict[str, Any]] = []
    for rec in method_results:
        rec2 = dict(rec)
        if rec2.get("status") == STATUS_PASS:
            rec2["status"] = c5e.STATUS_PASS
        c5e_results.append(rec2)
    status = c5e._status_from_method_results(c5e_results)
    if status == c5e.STATUS_PASS:
        return STATUS_PASS
    return status


def run_self_test_checks() -> tuple[list[dict[str, Any]], bool]:
    """Run all C5-F self-test groups (no network; synthetic data)."""
    checks: list[dict[str, Any]] = []

    # --- Group 1: Artifact identity fields. ---
    method_results = [
        {
            "method": "bm25",
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {c: 0 for c in FAILURE_CATEGORIES},
            "aggregate_runtime_seconds": 12.0,
        },
        {
            "method": "regex",
            "status": c5e.STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("regex"),
            "failure_category_counts": {c: 0 for c in FAILURE_CATEGORIES},
            "aggregate_runtime_seconds": 10.0,
        },
    ]
    skeleton = _build_matrix_report(
        self_test_passed=True,
        needle_limit_requested=10,
        needles_seen=10,
        methods=["bm25", "regex", "symbol"],
        method_results=method_results,
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
        network_calls=1,
        failure_category_counts={c: 0 for c in FAILURE_CATEGORIES},
    )
    checks.append(
        _check(
            "schema_version_correct",
            skeleton["schema_version"] == SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "claim_level_correct",
            skeleton["claim_level"] == CLAIM_LEVEL,
        )
    )
    checks.append(_check("mode_correct", skeleton["mode"] == MODE))
    checks.append(_check("phase_correct", skeleton["phase"] == PHASE))
    checks.append(
        _check(
            "generated_by_correct",
            skeleton["generated_by"] == GENERATED_BY,
        )
    )
    checks.append(
        _check(
            "benchmark_correct",
            skeleton["benchmark"] == BENCHMARK,
        )
    )
    checks.append(
        _check(
            "dataset_release_correct",
            skeleton["dataset_release"] == DATASET_RELEASE,
        )
    )
    checks.append(
        _check(
            "query_mode_correct",
            skeleton["query_mode"] == QUERY_MODE,
        )
    )
    checks.append(
        _check(
            "gold_target_mode_correct",
            skeleton["gold_target_mode"] == GOLD_TARGET_MODE,
        )
    )
    checks.append(
        _check(
            "status_pass_when_self_test_passed",
            skeleton["status"] == STATUS_PASS,
        )
    )
    checks.append(
        _check(
            "status_pass_enum_is_repoqa_method_matrix_scale_smoke_pass",
            STATUS_PASS == "repoqa_method_matrix_scale_smoke_pass",
        )
    )

    # --- Group 2: Safe true flags (C5-F-specific name). ---
    checks.append(
        _check(
            "safe_true_repoqa_method_matrix_scale_smoke_performed",
            skeleton.get("repoqa_method_matrix_scale_smoke_performed") is True,
        )
    )
    checks.append(
        _check(
            "no_c5e_repoqa_method_matrix_smoke_performed_flag",
            "repoqa_method_matrix_smoke_performed" not in skeleton,
        )
    )
    for flag in (
        "asset_downloaded_transiently",
        "repoqa_needles_parsed_in_memory",
        "repositories_materialized_transiently",
        "openlocus_retrieval_executed",
        "score_py_metrics_computed",
        "aggregate_only_public_artifact",
        "diagnostic_only",
    ):
        checks.append(
            _check(
                f"safe_true_{flag}_present",
                flag in skeleton,
            )
        )
    checks.append(
        _check(
            "safe_true_aggregate_only_public_artifact",
            skeleton.get("aggregate_only_public_artifact") is True,
        )
    )
    checks.append(
        _check(
            "safe_true_diagnostic_only",
            skeleton.get("diagnostic_only") is True,
        )
    )

    # --- Group 3: No-claim / no-runtime-change false flags. ---
    for flag in DEFAULT_FALSE_FLAGS:
        checks.append(
            _check(
                f"no_claim_{flag}_false",
                skeleton.get(flag) is False,
            )
        )

    # --- Group 4: License fields. ---
    checks.append(
        _check(
            "license_dataset_license_status",
            skeleton.get("dataset_license_status")
            == "unknown_dataset_license",
        )
    )
    checks.append(
        _check(
            "license_row_level_redistribution_allowed_false",
            skeleton.get("row_level_redistribution_allowed") is False,
        )
    )
    checks.append(
        _check(
            "license_derived_row_level_publication_allowed_false",
            skeleton.get("derived_row_level_publication_allowed")
            is False,
        )
    )
    checks.append(
        _check(
            "license_aggregate_metrics_publication",
            skeleton.get("aggregate_metrics_publication")
            == "aggregate_only_smoke",
        )
    )

    # --- Group 5: Needle limit hard cap 10 (C5-F default is 10). ---
    checks.append(
        _check("needle_limit_default_10", NEEDLE_LIMIT_DEFAULT == 10)
    )
    checks.append(
        _check("needle_limit_hard_cap_10", NEEDLE_LIMIT_HARD_CAP == 10)
    )
    checks.append(
        _check(
            "needle_limit_cap_enforced_at_10",
            _validate_needle_limit(100) == 10,
        )
    )
    checks.append(
        _check(
            "needle_limit_passes_through_at_10",
            _validate_needle_limit(10) == 10,
        )
    )
    try:
        _validate_needle_limit(0)
        checks.append(_check("needle_limit_rejects_zero", False))
    except SystemExit:
        checks.append(_check("needle_limit_rejects_zero", True))

    # --- Group 6: Method parser (reuse C5-E parser). ---
    # rejects unknown methods.
    try:
        c5e.parse_methods("bm25,unknown,symbol")
        checks.append(_check("method_parser_rejects_unknown", False))
    except c5e.MethodConfigError:
        checks.append(_check("method_parser_rejects_unknown", True))
    # rejects text method.
    try:
        c5e.parse_methods("bm25,text,symbol")
        checks.append(_check("method_parser_rejects_text_method", False))
    except c5e.MethodConfigError:
        checks.append(_check("method_parser_rejects_text_method", True))
    # default methods exactly bm25,regex,symbol.
    checks.append(
        _check(
            "default_methods_exact",
            list(DEFAULT_METHODS) == ["bm25", "regex", "symbol"],
        )
    )
    # deduplicates duplicates deterministically.
    checks.append(
        _check(
            "method_parser_dedups_duplicates",
            c5e.parse_methods("bm25,bm25,regex,regex,symbol,symbol")
            == ["bm25", "regex", "symbol"],
        )
    )

    # --- Group 7: ALLOWED_METHODS exactly bm25,regex,symbol. ---
    checks.append(
        _check(
            "allowed_methods_exact",
            ALLOWED_METHODS == ("bm25", "regex", "symbol"),
        )
    )
    checks.append(
        _check(
            "allowed_methods_excludes_text",
            "text" not in ALLOWED_METHODS,
        )
    )

    # --- Group 8: method_results list shape, not dict keyed by method. ---
    checks.append(
        _check(
            "method_results_is_list",
            isinstance(skeleton.get("method_results"), list),
        )
    )
    # Scanner rejects method_results as dict.
    checks.append(
        _check(
            "scanner_rejects_method_results_as_dict",
            bool(_scan_c5f({"method_results": {"vector": {"metrics": {}}}})),
        )
    )
    # Scanner rejects method_result_record_method_not_allowlisted.
    checks.append(
        _check(
            "scanner_rejects_method_result_record_method_not_allowlisted",
            bool(
                _scan_c5f(
                    {"method_results": [{"method": "vector", "metrics": {}}]}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_method_result_record_text_method",
            bool(
                _scan_c5f(
                    {"method_results": [{"method": "text", "metrics": {}}]}
                )
            ),
        )
    )

    # --- Group 9: Metric allowlist. ---
    # Method metric allowlist is a subset of C5-D score allowlist.
    for k in METHOD_METRIC_ALLOWLIST:
        checks.append(
            _check(
                f"method_metric_allowlist_subset_of_c5d_{k}",
                k in c5e.c5d.SCORE_METRIC_ALLOWLIST,
            )
        )

    # --- Group 10: Baseline deltas vs bm25. ---
    deltas = skeleton.get("smoke_metric_deltas_vs_baseline", [])
    checks.append(
        _check(
            "deltas_excludes_baseline_method",
            isinstance(deltas, list)
            and all(d.get("method") != BASELINE_METHOD for d in deltas),
        )
    )
    checks.append(
        _check(
            "deltas_only_for_allowlisted_metrics",
            isinstance(deltas, list)
            and all(
                d.get("metric") in DELTA_METRIC_ALLOWLIST
                and set(d.keys())
                == {"baseline_method", "method", "metric", "delta"}
                for d in deltas
            ),
        )
    )
    checks.append(
        _check(
            "deltas_baseline_method_is_bm25",
            BASELINE_METHOD == "bm25",
        )
    )

    # --- Group 11: No winner/best_method/recommended_default. ---
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"scanner_rejects_{field}_key",
                bool(_scan_c5f({field: "bm25"})),
            )
        )
    for field in FORBIDDEN_RECOMMENDATION_FIELDS:
        checks.append(
            _check(
                f"clean_report_missing_{field}",
                field not in skeleton,
            )
        )
    checks.append(
        _check(
            "clean_report_baseline_is_policy_candidate_false",
            skeleton.get("baseline_is_policy_candidate") is False,
        )
    )
    checks.append(
        _check(
            "clean_report_default_should_change_false",
            skeleton.get("default_should_change") is False,
        )
    )

    # --- Group 12: Fixed failure-category aggregation. ---
    fcc = skeleton.get("failure_category_counts", {})
    checks.append(
        _check(
            "failure_category_counts_is_dict",
            isinstance(fcc, dict),
        )
    )
    # All keys are in the FAILURE_CATEGORIES enum.
    checks.append(
        _check(
            "failure_category_counts_keys_in_enum",
            isinstance(fcc, dict)
            and all(k in FAILURE_CATEGORIES for k in fcc.keys()),
        )
    )

    # --- Group 13: Scanner rejects forbidden row-level/provider/default strings. ---
    for forbidden_key in (
        "repo", "commit_sha", "entrypoint_path", "topic", "content",
        "dependency", "needles", "needle", "needle_name", "needle_path",
        "needle_description", "needle_id", "name", "start_line", "end_line",
        "start_byte", "end_byte", "global_start_line", "global_end_line",
        "global_start_byte", "global_end_byte", "code_ratio", "path",
        "description", "row", "repo_name", "repo_slug", "repo_url",
        "base_commit", "instance_id", "task_id", "query", "query_text",
        "problem_statement", "gold", "gold_path", "gold_span",
        "gold_snippet", "gold_paths", "gold_lines", "gold_context",
        "snippet", "snippets", "content_sha", "stdout", "stderr",
        "stdout_text", "stderr_text", "evidence", "evidence_row",
        "evidence_rows", "retrieved_path", "retrieved_paths",
        "retrieved_snippet", "cloned_repo_path", "cloned_repo",
        "per_row_metrics", "row_metrics", "per_needle_metrics",
        "needle_metrics", "patch", "diff",
    ):
        checks.append(
            _check(
                f"scanner_rejects_{forbidden_key}_key",
                bool(_scan_c5f({forbidden_key: "value"})),
            )
        )
    # Value patterns.
    checks.append(
        _check(
            "scanner_rejects_repo_url_value",
            bool(_scan_c5f({"leaked": "https://github.com/foo/bar"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_repo_slug_value",
            bool(_scan_c5f({"leaked": "psf/black"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_commit_sha_value",
            bool(
                _scan_c5f(
                    {"leaked": "f03ee113c9f3dfeb477f2d4247bfb7de2e5f465c"}
                )
            ),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_file_path_value",
            bool(_scan_c5f({"leaked": "src/black/trans.py"})),
        )
    )
    checks.append(
        _check(
            "scanner_rejects_line_range_value",
            bool(_scan_c5f({"leaked": "585-639"})),
        )
    )

    # --- Group 14: Scanner allows safe values. ---
    checks.append(
        _check(
            "scanner_allows_benchmark_value",
            not _scan_c5f({"benchmark": "repoqa"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_dataset_release_value",
            not _scan_c5f({"dataset_release": "repoqa-2024-06-23"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_baseline_method_value",
            not _scan_c5f({"baseline_method": "bm25"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_language_filter_value",
            not _scan_c5f({"language_filter": "python"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_query_mode_value",
            not _scan_c5f({"query_mode": "needle_description"}),
        )
    )
    checks.append(
        _check(
            "scanner_allows_gold_target_mode_value",
            not _scan_c5f({"gold_target_mode": "needle_path_line_range"}),
        )
    )

    # --- Group 15: Status semantics. ---
    all_pass_results = [
        {
            "method": "bm25",
            "status": STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("regex"),
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_pass_when_all_methods_succeed",
            _status_from_method_results(all_pass_results) == STATUS_PASS,
        )
    )
    mixed_results = [
        {
            "method": "bm25",
            "status": STATUS_PASS,
            "needles_evaluated": 10,
            "needles_successful": 10,
            "needles_failed": 0,
            "metrics": _build_synthetic_method_metrics("bm25"),
            "failure_category_counts": {},
        },
        {
            "method": "regex",
            "status": STATUS_UNAVAILABLE,
            "needles_evaluated": 10,
            "needles_successful": 0,
            "needles_failed": 10,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_partial_when_mixed",
            _status_from_method_results(mixed_results) == STATUS_PARTIAL,
        )
    )
    none_results = [
        {
            "method": "bm25",
            "status": STATUS_UNAVAILABLE,
            "needles_evaluated": 10,
            "needles_successful": 0,
            "needles_failed": 10,
            "metrics": {},
            "failure_category_counts": {},
        },
    ]
    checks.append(
        _check(
            "status_unavailable_when_none_succeed",
            _status_from_method_results(none_results) == STATUS_UNAVAILABLE,
        )
    )
    checks.append(
        _check(
            "status_unavailable_when_empty",
            _status_from_method_results([]) == STATUS_UNAVAILABLE,
        )
    )

    # --- Group 16: Unavailable report. ---
    unavail = _build_unavailable_report(
        "asset_download_failed",
        self_test_passed=True,
        needle_limit_requested=10,
        methods=["bm25", "regex", "symbol"],
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "unavailable_status",
            unavail["status"] == STATUS_UNAVAILABLE,
        )
    )
    checks.append(
        _check(
            "unavailable_no_repoqa_method_matrix_scale_smoke_performed_flag",
            unavail["repoqa_method_matrix_scale_smoke_performed"] is False,
        )
    )
    checks.append(
        _check(
            "unavailable_no_deltas",
            unavail["smoke_metric_deltas_vs_baseline"] == [],
        )
    )
    checks.append(
        _check(
            "unavailable_forbidden_scan_pass",
            unavail["forbidden_scan"]["status"] == "pass",
        )
    )

    # --- Group 17: Schema contract failure. ---
    schema_fail = _build_schema_contract_failure(
        "method_result_record_invalid",
        self_test_passed=True,
        needle_limit_requested=10,
        methods=["bm25", "regex", "symbol"],
        language_filter="python",
        openlocus_binary_source="default",
        network_mode="local_explicit",
    )
    checks.append(
        _check(
            "schema_contract_failure_status",
            schema_fail["status"] == STATUS_FAIL_SCHEMA_CONTRACT,
        )
    )
    checks.append(
        _check(
            "schema_contract_failure_no_method_results",
            schema_fail["method_results"] == [],
        )
    )

    # --- Group 18: Fail-closed generation. ---
    try:
        _enforce_c5f_no_forbidden(skeleton)
        checks.append(_check("fail_closed_clean_report_no_raise", True))
    except SystemExit:
        checks.append(_check("fail_closed_clean_report_no_raise", False))

    leaked_report = dict(skeleton)
    leaked_report["leaked_repo"] = "psf/black"
    try:
        _enforce_c5f_no_forbidden(leaked_report)
        checks.append(_check("fail_closed_leaked_repo_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_leaked_repo_raises", True))

    leaked_report2 = dict(skeleton)
    leaked_report2["best_method"] = "regex"
    try:
        _enforce_c5f_no_forbidden(leaked_report2)
        checks.append(_check("fail_closed_best_method_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_best_method_raises", True))

    leaked_report3 = dict(skeleton)
    leaked_report3["winner"] = "symbol"
    try:
        _enforce_c5f_no_forbidden(leaked_report3)
        checks.append(_check("fail_closed_winner_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_winner_raises", True))

    leaked_report4 = dict(skeleton)
    leaked_report4["recommended_default"] = "bm25"
    try:
        _enforce_c5f_no_forbidden(leaked_report4)
        checks.append(_check("fail_closed_recommended_default_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_recommended_default_raises", True))

    leaked_report5 = dict(skeleton)
    leaked_report5["commit_sha"] = "0" * 40
    try:
        _enforce_c5f_no_forbidden(leaked_report5)
        checks.append(_check("fail_closed_commit_sha_raises", False))
    except SystemExit:
        checks.append(_check("fail_closed_commit_sha_raises", True))

    failed_self_test_report = dict(skeleton)
    failed_self_test_report["self_test_passed"] = False
    try:
        c5e.c5d.c5a._refuse_on_self_test_failure(failed_self_test_report)
        checks.append(_check("refuse_on_self_test_failure_raises", False))
    except SystemExit:
        checks.append(_check("refuse_on_self_test_failure_raises", True))

    # --- Group 19: Public artifact self-scan is clean. ---
    checks.append(
        _check(
            "public_artifact_self_scan_clean",
            not _scan_c5f(skeleton),
        )
    )
    checks.append(
        _check(
            "unavailable_self_scan_clean",
            not _scan_c5f(unavail),
        )
    )

    # --- Group 20: CLI argument surface. ---
    parser = build_parser()
    option_strings: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            option_strings.add(opt)
    for required_opt in (
        "--self-test",
        "--needle-limit",
        "--methods",
        "--language-filter",
        "--openlocus",
        "--out",
    ):
        checks.append(
            _check(
                f"cli_has_option_{required_opt}",
                required_opt in option_strings,
            )
        )

    # --- Group 21: C5-F distinct identity from C5-E. ---
    checks.append(
        _check(
            "c5f_schema_version_distinct_from_c5e",
            SCHEMA_VERSION != c5e.SCHEMA_VERSION,
        )
    )
    checks.append(
        _check(
            "c5f_claim_level_distinct_from_c5e",
            CLAIM_LEVEL != c5e.CLAIM_LEVEL,
        )
    )
    checks.append(
        _check(
            "c5f_mode_distinct_from_c5e",
            MODE != c5e.MODE,
        )
    )
    checks.append(
        _check(
            "c5f_phase_distinct_from_c5e",
            PHASE != c5e.PHASE,
        )
    )
    checks.append(
        _check(
            "c5f_status_pass_distinct_from_c5e",
            STATUS_PASS != c5e.STATUS_PASS,
        )
    )
    checks.append(
        _check(
            "c5f_default_out_distinct_from_c5e",
            str(DEFAULT_OUT) != str(c5e.DEFAULT_OUT),
        )
    )
    checks.append(
        _check(
            "c5f_needle_limit_default_10_distinct_from_c5e_5",
            NEEDLE_LIMIT_DEFAULT == 10 and c5e.NEEDLE_LIMIT_DEFAULT == 5,
        )
    )

    all_passed = all(c["passed"] for c in checks)
    return checks, all_passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class SafeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that never echoes unknown/private-looking args."""

    def error(self, message: str) -> NoReturn:  # noqa: D401
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the C5-F CLI parser."""
    ap = SafeArgumentParser(
        description=(
            "C5-F RepoQA 10-needle method-matrix scale smoke "
            "(public aggregate-only artifact; bounded 10-needle RepoQA "
            "Python needle subset per method; transient /tmp asset "
            "download + clone + retrieval + score; methods "
            "bm25,regex,symbol only; no provider calls; no raw "
            "repo/commit/path/description/line/source/needle IDs/row "
            "IDs/hashes/winner/best_method/recommended_default "
            "committed)."
        )
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic self-test groups and exit (no artifact written, no network)",
    )
    ap.add_argument(
        "--needle-limit",
        type=int,
        default=NEEDLE_LIMIT_DEFAULT,
        help=(
            "number of RepoQA Python needles to evaluate per method "
            "(default: " f"{NEEDLE_LIMIT_DEFAULT}; hard cap "
            f"{NEEDLE_LIMIT_HARD_CAP})"
        ),
    )
    ap.add_argument(
        "--methods",
        default=None,
        help=(
            "comma-separated OpenLocus retrieval methods (default: "
            f"{','.join(DEFAULT_METHODS)}; allowed: "
            f"{', '.join(ALLOWED_METHODS)}; duplicates are deduplicated "
            "deterministically; text is NOT allowed in C5-F)"
        ),
    )
    ap.add_argument(
        "--language-filter",
        default=DEFAULT_LANGUAGE_FILTER,
        choices=ALLOWED_LANGUAGE_FILTERS,
        help=(
            "language filter category (default: python; allowed: "
            f"{', '.join(ALLOWED_LANGUAGE_FILTERS)}; C5-F does NOT "
            "silently fall back to all languages)"
        ),
    )
    ap.add_argument(
        "--openlocus",
        default=None,
        help=(
            "OpenLocus binary path (default: target/release/openlocus "
            "then target/debug/openlocus fallback)"
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "output artifact JSON path (default: committed public "
            "aggregate-only artifact)"
        ),
    )
    return ap


def main() -> None:
    import subprocess

    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        checks, passed = run_self_test_checks()
        for c in checks:
            tag = "PASS" if c["passed"] else "FAIL"
            print(f"[{tag}] {c['check']}")
        passed_count = sum(1 for c in checks if c["passed"])
        print(
            f"self_test_passed={passed} "
            f"({passed_count}/{len(checks)} checks)"
        )
        sys.exit(0 if passed else 1)

    # Parse methods (raises MethodConfigError on invalid config).
    try:
        methods = c5e.parse_methods(args.methods)
    except c5e.MethodConfigError:
        report = _build_schema_contract_failure(
            "method_config_invalid",
            self_test_passed=False,
            needle_limit_requested=args.needle_limit,
            methods=[],
            language_filter=args.language_filter,
            openlocus_binary_source="missing",
            network_mode="local_explicit",
        )
        _write_json(args.out, report)
        sys.exit(1)

    needle_limit = _validate_needle_limit(args.needle_limit)
    language_filter = args.language_filter
    out_path = args.out if args.out is not None else DEFAULT_OUT

    # Self-test must pass before any artifact is written.
    checks, self_test_passed = run_self_test_checks()
    if not self_test_passed:
        print(
            "error: self-test failed; refusing to write artifact",
            file=sys.stderr,
        )
        for c in checks:
            if not c["passed"]:
                print(f"  FAIL: {c['check']}", file=sys.stderr)
        sys.exit(1)

    # Resolve OpenLocus binary.
    openlocus_bin, openlocus_source = c5e.c5d.c5a._resolve_openlocus_binary(
        args.openlocus
    )
    if openlocus_bin is None:
        report = _build_unavailable_report(
            "retrieval_failed",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode="local_explicit",
        )
        _enforce_c5f_no_forbidden(report)
        _write_json(out_path, report)
        print(
            f"wrote artifact "
            f"(forbidden_scan={report['forbidden_scan']['status']}, "
            f"self_test_passed={report['self_test_passed']}, "
            f"status={report['status']}, "
            f"phase={report['phase']}, "
            f"methods={report['methods_requested']}, "
            f"failure_reason={report['failure_reason_category']})"
        )
        return

    network_mode = "local_explicit"
    eval_dir = Path(__file__).resolve().parent
    try:
        report = _run_matrix_smoke(
            needle_limit=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_bin=openlocus_bin,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
            eval_dir=eval_dir,
            self_test_passed=self_test_passed,
        )
    except (OSError, subprocess.SubprocessError):
        report = _build_unavailable_report(
            "unexpected_exception",
            self_test_passed=self_test_passed,
            needle_limit_requested=needle_limit,
            methods=methods,
            language_filter=language_filter,
            openlocus_binary_source=openlocus_source,
            network_mode=network_mode,
        )

    _enforce_c5f_no_forbidden(report)
    _write_json(out_path, report)
    print(
        f"wrote artifact "
        f"(forbidden_scan={report['forbidden_scan']['status']}, "
        f"self_test_passed={report['self_test_passed']}, "
        f"status={report['status']}, "
        f"phase={report['phase']}, "
        f"methods={report['methods_requested']}, "
        f"methods_successful={report['methods_successful']}, "
        f"needles_seen={report['needles_seen']})"
    )


if __name__ == "__main__":
    main()
