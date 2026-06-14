#!/usr/bin/env python3
"""P22/P23 Evidence-Seeking Retrieval Policy Research harness.

P22 Decision Surface Freeze: reproducible manifest of the current retrieval
surface (fixture hashes, baseline reference hashes, available strategy
baselines, model profile manifest).

P23 Bottleneck Decomposition: run local candidate strategies on a capped
public-task set and decompose failures into candidate_absent, file_wrong,
file_right_span_wrong, no_gold_false_primary, filter/admission proxy metrics,
per-bucket breakdowns, etc.

Safety:
- No remote provider/model calls. Only local deterministic search is used.
- RUN phase uses public tasks + local source; labels are loaded only after
  predictions exist.
- Artifacts never contain raw query text, raw source snippets, gold spans,
  private labels, provider keys, or secrets.
- Reports may contain task IDs, repo IDs, hashes, aggregate counts/metrics,
  and strategy names.
- Promotion and default recommendations are always false in this research
  harness.
- Does not modify Rust core or EvidenceCore semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_EVAL_DIR = Path(__file__).resolve().parent

try:
    import p20_llm_large_scale as p20  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r29_r26_stress_matrix as r29  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import score as score_mod  # type: ignore
except Exception:  # pragma: no cover
    sys.path.insert(0, str(_EVAL_DIR))
    import p20_llm_large_scale as p20  # type: ignore
    import p21_embedding_context as p21e  # type: ignore
    import r29_r26_stress_matrix as r29  # type: ignore
    import r32_embedding_view_bakeoff as r32  # type: ignore
    import score as score_mod  # type: ignore


SCHEMA_VERSION = "p22-p23-policy-surface-v1"
BASE_STRATEGIES = ["regex", "bm25", "symbol", "rrf"]
COMPOSITE_STRATEGIES = ["symbol_regex_union", "rrf_guarded_by_symbol_regex"]
ALL_STRATEGIES = BASE_STRATEGIES + COMPOSITE_STRATEGIES

REFERENCE_PATHS = [
    Path("docs/en/r29-r26-stress-matrix.md"),
    Path("docs/en/r30-baseline-freeze.md"),
    Path("artifacts/r30/baseline_manifest.json"),
    Path("artifacts/p20_llm_large/p20_llm_large_report.json"),
]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return r29.file_sha256(path)
    except OSError:
        return None


def hash_info(path: Path, *, count_lines: bool = False) -> dict[str, Any] | None:
    sha = file_hash(path)
    if sha is None:
        return None
    info: dict[str, Any] = {"path": str(path), "sha256": sha}
    try:
        info["bytes"] = path.stat().st_size
        if count_lines:
            text = path.read_text(encoding="utf-8")
            info["lines"] = sum(1 for line in text.splitlines() if line.strip())
    except OSError:
        pass
    return info


def load_repo_lock_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = r32.load_jsonl(path) if path.suffix == ".jsonl" else [json.loads(path.read_text(encoding="utf-8"))]
    if isinstance(rows, dict):
        if "repo_id" in rows and "source" in rows:
            rows = [rows]
        else:
            rows = rows.get("repos", rows.get("repositories", []))
    return [row for row in rows if isinstance(row, dict)]


def sample_tasks(tasks: list[dict[str, Any]], max_tasks: int, mode: str) -> list[dict[str, Any]]:
    return p21e.sample_public_tasks(tasks, max_tasks, mode)


def sanitize_public_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip legacy task rows down to fields allowed during RUN.

    Older fixtures sometimes include task_type/method hints. Those are not labels,
    but P22/P23 keeps the RUN phase intentionally minimal and public-only. Labels,
    gold spans, hard negatives, and private fields are never copied here.
    """
    out: list[dict[str, Any]] = []
    for row in tasks:
        tid = row.get("test_id") or row.get("task_id")
        sanitized = {
            "test_id": tid,
            "task_id": tid,
            "repo_id": row.get("repo_id"),
            "query": row.get("query", ""),
        }
        # Optional public bucket metadata; never inferred from labels here.
        if row.get("task_bucket") is not None:
            sanitized["task_bucket"] = row.get("task_bucket")
        # Deliberately do not promote legacy source_category/task_type into
        # public buckets. They may be label-like in historical fixtures. Only
        # explicit task_bucket/task_risk_tags are treated as public metadata.
        if row.get("task_risk_tags") is not None:
            sanitized["task_risk_tags"] = row.get("task_risk_tags")
        out.append(sanitized)
    return out


