#!/usr/bin/env python3
"""P21-G1E embedding context-atom screening harness.

P21-G studies context injection effects across models.  This harness covers the
embedding track: compare atom/view packs (path, signatures, matched lines, body
windows, comments, test/config/route cues) under the same tasks and repo caps.

RUN/SCORE separation is preserved: public tasks and source-derived candidate
views are embedded/ranked before private labels are loaded for metrics.  Rich
source snippets may be sent to the remote embedding provider only in explicit
public/opt-in runs, after ignore/secret filtering, but raw text is never written
to artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import r32_embedding_view_bakeoff as r32  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import r32_embedding_view_bakeoff as r32  # type: ignore


SCHEMA_VERSION = "p21-g1e-embedding-context-v1"

STRATEGY_VIEWS: dict[str, list[str]] = {
    "atom_path_symbol": ["path_plus_symbol"],
    "atom_signature": ["signature_only"],
    "atom_signature_doc": ["signature_plus_doc"],
    "atom_matched_lines": ["ast_header"],
    "atom_body_window": ["raw_code_trimmed"],
    "atom_comment_doc": ["comment_docstring"],
    "atom_test_intent": ["test_name_plus_assert_terms"],
    "atom_config_route": ["config_key_plus_context", "route_plus_handler_signature"],
    "pack1_metadata": ["path_plus_symbol", "signature_only"],
    "pack2_evidence_sketch": ["path_plus_symbol", "signature_only", "signature_plus_doc", "ast_header"],
    "pack3_local_code": ["path_plus_symbol", "signature_only", "signature_plus_doc", "ast_header", "raw_code_trimmed"],
    "pack5_contrastive": [
        "path_plus_symbol",
        "signature_only",
        "signature_plus_doc",
        "ast_header",
        "raw_code_trimmed",
        "comment_docstring",
        "test_name_plus_assert_terms",
        "config_key_plus_context",
        "route_plus_handler_signature",
    ],
}


@dataclass
class StrategyRun:
    predictions: list[dict[str, Any]]
    latencies: list[int]
    embed_status: dict[str, Any]
    query_remote_stats: dict[str, Any]
    records: list[r32.ViewRecord]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strategy_list(raw: str) -> list[str]:
    if raw.strip() == "all":
        return list(STRATEGY_VIEWS)
    out = [item.strip() for item in raw.split(",") if item.strip()]
    if "all" in out:
        return list(STRATEGY_VIEWS)
    unknown = [item for item in out if item not in STRATEGY_VIEWS]
    if unknown:
        raise SystemExit(f"unknown P21-G1E strategies: {unknown}")
    return out


def public_bucket_for_task(task: dict[str, Any]) -> str:
    bucket = task.get("task_bucket") or "unknown"
    tags = task.get("task_risk_tags") or []
    if isinstance(tags, list) and tags:
        return f"{bucket}:{tags[0]}"
    return str(bucket)


def sample_public_tasks(tasks: list[dict[str, Any]], max_tasks: int, mode: str) -> list[dict[str, Any]]:
    if mode == "prefix" or max_tasks >= len(tasks):
        return tasks[:max_tasks]
    if mode != "round_robin_public_buckets":
        raise SystemExit(f"unsupported task sample mode: {mode}")
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        by_bucket[public_bucket_for_task(task)].append(task)
    selected: list[dict[str, Any]] = []
    bucket_names = sorted(by_bucket)
    idx = 0
    while len(selected) < max_tasks and any(by_bucket.values()):
        bucket = bucket_names[idx % len(bucket_names)]
        if by_bucket[bucket]:
            selected.append(by_bucket[bucket].pop(0))
        idx += 1
    return selected


def load_inputs(args: argparse.Namespace) -> tuple[tempfile.TemporaryDirectory[str] | None, list[dict[str, Any]], Path, dict[str, Path]]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-p21-g1e-")
        repo_lock, tasks_path, labels_path, repo_roots = r32.make_self_test_inputs(Path(tmp_ctx.name))
    else:
        tmp_ctx = None
        repo_lock, tasks_path, labels_path = args.repo_lock, args.tasks, args.labels
        repo_roots = r32.load_repo_lock(repo_lock)
    tasks = r32.load_jsonl(tasks_path)
    issues = r32.validate_public_tasks(tasks)
    if issues:
        raise SystemExit("public task validation failed: " + "; ".join(issues[:5]))
    repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
    tasks = [task for task in tasks if task["repo_id"] in repo_roots]
    tasks = sample_public_tasks(tasks, args.max_tasks, getattr(args, "task_sample_mode", "prefix"))
    return tmp_ctx, tasks, labels_path, repo_roots


def build_all_views(args: argparse.Namespace, repo_roots: dict[str, Path]) -> dict[str, dict[str, list[r32.ViewRecord]]]:
    by_view: dict[str, dict[str, list[r32.ViewRecord]]] = {view: {} for views in STRATEGY_VIEWS.values() for view in views}
    for repo_id, root in repo_roots.items():
        scan_map = r32.run_scan(args.openlocus, root)
        for file_path in r32.iter_source_files(root, args.max_files_per_repo):
            rel = str(file_path.relative_to(root)).replace(os.sep, "/")
            built = r32.build_views_for_file(repo_id, root, file_path, scan_map.get(rel))
            for view in by_view:
                by_view[view].setdefault(repo_id, []).extend(built.get(view, []))
    return by_view


def git_tracked_files(repo_root: Path) -> set[str] | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            text=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return {part.decode("utf-8", errors="ignore").replace(os.sep, "/") for part in completed.stdout.split(b"\0") if part}


def remote_file_filter(repo_roots: dict[str, Path], *, allow_self_test: bool) -> dict[str, Any]:
    if allow_self_test:
        return {
            "mode": "self_test_generated_public",
            "applied": True,
            "tracked_files_by_repo": {},
            "reason": "generated self-test repo; no private/ignored inputs",
        }
    tracked_by_repo: dict[str, set[str]] = {}
    missing: list[str] = []
    for repo_id, root in repo_roots.items():
        tracked = git_tracked_files(root)
        if tracked is None:
            missing.append(repo_id)
        else:
            tracked_by_repo[repo_id] = tracked
    return {
        "mode": "git_ls_files",
        "applied": not missing,
        "tracked_files_by_repo": tracked_by_repo,
        "missing_repo_ids": missing,
    }


def records_for_strategy(
    by_view: dict[str, dict[str, list[r32.ViewRecord]]],
    strategy: str,
    repo_roots: dict[str, Path],
    max_records_per_repo: int,
) -> list[r32.ViewRecord]:
    records: list[r32.ViewRecord] = []
    for repo_id in sorted(repo_roots):
        repo_records: list[r32.ViewRecord] = []
        for view in STRATEGY_VIEWS[strategy]:
            repo_records.extend(by_view.get(view, {}).get(repo_id, []))
        repo_records.sort(key=lambda rec: (rec.path, rec.start_line, rec.end_line, rec.view_kind, rec.text_sha))
        records.extend(repo_records[:max_records_per_repo])
    return records


def p21_embed_records(
    records: list[r32.ViewRecord],
    provider: str,
    allow_remote: bool,
    max_remote_data_level: int,
    file_filter: dict[str, Any],
) -> dict[str, Any]:
    started = time.time()
    total_input_chars = sum(len(rec.text) for rec in records)
    if provider == "local_token_hash":
        for rec in records:
            rec.vector = r32.token_hash_embedding(rec.text)
        return {
            "provider": provider,
            "status": "ok",
            "remote_calls": 0,
            "remote_requests": 0,
            "remote_texts": 0,
            "input_chars": total_input_chars,
            "latency_ms": int((time.time() - started) * 1000),
        }
    if provider != "openai-compatible":
        return {"provider": provider, "status": "unavailable", "reason": "unknown provider", "remote_calls": 0}
    if not allow_remote or os.environ.get("OPENLOCUS_ALLOW_REMOTE") != "1":
        return {"provider": provider, "status": "unavailable", "reason": "requires --allow-remote and OPENLOCUS_ALLOW_REMOTE=1", "remote_calls": 0}
    if not file_filter.get("applied"):
        return {
            "provider": provider,
            "status": "unavailable",
            "reason": "remote rich context requires gitignore/tracked-file filtering",
            "missing_repo_ids": file_filter.get("missing_repo_ids", []),
            "remote_calls": 0,
        }
    tracked_by_repo: dict[str, set[str]] = file_filter.get("tracked_files_by_repo", {})
    if tracked_by_repo:
        blocked_paths = [f"{rec.repo_id}:{rec.path}" for rec in records if rec.path not in tracked_by_repo.get(rec.repo_id, set())]
        if blocked_paths:
            return {
                "provider": provider,
                "status": "unavailable",
                "reason": "remote record path is not git-tracked",
                "blocked_path_count": len(blocked_paths),
                "blocked_path_examples": blocked_paths[:5],
                "remote_calls": 0,
            }
    unsafe_levels = sorted({rec.data_level for rec in records if rec.data_level > max_remote_data_level})
    if unsafe_levels:
        return {"provider": provider, "status": "unavailable", "reason": "record data_level exceeds max_remote_data_level", "blocked_data_levels": unsafe_levels, "remote_calls": 0}
    if any(r32.text_has_secret(rec.text) for rec in records):
        return {"provider": provider, "status": "unavailable", "reason": "record text blocked by secret scan", "remote_calls": 0}
    try:
        vectors, stats = r32.remote_embed_detailed([rec.text for rec in records])
    except r32.RemoteEmbeddingProviderError as exc:
        return {"provider": provider, "status": "unavailable", "reason": "remote embedding provider unavailable_or_failed", "remote_calls": 0, **exc.as_public_dict()}
    except Exception as exc:
        return {"provider": provider, "status": "unavailable", "reason": "remote embedding provider unavailable_or_failed", "remote_calls": 0, "error_type": type(exc).__name__}
    for rec, vec in zip(records, vectors):
        rec.vector = vec
    return {
        "provider": provider,
        "status": "ok",
        "remote_calls": len(records),
        "input_chars": total_input_chars,
        "latency_ms": int((time.time() - started) * 1000),
        **stats,
    }


def rank_strategy(tasks: list[dict[str, Any]], records: list[r32.ViewRecord], provider: str, top_k: int) -> tuple[list[dict[str, Any]], list[int], dict[str, Any]]:
    by_repo: dict[str, list[r32.ViewRecord]] = {}
    for rec in records:
        by_repo.setdefault(rec.repo_id, []).append(rec)

    predictions: list[dict[str, Any]] = []
    latencies: list[int] = []
    query_vectors: dict[str, list[float]] = {}
    query_remote_stats: dict[str, Any] = {"remote_calls": 0, "remote_requests": 0, "remote_texts": 0, "query_embedding_complete": True}

    if provider != "local_token_hash":
        query_texts: list[str] = []
        query_keys: list[str] = []
        for task in tasks:
            tid = str(task.get("test_id") or task.get("task_id") or "")
            query = str(task.get("query", ""))
            if not tid or r32.text_has_secret(query):
                query_remote_stats = {
                    "remote_calls": 0,
                    "remote_requests": 0,
                    "remote_texts": 0,
                    "query_embedding_complete": False,
                    "reason_code": "query_secret_or_missing_task_id",
                }
                break
            query_keys.append(tid)
            query_texts.append(f"query {query}")
        if query_texts and query_remote_stats.get("query_embedding_complete"):
            try:
                vectors, stats = r32.remote_embed_detailed(query_texts)
                query_vectors = dict(zip(query_keys, vectors))
                query_remote_stats = {
                    "remote_calls": len(query_texts),
                    "remote_requests": stats.get("remote_requests", 0),
                    "remote_texts": stats.get("remote_texts", len(query_texts)),
                    "batch_size": stats.get("batch_size"),
                    "query_embedding_complete": len(vectors) == len(tasks),
                }
            except r32.RemoteEmbeddingProviderError as exc:
                query_remote_stats = {"remote_calls": 0, "remote_requests": 0, "remote_texts": 0, "query_embedding_complete": False, **exc.as_public_dict()}
            except Exception as exc:
                query_remote_stats = {"remote_calls": 0, "remote_requests": 0, "remote_texts": 0, "query_embedding_complete": False, "error_type": type(exc).__name__}

    for task in tasks:
        started = time.time()
        tid = str(task.get("test_id") or task.get("task_id"))
        query = task["query"]
        repo_id = task["repo_id"]
        if provider == "local_token_hash":
            query_vec = r32.token_hash_embedding(f"query {query}")
        else:
            query_vec = query_vectors.get(tid, [])
        unique: dict[tuple[Any, ...], tuple[float, r32.ViewRecord, set[str]]] = {}
        if query_vec:
            for rec in by_repo.get(repo_id, []):
                if not rec.vector:
                    continue
                score = r32.cosine(query_vec, rec.vector or [])
                if score <= 0 and provider == "local_token_hash":
                    continue
                key = (rec.path, rec.start_line, rec.end_line, rec.content_sha)
                prior = unique.get(key)
                if prior is None or score > prior[0]:
                    views = set(prior[2]) if prior else set()
                    views.add(rec.view_kind)
                    unique[key] = (score, rec, views)
                else:
                    prior[2].add(rec.view_kind)
        ranked = sorted(unique.values(), key=lambda item: (item[0], item[1].path, -item[1].start_line), reverse=True)
        evidence: list[dict[str, Any]] = []
        for score, rec, source_views in ranked[:top_k]:
            evidence.append({
                "path": rec.path,
                "start_line": rec.start_line,
                "end_line": rec.end_line,
                "content_sha": rec.content_sha,
                "score": round(float(score), 6),
                "why": ["P21-G1E unique dense candidate", "candidate_not_fact"],
                "channels": ["dense"],
                "meta": {
                    "view_kind": rec.view_kind,
                    "source_view_kinds": sorted(source_views),
                    "provider": provider,
                    "data_level": rec.data_level,
                    "not_evidence_until_materialized": True,
                },
            })
        latency_ms = int((time.time() - started) * 1000)
        latencies.append(latency_ms)
        predictions.append({
            "task_id": tid,
            "repo_id": repo_id,
            "strategy": f"p21_g1e_dense_{provider}",
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "evidence": evidence,
            "latency_ms": latency_ms,
            "returncode": 0,
        })
    return predictions, latencies, query_remote_stats


def evidence_overlaps(ev: dict[str, Any], span: dict[str, Any]) -> bool:
    return (
        ev.get("path") == span.get("path")
        and int(ev.get("end_line", 0)) >= int(span.get("start_line", 0))
        and int(ev.get("start_line", 0)) <= int(span.get("end_line", 0))
    )


def contribution(predictions: list[dict[str, Any]], labels: dict[str, dict[str, Any]], top_k: int) -> dict[str, Any]:
    added_gold = 0
    added_false = 0
    file_right_span_wrong = 0
    file_wrong = 0
    candidate_pool_miss = 0
    source_test_confusion = 0
    docs_source_confusion = 0
    frontend_backend_confusion = 0
    positives = 0
    for pred in predictions:
        label = labels.get(pred["task_id"], {})
        gold_spans = label.get("gold_spans") or []
        evidence = pred.get("evidence", [])[:top_k]
        if gold_spans:
            positives += 1
            gold_paths = {span["path"] for span in gold_spans}
            ev_paths = {ev.get("path") for ev in evidence}
            if not evidence:
                candidate_pool_miss += 1
            elif not (gold_paths & ev_paths):
                file_wrong += 1
            elif not any(evidence_overlaps(ev, span) for ev in evidence for span in gold_spans):
                file_right_span_wrong += 1
            top_path = str(evidence[0].get("path", "")) if evidence else ""
            gold_path_joined = " ".join(sorted(gold_paths))
            if top_path:
                if ("test" in top_path.lower()) != ("test" in gold_path_joined.lower()):
                    source_test_confusion += 1
                if any(tok in top_path.lower() for tok in ["doc", "readme", "guide"]):
                    docs_source_confusion += 1
                if ("frontend" in top_path.lower() or "/web/" in top_path.lower()) != ("frontend" in gold_path_joined.lower() or "/web/" in gold_path_joined.lower()):
                    frontend_backend_confusion += 1
        for ev in evidence:
            if any(evidence_overlaps(ev, span) for span in gold_spans):
                added_gold += 1
            else:
                added_false += 1
    false_to_gold_ratio: float | None
    if added_gold:
        false_to_gold_ratio = added_false / added_gold
    elif added_false:
        false_to_gold_ratio = None
    else:
        false_to_gold_ratio = 0.0
    return {
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "false_to_gold_ratio": false_to_gold_ratio,
        "candidate_pool_miss_rate": candidate_pool_miss / positives if positives else 0.0,
        "file_wrong_rate": file_wrong / positives if positives else 0.0,
        "file_right_span_wrong_rate": file_right_span_wrong / positives if positives else 0.0,
        "source_test_confusion_rate": source_test_confusion / positives if positives else 0.0,
        "docs_source_confusion_rate": docs_source_confusion / positives if positives else 0.0,
        "frontend_backend_confusion_rate": frontend_backend_confusion / positives if positives else 0.0,
    }


def metric_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    keys = ["FileRecall@1", "FileRecall@5", "MRR", "SpanF0.5", "primary_false_positive_rate", "token_waste", "added_gold_span", "added_false_span"]
    out: dict[str, Any] = {}
    for key in keys:
        cv = current.get(key)
        bv = baseline.get(key)
        out[key] = (cv - bv) if isinstance(cv, (int, float)) and isinstance(bv, (int, float)) and math.isfinite(float(cv)) and math.isfinite(float(bv)) else None
    return out


def summarize_effects(results: dict[str, Any], baseline_strategy: str) -> dict[str, Any]:
    baseline = (results.get(baseline_strategy) or {}).get("metrics") or {}
    summary: dict[str, Any] = {}
    for strategy, payload in results.items():
        metrics = payload.get("metrics") or {}
        if payload.get("status") != "ok" or not metrics:
            continue
        delta = metric_delta(metrics, baseline) if strategy != baseline_strategy else {"baseline": True}
        summary[strategy] = {
            "status": "baseline" if strategy == baseline_strategy else "compared",
            "delta_vs_baseline": delta,
            "blocked_as_primary": bool(metrics.get("primary_false_positive_rate", 0.0) > baseline.get("primary_false_positive_rate", 0.0) or metrics.get("added_false_span", 0) >= max(1, metrics.get("added_gold_span", 0))),
        }
    return summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    provider = args.provider
    if provider != "local_token_hash" and not args.allow_remote:
        return {
            "schema_version": SCHEMA_VERSION,
            "provider": provider,
            **r32.embedding_model_metadata(provider),
            "provider_status": "unavailable",
            "unavailable_reason": "requires --allow-remote and OPENLOCUS_ALLOW_REMOTE=1",
            "promotion_ready": False,
            "default_should_change": False,
        }

    tmp_ctx, tasks, labels_path, repo_roots = load_inputs(args)
    try:
        strategies = strategy_list(args.strategies)
        by_view = build_all_views(args, repo_roots)
        file_filter = remote_file_filter(repo_roots, allow_self_test=bool(args.self_test))

        # RUN phase: labels are not loaded until every strategy has ranked public tasks.
        run_outputs: dict[str, StrategyRun] = {}
        for strategy in strategies:
            records = records_for_strategy(by_view, strategy, repo_roots, args.max_records_per_repo)
            embed_status = p21_embed_records(records, provider, args.allow_remote, args.max_remote_data_level, file_filter)
            if embed_status.get("status") != "ok":
                run_outputs[strategy] = StrategyRun([], [], embed_status, {}, records)
                continue
            preds, latencies, query_remote_stats = rank_strategy(tasks, records, provider, args.top_k)
            if provider != "local_token_hash" and (
                not query_remote_stats.get("query_embedding_complete", False)
                or query_remote_stats.get("reason_code")
                or query_remote_stats.get("error_type")
                or int(query_remote_stats.get("remote_calls", 0)) < len(tasks)
            ):
                run_outputs[strategy] = StrategyRun(
                    [],
                    [],
                    {"status": "unavailable", "reason": "remote query embedding incomplete_or_failed", **query_remote_stats},
                    query_remote_stats,
                    records,
                )
                continue
            for pred in preds:
                pred["strategy"] = f"p21_g1e_{strategy}"
                for ev in pred.get("evidence", []):
                    ev.setdefault("meta", {})["p21_strategy"] = strategy
                    ev.setdefault("meta", {})["candidate_not_fact"] = True
                    ev.setdefault("meta", {})["not_evidence_until_materialized"] = True
            run_outputs[strategy] = StrategyRun(preds, latencies, embed_status, query_remote_stats, records)

        labels_loaded_after_run = False
        labels = r32.normalize_labels(r32.load_jsonl(labels_path))
        labels_loaded_after_run = True

        results: dict[str, Any] = {}
        for strategy, output in run_outputs.items():
            if output.embed_status.get("status") != "ok":
                results[strategy] = {"status": "unavailable", "reason": output.embed_status.get("reason"), "metrics": None}
                continue
            metrics = r32.metrics_for(output.predictions, labels, repo_roots, output.latencies)
            metrics.update(contribution(output.predictions, labels, args.top_k))
            metrics["remote_calls"] = output.embed_status.get("remote_calls", 0) + output.query_remote_stats.get("remote_calls", 0)
            metrics["remote_requests"] = output.embed_status.get("remote_requests", 0) + output.query_remote_stats.get("remote_requests", 0)
            metrics["remote_texts"] = output.embed_status.get("remote_texts", 0) + output.query_remote_stats.get("remote_texts", 0)
            metrics["input_chars"] = output.embed_status.get("input_chars", 0)
            metrics["index_build_time_ms"] = output.embed_status.get("latency_ms", 0)
            metrics["vector_store_size"] = len(output.records)
            unique_record_keys = {(rec.repo_id, rec.path, rec.start_line, rec.end_line, rec.content_sha) for rec in output.records}
            metrics["unique_candidate_records"] = len(unique_record_keys)
            metrics["embedding_cost_estimate"] = 0.0 if provider == "local_token_hash" else None
            results[strategy] = {
                "status": "ok",
                "views": STRATEGY_VIEWS[strategy],
                "records": len(output.records),
                "metrics": metrics,
            }

        baseline_strategy = args.baseline_strategy
        if baseline_strategy not in results or results.get(baseline_strategy, {}).get("status") != "ok":
            baseline_strategy = next((s for s, v in results.items() if v.get("status") == "ok"), args.baseline_strategy)
        effects = summarize_effects(results, baseline_strategy)
        ok_results = {s: v for s, v in results.items() if v.get("status") == "ok" and v.get("metrics")}
        best_span = max(ok_results, key=lambda s: ok_results[s]["metrics"].get("SpanF0.5", 0.0), default=None)
        best_file = max(ok_results, key=lambda s: ok_results[s]["metrics"].get("FileRecall@5", 0.0), default=None)
        blocked_primary = [s for s, v in ok_results.items() if effects.get(s, {}).get("blocked_as_primary")]

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stage": "P21-G1E embedding context atom screening",
            "provider": provider,
            **r32.embedding_model_metadata(provider),
            "provider_status": "ok" if ok_results else "unavailable",
            "provider_role": "candidate/supporting-only",
            "remote_enabled": provider != "local_token_hash",
            "rich_context_remote_allowed": bool(provider != "local_token_hash" and args.max_remote_data_level >= 1),
            "max_remote_data_level": args.max_remote_data_level,
            "run_phase_public_only": True,
            "labels_loaded_after_run": labels_loaded_after_run,
            "score_phase_labels_only": True,
            "promotion_ready": False,
            "default_should_change": False,
            "candidate_not_fact": True,
            "not_promotion_evidence": True,
            "core_changes": False,
            "evidencecore_semantics_changed": False,
            "raw_text_stored": False,
            "raw_query_stored": False,
            "raw_prompt_or_response_stored": False,
            "raw_snippets_committed": False,
            "private_labels_committed": False,
            "remote_file_filter_mode": file_filter.get("mode"),
            "remote_file_filter_applied": file_filter.get("applied"),
            "tasks_scored": len(tasks),
            "repo_count": len(repo_roots),
            "strategies": strategies,
            "baseline_strategy": baseline_strategy,
            "strategy_results": results,
            "treatment_effects_vs_baseline": effects,
            "conclusion": {
                "best_span_strategy": best_span,
                "best_file_strategy": best_file,
                "blocked_primary_strategies": blocked_primary,
                "dense_should_remain_supporting_only": True,
                "promotion_ready": False,
                "note": "local_token_hash is deterministic smoke, not semantic quality evidence" if provider == "local_token_hash" else "real embedding context atoms remain candidate/supporting-only",
            },
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P21-G1E Embedding Context Atom Screening",
        "",
        "P21-G1E tests embedding context atoms/packs as candidate/supporting signals. It does not change EvidenceCore and does not promote dense results to primary/default.",
        "",
        "## Safety / Policy",
        "",
        f"- provider: `{report.get('provider')}`",
        f"- embedding_model: `{report.get('embedding_model')}`",
        f"- rich_context_remote_allowed: `{report.get('rich_context_remote_allowed')}`",
        f"- run_phase_public_only: `{report.get('run_phase_public_only')}`",
        f"- labels_loaded_after_run: `{report.get('labels_loaded_after_run')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- raw_text_stored: `{report.get('raw_text_stored')}`",
        f"- raw_snippets_committed: `{report.get('raw_snippets_committed')}`",
        f"- remote_file_filter_mode: `{report.get('remote_file_filter_mode')}`",
        f"- remote_file_filter_applied: `{report.get('remote_file_filter_applied')}`",
        "",
        "## Strategy Results",
        "",
        "| Strategy | Records | FileRecall@5 | SpanF0.5 | PFP | added_gold | added_false | false:gold | citation | remote calls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, payload in report.get("strategy_results", {}).items():
        metrics = payload.get("metrics") or {}
        lines.append(
            f"| {strategy} | {payload.get('records', 0)} | {metrics.get('FileRecall@5')} | {metrics.get('SpanF0.5')} | "
            f"{metrics.get('primary_false_positive_rate')} | {metrics.get('added_gold_span')} | {metrics.get('added_false_span')} | "
            f"{metrics.get('false_to_gold_ratio')} | {metrics.get('citation_validity')} | {metrics.get('remote_calls')} |"
        )
    lines.extend([
        "",
        "## Conclusion",
        "",
        f"- best_span_strategy: `{report.get('conclusion', {}).get('best_span_strategy')}`",
        f"- best_file_strategy: `{report.get('conclusion', {}).get('best_file_strategy')}`",
        f"- dense_should_remain_supporting_only: `{report.get('conclusion', {}).get('dense_should_remain_supporting_only')}`",
        f"- blocked_primary_strategies: `{report.get('conclusion', {}).get('blocked_primary_strategies')}`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--strategies", default="atom_path_symbol,atom_signature,atom_matched_lines,atom_body_window,pack1_metadata,pack2_evidence_sketch,pack3_local_code,pack5_contrastive")
    parser.add_argument("--baseline-strategy", default="atom_path_symbol")
    parser.add_argument("--provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-remote-data-level", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=120)
    parser.add_argument("--task-sample-mode", default="prefix", choices=["prefix", "round_robin_public_buckets"])
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-repo", type=int, default=800)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p21_g/embedding_context_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/p21-g-embedding-context.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()

    report = run(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
