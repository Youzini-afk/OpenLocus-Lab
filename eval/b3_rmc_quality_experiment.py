#!/usr/bin/env python3
"""B3 Request-More-Context live quality experiment.

B3 compares fixed RMC treatment rules against the P25 bucket-routed reference
using live P21 rich-candidate outputs from two pack layouts over the same frozen
task set:

* ``topk_plain_v0`` records provide candidate_baseline and positive span_narrow.
* ``hard_distractor_contrast_v0`` records provide filter outcomes for negative /
  no-gold / hard-distractor routes.

The public report is aggregate-only.  Per-task details, candidate identifiers,
paths, line ranges, digests, snippets, prompts, responses, and labels remain only
inside ephemeral P25 records consumed during the workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import p25_bucket_policy as p25

SCHEMA_VERSION = "b3-rmc-quality-experiment-v0"
GENERATED_BY = "b3_rmc_quality_experiment"

DEFAULT_OUT = Path("artifacts/b3_rmc_quality_experiment/b3_rmc_quality_experiment_report.json")
DEFAULT_DOC = Path("docs/en/b3-rmc-quality-experiment.md")

TREATMENTS = [
    "p25_bucket_routed_v0_plain",
    "rmc_local_conservative_v0",
    "rmc_llm_pack_routed_v0",
    "rmc_hybrid_v0",
]

PUBLIC_ACTIONS = {
    "candidate_baseline",
    "plain_llm_span_narrow",
    "plain_llm_filter",
    "plain_llm_abstain_filter",
    "hard_llm_filter",
    "weak_candidate_only",
}

FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "test_id",
    "candidate_id",
    "repo_id",
    "query",
    "path",
    "candidate_path",
    "start_line",
    "end_line",
    "line_range",
    "content_sha",
    "digest",
    "snippet",
    "prompt",
    "response",
    "raw_response",
    "gold_spans",
    "label",
    "labels",
    "private_labels",
    "decision_records",
    "candidate_meta",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"/[A-Za-z0-9._/\-]{3,}"),
    re.compile(r"[A-Fa-f0-9]{32,}"),
    re.compile(r"https?://", re.I),
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"base[_-]?url", re.I),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_outcome(raw: dict[str, Any], name: str) -> dict[str, Any]:
    src = raw.get(name)
    if isinstance(src, dict):
        return src
    for key in ("strategies", "outcomes", "strategy_results", "results", "metrics"):
        container = raw.get(key) or {}
        if isinstance(container, dict) and isinstance(container.get(name), dict):
            return container[name]
    return {}


def _weak_outcome(raw: dict[str, Any]) -> dict[str, Any]:
    weak = _extract_outcome(raw, "weak_candidate_only") or _extract_outcome(raw, "supporting_only")
    return {
        "file_recall_at_5": weak.get("file_recall_at_5"),
        "span_f0_5": weak.get("span_f0_5", 0.0),
        "primary_false_positive_rate": weak.get("primary_false_positive_rate", 0.0),
        "no_gold_false_primary_rate": weak.get("no_gold_false_primary_rate", 0.0),
        "added_gold_span": _as_int(weak.get("added_gold_span")) or 0,
        "added_false_span": _as_int(weak.get("added_false_span")) or 0,
        "abstained": True,
    }


def _load_records(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw_rows = p25.load_p21_inputs([path])
    normalized: list[dict[str, Any]] = []
    raw_by_task: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        norm = p25.normalize_task(row)
        if norm is None:
            continue
        tid = str(norm["task_id"])
        norm["outcomes"]["weak_candidate_only"] = _weak_outcome(row)
        normalized.append(norm)
        raw_by_task[tid] = row
    return normalized, raw_by_task


def _labels(task: dict[str, Any]) -> set[str]:
    return p25.bucket_labels(task)


def _has_support(task: dict[str, Any]) -> bool:
    rf = task.get("route_features") or {}
    return bool(rf.get("candidate_support_exists")) or int(rf.get("candidate_count") or 0) > 0


def _exact_unique(task: dict[str, Any]) -> bool:
    labels = _labels(task)
    return bool(
        (labels & {"exact_symbol", "exact_symbol_unique", "exact_symbol_match"})
        and (labels & {"unique", "unique_symbol", "symbol_anchor"})
    )


def _positive_like(task: dict[str, Any]) -> bool:
    labels = _labels(task)
    return bool(labels & p25.POSITIVE_BUCKET_KEYS)


def _negative_like(task: dict[str, Any]) -> bool:
    labels = _labels(task)
    return bool(labels & p25.NEGATIVE_BUCKET_KEYS)


def _hard_filter_like(task: dict[str, Any]) -> bool:
    labels = _labels(task)
    return (
        task.get("has_gold") is False
        or bool(labels & {"hard_distractor", "dense_false_positive", "dense_quiver_trap", "ambiguous"})
        or _negative_like(task)
    )


def _action_for_treatment(treatment: str, task: dict[str, Any]) -> str:
    if treatment == "p25_bucket_routed_v0_plain":
        action = p25.route_bucket_routed_v0(task, p25.choose_negative_strategy([task]))
        if action == "llm_span_narrow":
            return "plain_llm_span_narrow"
        if action == "llm_filter":
            return "plain_llm_filter"
        if action == "llm_abstain_filter":
            return "plain_llm_abstain_filter"
        return "candidate_baseline"

    if treatment == "rmc_local_conservative_v0":
        if _hard_filter_like(task):
            return "weak_candidate_only"
        return "candidate_baseline"

    if treatment == "rmc_llm_pack_routed_v0":
        if _exact_unique(task):
            return "candidate_baseline"
        if _hard_filter_like(task):
            return "hard_llm_filter"
        if _positive_like(task) and _has_support(task):
            return "plain_llm_span_narrow"
        return "candidate_baseline"

    if treatment == "rmc_hybrid_v0":
        if _exact_unique(task):
            return "candidate_baseline"
        if not _has_support(task):
            return "weak_candidate_only"
        if _hard_filter_like(task):
            return "hard_llm_filter"
        if _positive_like(task):
            return "plain_llm_span_narrow"
        return "candidate_baseline"

    raise ValueError(f"unknown treatment: {treatment}")


def _outcome_for_action(action: str, plain: dict[str, Any], hard: dict[str, Any]) -> dict[str, Any]:
    if action == "candidate_baseline":
        return plain["outcomes"]["candidate_baseline"]
    if action == "plain_llm_span_narrow":
        return plain["outcomes"]["llm_span_narrow"]
    if action == "plain_llm_filter":
        return plain["outcomes"]["llm_filter"]
    if action == "plain_llm_abstain_filter":
        return plain["outcomes"]["llm_abstain_filter"]
    if action == "hard_llm_filter":
        return hard["outcomes"]["llm_filter"]
    if action == "weak_candidate_only":
        return plain["outcomes"]["weak_candidate_only"]
    raise ValueError(action)


def _metric_for_task(plain: dict[str, Any], hard: dict[str, Any], treatment: str) -> tuple[str, dict[str, Any]]:
    action = _action_for_treatment(treatment, plain)
    return action, _outcome_for_action(action, plain, hard)


def _aggregate_treatment(
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
    treatment: str,
    p25_outcomes: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    task_count = len(plain_tasks)
    pos_count = sum(1 for t in plain_tasks if t.get("has_gold"))
    no_gold_count = task_count - pos_count
    action_counts: Counter[str] = Counter()
    spans: list[float] = []
    pfps: list[float] = []
    no_gold_pfps: list[float] = []
    added_gold = 0
    added_false = 0
    selected: dict[str, dict[str, Any]] = {}
    gold_kill = 0

    for plain in plain_tasks:
        tid = str(plain["task_id"])
        hard = hard_by_task[tid]
        action, outcome = _metric_for_task(plain, hard, treatment)
        action_counts[action] += 1
        selected[tid] = outcome
        ag = int(outcome.get("added_gold_span") or 0)
        af = int(outcome.get("added_false_span") or 0)
        added_gold += ag
        added_false += af
        if outcome.get("span_f0_5") is not None:
            spans.append(float(outcome["span_f0_5"]))
        if outcome.get("primary_false_positive_rate") is not None:
            pfps.append(float(outcome["primary_false_positive_rate"]))
        if not plain.get("has_gold"):
            ng = outcome.get("no_gold_false_primary_rate")
            if ng is None:
                ng = outcome.get("primary_false_positive_rate")
            if ng is not None:
                no_gold_pfps.append(float(ng))
        if p25_outcomes is not None:
            base = p25_outcomes[tid]
            if plain.get("has_gold") and int(base.get("added_gold_span") or 0) > 0 and ag == 0:
                gold_kill += 1

    llm_actions = {"plain_llm_span_narrow", "plain_llm_filter", "plain_llm_abstain_filter", "hard_llm_filter"}
    effective_llm_count = sum(action_counts[a] for a in llm_actions)
    metrics = {
        "task_count": task_count,
        "positive_task_count": pos_count,
        "no_gold_task_count": no_gold_count,
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "false_per_gold": _safe_div(added_false, added_gold),
        "mean_span_f05": _avg(spans),
        "mean_primary_false_positive_rate": _avg(pfps),
        "no_gold_false_primary_rate": _avg(no_gold_pfps),
        "action_counts": {a: int(action_counts.get(a, 0)) for a in sorted(PUBLIC_ACTIONS)},
        "action_rates": {a: _safe_div(action_counts.get(a, 0), task_count) for a in sorted(PUBLIC_ACTIONS)},
        "effective_llm_action_count": effective_llm_count,
        "effective_llm_action_rate": _safe_div(effective_llm_count, task_count),
        "provider_call_estimate": effective_llm_count,
        "provider_call_estimate_not_measured": True,
        "gold_kill_count_vs_p25": gold_kill,
        "false_reduction_vs_p25": None,
        "net_span_value_2x": added_gold - 2 * added_false,
    }
    if p25_outcomes is not None:
        p25_false = sum(int(o.get("added_false_span") or 0) for o in p25_outcomes.values())
        metrics["false_reduction_vs_p25"] = p25_false - added_false
    return metrics, selected


def _call_health(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"summary_present": False}
    cs = summary.get("call_summary") or {}
    return {
        "summary_present": True,
        "task_count": summary.get("task_count") or (summary.get("decision_summary") or {}).get("task_count"),
        "pack_layout": summary.get("pack_layout"),
        "successful_calls": summary.get("successful_calls") or summary.get("schema_valid_calls"),
        "schema_valid_calls": summary.get("schema_valid_calls"),
        "fallback_event_count": cs.get("fallback_event_count") or 0,
        "schema_error_count": cs.get("schema_error_count") or 0,
        "input_chars_total": cs.get("input_chars_total"),
        "packed_candidates_total": cs.get("packed_candidates_total") or (summary.get("pack_layout_metrics") or {}).get("candidates_packed_total"),
        "latency_ms_p50": cs.get("latency_ms_p50") or cs.get("latency_p50_ms"),
        "latency_ms_p95": cs.get("latency_ms_p95") or cs.get("latency_p95_ms"),
    }


def _load_summary(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.self_test:
        plain_path, hard_path, plain_summary, hard_summary = _write_self_test_inputs()
    else:
        plain_path, hard_path = args.plain_records, args.hard_records
        plain_summary = _load_summary(args.plain_summary)
        hard_summary = _load_summary(args.hard_summary)

    plain_tasks, _ = _load_records(plain_path)
    hard_tasks, _ = _load_records(hard_path)
    plain_ids = [str(t["task_id"]) for t in plain_tasks]
    hard_ids = [str(t["task_id"]) for t in hard_tasks]
    same_task_set = sorted(plain_ids) == sorted(hard_ids) and len(set(plain_ids)) == len(plain_ids)
    if not same_task_set:
        report = _base_report("blocked_task_set_mismatch", args.self_test)
        report["same_task_set"] = False
        report["plain_task_count"] = len(plain_ids)
        report["hard_task_count"] = len(hard_ids)
        validate_report(report)
        return report

    hard_by_task = {str(t["task_id"]): t for t in hard_tasks}
    treatment_metrics: dict[str, Any] = {}
    p25_metrics, p25_selected = _aggregate_treatment(plain_tasks, hard_by_task, "p25_bucket_routed_v0_plain")
    treatment_metrics["p25_bucket_routed_v0_plain"] = p25_metrics
    for treatment in TREATMENTS[1:]:
        metrics, _selected = _aggregate_treatment(plain_tasks, hard_by_task, treatment, p25_selected)
        treatment_metrics[treatment] = metrics

    report = _base_report("self_test_only" if args.self_test else "ok", args.self_test)
    report.update({
        "same_task_set": True,
        "task_count": len(plain_tasks),
        "positive_task_count": sum(1 for t in plain_tasks if t.get("has_gold")),
        "no_gold_task_count": sum(1 for t in plain_tasks if not t.get("has_gold")),
        "treatments": treatment_metrics,
        "comparability": {
            "plain_pack_layout": "topk_plain_v0",
            "hard_pack_layout": "hard_distractor_contrast_v0",
            "same_model_required": True,
            "same_task_set_required": True,
            "same_task_set_observed": True,
        },
        "call_health": {
            "plain": _call_health(plain_summary),
            "hard": _call_health(hard_summary),
        },
    })
    validate_report(report)
    return report


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "status": status,
        "self_test": bool(self_test),
        "live_quality_experiment": not self_test,
        "not_evidence": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "aggregate_only_public_artifact": True,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
    }


def _walk_forbidden(obj: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key) in FORBIDDEN_PUBLIC_KEYS:
                violations.append(f"{path}.{key}")
            violations.extend(_walk_forbidden(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_walk_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        if len(obj) > 256:
            violations.append(f"{path}:long_string")
        elif any(p.search(obj) for p in FORBIDDEN_VALUE_PATTERNS):
            violations.append(f"{path}:private_like_value")
    return violations


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bad schema_version")
    if report.get("status") not in {"ok", "self_test_only", "blocked_task_set_mismatch"}:
        raise ValueError("bad status")
    for key in [
        "not_evidence", "llm_output_not_evidence", "aggregate_only_public_artifact",
    ]:
        if report.get(key) is not True:
            raise ValueError(f"{key} must be true")
    for key in [
        "promotion_ready", "default_should_change", "evidencecore_semantics_changed",
        "task_ids_in_artifact", "candidate_ids_in_artifact", "raw_prompts_stored",
        "raw_responses_stored", "raw_snippets_stored", "raw_snippets_committed",
        "raw_paths_in_artifact", "raw_line_ranges_in_artifact", "raw_digests_in_artifact",
        "private_labels_committed", "gold_spans_in_artifact",
    ]:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")
    violations = _walk_forbidden(report)
    if violations:
        raise ValueError("public report contains forbidden fields: " + ", ".join(violations[:5]))
    if report.get("status") == "ok":
        treatments = report.get("treatments") or {}
        if set(treatments) != set(TREATMENTS):
            raise ValueError("missing treatments")
        for name, metrics in treatments.items():
            if metrics.get("task_count") != report.get("task_count"):
                raise ValueError(f"{name} task_count mismatch")
            if sum((metrics.get("action_counts") or {}).values()) != metrics.get("task_count"):
                raise ValueError(f"{name} action counts do not sum")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B3 Request-More-Context Quality Experiment")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    lines.append("B3 compares P25 against three fixed request-more-context treatments using live P21 outputs from `topk_plain_v0` and `hard_distractor_contrast_v0` packs. LLM outputs are not Evidence and the report is aggregate-only.")
    lines.append("")
    if report.get("status") == "ok":
        lines.append("| Treatment | Gold | False | False/gold | SpanF0.5 | PFP | LLM actions | Net value 2x |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name in TREATMENTS:
            m = report["treatments"][name]
            lines.append(
                f"| `{name}` | {m['added_gold_span']} | {m['added_false_span']} | "
                f"{_fmt(m['false_per_gold'])} | {_fmt(m['mean_span_f05'])} | "
                f"{_fmt(m['mean_primary_false_positive_rate'])} | {m['effective_llm_action_count']} | {m['net_span_value_2x']} |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_self_test_inputs() -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    rows = p25.make_self_test_tasks()
    payload = {
        "schema_version": "p25-policy-records-ephemeral-v1",
        "not_artifact_for_commit": True,
        "records": rows,
    }
    hard_rows = json.loads(json.dumps(rows))
    for row in hard_rows:
        labels = set(row.get("task_risk_tags") or []) | {row.get("task_bucket")}
        if labels & {"negative", "hard_distractor", "ambiguous", "dense_false_positive"}:
            row["llm_filter"] = {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0}
    tmp = Path("/tmp/opencode/b3-self-test")
    tmp.mkdir(parents=True, exist_ok=True)
    plain = tmp / "plain.private.json"
    hard = tmp / "hard.private.json"
    plain.write_text(json.dumps(payload), encoding="utf-8")
    hard.write_text(json.dumps({**payload, "records": hard_rows}), encoding="utf-8")
    return plain, hard, {"task_count": len(rows), "pack_layout": "topk_plain_v0"}, {"task_count": len(rows), "pack_layout": "hard_distractor_contrast_v0"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plain-records", type=Path)
    p.add_argument("--hard-records", type=Path)
    p.add_argument("--plain-summary", type=Path)
    p.add_argument("--hard-summary", type=Path)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if not args.self_test and (not args.plain_records or not args.hard_records):
        p.error("--plain-records and --hard-records are required unless --self-test")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, args.doc)
    print(json.dumps({"status": report["status"], "task_count": report.get("task_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