def build_decision_surface(
    repo_lock_path: Path,
    tasks_path: Path,
    labels_path: Path,
    repo_lock_rows: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    tasks: list[dict[str, Any]],
    elapsed_ms: int,
    self_test: bool,
) -> dict[str, Any]:
    repo_lock_hash = hash_info(repo_lock_path)
    tasks_hash = hash_info(tasks_path)
    labels_hash = hash_info(labels_path)

    available_repos = []
    rows_by_id = {str(row.get("repo_id", "")): row for row in repo_lock_rows}
    for repo_id in sorted(rows_by_id):
        row = rows_by_id[repo_id]
        manifest_sha = row.get("content_manifest_sha")
        if not manifest_sha and repo_id in repo_roots:
            try:
                manifest_sha, _fc, _tl = r29.compute_normalized_manifest_sha(repo_roots[repo_id])
            except Exception:  # pragma: no cover
                manifest_sha = None
        if manifest_sha:
            available_repos.append({"repo_id": repo_id, "content_manifest_sha": manifest_sha})

    references: dict[str, Any] = {}
    for ref_path in REFERENCE_PATHS:
        info = hash_info(ref_path)
        if info is not None:
            references[str(ref_path)] = info

    model_profile_path = Path("eval/p21_model_profiles.json")
    model_manifest = hash_info(model_profile_path)

    return {
        "self_test_inputs": self_test,
        "input_hashes": {
            "repo_lock": repo_lock_hash.get("sha256") if isinstance(repo_lock_hash, dict) else None,
            "tasks": tasks_hash.get("sha256") if isinstance(tasks_hash, dict) else None,
            "labels": labels_hash.get("sha256") if isinstance(labels_hash, dict) else None,
        },
        "task_count_loaded": len(tasks),
        "task_count_scored": len(tasks),
        "repo_count_loaded": len(repo_lock_rows),
        "available_repo_count": len(repo_roots),
        "available_repos": available_repos,
        "available_strategy_baselines": list(ALL_STRATEGIES),
        "reference_artifact_hashes": references,
        "model_profile_manifest": model_manifest,
        "elapsed_ms": elapsed_ms,
    }


