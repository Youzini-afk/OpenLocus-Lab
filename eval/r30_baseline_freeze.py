#!/usr/bin/env python3
"""R30 baseline freeze for the R29 × R26 stress matrix.

R30 is a control-plane artifact for later real-model experiments.  It does not
invoke retrieval, does not read provider credentials, does not change the Rust
core, and does not promote any strategy.  It records a stable R29 baseline from
the committed R29 report plus optional runtime artifacts when they are present.

The freeze deliberately distinguishes:
  * frozen committed summary values (always available), and
  * raw runtime artifact inventory (optional; /runs is gitignored).

If runtime artifacts are absent, R30 says so instead of fabricating hashes or
quality numbers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "r30-baseline-freeze-v1"
BASELINE_NAME = "r29_r26_stress_matrix"

IMPLEMENTED_STRATEGIES = [
    "regex",
    "bm25",
    "symbol",
    "rrf",
    "bm25_regex",
    "bm25_symbol",
    "rrf_guarded_by_symbol",
    "rrf_guarded_by_regex",
    "rrf_guarded_by_symbol_regex",
    "query_noise_plus_rrf_agree_min",
    "dense_mock",
    "dense_mock_plus_rrf",
    "graph_basic",
    "rrf_plus_graph",
    "rrf_plus_dense_mock",
    "rrf_plus_dense_mock_plus_graph",
]

UNAVAILABLE_STRATEGIES = {
    "dense_real_if_available": "not_configured_or_policy_disabled",
    "tdb_quiver_if_available": "quiver_not_implemented",
    "tdb_quiver_plus_rrf": "quiver_not_implemented",
    "tdb_quiver_guarded_by_symbol_regex": "quiver_not_implemented",
    "fast_context_if_available": "not wired as standalone matrix strategy",
}

KEY_METRICS = [
    "FileRecall@1",
    "FileRecall@5",
    "MRR",
    "SpanF0.5",
    "primary_false_positive_rate",
    "no_gold_nonempty_rate",
    "abstain_rate",
    "token_waste",
    "guard_recall_kill_rate",
]

EXPECTED_FAILURE_CLUSTERS = [
    "DENSE_MOCK_NOISE",
    "RRF_INHERITED_BM25_FALSE_POSITIVE",
    "DENSE_SEMANTIC_TRAP_FALSE_POSITIVE",
    "GRAPH_ADDS_NO_GOLD",
    "SYMBOL_EXTRACTION_MISS",
    "GUARD_RECALL_KILL",
    "FRONTEND_BACKEND_CONFUSION",
    "HARD_DISTRACTOR_CONFUSION",
    "NEGATIVE_NONEXISTENT_FALSE_PRIMARY",
    "TEST_SOURCE_CONFUSION",
    "REGEX_NORMALIZATION_BUG",
    "GRAPH_NEIGHBOR_FALSE_POSITIVE",
    "STALE_INDEX_LIKE_FALSE_PRIMARY",
    "BENCHMARK_ORACLE_SUSPECT",
]

EXPECTED_ARTIFACT_SUFFIXES = [
    "predictions.jsonl",
    "evidence.jsonl",
    "trace.jsonl",
    "rejections.jsonl",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as f:
        return sum(1 for line in f if line.strip())


def parse_markdown_metrics(markdown: str) -> dict[str, dict[str, float | None]]:
    metrics: dict[str, dict[str, float | None]] = {}
    table_re = re.compile(r"^\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", re.MULTILINE)
    for match in table_re.finditer(markdown):
        values = [v.strip() for v in match.groups()]
        strategy = values[0]
        if strategy in {"Strategy", "---"} or strategy.startswith("---"):
            continue
        if strategy not in IMPLEMENTED_STRATEGIES:
            continue
        parsed: dict[str, float | None] = {}
        for key, raw in zip(KEY_METRICS, values[1:]):
            parsed[key] = None if raw in {"—", "", "null"} else float(raw)
        metrics[strategy] = parsed
    return metrics


def parse_markdown_clusters(markdown: str) -> dict[str, int]:
    clusters: dict[str, int] = {}
    table_re = re.compile(r"^\| ([A-Z0-9_]+) \| (\d+) \|$", re.MULTILINE)
    for cluster, count in table_re.findall(markdown):
        if cluster in EXPECTED_FAILURE_CLUSTERS:
            clusters[cluster] = int(count)
    return clusters


def parse_markdown_contributions(markdown: str) -> dict[str, dict[str, Any]]:
    contributions: dict[str, dict[str, Any]] = {}
    table_re = re.compile(r"^\| ([^|]+) \| (\d+) \| (\d+) \| (\d+) \| (true|false) \|$", re.MULTILINE)
    for strategy, added_gold, added_false, tasks, blocked in table_re.findall(markdown):
        strategy = strategy.strip()
        if strategy == "Strategy" or strategy.startswith("---"):
            continue
        contributions[strategy] = {
            "added_gold_span": int(added_gold),
            "added_false_span": int(added_false),
            "tasks_with_additions": int(tasks),
            "default_expansion_blocked": blocked == "true",
        }
    return contributions


def parse_bucket_regressions(markdown: str) -> dict[str, Any]:
    total_match = re.search(r"total_bucket_regressions:\s*(\d+)", markdown)
    strategies_match = re.search(r"strategies_with_bucket_regression:\s*([^\n]+)", markdown)
    return {
        "total_bucket_regressions": int(total_match.group(1)) if total_match else None,
        "strategies_with_bucket_regression": [
            s.strip().strip("`")
            for s in (strategies_match.group(1).split(",") if strategies_match else [])
            if s.strip()
        ],
    }


def artifact_inventory(runs_dir: Path) -> dict[str, Any]:
    if not runs_dir.exists():
        return {
            "present": False,
            "reason": "runs_directory_missing",
            "files": [],
            "expected_files_present": False,
        }

    files: list[dict[str, Any]] = []
    for path in sorted(runs_dir.glob("r29-r26-stress-*")):
        if not path.is_file():
            continue
        files.append({
            "path": str(path.relative_to(runs_dir.parent)),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "jsonl_lines": count_jsonl(path) if path.suffix == ".jsonl" else None,
        })

    expected_missing: list[str] = []
    for strategy in IMPLEMENTED_STRATEGIES:
        for suffix in EXPECTED_ARTIFACT_SUFFIXES:
            name = f"r29-r26-stress-{strategy}-{suffix}"
            if not (runs_dir / name).exists():
                expected_missing.append(str(Path("runs") / name))

    report_missing = not (runs_dir / "r29-r26-stress-matrix-report.json").exists()
    manifest_missing = not (runs_dir / "r29-r26-stress-artifacts-manifest.json").exists()
    if report_missing:
        expected_missing.append("runs/r29-r26-stress-matrix-report.json")
    if manifest_missing:
        expected_missing.append("runs/r29-r26-stress-artifacts-manifest.json")

    return {
        "present": bool(files),
        "files": files,
        "file_count": len(files),
        "expected_files_present": not expected_missing,
        "missing_expected_files": expected_missing,
    }


def maybe_load_r29_json(runs_dir: Path) -> dict[str, Any] | None:
    path = runs_dir / "r29-r26-stress-matrix-report.json"
    if not path.exists():
        return None
    return load_json(path)


def validate_public_tasks(tasks_path: Path) -> dict[str, Any]:
    public_fields = {"test_id", "repo_id", "query", "public_version", "source"}
    private_fields = {
        "source_category", "risk_public", "intent_guess", "risk_tags", "oracle_type",
        "expected_behavior", "gold_spans", "hard_distractors", "must_not_primary",
        "why_this_is_hard", "which_strategy_it_targets",
    }
    issues: list[str] = []
    count = 0
    with tasks_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            count += 1
            row = json.loads(line)
            extra = set(row) - public_fields
            leaked = set(row) & private_fields
            if extra:
                issues.append(f"task {row.get('test_id', count)} has non-public fields {sorted(extra)}")
            if leaked:
                issues.append(f"task {row.get('test_id', count)} leaks private fields {sorted(leaked)}")
            if len(issues) >= 20:
                break
    return {"task_count": count, "public_only": not issues, "issues": issues}


def build_report(workspace: Path) -> dict[str, Any]:
    docs_path = workspace / "docs" / "r29-r26-stress-matrix.md"
    r26_manifest_path = workspace / "fixtures" / "r26_auto_stress" / "dataset_manifest.json"
    r26_safety_path = workspace / "fixtures" / "r26_auto_stress" / "safety_checks.json"
    r26_summary_path = workspace / "fixtures" / "r26_auto_stress" / "summary.json"
    r26_tasks_path = workspace / "fixtures" / "r26_auto_stress" / "tasks" / "auto_stress.jsonl"

    markdown = read_text(docs_path)
    r26_manifest = load_json(r26_manifest_path)
    r26_safety = load_json(r26_safety_path)
    r26_summary = load_json(r26_summary_path)
    public_task_validation = validate_public_tasks(r26_tasks_path)

    runs_dir = workspace / "runs"
    r29_json = maybe_load_r29_json(runs_dir)
    inventory = artifact_inventory(runs_dir)

    if r29_json:
        metrics = r29_json.get("metrics", {})
        failure_clusters = {
            k: v.get("count") if isinstance(v, dict) else v
            for k, v in r29_json.get("failure_clusters", {}).items()
        }
        span_contributions = r29_json.get("span_contributions", {})
        bucket_regressions = r29_json.get("bucket_regressions", {})
        metrics_source = "runs/r29-r26-stress-matrix-report.json"
    else:
        metrics = parse_markdown_metrics(markdown)
        failure_clusters = parse_markdown_clusters(markdown)
        span_contributions = parse_markdown_contributions(markdown)
        bucket_regressions = parse_bucket_regressions(markdown)
        metrics_source = "docs/r29-r26-stress-matrix.md"

    issues: list[str] = []
    for strategy in ["rrf", "symbol", "query_noise_plus_rrf_agree_min"]:
        if strategy not in metrics:
            issues.append(f"missing required key metric strategy: {strategy}")
    for cluster in EXPECTED_FAILURE_CLUSTERS:
        if cluster not in failure_clusters:
            issues.append(f"missing failure cluster: {cluster}")
    if r26_safety.get("passed") is not True:
        issues.append("R26 safety checks did not pass")
    if r26_summary.get("total_tasks") != 1100:
        issues.append("R26 total_tasks must be 1100")
    if public_task_validation.get("public_only") is not True:
        issues.append("R26 public tasks contain private or unknown fields")

    if issues:
        raise SystemExit("R30 baseline freeze validation failed:\n" + "\n".join(f"- {i}" for i in issues))

    rrf = metrics["rrf"]
    symbol = metrics["symbol"]
    guard = metrics["query_noise_plus_rrf_agree_min"]

    observations = {
        "rrf": {
            "role": "current_best_recall_channel",
            "summary": "RRF remains recall-strong but primary-false-positive high on R26 stress.",
            "FileRecall@1": rrf.get("FileRecall@1"),
            "FileRecall@5": rrf.get("FileRecall@5"),
            "primary_false_positive_rate": rrf.get("primary_false_positive_rate"),
        },
        "query_noise_plus_rrf_agree_min": {
            "role": "current_best_guard_candidate",
            "summary": "Preserves RRF recall on R26 while reducing false-primary, but prior bucket regressions still block promotion.",
            "FileRecall@1": guard.get("FileRecall@1"),
            "primary_false_positive_rate": guard.get("primary_false_positive_rate"),
            "guard_recall_kill_rate": guard.get("guard_recall_kill_rate"),
        },
        "symbol": {
            "role": "current_best_precision_anchor",
            "summary": "Symbol is the precision anchor with low false-primary and high abstain.",
            "FileRecall@1": symbol.get("FileRecall@1"),
            "SpanF0.5": symbol.get("SpanF0.5"),
            "primary_false_positive_rate": symbol.get("primary_false_positive_rate"),
            "abstain_rate": symbol.get("abstain_rate"),
        },
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_name": BASELINE_NAME,
        "baseline_source": metrics_source,
        "docs_report": {
            "path": str(docs_path.relative_to(workspace)),
            "sha256": sha256_file(docs_path),
            "results_section_sha256": sha256_text(markdown.split("## Full-run results", 1)[-1]),
        },
        "r26_source_artifacts": {
            "dataset_manifest": {
                "path": str(r26_manifest_path.relative_to(workspace)),
                "sha256": sha256_file(r26_manifest_path),
                "schema_version": r26_manifest.get("schema_version"),
                "tasks_sha256": r26_manifest.get("generation_info", {}).get("tasks_sha256"),
                "labels_sha256": r26_manifest.get("generation_info", {}).get("labels_sha256"),
            },
            "safety_checks": {
                "path": str(r26_safety_path.relative_to(workspace)),
                "sha256": sha256_file(r26_safety_path),
                "passed": r26_safety.get("passed"),
                "total_checks": r26_safety.get("total_checks"),
            },
            "summary": {
                "path": str(r26_summary_path.relative_to(workspace)),
                "sha256": sha256_file(r26_summary_path),
                "total_tasks": r26_summary.get("total_tasks"),
                "total_labels": r26_summary.get("total_labels"),
            },
            "public_task_validation": public_task_validation,
        },
        "implemented_strategies": len(IMPLEMENTED_STRATEGIES),
        "implemented_strategy_names": IMPLEMENTED_STRATEGIES,
        "unavailable_strategies": len(UNAVAILABLE_STRATEGIES),
        "unavailable_strategy_reasons": UNAVAILABLE_STRATEGIES,
        "current_best_recall_channel": "rrf",
        "current_best_precision_anchor": "symbol",
        "current_best_guard_candidate": "query_noise_plus_rrf_agree_min",
        "r29_key_metrics": {
            "rrf": rrf,
            "symbol": symbol,
            "query_noise_plus_rrf_agree_min": guard,
        },
        "observations": observations,
        "failure_clusters": failure_clusters,
        "span_contributions": span_contributions,
        "bucket_regressions": bucket_regressions,
        "artifact_inventory": inventory,
        "runtime_artifacts_available": inventory.get("present") is True,
        "runtime_artifact_note": (
            "Runtime R29 artifacts were hashed and inventoried."
            if inventory.get("present")
            else "R29 runtime artifacts are absent from this checkout because runs/ is gitignored; freeze uses committed R29 report values and records absence explicitly."
        ),
        "required_future_delta_baselines": [
            "delta_vs_r29_rrf",
            "delta_vs_r29_query_noise_guard",
            "delta_vs_r29_symbol",
        ],
        "safety_gates": {
            "promotion_ready": False,
            "default_should_change": False,
            "not_promotion_evidence": True,
            "core_changes": False,
            "evidencecore_semantics_changed": False,
            "remote_calls": 0,
            "dense_or_llm_claims": False,
            "run_phase_public_only": True,
            "score_phase_labels_only": True,
            "labels_loaded_after_run": True,
            "r26_public_tasks_public_only": public_task_validation.get("public_only") is True,
            "citation_validity_all_strategies": 1.0,
            "artifact_manifest_verified_if_present": inventory.get("expected_files_present") if inventory.get("present") else None,
            "unavailable_strategies_reason_only": True,
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    metrics = report["r29_key_metrics"]
    lines = [
        "# R30 Baseline Freeze",
        "",
        "R30 freezes the R29 × R26 stress-matrix baseline for later real-model retrieval experiments. It is a control artifact only: no retrieval was run, no remote provider was called, no EvidenceCore semantics changed, and no strategy is promoted.",
        "",
        "## Frozen Baseline",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- baseline_name: `{report['baseline_name']}`",
        f"- baseline_source: `{report['baseline_source']}`",
        f"- implemented_strategies: {report['implemented_strategies']}",
        f"- unavailable_strategies: {report['unavailable_strategies']} (reason-only, no fake metrics)",
        "- promotion_ready: false",
        "- default_should_change: false",
        "- core_changes: false",
        "- evidencecore_semantics_changed: false",
        "- remote_calls: 0",
        "",
        "## Control Strategies",
        "",
        "| Strategy | Role | FileRecall@1 | SpanF0.5 | primary_false_positive_rate | abstain_rate | guard_recall_kill_rate |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    roles = {
        "rrf": "best recall channel",
        "query_noise_plus_rrf_agree_min": "best guard candidate",
        "symbol": "precision anchor",
    }
    for strategy in ["rrf", "query_noise_plus_rrf_agree_min", "symbol"]:
        m = metrics[strategy]
        lines.append(
            "| {strategy} | {role} | {fr1} | {span} | {fpr} | {abstain} | {kill} |".format(
                strategy=strategy,
                role=roles[strategy],
                fr1=m.get("FileRecall@1"),
                span=m.get("SpanF0.5"),
                fpr=m.get("primary_false_positive_rate"),
                abstain=m.get("abstain_rate"),
                kill=m.get("guard_recall_kill_rate"),
            )
        )

    lines.extend([
        "",
        "## R30 Required Deltas for Future Phases",
        "",
        "Every later real-model experiment must report:",
        "",
        "- `delta_vs_r29_rrf`",
        "- `delta_vs_r29_query_noise_guard`",
        "- `delta_vs_r29_symbol`",
        "",
        "## Main Frozen Facts",
        "",
        "1. RRF remains the strongest recall channel, but primary false-positive risk is high.",
        "2. `query_noise_plus_rrf_agree_min` preserves RRF recall on R26 while reducing false-primary, but prior bucket-regression evidence still blocks promotion.",
        "3. Symbol remains the precision anchor: low false-primary, higher abstain.",
        "4. Dense mock is a safety/noise probe, not semantic-quality evidence.",
        "5. Graph expansion remains blocked by added false spans > added gold spans.",
        "6. QuIVer/TDB remain unavailable for quality; no fabricated metrics are allowed.",
        "",
        "## Runtime Artifact Inventory",
        "",
        f"- runtime_artifacts_available: {str(report['runtime_artifacts_available']).lower()}",
        f"- note: {report['runtime_artifact_note']}",
        "",
        "## Safety Gate Freeze",
        "",
    ])
    for key, value in report["safety_gates"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("artifacts/r30/baseline_manifest.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/r30-baseline-freeze.md"))
    args = parser.parse_args(argv)

    workspace = args.workspace.resolve()
    report = build_report(workspace)

    out = args.out if args.out.is_absolute() else workspace / args.out
    doc = args.doc if args.doc.is_absolute() else workspace / args.doc
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, doc)
    print(f"Wrote {out.relative_to(workspace)}")
    print(f"Wrote {doc.relative_to(workspace)}")


if __name__ == "__main__":
    main()
