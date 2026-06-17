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
import urllib.error
import urllib.request
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
OUTPUT_MODES = {"prompt_only", "json_object", "json_schema_strict", "tool_call"}
BUCKET_PREFIXES = ("source_category", "risk_tag", "expected_behavior", "oracle_type")
PACK_LAYOUTS = {
    "topk_plain_v0",
    "topk_scores_provenance_v0",
    "contrastive_competitor_v0",
    "hard_distractor_contrast_v0",
}
DEFAULT_PACK_LAYOUT = "topk_plain_v0"


def candidate_decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["not_evidence", "candidate_not_fact", "answerable", "items"],
        "properties": {
            "not_evidence": {"const": True},
            "candidate_not_fact": {"const": True},
            "answerable": {"type": "boolean"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["candidate_id", "decision", "start_line", "end_line", "reason_code"],
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "decision": {"type": "string", "enum": sorted(DECISIONS)},
                        "start_line": {"type": "integer", "minimum": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                        "reason_code": {"type": "string"},
                    },
                },
            },
        },
    }


def output_mode_payload(mode: str) -> dict[str, Any]:
    schema = candidate_decision_schema()
    if mode == "prompt_only":
        return {}
    if mode == "json_object":
        return {"response_format": {"type": "json_object"}}
    if mode == "json_schema_strict":
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "p21_g3l_candidate_decision",
                    "strict": True,
                    "schema": schema,
                },
            }
        }
    if mode == "tool_call":
        return {
            "tools": [{
                "type": "function",
                "function": {
                    "name": "emit_candidate_decisions",
                    "description": "Emit candidate-only retrieval decisions for P21-G3L.",
                    "parameters": schema,
                },
            }],
            "tool_choice": {"type": "function", "function": {"name": "emit_candidate_decisions"}},
        }
    raise ValueError(f"unsupported output mode: {mode}")


def fallback_modes(mode: str) -> list[str]:
    if mode == "tool_call":
        return ["json_schema_strict", "json_object", "prompt_only"]
    if mode == "json_schema_strict":
        return ["json_object", "prompt_only"]
    if mode == "json_object":
        return ["prompt_only"]
    return []


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _path_kind(path: str) -> str:
    """Infer a coarse path-kind from a relative path string using only public metadata."""
    p = str(path or "").lower().replace("\\", "/")
    parts = [part for part in p.split("/") if part]
    filename = parts[-1] if parts else ""
    if any(part in {"node_modules", "vendor", ".git", "generated", "gen", "dist", "build"} for part in parts):
        return "generated_or_vendor"
    if (
        any(part in {"test", "tests", "testing", "__tests__"} for part in parts)
        or filename.startswith(("test_", "tests_"))
        or any(filename.endswith(suffix) for suffix in ("_test.py", "_spec.js", ".test.ts", ".spec.ts", ".test.js", ".spec.js"))
    ):
        return "test"
    if filename.endswith((".md", ".rst", ".txt", ".markdown")) or any(part in {"docs", "doc", "documentation"} for part in parts):
        return "doc"
    if (
        filename.startswith(("config", "setup", "pyproject", "package", "tsconfig", "webpack", "dockerfile", "makefile", ".github"))
        or any(part in {"config", "configs", "conf", "ci"} for part in parts)
    ):
        return "config"
    return "source"


def _path_kind_flags(path: str) -> dict[str, bool]:
    kind = _path_kind(path)
    return {
        "source_code": kind in {"source", "config"},
        "test_code": kind == "test",
        "doc_ish": kind == "doc",
        "generated_or_vendor": kind == "generated_or_vendor",
    }


def _span_overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    try:
        return (
            int(a.get("end_line") or 0) >= int(b.get("start_line") or 0)
            and int(a.get("start_line") or 0) <= int(b.get("end_line") or 0)
        )
    except (TypeError, ValueError):
        return False


def _is_hard_distractor_proxy(cand: dict[str, Any], anchor: dict[str, Any], rank: int, task: dict[str, Any]) -> bool:
    """Gold-free RUN proxy for a hard distractor using only public metadata.

    Never uses labels, gold, SCORE outcomes, raw query/source text, or provider
    outputs.  The proxy needs at least two weak contrast signals versus the
    primary anchor to flag a candidate as a plausible distractor.
    """
    if rank == 1:
        return False
    signals = 0

    # Rank/score closeness: plausible wrong alternative near the top.
    if rank <= 3 or abs(rank - 1) <= 2:
        signals += 1
    c_score = cand.get("score")
    a_score = anchor.get("score")
    if isinstance(c_score, (int, float)) and isinstance(a_score, (int, float)) and abs(c_score - a_score) <= 0.15:
        signals += 1

    # Same-file non-overlapping or cross-file competitor shape.
    if str(cand.get("path") or "") != str(anchor.get("path") or ""):
        signals += 1
    elif not _span_overlaps(cand, anchor):
        signals += 1

    # Path-kind contrast (source/test/doc/config/generated).
    c_kind = cand.get("path_kind", "unknown")
    a_kind = anchor.get("path_kind", "unknown")
    if c_kind != a_kind:
        signals += 1
    if c_kind in {"test", "doc", "config", "generated_or_vendor"}:
        signals += 1

    # Channel/provenance disagreement.
    c_channels = set(cand.get("channels", []))
    a_channels = set(anchor.get("channels", []))
    if c_channels and a_channels and not (c_channels & a_channels):
        signals += 1

    # Public task risk context (aggregate-only tags already in the task).
    risk_tags = {str(t).lower() for t in task.get("task_risk_tags", [])}
    if risk_tags & {"high_confidence", "config", "negative", "weak_candidates", "ambiguous"}:
        signals += 1

    return signals >= 2


def _slot_label(
    layout: str,
    cand: dict[str, Any],
    anchor: dict[str, Any],
    rank: int,
    task: dict[str, Any],
) -> list[str]:
    """Return public, gold-free slot labels for a packed candidate."""
    if layout == "topk_plain_v0":
        return []
    if layout == "topk_scores_provenance_v0":
        return ["ranked"]

    is_primary = rank == 1
    labels: list[str] = []
    if is_primary:
        labels.append("primary")
        if layout in {"contrastive_competitor_v0", "hard_distractor_contrast_v0"}:
            return labels

    c_path = str(cand.get("path") or "")
    a_path = str(anchor.get("path") or "")
    if c_path == a_path:
        labels.append("same_file")
    else:
        labels.append("cross_file")

    c_kind = cand.get("path_kind", "unknown")
    a_kind = anchor.get("path_kind", "unknown")
    if c_kind != a_kind:
        labels.append(f"path_kind_contrast:{c_kind}_vs_{a_kind}")
    if c_kind == "test":
        labels.append("test_contrast")
    elif c_kind == "doc":
        labels.append("doc_contrast")
    elif c_kind == "config":
        labels.append("config_contrast")

    c_channels = set(cand.get("channels", []))
    a_channels = set(anchor.get("channels", []))
    if c_channels and a_channels and not (c_channels & a_channels):
        labels.append("channel_disagree")

    if layout == "hard_distractor_contrast_v0" and _is_hard_distractor_proxy(cand, anchor, rank, task):
        labels.append("hard_distractor_proxy")

    return labels