def make_self_test_inputs(tmp: Path) -> tuple[Path, Path, Path, dict[str, Path]]:
    """Generate a minimal repo + public tasks + private labels for self-test."""
    repo = tmp / "p22-mini-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "config").mkdir(parents=True)

    (repo / "src" / "lib.py").write_text(
        "# Alpha lookup resolves the primary account path\n"
        "def alpha_lookup(user_id):\n"
        "    return {'user_id': user_id}\n\n"
        "def beta_route_handler(request):\n"
        "    return alpha_lookup(request.user_id)\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_lib.py").write_text(
        "def test_alpha_lookup():\n"
        "    assert alpha_lookup('u1')['user_id'] == 'u1'\n",
        encoding="utf-8",
    )
    (repo / "config" / "service.yaml").write_text(
        "service_name: alpha\n"
        "timeout_ms: 100\n",
        encoding="utf-8",
    )

    repo_lock = tmp / "repo-lock.jsonl"
    repo_lock.write_text(
        json.dumps({"repo_id": "p22-mini", "source": {"path": str(repo)}}) + "\n",
        encoding="utf-8",
    )

    tasks_path = tmp / "tasks.jsonl"
    labels_path = tmp / "labels.jsonl"

    task_rows = [
        {"test_id": "p22-001", "repo_id": "p22-mini", "query": "alpha_lookup", "public_version": "0", "source": "p22_self_test", "task_bucket": "positive", "task_risk_tags": ["symbol_easy"]},
        {"test_id": "p22-002", "repo_id": "p22-mini", "query": "timeout_ms config", "public_version": "0", "source": "p22_self_test", "task_bucket": "positive", "task_risk_tags": ["config"]},
        {"test_id": "p22-003", "repo_id": "p22-mini", "query": "beta_route_handler", "public_version": "0", "source": "p22_self_test", "task_bucket": "positive", "task_risk_tags": ["multi_symbol"]},
        {"test_id": "p22-004", "repo_id": "p22-mini", "query": "quantum payment mesh", "public_version": "0", "source": "p22_self_test", "task_bucket": "negative", "task_risk_tags": ["false_positive"]},
        {"test_id": "p22-005", "repo_id": "p22-mini", "query": "nonexistent_bogus_symbol", "public_version": "0", "source": "p22_self_test", "task_bucket": "negative", "task_risk_tags": ["abstain"]},
        {"test_id": "p22-006", "repo_id": "p22-mini", "query": "assert alpha_lookup test", "public_version": "0", "source": "p22_self_test", "task_bucket": "positive", "task_risk_tags": ["test_source"]},
    ]
    label_rows = [
        {"test_id": "p22-001", "repo_id": "p22-mini", "query": "alpha_lookup", "expected_behavior": "primary_evidence", "source_category": "positive", "oracle_type": "deterministic", "risk_tags": ["symbol_easy"], "gold_spans": [{"path": "src/lib.py", "start_line": 2, "end_line": 3}], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "p22-002", "repo_id": "p22-mini", "query": "timeout_ms config", "expected_behavior": "primary_evidence", "source_category": "config_key", "oracle_type": "deterministic", "risk_tags": ["config"], "gold_spans": [{"path": "config/service.yaml", "start_line": 2, "end_line": 2}], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "p22-003", "repo_id": "p22-mini", "query": "beta_route_handler", "expected_behavior": "primary_evidence", "source_category": "positive", "oracle_type": "deterministic", "risk_tags": ["multi_symbol"], "gold_spans": [{"path": "src/lib.py", "start_line": 5, "end_line": 6}], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "p22-004", "repo_id": "p22-mini", "query": "quantum payment mesh", "expected_behavior": "no_primary", "source_category": "negative_nonexistent", "oracle_type": "deterministic", "risk_tags": ["false_positive"], "gold_spans": [], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "p22-005", "repo_id": "p22-mini", "query": "nonexistent_bogus_symbol", "expected_behavior": "abstain", "source_category": "negative_nonexistent", "oracle_type": "deterministic", "risk_tags": ["abstain"], "gold_spans": [], "hard_distractors": [], "must_not_primary": []},
        {"test_id": "p22-006", "repo_id": "p22-mini", "query": "assert alpha_lookup test", "expected_behavior": "primary_evidence", "source_category": "test_source", "oracle_type": "deterministic", "risk_tags": ["test_source"], "gold_spans": [{"path": "tests/test_lib.py", "start_line": 2, "end_line": 2}], "hard_distractors": [], "must_not_primary": []},
    ]

    tasks_path.write_text("".join(json.dumps(row) + "\n" for row in task_rows), encoding="utf-8")
    labels_path.write_text("".join(json.dumps(row) + "\n" for row in label_rows), encoding="utf-8")
    return repo_lock, tasks_path, labels_path, {"p22-mini": repo}


def load_inputs(args: argparse.Namespace) -> tuple[tempfile.TemporaryDirectory[str] | None, Path, Path, Path, list[dict[str, Any]], dict[str, Path], list[dict[str, Any]]]:
    """Return tmp_ctx, repo_lock_path, tasks_path, labels_path, tasks, repo_roots, repo_lock_rows."""
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-p22-p23-")
        repo_lock, tasks_path, labels_path, repo_roots = make_self_test_inputs(Path(tmp_ctx.name))
    else:
        tmp_ctx = None
        repo_lock = args.repo_lock
        tasks_path = args.tasks
        labels_path = args.labels
        if not repo_lock.exists():
            raise SystemExit(f"repo-lock not found: {repo_lock}; use --self-test or provide a valid repo-lock")
        if not tasks_path.exists():
            raise SystemExit(f"tasks file not found: {tasks_path}; use --self-test or provide a valid tasks file")
        if not labels_path.exists():
            raise SystemExit(f"labels file not found: {labels_path}; use --self-test or provide a valid labels file")
        repo_roots = r32.load_repo_lock(repo_lock)

    raw_tasks = r32.load_jsonl(tasks_path)
    tasks = sanitize_public_tasks(raw_tasks)
    issues = r32.validate_public_tasks(tasks)
    if issues:
        raise SystemExit("public task validation failed after P22 sanitization: " + "; ".join(issues[:5]))

    repo_lock_rows = load_repo_lock_rows(repo_lock)
    repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
    tasks = [task for task in tasks if task["repo_id"] in repo_roots]
    tasks = sample_tasks(tasks, args.max_tasks, args.task_sample_mode)

    return tmp_ctx, repo_lock, tasks_path, labels_path, tasks, repo_roots, repo_lock_rows


