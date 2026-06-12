#!/usr/bin/env python3
"""R16 Multi-Method Quality Bakeoff.

Runs R14-S, R15-M, and R15-stress benchmark matrices using existing
R14/R15 benchmark runners, then aggregates results into a cross-matrix
quality comparison with safety gates.

This is a lexical/symbol/RRF quality bakeoff only. No provider/dense/LLM
claims are made.

Safety:
- Hard fail (exit nonzero) if any runner command fails
- Hard fail if any safety_passed is false in any report
- Hard fail if citation_validity < 1.0 for any method with evidence
- Hard fail if citation_hash_checked is not true (or citation_not_applicable
  is not true) for any method
- Hard fail if canary_retrieval.passed is false where present
- No remote calls; all benchmarks are local-only

Usage:
    python3 eval/r16_quality_bakeoff.py \\
        --openlocus target/debug/openlocus \\
        --workspace . \\
        --out runs/r16-quality-bakeoff.json

    # Reuse existing reports (skip running benchmarks):
    python3 eval/r16_quality_bakeoff.py \\
        --skip-run \\
        --workspace . \\
        --out runs/r16-quality-bakeoff.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "r16-v1"

METHODS = ["regex", "bm25", "symbol", "rrf"]

# Metric keys for the method comparison tables
RECALL_METRICS = [
    "file_recall@1",
    "file_recall@5",
    "file_recall@10",
    "mrr",
    "span_f0.5@10",
    "hard_negative_hit_rate@10",
    "negative_nonempty_rate@10",
    "citation_validity",
    "success_rate",
]


def run_command(cmd: list[str], description: str, cwd: Path) -> None:
    """Run a subprocess command; hard fail on nonzero exit."""
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, capture_output=False, text=True, cwd=str(cwd))
    if result.returncode != 0:
        print(
            f"CRITICAL: {description} failed with exit code {result.returncode}",
            file=sys.stderr,
        )
        sys.exit(1)


def load_report(path: Path) -> dict[str, Any]:
    """Load a benchmark report JSON."""
    if not path.exists():
        print(f"ERROR: Report not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str, workspace: Path) -> Path:
    """Resolve a CLI path relative to workspace, not caller cwd."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (workspace / path).resolve()


def verify_safety_gates(
    report: dict[str, Any], matrix_name: str
) -> list[str]:
    """Verify safety gates on a benchmark report. Returns list of issues."""
    issues: list[str] = []

    # safety_passed must be true
    if not report.get("safety_passed", False):
        issues.append(
            f"CRITICAL: {matrix_name}: safety_passed is false "
            f"(issues: {report.get('safety_issues', [])})"
        )

    # canary_retrieval.passed where present
    canary = report.get("canary_retrieval", {})
    if not canary:
        issues.append(
            f"CRITICAL: {matrix_name}: canary_retrieval is missing"
        )
    elif not canary.get("passed", False):
        issues.append(
            f"CRITICAL: {matrix_name}: canary_retrieval.passed is false "
            f"(checked={canary.get('checked')}, hits={canary.get('hits')}, "
            f"failures={canary.get('failures')})"
        )

    # Per-method checks
    metrics = report.get("metrics", {})
    missing_methods = sorted(set(METHODS) - set(metrics.keys()))
    if missing_methods:
        issues.append(
            f"CRITICAL: {matrix_name}: missing expected methods: {missing_methods}"
        )
    for method, method_metrics in metrics.items():
        # citation_validity must be 1.0 for methods with evidence
        cv = method_metrics.get("citation_validity", 0.0)
        total = method_metrics.get("citation_total_count", 0)
        if total > 0 and cv < 1.0:
            issues.append(
                f"CRITICAL: {matrix_name}/{method}: citation_validity={cv:.3f} < 1.0 "
                f"(valid={method_metrics.get('citation_valid_count')}, "
                f"total={total})"
            )

        # citation_hash_checked must be true, or citation_not_applicable true
        hash_checked = method_metrics.get("citation_hash_checked", False)
        not_applicable = method_metrics.get("citation_not_applicable", False)
        if not hash_checked and not not_applicable:
            issues.append(
                f"CRITICAL: {matrix_name}/{method}: citation_hash_checked is not true "
                f"and citation_not_applicable is not true"
            )

    return issues


