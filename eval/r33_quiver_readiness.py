#!/usr/bin/env python3
"""R33 QuIVer readiness diagnostics.

R33 does not implement QuIVer graph search and does not emit QuIVer quality
numbers.  It measures whether the current embedding distribution looks suitable
for a future BQ/Vamana-style candidate backend by comparing float32 cosine
neighbors with a simple 2-bit sign+magnitude binary quantization diagnostic.

Default mode is an offline self-test using R32's local token-hash embeddings.
Real OpenAI-compatible embeddings require explicit `--allow-remote` and are
restricted by R32's remote safety rules.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
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


SCHEMA_VERSION = "r33-quiver-readiness-v1"
DEFAULT_VIEWS = ["path_plus_symbol", "signature_plus_doc", "raw_code_trimmed", "mixed_all_views"]
OVERLAP_KS = [10, 50, 100]


@dataclass
class DiagnosticPoint:
    repo_id: str
    view: str
    language: str
    vector: list[float]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) if len(a) == len(b) else 0.0


def norm(a: list[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def cosine(a: list[float], b: list[float]) -> float:
    na = norm(a)
    nb = norm(b)
    if not na or not nb or len(a) != len(b):
        return 0.0
    return dot(a, b) / (na * nb)


def angle_between(a: list[float], b: list[float]) -> float:
    c = max(-1.0, min(1.0, cosine(a, b)))
    return math.acos(c) / math.pi


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dims = len(vectors[0])
    out = [0.0] * dims
    for vec in vectors:
        for i, value in enumerate(vec[:dims]):
            out[i] += value
    return [value / len(vectors) for value in out]


def dimension_thresholds(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dims = len(vectors[0])
    thresholds = []
    for i in range(dims):
        thresholds.append(statistics.mean(abs(vec[i]) for vec in vectors if len(vec) > i))
    return thresholds


def bq2_encode(vec: list[float], thresholds: list[float]) -> tuple[tuple[int, int], ...]:
    bits: list[tuple[int, int]] = []
    for i, value in enumerate(vec):
        threshold = thresholds[i] if i < len(thresholds) else 0.0
        sign = 1 if value >= 0 else 0
        mag = 1 if abs(value) >= threshold else 0
        bits.append((sign, mag))
    return tuple(bits)


def bq2_distance(a: tuple[tuple[int, int], ...], b: tuple[tuple[int, int], ...]) -> int:
    total = 0
    for (asign, amag), (bsign, bmag) in zip(a, b):
        total += 2 if asign != bsign else 0
        total += 1 if amag != bmag else 0
    return total


def sign_entropy(vectors: list[list[float]]) -> dict[str, float]:
    if not vectors:
        return {"mean": 0.0, "std": 0.0}
    dims = len(vectors[0])
    entropies = []
    for i in range(dims):
        positives = sum(1 for vec in vectors if len(vec) > i and vec[i] >= 0)
        p = positives / len(vectors)
        if p in {0.0, 1.0}:
            entropies.append(0.0)
        else:
            entropies.append(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))
    return {
        "mean": statistics.mean(entropies) if entropies else 0.0,
        "std": statistics.pstdev(entropies) if len(entropies) > 1 else 0.0,
    }


def effective_dimension_proxy(vectors: list[list[float]]) -> float:
    if len(vectors) < 2:
        return 0.0
    dims = len(vectors[0])
    variances = []
    for i in range(dims):
        values = [vec[i] for vec in vectors if len(vec) > i]
        variances.append(statistics.pvariance(values) if len(values) > 1 else 0.0)
    numerator = sum(variances) ** 2
    denominator = sum(v * v for v in variances)
    return numerator / denominator if denominator else 0.0


def centroid_variance(points: list[DiagnosticPoint], key: str) -> float:
    groups: dict[str, list[list[float]]] = defaultdict(list)
    for point in points:
        groups[getattr(point, key) or "unknown"].append(point.vector)
    centroids = [mean_vector(vectors) for vectors in groups.values() if vectors]
    if len(centroids) < 2:
        return 0.0
    global_centroid = mean_vector([point.vector for point in points])
    return statistics.mean(angle_between(global_centroid, centroid) for centroid in centroids)


def top_indices_by_cosine(query: list[float], corpus: list[list[float]], k: int) -> list[int]:
    scored = sorted(((cosine(query, vec), i) for i, vec in enumerate(corpus)), reverse=True)
    return [i for _, i in scored[: min(k, len(scored))]]


def top_indices_by_bq(query_bq: tuple[tuple[int, int], ...], corpus_bq: list[tuple[tuple[int, int], ...]], k: int) -> list[int]:
    scored = sorted((bq2_distance(query_bq, encoded), i) for i, encoded in enumerate(corpus_bq))
    return [i for _, i in scored[: min(k, len(scored))]]


def bq_diagnostics(query_vectors: list[list[float]], points: list[DiagnosticPoint]) -> dict[str, Any]:
    corpus = [point.vector for point in points if point.vector]
    if not corpus or not query_vectors:
        return {
            "status": "insufficient_vectors",
            "BQ_overlap@10": None,
            "BQ_overlap@50": None,
            "BQ_overlap@100": None,
        }
    thresholds = dimension_thresholds(corpus)
    corpus_bq = [bq2_encode(vec, thresholds) for vec in corpus]
    overlaps: dict[int, list[float]] = {k: [] for k in OVERLAP_KS}
    reciprocal_ranks: list[float] = []
    angular_gaps: dict[int, list[float]] = {10: [], 50: []}
    for query in query_vectors:
        query_bq = bq2_encode(query, thresholds)
        f32_top_full = top_indices_by_cosine(query, corpus, min(100, len(corpus)))
        bq_top_full = top_indices_by_bq(query_bq, corpus_bq, min(100, len(corpus)))
        for k in OVERLAP_KS:
            denom = min(k, len(corpus))
            if denom:
                overlaps[k].append(len(set(f32_top_full[:denom]) & set(bq_top_full[:denom])) / denom)
        if f32_top_full:
            f32_best = f32_top_full[0]
            try:
                reciprocal_ranks.append(1.0 / (bq_top_full.index(f32_best) + 1))
            except ValueError:
                reciprocal_ranks.append(0.0)
            for k in [10, 50]:
                top = f32_top_full[: min(k, len(f32_top_full))]
                if top:
                    best_score = cosine(query, corpus[top[0]])
                    kth_score = cosine(query, corpus[top[-1]])
                    angular_gaps[k].append(max(0.0, best_score - kth_score))

    sign = sign_entropy(corpus)
    corpus_centroid = mean_vector(corpus)
    query_centroid = mean_vector(query_vectors)
    overlap10 = statistics.mean(overlaps[10]) if overlaps[10] else 0.0
    overlap100 = statistics.mean(overlaps[100]) if overlaps[100] else overlap10
    entropy_score = sign["mean"]
    fit_score = (overlap100 + entropy_score) / 2
    if fit_score >= 0.70:
        quiver_fit = "promising"
        recommendation = "test_sharded_quiver"
    elif fit_score >= 0.45:
        quiver_fit = "mixed"
        recommendation = "continue_diagnostics_then_proto"
    else:
        quiver_fit = "weak"
        recommendation = "hold_graph_proto_until_embedding_or_sharding_improves"

    return {
        "status": "ok",
        "BQ_overlap@10": statistics.mean(overlaps[10]) if overlaps[10] else 0.0,
        "BQ_overlap@50": statistics.mean(overlaps[50]) if overlaps[50] else 0.0,
        "BQ_overlap@100": overlap100,
        "BQ_vs_f32_MRR": statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "sign_entropy_mean": sign["mean"],
        "sign_entropy_std": sign["std"],
        "angular_gap@10": statistics.mean(angular_gaps[10]) if angular_gaps[10] else 0.0,
        "angular_gap@50": statistics.mean(angular_gaps[50]) if angular_gaps[50] else 0.0,
        "query_corpus_centroid_angle": angle_between(query_centroid, corpus_centroid),
        "language_shard_variance": centroid_variance(points, "language"),
        "view_shard_variance": centroid_variance(points, "view"),
        "effective_dimension_proxy": effective_dimension_proxy(corpus),
        "quiver_fit": quiver_fit,
        "recommendation": recommendation,
    }


def build_points(args: argparse.Namespace) -> tuple[list[DiagnosticPoint], list[dict[str, Any]], dict[str, Any]]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r33-")
        repo_lock, tasks_path, _labels_path, self_repo_roots = r32.make_self_test_inputs(Path(tmp_ctx.name))
    else:
        tmp_ctx = None
        repo_lock, tasks_path, self_repo_roots = args.repo_lock, args.tasks, {}
    try:
        repo_roots = self_repo_roots or r32.load_repo_lock(repo_lock)
        repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
        tasks = [task for task in r32.load_jsonl(tasks_path) if task["repo_id"] in repo_roots]
        public_issues = r32.validate_public_tasks(tasks)
        if public_issues:
            raise SystemExit("public task validation failed: " + "; ".join(public_issues[:5]))
        views = [v.strip() for v in args.views.split(",") if v.strip()]
        unknown = [view for view in views if view not in r32.DEFAULT_VIEWS]
        if unknown:
            raise SystemExit(f"unknown R33 views: {unknown}")
        all_records: list[r32.ViewRecord] = []
        for repo_id, root in repo_roots.items():
            scan_map = r32.run_scan(args.openlocus, root)
            for file_path in r32.iter_source_files(root, args.max_files_per_repo):
                rel = str(file_path.relative_to(root)).replace("\\", "/")
                built = r32.build_views_for_file(repo_id, root, file_path, scan_map.get(rel))
                for view in views:
                    all_records.extend(built.get(view, [])[: args.max_records_per_file])
        if args.provider == "openai-compatible" and any(record.view_kind not in r32.REMOTE_SAFE_VIEWS for record in all_records):
            return [], tasks, {
                "status": "unavailable",
                "reason": "remote R33 is restricted to data-level-0 path_plus_symbol views",
            }
        embed_status = r32.embed_records(all_records[: args.max_records], args.provider, args.allow_remote)
        if embed_status.get("status") != "ok":
            return [], tasks, {"status": "unavailable", "reason": embed_status.get("reason")}
        points = [
            DiagnosticPoint(record.repo_id, record.view_kind, record.language, record.vector or [])
            for record in all_records[: args.max_records]
            if record.vector
        ]
        return points, tasks[: args.max_queries], {"status": "ok", "repo_count": len(repo_roots), "record_count": len(points), "embed_status": embed_status}
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def query_vectors(tasks: list[dict[str, Any]], provider: str, allow_remote: bool) -> tuple[list[list[float]], dict[str, Any]]:
    queries = [task["query"] for task in tasks]
    if provider == "local_token_hash":
        return [r32.token_hash_embedding(f"query {query}") for query in queries], {"remote_calls": 0, "status": "ok"}
    if not allow_remote:
        return [], {"remote_calls": 0, "status": "unavailable", "reason": "requires --allow-remote"}
    if any(r32.text_has_secret(query) for query in queries):
        return [], {"remote_calls": 0, "status": "unavailable", "reason": "query blocked by secret scan"}
    try:
        return r32.remote_embed([f"query {query}" for query in queries]), {"remote_calls": len(queries), "status": "ok"}
    except Exception:
        return [], {"remote_calls": 0, "status": "unavailable", "reason": "remote embedding provider unavailable_or_failed"}


def run_readiness(args: argparse.Namespace) -> dict[str, Any]:
    start = time.time()
    points, tasks, point_status = build_points(args)
    if point_status.get("status") != "ok":
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": args.provider,
            **r32.embedding_model_metadata(args.provider),
            "provider_status": "unavailable",
            "unavailable_reason": point_status.get("reason"),
            "quiver_graph_implemented": False,
            "BQ_diagnostics_only": True,
            "quiver_quality_metrics_emitted": False,
            "promotion_ready": False,
            "default_should_change": False,
            "evidencecore_semantics_changed": False,
        }
    qvectors, query_status = query_vectors(tasks, args.provider, args.allow_remote)
    if query_status.get("status") != "ok":
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": args.provider,
            **r32.embedding_model_metadata(args.provider),
            "provider_status": "unavailable",
            "unavailable_reason": query_status.get("reason"),
            "quiver_graph_implemented": False,
            "BQ_diagnostics_only": True,
            "quiver_quality_metrics_emitted": False,
            "promotion_ready": False,
            "default_should_change": False,
            "evidencecore_semantics_changed": False,
        }
    diagnostics = bq_diagnostics(qvectors, points)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        **r32.embedding_model_metadata(args.provider),
        "provider_status": "ok",
        "views": [v.strip() for v in args.views.split(",") if v.strip()],
        "repo_count": point_status.get("repo_count", 0),
        "record_count": point_status.get("record_count", 0),
        "query_count": len(qvectors),
        "remote_calls": int(point_status.get("embed_status", {}).get("remote_calls", 0)) + int(query_status.get("remote_calls", 0)),
        "elapsed_ms": int((time.time() - start) * 1000),
        "quiver_graph_implemented": False,
        "BQ_diagnostics_only": True,
        "quiver_quality_metrics_emitted": False,
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
        "diagnostics": diagnostics,
        "fit_summary": {
            "quiver_fit": diagnostics.get("quiver_fit"),
            "recommendation": diagnostics.get("recommendation"),
            "reason": "BQ overlap/sign-entropy diagnostic only; no Vamana graph or ANN quality measured",
        },
    }


def write_doc(report: dict[str, Any], path: Path) -> None:
    diag = report.get("diagnostics", {})
    lines = [
        "# R33 QuIVer Readiness",
        "",
        "R33 measures BQ2 readiness for future QuIVer research. It does **not** implement QuIVer graph search and does **not** emit QuIVer quality numbers.",
        "",
        "## Safety",
        "",
        f"- provider: `{report.get('provider')}`",
        f"- embedding_model: `{report.get('embedding_model')}`",
        f"- provider_status: `{report.get('provider_status')}`",
        f"- quiver_graph_implemented: `{report.get('quiver_graph_implemented')}`",
        f"- BQ_diagnostics_only: `{report.get('BQ_diagnostics_only')}`",
        f"- quiver_quality_metrics_emitted: `{report.get('quiver_quality_metrics_emitted')}`",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        "",
        "## BQ Diagnostics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in [
        "BQ_overlap@10",
        "BQ_overlap@50",
        "BQ_overlap@100",
        "BQ_vs_f32_MRR",
        "sign_entropy_mean",
        "sign_entropy_std",
        "angular_gap@10",
        "angular_gap@50",
        "query_corpus_centroid_angle",
        "language_shard_variance",
        "view_shard_variance",
        "effective_dimension_proxy",
    ]:
        lines.append(f"| {key} | {diag.get(key)} |")
    lines.extend([
        "",
        "## Recommendation",
        "",
        f"- quiver_fit: `{diag.get('quiver_fit')}`",
        f"- recommendation: `{diag.get('recommendation')}`",
        "- Next step remains R34 prototype only after diagnostics; unavailable graph search must stay reason-only.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    parser.add_argument("--provider", default="local_token_hash", choices=["local_token_hash", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-records", type=int, default=2000)
    parser.add_argument("--max-files-per-repo", type=int, default=None)
    parser.add_argument("--max-records-per-file", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=200)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/r33/quiver_readiness.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/en/r33-quiver-readiness.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()

    report = run_readiness(args)
    write_json(args.out, report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
