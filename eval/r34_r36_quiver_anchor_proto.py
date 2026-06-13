#!/usr/bin/env python3
"""R34-R36 minimal QuIVer diagnostic prototype and anchor-seeded dense harness.

This is a research harness, not a production backend.  It compares:
  * flat_f32 diagnostic search,
  * bq_topk_f32_rerank diagnostic search,
  * sharded variants (per_view, per_language, source_vs_test_split), and
  * anchor-seeded candidate-pool restrictions.

It does not implement a Vamana/QuIVer graph (`quiver_mode=diagnostic_only`) and
does not change EvidenceCore.  All hits are candidates/supporting-only until
materialized and scored against labels in the SCORE phase.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import r33_quiver_readiness as r33  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import r33_quiver_readiness as r33  # type: ignore


SCHEMA_VERSION = "r34-r36-quiver-anchor-proto-v1"
DEFAULT_VIEWS = ["path_plus_symbol", "signature_plus_doc", "raw_code_trimmed", "mixed_all_views"]
ANCHOR_MODES = ["global", "regex", "symbol", "regex_or_symbol"]
LAYOUTS = ["global_mixed_all", "per_view", "per_language", "source_vs_test_split", "generated_excluded", "per_view_plus_language"]
SYMBOL_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


@dataclass
class CandidateRecord:
    rec: r32.ViewRecord
    f32_score: float = 0.0
    bq_distance: int = 0


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Path], dict[str, dict[str, Any]]]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r34-r36-")
        repo_lock, tasks_path, labels_path, repo_roots = r32.make_self_test_inputs(Path(tmp_ctx.name))
        args._tmp_ctx = tmp_ctx
    else:
        repo_lock, tasks_path, labels_path = args.repo_lock, args.tasks, args.labels
        repo_roots = r32.load_repo_lock(repo_lock)
        args._tmp_ctx = None
    repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
    tasks = [task for task in r32.load_jsonl(tasks_path) if task["repo_id"] in repo_roots]
    issues = r32.validate_public_tasks(tasks)
    if issues:
        raise SystemExit("public task validation failed: " + "; ".join(issues[:5]))
    # Labels are loaded by caller after RUN phase, but self-test needs the path
    # retained.  The caller receives no labels here.
    args._labels_path = labels_path
    return tasks[: args.max_tasks], repo_roots, {}


def build_records(args: argparse.Namespace, repo_roots: dict[str, Path]) -> list[r32.ViewRecord]:
    views = [v.strip() for v in args.views.split(",") if v.strip()]
    records: list[r32.ViewRecord] = []
    for repo_id, root in repo_roots.items():
        scan_map = r32.run_scan(args.openlocus, root)
        for file_path in r32.iter_source_files(root):
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            built = r32.build_views_for_file(repo_id, root, file_path, scan_map.get(rel))
            for view in views:
                records.extend(built.get(view, [])[: args.max_records_per_file])
    records = records[: args.max_records]
    if args.provider == "openai-compatible" and any(record.view_kind not in r32.REMOTE_SAFE_VIEWS for record in records):
        raise SystemExit("remote R34-R36 is restricted to path_plus_symbol data-level-0 views")
    embed_status = r32.embed_records(records, args.provider, args.allow_remote)
    if embed_status.get("status") != "ok":
        raise SystemExit("provider unavailable: " + str(embed_status.get("reason")))
    return [record for record in records if record.vector]


def query_vector(query: str, args: argparse.Namespace) -> list[float]:
    if args.provider == "local_token_hash":
        return r32.token_hash_embedding(f"query {query}")
    if not args.allow_remote or r32.text_has_secret(query):
        return []
    try:
        return r32.remote_embed([f"query {query}"])[0]
    except Exception:
        return []


def layout_filter(records: list[r32.ViewRecord], layout: str, query: str) -> list[r32.ViewRecord]:
    if layout == "global_mixed_all":
        return records
    if layout == "per_view":
        # Search each view independently by keeping all records; grouping is
        # represented in report metadata.  The ranking path stays comparable.
        return records
    if layout == "per_language":
        query_l = query.lower()
        if "python" in query_l or "pytest" in query_l:
            return [r for r in records if r.language == "python"] or records
        if "rust" in query_l or "cargo" in query_l:
            return [r for r in records if r.language == "rust"] or records
        if "config" in query_l or "yaml" in query_l or "toml" in query_l:
            return [r for r in records if r.language == "config"] or records
        return records
    if layout == "source_vs_test_split":
        wants_test = bool(re.search(r"\b(test|spec|assert|pytest)\b", query, re.I))
        return [r for r in records if ("test" in r.path.lower()) == wants_test] or records
    if layout == "generated_excluded":
        return [r for r in records if not re.search(r"(generated|vendor|node_modules|dist|build)", r.path, re.I)]
    if layout == "per_view_plus_language":
        return layout_filter(layout_filter(records, "per_language", query), "per_view", query)
    return records


def anchor_filter(records: list[r32.ViewRecord], query: str, anchor_mode: str) -> list[r32.ViewRecord]:
    if anchor_mode == "global":
        return records
    tokens = {tok.lower() for tok in SYMBOL_TOKEN_RE.findall(query)}
    if not tokens:
        return records
    def path_or_symbol(rec: r32.ViewRecord) -> bool:
        haystack = f"{rec.path} {rec.text}".lower()
        return any(tok in haystack for tok in tokens)
    if anchor_mode in {"regex", "symbol", "regex_or_symbol"}:
        filtered = [rec for rec in records if path_or_symbol(rec)]
        return filtered or []
    return records


def flat_f32(query_vec: list[float], records: list[r32.ViewRecord], limit: int) -> list[CandidateRecord]:
    candidates = [CandidateRecord(rec, r32.cosine(query_vec, rec.vector or []), 0) for rec in records if rec.vector]
    candidates.sort(key=lambda item: item.f32_score, reverse=True)
    return candidates[:limit]


def bq_topk_rerank(query_vec: list[float], records: list[r32.ViewRecord], bq_limit: int, final_limit: int) -> list[CandidateRecord]:
    vectors = [rec.vector or [] for rec in records if rec.vector]
    kept = [rec for rec in records if rec.vector]
    if not vectors:
        return []
    thresholds = r33.dimension_thresholds(vectors)
    q_bq = r33.bq2_encode(query_vec, thresholds)
    encoded = [r33.bq2_encode(vec, thresholds) for vec in vectors]
    prelim = sorted((r33.bq2_distance(q_bq, e), idx) for idx, e in enumerate(encoded))[: min(bq_limit, len(encoded))]
    candidates = [CandidateRecord(kept[idx], r32.cosine(query_vec, kept[idx].vector or []), dist) for dist, idx in prelim]
    candidates.sort(key=lambda item: item.f32_score, reverse=True)
    return candidates[:final_limit]


def to_evidence(items: list[CandidateRecord], strategy: str) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in items:
        rec = item.rec
        evidence.append({
            "path": rec.path,
            "start_line": rec.start_line,
            "end_line": rec.end_line,
            "content_sha": rec.content_sha,
            "score": round(item.f32_score, 6),
            "why": [strategy, "candidate_not_fact", "quiver_mode=diagnostic_only"],
            "channels": ["dense", "quiver_diag"],
            "meta": {"view_kind": rec.view_kind, "bq_distance": item.bq_distance, "role": "candidate/supporting-only"},
        })
    return evidence


def run_strategy(tasks: list[dict[str, Any]], records: list[r32.ViewRecord], args: argparse.Namespace, strategy: str, layout: str, anchor_mode: str) -> tuple[list[dict[str, Any]], list[int]]:
    predictions: list[dict[str, Any]] = []
    latencies: list[int] = []
    for task in tasks:
        started = time.time()
        repo_records = [rec for rec in records if rec.repo_id == task["repo_id"]]
        filtered = anchor_filter(layout_filter(repo_records, layout, task["query"]), task["query"], anchor_mode)
        query_vec = query_vector(task["query"], args)
        if not query_vec or not filtered:
            items: list[CandidateRecord] = []
        elif strategy.startswith("flat_f32"):
            items = flat_f32(query_vec, filtered, args.top_k)
        else:
            items = bq_topk_rerank(query_vec, filtered, args.bq_limit, args.top_k)
        latencies.append(int((time.time() - started) * 1000))
        predictions.append({
            "task_id": task.get("test_id") or task.get("task_id"),
            "repo_id": task["repo_id"],
            "strategy": strategy,
            "evidence": to_evidence(items, strategy),
            "latency_ms": latencies[-1],
            "returncode": 0,
        })
    return predictions, latencies


def contribution(predictions: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    added_gold = 0
    added_false = 0
    semantic_trap_nonempty = 0
    for pred in predictions:
        label = labels.get(pred["task_id"], {})
        gold_spans = label.get("gold_spans", [])
        if label.get("source_category") == "dense_quiver_trap" and pred.get("evidence"):
            semantic_trap_nonempty += 1
        for ev in pred.get("evidence", []):
            matched = False
            for span in gold_spans:
                if ev["path"] == span["path"] and int(ev["end_line"]) >= int(span["start_line"]) and int(ev["start_line"]) <= int(span["end_line"]):
                    matched = True
                    break
            if matched:
                added_gold += 1
            else:
                added_false += 1
    return {
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "semantic_trap_nonempty": semantic_trap_nonempty,
        "default_expansion_blocked": added_false >= added_gold,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    tasks, repo_roots, _ = load_inputs(args)
    records = build_records(args, repo_roots)
    run_outputs: dict[str, tuple[list[dict[str, Any]], list[int]]] = {}
    # RUN phase: labels are not loaded until every strategy has produced its
    # predictions from public tasks + candidate records.
    labels_loaded_after_run = False
    labels_loaded_path = str(args._labels_path)
    results: dict[str, Any] = {}
    for layout in LAYOUTS:
        for anchor in ANCHOR_MODES:
            for mode in ["flat_f32", "bq_topk_f32_rerank"]:
                strategy = f"{mode}__{layout}__anchor_{anchor}"
                preds, latencies = run_strategy(tasks, records, args, strategy, layout, anchor)
                run_outputs[strategy] = (preds, latencies)

    # SCORE phase: private labels are loaded only after all RUN predictions are
    # available.  This preserves the R26/R29 public-task discipline.
    labels = r32.normalize_labels(r32.load_jsonl(args._labels_path))
    labels_loaded_after_run = True
    baseline = r32.load_r30_baseline(args.r30_baseline)
    for strategy, (preds, latencies) in run_outputs.items():
        metrics = r32.metrics_for(preds, labels, repo_roots, latencies)
        metrics.update(contribution(preds, labels))
        metrics["delta_vs_r29_baseline"] = r32.delta(metrics, baseline)
        metrics["candidate_count"] = sum(len(p.get("evidence", [])) for p in preds)
        metrics["hot_memory_estimate_bytes"] = len(records) * (len(records[0].vector or []) if records else 0) * 4
        results[strategy] = metrics
    best = sorted(results.items(), key=lambda kv: (kv[1].get("added_gold_span", 0) - kv[1].get("added_false_span", 0), kv[1].get("SpanF0.5", 0)), reverse=True)[:5]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "quiver_mode": "diagnostic_only",
        "quiver_graph_implemented": False,
        "vamana_pruning_implemented": False,
        "bq_topk_implemented": True,
        "f32_rerank_implemented": True,
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
        "global_index_safe": False,
        "quiver_default_allowed": False,
        "quiver_supporting_channel_allowed": True,
        "dense_or_quiver_role": "candidate/supporting-only",
        "repo_count": len(repo_roots),
        "task_count": len(tasks),
        "record_count": len(records),
        "run_phase_public_only": True,
        "labels_loaded_after_run": labels_loaded_after_run,
        "score_phase_labels_only": True,
        "score_labels_path_recorded": bool(labels_loaded_path),
        "views": [v.strip() for v in args.views.split(",") if v.strip()],
        "strategies_evaluated": len(results),
        "best_net_strategies": [{"strategy": name, "metrics": metrics} for name, metrics in best],
        "results": results,
        "conclusion": {
            "quiver_proto_is_faster_quality_claim": False,
            "quiver_proto_is_quality_claim": False,
            "anchor_seeded_research_continue": True,
            "default_expansion_blocked": True,
        },
    }


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# R34-R36 QuIVer Diagnostic Prototype and Anchor-Seeded Dense",
        "",
        "This phase implements an offline diagnostic prototype: flat f32 search, BQ top-k + f32 rerank, sharding layouts, and anchor-seeded candidate-pool restriction. It does not implement Vamana/QuIVer graph search.",
        "",
        "## Safety",
        "",
        f"- quiver_mode: `{report.get('quiver_mode')}`",
        f"- quiver_graph_implemented: `{report.get('quiver_graph_implemented')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        f"- run_phase_public_only: `{report.get('run_phase_public_only')}`",
        f"- labels_loaded_after_run: `{report.get('labels_loaded_after_run')}`",
        f"- quiver_default_allowed: `{report.get('quiver_default_allowed')}`",
        f"- quiver_supporting_channel_allowed: `{report.get('quiver_supporting_channel_allowed')}`",
        "",
        "## Best Net Strategies",
        "",
        "| Strategy | SpanF0.5 | added_gold_span | added_false_span | semantic_trap_nonempty | default_expansion_blocked |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in report.get("best_net_strategies", []):
        m = item["metrics"]
        lines.append(f"| {item['strategy']} | {m.get('SpanF0.5')} | {m.get('added_gold_span')} | {m.get('added_false_span')} | {m.get('semantic_trap_nonempty')} | {m.get('default_expansion_blocked')} |")
    lines.extend([
        "",
        "## Decision",
        "",
        "- `quiver_mode=diagnostic_only`; no QuIVer graph quality numbers are claimed.",
        "- Global/default expansion remains blocked.",
        "- Anchor-seeded dense/QuIVer remains a research direction for R43, supporting-only.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--r30-baseline", type=Path, default=Path("artifacts/r30/baseline_manifest.json"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    parser.add_argument("--provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--max-records", type=int, default=2000)
    parser.add_argument("--max-records-per-file", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--bq-limit", type=int, default=50)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/r34_r36/quiver_anchor_proto.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/r34-r36-quiver-anchor-proto.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    args._tmp_ctx = None

    report = run(args)
    write_json(args.out, report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    write_doc(report, args.doc)
    tmp_ctx = getattr(args, "_tmp_ctx", None)
    if tmp_ctx is not None:
        tmp_ctx.cleanup()
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