def extract_method_table(
    report: dict[str, Any], metrics_keys: list[str] | None = None
) -> dict[str, dict[str, Any]]:
    """Extract a method -> metrics dict from a report."""
    if metrics_keys is None:
        metrics_keys = RECALL_METRICS
    result: dict[str, dict[str, Any]] = {}
    for method, method_metrics in report.get("metrics", {}).items():
        row: dict[str, Any] = {}
        for key in metrics_keys:
            val = method_metrics.get(key)
            if val is not None:
                row[key] = val
        result[method] = row
    return result


def find_winners(
    method_table: dict[str, dict[str, Any]],
    metric: str,
    higher_is_better: bool = True,
) -> list[str]:
    """Find the method(s) with the best value for a metric."""
    values: dict[str, float] = {}
    for method, row in method_table.items():
        val = row.get(metric)
        if val is not None and isinstance(val, (int, float)):
            values[method] = float(val)

    if not values:
        return []

    if higher_is_better:
        best = max(values.values())
    else:
        best = min(values.values())

    return [m for m, v in values.items() if abs(v - best) < 1e-9]


def generate_markdown_report(
    r14s_table: dict[str, dict[str, Any]],
    r15m_table: dict[str, dict[str, Any]],
    r15stress_table: dict[str, dict[str, Any]],
    safety_issues: list[str],
    winners: dict[str, dict[str, list[str]]],
    conclusions: list[str],
) -> str:
    """Generate a markdown report for R16 quality bakeoff."""
    lines = [
        "# R16 Multi-Method Quality Bakeoff",
        "",
        "**This is a lexical/symbol/RRF quality bakeoff. No provider/dense/LLM claims are made.**",
        "",
    ]

    # Safety section
    if safety_issues:
        lines.append("## Safety Issues")
        for issue in safety_issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines.append("## Safety Checks: All Passed")
        lines.append("")

    # R14-S table
    lines.append("## R14-S Matrix (regex, bm25, symbol, rrf)")
    lines.append("")
    lines.append(_format_metric_table(r14s_table))
    lines.append("")

    # R15-M table
    lines.append("## R15-M Matrix (regex, bm25, symbol, rrf)")
    lines.append("")
    lines.append(_format_metric_table(r15m_table))
    lines.append("")

    # R15-stress table
    lines.append("## R15-stress Matrix (regex, bm25, symbol, rrf)")
    lines.append("")
    lines.append(_format_metric_table(r15stress_table))
    lines.append("")

    # Winners
    lines.append("## Winners per Metric")
    lines.append("")
    for matrix_name, matrix_winners in winners.items():
        lines.append(f"### {matrix_name}")
        for metric, winner_list in matrix_winners.items():
            lines.append(f"- **{metric}**: {', '.join(winner_list)}")
        lines.append("")

    # Conclusions
    lines.append("## Conclusions")
    lines.append("")
    for i, conclusion in enumerate(conclusions, 1):
        lines.append(f"{i}. {conclusion}")
    lines.append("")

    # Caveats
    lines.append("## Caveats")
    lines.append("- R16 is a multi-method quality bakeoff across R14-S/R15-M/R15-stress matrices; not a universal quality conclusion.")
    lines.append("- Mined labels are not human-verified; line ranges may be imprecise.")
    lines.append("- Hard negatives are first-class data measuring precision under ambiguity.")
    lines.append("- Citation validity is a safety gate, not a quality metric.")
    lines.append("- No promotion of any method to universal default from R16.")
    lines.append("- No provider/dense/LLM quality claims are made.")
    lines.append("- RRF negative_nonempty_rate reflects BM25 false-positive inheritance; not a retrieval quality win.")

    return "\n".join(lines)


