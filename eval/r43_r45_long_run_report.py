#!/usr/bin/env python3
"""R43-R45 long-run matrix, failure clusters, and promotion report.

This script consolidates R30-R42 artifacts into:
  * R43 real-model full-matrix summary,
  * R44 failure cluster deep dive,
  * R45 promotion candidate report.

It does not promote any strategy.  Missing/unavailable real providers remain
reason-only; no fake quality numbers are emitted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "r43-r45-long-run-report-v1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_manifest(root: Path) -> dict[str, Any]:
    paths = {
        "r30": root / "artifacts/r30/baseline_manifest.json",
        "r31": root / "artifacts/r31/provider_smoke.json",
        "r32": root / "artifacts/r32/view_bakeoff_report.json",
        "r33": root / "artifacts/r33/quiver_readiness.json",
        "r34_r36": root / "artifacts/r34_r36/quiver_anchor_proto.json",
        "r37_r38": root / "artifacts/r37_r38/llm_derived_stress_report.json",
        "r39_r40": root / "artifacts/r39_r40/symbol_regex_repair.json",
        "r41_r42": root / "artifacts/r41_r42/graph_admission.json",
    }
    return {key: {"path": str(path.relative_to(root)), "present": path.exists(), "data": load_json(path)} for key, path in paths.items()}


def r43_matrix(artifacts: dict[str, Any]) -> dict[str, Any]:
    r30 = artifacts["r30"]["data"]
    r32 = artifacts["r32"]["data"]
    r33 = artifacts["r33"]["data"]
    r34 = artifacts["r34_r36"]["data"]
    r37 = artifacts["r37_r38"]["data"]
    r39 = artifacts["r39_r40"]["data"]
    r41 = artifacts["r41_r42"]["data"]
    strategies: dict[str, Any] = {}
    for anchor in ["rrf", "query_noise_plus_rrf_agree_min", "symbol"]:
        strategies[f"r29_{anchor}"] = {
            "source": "R30 baseline freeze",
            "metrics": r30.get("r29_key_metrics", {}).get(anchor, {}),
            "role": r30.get("observations", {}).get(anchor, {}).get("role"),
        }
    for view, data in r32.get("view_results", {}).items():
        strategies[f"dense_view_{view}"] = {
            "source": "R32 view bakeoff",
            "status": data.get("status"),
            "role": "dense candidate/supporting-only",
            "metrics": data.get("metrics"),
        }
    strategies["quiver_readiness_bq_diag"] = {
        "source": "R33 BQ diagnostics",
        "role": "diagnostic_only",
        "metrics": r33.get("diagnostics", {}),
        "quiver_graph_implemented": r33.get("quiver_graph_implemented"),
    }
    for name, metrics in r34.get("results", {}).items():
        strategies[f"quiver_diag_{name}"] = {
            "source": "R34-R36 diagnostic prototype",
            "role": "candidate/supporting-only",
            "metrics": metrics,
        }
    strategies["llm_derived_views"] = {
        "source": "R37 derived views",
        "role": "derived-only not evidence",
        "metrics": {
            "derived_view_count": r37.get("derived_view_count"),
            "remote_calls": r37.get("remote_calls"),
            "artifact_secret_scan_clean": r37.get("safety_gates", {}).get("artifact_secret_scan_clean"),
        },
    }
    strategies["r38_failure_discovery_stress"] = {
        "source": "R38 stress expansion",
        "role": "failure_discovery_only not promotion",
        "metrics": {
            "stress_public_task_count": r37.get("stress_public_task_count"),
            "stress_by_category": r37.get("stress_by_category"),
            "label_quality": r37.get("stress_label_quality"),
        },
    }
    strategies["symbol_new"] = {
        "source": "R39 symbol repair",
        "role": "precision-anchor repair candidate",
        "metrics": r39.get("symbol_repair", {}).get("symbol_new"),
        "delta": {k: v for k, v in r39.get("symbol_repair", {}).items() if k.endswith("_delta")},
    }
    strategies["regex_hybrid_normalized"] = {
        "source": "R40 regex repair",
        "role": "query normalization candidate",
        "metrics": r39.get("regex_repair", {}).get("results", {}).get("regex_hybrid_normalized"),
    }
    strategies["graph_supporting_only"] = {
        "source": "R41 graph role research",
        "role": r41.get("graph_role_recommendation"),
        "metrics": {k: r41.get("metrics", {}).get(k) for k in ["graph_added_gold_span", "graph_added_false_span", "graph_expansion_blocked", "graph_explainer_precision"]},
    }
    strategies["admission_v2_rules"] = {
        "source": "R42 admission rules",
        "role": "explainable research only",
        "metrics": {k: r41.get("metrics", {}).get(k) for k in ["coverage", "selective_risk", "FileRecall@1", "SpanF0.5", "action_counts"]},
    }
    return {
        "schema_version": "r43-consolidated-real-model-readiness-summary-v1",
        "strategies": strategies,
        "datasets": ["R26/R29 baseline", "R32 self-test view bakeoff", "R38 failure discovery stress", "R39-R42 self-test tracks"],
        "compatibility_probes": {"CORE-Bench": "not_run", "ContextBench": "not_run"},
        "required_future_work": ["run real embeddings on CI corpus", "run R38 failure-discovery stress in non-promotion mode", "add CORE-Bench/ContextBench compatibility sample"],
    }


def r44_clusters(artifacts: dict[str, Any]) -> dict[str, Any]:
    r30 = artifacts["r30"]["data"]
    r33 = artifacts["r33"]["data"]
    r34 = artifacts["r34_r36"]["data"]
    r37 = artifacts["r37_r38"]["data"]
    r39 = artifacts["r39_r40"]["data"]
    r41 = artifacts["r41_r42"]["data"]
    clusters: list[dict[str, Any]] = []
    for name, count in r30.get("failure_clusters", {}).items():
        clusters.append({
            "cluster": name,
            "count": count,
            "affected_strategies": ["r29 matrix"],
            "likely_cause": "frozen R29 failure cluster",
            "recommended_next_fix": "covered by R30 baseline; re-evaluate in R43 full matrix",
            "needs_new_tests": True,
        })
    clusters.extend([
        {
            "cluster": "QUIVER_BQ_DISTRIBUTION_MISMATCH",
            "count": 1 if r33.get("diagnostics", {}).get("quiver_fit") != "promising" else 0,
            "affected_strategies": ["quiver_diag"],
            "unaffected_strategies": ["symbol", "regex"],
            "likely_cause": f"R33 fit={r33.get('diagnostics', {}).get('quiver_fit')}; graph not implemented",
            "recommended_next_fix": "test sharded/proto only; no default expansion",
            "needs_new_tests": True,
        },
        {
            "cluster": "QUIVER_GLOBAL_INDEX_MIXING_FAILURE",
            "count": 1 if r34.get("global_index_safe") is False else 0,
            "affected_strategies": ["global_mixed_all"],
            "likely_cause": "global mixing remains unsafe in diagnostic prototype",
            "recommended_next_fix": "continue per-view/language/source-test sharding bakeoff",
            "needs_new_tests": True,
        },
        {
            "cluster": "LLM_DERIVED_VIEW_HALLUCINATION",
            "count": 0,
            "affected_strategies": ["llm_derived"],
            "likely_cause": "offline deterministic run only; no real LLM content trusted",
            "recommended_next_fix": "when real LLM is used, require schema and source span validation",
            "needs_new_tests": True,
        },
        {
            "cluster": "GRAPH_ADDS_NO_GOLD",
            "count": r41.get("metrics", {}).get("graph_added_false_span", 0),
            "affected_strategies": ["graph_supporting_only"],
            "likely_cause": "graph edges are useful as support but still pollute expansion",
            "recommended_next_fix": "keep graph out of primary expansion; use as explanation/rerank feature only",
            "needs_new_tests": True,
        },
        {
            "cluster": "REGEX_NORMALIZATION_BUG",
            "count": None,
            "affected_strategies": ["regex_raw"],
            "unaffected_strategies": ["regex_hybrid_normalized"],
            "likely_cause": "user query should not be raw regex by default",
            "recommended_next_fix": r39.get("regex_repair", {}).get("default_recommendation"),
            "needs_new_tests": True,
        },
        {
            "cluster": "SYMBOL_EXTRACTION_MISS",
            "count": None,
            "affected_strategies": ["symbol_old"],
            "unaffected_strategies": ["symbol_new candidate"],
            "likely_cause": "missing impl/decorator/arrow/export patterns",
            "recommended_next_fix": "validate R39 repair on R26/R38 before integration",
            "needs_new_tests": True,
        },
        {
            "cluster": "DENSE_REAL_SEMANTIC_TRAP",
            "count": r37.get("stress_by_category", {}).get("dense_quiver_specific_trap", 0),
            "affected_strategies": ["dense_real", "quiver"],
            "likely_cause": "failure-discovery trap tasks generated, real model matrix pending",
            "recommended_next_fix": "run real embeddings supporting-only on R38 traps",
            "needs_new_tests": True,
        },
    ])
    return {"schema_version": "r44-failure-cluster-deep-dive-v1", "clusters": clusters}


def r45_report(artifacts: dict[str, Any], matrix: dict[str, Any], clusters: dict[str, Any]) -> dict[str, Any]:
    r30 = artifacts["r30"]["data"]
    r32 = artifacts["r32"]["data"]
    r33 = artifacts["r33"]["data"]
    r34 = artifacts["r34_r36"]["data"]
    r37 = artifacts["r37_r38"]["data"]
    r39 = artifacts["r39_r40"]["data"]
    r41 = artifacts["r41_r42"]["data"]
    blocking = [
        "real embeddings not yet run on full R26/R20/R15 matrix",
        "QuIVer graph remains diagnostic_only; no Vamana/default backend",
        "LLM-derived views are offline/failure-discovery only, not evidence",
        "graph expansion remains blocked",
        "R39/R40 repairs need broad R26/R38 regression validation",
        "CORE-Bench/ContextBench compatibility not run",
    ]
    return {
        "schema_version": "r45-promotion-report-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_ready": False,
        "current_default_should_change": False,
        "best_recall_channel": r30.get("current_best_recall_channel", "rrf"),
        "best_precision_anchor": r30.get("current_best_precision_anchor", "symbol"),
        "best_guard_candidate": r30.get("current_best_guard_candidate", "query_noise_plus_rrf_agree_min"),
        "best_dense_candidate": r32.get("conclusion", {}).get("best_dense_view"),
        "dense_recommendation": "continue_harness_only_supporting_only" if r32.get("provider") == "local_token_hash" else "hold",
        "quiver_recommendation": "continue_diagnostics_only" if r33.get("diagnostics", {}).get("quiver_fit") in {"mixed", "promising"} else "hold",
        "llm_derived_recommendation": "continue_derived_only_supporting_only" if r37.get("derived_view_count", 0) else "hold",
        "graph_recommendation": "explainer_only" if r41.get("metrics", {}).get("graph_expansion_blocked") else "rerank_only",
        "blocking_buckets": blocking,
        "next_required_tests": [
            "run R32 real embedding view bakeoff with path_plus_symbol then richer local-only views",
            "run R34-R36 on CI medium corpus with supporting-only outputs",
            "validate R39/R40 repair on R26 and R38 generated stress",
            "run R41/R42 admission rules on R26/R38 without changing defaults",
            "add CORE-Bench/ContextBench compatibility probe",
        ],
        "answers": {
            "current_default_should_change": False,
            "r29_query_noise_guard_still_best_guard": True,
            "dense_real_independent_positive_signal": "not_established; committed run is offline local_token_hash only",
            "dense_buckets_helped": r32.get("conclusion", {}).get("best_dense_view"),
            "dense_risk_buckets": ["negative_nonexistent", "semantic_trap", "proper_name_api_config"],
            "quiver_fit": r33.get("diagnostics", {}).get("quiver_fit"),
            "quiver_requires_sharding": True,
            "quiver_faster_noise_risk": "unknown; graph not implemented, diagnostic only",
            "llm_derived_gold_vs_false": "not measured; derived/stress only",
            "graph_role": r41.get("graph_role_recommendation"),
            "symbol_regex_repair_guard_recall_kill": "proxy improvements observed; broad guard validation pending",
            "promotion_blockers": blocking,
        },
        "evidencecore_changed": False,
        "core_changes": False,
        "source_artifacts": {key: {"path": value["path"], "present": value["present"]} for key, value in artifacts.items()},
        "safety_gates": {
            "no_promotion": True,
            "no_default_change": True,
            "no_evidencecore_change": True,
            "unavailable_reason_only": True,
            "remote_default_disabled": True,
            "llm_not_evidence": r37.get("llm_outputs_are_evidence") is False,
            "graph_default_blocked": r41.get("graph_default_expansion_allowed") is False,
            "quiver_graph_not_claimed": r34.get("quiver_graph_implemented") is False,
        },
    }


def write_docs(root: Path, matrix: dict[str, Any], clusters: dict[str, Any], report: dict[str, Any]) -> None:
    matrix_path = root / "docs/en/r43-real-model-full-matrix.md"
    cluster_path = root / "docs/en/r44-failure-clusters.md"
    report_path = root / "docs/en/r45-promotion-candidate-report.md"

    matrix_lines = [
        "# R43 Consolidated Real-Model Readiness Matrix",
        "",
        "R43 consolidates R30-R42 offline, diagnostic, and provider-smoke artifacts. It does not claim a completed full real-provider quality matrix, rerun unavailable providers, or emit fake quality numbers.",
        "",
        "| Strategy | Source | Role | Status |",
        "|---|---|---|---|",
    ]
    for name, data in matrix["strategies"].items():
        matrix_lines.append(f"| {name} | {data.get('source')} | {data.get('role')} | {data.get('status', 'ok')} |")
    matrix_lines.extend(["", "## Required Future Work", ""])
    for item in matrix.get("required_future_work", []):
        matrix_lines.append(f"- {item}")
    matrix_path.write_text("\n".join(matrix_lines) + "\n", encoding="utf-8")

    cluster_lines = ["# R44 Failure Clusters", "", "| Cluster | Count | Recommended next fix |", "|---|---:|---|"]
    for cluster in clusters["clusters"]:
        cluster_lines.append(f"| {cluster.get('cluster')} | {cluster.get('count')} | {cluster.get('recommended_next_fix')} |")
    cluster_path.write_text("\n".join(cluster_lines) + "\n", encoding="utf-8")

    report_lines = [
        "# R45 Promotion Candidate Report",
        "",
        "R45 concludes the R30-R45 real-model readiness and diagnostic expansion pass. Full real-provider quality evidence is still pending, and default promotion remains blocked.",
        "",
        "## Decision",
        "",
        f"- promotion_ready: `{report['promotion_ready']}`",
        f"- current_default_should_change: `{report['current_default_should_change']}`",
        f"- best_recall_channel: `{report['best_recall_channel']}`",
        f"- best_precision_anchor: `{report['best_precision_anchor']}`",
        f"- best_guard_candidate: `{report['best_guard_candidate']}`",
        f"- dense_recommendation: `{report['dense_recommendation']}`",
        f"- quiver_recommendation: `{report['quiver_recommendation']}`",
        f"- llm_derived_recommendation: `{report['llm_derived_recommendation']}`",
        f"- graph_recommendation: `{report['graph_recommendation']}`",
        "",
        "## Blocking Buckets",
        "",
    ]
    for item in report["blocking_buckets"]:
        report_lines.append(f"- {item}")
    report_lines.extend(["", "## Next Required Tests", ""])
    for item in report["next_required_tests"]:
        report_lines.append(f"- {item}")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    artifacts = artifact_manifest(root)
    missing = [key for key, value in artifacts.items() if not value["present"]]
    if missing:
        raise SystemExit(f"missing required artifacts: {missing}")
    matrix = r43_matrix(artifacts)
    clusters = r44_clusters(artifacts)
    report = r45_report(artifacts, matrix, clusters)
    out = {"schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(), "r43_matrix": matrix, "r44_clusters": clusters, "r45_report": report}
    write_json(root / "docs/r45-promotion-candidate-report.json", report)
    write_json(root / "artifacts/r43_r45/long_run_report.json", out)
    write_docs(root, matrix, clusters, report)
    print("Wrote artifacts/r43_r45/long_run_report.json")
    print("Wrote docs/en/r43-real-model-full-matrix.md")
    print("Wrote docs/en/r44-failure-clusters.md")
    print("Wrote docs/en/r45-promotion-candidate-report.md")
    print("Wrote docs/r45-promotion-candidate-report.json")


if __name__ == "__main__":
    main()
