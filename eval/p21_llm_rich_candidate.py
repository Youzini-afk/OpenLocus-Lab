#!/usr/bin/env python3
"""P21-G3L rich-context LLM candidate pilot.

This harness gives an LLM constrained candidate packs produced from local
anchors plus P21-G2E dense-hybrid strategies.  The model may filter, abstain,
or narrow spans, but its output is never Evidence, never a label, and never a
promotion verdict.  Artifacts store decisions, hashes, line ranges, and
telemetry; raw snippets/prompts/responses are not persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    import p20_llm_large_scale as p20  # type: ignore
    import p21_dense_hybrid as p21d  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import p20_llm_large_scale as p20  # type: ignore
    import p21_dense_hybrid as p21d  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore


SCHEMA_VERSION = "p21-g3l-llm-rich-candidate-v1"
PROMPT_VERSION = "p21-g3l-rich-candidate-v1"
DEFAULT_CANDIDATE_STRATEGY = "dense_atom_signature_rrf_file_constrained"
DECISIONS = {"primary", "supporting", "reject"}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_line_window(repo_root: Path, ev: dict[str, Any], window: int) -> tuple[str, str | None, int, int]:
    path = str(ev.get("path") or "")
    if not path or ".." in Path(path).parts or Path(path).is_absolute():
        return "", "invalid_path", 0, 0
    full = repo_root / path
    try:
        resolved_root = repo_root.resolve()
        resolved_full = full.resolve()
        if not resolved_full.is_relative_to(resolved_root):
            return "", "path_outside_repo", 0, 0
    except OSError:
        return "", "resolve_error", 0, 0
    if not full.exists() or not full.is_file() or full.is_symlink():
        return "", "missing_file", 0, 0
    if r32.text_has_secret(path):
        return "", "secret_like_path", 0, 0
    try:
        lines = full.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return "", "read_error", 0, 0
    start = max(1, int(ev.get("start_line") or 1) - window)
    end = min(len(lines), int(ev.get("end_line") or start) + window)
    snippet_lines = []
    for idx in range(start, end + 1):
        line = lines[idx - 1]
        if r32.text_has_secret(line):
            return "", "secret_like_line", 0, 0
        snippet_lines.append(f"{idx}: {line}")
    return "\n".join(snippet_lines), None, start, end


def build_candidate_predictions(args: argparse.Namespace, tasks: list[dict[str, Any]], repo_roots: dict[str, Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dense_args = SimpleNamespace(
        provider=args.embedding_provider,
        allow_remote=args.allow_remote_embedding,
        max_remote_data_level=args.max_remote_data_level,
        dense_strategies=args.dense_strategies,
        max_records_per_repo=args.max_records_per_repo,
        max_files_per_repo=args.max_files_per_repo,
        top_k=args.top_k,
        anchor_file_k=args.anchor_file_k,
        openlocus=args.openlocus,
        self_test=args.self_test,
    )
    anchor = p21d.run_anchor_predictions(tasks, repo_roots, args.openlocus, args.top_k)
    dense, dense_statuses, file_filter = p21d.dense_predictions(dense_args, tasks, repo_roots)
    hybrids = p21d.build_hybrids(tasks, anchor, dense, args.top_k, args.anchor_file_k)
    strategy = args.candidate_strategy
    if strategy not in hybrids:
        return [], {
            "requested_candidate_strategy": args.candidate_strategy,
            "actual_candidate_strategy": None,
            "candidate_strategy_available": False,
            "unavailable_reason": "requested_candidate_strategy_unavailable",
            "dense_statuses": dense_statuses,
            "remote_file_filter_mode": file_filter.get("mode"),
            "remote_file_filter_applied": file_filter.get("applied"),
        }
    return hybrids.get(strategy, []), {
        "requested_candidate_strategy": args.candidate_strategy,
        "actual_candidate_strategy": strategy,
        "candidate_strategy_available": True,
        "unavailable_reason": None,
        "dense_statuses": dense_statuses,
        "remote_file_filter_mode": file_filter.get("mode"),
        "remote_file_filter_applied": file_filter.get("applied"),
    }


def pack_candidates(
    task: dict[str, Any],
    prediction: dict[str, Any],
    repo_roots: dict[str, Path],
    *,
    max_candidates: int,
    window: int,
    allow_self_test: bool,
    require_filter_applied: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    repo_id = task["repo_id"]
    repo_root = repo_roots[repo_id]
    file_filter = p21e.remote_file_filter({repo_id: repo_root}, allow_self_test=allow_self_test)
    if require_filter_applied and not file_filter.get("applied"):
        return [], [], {"skipped": {"remote_file_filter_not_applied": 1}, "remote_file_filter_applied": False, "packed_count": 0}
    tracked_paths = (file_filter.get("tracked_files_by_repo") or {}).get(repo_id)
    packed: list[dict[str, Any]] = []
    candidate_meta: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    for idx, ev in enumerate(prediction.get("evidence", [])[:max_candidates], start=1):
        path = str(ev.get("path") or "")
        if file_filter.get("applied") and tracked_paths is not None and path not in tracked_paths:
            skipped["not_git_tracked_or_disallowed"] = skipped.get("not_git_tracked_or_disallowed", 0) + 1
            continue
        snippet, reason, snippet_start, snippet_end = safe_line_window(repo_root, ev, window)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        cid = f"C{len(packed)+1}"
        packed.append({
            "candidate_id": cid,
            "path": path,
            "start_line": int(ev.get("start_line") or 1),
            "end_line": int(ev.get("end_line") or ev.get("start_line") or 1),
            "allowed_start_line": snippet_start,
            "allowed_end_line": snippet_end,
            "score": ev.get("score"),
            "channels": ev.get("channels", []),
            "source_views": (ev.get("meta") or {}).get("source_view_kinds", []),
            "snippet": snippet,
        })
        candidate_meta.append({
            "candidate_id": cid,
            "path": path,
            "start_line": int(ev.get("start_line") or 1),
            "end_line": int(ev.get("end_line") or ev.get("start_line") or 1),
            "allowed_start_line": snippet_start,
            "allowed_end_line": snippet_end,
            "content_sha": ev.get("content_sha"),
            "snippet_sha": sha_text(snippet),
            "channels": ev.get("channels", []),
            "source_views": (ev.get("meta") or {}).get("source_view_kinds", []),
        })
        if len(packed) >= max_candidates:
            break
    return packed, candidate_meta, {"skipped": skipped, "remote_file_filter_applied": file_filter.get("applied"), "packed_count": len(packed)}


def local_decision(task: dict[str, Any], packed: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    noisy = p20.is_negative_noise_query(task.get("query", "")) or p20.is_vague_multi_word_query(task.get("query", ""))
    if not packed or noisy:
        return {"not_evidence": True, "candidate_not_fact": True, "answerable": False, "items": []}, {"call_succeeded": True, "offline_deterministic": True, "latency_ms": 0}
    first = packed[0]
    return {
        "not_evidence": True,
        "candidate_not_fact": True,
        "answerable": True,
        "items": [{
            "candidate_id": first["candidate_id"],
            "decision": "primary",
            "start_line": first["start_line"],
            "end_line": first["end_line"],
            "reason_code": "offline_top_candidate",
        }],
    }, {"call_succeeded": True, "offline_deterministic": True, "latency_ms": 0}


def remote_decision(task: dict[str, Any], packed: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id = os.environ.get("OPENLOCUS_LLM_MODEL", "unknown")
    candidates_text = []
    for cand in packed:
        candidates_text.append(
            f"candidate_id={cand['candidate_id']} path={cand['path']} lines={cand['start_line']}-{cand['end_line']} "
            f"channels={cand.get('channels')} source_views={cand.get('source_views')}\n{cand['snippet']}"
        )
    user_content = (
        f"repo_id={task.get('repo_id')} task_id={task.get('test_id') or task.get('task_id')}\n"
        f"query={task.get('query')!r}\n\n"
        "Candidates are source snippets from current public/opt-in code after filtering. "
        "Choose only from candidate_id values shown. Do not invent paths or identifiers.\n\n"
        + "\n\n---\n\n".join(candidates_text)
        + "\n\nRespond as JSON: {\"not_evidence\": true, \"candidate_not_fact\": true, "
        "\"answerable\": true|false, \"items\": [{\"candidate_id\": \"C1\", \"decision\": \"primary|supporting|reject\", "
        "\"start_line\": 1, \"end_line\": 2, \"reason_code\": \"short_token\"}]}"
    )
    messages = [
        {"role": "system", "content": "You are a code retrieval candidate filter. Output JSON only. Your output is not Evidence, not a label, and not a promotion verdict. If candidates do not support the query, set answerable=false and items=[]."},
        {"role": "user", "content": user_content},
    ]
    t0 = time.time()
    try:
        parsed = p20._post_chat_completion(messages, temperature=0.0)  # type: ignore[attr-defined]
    except p20.RemoteLLMProviderError as exc:
        return None, {"call_succeeded": False, **exc.as_public_dict(), "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "model_id": model_id}
    except Exception as exc:
        return None, {"call_succeeded": False, "error_type": type(exc).__name__, "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "model_id": model_id}
    return parsed, {"call_succeeded": True, "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "output_chars": len(json.dumps(parsed)), "model_id": model_id}


def validate_decision(parsed: dict[str, Any] | None, packed: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(parsed, dict):
        return {"not_evidence": True, "candidate_not_fact": True, "answerable": False, "items": []}, {"schema_valid": False, "schema_error": "top_level_not_object"}
    if parsed.get("not_evidence") is not True or parsed.get("candidate_not_fact") is not True:
        return {"not_evidence": True, "candidate_not_fact": True, "answerable": False, "items": []}, {"schema_valid": False, "schema_error": "missing_not_evidence_or_candidate_not_fact"}
    id_map = {c["candidate_id"]: c for c in packed}
    items = parsed.get("items")
    if not isinstance(items, list):
        return {"not_evidence": True, "candidate_not_fact": True, "answerable": False, "items": []}, {"schema_valid": False, "schema_error": "items_not_array"}
    valid_items = []
    rejected = 0
    for item in items[: len(packed)]:
        if not isinstance(item, dict):
            rejected += 1
            continue
        cid = str(item.get("candidate_id") or "")
        cand = id_map.get(cid)
        decision = str(item.get("decision") or "")
        if not cand or decision not in DECISIONS:
            rejected += 1
            continue
        try:
            start = int(item.get("start_line") or cand["start_line"])
            end = int(item.get("end_line") or start)
        except (TypeError, ValueError):
            rejected += 1
            continue
        if start < 1 or end < start:
            rejected += 1
            continue
        if start < int(cand.get("allowed_start_line", cand["start_line"])) or end > int(cand.get("allowed_end_line", cand["end_line"])):
            rejected += 1
            continue
        valid_items.append({
            "candidate_id": cid,
            "decision": decision,
            "start_line": start,
            "end_line": end,
            "reason_code": p20.safe_reason_token(item.get("reason_code") or "unspecified"),
        })
    return {
        "not_evidence": True,
        "candidate_not_fact": True,
        "answerable": bool(parsed.get("answerable")) and any(i["decision"] in {"primary", "supporting"} for i in valid_items),
        "items": valid_items,
    }, {"schema_valid": True, "schema_rejected_items": rejected}


def decisions_to_predictions(task: dict[str, Any], candidate_meta: list[dict[str, Any]], decision: dict[str, Any], baseline_pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    meta_by_id = {m["candidate_id"]: m for m in candidate_meta}
    base = {
        "task_id": task.get("test_id") or task.get("task_id"),
        "repo_id": task["repo_id"],
        "query_sha": sha_text(task.get("query", "")),
        "latency_ms": 0,
        "returncode": 0,
    }
    filter_evidence: list[dict[str, Any]] = []
    narrow_evidence: list[dict[str, Any]] = []
    for item in decision.get("items", []):
        if item.get("decision") == "reject":
            continue
        meta = meta_by_id.get(item.get("candidate_id"))
        if not meta:
            continue
        original = {
            "path": meta["path"],
            "start_line": meta["start_line"],
            "end_line": meta["end_line"],
            "content_sha": meta.get("content_sha"),
            "score": 1.0 if item.get("decision") == "primary" else 0.5,
            "why": ["P21-G3L llm_filtered_candidate", item.get("reason_code", "unspecified")],
            "channels": ["llm_filter"],
            "meta": {"candidate_not_fact": True, "not_evidence_until_materialized": True, "candidate_id": item.get("candidate_id")},
        }
        narrowed = dict(original)
        narrowed["start_line"] = item["start_line"]
        narrowed["end_line"] = item["end_line"]
        narrowed["why"] = ["P21-G3L llm_span_narrow_candidate", item.get("reason_code", "unspecified")]
        narrowed["channels"] = ["llm_span_narrow"]
        filter_evidence.append(original)
        narrow_evidence.append(narrowed)
    return {
        "candidate_baseline": {**base, "strategy": "candidate_baseline", "evidence": baseline_pred.get("evidence", [])},
        "llm_filter": {**base, "strategy": "llm_filter", "evidence": filter_evidence},
        "llm_span_narrow": {**base, "strategy": "llm_span_narrow", "evidence": narrow_evidence},
        "llm_abstain_filter": {**base, "strategy": "llm_abstain_filter", "evidence": [] if not decision.get("answerable") else filter_evidence},
    }


def metric_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return p21e.metric_delta(current, baseline)


def run(args: argparse.Namespace) -> dict[str, Any]:
    tmp_ctx, tasks, labels_path, repo_roots = p21e.load_inputs(args)
    try:
        candidate_preds, candidate_info = build_candidate_predictions(args, tasks, repo_roots)
        cand_by_task = {str(p.get("task_id")): p for p in candidate_preds}
        remote_requested = args.llm_provider == "openai-compatible" and bool(args.allow_remote_llm)
        remote_enabled, remote_reason = p20.remote_llm_enabled(SimpleNamespace(provider=args.llm_provider, allow_remote=args.allow_remote_llm))
        if not candidate_info.get("candidate_strategy_available"):
            remote_enabled = False
            remote_reason = candidate_info.get("unavailable_reason") or "candidate_strategy_unavailable"
        predictions_by_strategy: dict[str, list[dict[str, Any]]] = {"candidate_baseline": [], "llm_filter": [], "llm_span_narrow": [], "llm_abstain_filter": []}
        decision_records: list[dict[str, Any]] = []
        call_diags: list[dict[str, Any]] = []
        pack_diags: list[dict[str, Any]] = []
        for task in tasks:
            tid = str(task.get("test_id") or task.get("task_id"))
            baseline_pred = cand_by_task.get(tid, {"task_id": tid, "repo_id": task["repo_id"], "evidence": []})
            packed, candidate_meta, pack_diag = pack_candidates(task, baseline_pred, repo_roots, max_candidates=args.max_candidates, window=args.snippet_window, allow_self_test=args.self_test, require_filter_applied=bool(remote_enabled))
            pack_diags.append({"task_id": tid, **pack_diag})
            if not packed:
                parsed, call_diag = local_decision(task, packed)
                call_diag["disabled_reason"] = "no_packed_candidates"
            elif remote_enabled:
                parsed, call_diag = remote_decision(task, packed)
            else:
                parsed, call_diag = local_decision(task, packed)
                call_diag["disabled_reason"] = remote_reason
            decision, schema_diag = validate_decision(parsed, packed)
            call_diag.update(schema_diag)
            call_diag["task_id"] = tid
            call_diags.append(call_diag)
            decision_records.append({
                "task_id": tid,
                "candidate_count": len(candidate_meta),
                "decision": decision,
                "candidate_meta": candidate_meta,
            })
            preds = decisions_to_predictions(task, candidate_meta, decision, baseline_pred)
            for strategy, pred in preds.items():
                predictions_by_strategy[strategy].append(pred)
        labels = r32.normalize_labels(r32.load_jsonl(labels_path))
        results: dict[str, Any] = {}
        for strategy, preds in predictions_by_strategy.items():
            metrics = r32.metrics_for(preds, labels, repo_roots, [int(p.get("latency_ms", 0)) for p in preds])
            metrics.update(p21e.contribution(preds, labels, args.top_k))
            results[strategy] = {"status": "ok", "metrics": metrics}
        baseline = results["candidate_baseline"]["metrics"]
        for strategy, payload in results.items():
            payload["delta_vs_candidate_baseline"] = {"baseline": True} if strategy == "candidate_baseline" else metric_delta(payload["metrics"], baseline)
            payload["primary_promotion_eligible"] = False
        successful_calls = sum(1 for d in call_diags if d.get("call_succeeded"))
        schema_valid = sum(1 for d in call_diags if d.get("schema_valid"))
        all_pack_filters_applied = all(bool(d.get("remote_file_filter_applied")) for d in pack_diags) if pack_diags else False
        if not candidate_info.get("candidate_strategy_available"):
            provider_status = "unavailable"
        elif remote_requested and not remote_enabled:
            provider_status = "unavailable"
        elif remote_requested and not all_pack_filters_applied:
            provider_status = "unavailable"
        elif successful_calls == len(tasks) and schema_valid == len(tasks):
            provider_status = "ok"
        else:
            provider_status = "degraded"
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stage": "P21-G3L LLM rich candidate pilot",
            "prompt_version": PROMPT_VERSION,
            "llm_provider": args.llm_provider,
            "llm_model": os.environ.get("OPENLOCUS_LLM_MODEL") if remote_enabled else "offline_deterministic",
            "llm_remote_requested": remote_requested,
            "llm_remote_enabled": remote_enabled,
            "llm_disabled_reason": remote_reason,
            "embedding_provider": args.embedding_provider,
            **r32.embedding_model_metadata(args.embedding_provider),
            "candidate_info": candidate_info,
            "provider_status": provider_status,
            "successful_calls": successful_calls,
            "schema_valid_calls": schema_valid,
            "tasks_scored": len(tasks),
            "candidate_strategy": candidate_info.get("actual_candidate_strategy"),
            "raw_snippets_sent_to_provider": bool(remote_enabled and any(d.get("packed_count", 0) for d in pack_diags)),
            "all_pack_file_filters_applied": all_pack_filters_applied,
            "raw_text_stored": False,
            "raw_query_stored": False,
            "raw_prompts_stored": False,
            "raw_responses_stored": False,
            "raw_snippets_committed": False,
            "private_labels_committed": False,
            "run_phase_public_only": True,
            "labels_loaded_after_run": True,
            "candidate_not_fact": True,
            "not_promotion_evidence": True,
            "promotion_ready": False,
            "default_should_change": False,
            "llm_direct_evidence_allowed": False,
            "strategy_results": results,
            "call_summary": {
                "latency_ms_p50": sorted([d.get("latency_ms", 0) for d in call_diags])[len(call_diags)//2] if call_diags else 0,
                "input_chars_total": sum(int(d.get("input_chars", 0)) for d in call_diags),
                "schema_error_count": sum(1 for d in call_diags if not d.get("schema_valid")),
                "packed_candidates_total": sum(d.get("packed_count", 0) for d in pack_diags),
            },
            "decision_records": decision_records,
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P21-G3L LLM Rich Candidate Pilot",
        "",
        "LLM sees constrained candidate snippets and may filter, abstain, or narrow spans. Its output is not Evidence.",
        "",
        "## Safety",
        "",
        f"- llm_remote_enabled: `{report.get('llm_remote_enabled')}`",
        f"- llm_model: `{report.get('llm_model')}`",
        f"- candidate_strategy: `{report.get('candidate_strategy')}`",
        f"- raw_snippets_sent_to_provider: `{report.get('raw_snippets_sent_to_provider')}`",
        f"- raw_snippets_committed: `{report.get('raw_snippets_committed')}`",
        f"- raw_prompts_stored: `{report.get('raw_prompts_stored')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        "",
        "## Results",
        "",
        "| Strategy | FileRecall@5 | SpanF0.5 | PFP | Gold | False | ΔSpan vs candidate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, payload in report.get("strategy_results", {}).items():
        metrics = payload.get("metrics", {})
        delta = payload.get("delta_vs_candidate_baseline", {})
        lines.append(f"| {strategy} | {metrics.get('FileRecall@5')} | {metrics.get('SpanF0.5')} | {metrics.get('primary_false_positive_rate')} | {metrics.get('added_gold_span')} | {metrics.get('added_false_span')} | {delta.get('SpanF0.5')} |")
    lines += ["", "## Call Summary", "", f"```json\n{json.dumps(report.get('call_summary', {}), indent=2)}\n```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("fixtures/r26_auto_stress/labels/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--embedding-provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--llm-provider", default="offline_deterministic", choices=["offline_deterministic", "openai-compatible"])
    parser.add_argument("--allow-remote-embedding", action="store_true")
    parser.add_argument("--allow-remote-llm", action="store_true")
    parser.add_argument("--dense-strategies", default=p21d.DEFAULT_DENSE_STRATEGIES)
    parser.add_argument("--candidate-strategy", default=DEFAULT_CANDIDATE_STRATEGY)
    parser.add_argument("--max-remote-data-level", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=20)
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-repo", type=int, default=120)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--anchor-file-k", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--snippet-window", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p21_g/llm_rich_candidate_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/p21-g-llm-rich-candidate.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    report = run(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
