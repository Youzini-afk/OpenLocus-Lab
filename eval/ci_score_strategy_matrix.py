#!/usr/bin/env python3
"""R49 CI Score Strategy Matrix: SCORE phase only.

Reads labels and run output; computes metrics using helper semantics
compatible with r29_r26_stress_matrix.py where possible.
citation_validity must be 1.0 for all implemented strategies.
Report includes: promotion_ready=false, default_should_change=false,
delta_vs_r29_baseline, strategy_registry, unavailable reason-only,
private scan summary.

Does NOT invoke openlocus CLI. Does NOT use run-phase artifacts
beyond predictions and citation summaries.

Usage:
    python3 eval/ci_score_strategy_matrix.py \\
        --labels eval/ci_output/labels/ci_labels.jsonl \\
        --run-dir eval/ci_output/run \\
        --out eval/ci_output/score/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ── Schema ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = "ci-score-v1"

PRIVATE_FIELD_DENYLIST = [
    "source_category", "risk_public", "intent_guess", "risk_tags",
    "oracle_type", "expected_behavior", "gold_spans",
    "hard_distractors", "must_not_primary", "why_this_is_hard",
    "which_strategy_it_targets",
]

# R29 baseline metrics for delta computation (from r29-r26-stress-matrix.md)
R29_BASELINE = {
    "rrf": {"FileRecall@1": 0.803, "MRR": 0.858, "SpanF0.5": 0.250,
            "primary_false_positive_rate": 0.453, "abstain_rate": 0.343},
    "regex": {"FileRecall@1": 0.615, "MRR": 0.692, "SpanF0.5": 0.229,
              "primary_false_positive_rate": 0.135, "abstain_rate": 0.563},
    "bm25": {"FileRecall@1": 0.514, "MRR": 0.615, "SpanF0.5": 0.164,
             "primary_false_positive_rate": 0.444, "abstain_rate": 0.405},
    "symbol": {"FileRecall@1": 0.686, "MRR": 0.704, "SpanF0.5": 0.291,
               "primary_false_positive_rate": 0.080, "abstain_rate": 0.671},
    "query_noise_plus_rrf_agree_min": {
        "FileRecall@1": 0.803, "MRR": 0.857, "SpanF0.5": 0.250,
        "primary_false_positive_rate": 0.106, "abstain_rate": 0.588,
    },
    "dense_mock": {"FileRecall@1": 0.016, "MRR": 0.055, "SpanF0.5": 0.000,
                   "primary_false_positive_rate": 0.874, "abstain_rate": 0.139},
    "graph_basic": {"FileRecall@1": 0.011, "MRR": 0.015, "SpanF0.5": 0.000,
                    "primary_false_positive_rate": 0.039, "abstain_rate": 0.883},
}


# ── Data loading ────────────────────────────────────────────────────────


def load_jsonl(path: Path) -> list[dict]:
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ── Score helpers (compatible with r29_r26_stress_matrix.py) ────────────


def build_gold_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def build_hard_distractor_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for hd in label.get("hard_distractors", []):
        path = hd.get("path", "")
        start = hd.get("start_line", 0)
        end = hd.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def build_must_not_primary_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for mnp in label.get("must_not_primary", []):
        path = mnp.get("path", "")
        start = mnp.get("start_line", 0)
        end = mnp.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def get_gold_paths(label: dict) -> set[str]:
    return {span.get("path", "") for span in label.get("gold_spans", [])}


def get_hard_distractor_paths(label: dict) -> set[str]:
    return {hd.get("path", "") for hd in label.get("hard_distractors", [])}


def match_path(pred_path: str, label_path: str, repo_id: str) -> bool:
    if pred_path == label_path:
        return True
    if repo_id and pred_path == f"{repo_id}/{label_path}":
        return True
    return False


def file_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        pred_paths = set()
        for e in pred["evidence"][:k]:
            pred_paths.add(e.get("path", ""))
        for gp in gold_paths:
            for pp in pred_paths:
                if match_path(pp, gp, repo_id):
                    hits += 1
                    break
            else:
                continue
            break
    return hits / total if total else 0.0


def mrr(predictions: list[dict], gold: dict[str, dict]) -> float:
    total_rr = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        for rank, e in enumerate(pred["evidence"], 1):
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    total_rr += 1.0 / rank
                    break
            else:
                continue
            break
    return total_rr / total if total else 0.0


def span_precision_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    total_prec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        pred_lines: set[tuple[str, int]] = set()
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                pred_lines.add((path, ln))
        if not pred_lines:
            continue
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_prec += overlap / len(pred_lines) if pred_lines else 0.0
    return total_prec / total if total else 0.0


def span_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    total_rec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        pred_lines: set[tuple[str, int]] = set()
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                pred_lines.add((path, ln))
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_rec += overlap / len(gold_lines) if gold_lines else 0.0
    return total_rec / total if total else 0.0


def span_f_beta_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int, beta: float = 0.5,
) -> float:
    avg_prec = span_precision_at_k(predictions, gold, k)
    avg_rec = span_recall_at_k(predictions, gold, k)
    if avg_prec + avg_rec == 0:
        return 0.0
    beta2 = beta * beta
    return (1 + beta2) * avg_prec * avg_rec / (beta2 * avg_prec + avg_rec)


def token_waste_ratio_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int,
) -> float:
    total_waste = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        all_pred_lines = 0
        non_gold_lines = 0
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                all_pred_lines += 1
                matched = any(
                    match_path(path, gp, repo_id) and ln == gln
                    for gp, gln in gold_lines
                )
                if not matched:
                    non_gold_lines += 1
        if all_pred_lines > 0:
            total_waste += non_gold_lines / all_pred_lines
    return total_waste / total if total else 0.0


def no_gold_nonempty_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int,
) -> float:
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        if label.get("gold_spans"):
            continue
        total += 1
        if pred.get("evidence", [])[:k]:
            nonempty += 1
    return nonempty / total if total else 0.0


def hard_distractor_hit_rate_at_k(
    predictions: list[dict], gold: dict[str, dict], k: int,
) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        hard_dist_lines = build_hard_distractor_line_set(label)
        hard_dist_paths = get_hard_distractor_paths(label)
        if not hard_dist_paths:
            continue
        total += 1
        for e in pred.get("evidence", [])[:k]:
            pred_path = e.get("path", "")
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            if start > 0 and end >= start:
                for ln in range(start, end + 1):
                    for (hp, hln) in hard_dist_lines:
                        if match_path(pred_path, hp, repo_id) and ln == hln:
                            hits += 1
                            break
                    else:
                        if any(
                            match_path(pred_path, hp, repo_id) and hln == 0
                            for hp, hln in hard_dist_lines
                        ):
                            hits += 1
                            break
                        continue
                    break
    return hits / total if total else 0.0


def false_primary_on_negative_rate(
    predictions: list[dict], gold: dict[str, dict],
) -> float:
    false_primary = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        total += 1
        if pred.get("evidence", []):
            false_primary += 1
    return false_primary / total if total else 0.0


def abstain_rate(predictions: list[dict]) -> float:
    abstained = sum(1 for p in predictions if not p.get("evidence", []))
    return abstained / len(predictions) if predictions else 0.0


def must_not_primary_violation_rate(
    predictions: list[dict], gold: dict[str, dict],
) -> float:
    violations = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        mnp_lines = build_must_not_primary_line_set(label)
        if not mnp_lines:
            continue
        total += 1
        evidence = pred.get("evidence", [])
        if not evidence:
            continue
        top = evidence[0]
        top_path = top.get("path", "")
        start = top.get("start_line", 0)
        end = top.get("end_line", 0)
        for ln in range(start, end + 1):
            for (mp, mln) in mnp_lines:
                if match_path(top_path, mp, repo_id) and ln == mln:
                    violations += 1
                    break
            else:
                continue
            break
    return violations / total if total else 0.0


def compute_latency_stats(predictions: list[dict]) -> dict[str, Any]:
    latencies = sorted(p.get("latency_ms", 0) for p in predictions)
    if not latencies:
        return {"p50": 0, "p95": 0, "max": 0, "count": 0}

    def percentile(data: list, p: float) -> int:
        idx = int(len(data) * p / 100.0)
        return data[min(idx, len(data) - 1)]

    return {
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "max": latencies[-1],
        "count": len(latencies),
    }


# ── Delta vs R29 baseline ──────────────────────────────────────────────


def compute_delta_vs_r29(strategy: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Compute delta between current metrics and R29 baseline."""
    baseline = R29_BASELINE.get(strategy)
    if baseline is None:
        return {"available": False, "reason": "no_r29_baseline_for_strategy"}

    deltas: dict[str, Any] = {}
    for key, baseline_val in baseline.items():
        current_val = metrics.get(key)
        if current_val is not None and isinstance(current_val, (int, float)):
            deltas[key] = {
                "current": current_val,
                "r29_baseline": baseline_val,
                "delta": round(current_val - baseline_val, 6),
            }

    return {"available": True, "deltas": deltas}


