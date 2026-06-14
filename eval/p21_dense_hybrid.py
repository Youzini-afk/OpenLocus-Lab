#!/usr/bin/env python3
"""P21-G2E constrained/fused dense hybrid harness.

P21-G1E showed embedding context atoms have file/span signal but naked dense
adds many false spans.  P21-G2E tests dense only as constrained/supporting
signal combined with local anchors (RRF, symbol, regex).  Dense candidates never
become Evidence directly and the default/promotion decision stays false.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import p20_llm_large_scale as p20  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import p20_llm_large_scale as p20  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore


SCHEMA_VERSION = "p21-g2e-dense-hybrid-v1"
ANCHOR_METHODS = ["rrf", "symbol", "regex"]
DEFAULT_DENSE_STRATEGIES = "pack2_evidence_sketch,atom_signature"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evidence_key(ev: dict[str, Any]) -> tuple[Any, ...]:
    return (ev.get("path"), int(ev.get("start_line", 0)), int(ev.get("end_line", 0)), ev.get("content_sha"))


def dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for ev in items:
        key = evidence_key(ev)
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out


def mark(ev: dict[str, Any], source: str, role: str) -> dict[str, Any]:
    out = dict(ev)
    out["why"] = list(out.get("why") or []) + ["P21-G2E candidate_not_fact", source]
    out["channels"] = sorted(set(list(out.get("channels") or []) + [source]))
    meta = dict(out.get("meta") or {})
    meta.update({"p21_g2e_source": source, "role": role, "candidate_not_fact": True, "not_evidence_until_materialized": True})
    out["meta"] = meta
    return out


def rrf_fuse(named_lists: list[tuple[str, list[dict[str, Any]]]], *, k: int = 60, top_k: int = 10) -> list[dict[str, Any]]:
    scores: dict[tuple[Any, ...], float] = {}
    evidence: dict[tuple[Any, ...], dict[str, Any]] = {}
    sources: dict[tuple[Any, ...], set[str]] = {}
    for name, items in named_lists:
        for rank, ev in enumerate(items):
            key = evidence_key(ev)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            evidence.setdefault(key, dict(ev))
            sources.setdefault(key, set()).add(name)
    ranked = sorted(scores, key=lambda key: scores[key], reverse=True)
    out: list[dict[str, Any]] = []
    for key in ranked[:top_k]:
        ev = dict(evidence[key])
        ev["score"] = round(scores[key], 6)
        ev["why"] = list(ev.get("why") or []) + ["P21-G2E late_fusion"]
        ev["channels"] = sorted(set(list(ev.get("channels") or []) + list(sources[key])))
        meta = dict(ev.get("meta") or {})
        meta["fusion_sources"] = sorted(sources[key])
        meta["candidate_not_fact"] = True
        meta["not_evidence_until_materialized"] = True
        ev["meta"] = meta
        out.append(ev)
    return out


def same_files(items: list[dict[str, Any]], max_files: int) -> set[str]:
    files: list[str] = []
    for ev in items:
        path = str(ev.get("path") or "")
        if path and path not in files:
            files.append(path)
        if len(files) >= max_files:
            break
    return set(files)


def run_anchor_predictions(
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    openlocus: Path | None,
    top_k: int,
) -> dict[str, list[dict[str, Any]]]:
    predictions: dict[str, list[dict[str, Any]]] = {method: [] for method in ANCHOR_METHODS}
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task["repo_id"]
        query = task["query"]
        root = repo_roots.get(repo_id)
        for method in ANCHOR_METHODS:
            if not root:
                evidence: list[dict[str, Any]] = []
                latency_ms = 0
                returncode = -1
            else:
                result = p20.run_strategy_query(method, query, root, openlocus, top_k)
                evidence = [mark(ev, method, "anchor") for ev in result.get("evidence", [])]
                latency_ms = int(result.get("latency_ms", 0))
                returncode = int(result.get("returncode", 0))
            predictions[method].append({
                "task_id": tid,
                "repo_id": repo_id,
                "strategy": f"anchor_{method}",
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "evidence": evidence[:top_k],
                "latency_ms": latency_ms,
                "returncode": returncode,
            })
    return predictions


def dense_predictions(
    args: argparse.Namespace,
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, Any]]:
    strategies = p21e.strategy_list(args.dense_strategies)
    by_view = p21e.build_all_views(args, repo_roots)
    file_filter = p21e.remote_file_filter(repo_roots, allow_self_test=bool(args.self_test))
    outputs: dict[str, list[dict[str, Any]]] = {}
    statuses: dict[str, Any] = {}
    for strategy in strategies:
        records = p21e.records_for_strategy(by_view, strategy, repo_roots, args.max_records_per_repo)
        embed_status = p21e.p21_embed_records(records, args.provider, args.allow_remote, args.max_remote_data_level, file_filter)
        if embed_status.get("status") != "ok":
            statuses[strategy] = {"status": "unavailable", "reason": embed_status.get("reason"), "records": len(records)}
            continue
        preds, _latencies, query_stats = p21e.rank_strategy(tasks, records, args.provider, args.top_k)
        if args.provider != "local_token_hash" and (
            not query_stats.get("query_embedding_complete", False)
            or query_stats.get("reason_code")
            or query_stats.get("error_type")
            or int(query_stats.get("remote_calls", 0)) < len(tasks)
        ):
            statuses[strategy] = {"status": "unavailable", "reason": "remote query embedding incomplete_or_failed", **query_stats, "records": len(records)}
            continue
        for pred in preds:
            pred["strategy"] = f"dense_{strategy}"
            pred["evidence"] = [mark(ev, f"dense_{strategy}", "dense_candidate") for ev in pred.get("evidence", [])]
        outputs[strategy] = preds
        statuses[strategy] = {
            "status": "ok",
            "records": len(records),
            "unique_candidate_records": len({(r.repo_id, r.path, r.start_line, r.end_line, r.content_sha) for r in records}),
            "embed_status": embed_status,
            "query_remote_stats": query_stats,
            "views": p21e.STRATEGY_VIEWS[strategy],
        }
    return outputs, statuses, file_filter


def by_task(predictions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(pred.get("task_id")): pred for pred in predictions}


def build_hybrids(
    tasks: list[dict[str, Any]],
    anchor_preds: dict[str, list[dict[str, Any]]],
    dense_preds: dict[str, list[dict[str, Any]]],
    top_k: int,
    anchor_file_k: int,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"rrf_baseline": anchor_preds["rrf"]}
    anchor_maps = {name: by_task(preds) for name, preds in anchor_preds.items()}
    for dense_name, dense_list in dense_preds.items():
        dense_map = by_task(dense_list)
        for strategy in [
            f"dense_{dense_name}_only",
            f"dense_{dense_name}_rrf_file_constrained",
            f"dense_{dense_name}_symbol_regex_file_constrained",
            f"rrf_plus_dense_{dense_name}_supporting",
            f"rrf_dense_{dense_name}_late_fusion_anchor_constrained",
            f"query_noise_guard_rrf_dense_{dense_name}",
        ]:
            out[strategy] = []
        for task in tasks:
            tid = str(task.get("test_id") or task.get("task_id"))
            query = task["query"]
            repo_id = task["repo_id"]
            rrf_ev = list(anchor_maps["rrf"].get(tid, {}).get("evidence", []))
            symbol_ev = list(anchor_maps["symbol"].get(tid, {}).get("evidence", []))
            regex_ev = list(anchor_maps["regex"].get(tid, {}).get("evidence", []))
            dense_ev = list(dense_map.get(tid, {}).get("evidence", []))
            rrf_files = same_files(rrf_ev, anchor_file_k)
            sr_files = same_files(symbol_ev + regex_ev, anchor_file_k)
            any_anchor_files = rrf_files | sr_files

            constrained_rrf = [ev for ev in dense_ev if ev.get("path") in rrf_files]
            constrained_sr = [ev for ev in dense_ev if ev.get("path") in sr_files]
            constrained_any = [ev for ev in dense_ev if ev.get("path") in any_anchor_files]
            supporting = dedupe_evidence(rrf_ev + constrained_any)[:top_k] if rrf_ev else []
            late = rrf_fuse([("rrf", rrf_ev), ("dense", constrained_any)], top_k=top_k) if any_anchor_files else []
            noise = p20.is_negative_noise_query(query) or p20.is_vague_multi_word_query(query) or p20.is_compound_snake_case_noise(query)
            guarded = [] if noise else late

            variants = {
                f"dense_{dense_name}_only": dense_ev[:top_k],
                f"dense_{dense_name}_rrf_file_constrained": constrained_rrf[:top_k],
                f"dense_{dense_name}_symbol_regex_file_constrained": constrained_sr[:top_k],
                f"rrf_plus_dense_{dense_name}_supporting": supporting,
                f"rrf_dense_{dense_name}_late_fusion_anchor_constrained": late,
                f"query_noise_guard_rrf_dense_{dense_name}": guarded,
            }
            for strategy, evidence in variants.items():
                out[strategy].append({
                    "task_id": tid,
                    "repo_id": repo_id,
                    "strategy": strategy,
                    "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "evidence": evidence[:top_k],
                    "latency_ms": 0,
                    "returncode": 0,
                })
    return out


def score_predictions(preds_by_strategy: dict[str, list[dict[str, Any]]], labels: dict[str, dict[str, Any]], repo_roots: dict[str, Path], top_k: int) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for strategy, preds in preds_by_strategy.items():
        metrics = r32.metrics_for(preds, labels, repo_roots, [int(p.get("latency_ms", 0)) for p in preds])
        metrics.update(p21e.contribution(preds, labels, top_k))
        results[strategy] = {"status": "ok", "metrics": metrics}
    baseline = results.get("rrf_baseline", {}).get("metrics", {})
    for strategy, payload in results.items():
        metrics = payload.get("metrics", {})
        payload["delta_vs_rrf"] = p21e.metric_delta(metrics, baseline) if strategy != "rrf_baseline" else {"baseline": True}
        delta = payload.get("delta_vs_rrf", {}) or {}
        is_dense_only = strategy.startswith("dense_") and strategy.endswith("_only")
        payload["diagnostic_control_only"] = is_dense_only
        payload["primary_promotion_eligible"] = False
        payload["blocked_as_primary"] = True
        payload["supporting_signal_useful_vs_rrf"] = bool(
            not is_dense_only
            and (delta.get("SpanF0.5") or 0) > 0
            and (delta.get("primary_false_positive_rate") or 0) <= 0
            and (delta.get("added_false_span") or 0) <= max(0, (delta.get("added_gold_span") or 0) * 2)
        )
    return results


def load_inputs(args: argparse.Namespace) -> tuple[tempfile.TemporaryDirectory[str] | None, list[dict[str, Any]], Path, dict[str, Path]]:
    return p21e.load_inputs(args)


def run(args: argparse.Namespace) -> dict[str, Any]:
    tmp_ctx, tasks, labels_path, repo_roots = load_inputs(args)
    try:
        anchor_preds = run_anchor_predictions(tasks, repo_roots, args.openlocus, args.top_k)
        dense_preds, dense_statuses, file_filter = dense_predictions(args, tasks, repo_roots)
        hybrid_preds = build_hybrids(tasks, anchor_preds, dense_preds, args.top_k, args.anchor_file_k)

        # SCORE phase starts only after anchors, dense candidates, and hybrids are materialized.
        labels = r32.normalize_labels(r32.load_jsonl(labels_path))
        results = score_predictions(hybrid_preds, labels, repo_roots, args.top_k)
        ok_dense_statuses = [name for name, payload in dense_statuses.items() if payload.get("status") == "ok"]
        ok = {k: v for k, v in results.items() if v.get("status") == "ok"}
        eligible_supporting = {
            k: v for k, v in ok.items()
            if k != "rrf_baseline" and not v.get("diagnostic_control_only")
        }
        best_span = max(eligible_supporting, key=lambda s: eligible_supporting[s]["metrics"].get("SpanF0.5", 0.0), default=None)
        best_file = max(eligible_supporting, key=lambda s: eligible_supporting[s]["metrics"].get("FileRecall@5", 0.0), default=None)
        helpful = [
            strategy for strategy, payload in eligible_supporting.items()
            if payload.get("supporting_signal_useful_vs_rrf")
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stage": "P21-G2E constrained/fused dense hybrid",
            "provider": args.provider,
            **r32.embedding_model_metadata(args.provider),
            "provider_status": "ok" if ok_dense_statuses else "unavailable",
            "remote_enabled": args.provider != "local_token_hash",
            "remote_file_filter_mode": file_filter.get("mode"),
            "remote_file_filter_applied": file_filter.get("applied"),
            "run_phase_public_only": True,
            "labels_loaded_after_run": True,
            "score_phase_labels_only": True,
            "candidate_not_fact": True,
            "not_promotion_evidence": True,
            "promotion_ready": False,
            "default_should_change": False,
            "dense_primary_allowed": False,
            "core_changes": False,
            "evidencecore_semantics_changed": False,
            "raw_text_stored": False,
            "raw_query_stored": False,
            "raw_snippets_committed": False,
            "private_labels_committed": False,
            "tasks_scored": len(tasks),
            "repo_count": len(repo_roots),
            "dense_strategies": p21e.strategy_list(args.dense_strategies),
            "dense_statuses": dense_statuses,
            "dense_strategy_success_count": len(ok_dense_statuses),
            "dense_strategy_successes": ok_dense_statuses,
            "strategy_results": results,
            "conclusion": {
                "best_span_strategy": best_span,
                "best_file_strategy": best_file,
                "helpful_vs_rrf_without_pfp_increase": helpful,
                "dense_should_remain_supporting_only": True,
                "promotion_ready": False,
                "default_should_change": False,
            },
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P21-G2E Constrained/Fused Dense Hybrid",
        "",
        "P21-G2E tests whether embedding context atoms become useful when constrained or fused with RRF/symbol/regex anchors. Dense remains candidate/supporting-only.",
        "",
        "## Safety",
        "",
        f"- provider: `{report.get('provider')}`",
        f"- embedding_model: `{report.get('embedding_model')}`",
        f"- remote_file_filter_applied: `{report.get('remote_file_filter_applied')}`",
        f"- raw_text_stored: `{report.get('raw_text_stored')}`",
        f"- raw_snippets_committed: `{report.get('raw_snippets_committed')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        "",
        "## Strategy Results",
        "",
        "| Strategy | FileRecall@5 | SpanF0.5 | PFP | Gold | False | ΔSpanF0.5 vs RRF | diagnostic_only | supporting_useful |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for strategy, payload in report.get("strategy_results", {}).items():
        metrics = payload.get("metrics") or {}
        delta = payload.get("delta_vs_rrf") or {}
        lines.append(
            f"| {strategy} | {metrics.get('FileRecall@5')} | {metrics.get('SpanF0.5')} | {metrics.get('primary_false_positive_rate')} | "
            f"{metrics.get('added_gold_span')} | {metrics.get('added_false_span')} | {delta.get('SpanF0.5')} | "
            f"{payload.get('diagnostic_control_only')} | {payload.get('supporting_signal_useful_vs_rrf')} |"
        )
    lines += [
        "",
        "## Conclusion",
        "",
        f"- best_span_strategy: `{report.get('conclusion', {}).get('best_span_strategy')}`",
        f"- best_file_strategy: `{report.get('conclusion', {}).get('best_file_strategy')}`",
        f"- helpful_vs_rrf_without_pfp_increase: `{report.get('conclusion', {}).get('helpful_vs_rrf_without_pfp_increase')}`",
        f"- dense_should_remain_supporting_only: `{report.get('conclusion', {}).get('dense_should_remain_supporting_only')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--dense-strategies", default=DEFAULT_DENSE_STRATEGIES)
    parser.add_argument("--provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-remote-data-level", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=80)
    parser.add_argument("--task-sample-mode", default="prefix", choices=["prefix", "round_robin_public_buckets"])
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-repo", type=int, default=400)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--anchor-file-k", type=int, default=5)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p21_g/dense_hybrid_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/p21-g-dense-hybrid.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    report = run(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