def _format_candidate_prompt(layout: str, cand: dict[str, Any]) -> str:
    """Format one candidate block for the provider prompt."""
    base = (
        f"candidate_id={cand['candidate_id']} path={cand['path']} "
        f"lines={cand['start_line']}-{cand['end_line']}"
    )
    if layout == "topk_plain_v0":
        return f"{base}\n{cand['snippet']}"

    extras: list[str] = []
    rank = cand.get("rank")
    if rank is not None:
        extras.append(f"rank={rank}")
    score = cand.get("score")
    if score is not None:
        extras.append(f"score={score}")
    extras.append(f"path_kind={cand.get('path_kind', 'unknown')}")
    flags = {k for k, v in (_path_kind_flags(cand['path']) or {}).items() if v}
    if flags:
        extras.append(f"path_kind_flags={sorted(flags)}")
    channels = cand.get("channels")
    if channels:
        extras.append(f"channels={list(channels)}")
    source_views = cand.get("source_views")
    if source_views:
        extras.append(f"source_views={list(source_views)}")
    slot_label = cand.get("slot_label")
    if slot_label:
        extras.append(f"slot_labels={list(slot_label)}")

    if layout == "topk_scores_provenance_v0":
        return f"{base} {' '.join(extras)}\n{cand['snippet']}"

    # Contrastive and hard-distractor layouts keep slot labels together.
    return f"{base} {' '.join(extras)}\n{cand['snippet']}"


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
    dense, dense_statuses, file_filter = p21d.dense_predictions(dense_args, tasks, repo_roots)  # type: ignore[arg-type]
    hybrids = p21d.build_hybrids(tasks, anchor, dense, args.top_k, args.anchor_file_k)
    strategy = args.candidate_strategy
    shared_info = {
        "dense_statuses": dense_statuses,
        "remote_file_filter_mode": file_filter.get("mode"),
        "remote_file_filter_applied": file_filter.get("applied"),
        "anchor_predictions": anchor,
        "hybrid_predictions": hybrids,
    }
    if strategy not in hybrids:
        return [], {
            "requested_candidate_strategy": args.candidate_strategy,
            "actual_candidate_strategy": None,
            "candidate_strategy_available": False,
            "unavailable_reason": "requested_candidate_strategy_unavailable",
            **shared_info,
        }
    return hybrids.get(strategy, []), {
        "requested_candidate_strategy": args.candidate_strategy,
        "actual_candidate_strategy": strategy,
        "candidate_strategy_available": True,
        "unavailable_reason": None,
        **shared_info,
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
    pack_layout: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    repo_id = task["repo_id"]
    repo_root = repo_roots[repo_id]
    file_filter = p21e.remote_file_filter({repo_id: repo_root}, allow_self_test=allow_self_test)
    if require_filter_applied and not file_filter.get("applied"):
        return [], [], {"skipped": {"remote_file_filter_not_applied": 1}, "remote_file_filter_applied": False, "packed_count": 0, "pack_layout": pack_layout, "pack_layout_metrics": None}
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

    # Apply public, gold-free layout metadata to packed candidates only.
    # This metadata is never persisted outside the transient provider prompt.
    anchor = packed[0] if packed else {}
    for rank, cand in enumerate(packed, start=1):
        cand["rank"] = rank
        cand["path_kind"] = _path_kind(cand["path"])
        cand["slot_label"] = _slot_label(pack_layout, cand, anchor, rank, task)

    layout_metrics = _compute_pack_layout_metrics(pack_layout, packed, task)
    return (
        packed,
        candidate_meta,
        {
            "skipped": skipped,
            "remote_file_filter_applied": file_filter.get("applied"),
            "packed_count": len(packed),
            "pack_layout": pack_layout,
            "pack_layout_metrics": layout_metrics,
        },
    )


def _compute_pack_layout_metrics(layout: str, packed: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any] | None:
    """Aggregate, gold-free metrics about the packed candidate layout."""
    if not packed:
        return None
    total = len(packed)
    path_kind_counts: dict[str, int] = {}
    flag_counts: dict[str, int] = {"source_code": 0, "test_code": 0, "doc_ish": 0, "generated_or_vendor": 0}
    slot_counts: dict[str, int] = {}
    hard_distractor_count = 0
    competitor_slot_count = 0
    anchor = packed[0]
    for rank, cand in enumerate(packed, start=1):
        kind = _path_kind(cand["path"])
        path_kind_counts[kind] = path_kind_counts.get(kind, 0) + 1
        for flag, present in _path_kind_flags(cand["path"]).items():
            if present:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        labels = _slot_label(layout, cand, anchor, rank, task)
        for label in labels:
            slot_counts[label] = slot_counts.get(label, 0) + 1
        if "hard_distractor_proxy" in labels:
            hard_distractor_count += 1
        if layout in {"contrastive_competitor_v0", "hard_distractor_contrast_v0"} and rank > 1:
            # Any non-primary slot label counts as a competitor slot.
            non_primary = [label for label in labels if label != "primary"]
            if non_primary:
                competitor_slot_count += 1

    return {
        "candidates_packed": total,
        "path_kind_counts": path_kind_counts,
        "flag_counts": flag_counts,
        "slot_counts": slot_counts,
        "hard_distractor_proxy_count": hard_distractor_count,
        "hard_distractor_proxy_rate": round(hard_distractor_count / total, 6) if total else 0.0,
        "competitor_slot_count": competitor_slot_count,
        "competitor_slot_rate": round(competitor_slot_count / total, 6) if total else 0.0,
    }


def _merge_int_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def aggregate_pack_layout_metrics(pack_diags: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-task pack layout metrics into RUN-phase public totals."""
    per_task = [d.get("pack_layout_metrics") for d in pack_diags if isinstance(d.get("pack_layout_metrics"), dict)]
    total_candidates = sum((m or {}).get("candidates_packed", 0) for m in per_task)
    path_kind_counts: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    slot_counts: dict[str, int] = {}
    hard_distractor_count = 0
    competitor_slot_count = 0
    for m in per_task:
        if not m:
            continue
        _merge_int_counts(path_kind_counts, m.get("path_kind_counts") or {})
        _merge_int_counts(flag_counts, m.get("flag_counts") or {})
        _merge_int_counts(slot_counts, m.get("slot_counts") or {})
        hard_distractor_count += m.get("hard_distractor_proxy_count", 0)
        competitor_slot_count += m.get("competitor_slot_count", 0)
    return {
        "tasks_with_packed_candidates": len(per_task),
        "candidates_packed_total": total_candidates,
        "path_kind_counts": path_kind_counts,
        "flag_counts": flag_counts,
        "slot_counts": slot_counts,
        "hard_distractor_proxy_count": hard_distractor_count,
        "hard_distractor_proxy_rate": round(hard_distractor_count / total_candidates, 6) if total_candidates else 0.0,
        "competitor_slot_count": competitor_slot_count,
        "competitor_slot_rate": round(competitor_slot_count / total_candidates, 6) if total_candidates else 0.0,
    }


def aggregate_decision_records(decision_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate transient per-task decisions for the public report.

    Full decision records contain candidate IDs, paths, ranges, and digests and
    are allowed only in the ephemeral P25 handoff.  The uploaded P21 report must
    remain aggregate-only.
    """
    decision_counts: dict[str, int] = {"primary": 0, "supporting": 0, "reject": 0}
    answerable_count = 0
    tasks_with_candidates = 0
    candidate_count_total = 0
    selected_item_count_total = 0
    for record in decision_records:
        candidate_count = int(record.get("candidate_count") or 0)
        candidate_count_total += candidate_count
        if candidate_count > 0:
            tasks_with_candidates += 1
        decision = record.get("decision") or {}
        if isinstance(decision, dict) and decision.get("answerable") is True:
            answerable_count += 1
        items = decision.get("items") if isinstance(decision, dict) else []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            token = str(item.get("decision") or "")
            if token in decision_counts:
                decision_counts[token] += 1
                selected_item_count_total += 1
    total_tasks = len(decision_records)
    return {
        "task_count": total_tasks,
        "tasks_with_candidates": tasks_with_candidates,
        "answerable_count": answerable_count,
        "answerable_rate": round(answerable_count / total_tasks, 6) if total_tasks else 0.0,
        "candidate_count_total": candidate_count_total,
        "selected_item_count_total": selected_item_count_total,
        "decision_counts": decision_counts,
        "decision_records_persisted": False,
        "candidate_meta_persisted": False,
    }


def aggregate_fallback_events(fallback_events: list[dict[str, Any]]) -> dict[str, Any]:
    mode_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    repair_attempted_count = 0
    repair_success_count = 0
    for event in fallback_events:
        mode = str(event.get("actual_output_mode") or event.get("requested_output_mode") or "unknown")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        if event.get("schema_repair_attempted"):
            repair_attempted_count += 1
        if event.get("schema_repair_success"):
            repair_success_count += 1
        for err in event.get("fallback_errors") or []:
            if not isinstance(err, dict):
                continue
            key = str(p20.safe_reason_token(err.get("reason") or err.get("error_type") or err.get("provider_code") or "unknown") or "unknown")
            error_counts[key] = error_counts.get(key, 0) + 1
        for err in event.get("schema_repair_fallback_errors") or []:
            if not isinstance(err, dict):
                continue
            key = str(p20.safe_reason_token(err.get("reason") or err.get("error_type") or err.get("provider_code") or "unknown") or "unknown")
            error_counts[key] = error_counts.get(key, 0) + 1
    return {
        "fallback_event_count": len(fallback_events),
        "mode_counts": mode_counts,
        "error_counts": error_counts,
        "schema_repair_attempted_count": repair_attempted_count,
        "schema_repair_success_count": repair_success_count,
        "per_task_fallback_events_persisted": False,
    }


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


def post_chat_completion_structured(messages: list[dict[str, str]], temperature: float, mode: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base_url = os.environ.get("OPENLOCUS_LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("OPENLOCUS_LLM_API_KEY", "")
    model = os.environ.get("OPENLOCUS_LLM_MODEL", "")
    url = base_url + "/chat/completions"
    retries = p20.positive_env_int("OPENLOCUS_LLM_RETRIES", 2, minimum=0, maximum=5)
    timeout = p20.positive_env_int("OPENLOCUS_LLM_TIMEOUT_SEC", 90, minimum=5, maximum=300)
    payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
    payload.update(output_mode_payload(mode))
    last_error: p20.RemoteLLMProviderError | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OpenLocus/0.1 (research harness)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - explicit opt-in
                body = json.loads(resp.read().decode("utf-8"))
            message = body.get("choices", [{}])[0].get("message", {})
            if mode == "tool_call":
                calls = message.get("tool_calls") or []
                if not calls:
                    raise json.JSONDecodeError("missing_tool_calls", "", 0)
                fn = calls[0].get("function", {})
                if fn.get("name") != "emit_candidate_decisions":
                    raise json.JSONDecodeError("unexpected_tool_call", "", 0)
                args = fn.get("arguments", "{}")
                return json.loads(args), {"actual_output_mode": mode, "provider_accepted_output_mode": True}
            content = message.get("content", "{}")
            return json.loads(content), {"actual_output_mode": mode, "provider_accepted_output_mode": True}
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="ignore")
            provider_code = None
            provider_error_type = None
            try:
                body = json.loads(raw_body)
                error_obj = body.get("error") if isinstance(body, dict) else None
                if isinstance(error_obj, dict):
                    provider_code = p20.safe_reason_token(error_obj.get("code"))
                    provider_error_type = p20.safe_reason_token(error_obj.get("type"))
            except json.JSONDecodeError:
                pass
            retriable = exc.code == 429 or 500 <= exc.code < 600
            last_error = p20.RemoteLLMProviderError(
                f"provider_http_{exc.code}",
                http_status=exc.code,
                provider_code=provider_code,
                provider_error_type=provider_error_type,
                retriable=retriable,
            )
        except TimeoutError:
            last_error = p20.RemoteLLMProviderError("provider_timeout", retriable=True)
        except urllib.error.URLError as exc:
            reason_class = type(exc.reason).__name__ if getattr(exc, "reason", None) is not None else "unknown"
            last_error = p20.RemoteLLMProviderError("provider_url_error", provider_error_type=p20.safe_reason_token(reason_class), retriable=True)
        except json.JSONDecodeError:
            last_error = p20.RemoteLLMProviderError("provider_invalid_json", retriable=True)
        if last_error is None or not last_error.retriable or attempt >= retries:
            break
        time.sleep(min(8.0, 0.5 * (2**attempt)))
    assert last_error is not None
    raise last_error


def remote_decision(task: dict[str, Any], packed: list[dict[str, Any]], output_mode: str, *, pack_layout: str = DEFAULT_PACK_LAYOUT, allow_fallback: bool = True) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id = os.environ.get("OPENLOCUS_LLM_MODEL", "unknown")
    candidates_text = [_format_candidate_prompt(pack_layout, cand) for cand in packed]
    layout_note = ""
    if pack_layout == "contrastive_competitor_v0":
        layout_note = "\n\nCandidate slot labels (primary/same_file/cross_file/path_kind_contrast/etc.) are metadata-only hints; they are not Evidence and do not indicate correctness."
    elif pack_layout == "hard_distractor_contrast_v0":
        layout_note = "\n\nA hard_distractor_proxy slot label marks a plausible distractor inferred from public metadata only; it is not a label, not gold, and not Evidence."
    elif pack_layout == "topk_scores_provenance_v0":
        layout_note = "\n\nRank/score/channel/source_view metadata is provenance only; it does not indicate correctness."
    user_content = (
        f"repo_id={task.get('repo_id')} task_id={task.get('test_id') or task.get('task_id')}\n"
        f"query={task.get('query')!r}\n\n"
        "Candidates are source snippets from current public/opt-in code after filtering. "
        "Choose only from candidate_id values shown. Do not invent paths or identifiers."
        + layout_note
        + "\n\n"
        + "\n\n---\n\n".join(candidates_text)
        + "\n\nRespond as JSON: {\"not_evidence\": true, \"candidate_not_fact\": true, "
        "\"answerable\": true|false, \"items\": [{\"candidate_id\": \"C1\", \"decision\": \"primary|supporting|reject\", "
        "\"start_line\": 1, \"end_line\": 2, \"reason_code\": \"short_token\"}]}"
    )
    if task.get("repair_instruction"):
        user_content += "\n\nSCHEMA REPAIR INSTRUCTION:\n" + str(task["repair_instruction"])
    messages = [
        {"role": "system", "content": "You are a code retrieval candidate filter. Output JSON only. Your output is not Evidence, not a label, and not a promotion verdict. If candidates do not support the query, set answerable=false and items=[]."},
        {"role": "user", "content": user_content},
    ]
    t0 = time.time()
    attempted = [output_mode] + (fallback_modes(output_mode) if allow_fallback else [])
    errors: list[dict[str, Any]] = []
    for idx, mode in enumerate(attempted):
        try:
            parsed, mode_diag = post_chat_completion_structured(messages, 0.0, mode)
            return parsed, {
                "call_succeeded": True,
                "latency_ms": int((time.time() - t0) * 1000),
                "input_chars": len(user_content),
                "output_chars": len(json.dumps(parsed)),
                "model_id": model_id,
                "requested_output_mode": output_mode,
                "actual_output_mode": mode_diag.get("actual_output_mode", mode),
                "fallback_used": idx > 0,
                "fallback_errors": errors,
            }
        except p20.RemoteLLMProviderError as exc:
            public = exc.as_public_dict()
            errors.append({"mode": mode, **public})
            provider_rejected = exc.http_status in {400, 404, 422}
            if provider_rejected and idx < len(attempted) - 1:
                continue
            return None, {"call_succeeded": False, **public, "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "model_id": model_id, "requested_output_mode": output_mode, "actual_output_mode": mode, "fallback_errors": errors}
        except Exception as exc:
            errors.append({"mode": mode, "error_type": type(exc).__name__})
            return None, {"call_succeeded": False, "error_type": type(exc).__name__, "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "model_id": model_id, "requested_output_mode": output_mode, "actual_output_mode": mode, "fallback_errors": errors}
    return None, {"call_succeeded": False, "error_type": "all_output_modes_failed", "latency_ms": int((time.time() - t0) * 1000), "input_chars": len(user_content), "model_id": model_id, "requested_output_mode": output_mode, "fallback_errors": errors}


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


def task_bucket_names(task: dict[str, Any], label: dict[str, Any]) -> list[str]:
    buckets: set[str] = set()
    for key in ["task_bucket"]:
        value = task.get(key)
        if value:
            buckets.add(f"{key}:{p20.safe_reason_token(value)}")
    risk_tags = task.get("task_risk_tags") or []
    if isinstance(risk_tags, str):
        risk_tags = [risk_tags]
    for tag in risk_tags:
        if tag:
            buckets.add(f"risk_tag:{p20.safe_reason_token(tag)}")
    return sorted(buckets) or ["task_bucket:unknown"]


def compute_bucket_results(
    predictions_by_strategy: dict[str, list[dict[str, Any]]],
    labels: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    top_k: int,
) -> dict[str, Any]:
    tasks_by_id = {str(t.get("test_id") or t.get("task_id")): t for t in tasks}
    bucket_to_task_ids: dict[str, list[str]] = {}
    for tid, task in tasks_by_id.items():
        label = labels.get(tid, {})
        for bucket in task_bucket_names(task, label):
            bucket_to_task_ids.setdefault(bucket, []).append(tid)
    out: dict[str, Any] = {}
    for bucket, tids in sorted(bucket_to_task_ids.items()):
        if len(tids) < 2:
            continue
        tid_set = set(tids)
        label_subset = {tid: labels[tid] for tid in tid_set if tid in labels}
        strategy_payloads: dict[str, Any] = {}
        for strategy, preds in predictions_by_strategy.items():
            subset = [p for p in preds if str(p.get("task_id")) in tid_set]
            if not subset:
                continue
            metrics = r32.metrics_for(subset, label_subset, repo_roots, [int(p.get("latency_ms", 0)) for p in subset])
            metrics.update(p21e.contribution(subset, label_subset, top_k))
            strategy_payloads[strategy] = metrics
        baseline = strategy_payloads.get("candidate_baseline")
        if baseline:
            for strategy, metrics in list(strategy_payloads.items()):
                strategy_payloads[strategy] = {
                    "metrics": metrics,
                    "delta_vs_candidate_baseline": {"baseline": True} if strategy == "candidate_baseline" else metric_delta(metrics, baseline),
                }
        out[bucket] = {"task_count": len(tids), "strategy_results": strategy_payloads}
    return out


P25_PUBLIC_BUCKET_ALLOWLIST = {"positive", "negative", "ambiguous", "hard_distractor", "stale-like", "dense_quiver_trap", "exact_symbol_unique", "config", "route_handler", "other", "unknown"}
P25_PUBLIC_TAG_ALLOWLIST = {"exact_symbol_match", "exact_symbol", "unique_symbol", "symbol_anchor", "config", "route_handler", "positive", "likely_positive", "high_confidence", "negative", "ambiguous", "hallucination_risk", "same_name_disambiguation", "test_source_confusion", "same_name_symbol", "frontend_backend_confusion", "generated_vendor", "stale_index_like", "stale_index_confusion", "dense_false_positive", "quiver_not_implemented", "hard_distractor", "weak_candidates", "other"}


def _p25_bucket(value: Any) -> str:
    token = str(value or "unknown")
    return token if token in P25_PUBLIC_BUCKET_ALLOWLIST else "other"


def _p25_tags(values: Any) -> list[str]:
    raw = values if isinstance(values, list) else []
    out: list[str] = []
    for value in raw:
        token = str(value)
        if token in P25_PUBLIC_TAG_ALLOWLIST and token not in out:
            out.append(token)
    return out or ["other"]


def _p25_outcome_dict(pred: dict[str, Any], label: dict[str, Any], labels: dict[str, dict[str, Any]], repo_roots: dict[str, Path], top_k: int, *, abstained: bool = False) -> dict[str, Any]:
    tid = pred["task_id"]
    label_subset = {tid: label} if tid in labels else {}
    metrics = r32.metrics_for([pred], label_subset, repo_roots, [0])
    metrics.update(p21e.contribution([pred], label_subset, top_k))
    return {
        "file_recall_at_5": metrics.get("FileRecall@5"),
        "span_f0_5": metrics.get("SpanF0.5"),
        "primary_false_positive_rate": metrics.get("primary_false_positive_rate"),
        "no_gold_false_primary_rate": metrics.get("primary_false_positive_rate") if not label.get("gold_spans") else 0.0,
        "added_gold_span": metrics.get("added_gold_span"),
        "added_false_span": metrics.get("added_false_span"),
        "abstained": abstained,
    }


def _span_flags_from_decision(decision: dict[str, Any] | None, candidate_meta: list[dict[str, Any]]) -> tuple[bool, bool]:
    items = (decision.get("items") or []) if isinstance(decision, dict) else []
    meta_by_id = {m["candidate_id"]: m for m in candidate_meta}
    valid = False
    within = False
    for item in items:
        cid = str(item.get("candidate_id") or "")
        meta = meta_by_id.get(cid)
        if not meta:
            continue
        if item.get("decision") in {"primary", "supporting"}:
            try:
                s = int(item.get("start_line") or meta["start_line"])
                e = int(item.get("end_line") or s)
                a0 = int(meta.get("allowed_start_line", meta["start_line"]))
                a1 = int(meta.get("allowed_end_line", meta["end_line"]))
                if a0 <= s <= e <= a1:
                    within = True
                    if (s, e) != (meta["start_line"], meta["end_line"]):
                        valid = True
            except (KeyError, TypeError, ValueError):
                continue
    return valid, within


def _evidence_paths(items: list[dict[str, Any]]) -> set[str]:
    return {str(ev.get("path") or "") for ev in items if ev.get("path")}


def _evidence_overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    try:
        return (
            str(a.get("path") or "") == str(b.get("path") or "")
            and int(a.get("end_line") or 0) >= int(b.get("start_line") or 0)
            and int(a.get("start_line") or 0) <= int(b.get("end_line") or 0)
        )
    except (TypeError, ValueError):
        return False


def _anchor_agreement_features(rrf_ev: list[dict[str, Any]], symbol_ev: list[dict[str, Any]], regex_ev: list[dict[str, Any]]) -> dict[str, bool]:
    """Compute RUN-phase local anchor agreement without labels or raw text."""
    symbol_paths = _evidence_paths(symbol_ev)
    regex_paths = _evidence_paths(regex_ev)
    local_anchor_ev = symbol_ev + regex_ev
    local_anchor_paths = symbol_paths | regex_paths
    top_rrf = rrf_ev[:1]
    rrf_anchor_agree_file = bool(top_rrf and local_anchor_paths and str(top_rrf[0].get("path") or "") in local_anchor_paths)
    rrf_anchor_agree_span = any(_evidence_overlaps(r, a) for r in top_rrf for a in local_anchor_ev)
    return {
        "symbol_regex_agree_file": bool(symbol_paths & regex_paths),
        "symbol_regex_agree_span": any(_evidence_overlaps(s, r) for s in symbol_ev for r in regex_ev),
        "rrf_anchor_agree_file": rrf_anchor_agree_file,
        "rrf_anchor_agree_span": rrf_anchor_agree_span,
        "rrf_backed_by_anchor": rrf_anchor_agree_span or rrf_anchor_agree_file,
    }


def _p31_lightweight_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return lightweight candidate evidence for P31 reach study.

    Keeps only rank, path, line range, content_sha, score, and channels.
    Never stores snippet text, raw queries, prompts, or responses.
    """
    out: list[dict[str, Any]] = []
    for rank, ev in enumerate(items, start=1):
        key = p21d.evidence_key(ev)
        entry: dict[str, Any] = {
            "rank": rank,
            "path": str(ev.get("path") or ""),
            "start_line": ev.get("start_line"),
            "end_line": ev.get("end_line"),
            "candidate_id": hashlib.sha256(f"{key[0]}:{key[1]}:{key[2]}:{rank}".encode("utf-8")).hexdigest()[:16],
        }
        if ev.get("content_sha"):
            entry["content_sha"] = str(ev["content_sha"])
        if ev.get("score") is not None:
            entry["score"] = float(ev["score"])
        if ev.get("channels"):
            entry["channels"] = list(ev["channels"])
        out.append(entry)
    return out


def _p33b_subtype_rows(
    symbol_regex_evidence: list[dict[str, Any]],
    symbol_ev: list[dict[str, Any]],
    regex_ev: list[dict[str, Any]],
    rrf_ev: list[dict[str, Any]],
    route_features: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    """Build private anchor subtype rows for P33-B calibration.

    Rows contain only aggregate-able classification metadata; no raw text,
    queries, snippets, prompts, responses, gold, or provider fields.
    """
    symbol_files = {p21d.evidence_key(ev)[0] for ev in symbol_ev if ev.get("path")}
    regex_files = {p21d.evidence_key(ev)[0] for ev in regex_ev if ev.get("path")}
    rrf_keys = {p21d.evidence_key(ev) for ev in rrf_ev}
    rrf_files = {key[0] for key in rrf_keys if key[0]}

    cand_count = int(route_features.get("candidate_count") or 0)
    if cand_count <= 5:
        count_bin = "small"
    elif cand_count <= 15:
        count_bin = "medium"
    else:
        count_bin = "large"

    rows: list[dict[str, Any]] = []
    for rank, ev in enumerate(symbol_regex_evidence[:top_k], start=1):
        key = p21d.evidence_key(ev)
        path = key[0]
        meta = ev.get("meta") or {}
        sources = set(meta.get("fusion_sources") or [])
        if not sources:
            sources = set(ev.get("channels") or [])
        if sources == {"symbol"}:
            source_class = "symbol_only"
        elif sources == {"regex"}:
            source_class = "regex_only"
        elif "symbol" in sources and "regex" in sources:
            source_class = "symbol_regex_fusion"
        elif "symbol" in sources:
            source_class = "symbol_only"
        elif "regex" in sources:
            source_class = "regex_only"
        else:
            source_class = "other"

        if source_class == "symbol_regex_fusion":
            agreement_class = "span_overlap"
        elif source_class == "symbol_only":
            if not regex_ev:
                agreement_class = "single_source"
            elif any(_evidence_overlaps(ev, other) for other in regex_ev):
                agreement_class = "span_overlap"
            elif path in regex_files:
                agreement_class = "same_file_only"
            else:
                agreement_class = "disagree"
        elif source_class == "regex_only":
            if not symbol_ev:
                agreement_class = "single_source"
            elif any(_evidence_overlaps(ev, other) for other in symbol_ev):
                agreement_class = "span_overlap"
            elif path in symbol_files:
                agreement_class = "same_file_only"
            else:
                agreement_class = "disagree"
        else:
            agreement_class = "single_source"

        rrf_backing = key in rrf_keys

        if rank <= 3:
            rank_bin = "top3"
        elif rank <= 5:
            rank_bin = "top5"
        else:
            rank_bin = "top10"

        start_line = int(key[1] or 0)
        end_line = int(key[2] or 0)
        width = max(0, end_line - start_line + 1)
        if width <= 1:
            width_bin = "point"
        elif width <= 10:
            width_bin = "short"
        else:
            width_bin = "long"

        rows.append({
            "candidate_id": hashlib.sha256(f"{key[0]}:{key[1]}:{key[2]}:{rank}".encode("utf-8")).hexdigest()[:16],
            "rank": rank,
            "source_class": source_class,
            "agreement_class": agreement_class,
            "rank_bin": rank_bin,
            "candidate_count_bin": count_bin,
            "span_width_bin": width_bin,
            "rrf_backing": rrf_backing,
        })
    return rows


def _p31_score_gold(label: dict[str, Any]) -> dict[str, Any]:
    """Private SCORE-phase gold metadata for P31 reach study.

    Ephemeral only; never committed or uploaded.
    """
    gold_spans: list[dict[str, Any]] = []
    for gs in label.get("gold_spans") or []:
        if not isinstance(gs, dict):
            continue
        entry: dict[str, Any] = {
            "path": str(gs.get("path") or ""),
            "start_line": int(gs["start_line"]) if isinstance(gs.get("start_line"), (int, float, str)) else None,
            "end_line": int(gs["end_line"]) if isinstance(gs.get("end_line"), (int, float, str)) else None,
        }
        if gs.get("content_sha"):
            entry["content_sha"] = str(gs["content_sha"])
        gold_spans.append(entry)
    has_gold = bool(gold_spans)
    return {
        "has_gold": has_gold,
        "score_group": "positive" if has_gold else "no_gold",
        "gold_spans": gold_spans,
    }


def write_p25_policy_records(
    path: Path,
    tasks: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    predictions_by_strategy: dict[str, list[dict[str, Any]]],
    decision_records: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    top_k: int,
    candidate_info: dict[str, Any] | None = None,
) -> None:
    """Write ephemeral per-task score records for P25 same-run handoff."""
    decision_by_task = {str(d.get("task_id")): d for d in decision_records}
    preds_by_strategy_task: dict[str, dict[str, dict[str, Any]]] = {}
    for strategy, preds in predictions_by_strategy.items():
        preds_by_strategy_task[strategy] = {str(p.get("task_id")): p for p in preds}

    anchor_preds = (candidate_info or {}).get("anchor_predictions") or {}
    anchor_by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for method, preds in anchor_preds.items():
        if isinstance(preds, list):
            anchor_by_task[method] = {str(p.get("task_id")): p for p in preds}

    records: list[dict[str, Any]] = []
    for task in tasks:
        tid = str(task.get("test_id") or task.get("task_id"))
        label = labels.get(tid, {})
        tags = _p25_tags(task.get("task_risk_tags"))
        decision = decision_by_task.get(tid, {})
        candidate_meta = decision.get("candidate_meta") or []

        query = str(task.get("query", ""))
        noisy = (
            p20.is_negative_noise_query(query)
            or p20.is_vague_multi_word_query(query)
            or p20.is_compound_snake_case_noise(query)
        )

        rrf_pred = anchor_by_task.get("rrf", {}).get(tid, {})
        symbol_pred = anchor_by_task.get("symbol", {}).get(tid, {})
        regex_pred = anchor_by_task.get("regex", {}).get(tid, {})
        rrf_ev = list(rrf_pred.get("evidence", []) or [])
        symbol_ev = list(symbol_pred.get("evidence", []) or [])
        regex_ev = list(regex_pred.get("evidence", []) or [])
        anchor_features = _anchor_agreement_features(rrf_ev, symbol_ev, regex_ev)

        llm_span_narrow_valid, llm_span_within_candidate = _span_flags_from_decision(
            decision.get("decision"), candidate_meta
        )
        dense_support_present = any(
            ch.startswith("dense_")
            for m in candidate_meta
            for ch in (m.get("channels") or [])
        )
        tags_set = set(tags)
        symbol_anchor = bool(symbol_ev) or "symbol_anchor" in tags_set or "exact_symbol" in tags_set
        regex_anchor = bool(regex_ev) or "regex_anchor" in tags_set
        local_anchor = bool(rrf_ev or symbol_ev or regex_ev)

        rec: dict[str, Any] = {
            "task_id": tid,
            "repo_id": task.get("repo_id"),
            "task_bucket": _p25_bucket(task.get("task_bucket")),
            "task_risk_tags": tags,
            "score_group": "positive" if label.get("gold_spans") else "no_gold",
            "route_features": {
                "candidate_count": len(candidate_meta),
                "candidate_support_exists": bool(candidate_meta),
                "unique_symbol_anchor": "unique_symbol" in tags_set,
                "exact_unique_symbol_anchor": "exact_symbol" in tags_set and "unique_symbol" in tags_set,
                "symbol_anchor": symbol_anchor,
                "regex_anchor": regex_anchor,
                "local_anchor": local_anchor,
                "symbol_regex_agree_file": anchor_features["symbol_regex_agree_file"],
                "symbol_regex_agree_span": anchor_features["symbol_regex_agree_span"],
                "rrf_anchor_agree_file": anchor_features["rrf_anchor_agree_file"],
                "rrf_anchor_agree_span": anchor_features["rrf_anchor_agree_span"],
                "rrf_backed_by_anchor": anchor_features["rrf_backed_by_anchor"],
                "query_noise": 1.0 if noisy else 0.0,
                "llm_span_narrow_valid": llm_span_narrow_valid,
                "llm_span_within_candidate": llm_span_within_candidate,
                "dense_support_present": dense_support_present,
                "graph_support_present": False,
            },
        }
        for strategy in ["candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter"]:
            pred = preds_by_strategy_task.get(strategy, {}).get(tid, {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": []})
            rec[strategy] = _p25_outcome_dict(pred, label, labels, repo_roots, top_k, abstained=not bool(pred.get("evidence")))

        # P30-H1 local anchor outcomes measured after labels are loaded; ephemeral only.
        symbol_regex_evidence = p21d.rrf_fuse([("symbol", symbol_ev), ("regex", regex_ev)], top_k=top_k)
        rec["symbol_regex_union"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": symbol_regex_evidence, "latency_ms": 0},
            label, labels, repo_roots, top_k,
        )
        rec["rrf_primary"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": rrf_ev, "latency_ms": 0},
            label, labels, repo_roots, top_k,
        )
        # P33-B: primary symbol/regex outcomes for subtype calibration; ephemeral only.
        rec["symbol_primary"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": symbol_ev, "latency_ms": 0},
            label, labels, repo_roots, top_k,
        )
        rec["regex_primary"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": regex_ev, "latency_ms": 0},
            label, labels, repo_roots, top_k,
        )
        rec["supporting_only"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": [], "latency_ms": 0},
            label, labels, repo_roots, top_k, abstained=True,
        )
        rec["weak_candidate_only"] = _p25_outcome_dict(
            {"task_id": tid, "repo_id": task.get("repo_id"), "evidence": [], "latency_ms": 0},
            label, labels, repo_roots, top_k, abstained=True,
        )

        # P31-H1: lightweight candidate pools and private SCORE-phase gold spans.
        # These live only in the ephemeral handoff, never in committed artifacts.
        p31_pools: dict[str, list[dict[str, Any]]] = {}
        for strategy in ["candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter"]:
            pred = preds_by_strategy_task.get(strategy, {}).get(tid, {})
            p31_pools[strategy] = _p31_lightweight_evidence(list(pred.get("evidence", []) or [])[:top_k])
        p31_pools["symbol_regex_union"] = _p31_lightweight_evidence(symbol_regex_evidence[:top_k])
        p31_pools["rrf_primary"] = _p31_lightweight_evidence(rrf_ev[:top_k])
        p31_pools["symbol_primary"] = _p31_lightweight_evidence(symbol_ev[:top_k])
        p31_pools["regex_primary"] = _p31_lightweight_evidence(regex_ev[:top_k])
        rec["p31_candidate_pools"] = p31_pools
        rec["p31_score_gold"] = _p31_score_gold(label)

        # P33-B: private anchor subtype metadata for subtype calibration; ephemeral only.
        rec["p33b_anchor_subtypes"] = _p33b_subtype_rows(
            symbol_regex_evidence, symbol_ev, regex_ev, rrf_ev, rec["route_features"], top_k
        )
        rec["p33b_anchor_subtypes_schema"] = "p33b-anchor-subtypes-v1"
        rec["p33b_anchor_subtype_handoff"] = True

        records.append(rec)
    payload = {
        "schema_version": "p25-policy-records-ephemeral-v1",
        "p31_h1_candidate_reach_handoff": True,
        "p31_h1_schema_version": "p31-h1-candidate-reach-handoff-v1",
        "p30_h1_fields_present": True,
        "contains_local_anchor_outcomes": True,
        "p30_h1_route_features_present": True,
        "not_artifact_for_commit": True,
        "score_phase_gold_group_stored": True,
        "p31_score_gold_spans_stored": True,
        "raw_queries_stored": False,
        "raw_snippets_stored": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "gold_spans_stored": False,
        "private_label_categories_stored": False,
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    tmp_ctx, tasks, labels_path, repo_roots = p21e.load_inputs(args)
    try:
        candidate_preds, candidate_info = build_candidate_predictions(args, tasks, repo_roots)
        cand_by_task = {str(p.get("task_id")): p for p in candidate_preds}
        remote_requested = args.llm_provider == "openai-compatible" and bool(args.allow_remote_llm)
        remote_enabled, remote_reason = p20.remote_llm_enabled(SimpleNamespace(provider=args.llm_provider, allow_remote=args.allow_remote_llm))  # type: ignore[arg-type]
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
            packed, candidate_meta, pack_diag = pack_candidates(task, baseline_pred, repo_roots, max_candidates=args.max_candidates, window=args.snippet_window, allow_self_test=args.self_test, require_filter_applied=bool(remote_enabled), pack_layout=args.pack_layout)
            pack_diags.append({"task_id": tid, **pack_diag})
            if not packed:
                parsed, call_diag = local_decision(task, packed)
                call_diag["disabled_reason"] = "no_packed_candidates"
            elif remote_enabled:
                parsed, call_diag = remote_decision(task, packed, args.llm_output_mode, pack_layout=args.pack_layout)
            else:
                parsed, call_diag = local_decision(task, packed)
                call_diag["disabled_reason"] = remote_reason
            decision, schema_diag = validate_decision(parsed, packed)
            repair_diag: dict[str, Any] = {"schema_repair_attempted": False, "schema_repair_success": False}
            if remote_enabled and args.schema_repair_retry and call_diag.get("call_succeeded") and not schema_diag.get("schema_valid"):
                repair_diag["schema_repair_attempted"] = True
                repair_task = dict(task)
                repair_task["repair_instruction"] = (
                    "Your previous output violated schema. Error: "
                    + str(schema_diag.get("schema_error") or "invalid_items")
                    + ". Re-output only valid JSON/tool arguments for the same candidates. Do not add explanation."
                )
                repair_mode = str(call_diag.get("actual_output_mode") or args.llm_output_mode)
                repaired, repair_call_diag = remote_decision(repair_task, packed, repair_mode, pack_layout=args.pack_layout, allow_fallback=False)
                repaired_decision, repaired_schema_diag = validate_decision(repaired, packed)
                repair_diag.update({
                    "schema_repair_call_succeeded": repair_call_diag.get("call_succeeded"),
                    "schema_repair_requested_output_mode": repair_mode,
                    "schema_repair_actual_output_mode": repair_call_diag.get("actual_output_mode"),
                    "schema_repair_fallback_used": repair_call_diag.get("fallback_used", False),
                    "schema_repair_fallback_errors": repair_call_diag.get("fallback_errors", []),
                    "schema_repair_latency_ms": repair_call_diag.get("latency_ms", 0),
                    "schema_repair_schema_valid": repaired_schema_diag.get("schema_valid"),
                })
                if repaired_schema_diag.get("schema_valid"):
                    decision = repaired_decision
                    schema_diag = repaired_schema_diag
                    repair_diag["schema_repair_success"] = True
            call_diag.update(schema_diag)
            call_diag.update(repair_diag)
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
        bucket_results = compute_bucket_results(predictions_by_strategy, labels, tasks, repo_roots, args.top_k)
        if args.p25_policy_records_out:
            write_p25_policy_records(
                args.p25_policy_records_out, tasks, labels, predictions_by_strategy,
                decision_records, repo_roots, args.top_k, candidate_info=candidate_info,
            )
        candidate_info_public = {
            k: v for k, v in candidate_info.items()
            if k not in {"anchor_predictions", "hybrid_predictions"}
        }
        successful_calls = sum(1 for d in call_diags if d.get("call_succeeded"))
        schema_valid = sum(1 for d in call_diags if d.get("schema_valid"))
        fallback_events = [
            {
                "task_id": d.get("task_id"),
                "requested_output_mode": d.get("requested_output_mode"),
                "actual_output_mode": d.get("actual_output_mode"),
                "fallback_used": d.get("fallback_used", False),
                "fallback_errors": d.get("fallback_errors", []),
                "schema_repair_attempted": d.get("schema_repair_attempted", False),
                "schema_repair_success": d.get("schema_repair_success", False),
                "schema_repair_actual_output_mode": d.get("schema_repair_actual_output_mode"),
                "schema_repair_fallback_errors": d.get("schema_repair_fallback_errors", []),
            }
            for d in call_diags
            if d.get("fallback_used") or d.get("fallback_errors") or d.get("schema_repair_attempted")
        ]
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
            "requested_output_mode": args.llm_output_mode,
            "llm_provider": args.llm_provider,
            "llm_model": os.environ.get("OPENLOCUS_LLM_MODEL") if remote_enabled else "offline_deterministic",
            "llm_remote_requested": remote_requested,
            "llm_remote_enabled": remote_enabled,
            "llm_disabled_reason": remote_reason,
            "embedding_provider": args.embedding_provider,
            **r32.embedding_model_metadata(args.embedding_provider),
            "candidate_info": candidate_info_public,
            "provider_status": provider_status,
            "successful_calls": successful_calls,
            "schema_valid_calls": schema_valid,
            "tasks_scored": len(tasks),
            "task_sample_mode": getattr(args, "task_sample_mode", "prefix"),
            "candidate_strategy": candidate_info.get("actual_candidate_strategy"),
            "raw_snippets_sent_to_provider": bool(remote_enabled and any(d.get("packed_count", 0) for d in pack_diags)),
            "all_pack_file_filters_applied": all_pack_filters_applied,
            "raw_text_stored": False,
            "raw_query_stored": False,
            "raw_prompts_stored": False,
            "raw_responses_stored": False,
            "raw_snippets_committed": False,
            "raw_paths_in_artifact": False,
            "raw_line_ranges_in_artifact": False,
            "raw_digests_in_artifact": False,
            "decision_records_in_artifact": False,
            "candidate_meta_in_artifact": False,
            "private_labels_committed": False,
            "aggregate_only_public_artifact": True,
            "run_phase_public_only": True,
            "labels_loaded_after_run": True,
            "candidate_not_fact": True,
            "not_promotion_evidence": True,
            "promotion_ready": False,
            "default_should_change": False,
            "llm_direct_evidence_allowed": False,
            "pack_layout": args.pack_layout,
            "pack_layout_not_evidence": True,
            "pack_layout_metrics": aggregate_pack_layout_metrics(pack_diags),
            "decision_summary": aggregate_decision_records(decision_records),
            "strategy_results": results,
            "bucket_results": bucket_results,
            "call_summary": {
                "latency_ms_p50": sorted([d.get("latency_ms", 0) for d in call_diags])[len(call_diags)//2] if call_diags else 0,
                "input_chars_total": sum(int(d.get("input_chars", 0)) for d in call_diags),
                "schema_error_count": sum(1 for d in call_diags if not d.get("schema_valid")),
                "schema_repair_attempted_count": sum(1 for d in call_diags if d.get("schema_repair_attempted")),
                "schema_repair_success_count": sum(1 for d in call_diags if d.get("schema_repair_success")),
                "actual_output_modes": sorted({str(d.get("actual_output_mode")) for d in call_diags if d.get("actual_output_mode")}),
                "fallback_used_count": sum(1 for d in call_diags if d.get("fallback_used")),
                "fallback_event_count": len(fallback_events),
                "fallback_events": aggregate_fallback_events(fallback_events),
                "packed_candidates_total": sum(d.get("packed_count", 0) for d in pack_diags),
            },
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
        f"- requested_output_mode: `{report.get('requested_output_mode')}`",
        f"- candidate_strategy: `{report.get('candidate_strategy')}`",
        f"- pack_layout: `{report.get('pack_layout')}`",
        f"- pack_layout_not_evidence: `{report.get('pack_layout_not_evidence')}`",
        f"- raw_snippets_sent_to_provider: `{report.get('raw_snippets_sent_to_provider')}`",
        f"- raw_snippets_committed: `{report.get('raw_snippets_committed')}`",
        f"- raw_prompts_stored: `{report.get('raw_prompts_stored')}`",
        f"- aggregate_only_public_artifact: `{report.get('aggregate_only_public_artifact')}`",
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
    lines += ["", "## Decision Summary", "", f"```json\n{json.dumps(report.get('decision_summary', {}), indent=2)}\n```", ""]
    lines += ["", "## Pack Layout Metrics", "", f"```json\n{json.dumps(report.get('pack_layout_metrics', {}), indent=2)}\n```", ""]
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
    parser.add_argument("--llm-output-mode", default="json_object", choices=sorted(OUTPUT_MODES))
    parser.add_argument("--pack-layout", default=DEFAULT_PACK_LAYOUT, choices=sorted(PACK_LAYOUTS))
    parser.add_argument("--schema-repair-retry", action="store_true")
    parser.add_argument("--p25-policy-records-out", type=Path, help="Ephemeral SCORE-phase records for P25; do not commit/upload.")
    parser.add_argument("--allow-remote-embedding", action="store_true")
    parser.add_argument("--allow-remote-llm", action="store_true")
    parser.add_argument("--dense-strategies", default=p21d.DEFAULT_DENSE_STRATEGIES)
    parser.add_argument("--candidate-strategy", default=DEFAULT_CANDIDATE_STRATEGY)
    parser.add_argument("--max-remote-data-level", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=20)
    parser.add_argument("--task-sample-mode", default="prefix", choices=["prefix", "round_robin_public_buckets"])
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-repo", type=int, default=120)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--anchor-file-k", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--snippet-window", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p21_g/llm_rich_candidate_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/en/p21-g-llm-rich-candidate.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    report = run(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    if args.self_test:
        assert report.get("pack_layout") == args.pack_layout
        assert isinstance(report.get("pack_layout_metrics"), dict)
        assert report["pack_layout_metrics"].get("candidates_packed_total") is not None
        assert report.get("decision_records") is None
        assert report.get("decision_records_in_artifact") is False
        assert report.get("candidate_meta_in_artifact") is False
        print("self-test pack layout assertions ok")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
