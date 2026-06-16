#!/usr/bin/env python3
"""P57 Generalization Gate v0.

P57 is a deterministic, no-live-LLM, no-provider aggregate-only
generalization-readiness gate. It runs after P51B and consumes only existing
upstream aggregate report JSON. It does NOT read source files, candidate pools,
tasks, snippets, prompts, responses, repo locks, or provider configs.

P57 is NOT quality evidence, NOT a promotion/default gate, and NOT live
readiness. It checks safety/completeness/availability across existing diagnostic
reports. For single-slice/self-test runs it reports `insufficient_matrix` rather
than success.

Hard constraints:
* No remote or LLM calls by P57 (`remote_calls_by_p57=0`, `llm_calls_by_p57=0`).
* No prompt construction (`prompt_construction_by_p57=false`).
* No source reads by P57 (`source_reads_attempted_by_p57=false`).
* Public output contains no paths, repo/dataset/task/candidate identifiers,
  spans, digests, queries, snippets, prompts, responses, providers, models,
  URLs, or keys.
* Aggregate-only counts copied from upstream reports.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p57-generalization-gate-v0"
GENERATED_BY = "p57_generalization_gate"
STAGE = "P57 Generalization Gate v0"

DEFAULT_OUT = Path("artifacts/p57_generalization_gate/p57_generalization_gate_report.json")
DEFAULT_DOC = Path("docs/en/p57-generalization-gate.md")

REQUIRED_PHASES = [
    "p46", "p47", "p48", "p49", "p50", "p52", "p52a", "p52b", "p52c", "p51b"
]
OPTIONAL_PHASES = ["p51"]

MIN_REQUIRED_SLICES = 4
MIN_REQUIRED_REPOS = 3
MIN_TASKS_PER_SLICE = 6

ALLOWED_STATUS = {
    "blocked_safety",
    "insufficient_matrix",
    "diagnostic_matrix_complete",
    "diagnostic_matrix_unstable",
}

ALLOWED_UPSTREAM_STATUS = {
    "ok",
    "self_test_only",
    "insufficient_matrix",
    "diagnostic_matrix_complete",
    "diagnostic_matrix_unstable",
    "blocked_safety",
}

# Exact public forbidden keys. Safety flags that contain these substrings but are
# required (e.g. raw_paths_in_artifact) are not exact matches and therefore allowed.
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
    "query",
    "snippet",
    "prompt",
    "response",
    "provider",
    "model",
    "base_url",
    "api_key",
    "repo_lock",
    "source_root",
    "tasks",
    "records",
    "per_task_results",
    "per_candidate_results",
    "per_slice_rows",
}

# Additional keys that are allowed even if they would otherwise match the exact
# forbidden set (none currently do, but this makes future key renames safer).
P57_SAFETY_FLAG_KEYS = {
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "score_phase_only_metrics",
    "aggregate_only_public_artifact",
    "remote_calls_by_p57",
    "llm_calls_by_p57",
    "prompt_construction_by_p57",
    "source_reads_attempted_by_p57",
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
    "upstream_safety_gate",
    "generalization_matrix",
    "blockers",
    "warnings",
    "conclusion",
    "validation",
    # input_summary sub-keys
    "required_reports",
    "optional_reports",
    "required_present_count",
    "optional_present_count",
    "required_missing",
    "slice_count",
    "slice_count_with_all_required_reports",
    "self_test_slice_count",
    "included_generalization_slice_count",
    "matrix_requirement_summary",
    # upstream_safety_gate sub-keys
    "checked_count",
    "blocker_count",
    "warning_count",
    "by_phase",
    "phase",
    "report_present",
    "safety_blocker",
    "safety_warnings",
    "promotion_default_false",
    "candidate_not_fact_true",
    "aggregate_only_true",
    "remote_calls_zero",
    "llm_calls_zero",
    "prompt_construction_false",
    "source_reads_not_attempted_or_bounded",
    # generalization_matrix sub-keys
    "readiness_status",
    "required_slice_count",
    "required_min_repo_count",
    "observed_slice_count",
    "observed_repo_count",
    "observed_task_count_aggregate",
    "per_phase_availability",
    "per_phase_status_summary",
    "dispersion",
    "worst_slice_task_count",
    "worst_slice_required_reports_missing",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "coverage_summary",
    "availability",
}

# Map each phase to the top-level safety keys P57 checks.
PHASE_SAFETY = {
    "p46": {
        "remote": "remote_calls_by_p46",
        "llm": "llm_calls_by_p46",
        "prompt": "prompt_construction_by_p46",
        "source_reads": "source_reads_attempted_by_p46",
        "source_bounded": None,
    },
    "p47": {
        "remote": "remote_calls_by_p47",
        "llm": "llm_calls_by_p47",
        "prompt": "prompt_construction_by_p47",
        "source_reads": "source_reads_attempted_by_p47",
        "source_bounded": None,
    },
    "p48": {
        "remote": "remote_calls_by_p48",
        "llm": "llm_calls_by_p48",
        "prompt": "prompt_construction_by_p48",
        "source_reads": "source_reads_attempted_by_p48",
        "source_bounded": None,
    },
    "p49": {
        "remote": "remote_calls_by_p49",
        "llm": "llm_calls_by_p49",
        "prompt": "prompt_construction_by_p49",
        "source_reads": "source_reads_attempted_by_p49",
        "source_bounded": None,
    },
    "p50": {
        "remote": "remote_calls_by_p50",
        "llm": "llm_calls_by_p50",
        "prompt": "prompt_construction_by_p50",
        "source_reads": "source_reads_attempted_by_p50",
        "source_bounded": None,
    },
    "p52": {
        "remote": "remote_calls_by_p52",
        "llm": "llm_calls_by_p52",
        "prompt": "prompt_construction_by_p52",
        "source_reads": "source_reads_attempted_by_p52",
        "source_bounded": None,
    },
    "p52a": {
        "remote": "remote_calls_by_p52a",
        "llm": "llm_calls_by_p52a",
        "prompt": "prompt_construction_by_p52a",
        "source_reads": "source_reads_attempted_by_p52a",
        "source_bounded": "source_reads_bounded_by_p52a",
    },
    "p52b": {
        "remote": "remote_calls_by_p52b",
        "llm": "llm_calls_by_p52b",
        "prompt": "prompt_construction_by_p52b",
        "source_reads": "source_reads_attempted_by_p52b",
        "source_bounded": "source_reads_bounded_by_p52b",
    },
    "p52c": {
        "remote": "remote_calls_by_p52c",
        "llm": "llm_calls_by_p52c",
        "prompt": "prompt_construction_by_p52c",
        "source_reads": "source_reads_attempted_by_p52c",
        "source_bounded": "source_reads_bounded_by_p52c",
    },
    "p51": {
        "remote": "remote_calls_by_p51",
        "llm": "llm_calls_by_p51",
        "prompt": "prompt_construction_by_p51",
        "source_reads": "source_reads_attempted_by_p51",
        "source_bounded": None,
    },
    "p51b": {
        "remote": "remote_calls_by_p51b",
        "llm": "llm_calls_by_p51b",
        "prompt": "prompt_construction_by_p51b",
        "source_reads": "source_reads_attempted_by_p51b",
        "source_bounded": None,
        "extra": {
            "remote_requests_by_p51b": 0,
            "dry_run_payload_validation_only": True,
        },
    },
}

SOURCE_READ_PHASES = {"p52a", "p52b", "p52c"}


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


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P57_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _scan_values_for_leaks(obj: Any, prefix: str = "") -> list[str]:
    """Detect values that look like paths, URLs, or provider keys."""
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
    return violations


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


def _phase_status(data: dict[str, Any] | None) -> str:
    if data is None:
        return "not_provided"
    if data.get("_invalid_json"):
        return "invalid_json"
    status = data.get("status")
    if not isinstance(status, str):
        return "not_provided"
    return status if status in ALLOWED_UPSTREAM_STATUS else "unrecognized_status"


def _verify_upstream_safety(phase: str, data: dict[str, Any] | None) -> dict[str, Any]:
    """Return aggregate safety gate summary for one phase (no paths)."""
    result: dict[str, Any] = {
        "report_present": data is not None and not data.get("_invalid_json"),
        "status": _phase_status(data),
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

    cfg = PHASE_SAFETY.get(phase, {})

    def check_bool(key: str, expected: Any, label: str, blocker: bool) -> None:
        present = key in data
        actual = data.get(key)
        if not present:
            result["safety_warnings"].append(f"missing_{label}")
            return
        if actual is not expected:
            if blocker:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{label}_violation")
            else:
                result["safety_warnings"].append(f"{label}_unexpected")
        else:
            setattr_state(label, True)

    # manual boolean buckets
    def setattr_state(label: str, value: bool | None) -> None:
        if label == "promotion_default_false":
            result["promotion_default_false"] = value
        elif label == "candidate_not_fact_true":
            result["candidate_not_fact_true"] = value
        elif label == "aggregate_only_true":
            result["aggregate_only_true"] = value
        elif label == "remote_calls_zero":
            result["remote_calls_zero"] = value
        elif label == "llm_calls_zero":
            result["llm_calls_zero"] = value
        elif label == "prompt_construction_false":
            result["prompt_construction_false"] = value
        elif label == "source_reads_not_attempted_or_bounded":
            result["source_reads_not_attempted_or_bounded"] = value

    def check_pair(keys: list[str], expected: Any, label: str, blocker: bool) -> None:
        for key in keys:
            check_bool(key, expected, label, blocker)

    # Top-level safety flags common to all deterministic diagnostic reports.
    for key, expected in [
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("candidate_not_fact", True),
        ("aggregate_only_public_artifact", True),
        ("score_phase_only_metrics", True),
    ]:
        if key in data:
            if data[key] is not expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{key}_violation")
            else:
                if key in {"promotion_ready", "default_should_change", "evidencecore_semantics_changed"}:
                    result["promotion_default_false"] = True
                elif key == "candidate_not_fact":
                    result["candidate_not_fact_true"] = True
                elif key == "aggregate_only_public_artifact":
                    result["aggregate_only_true"] = True
        else:
            result["safety_warnings"].append(f"missing_{key}")

    raw_flags = [
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
    for key in raw_flags:
        if key in data and data[key] is not False:
            result["safety_blocker"] = True
            result["safety_warnings"].append(f"{key}_violation")

    # Phase-specific counters/flags.
    remote_key = cfg.get("remote")
    if remote_key:
        check_bool(remote_key, 0, "remote_calls_zero", blocker=True)
    llm_key = cfg.get("llm")
    if llm_key:
        check_bool(llm_key, 0, "llm_calls_zero", blocker=True)
    prompt_key = cfg.get("prompt")
    if prompt_key:
        check_bool(prompt_key, False, "prompt_construction_false", blocker=True)
    source_reads_key = cfg.get("source_reads")
    source_bounded_key = cfg.get("source_bounded")
    if source_reads_key:
        attempted = data.get(source_reads_key)
        if phase in SOURCE_READ_PHASES:
            bounded = data.get(source_bounded_key) if source_bounded_key else None
            if attempted is not True:
                if source_reads_key in data:
                    result["safety_warnings"].append("source_reads_not_attempted")
                else:
                    result["safety_warnings"].append("missing_source_reads_attempted")
            if bounded is not True:
                result["safety_blocker"] = True
                result["safety_warnings"].append("source_reads_not_bounded")
            else:
                result["source_reads_not_attempted_or_bounded"] = True
        else:
            if attempted is not False:
                if source_reads_key in data:
                    result["safety_blocker"] = True
                    result["safety_warnings"].append("source_reads_unexpectedly_attempted")
                else:
                    result["safety_warnings"].append("missing_source_reads_attempted")
            else:
                result["source_reads_not_attempted_or_bounded"] = True

    extra = cfg.get("extra") or {}
    for key, expected in extra.items():
        if key in data:
            if data[key] != expected:
                result["safety_blocker"] = True
                result["safety_warnings"].append(f"{key}_violation")
        else:
            result["safety_warnings"].append(f"missing_{key}")

    # Upstream status should be a recognized diagnostic status.
    status = _phase_status(data)
    if status not in {"ok", "self_test_only"}:
        result["safety_warnings"].append(f"upstream_status_{status}")

    return result


def _make_synthetic_phase_report(phase: str, unsafe: bool = False) -> dict[str, Any]:
    """Build a minimal aggregate upstream report in memory for self-test."""
    cfg = PHASE_SAFETY.get(phase, {})
    report: dict[str, Any] = {
        "schema_version": f"{phase}-aggregate-report-v0",
        "status": "self_test_only",
        "self_test": True,
        "not_quality_evidence": True,
        "promotion_ready": True if unsafe and phase == "p46" else False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "task_count": 7,
        "positive_task_count": 5,
        "no_gold_task_count": 2,
    }
    remote_key = cfg.get("remote")
    if remote_key:
        report[remote_key] = 0
    llm_key = cfg.get("llm")
    if llm_key:
        report[llm_key] = 0
    prompt_key = cfg.get("prompt")
    if prompt_key:
        report[prompt_key] = False
    source_reads_key = cfg.get("source_reads")
    if source_reads_key:
        report[source_reads_key] = phase in SOURCE_READ_PHASES
    source_bounded_key = cfg.get("source_bounded")
    if source_bounded_key:
        report[source_bounded_key] = True
    extra = cfg.get("extra") or {}
    report.update(extra)
    for key in [
        "raw_text_stored", "raw_source_stored", "raw_snippets_stored",
        "raw_snippets_committed", "raw_snippets_sent_to_provider",
        "raw_prompts_stored", "raw_responses_stored", "raw_query_stored",
        "raw_paths_in_artifact", "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact", "provider_keys_in_artifact",
        "gold_spans_in_artifact", "private_labels_committed",
    ]:
        report[key] = False
    return report


def _make_self_test_slices(unsafe: bool = False) -> list[dict[str, Any]]:
    """Return one synthetic slice map: phase -> report dict."""
    slice_map: dict[str, dict[str, Any]] = {}
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        slice_map[phase] = _make_synthetic_phase_report(phase, unsafe=unsafe)
    return [slice_map]


def _load_slices_from_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build a list of slices from CLI paths or input matrix."""
    if args.input_matrix:
        raw = json.loads(Path(args.input_matrix).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise SystemExit("--input-matrix must contain a JSON list of slices")
        slices: list[dict[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise SystemExit("each --input-matrix entry must be an object")
            slice_map: dict[str, dict[str, Any] | None] = {}
            for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
                path_key = f"{phase}_report"
                path = entry.get(path_key)
                if path:
                    slice_map[phase] = _read_aggregate_report(Path(path))
                else:
                    slice_map[phase] = None
            slices.append(slice_map)
        return slices

    slice_map = {}
    path_args = {
        "p46": args.p46_report,
        "p47": args.p47_report,
        "p48": args.p48_report,
        "p49": args.p49_report,
        "p50": args.p50_report,
        "p52": args.p52_report,
        "p52a": args.p52a_report,
        "p52b": args.p52b_report,
        "p52c": args.p52c_report,
        "p51": args.p51_report,
        "p51b": args.p51b_report,
    }
    for phase, path in path_args.items():
        slice_map[phase] = _read_aggregate_report(path)
    return [slice_map]


def _slice_task_counts(slice_map: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    """Aggregate task counts if all required upstream reports safely provide them."""
    counts: list[int] = []
    positives: list[int] = []
    no_golds: list[int] = []

    def report_task_counts(data: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
        """Return aggregate task counts without reading private task/label data.

        Most phases publish top-level task counts. P50 predates that convention
        and publishes the same aggregate counts under `suite_composition`; keep
        accepting that sanitized aggregate shape so cross-run matrices do not
        collapse only because a required health gate reports counts one level
        down.
        """
        tc = _as_int(data.get("task_count"))
        pc = _as_int(data.get("positive_task_count"))
        ng = _as_int(data.get("no_gold_task_count"))
        if tc is not None:
            return tc, pc, ng
        suite = data.get("suite_composition")
        if isinstance(suite, dict):
            return (
                _as_int(suite.get("task_count")),
                _as_int(suite.get("positive_task_count")),
                _as_int(suite.get("no_gold_task_count")),
            )
        return None, None, None

    for phase in REQUIRED_PHASES:
        data = slice_map.get(phase)
        if not data or data.get("_invalid_json"):
            return {"task_count": None, "positive_task_count": None, "no_gold_task_count": None}
        tc, pc, ng = report_task_counts(data)
        if tc is None or tc <= 0:
            return {"task_count": None, "positive_task_count": None, "no_gold_task_count": None}
        counts.append(tc)
        positives.append(pc if pc is not None else 0)
        no_golds.append(ng if ng is not None else 0)
    return {
        "task_count": min(counts),
        "positive_task_count": min(positives),
        "no_gold_task_count": min(no_golds),
    }


def _evaluate_slices(slices: list[dict[str, Any]]) -> dict[str, Any]:
    required_present_count = 0
    optional_present_count = 0
    required_missing: list[str] = []
    optional_missing: list[str] = []

    # Per-slice metadata without identifiers.
    slice_meta: list[dict[str, Any]] = []
    for slice_map in slices:
        meta: dict[str, Any] = {"required_present": [], "required_missing": []}
        for phase in REQUIRED_PHASES:
            data = slice_map.get(phase)
            if data and not data.get("_invalid_json"):
                meta["required_present"].append(phase)
            else:
                meta["required_missing"].append(phase)
        for phase in OPTIONAL_PHASES:
            data = slice_map.get(phase)
            meta[f"{phase}_present"] = bool(data and not data.get("_invalid_json"))
        meta.update(_slice_task_counts(slice_map))
        status = "all_required_present" if not meta["required_missing"] else "missing_required"
        if any(
            (slice_map.get(phase) or {}).get("self_test") is True
            or (slice_map.get(phase) or {}).get("status") == "self_test_only"
            for phase in REQUIRED_PHASES
        ):
            meta["self_test_only"] = True
        else:
            meta["self_test_only"] = False
        meta["status"] = status
        slice_meta.append(meta)

    for phase in REQUIRED_PHASES:
        present_in_any = any(meta["required_present"] and phase in meta["required_present"] for meta in slice_meta)
        if present_in_any:
            required_present_count += 1
        else:
            required_missing.append(phase)
    for phase in OPTIONAL_PHASES:
        present_in_any = any(meta.get(f"{phase}_present") for meta in slice_meta)
        optional_present_count += 1 if present_in_any else 0
        if not present_in_any:
            optional_missing.append(phase)

    slice_count = len(slices)
    slice_count_with_all_required = sum(1 for m in slice_meta if m["status"] == "all_required_present")
    self_test_slice_count = sum(1 for m in slice_meta if m.get("self_test_only"))

    included_generalization_slices = []
    for meta in slice_meta:
        if meta.get("self_test_only"):
            continue
        if meta["status"] != "all_required_present":
            continue
        tc = meta.get("task_count")
        if tc is None or tc < MIN_TASKS_PER_SLICE:
            continue
        included_generalization_slices.append(meta)
    included_generalization_slice_count = len(included_generalization_slices)

    observed_task_count_aggregate: int | str = "unavailable"
    observed_positive_count: int | str = "unavailable"
    observed_no_gold_count: int | str = "unavailable"
    if included_generalization_slice_count > 0:
        tcs = [m["task_count"] for m in included_generalization_slices if isinstance(m["task_count"], int)]
        pcs = [m["positive_task_count"] for m in included_generalization_slices if isinstance(m["positive_task_count"], int)]
        ngs = [m["no_gold_task_count"] for m in included_generalization_slices if isinstance(m["no_gold_task_count"], int)]
        if tcs:
            observed_task_count_aggregate = sum(tcs)
        if pcs:
            observed_positive_count = sum(pcs)
        if ngs:
            observed_no_gold_count = sum(ngs)

    positive_coverage = (
        isinstance(observed_positive_count, int) and observed_positive_count > 0
    )
    no_gold_coverage = (
        isinstance(observed_no_gold_count, int) and observed_no_gold_count > 0
    )

    return {
        "slice_count": slice_count,
        "slice_count_with_all_required_reports": slice_count_with_all_required,
        "self_test_slice_count": self_test_slice_count,
        "included_generalization_slice_count": included_generalization_slice_count,
        "required_present_count": required_present_count,
        "required_missing": required_missing,
        "optional_present_count": optional_present_count,
        "optional_missing": optional_missing,
        "observed_task_count_aggregate": observed_task_count_aggregate,
        "observed_positive_count": observed_positive_count,
        "observed_no_gold_count": observed_no_gold_count,
        "positive_coverage": positive_coverage,
        "no_gold_coverage": no_gold_coverage,
        "slice_meta": slice_meta,
    }


def _build_report(
    slices: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
) -> dict[str, Any]:
    # Upstream safety verification across all slices.
    by_phase: dict[str, Any] = {}
    safety_blocker_count = 0
    safety_warning_count = 0
    checked_count = 0

    # Aggregate status per phase across slices.
    per_phase_status_sets: dict[str, set[str]] = {phase: set() for phase in REQUIRED_PHASES + OPTIONAL_PHASES}
    per_phase_availability: dict[str, str] = {}
    per_phase_status_summary: dict[str, str] = {}

    for slice_map in slices:
        for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
            data = slice_map.get(phase)
            phase_status = _phase_status(data)
            per_phase_status_sets[phase].add(phase_status)
            if data and not data.get("_invalid_json"):
                checked_count += 1
                v = _verify_upstream_safety(phase, data)
                by_phase.setdefault(phase, v)
                # If multiple slices, keep the most conservative (blocked if any).
                existing = by_phase[phase]
                if v["safety_blocker"]:
                    existing["safety_blocker"] = True
                if v["safety_warnings"]:
                    existing["safety_warnings"] = list(set(existing["safety_warnings"]) | set(v["safety_warnings"]))
                if v["report_present"]:
                    existing["report_present"] = True

    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        statuses = per_phase_status_sets[phase]
        if not statuses or statuses == {"not_provided"}:
            per_phase_availability[phase] = "unavailable"
            per_phase_status_summary[phase] = "not_provided"
        elif statuses <= {"ok", "self_test_only"}:
            per_phase_availability[phase] = "available"
            per_phase_status_summary[phase] = "ok" if "ok" in statuses else "self_test_only"
        else:
            per_phase_availability[phase] = "partial"
            per_phase_status_summary[phase] = "mixed"

    # Recompute warnings/blockers totals from merged by_phase.
    for phase, v in by_phase.items():
        if v["safety_blocker"]:
            safety_blocker_count += 1
        safety_warning_count += len(v["safety_warnings"])

    # Matrix structural evaluation.
    matrix = _evaluate_slices(slices)

    blockers: list[str] = []
    warnings: list[str] = []

    # Missing required reports are blockers.
    for phase in matrix["required_missing"]:
        blockers.append(f"Required upstream report {phase} missing or unreadable.")

    # Slice count.
    if matrix["slice_count"] < MIN_REQUIRED_SLICES:
        blockers.append(
            f"slice_count={matrix['slice_count']} < required {MIN_REQUIRED_SLICES}."
        )

    # Included generalization slices.
    if matrix["included_generalization_slice_count"] < MIN_REQUIRED_SLICES:
        blockers.append(
            f"included_generalization_slice_count={matrix['included_generalization_slice_count']} < required {MIN_REQUIRED_SLICES}."
        )

    # Coverage.
    if isinstance(matrix["observed_positive_count"], int) and not matrix["positive_coverage"]:
        blockers.append("No positive-task coverage in included generalization slices.")
    if isinstance(matrix["observed_no_gold_count"], int) and not matrix["no_gold_coverage"]:
        blockers.append("No no-gold-task coverage in included generalization slices.")

    # Warnings for optional missing / unavailable counts.
    for phase in matrix["optional_missing"]:
        warnings.append(f"Optional upstream report {phase} missing.")
    if matrix["observed_task_count_aggregate"] == "unavailable":
        warnings.append("observed_task_count_aggregate unavailable.")
    if matrix["slice_count"] >= MIN_REQUIRED_SLICES and matrix["observed_task_count_aggregate"] == "unavailable":
        warnings.append("Multi-slice matrix present but aggregate task count unavailable.")

    # Upstream unstable statuses are warnings.
    for phase, agg_status in per_phase_status_summary.items():
        if agg_status in {"mixed", "invalid_json"}:
            warnings.append(f"Upstream phase {phase} has unstable status aggregate: {agg_status}.")
    if safety_warning_count > 0:
        warnings.append(f"Upstream safety warnings detected across {safety_warning_count} phase checks.")

    # Determine final status.
    if safety_blocker_count > 0:
        status = "blocked_safety"
        status_reason = f"Upstream safety flag violations detected in {safety_blocker_count} phase(s)."
    elif blockers:
        status = "insufficient_matrix"
        status_reason = "Generalization-readiness requirements not satisfied."
    elif any(agg_status == "mixed" for agg_status in per_phase_status_summary.values()):
        status = "diagnostic_matrix_unstable"
        status_reason = "All structural requirements satisfied but upstream reports contain unstable statuses."
    else:
        status = "diagnostic_matrix_complete"
        status_reason = "Diagnostic matrix meets current structural requirements."

    # For single/self-test runs, force insufficient_matrix unless safety blocked.
    if status not in {"blocked_safety"} and matrix["slice_count"] < MIN_REQUIRED_SLICES:
        status = "insufficient_matrix"
        status_reason = "Single/self-test slice; generalization matrix is insufficient by design."

    generalization_matrix: dict[str, Any] = {
        "readiness_status": status,
        "required_slice_count": MIN_REQUIRED_SLICES,
        "required_min_repo_count": MIN_REQUIRED_REPOS,
        "observed_slice_count": matrix["slice_count"],
        "observed_repo_count": "unavailable",
        "observed_task_count_aggregate": matrix["observed_task_count_aggregate"],
        "per_phase_availability": per_phase_availability,
        "per_phase_status_summary": per_phase_status_summary,
        "dispersion": "unavailable" if matrix["slice_count"] < 2 else "future_multi_slice_metric",
        "worst_slice_task_count": "unavailable",
        "worst_slice_required_reports_missing": "unavailable",
    }

    input_summary: dict[str, Any] = {
        "required_reports": list(REQUIRED_PHASES),
        "optional_reports": list(OPTIONAL_PHASES),
        "required_present_count": matrix["required_present_count"],
        "optional_present_count": matrix["optional_present_count"],
        "required_missing": matrix["required_missing"],
        "slice_count": matrix["slice_count"],
        "slice_count_with_all_required_reports": matrix["slice_count_with_all_required_reports"],
        "self_test_slice_count": matrix["self_test_slice_count"],
        "included_generalization_slice_count": matrix["included_generalization_slice_count"],
        "matrix_requirement_summary": (
            "single_slice_self_test" if matrix["slice_count"] == 1 and self_test
            else "single_slice" if matrix["slice_count"] == 1
            else "multi_slice_v0"
        ),
    }

    upstream_safety_gate: dict[str, Any] = {
        "checked_count": checked_count,
        "blocker_count": safety_blocker_count,
        "warning_count": safety_warning_count,
        "by_phase": by_phase,
    }

    coverage_summary = "unavailable"
    if isinstance(matrix["observed_positive_count"], int) and isinstance(matrix["observed_no_gold_count"], int):
        coverage_summary = f"positive={matrix['observed_positive_count']} no_gold={matrix['observed_no_gold_count']}"

    generalization_matrix["coverage_summary"] = coverage_summary

    conclusion: list[str] = [
        "P57 Generalization Gate v0 is an aggregate-only, deterministic diagnostic readiness check.",
        "P57 does not read source files, candidate pools, prompts, responses, provider configs, or private labels.",
        "P57 is not quality evidence, not a promotion/default gate, and not live-readiness evidence.",
    ]
    if self_test:
        conclusion.append("This self-test exercised the P57 validation paths with synthetic upstream reports.")
    if safety_blocker_count > 0:
        conclusion.append(f"Safety blocker(s): {safety_blocker_count} upstream phase(s) failed safety verification.")
    if blockers:
        conclusion.append(f"Generalization blocker(s): {len(blockers)}.")
    conclusion.append(
        f"Current status: {status}. "
        f"Slices observed: {matrix['slice_count']}; included generalization slices: {matrix['included_generalization_slice_count']}."
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": status_reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "remote_calls_by_p57": 0,
        "llm_calls_by_p57": 0,
        "prompt_construction_by_p57": False,
        "source_reads_attempted_by_p57": False,
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
        "upstream_safety_gate": upstream_safety_gate,
        "generalization_matrix": generalization_matrix,
        "blockers": blockers,
        "warnings": warnings,
        "conclusion": conclusion,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P57 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p57") != 0:
        errors.append("remote_calls_by_p57 must be 0")
    if report.get("llm_calls_by_p57") != 0:
        errors.append("llm_calls_by_p57 must be 0")
    if report.get("prompt_construction_by_p57") is not False:
        errors.append("prompt_construction_by_p57 must be false")
    if report.get("source_reads_attempted_by_p57") is not False:
        errors.append("source_reads_attempted_by_p57 must be false")

    expected_flags = {
        "not_quality_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
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
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")

    for forbidden in ("tasks", "records", "per_task_results", "per_candidate_results", "per_slice_rows"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))
    return errors


def _fmt_scalar(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    return str(x)


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P57: {report['remote_calls_by_p57']}",
        f"- LLM calls by P57: {report['llm_calls_by_p57']}",
        f"- Prompt construction by P57: {report['prompt_construction_by_p57']}",
        f"- Source reads attempted by P57: {report['source_reads_attempted_by_p57']}",
        f"- Upstream safety blockers: {report['upstream_safety_gate']['blocker_count']}",
        f"- Upstream safety warnings: {report['upstream_safety_gate']['warning_count']}",
        f"- Slices observed: {report['input_summary']['slice_count']}",
        f"- Included generalization slices: {report['input_summary']['included_generalization_slice_count']}",
        "",
    ])

    lines.extend([
        "## Purpose",
        "",
        "P57 Generalization Gate v0 checks whether the existing aggregate diagnostic reports provide enough safety, completeness, and availability to even discuss generalization readiness. ",
        "It is **not** quality evidence, **not** a promotion/default gate, and **not** evidence of live readiness. ",
        "It consumes only aggregate upstream JSON and emits only aggregate counts and status enums.",
        "",
        "## Methodology",
        "",
        "- Accept upstream aggregate report paths (P46, P47, P48, P49, P50, P52, P52A, P52B, P52C, optional P51, required P51B).",
        "- Read only sanitized aggregate fields (status, top-level task counts/safety flags, plus P50's aggregate `suite_composition` count fallback).",
        "- Verify upstream safety flags: no promotion/default claims, `candidate_not_fact=true`, aggregate-only artifacts, remote/LLM counters at zero for deterministic phases, and bounded source reads only for P52A/B/C.",
        "- Require at least 4 non-self-test slices with all required reports and at least 6 tasks per slice, plus both positive and no-gold coverage.",
        "- For the current single-slice/self-test workflow, report `insufficient_matrix` by design.",
        "",
        "## Safety notes",
        "",
        "- P57 makes no remote or LLM calls.",
        "- P57 does not construct prompts, read source files, or access candidate pools.",
        "- P57 does not persist paths, repo/task/candidate identifiers, spans, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.",
        "- P57 output is not Evidence and does not support default or promotion decisions.",
        "",
    ])

    inp = report["input_summary"]
    lines.extend([
        "## Input summary",
        "",
        f"- Required reports: {', '.join(inp['required_reports'])}",
        f"- Optional reports: {', '.join(inp['optional_reports'])}",
        f"- Required present count: {inp['required_present_count']}/{len(inp['required_reports'])}",
        f"- Optional present count: {inp['optional_present_count']}/{len(inp['optional_reports'])}",
        f"- Required missing: {', '.join(inp['required_missing']) if inp['required_missing'] else 'none'}",
        f"- Slice count: {inp['slice_count']}",
        f"- Slices with all required reports: {inp['slice_count_with_all_required_reports']}",
        f"- Self-test slices: {inp['self_test_slice_count']}",
        f"- Included generalization slices: {inp['included_generalization_slice_count']}",
        f"- Matrix requirement summary: `{inp['matrix_requirement_summary']}`",
        "",
    ])

    gm = report["generalization_matrix"]
    lines.extend([
        "## Generalization matrix",
        "",
        f"- Readiness status: `{gm['readiness_status']}`",
        f"- Required slices/repos: {gm['required_slice_count']}/{gm['required_min_repo_count']}",
        f"- Observed slices: {gm['observed_slice_count']}",
        f"- Observed repo count: {gm['observed_repo_count']}",
        f"- Observed aggregate task count: {gm['observed_task_count_aggregate']}",
        f"- Coverage summary: {gm['coverage_summary']}",
        f"- Dispersion: {gm['dispersion']}",
        f"- Worst-slice task count: {gm['worst_slice_task_count']}",
        f"- Worst-slice missing required reports: {gm['worst_slice_required_reports_missing']}",
        "",
        "### Per-phase availability",
        "",
        "| Phase | Availability | Status summary |",
        "|---|---|---|",
    ])
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        avail = gm["per_phase_availability"].get(phase)
        stat = gm["per_phase_status_summary"].get(phase)
        lines.append(f"| {phase} | `{avail}` | `{stat}` |")
    lines.append("")

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
    for phase in REQUIRED_PHASES + OPTIONAL_PHASES:
        v = sg["by_phase"].get(phase)
        if v is None:
            v = {}
        lines.append(
            f"| {phase} | {v.get('report_present', False)} | `{v.get('status', 'not_provided')}` | "
            f"{v.get('safety_blocker', False)} | {len(v.get('safety_warnings', []))} |"
        )
    lines.append("")

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


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input-matrix", type=Path, default=None, help="Optional JSON list of multi-slice report maps.")
    parser.add_argument("--p46-report", type=Path, default=None, help="P46 aggregate report path.")
    parser.add_argument("--p47-report", type=Path, default=None, help="P47 aggregate report path.")
    parser.add_argument("--p48-report", type=Path, default=None, help="P48 aggregate report path.")
    parser.add_argument("--p49-report", type=Path, default=None, help="P49 aggregate report path.")
    parser.add_argument("--p50-report", type=Path, default=None, help="P50 aggregate report path.")
    parser.add_argument("--p52-report", type=Path, default=None, help="P52 aggregate report path.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="P52A aggregate report path.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="P52B aggregate report path.")
    parser.add_argument("--p52c-report", type=Path, default=None, help="P52C aggregate report path.")
    parser.add_argument("--p51-report", type=Path, default=None, help="Optional P51 aggregate report path.")
    parser.add_argument("--p51b-report", type=Path, default=None, help="Required P51B aggregate report path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()

    if args.self_test:
        # Exercise both the safety-blocker path and the insufficient-matrix path.
        unsafe_slices = _make_self_test_slices(unsafe=True)
        unsafe_report = _build_report(unsafe_slices, self_test=True, elapsed_ms=0)
        if unsafe_report["status"] != "blocked_safety":
            raise RuntimeError("P57 self-test safety-blocker path did not trigger")
        slices = _make_self_test_slices(unsafe=False)
    else:
        slices = _load_slices_from_args(args)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    report = _build_report(slices, self_test=args.self_test, elapsed_ms=elapsed_ms)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P57 report written to {args.out}")
    print(f"P57 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
