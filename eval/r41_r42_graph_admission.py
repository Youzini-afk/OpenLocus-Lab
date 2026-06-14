#!/usr/bin/env python3
"""R41-R42 graph role research and admission model v2 rules.

R41 treats graph as supporting/rerank/explainer, not default expansion.  R42
builds an explainable rule-based admission layer with actions:

  admit_primary, admit_supporting, weak_candidate_only, abstain, fallback_symbol_regex

No learned model is promoted, no EvidenceCore semantics change, and graph
expansion remains blocked unless future evidence shows added_gold > added_false.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import r34_r36_quiver_anchor_proto as r34  # type: ignore
    import r39_r40_symbol_regex_repair as r39  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import r34_r36_quiver_anchor_proto as r34  # type: ignore
    import r39_r40_symbol_regex_repair as r39  # type: ignore


SCHEMA_VERSION = "r41-r42-graph-admission-v1"
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Path], Path, Any | None]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r41-r42-")
        repo_lock, tasks_path, labels_path, repo_roots = r32.make_self_test_inputs(Path(tmp_ctx.name))
        tasks = r32.load_jsonl(tasks_path)
        args._tmp_ctx = tmp_ctx
        return tasks, repo_roots, labels_path, tmp_ctx
    repo_roots = r32.load_repo_lock(args.repo_lock)
    tasks = [task for task in r32.load_jsonl(args.tasks) if task["repo_id"] in repo_roots][: args.max_tasks]
    args._tmp_ctx = None
    return tasks, repo_roots, args.labels, None


def build_files(repo_roots: dict[str, Path], args: argparse.Namespace) -> list[r39.SourceFile]:
    return r39.source_files(repo_roots, args)


def low_risk_edges(files: list[r39.SourceFile]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_repo_path = {(f.repo_id, f.path): f for f in files}
    for f in files:
        symbols = r39.new_symbols(f)
        for sym in symbols:
            edges.append({"edge": "DEFINES", "repo_id": f.repo_id, "src": f.path, "dst": sym["name"], "line": sym["line"]})
            edges.append({"edge": "CONTAINS", "repo_id": f.repo_id, "src": f.path, "dst": f"{f.path}:{sym['line']}", "line": sym["line"]})
        for i, line in enumerate(f.lines, 1):
            if re.search(r"\b(import|from|use|require)\b", line):
                edges.append({"edge": "IMPORTS", "repo_id": f.repo_id, "src": f.path, "dst": line.strip()[:120], "line": i})
        if "test" in f.path.lower() or any("assert" in line for line in f.lines):
            for (_, path), target in by_repo_path.items():
                if target.repo_id == f.repo_id and "test" not in target.path.lower() and Path(target.path).stem in f.text:
                    edges.append({"edge": "TESTS", "repo_id": f.repo_id, "src": f.path, "dst": target.path, "line": 1})
    return edges


def graph_support(task: dict[str, Any], files: list[r39.SourceFile], edges: list[dict[str, Any]]) -> dict[str, Any]:
    toks = {tok.lower() for tok in TOKEN_RE.findall(task["query"])}
    repo_edges = [e for e in edges if e["repo_id"] == task["repo_id"]]
    matched = [e for e in repo_edges if any(tok in str(e.get("dst", "")).lower() or tok in str(e.get("src", "")).lower() for tok in toks)]
    support_paths = sorted({e["src"] for e in matched})[:5]
    return {
        "support_count": len(matched),
        "support_paths": support_paths,
        "edge_types": sorted({e["edge"] for e in matched}),
        "confidence_boost": min(0.2, 0.03 * len(matched)),
    }


def regex_symbol_features(task: dict[str, Any], files: list[r39.SourceFile]) -> dict[str, Any]:
    repo_files = [f for f in files if f.repo_id == task["repo_id"]]
    toks = {tok.lower() for tok in TOKEN_RE.findall(task["query"])}
    regex_hits = 0
    symbol_hits = 0
    path_hits = 0
    for f in repo_files:
        haystack = f.path.lower() + "\n" + f.text.lower()
        if any(tok in haystack for tok in toks):
            regex_hits += 1
        if any(tok in f.path.lower() for tok in toks):
            path_hits += 1
        for sym in r39.new_symbols(f):
            if any(tok in sym["name"].lower() or sym["name"].lower() in tok for tok in toks):
                symbol_hits += 1
    return {
        "regex_hit_count": regex_hits,
        "symbol_hit_count": symbol_hits,
        "path_match_score": min(1.0, path_hits / 3),
        "identifier_density": sum(1 for tok in toks if re.match(r"^[A-Za-z_]\w+$", tok)) / max(1, len(toks)),
        "proper_name_score": sum(1 for tok in TOKEN_RE.findall(task["query"]) if tok[:1].isupper()) / max(1, len(toks)),
        "api_config_score": 1.0 if re.search(r"\b(api|config|key|route|handler|timeout)\b", task["query"], re.I) else 0.0,
    }


def admission_action(features: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    regex_hits = features["regex_hit_count"]
    symbol_hits = features["symbol_hit_count"]
    graph_support_count = features["graph_support"]["support_count"]
    identifier_density = features["identifier_density"]
    proper_name_score = features["proper_name_score"]
    api_config_score = features["api_config_score"]
    channel_count = int(regex_hits > 0) + int(symbol_hits > 0) + int(graph_support_count > 0)

    if symbol_hits and regex_hits:
        reasons.append("regex_symbol_agreement")
        return "admit_primary", reasons
    if symbol_hits:
        reasons.append("symbol_anchor")
        return "fallback_symbol_regex", reasons
    if regex_hits and graph_support_count and identifier_density > 0.4:
        reasons.append("regex_graph_identifier_support")
        return "admit_supporting", reasons
    if graph_support_count and channel_count == 1:
        reasons.append("graph_only_supporting_not_primary")
        return "weak_candidate_only", reasons
    if proper_name_score > 0.5 or api_config_score > 0.0:
        reasons.append("proper_name_or_api_config_requires_anchor")
        return "abstain", reasons
    if regex_hits:
        reasons.append("regex_only_weak")
        return "weak_candidate_only", reasons
    reasons.append("no_anchor")
    return "abstain", reasons


def evidence_for_action(task: dict[str, Any], files: list[r39.SourceFile], action: str) -> list[dict[str, Any]]:
    if action in {"abstain", "weak_candidate_only"}:
        return []
    toks = {tok.lower() for tok in TOKEN_RE.findall(task["query"])}
    evidence = []
    for f in files:
        if f.repo_id != task["repo_id"]:
            continue
        for i, line in enumerate(f.lines, 1):
            if any(tok in line.lower() or tok in f.path.lower() for tok in toks):
                evidence.append({"path": f.path, "start_line": i, "end_line": i, "content_sha": f.content_sha, "score": 1.0, "why": ["admission_v2_rules", action, "candidate_not_fact"], "channels": ["regex", "symbol", "graph_support"]})
                break
    return evidence[:5]


def run_admission(tasks: list[dict[str, Any]], files: list[r39.SourceFile], edges: list[dict[str, Any]]) -> dict[str, Any]:
    preds = []
    action_counts: dict[str, int] = defaultdict(int)
    explanations: list[dict[str, Any]] = []
    graph_supports: dict[str, dict[str, Any]] = {}
    for task in tasks:
        features = regex_symbol_features(task, files)
        g = graph_support(task, files, edges)
        features["graph_support"] = g
        action, reasons = admission_action(features)
        action_counts[action] += 1
        ev = evidence_for_action(task, files, action)
        tid = task.get("test_id") or task.get("task_id")
        if not tid:
            continue
        preds.append({"task_id": tid, "repo_id": task["repo_id"], "strategy": "admission_v2_rules", "evidence": ev, "latency_ms": 0, "returncode": 0})
        graph_supports[tid] = g
        explanations.append({"task_id": tid, "action": action, "reasons": reasons, "features": features})
    return {
        "predictions": preds,
        "action_counts": dict(action_counts),
        "examples": explanations[:20],
        "graph_supports": graph_supports,
    }


def score_admission(run_output: dict[str, Any], tasks: list[dict[str, Any]], labels: dict[str, dict[str, Any]], repo_roots: dict[str, Path], edges: list[dict[str, Any]]) -> dict[str, Any]:
    preds = run_output["predictions"]
    graph_supports = run_output["graph_supports"]
    graph_added_gold = 0
    graph_added_false = 0
    test_selector_hits = 0
    test_selector_total = 0
    task_by_id = {task.get("test_id") or task.get("task_id"): task for task in tasks}
    for tid, g in graph_supports.items():
        label = labels.get(tid, {})
        task = task_by_id.get(tid, {})
        for path in g["support_paths"]:
            matched = any(span["path"] == path for span in label.get("gold_spans", []))
            if matched:
                graph_added_gold += 1
            else:
                graph_added_false += 1
        if task and any(edge["edge"] == "TESTS" for edge in edges if edge["repo_id"] == task.get("repo_id")):
            test_selector_total += 1
            if any("test" in p.lower() for p in g["support_paths"]):
                test_selector_hits += 1
    m = r32.metrics_for(preds, labels, repo_roots, [0] * len(preds))
    answered = sum(1 for p in preds if p.get("evidence"))
    false_answered = sum(1 for p in preds if p.get("evidence") and not labels.get(p["task_id"], {}).get("gold_spans"))
    m.update({
        "coverage": answered / len(preds) if preds else 0.0,
        "selective_risk": false_answered / answered if answered else 0.0,
        "action_counts": run_output["action_counts"],
        "graph_added_gold_span": graph_added_gold,
        "graph_added_false_span": graph_added_false,
        "graph_pollution_ratio": graph_added_false / max(1, graph_added_gold + graph_added_false),
        "graph_expansion_blocked": graph_added_false >= graph_added_gold,
        "graph_confidence_calibration": "supporting_only",
        "graph_explainer_precision": graph_added_gold / max(1, graph_added_gold + graph_added_false),
        "test_selector_hit_rate": test_selector_hits / test_selector_total if test_selector_total else 0.0,
    })
    return {"metrics": m, "examples": run_output["examples"]}


def run(args: argparse.Namespace) -> dict[str, Any]:
    tasks, repo_roots, labels_path, tmp_ctx = load_inputs(args)
    issues = r32.validate_public_tasks(tasks)
    if issues:
        raise SystemExit("public task validation failed: " + "; ".join(issues[:5]))
    files = build_files(repo_roots, args)
    edges = low_risk_edges(files)
    # RUN phase: only public tasks/files/graph edges are used above this line.
    run_output = run_admission(tasks, files, edges)
    # SCORE phase: private labels load only after predictions and explanations.
    labels = r32.normalize_labels(r32.load_jsonl(labels_path))
    result = score_admission(run_output, tasks, labels, repo_roots, edges)
    if tmp_ctx is not None:
        tmp_ctx.cleanup()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
        "graph_default_expansion_allowed": False,
        "graph_role_recommendation": "supporting_or_explainer_only",
        "admission_model": "admission_v2_rules",
        "learned_calibrator_default_allowed": False,
        "run_phase_public_only": True,
        "task_count": len(tasks),
        "file_count": len(files),
        "edge_count": len(edges),
        "edge_types": sorted({edge["edge"] for edge in edges}),
        "metrics": result["metrics"],
        "example_decisions": result["examples"],
        "blocking": {
            "graph_expansion_blocked": result["metrics"]["graph_expansion_blocked"],
            "promotion_blocked": True,
        },
    }


def write_doc(report: dict[str, Any], path: Path) -> None:
    m = report["metrics"]
    lines = [
        "# R41-R42 Graph Role and Admission Model v2",
        "",
        "R41 evaluates graph as supporting/rerank/explainer only. R42 introduces an explainable rule-based admission model without promoting it.",
        "",
        "## Safety",
        "",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        f"- graph_default_expansion_allowed: `{report.get('graph_default_expansion_allowed')}`",
        f"- graph_role_recommendation: `{report.get('graph_role_recommendation')}`",
        f"- learned_calibrator_default_allowed: `{report.get('learned_calibrator_default_allowed')}`",
        "",
        "## Metrics",
        "",
        f"- selective_risk: `{m.get('selective_risk')}`",
        f"- coverage: `{m.get('coverage')}`",
        f"- FileRecall@1: `{m.get('FileRecall@1')}`",
        f"- SpanF0.5: `{m.get('SpanF0.5')}`",
        f"- graph_added_gold_span: `{m.get('graph_added_gold_span')}`",
        f"- graph_added_false_span: `{m.get('graph_added_false_span')}`",
        f"- graph_expansion_blocked: `{m.get('graph_expansion_blocked')}`",
        "",
        "## Admission Actions",
        "",
    ]
    for action, count in sorted(m.get("action_counts", {}).items()):
        lines.append(f"- {action}: `{count}`")
    lines.extend([
        "",
        "## Decision",
        "",
        "- Graph expansion remains blocked; graph can continue as supporting/explainer research.",
        "- `admission_v2_rules` is explainable research only; no learned router/default promotion.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/r41_r42/graph_admission.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/en/r41-r42-graph-admission.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    args._tmp_ctx = None
    report = run(args)
    write_json(args.out, report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
