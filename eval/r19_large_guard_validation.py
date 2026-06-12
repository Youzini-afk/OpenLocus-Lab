#!/usr/bin/env python3
"""R19 Large/Stress Guard Generalization Validation.

Eval-layer research only. Does NOT change Rust core.

Validates whether R18 train-selected guard strategies generalize to R15-L
(294 weak/mined tasks) and R15-stress. R15-L labels are mostly weak/mined;
used only for generalization smoke, not as promotion evidence.

Safety:
- Hard fail if source report safety_passed is not true
- Hard fail if citation_validity < 1.0 for any method with evidence
- Hard fail if citation_hash_checked is not true (or citation_not_applicable
  is not true) for any method
- Hard fail if canary_retrieval.passed is not true where present
- Hard fail if baseline prediction/report metrics are inconsistent
- Citation safety is inherited from source validated predictions, not re-claimed
- No remote calls; all benchmarks are local-only
- No LLM/dense claims

Usage:
    python3 eval/r19_large_guard_validation.py \\
        --openlocus target/debug/openlocus \\
        --workspace . \\
        --out runs/r19-large-guard-validation.json

    # Reuse existing R19-owned reports/predictions:
    python3 eval/r19_large_guard_validation.py \\
        --skip-run \\
        --workspace . \\
        --out runs/r19-large-guard-validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = "r19-v1"

METHODS = ["regex", "bm25", "symbol", "rrf"]

# Guard strategies to validate
GUARD_STRATEGIES = [
    "query_only_router_v0",
    "rrf_guarded_by_symbol_regex",
    "query_noise_plus_rrf_agree_min_0.0",
    "query_noise_plus_rrf_agree_min_0.02",
    "query_noise_plus_rrf_score_min_0.02",
]

# ── Utility ────────────────────────────────────────────────────────────────


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prediction_provenance(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "jsonl_lines": sum(1 for line in text.splitlines() if line.strip()),
    }


def generic_prediction_path(runs_dir: Path, tier_name: str, method: str) -> Path:
    return runs_dir / f"r15-{tier_name}-{method}-predictions.jsonl"


def owned_prediction_path(runs_dir: Path, tier_name: str, method: str) -> Path:
    return runs_dir / f"r19-r15-{tier_name}-{method}-predictions.jsonl"


def _fmt(val: Any) -> str:
    if isinstance(val, float):
        return f"{val:.4f}"
    if val is None:
        return "N/A"
    return str(val)


# ── R19-owned prediction materialization ────────────────────────────────────


def materialize_owned_prediction_artifacts(runs_dir: Path) -> dict[str, dict[str, Any]]:
    """Copy generic R15 prediction outputs into R19-owned artifact names."""
    provenance: dict[str, dict[str, Any]] = {}
    for tier_name in ["large", "stress"]:
        provenance[tier_name] = {}
        for method in METHODS:
            src = generic_prediction_path(runs_dir, tier_name, method)
            dst = owned_prediction_path(runs_dir, tier_name, method)
            if not src.exists():
                print(
                    f"CRITICAL: Missing generic prediction file after run: {src}",
                    file=sys.stderr,
                )
                sys.exit(1)
            shutil.copy2(src, dst)
            provenance[tier_name][method] = prediction_provenance(dst)
    return provenance


def require_owned_prediction_artifacts(runs_dir: Path) -> dict[str, dict[str, Any]]:
    """Require R19-owned prediction artifacts; never fall back to generic files."""
    provenance: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for tier_name in ["large", "stress"]:
        provenance[tier_name] = {}
        for method in METHODS:
            path = owned_prediction_path(runs_dir, tier_name, method)
            if not path.exists():
                missing.append(str(path))
            else:
                provenance[tier_name][method] = prediction_provenance(path)
    if missing:
        print(
            "CRITICAL: Missing R19-owned prediction artifacts:", file=sys.stderr
        )
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)
    return provenance


# ── R17/R18 helper imports ──────────────────────────────────────────────────


def _import_r17_helpers(workspace: Path):
    """Import R17 helper functions, resolving sys.path robustly."""
    eval_dir = str(workspace / "eval")
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    try:
        from r17_router_guard_experiment import (  # type: ignore[import-not-found]
            load_jsonl,
            load_report,
            resolve_path,
            verify_safety_gates,
            check_baseline_prediction_consistency,
            score_predictions,
            compute_deltas,
            is_negative_noise_query,
            is_vague_multi_word_query,
            is_compound_snake_case_noise,
            is_exact_identifier,
            has_identifier_tokens,
            route_query_only_v0,
            route_rrf_guarded_by_symbol_regex,
            apply_strategy,
            NEGATIVE_NOISE_MARKERS,
            COMMON_WORDS,
        )
        return {
            "load_jsonl": load_jsonl,
            "load_report": load_report,
            "resolve_path": resolve_path,
            "verify_safety_gates": verify_safety_gates,
            "check_baseline_prediction_consistency": check_baseline_prediction_consistency,
            "score_predictions": score_predictions,
            "compute_deltas": compute_deltas,
            "is_negative_noise_query": is_negative_noise_query,
            "is_vague_multi_word_query": is_vague_multi_word_query,
            "is_compound_snake_case_noise": is_compound_snake_case_noise,
            "is_exact_identifier": is_exact_identifier,
            "has_identifier_tokens": has_identifier_tokens,
            "route_query_only_v0": route_query_only_v0,
            "route_rrf_guarded_by_symbol_regex": route_rrf_guarded_by_symbol_regex,
            "apply_strategy": apply_strategy,
            "NEGATIVE_NOISE_MARKERS": NEGATIVE_NOISE_MARKERS,
            "COMMON_WORDS": COMMON_WORDS,
        }
    except ImportError as e:
        print(
            f"ERROR: Cannot import R17 helpers from {eval_dir}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


# ── R18 strategy imports ────────────────────────────────────────────────────


def _import_r18_helpers(workspace: Path):
    """Import R18 routing functions."""
    eval_dir = str(workspace / "eval")
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    try:
        from r18_calibration_sweep import (  # type: ignore[import-not-found]
            route_query_noise_plus_rrf_agree_min,
            route_query_noise_plus_rrf_score_min,
            is_query_noise,
            extract_query_features,
        )
        return {
            "route_query_noise_plus_rrf_agree_min": route_query_noise_plus_rrf_agree_min,
            "route_query_noise_plus_rrf_score_min": route_query_noise_plus_rrf_score_min,
            "is_query_noise": is_query_noise,
            "extract_query_features": extract_query_features,
        }
    except ImportError as e:
        print(
            f"ERROR: Cannot import R18 helpers from {eval_dir}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


# ── Guard strategy application ──────────────────────────────────────────────


def apply_guard_strategy(
    strategy_name: str,
    tasks: list[dict],
    predictions_by_method: dict[str, list[dict]],
    r17_helpers: dict,
    r18_helpers: dict,
) -> list[dict]:
    """Apply a guard strategy to produce predictions.

    Route decisions use only query text + prediction features.
    Labels/gold are NOT accessed.
    """
    results: list[dict] = []

    for task in tasks:
        task_id = task["task_id"]
        query = task["query"]
        repo_id = task.get("repo_id", "")

        evidence: list[dict] = []
        route_decision = ""
        selected_method = ""

        if strategy_name == "query_only_router_v0":
            evidence, route_decision, selected_method = r17_helpers[
                "route_query_only_v0"
            ](query, predictions_by_method, task_id, repo_id)

        elif strategy_name == "rrf_guarded_by_symbol_regex":
            evidence, route_decision, selected_method = r17_helpers[
                "route_rrf_guarded_by_symbol_regex"
            ](predictions_by_method, task_id, repo_id)

        elif strategy_name.startswith("query_noise_plus_rrf_agree_min_"):
            threshold = float(strategy_name.split("_")[-1])
            evidence, route_decision, selected_method, _ = (
                r18_helpers["route_query_noise_plus_rrf_agree_min"](
                    threshold,
                    predictions_by_method,
                    task_id,
                    repo_id,
                    query,
                    r17_helpers["is_negative_noise_query"],
                    r17_helpers["is_vague_multi_word_query"],
                    r17_helpers["is_compound_snake_case_noise"],
                )
            )

        elif strategy_name.startswith("query_noise_plus_rrf_score_min_"):
            threshold = float(strategy_name.split("_")[-1])
            evidence, route_decision, selected_method, _ = (
                r18_helpers["route_query_noise_plus_rrf_score_min"](
                    threshold,
                    predictions_by_method,
                    task_id,
                    repo_id,
                    query,
                    r17_helpers["is_negative_noise_query"],
                    r17_helpers["is_vague_multi_word_query"],
                    r17_helpers["is_compound_snake_case_noise"],
                )
            )

        else:
            route_decision = "unknown_strategy"
            selected_method = "empty"

        results.append(
            {
                "task_id": task_id,
                "query": query,
                "method": strategy_name,
                "repo_id": repo_id,
                "evidence": evidence,
                "returncode": 0,
                "strategy_name": strategy_name,
                "selected_method": selected_method,
                "route_decision": route_decision,
            }
        )

    return results


# ── Label quality analysis ──────────────────────────────────────────────────


def analyze_label_quality(labels: list[dict], tier_name: str) -> dict[str, Any]:
    """Analyze label quality counts for a tier."""
    quality_counts: dict[str, int] = {}
    has_gold = 0
    has_hard_neg = 0
    negative = 0

    for label in labels:
        q = label.get("label_quality", "unknown")
        quality_counts[q] = quality_counts.get(q, 0) + 1
        if label.get("gold_spans"):
            has_gold += 1
        if label.get("hard_negatives"):
            has_hard_neg += 1
        if not label.get("gold_spans"):
            negative += 1

    if tier_name == "large":
        caveat = (
            "R15-L labels are mostly weak/mined; used only for generalization "
            "smoke, not as promotion evidence."
        )
    elif tier_name == "stress":
        caveat = (
            "R15-stress has only 19 tasks and mostly weak labels; used only as "
            "a small false-positive stress surface, not as promotion evidence."
        )
    else:
        caveat = "Label quality varies by tier; not promotion evidence."

    return {
        "total": len(labels),
        "quality_counts": quality_counts,
        "has_gold_spans": has_gold,
        "has_hard_negatives": has_hard_neg,
        "negative_count": negative,
        "caveat": caveat,
    }


# ── Generalization assessment ───────────────────────────────────────────────


def compute_generalization_assessment(
    strategy_metrics: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Compute the generalization assessment fields."""
    large_metrics = strategy_metrics.get("large", {})
    stress_metrics = strategy_metrics.get("stress", {})

    # selected_candidate_large_ok: rrf_guarded large FileRecall@1 >= RRF - 0.05
    # and negative_nonempty <= RRF
    rrf_large = large_metrics.get("rrf", {})
    guarded_large = large_metrics.get("rrf_guarded_by_symbol_regex", {})

    rrf_large_recall1 = rrf_large.get("file_recall@1", 0.0)
    guarded_large_recall1 = guarded_large.get("file_recall@1", 0.0)
    rrf_large_neg = rrf_large.get("negative_nonempty_rate@10", 1.0)
    guarded_large_neg = guarded_large.get("negative_nonempty_rate@10", 1.0)

    selected_candidate_large_ok = (
        guarded_large_recall1 >= rrf_large_recall1 - 0.05
        and guarded_large_neg <= rrf_large_neg
    )

    # selected_candidate_stress_ok: rrf_guarded stress negative_nonempty
    # <= symbol stress negative_nonempty
    symbol_stress = stress_metrics.get("symbol", {})
    guarded_stress = stress_metrics.get("rrf_guarded_by_symbol_regex", {})

    symbol_stress_neg = symbol_stress.get("negative_nonempty_rate@10", 1.0)
    guarded_stress_neg = guarded_stress.get("negative_nonempty_rate@10", 1.0)

    selected_candidate_stress_ok = guarded_stress_neg <= symbol_stress_neg

    # stress_zero_observation_repeated: query_noise_plus_rrf_agree_min_0.0
    # stress negative_nonempty == 0.0
    agree_zero_stress = stress_metrics.get(
        "query_noise_plus_rrf_agree_min_0.0", {}
    )
    agree_zero_stress_neg = agree_zero_stress.get("negative_nonempty_rate@10", None)
    stress_zero_observation_repeated = agree_zero_stress_neg == 0.0

    return {
        "selected_candidate_large_ok": selected_candidate_large_ok,
        "selected_candidate_stress_ok": selected_candidate_stress_ok,
        "stress_zero_observation_repeated": stress_zero_observation_repeated,
        "promotion_ready": False,
        "promotion_reason": (
            "R15-L labels are weak/mined; R15-stress has only 19 tasks. "
            "No promotion from R19 generalization smoke. "
            "Requires human-verified labels and larger stress dataset."
        ),
    }