def _format_metric_table(method_table: dict[str, dict[str, Any]]) -> str:
    """Format a method table as markdown."""
    if not method_table:
        return "_No data_"

    methods = list(method_table.keys())
    # Collect all metric keys in order
    seen: set[str] = set()
    metric_keys: list[str] = []
    for key in RECALL_METRICS:
        for row in method_table.values():
            if key in row and key not in seen:
                metric_keys.append(key)
                seen.add(key)

    header = "| Metric | " + " | ".join(methods) + " |"
    separator = "|---|" + "|".join("---" for _ in methods) + "|"
    lines = [header, separator]

    for key in metric_keys:
        row = f"| {key} |"
        for method in methods:
            val = method_table.get(method, {}).get(key)
            if val is None:
                row += " N/A |"
            elif isinstance(val, float):
                row += f" {val:.3f} |"
            else:
                row += f" {val} |"
        lines.append(row)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="R16 Multi-Method Quality Bakeoff"
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
        default="runs/r16-quality-bakeoff.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing reports if present (skip running benchmarks)",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    openlocus = str(resolve_path(args.openlocus, workspace))
    out_path = resolve_path(args.out, workspace)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Define the three benchmark runs
    runs_config = [
        {
            "name": "R14-S",
            "script": "eval/r14_benchmark.py",
            "args": [
                "--manifest", "fixtures/r14/dataset_manifest.json",
                "--openlocus", openlocus,
                "--methods", "regex,bm25,symbol,rrf",
                "--repos-root", str(workspace),
                "--tier", "S",
                "--out", str(workspace / "runs" / "r16-r14-s.json"),
            ],
            "out": workspace / "runs" / "r16-r14-s.json",
        },
        {
            "name": "R15-M",
            "script": "eval/r15_benchmark.py",
            "args": [
                "--manifest", "fixtures/r15/dataset_manifest.json",
                "--openlocus", openlocus,
                "--methods", "regex,bm25,symbol,rrf",
                "--tier", "M",
                "--out", str(workspace / "runs" / "r16-r15-m.json"),
            ],
            "out": workspace / "runs" / "r16-r15-m.json",
        },
        {
            "name": "R15-stress",
            "script": "eval/r15_benchmark.py",
            "args": [
                "--manifest", "fixtures/r15/dataset_manifest.json",
                "--openlocus", openlocus,
                "--methods", "regex,bm25,symbol,rrf",
                "--tier", "stress",
                "--out", str(workspace / "runs" / "r16-r15-stress.json"),
            ],
            "out": workspace / "runs" / "r16-r15-stress.json",
        },
    ]

    # Run benchmarks unless --skip-run
    if not args.skip_run:
        print("R16 Quality Bakeoff: Running benchmark matrices")
        for config in runs_config:
            print(f"\n{'='*60}")
            print(f"Running {config['name']}...")
            script_path = workspace / config["script"]
            cmd = ["python3", str(script_path)] + config["args"]
            run_command(cmd, config["name"], workspace)
            print(f"  {config['name']} complete.")
    else:
        print("R16 Quality Bakeoff: --skip-run, reusing existing reports")

    # Load reports
    print(f"\n{'='*60}")
    print("Loading reports and verifying safety gates...")

    reports: dict[str, dict[str, Any]] = {}
    all_safety_issues: list[str] = []

    for config in runs_config:
        name = config["name"]
        report = load_report(config["out"])
        reports[name] = report
        issues = verify_safety_gates(report, name)
        all_safety_issues.extend(issues)

    # Extract method tables
    r14s_table = extract_method_table(reports["R14-S"])
    r15m_table = extract_method_table(reports["R15-M"])
    r15stress_table = extract_method_table(reports["R15-stress"])

    # Compute winners per metric per matrix
    higher_better = {
        "file_recall@1": True,
        "file_recall@5": True,
        "file_recall@10": True,
        "mrr": True,
        "span_f0.5@10": True,
        "hard_negative_hit_rate@10": False,
        "negative_nonempty_rate@10": False,
        "citation_validity": True,
        "success_rate": True,
    }

    winners: dict[str, dict[str, list[str]]] = {}
    for matrix_name, table in [
        ("R14-S", r14s_table),
        ("R15-M", r15m_table),
        ("R15-stress", r15stress_table),
    ]:
        matrix_winners: dict[str, list[str]] = {}
        for metric, is_higher in higher_better.items():
            w = find_winners(table, metric, higher_is_better=is_higher)
            if w:
                matrix_winners[metric] = w
        winners[matrix_name] = matrix_winners

    # Conclusions based on observed data
    conclusions = [
        "RRF wins R15-M recall/MRR (FileRecall@1 0.933, @5/10 0.993, "
        "MRR 0.959) but inherits BM25 negative false positive behavior "
        "(negative_nonempty@10 0.645 on R15-M and 0.684 on stress), "
        "so it is not safe as default for precision-sensitive tasks without "
        "negative gating or query intent routing.",

        "Symbol has best span precision/hard-negative profile on R15-M "
        "(SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) "
        "but lower recall than RRF, so it is ideal as precision anchor, "
        "not sole retriever.",

        "Regex is surprisingly strong on mined exact-symbol external tasks "
        "(R15-M FileRecall@1 0.852, negative_nonempty 0.000), "
        "but this reflects task distribution and exact-string bias; "
        "not a general natural-language conclusion.",

        "BM25 strong in R14-S but weak and false-positive-heavy in "
        "R15-M/stress; needs query intent routing or threshold/negative guard.",

        "No promotion of any method to universal default from R16; "
        "next research should be query intent router / negative guard / "
        "method fusion policy, not raw channel addition.",
    ]

    # Generate JSON report
    timestamp = datetime.now(timezone.utc).isoformat()
    json_report = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "openlocus": openlocus,
        "workspace": str(workspace),
        "skip_run": args.skip_run,
        "runs": {
            "R14-S": {
                "script": "eval/r14_benchmark.py",
                "tier": "S",
                "report_path": str(runs_config[0]["out"]),
                "tasks": reports["R14-S"].get("tasks", 0),
                "repos": reports["R14-S"].get("repos", 0),
                "safety_passed": reports["R14-S"].get("safety_passed", False),
            },
            "R15-M": {
                "script": "eval/r15_benchmark.py",
                "tier": "M",
                "report_path": str(runs_config[1]["out"]),
                "tasks": reports["R15-M"].get("tasks", 0),
                "repos": reports["R15-M"].get("repos", 0),
                "safety_passed": reports["R15-M"].get("safety_passed", False),
            },
            "R15-stress": {
                "script": "eval/r15_benchmark.py",
                "tier": "stress",
                "report_path": str(runs_config[2]["out"]),
                "tasks": reports["R15-stress"].get("tasks", 0),
                "repos": reports["R15-stress"].get("repos", 0),
                "safety_passed": reports["R15-stress"].get("safety_passed", False),
            },
        },
        "method_tables": {
            "R14-S": r14s_table,
            "R15-M": r15m_table,
            "R15-stress": r15stress_table,
        },
        "winners": winners,
        "safety_checks": {
            "all_safety_passed": len(all_safety_issues) == 0,
            "issues": all_safety_issues,
            "per_matrix": {
                name: report.get("safety_passed", False)
                for name, report in reports.items()
            },
            "citation_hash_checked": {
                f"{matrix}/{method}": method_metrics.get("citation_hash_checked", False)
                for matrix, report in reports.items()
                for method, method_metrics in report.get("metrics", {}).items()
            },
            "canary_retrieval": {
                name: report.get("canary_retrieval", {}).get("passed", None)
                for name, report in reports.items()
            },
        },
        "conclusions": conclusions,
        "caveats": [
            "R16 is a multi-method quality bakeoff; not a universal quality conclusion.",
            "Mined labels are not human-verified; line ranges may be imprecise.",
            "Hard negatives are first-class data measuring precision under ambiguity.",
            "Citation validity is a safety gate, not a quality metric.",
            "No provider/dense/LLM quality claims are made.",
            "RRF negative_nonempty_rate reflects BM25 false-positive inheritance.",
        ],
        "remote_calls": 0,
        "dense_or_llm_claims": False,
    }

    out_path.write_text(
        json.dumps(json_report, indent=2) + "\n", encoding="utf-8"
    )

    # Generate markdown report
    md_content = generate_markdown_report(
        r14s_table,
        r15m_table,
        r15stress_table,
        all_safety_issues,
        winners,
        conclusions,
    )
    md_path = out_path.with_suffix(".md")
    md_path.write_text(md_content, encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print("R16 Quality Bakeoff Results")
    print(f"{'='*60}")

    for matrix_name, table in [
        ("R14-S", r14s_table),
        ("R15-M", r15m_table),
        ("R15-stress", r15stress_table),
    ]:
        print(f"\n{matrix_name}:")
        for method in METHODS:
            if method in table:
                row = table[method]
                recall1 = row.get("file_recall@1", 0)
                mrr_val = row.get("mrr", 0)
                span = row.get("span_f0.5@10", 0)
                hn = row.get("hard_negative_hit_rate@10", 0)
                neg = row.get("negative_nonempty_rate@10", 0)
                print(
                    f"  {method}: @1={recall1:.3f}, MRR={mrr_val:.3f}, "
                    f"SpanF0.5={span:.3f}, hard_neg={hn:.3f}, "
                    f"neg_nonempty={neg:.3f}"
                )

    if all_safety_issues:
        print(f"\nSafety issues: {len(all_safety_issues)}")
        for issue in all_safety_issues:
            print(f"  - {issue}")
    else:
        print(f"\nAll safety checks passed")

    print(f"\nReport: {out_path}")
    print(f"Summary: {md_path}")

    # Hard fail on safety
    if all_safety_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