def _evidence_key(ev: dict[str, Any]) -> str:
    return f"{ev.get('path', '')}:{ev.get('start_line', 0)}:{ev.get('end_line', 0)}"


def _top_k_evidence(raw: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Return top-k evidence marked as candidate-only."""
    out: list[dict[str, Any]] = []
    for ev in raw[:top_k]:
        ev = dict(ev)
        ev.setdefault("why", []).append("P22/P23 candidate_not_fact")
        ev.setdefault("channels", [])
        if "p22_candidate" not in ev["channels"]:
            ev["channels"] = ev["channels"] + ["p22_candidate"]
        meta = dict(ev.get("meta") or {})
        meta.update({"candidate_not_fact": True, "not_evidence_until_materialized": True, "p22_source": "local_deterministic"})
        ev["meta"] = meta
        out.append(ev)
    return out


def run_base_predictions(
    tasks: list[dict[str, Any]],
    repo_roots: dict[str, Path],
    openlocus: Path,
    top_k: int,
) -> dict[str, list[dict[str, Any]]]:
    """RUN phase: local deterministic strategies, no labels."""
    predictions: dict[str, list[dict[str, Any]]] = {method: [] for method in BASE_STRATEGIES}
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task["repo_id"]
        query = task["query"]
        root = repo_roots.get(repo_id)
        if not root:
            for method in BASE_STRATEGIES:
                predictions[method].append({
                    "task_id": tid,
                    "repo_id": repo_id,
                    "strategy": method,
                    "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "evidence": [],
                    "latency_ms": 0,
                    "returncode": -1,
                })
            continue

        base_evidence: dict[str, list[dict[str, Any]]] = {}
        for method in BASE_STRATEGIES:
            result = p20.run_strategy_query(method, query, root, openlocus, top_k)
            evidence = _top_k_evidence(result.get("evidence", []), top_k)
            base_evidence[method] = evidence
            predictions[method].append({
                "task_id": tid,
                "repo_id": repo_id,
                "strategy": method,
                "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "evidence": evidence,
                "latency_ms": int(result.get("latency_ms", 0)),
                "returncode": int(result.get("returncode", 0)),
            })
    return predictions


def build_composite_predictions(
    base_predictions: dict[str, list[dict[str, Any]]],
    tasks: list[dict[str, Any]],
    top_k: int,
) -> dict[str, list[dict[str, Any]]]:
    """Build symbol_regex_union and rrf_guarded_by_symbol_regex from base predictions."""
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for method in BASE_STRATEGIES:
        for pred in base_predictions[method]:
            by_task[str(pred["task_id"])][method] = pred

    composites: dict[str, list[dict[str, Any]]] = {name: [] for name in COMPOSITE_STRATEGIES}
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id") or "?"
        repo_id = task["repo_id"]
        query = task["query"]
        preds = by_task.get(tid, {})

        # symbol_regex_union: fuse symbol and regex via RRF.
        symbol_ev = {"evidence": list(preds.get("symbol", {}).get("evidence", []))}
        regex_ev = {"evidence": list(preds.get("regex", {}).get("evidence", []))}
        union_ev = r29.rrf_fuse_predictions(symbol_ev, regex_ev, k=60)[:top_k]
        union_ev = _top_k_evidence(union_ev, top_k)
        composites["symbol_regex_union"].append({
            "task_id": tid,
            "repo_id": repo_id,
            "strategy": "symbol_regex_union",
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "evidence": union_ev,
            "latency_ms": 0,
            "returncode": 0,
        })

        # rrf_guarded_by_symbol_regex: admission proxy.
        # Abstain on noisy/vague queries and when both symbol and regex are empty.
        rrf_ev = list(preds.get("rrf", {}).get("evidence", []))
        symbol_empty = not preds.get("symbol", {}).get("evidence", [])
        regex_empty = not preds.get("regex", {}).get("evidence", [])
        noise = (
            r29.is_negative_noise_query(query)
            or r29.is_vague_multi_word_query(query)
            or r29.is_compound_snake_case_noise(query)
        )
        if noise or (symbol_empty and regex_empty):
            guarded_ev: list[dict[str, Any]] = []
        else:
            guarded_ev = _top_k_evidence(rrf_ev, top_k)
        composites["rrf_guarded_by_symbol_regex"].append({
            "task_id": tid,
            "repo_id": repo_id,
            "strategy": "rrf_guarded_by_symbol_regex",
            "query_sha": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "evidence": guarded_ev,
            "latency_ms": 0,
            "returncode": 0,
        })

    return composites


def _evidence_overlaps_span(ev: dict[str, Any], span: dict[str, Any]) -> bool:
    return (
        ev.get("path") == span.get("path")
        and int(ev.get("end_line", 0)) >= int(span.get("start_line", 0))
        and int(ev.get("start_line", 0)) <= int(span.get("end_line", 0))
    )


def _path_in_gold(evidence: list[dict[str, Any]], gold_paths: set[str]) -> bool:
    return any(ev.get("path") in gold_paths for ev in evidence)


def _span_overlap_in_topk(evidence: list[dict[str, Any]], gold_spans: list[dict[str, Any]]) -> bool:
    return any(_evidence_overlaps_span(ev, span) for ev in evidence for span in gold_spans)


def _citation_validity(
    predictions: list[dict[str, Any]],
    repo_roots: dict[str, Path],
) -> float:
    total = 0
    valid = 0
    for pred in predictions:
        root = repo_roots.get(pred["repo_id"])
        if not root:
            continue
        for ev in pred.get("evidence", []):
            total += 1
            path = ev.get("path", "")
            start = int(ev.get("start_line", 0))
            end = int(ev.get("end_line", 0))
            if not path or start < 1 or start > end:
                continue
            full = root / path
            if not full.exists() or not full.is_file():
                continue
            try:
                lines = full.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            if end > len(lines):
                continue
            valid += 1
    return valid / total if total else 1.0


def _bucket_key(task: dict[str, Any], label: dict[str, Any] | None) -> str:
    bucket = task.get("task_bucket")
    tags = task.get("task_risk_tags")
    if isinstance(bucket, str) and isinstance(tags, list) and tags:
        return f"{bucket}:{tags[0]}"
    if isinstance(bucket, str):
        return bucket
    if label:
        # Do not write label-derived category strings to artifacts. Historical
        # fixtures can contain private/source-quality fields; aggregate them
        # under an opaque private-label bucket instead.
        return "label_private_bucket"
    return "unknown"


def score_all_strategies(
    predictions_by_strategy: dict[str, list[dict[str, Any]]],
    labels: dict[str, dict[str, Any]],
    repo_roots: dict[str, Path],
    tasks: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    task_ids = [str(task.get("test_id") or task.get("task_id")) for task in tasks]

    for strategy, preds in predictions_by_strategy.items():
        preds = [p for p in preds if str(p["task_id"]) in task_ids]
        total = len(preds)
        positives = 0
        no_gold = 0
        no_gold_nonempty = 0
        candidate_absent = 0
        file_wrong = 0
        file_right_span_wrong = 0
        gold_file_present_span_absent = 0

        candidate_gold_file_reach = {1: 0, 5: 0, 10: 0}
        candidate_gold_span_reach = {1: 0, 5: 0, 10: 0}

        per_bucket: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "task_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "no_gold_false_primary_count": 0,
            "candidate_absent_count": 0,
            "file_wrong_count": 0,
            "file_right_span_wrong_count": 0,
        })

        for pred in preds:
            label = labels.get(pred["task_id"], {})
            task = next((t for t in tasks if str(t.get("test_id") or t.get("task_id")) == pred["task_id"]), {})
            evidence = pred.get("evidence", [])[:top_k]
            gold_spans = label.get("gold_spans") or []
            gold_paths = {span["path"] for span in gold_spans}
            bucket = _bucket_key(task, label)
            bucket_stats = per_bucket[bucket]
            bucket_stats["task_count"] += 1

            if gold_spans:
                positives += 1
                bucket_stats["positive_task_count"] += 1
                for k in (1, 5, 10):
                    ev_k = evidence[:k]
                    if _path_in_gold(ev_k, gold_paths):
                        candidate_gold_file_reach[k] += 1
                        if _span_overlap_in_topk(ev_k, gold_spans):
                            candidate_gold_span_reach[k] += 1
                    elif k > 1 and _path_in_gold(evidence[:k], gold_paths):
                        # file reach at k can be true even if span reach false
                        pass

                if not _path_in_gold(evidence, gold_paths):
                    candidate_absent += 1
                    bucket_stats["candidate_absent_count"] += 1
                elif not _span_overlap_in_topk(evidence, gold_spans):
                    gold_file_present_span_absent += 1

                if evidence and evidence[0].get("path") not in gold_paths:
                    file_wrong += 1
                    bucket_stats["file_wrong_count"] += 1
                elif evidence and evidence[0].get("path") in gold_paths and not _span_overlap_in_topk(evidence[:1], gold_spans):
                    file_right_span_wrong += 1
                    bucket_stats["file_right_span_wrong_count"] += 1
            else:
                no_gold += 1
                bucket_stats["no_gold_task_count"] += 1
                if evidence:
                    no_gold_nonempty += 1
                    bucket_stats["no_gold_false_primary_count"] += 1

        metrics = {
            "task_count": total,
            "positive_task_count": positives,
            "no_gold_task_count": no_gold,
            "candidate_gold_file_reach@1": candidate_gold_file_reach[1] / positives if positives else 0.0,
            "candidate_gold_file_reach@5": candidate_gold_file_reach[5] / positives if positives else 0.0,
            "candidate_gold_file_reach@10": candidate_gold_file_reach[10] / positives if positives else 0.0,
            "candidate_gold_span_reach@1": candidate_gold_span_reach[1] / positives if positives else 0.0,
            "candidate_gold_span_reach@5": candidate_gold_span_reach[5] / positives if positives else 0.0,
            "candidate_gold_span_reach@10": candidate_gold_span_reach[10] / positives if positives else 0.0,
            "candidate_absent_rate": candidate_absent / positives if positives else 0.0,
            "file_wrong_rate": file_wrong / positives if positives else 0.0,
            "file_right_span_wrong_rate": file_right_span_wrong / positives if positives else 0.0,
            "gold_file_present_span_absent_rate": gold_file_present_span_absent / positives if positives else 0.0,
            "no_gold_false_primary_rate": no_gold_nonempty / no_gold if no_gold else 0.0,
            "abstain_rate": sum(1 for p in preds if not p.get("evidence")) / total if total else 0.0,
            "citation_validity": _citation_validity(preds, repo_roots),
        }

        # Standard FileRecall/MRR/SpanF0.5 if easy.
        if positives:
            metrics["FileRecall@1"] = score_mod.file_recall_at_k(preds, labels, 1)
            metrics["FileRecall@5"] = score_mod.file_recall_at_k(preds, labels, 5)
            metrics["MRR"] = score_mod.mrr(preds, labels)
            metrics["SpanF0.5"] = score_mod.span_f_beta_at_k(preds, labels, top_k, 0.5)

        # Per-bucket aggregates (no raw spans or queries).
        bucket_metrics: dict[str, Any] = {}
        for bucket, stats in sorted(per_bucket.items()):
            bucket_metrics[bucket] = {
                "task_count": stats["task_count"],
                "positive_task_count": stats["positive_task_count"],
                "no_gold_task_count": stats["no_gold_task_count"],
                "no_gold_false_primary_count": stats["no_gold_false_primary_count"],
                "candidate_absent_count": stats["candidate_absent_count"],
                "file_wrong_count": stats["file_wrong_count"],
                "file_right_span_wrong_count": stats["file_right_span_wrong_count"],
            }
            if stats["positive_task_count"]:
                bucket_preds = [p for p in preds if str(p["task_id"]) in labels and labels[str(p["task_id"])].get("gold_spans") and _bucket_key(next((t for t in tasks if str(t.get("test_id") or t.get("task_id")) == p["task_id"]), {}), labels.get(str(p["task_id"]))) == bucket]
                if bucket_preds:
                    bucket_metrics[bucket]["FileRecall@5"] = score_mod.file_recall_at_k(bucket_preds, labels, 5)
                    bucket_metrics[bucket]["SpanF0.5"] = score_mod.span_f_beta_at_k(bucket_preds, labels, top_k, 0.5)

        results[strategy] = {
            "status": "ok",
            "metrics": metrics,
            "per_bucket": bucket_metrics,
        }

    return results


def build_bottleneck_summary(results: dict[str, Any]) -> dict[str, Any]:
    ok_strategies = {s: r for s, r in results.items() if r.get("status") == "ok"}
    if not ok_strategies:
        return {
            "best_candidate_reach_strategy": None,
            "highest_no_gold_false_primary_strategy": None,
            "research_baseline_candidate_for_p25_p30": None,
            "note": "No strategies produced usable predictions.",
        }

    total_positive = max(int(r["metrics"].get("positive_task_count", 0)) for r in ok_strategies.values())
    total_no_gold = max(int(r["metrics"].get("no_gold_task_count", 0)) for r in ok_strategies.values())

    best_reach = None
    if total_positive:
        best_reach = max(
            ok_strategies,
            key=lambda s: ok_strategies[s]["metrics"].get("candidate_gold_file_reach@5", 0.0),
        )
    max_fp = max(float(r["metrics"].get("no_gold_false_primary_rate", 0.0)) for r in ok_strategies.values())
    highest_fp = None
    if total_no_gold and max_fp > 0:
        highest_fp = max(
            ok_strategies,
            key=lambda s: ok_strategies[s]["metrics"].get("no_gold_false_primary_rate", 0.0),
        )

    guard_preference = {
        "rrf_guarded_by_symbol_regex": 6,
        "symbol_regex_union": 5,
        "symbol": 4,
        "regex": 3,
        "rrf": 2,
        "bm25": 1,
    }

    # Recommend candidate with best combined reach and low false-primary on no-gold tasks.
    def score(s: str) -> float:
        m = ok_strategies[s]["metrics"]
        return (
            m.get("candidate_gold_file_reach@5", 0.0)
            + m.get("candidate_gold_span_reach@5", 0.0)
            - m.get("no_gold_false_primary_rate", 0.0)
            - m.get("file_wrong_rate", 0.0)
        )

    if total_positive:
        recommended = max(ok_strategies, key=score)
        surface_type = "mixed_positive_no_gold" if total_no_gold else "positive_only"
    else:
        recommended = min(
            ok_strategies,
            key=lambda s: (
                ok_strategies[s]["metrics"].get("no_gold_false_primary_rate", 0.0),
                -guard_preference.get(s, 0),
            ),
        )
        surface_type = "guard_only_no_gold"
    return {
        "surface_type": surface_type,
        "best_candidate_reach_strategy": best_reach,
        "highest_no_gold_false_primary_strategy": highest_fp,
        "research_baseline_candidate_for_p25_p30": recommended,
        "note": (
            "P22/P23 are research-only; none of these local deterministic strategies "
            "should change defaults. Use RRF as the recall reference and "
            "research_baseline_candidate_for_p25_p30 only as a research baseline candidate for "
            "P25 admission/filter refinements and P30 guard experiments."
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    tmp_ctx, repo_lock_path, tasks_path, labels_path, tasks, repo_roots, repo_lock_rows = load_inputs(args)
    try:
        # RUN phase: predictions from local strategies only, before labels are loaded.
        base_preds = run_base_predictions(tasks, repo_roots, args.openlocus, args.top_k)
        composite_preds = build_composite_predictions(base_preds, tasks, args.top_k)
        all_preds = {**base_preds, **composite_preds}

        # SCORE phase: private labels are loaded only after predictions exist.
        labels = r32.normalize_labels(r32.load_jsonl(labels_path))
        elapsed_ms = int((time.time() - started) * 1000)

        strategy_results = score_all_strategies(all_preds, labels, repo_roots, tasks, args.top_k)
        surface = build_decision_surface(
            repo_lock_path, tasks_path, labels_path, repo_lock_rows, repo_roots, tasks, elapsed_ms, args.self_test
        )
        summary = build_bottleneck_summary(strategy_results)

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "stage": "P22/P23 evidence-seeking policy surface and bottleneck decomposition",
            "promotion_ready": False,
            "default_should_change": False,
            "evidencecore_semantics_changed": False,
            "core_changes": False,
            "run_phase_public_only": True,
            "run_phase_task_fields": sorted({key for task in tasks for key in task.keys()}),
            "legacy_task_rows_sanitized": True,
            "labels_loaded_after_run": True,
            "external_calls": 0,
            "decision_surface": surface,
            "strategy_results": strategy_results,
            "bottleneck_summary": summary,
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P22/P23 Evidence-Seeking Retrieval Policy Surface",
        "",
        "P22 freezes the decision surface of the current evidence-seeking retrieval policy. "
        "P23 decomposes local candidate strategy failures into actionable bottleneck categories.",
        "",
        "## Safety / Policy",
        "",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        f"- core_changes: `{report.get('core_changes')}`",
        f"- external_calls: `{report.get('external_calls')}`",
        "",
        "## P22 Decision Surface Freeze",
        "",
        f"- schema_version: `{report.get('schema_version')}`",
        f"- tasks_scored: `{report.get('decision_surface', {}).get('task_count_scored')}`",
        f"- repos_available: `{report.get('decision_surface', {}).get('available_repo_count')} / {report.get('decision_surface', {}).get('repo_count_loaded')}`",
        "",
        "### Input Hashes",
        "",
        "| Input | SHA256 |",
        "|---|---|",
    ]
    for label, sha in (report.get("decision_surface", {}).get("input_hashes") or {}).items():
        lines.append(f"| {label} | `{sha or 'missing'}` |")

    lines += [
        "",
        "## P23 Bottleneck Decomposition",
        "",
        "| Strategy | Pos | NoGold | Reach@5 | SpanReach@5 | Absent | FileWrong | FRSW | NoGoldFP | Abstain | FileRec@5 | SpanF0.5 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, payload in report.get("strategy_results", {}).items():
        m = payload.get("metrics", {})
        lines.append(
            f"| {strategy} | {m.get('positive_task_count')} | {m.get('no_gold_task_count')} | "
            f"{m.get('candidate_gold_file_reach@5')} | {m.get('candidate_gold_span_reach@5')} | "
            f"{m.get('candidate_absent_rate')} | {m.get('file_wrong_rate')} | {m.get('file_right_span_wrong_rate')} | "
            f"{m.get('no_gold_false_primary_rate')} | {m.get('abstain_rate')} | {m.get('FileRecall@5')} | {m.get('SpanF0.5')} |"
        )

    lines += [
        "",
        "## Bottleneck Summary",
        "",
        f"- surface_type: `{report.get('bottleneck_summary', {}).get('surface_type')}`",
        f"- best_candidate_reach_strategy: `{report.get('bottleneck_summary', {}).get('best_candidate_reach_strategy')}`",
        f"- highest_no_gold_false_primary_strategy: `{report.get('bottleneck_summary', {}).get('highest_no_gold_false_primary_strategy')}`",
        f"- research_baseline_candidate_for_p25_p30: `{report.get('bottleneck_summary', {}).get('research_baseline_candidate_for_p25_p30')}`",
        "",
        f"{report.get('bottleneck_summary', {}).get('note', '')}",
        "",
        "## Next Steps for P25/P30",
        "",
        "1. Use the research baseline candidate only for P25/P30 experiments; it is not a default recommendation.",
        "2. Target the highest observed failure bucket (candidate_absent, file_wrong, or file_right_span_wrong) with source-category-specific guards.",
        "3. Re-run after any EvidenceCore or retrieval change to refresh the P22 surface manifest.",
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
    parser.add_argument("--max-tasks", type=int, default=120)
    parser.add_argument("--task-sample-mode", default="prefix", choices=["prefix", "round_robin_public_buckets"])
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/p22_p23/policy_surface_full_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/en/p22-p23-policy-surface.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()

    report = run(args)
    write_json(args.out, report)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