# ── Markdown generation ─────────────────────────────────────────────────────


def generate_markdown_report(
    strategy_metrics: dict[str, dict[str, dict[str, Any]]],
    deltas_vs_rrf: dict[str, dict[str, dict[str, float]]],
    deltas_vs_symbol: dict[str, dict[str, dict[str, float]]],
    label_quality: dict[str, dict[str, Any]],
    generalization: dict[str, Any],
    safety_issues: list[str],
    source_safety: dict[str, Any],
    conclusions: list[str],
    caveats: list[str],
) -> str:
    lines = [
        "# R19 Large/Stress Guard Generalization Validation",
        "",
        "**Eval-layer research only. Does NOT change Rust core.**",
        "",
        "## Safety",
        "",
    ]

    if safety_issues:
        for issue in safety_issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines.append("All source safety gates passed.")
        lines.append(
            "Citation safety is inherited from source validated predictions; "
            "no new citation validation is claimed."
        )
        lines.append("")

    lines.append("### Source Report Safety Summary")
    lines.append("")
    for key, val in source_safety.items():
        lines.append(f"- {key}: {val}")
    lines.append("")

    # Label quality
    lines.append("## Label Quality")
    lines.append("")
    for tier_name, lq in label_quality.items():
        lines.append(f"### R15-{tier_name}")
        lines.append(f"- Total: {lq['total']}")
        lines.append(f"- Quality distribution: {lq['quality_counts']}")
        lines.append(f"- Has gold spans: {lq['has_gold_spans']}")
        lines.append(f"- Has hard negatives: {lq['has_hard_negatives']}")
        lines.append(f"- Negative count: {lq['negative_count']}")
        lines.append(f"- **Caveat**: {lq['caveat']}")
        lines.append("")

    # Strategy metrics
    metric_keys = [
        "file_recall@1",
        "file_recall@5",
        "file_recall@10",
        "mrr",
        "span_f0.5@10",
        "token_waste@10",
        "hard_negative_hit_rate@10",
        "negative_nonempty_rate@10",
        "success_rate",
    ]

    for tier_name in ["large", "stress"]:
        sm = strategy_metrics.get(tier_name, {})
        lines.append(f"## Strategy Metrics (R15-{tier_name})")
        lines.append("")
        if not sm:
            lines.append("_No data_")
        else:
            all_strategies = list(METHODS) + GUARD_STRATEGIES
            header = "| Strategy | " + " | ".join(metric_keys) + " |"
            separator = "|---|" + "|".join("---" for _ in metric_keys) + "|"
            lines.append(header)
            lines.append(separator)

            for sname in all_strategies:
                if sname not in sm:
                    continue
                m = sm[sname]
                row = f"| {sname} |"
                for k in metric_keys:
                    val = m.get(k)
                    row += f" {_fmt(val)} |"
                lines.append(row)
        lines.append("")

    # Deltas vs RRF
    lines.append("## Deltas vs RRF Baseline")
    lines.append("")
    for tier_name in ["large", "stress"]:
        tier_deltas = deltas_vs_rrf.get(tier_name, {})
        lines.append(f"### R15-{tier_name}")
        lines.append("")
        for sname, deltas in tier_deltas.items():
            if not deltas:
                continue
            lines.append(f"**{sname} vs RRF:**")
            for k, v in deltas.items():
                if not isinstance(v, (int, float)):
                    continue
                sign = "+" if v >= 0 else ""
                lines.append(f"- {k}: {sign}{v:.4f}")
            lines.append("")

    # Deltas vs symbol
    lines.append("## Deltas vs Symbol Baseline")
    lines.append("")
    for tier_name in ["large", "stress"]:
        tier_deltas = deltas_vs_symbol.get(tier_name, {})
        lines.append(f"### R15-{tier_name}")
        lines.append("")
        for sname, deltas in tier_deltas.items():
            if not deltas:
                continue
            lines.append(f"**{sname} vs Symbol:**")
            for k, v in deltas.items():
                if not isinstance(v, (int, float)):
                    continue
                sign = "+" if v >= 0 else ""
                lines.append(f"- {k}: {sign}{v:.4f}")
            lines.append("")

    # Generalization assessment
    lines.append("## Generalization Assessment")
    lines.append("")
    lines.append(
        f"- **selected_candidate_large_ok**: "
        f"{generalization['selected_candidate_large_ok']}"
    )
    lines.append(
        f"- **selected_candidate_stress_ok**: "
        f"{generalization['selected_candidate_stress_ok']}"
    )
    lines.append(
        f"- **stress_zero_observation_repeated**: "
        f"{generalization['stress_zero_observation_repeated']}"
    )
    lines.append(
        f"- **promotion_ready**: {generalization['promotion_ready']}"
    )
    lines.append(f"- **Reason**: {generalization['promotion_reason']}")
    lines.append("")

    # Conclusions
    lines.append("## Conclusions")
    lines.append("")
    for i, conclusion in enumerate(conclusions, 1):
        lines.append(f"{i}. {conclusion}")
    lines.append("")

    # Caveats
    lines.append("## Caveats")
    lines.append("")
    for caveat in caveats:
        lines.append(f"- {caveat}")
    lines.append("")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R19 Large/Stress Guard Generalization Validation"
    )
    parser.add_argument(
        "--openlocus",
        default="target/debug/openlocus",
        help="Path to openlocus binary",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory",
    )
    parser.add_argument(
        "--out",
        default="runs/r19-large-guard-validation.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing R19-owned reports/predictions if present",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    out_path = (
        (workspace / args.out).resolve()
        if not Path(args.out).is_absolute()
        else Path(args.out).resolve()
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Import helpers
    r17 = _import_r17_helpers(workspace)
    r18 = _import_r18_helpers(workspace)

    # ── Step 1: Ensure R15 benchmark reports exist (R19-owned) ─────────

    runs_dir = workspace / "runs"
    openlocus = str(r17["resolve_path"](args.openlocus, workspace))
    r15l_report_path = workspace / "runs" / "r19-r15-l.json"
    r15stress_report_path = workspace / "runs" / "r19-r15-stress.json"

    if not args.skip_run:
        print("R19 Large Guard Validation: Running R15 benchmark for L and stress")
        runs_config = [
            {
                "name": "R15-L",
                "cmd": [
                    "python3",
                    str(workspace / "eval" / "r15_benchmark.py"),
                    "--manifest",
                    "fixtures/r15/dataset_manifest.json",
                    "--openlocus",
                    openlocus,
                    "--methods",
                    "regex,bm25,symbol,rrf",
                    "--tier",
                    "L",
                    "--out",
                    str(r15l_report_path),
                ],
            },
            {
                "name": "R15-stress",
                "cmd": [
                    "python3",
                    str(workspace / "eval" / "r15_benchmark.py"),
                    "--manifest",
                    "fixtures/r15/dataset_manifest.json",
                    "--openlocus",
                    openlocus,
                    "--methods",
                    "regex,bm25,symbol,rrf",
                    "--tier",
                    "stress",
                    "--out",
                    str(r15stress_report_path),
                ],
            },
        ]
        for config in runs_config:
            print(f"  Running: {' '.join(config['cmd'])}")
            result = subprocess.run(
                config["cmd"],
                check=False,
                capture_output=False,
                text=True,
                cwd=str(workspace),
            )
            if result.returncode != 0:
                print(
                    f"CRITICAL: {config['name']} failed with exit code {result.returncode}",
                    file=sys.stderr,
                )
                sys.exit(1)
        prediction_artifacts = materialize_owned_prediction_artifacts(runs_dir)
    else:
        print(
            "R19 Large Guard Validation: --skip-run, reusing existing R19 reports"
        )
        if not r15l_report_path.exists() or not r15stress_report_path.exists():
            print(
                "CRITICAL: --skip-run requires R19-owned source reports "
                "runs/r19-r15-l.json and runs/r19-r15-stress.json",
                file=sys.stderr,
            )
            sys.exit(1)
        prediction_artifacts = require_owned_prediction_artifacts(runs_dir)

    # ── Step 2: Verify safety gates on source reports ──────────────────

    print("Verifying safety gates on source reports...")

    all_safety_issues: list[str] = []

    r15l_report = r17["load_report"](r15l_report_path)
    r15stress_report = r17["load_report"](r15stress_report_path)

    all_safety_issues.extend(r17["verify_safety_gates"](r15l_report, "R15-L"))
    all_safety_issues.extend(
        r17["verify_safety_gates"](r15stress_report, "R15-stress")
    )

    if all_safety_issues:
        print(
            "CRITICAL: Source report safety gate failures:", file=sys.stderr
        )
        for issue in all_safety_issues:
            print(f"  {issue}", file=sys.stderr)
        sys.exit(1)

    print("  Source safety gates: PASSED")

    # ── Step 3: Load public tasks and validated method predictions ─────

    fixtures_dir = workspace / "fixtures" / "r15"

    large_tasks = r17["load_jsonl"](fixtures_dir / "tasks" / "large.jsonl")
    stress_tasks = r17["load_jsonl"](fixtures_dir / "tasks" / "stress.jsonl")

    if not large_tasks:
        print("ERROR: No large tasks found", file=sys.stderr)
        sys.exit(1)
    if not stress_tasks:
        print("ERROR: No stress tasks found", file=sys.stderr)
        sys.exit(1)

    print(f"  Tasks: R15-L={len(large_tasks)}, R15-stress={len(stress_tasks)}")

    # Load only R19-owned prediction artifacts
    def load_predictions_for_tier(tier_name: str) -> dict[str, list[dict]]:
        preds: dict[str, list[dict]] = {}
        for method in METHODS:
            pred_path = owned_prediction_path(runs_dir, tier_name, method)
            if not pred_path.exists():
                print(
                    f"ERROR: Prediction file not found: {pred_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
            preds[method] = r17["load_jsonl"](pred_path)
        return preds

    large_preds = load_predictions_for_tier("large")
    stress_preds = load_predictions_for_tier("stress")

    # ── Step 4: Apply guard strategies (NO LABELS LOADED YET) ──────────

    print("Applying guard strategies...")

    all_strategies = list(METHODS) + GUARD_STRATEGIES
    print(f"  Strategy count: {len(all_strategies)}")

    # Route tier data: all strategies for both tiers
    all_strategy_predictions: dict[str, dict[str, list[dict]]] = {}

    route_tier_data = {
        "large": (large_tasks, large_preds),
        "stress": (stress_tasks, stress_preds),
    }

    for strategy in all_strategies:
        all_strategy_predictions[strategy] = {}

        for tier_name, (tasks, preds) in route_tier_data.items():
            if strategy in METHODS:
                # Baseline: pass through method predictions directly
                method_preds = preds.get(strategy, [])
                routed = []
                for pred in method_preds:
                    routed.append(
                        {
                            "task_id": pred["task_id"],
                            "query": pred.get("query", ""),
                            "method": strategy,
                            "repo_id": pred.get("repo_id", ""),
                            "evidence": pred.get("evidence", []),
                            "returncode": pred.get("returncode", 0),
                            "strategy_name": strategy,
                            "selected_method": strategy,
                            "route_decision": f"baseline_{strategy}",
                        }
                    )
                all_strategy_predictions[strategy][tier_name] = routed
            else:
                # Guard strategy
                routed = apply_guard_strategy(
                    strategy, tasks, preds, r17, r18
                )
                all_strategy_predictions[strategy][tier_name] = routed

    # ── Step 5: Load gold labels, verify consistency, score strategies ──
    # Labels are loaded here, AFTER all routing decisions have been made.

    print("Scoring all strategies...")

    # Load labels
    large_labels = r17["load_jsonl"](fixtures_dir / "labels" / "large.jsonl")
    stress_labels = r17["load_jsonl"](fixtures_dir / "labels" / "stress.jsonl")
    large_gold = {l["task_id"]: l for l in large_labels}
    stress_gold = {l["task_id"]: l for l in stress_labels}

    # Analyze label quality
    label_quality = {
        "large": analyze_label_quality(large_labels, "large"),
        "stress": analyze_label_quality(stress_labels, "stress"),
    }

    # Verify baseline prediction consistency
    print("Verifying baseline prediction consistency...")
    recomputed_large: dict[str, dict[str, Any]] = {}
    recomputed_stress: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        recomputed_large[method] = r17["score_predictions"](
            large_preds[method], large_gold
        )
        recomputed_stress[method] = r17["score_predictions"](
            stress_preds[method], stress_gold
        )

    consistency_issues: list[str] = []
    consistency_issues.extend(
        r17["check_baseline_prediction_consistency"](
            r15l_report, recomputed_large, "R15-L"
        )
    )
    consistency_issues.extend(
        r17["check_baseline_prediction_consistency"](
            r15stress_report, recomputed_stress, "R15-stress"
        )
    )
    if consistency_issues:
        print(
            "CRITICAL: Prediction/report consistency failures:",
            file=sys.stderr,
        )
        for issue in consistency_issues:
            print(f"  {issue}", file=sys.stderr)
        sys.exit(1)
    print("  Baseline prediction consistency: PASSED")

    # Score every strategy on R15-L and R15-stress
    strategy_metrics: dict[str, dict[str, dict[str, Any]]] = {
        "large": {},
        "stress": {},
    }

    for strategy in all_strategies:
        strategy_metrics["large"][strategy] = r17["score_predictions"](
            all_strategy_predictions[strategy]["large"], large_gold
        )
        strategy_metrics["stress"][strategy] = r17["score_predictions"](
            all_strategy_predictions[strategy]["stress"], stress_gold
        )

    # ── Step 6: Compute deltas vs RRF and vs symbol ───────────────────

    print("Computing deltas vs baselines...")

    deltas_vs_rrf: dict[str, dict[str, dict[str, float]]] = {
        "large": {},
        "stress": {},
    }
    deltas_vs_symbol: dict[str, dict[str, dict[str, float]]] = {
        "large": {},
        "stress": {},
    }

    for strategy in GUARD_STRATEGIES:
        for tier_name in ["large", "stress"]:
            rrf_baseline = strategy_metrics[tier_name].get("rrf", {})
            symbol_baseline = strategy_metrics[tier_name].get("symbol", {})
            strategy_m = strategy_metrics[tier_name].get(strategy, {})

            deltas_vs_rrf[tier_name][strategy] = r17["compute_deltas"](
                strategy_m, rrf_baseline
            )
            deltas_vs_symbol[tier_name][strategy] = r17["compute_deltas"](
                strategy_m, symbol_baseline
            )

    # ── Step 7: Compute generalization assessment ──────────────────────

    print("Computing generalization assessment...")

    generalization = compute_generalization_assessment(strategy_metrics)

    # ── Step 8: Build source safety summary ─────────────────────────────

    source_safety: dict[str, Any] = {
        "R15-L_safety_passed": r15l_report.get("safety_passed", False),
        "R15-L_canary_passed": r15l_report.get("canary_retrieval", {}).get(
            "passed", False
        ),
        "R15-stress_safety_passed": r15stress_report.get("safety_passed", False),
        "R15-stress_canary_passed": r15stress_report.get(
            "canary_retrieval", {}
        ).get("passed", False),
        "citation_inherited_from_validated_methods": True,
        "baseline_prediction_consistency_checked": True,
        "citation_hash_checked_all_methods": all(
            r15l_report.get("metrics", {})
            .get(m, {})
            .get("citation_hash_checked", False)
            or r15l_report.get("metrics", {})
            .get(m, {})
            .get("citation_not_applicable", False)
            for m in METHODS
        )
        and all(
            r15stress_report.get("metrics", {})
            .get(m, {})
            .get("citation_hash_checked", False)
            or r15stress_report.get("metrics", {})
            .get(m, {})
            .get("citation_not_applicable", False)
            for m in METHODS
        ),
    }

    # ── Step 9: Generate conclusions ───────────────────────────────────

    conclusions: list[str] = []

    # Conclusion 1: Selected candidate on large
    guarded_large = strategy_metrics["large"].get(
        "rrf_guarded_by_symbol_regex", {}
    )
    rrf_large = strategy_metrics["large"].get("rrf", {})
    symbol_large = strategy_metrics["large"].get("symbol", {})

    guarded_large_neg = guarded_large.get("negative_nonempty_rate@10")
    rrf_large_neg = rrf_large.get("negative_nonempty_rate@10")
    guarded_large_recall1 = guarded_large.get("file_recall@1")
    rrf_large_recall1 = rrf_large.get("file_recall@1")

    if (
        guarded_large_neg is not None
        and rrf_large_neg is not None
        and guarded_large_recall1 is not None
        and rrf_large_recall1 is not None
    ):
        neg_delta = guarded_large_neg - rrf_large_neg
        recall_delta = guarded_large_recall1 - rrf_large_recall1
        if neg_delta <= 0 and recall_delta >= -0.05:
            conclusions.append(
                f"rrf_guarded_by_symbol_regex generalizes to R15-L: "
                f"negative_nonempty {guarded_large_neg:.3f} vs RRF {rrf_large_neg:.3f} "
                f"(delta {neg_delta:+.3f}), FileRecall@1 {guarded_large_recall1:.3f} "
                f"vs RRF {rrf_large_recall1:.3f} (delta {recall_delta:+.3f}). "
                f"However, R15-L labels are weak/mined; this is generalization "
                f"smoke only, not promotion evidence."
            )
        else:
            conclusions.append(
                f"rrf_guarded_by_symbol_regex does NOT fully generalize to R15-L: "
                f"negative_nonempty {guarded_large_neg:.3f} vs RRF {rrf_large_neg:.3f} "
                f"(delta {neg_delta:+.3f}), FileRecall@1 {guarded_large_recall1:.3f} "
                f"vs RRF {rrf_large_recall1:.3f} (delta {recall_delta:+.3f}). "
                f"Guard may be too aggressive or too permissive on larger task set."
            )
    else:
        conclusions.append(
            "rrf_guarded_by_symbol_regex results incomplete on R15-L."
        )

    # Conclusion 2: Selected candidate on stress
    guarded_stress = strategy_metrics["stress"].get(
        "rrf_guarded_by_symbol_regex", {}
    )
    symbol_stress = strategy_metrics["stress"].get("symbol", {})
    guarded_stress_neg = guarded_stress.get("negative_nonempty_rate@10")
    symbol_stress_neg = symbol_stress.get("negative_nonempty_rate@10")

    if guarded_stress_neg is not None and symbol_stress_neg is not None:
        if guarded_stress_neg <= symbol_stress_neg:
            conclusions.append(
                f"rrf_guarded_by_symbol_regex stress negative_nonempty "
                f"{guarded_stress_neg:.3f} <= symbol baseline {symbol_stress_neg:.3f}. "
                f"However, stress has only 19 tasks and labels are weak."
            )
        else:
            conclusions.append(
                f"rrf_guarded_by_symbol_regex stress negative_nonempty "
                f"{guarded_stress_neg:.3f} > symbol baseline {symbol_stress_neg:.3f}. "
                f"The selected candidate does NOT improve stress beyond symbol. "
                f"Query noise guard is needed for stress improvement."
            )
    else:
        conclusions.append(
            "rrf_guarded_by_symbol_regex stress results incomplete."
        )

    # Conclusion 3: Stress-zero observation
    agree_zero_stress = strategy_metrics["stress"].get(
        "query_noise_plus_rrf_agree_min_0.0", {}
    )
    agree_zero_stress_neg = agree_zero_stress.get("negative_nonempty_rate@10")
    agree_zero_large = strategy_metrics["large"].get(
        "query_noise_plus_rrf_agree_min_0.0", {}
    )
    agree_zero_large_neg = agree_zero_large.get("negative_nonempty_rate@10")
    agree_zero_large_recall1 = agree_zero_large.get("file_recall@1")

    if agree_zero_stress_neg is not None:
        if agree_zero_stress_neg == 0.0:
            conclusions.append(
                f"query_noise_plus_rrf_agree_min_0.0 achieves stress "
                f"negative_nonempty=0.000, repeating the R18 observation. "
                f"On R15-L, negative_nonempty={agree_zero_large_neg:.3f} "
                f"with FileRecall@1={_fmt(agree_zero_large_recall1)}. "
                f"This is an observation, not promotion evidence; "
                f"R15-L labels are weak/mined and stress is only 19 tasks."
            )
        else:
            conclusions.append(
                f"query_noise_plus_rrf_agree_min_0.0 stress negative_nonempty "
                f"= {agree_zero_stress_neg:.3f} (not zero). The R18 stress-zero "
                f"observation does NOT repeat on R15-stress with R19-owned predictions."
            )
    else:
        conclusions.append(
            "query_noise_plus_rrf_agree_min_0.0 stress results incomplete."
        )

    # Conclusion 4: No promotion
    conclusions.append(
        "No core default promotion from R19: R15-L labels are weak/mined, "
        "R15-stress has only 19 tasks. Generalization smoke only."
    )

    # Conclusion 5: No LLM/dense
    conclusions.append(
        "No LLM/dense/provider claims. All routing uses query text and "
        "prediction features only."
    )

    caveats = [
        "R19 is an eval-layer generalization validation; does NOT change Rust core.",
        "R15-L labels are mostly weak/mined; used for generalization smoke only, "
        "not as promotion evidence.",
        "R15-stress has only 19 tasks; metric estimates are very noisy.",
        "R15-L has 294 tasks but label quality is predominantly 'mined' and 'weak'; "
        "recall/precision numbers are not reliable for quality conclusions.",
        "Guard strategies were calibrated on R15-M in R18; R15-L generalization "
        "is a smoke test, not a validation.",
        "Citation safety is inherited from validated source predictions; "
        "no new citation validation is claimed for guard-produced evidence.",
        "No LLM/dense/provider claims are made.",
        "Routing decisions are deterministic and reproducible from the same inputs.",
        "promotion_ready is always false in R19; requires human-verified labels "
        "and larger stress dataset.",
    ]

    # ── Step 10: Build JSON report ─────────────────────────────────────

    print("Building JSON report...")

    timestamp = datetime.now(timezone.utc).isoformat()

    json_report = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "openlocus": openlocus,
        "workspace": str(workspace),
        "skip_run": args.skip_run,
        "source_reports": {
            "R15-L": {
                "path": str(r15l_report_path),
                "safety_passed": r15l_report.get("safety_passed", False),
                "canary_retrieval_passed": r15l_report.get(
                    "canary_retrieval", {}
                ).get("passed", False),
                "citation_hash_checked_all_methods": all(
                    r15l_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_hash_checked", False)
                    or r15l_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_not_applicable", False)
                    for m in METHODS
                ),
            },
            "R15-stress": {
                "path": str(r15stress_report_path),
                "safety_passed": r15stress_report.get("safety_passed", False),
                "canary_retrieval_passed": r15stress_report.get(
                    "canary_retrieval", {}
                ).get("passed", False),
                "citation_hash_checked_all_methods": all(
                    r15stress_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_hash_checked", False)
                    or r15stress_report.get("metrics", {})
                    .get(m, {})
                    .get("citation_not_applicable", False)
                    for m in METHODS
                ),
            },
        },
        "prediction_artifacts": prediction_artifacts,
        "safety_summary": {
            "all_safety_passed": len(all_safety_issues) == 0,
            "issues": all_safety_issues,
        },
        "label_quality_counts": label_quality,
        "strategies": all_strategies,
        "strategy_metrics": {
            "large": strategy_metrics["large"],
            "stress": strategy_metrics["stress"],
        },
        "deltas_vs_rrf": deltas_vs_rrf,
        "deltas_vs_symbol": deltas_vs_symbol,
        "generalization_assessment": generalization,
        "conclusions": conclusions,
        "caveats": caveats,
        "core_changes": False,
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "citation_inherited_from_validated_methods": True,
        "baseline_prediction_consistency_checked": True,
    }

    out_path.write_text(
        json.dumps(json_report, indent=2) + "\n", encoding="utf-8"
    )

    # ── Step 11: Generate markdown report ───────────────────────────────

    md_content = generate_markdown_report(
        strategy_metrics,
        deltas_vs_rrf,
        deltas_vs_symbol,
        label_quality,
        generalization,
        all_safety_issues,
        source_safety,
        conclusions,
        caveats,
    )

    md_path = out_path.with_suffix(".md")
    md_path.write_text(md_content, encoding="utf-8")

    # ── Step 12: Write docs/r19-large-guard-validation.md ──────────────

    docs_r19 = workspace / "docs" / "r19-large-guard-validation.md"
    docs_r19.write_text(md_content, encoding="utf-8")

    # ── Step 13: Print summary ──────────────────────────────────────────

    print(f"\n{'='*60}")
    print("R19 Large/Stress Guard Generalization Validation Results")
    print(f"{'='*60}")

    for tier_name in ["large", "stress"]:
        sm = strategy_metrics[tier_name]
        print(f"\n{tier_name} (selected metrics):")
        for name in list(METHODS) + GUARD_STRATEGIES:
            m = sm.get(name, {})
            if not m:
                continue
            recall1 = m.get("file_recall@1")
            mrr_val = m.get("mrr")
            neg = m.get("negative_nonempty_rate@10")
            span = m.get("span_f0.5@10")
            parts = []
            if recall1 is not None:
                parts.append(f"@1={recall1:.3f}")
            if mrr_val is not None:
                parts.append(f"MRR={mrr_val:.3f}")
            if span is not None:
                parts.append(f"SpanF0.5={span:.3f}")
            if neg is not None:
                parts.append(f"neg_nonempty={neg:.3f}")
            print(f"  {name}: {', '.join(parts)}")

    print(f"\nGeneralization assessment:")
    print(
        f"  selected_candidate_large_ok: "
        f"{generalization['selected_candidate_large_ok']}"
    )
    print(
        f"  selected_candidate_stress_ok: "
        f"{generalization['selected_candidate_stress_ok']}"
    )
    print(
        f"  stress_zero_observation_repeated: "
        f"{generalization['stress_zero_observation_repeated']}"
    )
    print(f"  promotion_ready: {generalization['promotion_ready']}")

    if all_safety_issues:
        print(f"\nSafety issues: {len(all_safety_issues)}")
    else:
        print(f"\nAll safety checks passed")

    print(f"\nReport: {out_path}")
    print(f"Summary: {md_path}")
    print(f"Docs: {docs_r19}")

    if all_safety_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