# ── Private field scan ──────────────────────────────────────────────────


def _scan_object_for_private_fields(obj: Any, where: str, issues: list[str]) -> int:
    """Recursively scan JSON-like objects for exact private field keys."""
    violations = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in PRIVATE_FIELD_DENYLIST:
                violations += 1
                issues.append(f"CRITICAL: Private field '{key}' in {where}")
            violations += _scan_object_for_private_fields(value, f"{where}.{key}", issues)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            violations += _scan_object_for_private_fields(item, f"{where}[{idx}]", issues)
    return violations


def scan_json_artifacts_for_private_fields(paths: list[Path]) -> tuple[dict[str, Any], list[str]]:
    """Scan JSON/JSONL artifacts for private fields."""
    issues: list[str] = []
    scanned_files = 0
    total_lines = 0
    violations = 0

    artifact_files: list[Path] = []
    for path in paths:
        if path.is_dir():
            artifact_files.extend(sorted(path.rglob("*.json")))
            artifact_files.extend(sorted(path.rglob("*.jsonl")))
        elif path.suffix in {".json", ".jsonl"} and path.exists():
            artifact_files.append(path)

    for artifact_path in sorted(set(artifact_files)):
        scanned_files += 1
        try:
            text = artifact_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if artifact_path.suffix == ".jsonl":
            for line_no, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                total_lines += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                violations += _scan_object_for_private_fields(
                    obj, f"{artifact_path.name}:{line_no}", issues,
                )
        else:
            total_lines += 1
            try:
                obj = json.loads(text) if text.strip() else {}
            except json.JSONDecodeError:
                continue
            violations += _scan_object_for_private_fields(obj, artifact_path.name, issues)

    return {
        "scanned_files": scanned_files,
        "total_lines": total_lines,
        "violations": violations,
        "clean": violations == 0,
    }, issues


