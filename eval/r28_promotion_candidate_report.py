#!/usr/bin/env python3
"""R28 promotion candidate report.

R28 is intentionally a synthesis step, not a promotion step. It reads already
validated R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets
and produces a conservative promotion candidate report with
promotion_ready=false by default.

No retrieval CLI is invoked. No labels are used for routing. No core code is
changed. R20 weak/mined labels and R26 deterministic/metamorphic/mined/stress
oracle labels are treated as failure-discovery evidence only, never as
promotion evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"ERROR: required artifact missing: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def metric(report: dict[str, Any], strategy: str, name: str, default: Any = None) -> Any:
    return report.get("metrics", {}).get(strategy, {}).get(name, default)


def require(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def fmt_float(value: Any, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def build_report(workspace: Path) -> dict[str, Any]:
    r21 = load_json(workspace / "runs" / "r21-auto-wide-report.json")
    r23 = load_json(workspace / "runs" / "r23-guard-sweep.json")
    r24 = load_json(workspace / "runs" / "r24-quiver-tdb-probe.json")
    r25 = load_json(workspace / "runs" / "r25-graph-dense-ablation-report.json")
    r26_summary = load_json(workspace / "fixtures" / "r26_auto_stress" / "summary.json")
    r26_safety = load_json(workspace / "fixtures" / "r26_auto_stress" / "safety_checks.json")

    issues: list[str] = []
    require(r21.get("schema_version") == "r21-v1", "R21 schema_version must be r21-v1", issues)
    require(r23.get("schema_version") == "r23-v1", "R23 schema_version must be r23-v1", issues)
    require(r24.get("schema_version") == "r24-v1", "R24 schema_version must be r24-v1", issues)
    require(r25.get("schema_version") == "r25-v1", "R25 schema_version must be r25-v1", issues)
    require(r26_safety.get("task_count") == r26_summary.get("total_tasks"), "R26 safety/summary task counts must match", issues)

    require(r21.get("promotion_ready") is False, "R21 promotion_ready must be false", issues)
    require(r21.get("not_promotion_evidence") is True, "R21 not_promotion_evidence must be true", issues)
    require(r21.get("safety_gates", {}).get("all_passed") is True, "R21 safety gates must pass", issues)
    require(r21.get("core_changes") is False, "R21 core_changes must be false", issues)
    require(r21.get("remote_calls") == 0, "R21 remote_calls must be 0", issues)
    require(r23.get("promotion_ready") is False, "R23 promotion_ready must be false", issues)
    require(r23.get("not_promotion_evidence") is True, "R23 not_promotion_evidence must be true", issues)
    require(r23.get("safety_checks", {}).get("artifact_files_sha_bytes_lines_verified") is True, "R23 artifacts must be verified", issues)
    require(r23.get("core_changes") is False, "R23 core_changes must be false", issues)
    require(r23.get("remote_calls") == 0, "R23 remote_calls must be 0", issues)
    require(r24.get("promotion_ready") is False, "R24 promotion_ready must be false", issues)
    require(r24.get("not_promotion_evidence") is True, "R24 not_promotion_evidence must be true", issues)
    require(r24.get("safety_gates", {}).get("all_passed") is True, "R24 safety gates must pass", issues)
    require(r24.get("quiver_implemented") is False, "R24 must confirm QuIVer unavailable", issues)
    require(r24.get("core_changes") is False, "R24 core_changes must be false", issues)
    require(r24.get("remote_calls") == 0, "R24 remote_calls must be 0", issues)
    require(r24.get("dense_or_llm_claims") is False, "R24 dense_or_llm_claims must be false", issues)
    require(r25.get("promotion_ready") is False, "R25 promotion_ready must be false", issues)
    require(r25.get("not_promotion_evidence") is True, "R25 not_promotion_evidence must be true", issues)
    require(r25.get("safety_gates", {}).get("all_passed") is True, "R25 safety gates must pass", issues)
    require(r25.get("r21_artifact_manifest_verification", {}).get("passed") is True, "R25 R21 manifest verification must pass", issues)
    require(r25.get("core_changes") is False, "R25 core_changes must be false", issues)
    require(r25.get("remote_calls") == 0, "R25 remote_calls must be 0", issues)
    require(r25.get("dense_or_llm_claims") is False, "R25 dense_or_llm_claims must be false", issues)
    require(r26_safety.get("passed") is True, "R26 safety checks must pass", issues)
    require(r26_safety.get("task_count") == 1100, "R26 task_count must be 1100", issues)
    require(r26_safety.get("not_promotion_evidence") is True, "R26 not_promotion_evidence must be true", issues)
    require(r26_safety.get("core_changes") is False, "R26 core_changes must be false", issues)
    require(r26_safety.get("remote_calls") == 0, "R26 remote_calls must be 0", issues)
    require(r26_safety.get("dense_or_llm_claims") is False, "R26 dense_or_llm_claims must be false", issues)

    if issues:
        print("ERROR: R28 source artifact validation failed", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    r21_key = {
        "rrf": {
            "FileRecall@1": metric(r21, "rrf", "FileRecall@1"),
            "MRR": metric(r21, "rrf", "MRR"),
            "SpanF0.5": metric(r21, "rrf", "SpanF0.5"),
            "primary_false_positive_rate": metric(r21, "rrf", "primary_false_positive_rate"),
            "abstain_rate": metric(r21, "rrf", "abstain_rate"),
        },
        "symbol": {
            "FileRecall@1": metric(r21, "symbol", "FileRecall@1"),
            "SpanPrecision": metric(r21, "symbol", "SpanPrecision"),
            "SpanF0.5": metric(r21, "symbol", "SpanF0.5"),
            "primary_false_positive_rate": metric(r21, "symbol", "primary_false_positive_rate"),
            "abstain_rate": metric(r21, "symbol", "abstain_rate"),
        },
        "query_noise_plus_rrf_agree_min": {
            "FileRecall@1": metric(r21, "query_noise_plus_rrf_agree_min", "FileRecall@1"),
            "primary_false_positive_rate": metric(r21, "query_noise_plus_rrf_agree_min", "primary_false_positive_rate"),
            "guard_recall_kill_rate": metric(r21, "query_noise_plus_rrf_agree_min", "guard_recall_kill_rate"),
            "abstain_rate": metric(r21, "query_noise_plus_rrf_agree_min", "abstain_rate"),
        },
    }

    for strategy, values in r21_key.items():
        for key, value in values.items():
            require(value is not None, f"R21 metric {strategy}.{key} must be non-null", issues)

    if issues:
        print("ERROR: R28 metric validation failed", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)

    r23_observations = r23.get("observations", [])
    r23_blocked = r23.get("blocked_bucket_counts", {})

    dense_metrics = r24.get("dense_mock_probe", {}).get("metrics", {})
    dense_fusion = r24.get("dense_mock_plus_rrf", {}).get("metrics", {})
    graph_contribution = r25.get("ablation_metrics", {}).get("graph_contribution", {})
    dense_contribution = r25.get("ablation_metrics", {}).get("dense_contribution", {})
    combined_contribution = r25.get("ablation_metrics", {}).get("combined_contribution", {})

    recommendation = {
        "promotion_ready": False,
        "best_default_candidate": "no_change_current_evidence_gated_local_retrieval",
        "best_recall_channel": "rrf",
        "best_precision_anchor": "symbol",
        "best_dense_candidate": "none_available_for_default; dense_mock is safety/noise probe only",
        "quiver_recommendation": "hold",
        "graph_recommendation": "hold_default_expansion; graph may remain explicit/supporting only",
        "dense_recommendation": "supporting_only_after_real_embedding_bakeoff; mock dense rejected for quality",
        "default_should_change": False,
    }

    blocking_evidence_gaps = [
        "R26 auto-stress has static validation only; no retrieval runner/scorer matrix yet.",
        "R20 labels are weak/mined and R26 oracle types are deterministic/metamorphic/mined/stress; neither is human-verified promotion evidence.",
        "R23 all 51 guard strategies have bucket regressions; guard generalization is blocked.",
        "QuIVer is not implemented, so no BQ/ANN compatibility or quality evidence exists.",
        "Dense real provider is unavailable; dense_mock is non-semantic and mostly noise.",
        "Graph depth=1 ablation adds more false spans than gold spans.",
        "No broad human-verified stress/negative benchmark for default policy decisions.",
    ]

    next_required_tests = [
        "Run R26 auto-stress with R21/R24/R25 strategy matrix under runner/scorer separation.",
        "Add human-verified labels for high-impact R20/R26 failure buckets.",
        "Implement real embedding provider bakeoff only after R26 runner gates exist.",
        "If QuIVer is implemented, run per-view/per-language/per-repo sharded compatibility diagnostics before quality claims.",
        "Extend failure attribution to consume R24/R25/R26 artifacts, not only R21 artifacts.",
        "Add guard bucket regression gates to any candidate default policy.",
    ]

    answers = {
        "current_default_should_change": {
            "answer": False,
            "why": "RRF is the strongest recall channel but has high false-primary/no-gold rate on auto-wide; guards reduce risk but show bucket regressions; graph/dense expansions are net-negative.",
        },
        "query_noise_plus_rrf_agree_min_stability": {
            "answer": "not_stable_enough_for_promotion",
            "evidence": {
                "r21_file_recall_at_1": r21_key["query_noise_plus_rrf_agree_min"]["FileRecall@1"],
                "r21_primary_false_positive_rate": r21_key["query_noise_plus_rrf_agree_min"]["primary_false_positive_rate"],
                "r21_guard_recall_kill_rate": r21_key["query_noise_plus_rrf_agree_min"]["guard_recall_kill_rate"],
                "r23_bucket_regressions": r23_blocked,
            },
        },
        "quiver_tdb_independent_quality_gain": {
            "answer": "no_evidence_yet",
            "why": "QuIVer is not implemented; TDB is not an ANN/search backend in default build; R24 reports unavailable/not_measured rather than quality numbers.",
        },
        "graph_added_more_gold_than_noise": {
            "answer": False,
            "evidence": graph_contribution,
        },
        "dense_quiver_supporting_channel_only": {
            "answer": True,
            "why": "Dense mock is non-semantic and noisy; QuIVer is unavailable. Any future dense/QuIVer channel must remain candidate/supporting and pass EvidenceCore materialization.",
        },
        "coverage_gaps": blocking_evidence_gaps,
    }

    return {
        "schema_version": "r28-v1",
        "program": "R28 Promotion Candidate Report",
        "promotion_ready": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "remote_calls": 0,
        "source_artifacts_validated": True,
        "source_validation_scope": "schema_versions, promotion flags, safety gates, core_changes, remote_calls, dense_or_llm_claim flags where present, selected key metrics non-null, R26 task count consistency",
        "source_artifacts": {
            "r21": "runs/r21-auto-wide-report.json",
            "r23": "runs/r23-guard-sweep.json",
            "r24": "runs/r24-quiver-tdb-probe.json",
            "r25": "runs/r25-graph-dense-ablation-report.json",
            "r26_summary": "fixtures/r26_auto_stress/summary.json",
            "r26_safety": "fixtures/r26_auto_stress/safety_checks.json",
        },
        "recommendation": recommendation,
        "answers": answers,
        "r21_key_metrics": r21_key,
        "r23_guard_observations": {
            "sweep_count": r23.get("sweep_count"),
            "blocked_bucket_counts": r23_blocked,
            "observations": r23_observations,
        },
        "r24_dense_quiver_tdb_findings": {
            "quiver_implemented": r24.get("quiver_implemented"),
            "dense_mock_candidate_total": r24.get("dense_mock_probe", {}).get("candidate_total"),
            "dense_mock_metrics": {
                "FileRecall@1": dense_metrics.get("FileRecall@1"),
                "MRR": dense_metrics.get("MRR"),
                "primary_false_positive_rate": dense_metrics.get("primary_false_positive_rate"),
                "token_waste": dense_metrics.get("token_waste"),
            },
            "dense_mock_plus_rrf_metrics": {
                "FileRecall@1": dense_fusion.get("FileRecall@1"),
                "MRR": dense_fusion.get("MRR"),
                "primary_false_positive_rate": dense_fusion.get("primary_false_positive_rate"),
                "token_waste": dense_fusion.get("token_waste"),
            },
            "tdb_stale_leak_count": r24.get("tdb_stale_leak_count"),
        },
        "r25_graph_dense_ablation_findings": {
            "graph_contribution": graph_contribution,
            "dense_contribution": dense_contribution,
            "combined_contribution": combined_contribution,
        },
        "r26_auto_stress_status": {
            "total_tasks": r26_summary.get("total_tasks"),
            "total_labels": r26_summary.get("total_labels"),
            "categories": r26_summary.get("categories"),
            "safety_passed": r26_safety.get("passed"),
            "expected_behavior_distribution": r26_safety.get("expected_behavior_distribution"),
            "oracle_type_distribution": r26_safety.get("oracle_type_distribution"),
        },
        "blocking_evidence_gaps": blocking_evidence_gaps,
        "next_required_tests": next_required_tests,
    }


def render_markdown(report: dict[str, Any]) -> str:
    rec = report["recommendation"]
    r21 = report["r21_key_metrics"]
    r23 = report["r23_guard_observations"]
    r24 = report["r24_dense_quiver_tdb_findings"]
    r25 = report["r25_graph_dense_ablation_findings"]
    r26 = report["r26_auto_stress_status"]

    lines: list[str] = []
    lines.append("# R28 Promotion Candidate Report")
    lines.append("")
    lines.append("R28 is a conservative synthesis of R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets. It is **not** a promotion step. It exists to state what cannot yet be promoted and why.")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(rec, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("## Direct answers")
    lines.append("")
    lines.append("1. **Current default should change?** No. RRF is strongest recall, but false-primary risk remains high; guard strategies still have bucket regressions; graph/dense expansions are net-negative.")
    lines.append("2. **If not, why?** The evidence base is failure-oriented rather than promotion-grade: R20 labels are weak/mined, R26 oracle types are deterministic/metamorphic/mined/stress, no human-verified promotion tier covers the new stress space, and R26 has no retrieval runner/scorer matrix yet.")
    lines.append("3. **`query_noise_plus_rrf_agree_min` stable on auto-wide/auto-stress?** Not stable enough. R21 shows useful risk reduction without recall kill, but R23 finds bucket regressions across the entire sweep and R26 has not been run through a retrieval runner/scorer matrix yet.")
    lines.append("4. **QuIVer/TDB independent quality gain?** No evidence. QuIVer is not implemented; TDB is not an ANN/search backend in default build.")
    lines.append("5. **QuIVer/TDB gains by bucket?** Unknown; unavailable/not_measured.")
    lines.append("6. **QuIVer/TDB risks by bucket?** Hypothesized dense semantic traps, proper-name/API/config regressions, and stale candidates; R26 now has stress data for future measurement.")
    lines.append("7. **Graph adds gold more than noise?** No. R25 graph contribution: added_gold=0, added_false=435; default expansion blocked.")
    lines.append("8. **Dense/QuIVer supporting channel only?** Yes. Dense mock is noisy and non-semantic; QuIVer is unavailable. Future dense/QuIVer must remain candidate/supporting until real bakeoff evidence exists.")
    lines.append("9. **Coverage gaps?** See blocking gaps below.")
    lines.append("")
    lines.append("## Key metrics")
    lines.append("")
    lines.append("| Finding | Evidence |")
    lines.append("|---|---|")
    lines.append(f"| RRF recall | FileRecall@1={fmt_float(r21['rrf']['FileRecall@1'])}, MRR={fmt_float(r21['rrf']['MRR'])}, primary_false_positive_rate={fmt_float(r21['rrf']['primary_false_positive_rate'])} |")
    lines.append(f"| Symbol precision anchor | SpanPrecision={fmt_float(r21['symbol']['SpanPrecision'])}, SpanF0.5={fmt_float(r21['symbol']['SpanF0.5'])}, primary_false_positive_rate={fmt_float(r21['symbol']['primary_false_positive_rate'])}, abstain_rate={fmt_float(r21['symbol']['abstain_rate'])} |")
    lines.append(f"| Query-noise guard | FileRecall@1={fmt_float(r21['query_noise_plus_rrf_agree_min']['FileRecall@1'])}, primary_false_positive_rate={fmt_float(r21['query_noise_plus_rrf_agree_min']['primary_false_positive_rate'])}, guard_recall_kill_rate={fmt_float(r21['query_noise_plus_rrf_agree_min']['guard_recall_kill_rate'])} |")
    lines.append(f"| R23 guard sweep | sweep_count={r23['sweep_count']}, strategies_with_bucket_regression={r23['blocked_bucket_counts'].get('strategies_with_bucket_regression')}/{r23['blocked_bucket_counts'].get('total_strategies')}, total_bucket_regressions={r23['blocked_bucket_counts'].get('total_bucket_regressions')} |")
    lines.append(f"| Dense mock | candidates={r24['dense_mock_candidate_total']}, FileRecall@1={fmt_float(r24['dense_mock_metrics']['FileRecall@1'])}, primary_false_positive_rate={fmt_float(r24['dense_mock_metrics']['primary_false_positive_rate'])}, token_waste={fmt_float(r24['dense_mock_metrics']['token_waste'])} |")
    lines.append(f"| Graph ablation | added_gold={r25['graph_contribution'].get('graph_added_gold_span')}, added_false={r25['graph_contribution'].get('graph_added_false_span')}, blocked={r25['graph_contribution'].get('graph_default_expansion_blocked')} |")
    lines.append(f"| Dense ablation | added_gold={r25['dense_contribution'].get('dense_added_gold_span')}, added_false={r25['dense_contribution'].get('dense_added_false_span')}, blocked={r25['dense_contribution'].get('dense_default_expansion_blocked')} |")
    lines.append(f"| R26 stress coverage | tasks={r26['total_tasks']}, categories={len(r26['categories']) if isinstance(r26['categories'], dict) else 'unknown'}, safety_passed={r26['safety_passed']} |")
    lines.append("")
    lines.append("## Blocking evidence gaps")
    lines.append("")
    for gap in report["blocking_evidence_gaps"]:
        lines.append(f"- {gap}")
    lines.append("")
    lines.append("## Next required tests")
    lines.append("")
    for test in report["next_required_tests"]:
        lines.append(f"- {test}")
    lines.append("")
    lines.append("## Safety and scope")
    lines.append("")
    lines.append("- promotion_ready=false")
    lines.append("- not_promotion_evidence=true")
    lines.append("- core_changes=false")
    lines.append("- remote_calls=0")
    lines.append("- R28 source validation checks schema versions, promotion flags, safety gates, core_changes, remote_calls, dense_or_llm_claim flags where present, selected non-null key metrics, and R26 task count consistency before synthesis.")
    lines.append("- Candidate remains candidate: no BM25/RRF/regex/symbol/graph/dense/TDB/QuIVer/LLM-derived output is treated as fact without EvidenceCore materialization.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate R28 promotion candidate report")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--json-out", default="docs/r28-promotion-candidate-report.json")
    parser.add_argument("--md-out", default="docs/en/r28-promotion-candidate-report.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = build_report(workspace)
    json_out = workspace / args.json_out
    md_out = workspace / args.md_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")
    print("promotion_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
