#!/usr/bin/env python3
"""B9A adapter-health aggregate report.

This is not a quality leaderboard. It summarizes whether model profiles can
produce stable structured bounded candidate decisions under small live health
screens.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RUNS = {
    "glm_5_2_tool_call_py": "27739512626",
    "glm_5_2_tool_call_js": "27739600049",
    "glm_5_2_json_schema_py": "27739713629",
    "glm_5_2_json_schema_js": "27739804587",
    "qwen3_6_27b_tool_call_py": "27739892593",
    "qwen3_6_27b_tool_call_js": "27740025107",
    "qwen3_6_27b_json_schema_py": "27740156561",
    "qwen3_6_27b_json_schema_js": "27740270136",
}

MODEL_ADAPTERS = {
    "glm_5_2_tool_call": {
        "model_id": "[mk]GLM-5.2",
        "output_mode": "tool_call",
    },
    "glm_5_2_json_schema_strict": {
        "model_id": "[mk]GLM-5.2",
        "output_mode": "json_schema_strict",
    },
    "qwen3_6_27b_tool_call": {
        "model_id": "[mk]Qwen3.6-27B",
        "output_mode": "tool_call",
    },
    "qwen3_6_27b_json_schema_strict": {
        "model_id": "[mk]Qwen3.6-27B",
        "output_mode": "json_schema_strict",
    },
}


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_report(root: Path, run_id: str) -> Path:
    matches = list(root.glob(f"*_{run_id}/**/artifacts/real_provider_ci/p21_llm_rich_candidate.json"))
    if len(matches) != 1:
        raise SystemExit(f"expected one report for {run_id}, got {len(matches)}")
    return matches[0]


def _run_metrics(data: dict[str, Any]) -> dict[str, Any]:
    cs = data.get("call_summary") or {}
    schema_error_count = int(cs.get("schema_error_count") or 0)
    successful_calls = int(data.get("successful_calls") or 0)
    schema_valid_calls = int(data.get("schema_valid_calls") or 0)
    total_calls = successful_calls + schema_error_count
    fallback_event_count = int(cs.get("fallback_event_count") or 0)
    fallback_used_count = int(cs.get("fallback_used_count") or 0)
    fallback = cs.get("fallback_events") or {}
    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "schema_valid_calls": schema_valid_calls,
        "schema_error_count": schema_error_count,
        "fallback_event_count": fallback_event_count,
        "fallback_used_count": fallback_used_count,
        "mode_counts": fallback.get("mode_counts") or {},
        "error_counts": fallback.get("error_counts") or {},
        "latency_ms_p50": cs.get("latency_ms_p50"),
        "input_chars_total": cs.get("input_chars_total"),
        "packed_candidates_total": cs.get("packed_candidates_total"),
        "decision_records_in_artifact": data.get("decision_records_in_artifact"),
        "candidate_meta_in_artifact": data.get("candidate_meta_in_artifact"),
        "requested_output_mode": data.get("requested_output_mode"),
        "llm_model": data.get("llm_model"),
    }


def _sum_counts(items: list[dict[str, Any]], key: str) -> int:
    return sum(int(item.get(key) or 0) for item in items)


def _merge_counter(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        for k, v in (item.get(key) or {}).items():
            out[str(k)] = out.get(str(k), 0) + int(v)
    return out


def _health_status(schema_valid_rate: float, infra_failure_rate: float) -> str:
    if schema_valid_rate >= 0.95 and infra_failure_rate <= 0.05:
        return "quality_interpretable_health_pass"
    if schema_valid_rate >= 0.80 and infra_failure_rate <= 0.20:
        return "borderline_adapter_health"
    return "not_quality_interpretable_adapter_health"


def build_report(root: Path) -> dict[str, Any]:
    rows = []
    for label, run_id in RUNS.items():
        data = _load_report(_find_report(root, run_id))
        rows.append({"label": label, "run_id": run_id, **_run_metrics(data)})

    grouped: dict[str, list[dict[str, Any]]] = {k: [] for k in MODEL_ADAPTERS}
    for row in rows:
        if row["llm_model"] == "[mk]GLM-5.2" and row["requested_output_mode"] == "tool_call":
            grouped["glm_5_2_tool_call"].append(row)
        elif row["llm_model"] == "[mk]GLM-5.2" and row["requested_output_mode"] == "json_schema_strict":
            grouped["glm_5_2_json_schema_strict"].append(row)
        elif row["llm_model"] == "[mk]Qwen3.6-27B" and row["requested_output_mode"] == "tool_call":
            grouped["qwen3_6_27b_tool_call"].append(row)
        elif row["llm_model"] == "[mk]Qwen3.6-27B" and row["requested_output_mode"] == "json_schema_strict":
            grouped["qwen3_6_27b_json_schema_strict"].append(row)
        else:
            raise SystemExit(f"unexpected adapter row: {row['label']}")

    adapters: dict[str, Any] = {}
    for name, items in grouped.items():
        total_calls = _sum_counts(items, "total_calls")
        schema_valid_calls = _sum_counts(items, "schema_valid_calls")
        schema_error_count = _sum_counts(items, "schema_error_count")
        fallback_event_count = _sum_counts(items, "fallback_event_count")
        infra_failure_count = schema_error_count + fallback_event_count
        schema_valid_rate = schema_valid_calls / total_calls if total_calls else 0.0
        infra_failure_rate = infra_failure_count / total_calls if total_calls else 1.0
        adapters[name] = {
            **MODEL_ADAPTERS[name],
            "repo_slice_count": len(items),
            "run_ids_public": [item["run_id"] for item in items],
            "total_calls": total_calls,
            "successful_calls": _sum_counts(items, "successful_calls"),
            "schema_valid_calls": schema_valid_calls,
            "schema_error_count": schema_error_count,
            "fallback_event_count": fallback_event_count,
            "fallback_used_count": _sum_counts(items, "fallback_used_count"),
            "infra_failure_count": infra_failure_count,
            "schema_valid_rate": round(schema_valid_rate, 6),
            "infra_failure_rate": round(infra_failure_rate, 6),
            "error_counts": _merge_counter(items, "error_counts"),
            "fallback_mode_counts": _merge_counter(items, "mode_counts"),
            "latency_ms_p50_mean": round(sum(float(i.get("latency_ms_p50") or 0) for i in items) / len(items), 3),
            "decision_records_in_artifact": any(i.get("decision_records_in_artifact") for i in items),
            "candidate_meta_in_artifact": any(i.get("candidate_meta_in_artifact") for i in items),
            "health_status": _health_status(schema_valid_rate, infra_failure_rate),
        }

    return {
        "schema_version": "b9a-adapter-health-report-v0",
        "status": "ok",
        "not_quality_leaderboard": True,
        "output_mode_is_adapter_config": True,
        "quality_metrics_excluded": True,
        "provider_calls_performed_by_b9a": 0,
        "new_provider_calls_in_report_generation": 0,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "provider_keys_in_artifact": False,
        "adapter_health_thresholds": {
            "quality_interpretable_schema_valid_rate_min": 0.95,
            "quality_interpretable_infra_failure_rate_max": 0.05,
        },
        "run_matrix": {
            "repo_slice_count_per_adapter": 2,
            "max_tasks_per_run": 6,
            "task_sample_mode": "round_robin_public_buckets",
        },
        "adapter_results": adapters,
        "practical_recommendations": {
            "glm_5_2_json_schema_strict": "not quality-interpretable in this small screen; improve schema/infra health before quality claims",
            "glm_5_2_tool_call": "not quality-interpretable; do not use on critical path",
            "qwen3_6_27b_json_schema_strict": "health pass on small sequential screen; candidate for cautious low-volume quality follow-up",
            "qwen3_6_27b_tool_call": "not quality-interpretable in this small screen; tool-call adapter still noisier than schema profile",
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# B9A Adapter Health Repair Screen",
        "",
        "B9A is an adapter-health report, not a quality leaderboard. It checks whether GLM/Qwen model profiles can reliably produce structured bounded candidate decisions under small live screens.",
        "",
        "| Adapter | Calls | Schema valid rate | Infra failure rate | Health status | Latency p50 mean ms |",
        "| --- | ---: | ---: | ---: | --- | ---: |",
    ]
    for name, row in report["adapter_results"].items():
        lines.append(
            f"| `{name}` | {row['total_calls']} | {row['schema_valid_rate']:.3f} | {row['infra_failure_rate']:.3f} | `{row['health_status']}` | {row['latency_ms_p50_mean']:.1f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Output mode is treated as a model-adapter configuration parameter, not an OpenLocus algorithm variable.",
        "- Qwen3.6-27B `json_schema_strict` passed this small sequential health screen and can be used for cautious low-volume follow-up.",
        "- GLM-5.2 `json_schema_strict` improved over the worst tool-call behavior, but it is still not quality-interpretable in this screen and should not yet be used for policy quality conclusions.",
        "- GLM-5.2 `tool_call` and Qwen `tool_call` remain too noisy for critical-path validation.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("artifacts/b9a_adapter_health_report/b9a_adapter_health_report.json"))
    ap.add_argument("--doc", type=Path, default=Path("docs/en/b9a-adapter-health-report.md"))
    args = ap.parse_args()
    report = build_report(args.input_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, args.doc)


if __name__ == "__main__":
    main()