# ── Main SCORE phase ────────────────────────────────────────────────────


def score_strategy(
    predictions: list[dict],
    gold: dict[str, dict],
    citation_summary: dict[str, Any],
    strategy: str,
) -> dict[str, Any]:
    total = len(predictions)
    ok = sum(1 for p in predictions if p.get("returncode", 0) == 0)

    metrics: dict[str, Any] = {
        "total_tasks": total,
        "successful": ok,
        "success_rate": ok / total if total else 0.0,
        "citation_validity": citation_summary.get("citation_validity", 0.0),
        "citation_valid_count": citation_summary.get("citation_valid_count", 0),
        "citation_total_count": citation_summary.get("citation_total_count", 0),
        "citation_invalid_count": citation_summary.get("citation_invalid_count", 0),
        "citation_validation_mode": citation_summary.get("citation_validation_mode", "missing"),
        "citation_hash_checked": citation_summary.get("citation_hash_checked", False),
        "citation_not_applicable": citation_summary.get("citation_not_applicable", False),
    }

    non_neg_gold = {tid: g for tid, g in gold.items() if g.get("gold_spans")}
    negative_gold = {tid: g for tid, g in gold.items() if not g.get("gold_spans")}
    evaluable_gold = {
        tid: g for tid, g in gold.items()
        if g.get("gold_spans") or g.get("hard_distractors")
    }

    if non_neg_gold:
        for k in [1, 3, 5]:
            metrics[f"FileRecall@{k}"] = file_recall_at_k(predictions, non_neg_gold, k)
        metrics["MRR"] = mrr(predictions, non_neg_gold)
        metrics["SpanF0.5"] = span_f_beta_at_k(predictions, non_neg_gold, 10, 0.5)
        metrics["SpanPrecision"] = span_precision_at_k(predictions, non_neg_gold, 10)
        metrics["SpanRecall"] = span_recall_at_k(predictions, non_neg_gold, 10)
        metrics["token_waste"] = token_waste_ratio_at_k(predictions, non_neg_gold, 10)

    if evaluable_gold:
        metrics["hard_distractor_hit_rate"] = hard_distractor_hit_rate_at_k(
            predictions, evaluable_gold, 10
        )

    if negative_gold:
        metrics["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(
            predictions, negative_gold, 10
        )

    metrics["primary_false_positive_rate"] = false_primary_on_negative_rate(predictions, gold)
    metrics["abstain_rate"] = abstain_rate(predictions)
    metrics["must_not_primary_violation_rate"] = must_not_primary_violation_rate(predictions, gold)
    metrics["latency"] = compute_latency_stats(predictions)

    # Delta vs R29 baseline
    metrics["delta_vs_r29_baseline"] = compute_delta_vs_r29(strategy, metrics)

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="R49 CI Score Strategy Matrix")
    parser.add_argument("--labels", required=True, help="Private labels JSONL")
    parser.add_argument("--run-dir", required=True, help="Run output directory")
    parser.add_argument("--out", required=True, help="Output report JSON path")
    args = parser.parse_args()

    labels_path = Path(args.labels)
    run_dir = Path(args.run_dir)
    out_path = Path(args.out)

    # Load labels
    labels_list = load_jsonl(labels_path)
    gold: dict[str, dict] = {l["test_id"]: l for l in labels_list}
    print(f"Loaded {len(gold)} labels from {labels_path}")

    # Load run manifest
    manifest_path = run_dir / "run-manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: run-manifest.json not found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    citation_summaries = manifest.get("citation_summaries", {})
    strategies_run = manifest.get("strategies_run", [])
    unavailable_strategies = manifest.get("unavailable_strategies", {})

    # Score each implemented strategy
    strategy_metrics: dict[str, dict[str, Any]] = {}
    all_issues: list[str] = []

    for strategy in strategies_run:
        pred_path = run_dir / f"{strategy}-predictions.jsonl"
        if not pred_path.exists():
            print(f"WARNING: No predictions for strategy {strategy}", file=sys.stderr)
            continue

        predictions = load_jsonl(pred_path)
        cit_summary = citation_summaries.get(strategy, {
            "citation_validity": 0.0,
            "citation_valid_count": 0,
            "citation_total_count": 0,
            "citation_invalid_count": 0,
        })

        metrics = score_strategy(predictions, gold, cit_summary, strategy)
        strategy_metrics[strategy] = metrics

        # Verify citation_validity == 1.0
        cv = metrics.get("citation_validity", 0.0)
        if cv < 1.0 and metrics.get("citation_total_count", 0) > 0:
            all_issues.append(
                f"CRITICAL: Strategy {strategy}: citation_validity={cv} < 1.0"
            )

        print(f"  Scored {strategy}: FileRecall@1={metrics.get('FileRecall@1', 'N/A')}, "
              f"MRR={metrics.get('MRR', 'N/A')}, SpanF0.5={metrics.get('SpanF0.5', 'N/A')}")

    # Build strategy registry
    strategy_registry: dict[str, dict[str, Any]] = {}
    for strategy in strategies_run:
        strategy_registry[strategy] = {
            "status": "implemented",
            "metrics_available": True,
        }
    for strat, reason in unavailable_strategies.items():
        strategy_registry[strat] = {
            "status": "unavailable",
            "reason": reason,
        }

    # Private scan summary for RUN artifacts before report generation.
    pre_report_scan_result, scan_issues = scan_json_artifacts_for_private_fields([run_dir])
    all_issues.extend(scan_issues)

    # Build report
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "strategies": strategy_metrics,
        "strategy_registry": strategy_registry,
        "unavailable_strategies": {
            k: {"status": "unavailable", "reason": v}
            for k, v in unavailable_strategies.items()
        },
        "delta_vs_r29_baseline": {
            strategy: metrics.get("delta_vs_r29_baseline", {})
            for strategy, metrics in strategy_metrics.items()
        },
        "private_scan_summary": pre_report_scan_result,
        "citation_validity_all_implemented": all(
            m.get("citation_validity", 0.0) >= 1.0 or m.get("citation_total_count", 0) == 0
            for m in strategy_metrics.values()
        ),
        "run_score_separation": True,
        "labels_used_in_run_phase": False,
        "issues_count": len(all_issues),
        "total_labels": len(gold),
    }

    write_json(out_path, report)

    # Scan both RUN artifacts and the score report itself.  Then rewrite the
    # report with the complete scan summary so uploaded artifacts carry the
    # same invariant the validator enforces.
    final_scan_result, final_scan_issues = scan_json_artifacts_for_private_fields([run_dir, out_path])
    all_issues.extend(final_scan_issues)
    report["private_scan_summary"] = final_scan_result
    report["issues_count"] = len(all_issues)
    write_json(out_path, report)

    if all_issues:
        print(f"\n{len(all_issues)} issues:", file=sys.stderr)
        for issue in all_issues:
            print(f"  {issue}", file=sys.stderr)

    critical_count = sum(1 for i in all_issues if i.startswith("CRITICAL:"))
    if critical_count > 0:
        print(f"\nFATAL: {critical_count} critical issues in score phase.", file=sys.stderr)
        sys.exit(1)

    print(f"\nScore report written to {out_path}")


if __name__ == "__main__":
    main()
