#!/usr/bin/env python3
"""R23 Guard Parameter Sweep — analysis-only score phase.

Consumes R21 artifacts (runs/r21-auto-wide-*-predictions.jsonl,
runs/r21-auto-wide-report.json) and R20 labels. Produces guard
parameter sweep with curves and bucket analysis. Does NOT re-run
retrieval.

Architecture: strictly analysis-only SCORE phase.
  - Loads predictions + labels + R21 report.
  - Never invokes openlocus CLI.
  - Never loads labels in a run phase; this is analysis-only.

Guard semantics:
  - Based on raw RRF evidence; if guard condition fails then abstain.
  - query_noise_threshold: deterministic score of vague/fabricated/misspell/noise tokens.
  - rrf_score_threshold: RRF top score must exceed threshold.
  - regex_agreement_required: regex predictions must have evidence.
  - symbol_agreement_required: symbol predictions must have evidence.
  - regex_or_symbol_agreement_required: regex OR symbol must have evidence.
  - top1_top2_gap_threshold: top1 score - top2 score must exceed gap.
  - identifier_density_threshold: query must have >= threshold identifier-like tokens.
  - candidate_channel_count_threshold: top evidence channels union must have >= threshold channels.

Safety:
  - promotion_ready=false, not_promotion_evidence=true always.
  - No promotion claims, no dense/LLM/QuIVer quality claims.
  - Labels only in score phase; never used for routing.
  - Artifacts manifest sha verified for path/sha/lines.
  - analysis-only no CLI.

Usage:
    python3 eval/r23_guard_sweep.py \\
        --workspace . \\
        --r21-report runs/r21-auto-wide-report.json \\
        --fixtures fixtures/r20_auto_wide \\
        --out runs/r23-guard-sweep.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Schema version ─────────────────────────────────────────────────────

SCHEMA_VERSION = "r23-v1"

# ── Query noise helpers (inlined from R21) ─────────────────────────────

NEGATIVE_NOISE_MARKERS = [
    "FIXME_bogus",
    "TODO_nonexistent",
    "HACK_impossible",
    "nonexistent",
    "imaginary",
    "fake",
    "does_not_exist",
    "bogus",
    "_bogus_",
    "_nonexistent_",
    "_impossible_",
]

COMMON_WORDS = {
    "function", "error", "handler", "configuration", "the", "return",
    "initialization", "serialization", "validation", "logging", "testing",
    "routing", "parsing", "buffering", "cleanup", "settings", "setup",
    "import", "dependencies", "module", "exports", "server", "route",
    "definitions", "types", "client", "connection", "builder", "pattern",
    "handling", "search", "implementation", "data", "storage", "api",
    "endpoint", "request", "management", "processing", "startup",
    "response", "event", "model", "interface",
}

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

CAMEL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
SNAKE_CASE_FUNC_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CONTAINS_DOUBLE_COLON = re.compile(r"::")
SYMBOL_ISH_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_:.]*$")


def is_negative_noise_query(query: str) -> bool:
    q = query.strip()
    for marker in NEGATIVE_NOISE_MARKERS:
        if marker.lower() in q.lower():
            return True
    if q.lower() in COMMON_WORDS:
        return True
    if UUID_PATTERN.match(q):
        return True
    return False


def is_vague_multi_word_query(query: str) -> bool:
    q = query.strip()
    if " " not in q:
        return False
    tokens = q.split()
    return all(token.lower() in COMMON_WORDS for token in tokens) and len(tokens) >= 2


def is_compound_snake_case_noise(query: str) -> bool:
    q = query.strip()
    if " " in q or "_" not in q:
        return False
    parts = [p for p in q.split("_") if p]
    noise_domain_keywords = {
        "quantum", "neural", "blockchain", "distributed", "machine",
        "cryptographic", "microservice", "training", "consensus", "replication",
        "inference", "rotation", "orchestration", "streaming", "pipeline",
        "protocol", "entanglement", "solver",
    }
    if len(parts) >= 3:
        noise_count = sum(1 for p in parts if p.lower() in noise_domain_keywords)
        if noise_count >= 1:
            return True
    return False


def query_noise_score(query: str) -> int:
    """Deterministic noise score: count of noise indicators (0 = clean, higher = noisier)."""
    score = 0
    q = query.strip()
    if is_negative_noise_query(q):
        score += 2
    if is_vague_multi_word_query(q):
        score += 2
    if is_compound_snake_case_noise(q):
        score += 1
    # Fabricated/misspell indicators
    for marker in NEGATIVE_NOISE_MARKERS:
        if marker.lower() in q.lower():
            score += 1
            break
    # Common word only
    tokens = q.split()
    if len(tokens) == 1 and tokens[0].lower() in COMMON_WORDS:
        score += 1
    # UUID
    if UUID_PATTERN.match(q):
        score += 1
    return score


def identifier_density(query: str) -> int:
    """Count identifier-like tokens in the query."""
    tokens = query.strip().split()
    count = 0
    for token in tokens:
        if SYMBOL_ISH_PATTERN.match(token) and not token.lower() in COMMON_WORDS:
            count += 1
    return count


def candidate_channel_count(rrf_pred: dict, regex_pred: dict | None, symbol_pred: dict | None) -> int:
    """Estimate channel diversity from top evidence channels union."""
    channels: set[str] = set()
    for e in rrf_pred.get("evidence", [])[:10]:
        for ch in e.get("channels", []):
            channels.add(ch)
    if regex_pred:
        for e in regex_pred.get("evidence", [])[:5]:
            for ch in e.get("channels", []):
                channels.add(ch)
    if symbol_pred:
        for e in symbol_pred.get("evidence", [])[:5]:
            for ch in e.get("channels", []):
                channels.add(ch)
    return len(channels)


# ── Data loading ──────────────────────────────────────────────────────


def load_jsonl(path: Path) -> list[dict]:
    results = []
    if not path.exists():
        return results
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        results.append(json.loads(line))
    return results


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def count_jsonl_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def verify_r21_artifact_manifest(runs_dir: Path) -> tuple[str, int]:
    """Fail-closed verification of all R21 artifact manifest entries."""
    manifest_path = runs_dir / "r21-auto-wide-artifacts-manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Artifact manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or not manifest:
        print("ERROR: Artifact manifest is empty or malformed", file=sys.stderr)
        sys.exit(1)

    issues: list[str] = []
    artifact_file_check_count = 0
    for strategy, artifacts in manifest.items():
        if not isinstance(artifacts, dict):
            issues.append(f"{strategy}: manifest entry must be an object")
            continue
        for artifact_kind, info in artifacts.items():
            artifact_file_check_count += 1
            if not isinstance(info, dict):
                issues.append(f"{strategy}.{artifact_kind}: manifest artifact must be an object")
                continue
            artifact_path_raw = info.get("path", "")
            if not isinstance(artifact_path_raw, str) or not artifact_path_raw:
                issues.append(f"{strategy}.{artifact_kind}: missing path")
                continue
            artifact_path = Path(artifact_path_raw)
            if not artifact_path.exists():
                issues.append(f"{strategy}.{artifact_kind}: missing artifact {artifact_path}")
                continue

            expected_sha = info.get("sha256")
            expected_bytes = info.get("bytes")
            expected_lines = info.get("jsonl_lines")
            if not isinstance(expected_sha, str) or not expected_sha:
                issues.append(f"{strategy}.{artifact_kind}: missing sha256")
            if not isinstance(expected_bytes, int):
                issues.append(f"{strategy}.{artifact_kind}: missing integer bytes")
            if not isinstance(expected_lines, int):
                issues.append(f"{strategy}.{artifact_kind}: missing integer jsonl_lines")

            actual_sha = sha256_of_file(artifact_path)
            actual_bytes = artifact_path.stat().st_size
            actual_lines = count_jsonl_lines(artifact_path)
            if isinstance(expected_sha, str) and expected_sha and actual_sha != expected_sha:
                issues.append(
                    f"{strategy}.{artifact_kind}: sha mismatch expected={expected_sha[:16]} actual={actual_sha[:16]}"
                )
            if isinstance(expected_bytes, int) and actual_bytes != expected_bytes:
                issues.append(
                    f"{strategy}.{artifact_kind}: byte count mismatch expected={expected_bytes} actual={actual_bytes}"
                )
            if isinstance(expected_lines, int) and actual_lines != expected_lines:
                issues.append(
                    f"{strategy}.{artifact_kind}: jsonl line count mismatch expected={expected_lines} actual={actual_lines}"
                )

    for strategy in ["rrf", "regex", "symbol"]:
        if strategy not in manifest:
            issues.append(f"{strategy}: missing manifest strategy entry")
            continue
        predictions_info = manifest[strategy].get("predictions")
        if not isinstance(predictions_info, dict):
            issues.append(f"{strategy}.predictions: missing manifest artifact")
            continue
        expected_path = (runs_dir / f"r21-auto-wide-{strategy}-predictions.jsonl").resolve()
        actual_path = Path(predictions_info.get("path", "")).resolve()
        if actual_path != expected_path:
            issues.append(
                f"{strategy}.predictions: path mismatch expected={expected_path} actual={actual_path}"
            )

    if issues:
        print("ERROR: R21 artifact manifest verification failed", file=sys.stderr)
        for issue in issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        if len(issues) > 20:
            print(f"  ... {len(issues) - 20} more", file=sys.stderr)
        sys.exit(1)

    return sha256_of_file(manifest_path), artifact_file_check_count


# ── Scoring helpers (inlined from R21) ────────────────────────────────


def build_gold_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for span in label.get("gold_spans", []):
        path = span.get("path", "")
        start = span.get("start_line", 0)
        end = span.get("end_line", 0)
        for ln in range(start, end + 1):
            result.add((path, ln))
    return result


def build_hard_distractor_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for hd in label.get("hard_distractors", []):
        path = hd.get("path", "")
        start = hd.get("start_line", 0)
        end = hd.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def build_must_not_primary_line_set(label: dict) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for mnp in label.get("must_not_primary", []):
        path = mnp.get("path", "")
        start = mnp.get("start_line", 0)
        end = mnp.get("end_line", 0)
        if start > 0 and end >= start:
            for ln in range(start, end + 1):
                result.add((path, ln))
        elif path:
            result.add((path, 0))
    return result


def get_gold_paths(label: dict) -> set[str]:
    return {span.get("path", "") for span in label.get("gold_spans", [])}


def get_hard_distractor_paths(label: dict) -> set[str]:
    return {hd.get("path", "") for hd in label.get("hard_distractors", [])}


def match_path(pred_path: str, label_path: str, repo_id: str) -> bool:
    if pred_path == label_path:
        return True
    if repo_id and pred_path == f"{repo_id}/{label_path}":
        return True
    return False


def file_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        pred_paths = set()
        for e in pred["evidence"][:k]:
            pred_paths.add(e.get("path", ""))
        for gp in gold_paths:
            for pp in pred_paths:
                if match_path(pp, gp, repo_id):
                    hits += 1
                    break
            else:
                continue
            break
    return hits / total if total else 0.0


def mrr(predictions: list[dict], gold: dict[str, dict]) -> float:
    total_rr = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        total += 1
        gold_paths = get_gold_paths(gold[task_id])
        if not gold_paths:
            continue
        for rank, e in enumerate(pred["evidence"], 1):
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    total_rr += 1.0 / rank
                    break
            else:
                continue
            break
    return total_rr / total if total else 0.0


def span_precision_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    total_prec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        pred_lines: set[tuple[str, int]] = set()
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                pred_lines.add((path, ln))
        if not pred_lines:
            continue
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_prec += overlap / len(pred_lines) if pred_lines else 0.0
    return total_prec / total if total else 0.0


def span_recall_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    total_rec = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        pred_lines: set[tuple[str, int]] = set()
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                pred_lines.add((path, ln))
        matched_lines: set[tuple[str, int]] = set()
        for (pp, pln) in pred_lines:
            for (gp, gln) in gold_lines:
                if match_path(pp, gp, repo_id) and pln == gln:
                    matched_lines.add((gp, gln))
        overlap = len(matched_lines)
        total_rec += overlap / len(gold_lines) if gold_lines else 0.0
    return total_rec / total if total else 0.0


def span_f_beta_at_k(predictions: list[dict], gold: dict[str, dict], k: int, beta: float = 0.5) -> float:
    avg_prec = span_precision_at_k(predictions, gold, k)
    avg_rec = span_recall_at_k(predictions, gold, k)
    if avg_prec + avg_rec == 0:
        return 0.0
    beta2 = beta * beta
    return (1 + beta2) * avg_prec * avg_rec / (beta2 * avg_prec + avg_rec)


def token_waste_ratio_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    total_waste = 0.0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        gold_lines = build_gold_line_set(gold[task_id])
        if not gold_lines:
            continue
        total += 1
        all_pred_lines = 0
        non_gold_lines = 0
        for e in pred["evidence"][:k]:
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            path = e.get("path", "")
            for ln in range(start, end + 1):
                all_pred_lines += 1
                matched = any(
                    match_path(path, gp, repo_id) and ln == gln
                    for gp, gln in gold_lines
                )
                if not matched:
                    non_gold_lines += 1
        if all_pred_lines > 0:
            total_waste += non_gold_lines / all_pred_lines
    return total_waste / total if total else 0.0


def no_gold_nonempty_rate_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    nonempty = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        if label.get("gold_spans"):
            continue
        total += 1
        if pred.get("evidence", [])[:k]:
            nonempty += 1
    return nonempty / total if total else 0.0


def hard_distractor_hit_rate_at_k(predictions: list[dict], gold: dict[str, dict], k: int) -> float:
    hits = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        hard_dist_lines = build_hard_distractor_line_set(label)
        hard_dist_paths = get_hard_distractor_paths(label)
        if not hard_dist_paths:
            continue
        total += 1
        for e in pred.get("evidence", [])[:k]:
            pred_path = e.get("path", "")
            start = e.get("start_line", 0)
            end = e.get("end_line", 0)
            if start > 0 and end >= start:
                for ln in range(start, end + 1):
                    for (hp, hln) in hard_dist_lines:
                        if match_path(pred_path, hp, repo_id) and ln == hln:
                            hits += 1
                            break
                    else:
                        if any(
                            match_path(pred_path, hp, repo_id) and hln == 0
                            for hp, hln in hard_dist_lines
                        ):
                            hits += 1
                            break
                        continue
                    break
    return hits / total if total else 0.0


def false_primary_on_negative_rate(predictions: list[dict], gold: dict[str, dict]) -> float:
    false_primary = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        eb = label.get("expected_behavior", "")
        if eb not in ("abstain", "no_primary"):
            continue
        total += 1
        evidence = pred.get("evidence", [])
        if evidence:
            false_primary += 1
    return false_primary / total if total else 0.0


def abstain_rate(predictions: list[dict]) -> float:
    abstained = 0
    total = len(predictions)
    for pred in predictions:
        if not pred.get("evidence", []):
            abstained += 1
    return abstained / total if total else 0.0


def weak_candidate_rate(predictions: list[dict], gold: dict[str, dict]) -> float:
    weak = 0
    weak_with_evidence = 0
    for pred in predictions:
        task_id = pred["task_id"]
        if task_id not in gold:
            continue
        label = gold[task_id]
        if label.get("expected_behavior", "") == "weak_candidates":
            weak += 1
            if pred.get("evidence", []):
                weak_with_evidence += 1
    return weak_with_evidence / weak if weak else 0.0


def must_not_primary_violation_rate(predictions: list[dict], gold: dict[str, dict]) -> float:
    violations = 0
    total = 0
    for pred in predictions:
        task_id = pred["task_id"]
        repo_id = pred.get("repo_id", "")
        if task_id not in gold:
            continue
        label = gold[task_id]
        mnp_lines = build_must_not_primary_line_set(label)
        if not mnp_lines:
            continue
        total += 1
        evidence = pred.get("evidence", [])
        if not evidence:
            continue
        top = evidence[0]
        top_path = top.get("path", "")
        start = top.get("start_line", 0)
        end = top.get("end_line", 0)
        for ln in range(start, end + 1):
            for (mp, mln) in mnp_lines:
                if match_path(top_path, mp, repo_id) and ln == mln:
                    violations += 1
                    break
            else:
                continue
            break
    return violations / total if total else 0.0


def compute_guard_recall_kill_rate(
    predictions_guarded: list[dict],
    predictions_raw_rrf: list[dict],
    gold: dict[str, dict],
) -> float | None:
    denom = 0
    numer = 0
    guard_by_task = {p["task_id"]: p for p in predictions_guarded}
    rrf_by_task = {p["task_id"]: p for p in predictions_raw_rrf}
    for task_id, label in gold.items():
        if label.get("expected_behavior") != "primary_evidence":
            continue
        if not label.get("gold_spans"):
            continue
        repo_id = label.get("repo_id", "")
        gold_paths = get_gold_paths(label)
        rrf_pred = rrf_by_task.get(task_id)
        if not rrf_pred:
            continue
        rrf_hit = False
        for e in rrf_pred.get("evidence", [])[:10]:
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    rrf_hit = True
                    break
            if rrf_hit:
                break
        if not rrf_hit:
            continue
        denom += 1
        guard_pred = guard_by_task.get(task_id)
        if not guard_pred:
            numer += 1
            continue
        guard_hit = False
        for e in guard_pred.get("evidence", [])[:10]:
            pred_path = e.get("path", "")
            for gp in gold_paths:
                if match_path(pred_path, gp, repo_id):
                    guard_hit = True
                    break
            if guard_hit:
                break
        if not guard_hit:
            numer += 1
    return numer / denom if denom > 0 else None


# ── Guard strategy builder ─────────────────────────────────────────────


def apply_guard(
    rrf_pred: dict,
    regex_pred: dict | None,
    symbol_pred: dict | None,
    params: dict[str, Any],
) -> dict:
    """Apply guard parameters to raw RRF prediction. Returns new prediction.

    Guard semantics: based on raw RRF evidence; if guard fails, abstain.
    Labels are NOT used for routing; only for scoring after.
    """
    task_id = rrf_pred["task_id"]
    query = rrf_pred.get("query", "")
    repo_id = rrf_pred.get("repo_id", "")
    rrf_evidence = rrf_pred.get("evidence", [])

    # Extract guard signals
    noise_score = query_noise_score(query)
    ident_density = identifier_density(query)
    top_score = rrf_evidence[0].get("score", 0.0) if rrf_evidence else 0.0
    gap = 0.0
    if len(rrf_evidence) >= 2:
        gap = rrf_evidence[0].get("score", 0.0) - rrf_evidence[1].get("score", 0.0)
    regex_has = bool(regex_pred and regex_pred.get("evidence"))
    symbol_has = bool(symbol_pred and symbol_pred.get("evidence"))
    chan_count = candidate_channel_count(rrf_pred, regex_pred, symbol_pred)

    # Check guard conditions
    fail_reason = None

    # query_noise_threshold: if noise_score >= threshold, abstain
    qnt = params.get("query_noise_threshold")
    if qnt is not None and noise_score >= qnt:
        fail_reason = f"query_noise_score={noise_score}>={qnt}"

    # rrf_score_threshold: top RRF score must be >= threshold
    if fail_reason is None:
        rst = params.get("rrf_score_threshold")
        if rst is not None and top_score < rst:
            fail_reason = f"rrf_score={top_score}<{rst}"

    # regex_agreement_required
    if fail_reason is None:
        if params.get("regex_agreement_required") and not regex_has:
            fail_reason = "no_regex_agreement"

    # symbol_agreement_required
    if fail_reason is None:
        if params.get("symbol_agreement_required") and not symbol_has:
            fail_reason = "no_symbol_agreement"

    # regex_or_symbol_agreement_required
    if fail_reason is None:
        if params.get("regex_or_symbol_agreement_required") and not (regex_has or symbol_has):
            fail_reason = "no_regex_or_symbol_agreement"

    # top1_top2_gap_threshold
    if fail_reason is None:
        tgt = params.get("top1_top2_gap_threshold")
        if tgt is not None and gap < tgt:
            fail_reason = f"top1_top2_gap={gap}<{tgt}"

    # identifier_density_threshold
    if fail_reason is None:
        idt = params.get("identifier_density_threshold")
        if idt is not None and ident_density < idt:
            fail_reason = f"identifier_density={ident_density}<{idt}"

    # candidate_channel_count_threshold
    if fail_reason is None:
        cct = params.get("candidate_channel_count_threshold")
        if cct is not None and chan_count < cct:
            fail_reason = f"candidate_channel_count={chan_count}<{cct}"

    if fail_reason is not None:
        return {
            "task_id": task_id,
            "repo_id": repo_id,
            "query": query,
            "strategy": "guard_sweep",
            "selected_method": "empty",
            "route_decision": f"guard_abstain:{fail_reason}",
            "evidence": [],
            "latency_ms": 0,
            "returncode": 0,
        }
    else:
        return {
            "task_id": task_id,
            "repo_id": repo_id,
            "query": query,
            "strategy": "guard_sweep",
            "selected_method": "rrf",
            "route_decision": "guard_pass",
            "evidence": rrf_evidence,
            "latency_ms": rrf_pred.get("latency_ms", 0),
            "returncode": rrf_pred.get("returncode", 0),
        }


# ── Comprehensive metrics ──────────────────────────────────────────────


def compute_full_metrics(
    predictions: list[dict],
    gold: dict[str, dict],
    rrf_predictions: list[dict],
) -> dict[str, Any]:
    """Compute all required metrics for a guard strategy."""
    non_neg_gold = {tid: g for tid, g in gold.items() if g.get("gold_spans")}
    negative_gold = {tid: g for tid, g in gold.items() if not g.get("gold_spans")}
    evaluable_gold = {
        tid: g
        for tid, g in gold.items()
        if g.get("gold_spans") or g.get("hard_distractors")
    }

    metrics: dict[str, Any] = {"total_tasks": len(predictions)}

    if non_neg_gold:
        for k in [1, 3, 5]:
            metrics[f"FileRecall@{k}"] = file_recall_at_k(predictions, non_neg_gold, k)
        metrics["MRR"] = mrr(predictions, non_neg_gold)
        metrics["SpanF0.5"] = span_f_beta_at_k(predictions, non_neg_gold, 10, 0.5)
        metrics["SpanPrecision"] = span_precision_at_k(predictions, non_neg_gold, 10)
        metrics["SpanRecall"] = span_recall_at_k(predictions, non_neg_gold, 10)
        metrics["token_waste"] = token_waste_ratio_at_k(predictions, non_neg_gold, 10)

    if evaluable_gold:
        metrics["hard_distractor_hit_rate"] = hard_distractor_hit_rate_at_k(
            predictions, evaluable_gold, 10
        )

    if negative_gold:
        metrics["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(
            predictions, negative_gold, 10
        )

    metrics["primary_false_positive_rate"] = false_primary_on_negative_rate(predictions, gold)
    metrics["abstain_rate"] = abstain_rate(predictions)
    metrics["weak_candidate_rate"] = weak_candidate_rate(predictions, gold)
    metrics["must_not_primary_violation_rate"] = must_not_primary_violation_rate(predictions, gold)
    metrics["guard_recall_kill_rate"] = compute_guard_recall_kill_rate(
        predictions, rrf_predictions, gold
    )

    return metrics


# ── Bucket metrics ─────────────────────────────────────────────────────


def compute_bucket_metrics(
    predictions: list[dict],
    gold: dict[str, dict],
    bucket_key: str,
    rrf_predictions: list[dict] | None = None,
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for tid, label in gold.items():
        val = label.get(bucket_key, "unknown")
        if isinstance(val, list):
            val = ",".join(str(v) for v in val) if val else "none"
        else:
            val = str(val)
        buckets[val].append(tid)

    result: dict[str, dict[str, Any]] = {}
    for bucket_val, task_ids in sorted(buckets.items()):
        bucket_gold = {tid: gold[tid] for tid in task_ids}
        bucket_preds = [p for p in predictions if p["task_id"] in task_ids]
        if not bucket_preds:
            continue
        non_neg = {tid: g for tid, g in bucket_gold.items() if g.get("gold_spans")}
        neg = {tid: g for tid, g in bucket_gold.items() if not g.get("gold_spans")}
        m: dict[str, Any] = {"total_tasks": len(bucket_preds)}
        if non_neg:
            m["FileRecall@1"] = file_recall_at_k(bucket_preds, non_neg, 1)
            m["FileRecall@3"] = file_recall_at_k(bucket_preds, non_neg, 3)
            m["FileRecall@5"] = file_recall_at_k(bucket_preds, non_neg, 5)
            m["MRR"] = mrr(bucket_preds, non_neg)
            m["SpanF0.5"] = span_f_beta_at_k(bucket_preds, non_neg, 10, 0.5)
            m["SpanPrecision"] = span_precision_at_k(bucket_preds, non_neg, 10)
            m["SpanRecall"] = span_recall_at_k(bucket_preds, non_neg, 10)
            m["token_waste"] = token_waste_ratio_at_k(bucket_preds, non_neg, 10)
        if neg:
            m["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(bucket_preds, neg, 10)
        m["abstain_rate"] = abstain_rate(bucket_preds)
        m["primary_false_positive_rate"] = false_primary_on_negative_rate(bucket_preds, bucket_gold)
        m["must_not_primary_violation_rate"] = must_not_primary_violation_rate(bucket_preds, bucket_gold)
        m["weak_candidate_rate"] = weak_candidate_rate(bucket_preds, bucket_gold)
        if rrf_predictions is not None:
            bucket_rrf_preds = [p for p in rrf_predictions if p["task_id"] in task_ids]
            m["guard_recall_kill_rate"] = compute_guard_recall_kill_rate(
                bucket_preds, bucket_rrf_preds, bucket_gold
            )
        result[bucket_val] = m
    return result


# ── Bucket regression check ────────────────────────────────────────────


def check_bucket_regressions(
    bucket_metrics: dict[str, dict[str, Any]],
    rrf_bucket_metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check for bucket regressions vs raw RRF."""
    regressions = []
    for bucket_val, bm in bucket_metrics.items():
        rrf_bm = rrf_bucket_metrics.get(bucket_val, {})
        issues = []

        # Check recall gap vs RRF > 0.15
        for k in [1, 3, 5]:
            bk = f"FileRecall@{k}"
            if bk in bm and bk in rrf_bm:
                gap = rrf_bm[bk] - bm[bk]
                if gap > 0.15:
                    issues.append(f"{bk} gap={gap:.3f} (rrf={rrf_bm[bk]:.3f} guard={bm[bk]:.3f})")

        # Check no_gold_nonempty_rate > 0.3
        if bm.get("no_gold_nonempty_rate", 0) > 0.3:
            issues.append(f"no_gold_nonempty_rate={bm['no_gold_nonempty_rate']:.3f}>0.3")

        # Check primary_false_positive_rate > 0.3
        if bm.get("primary_false_positive_rate", 0) > 0.3:
            issues.append(f"primary_false_positive_rate={bm['primary_false_positive_rate']:.3f}>0.3")

        # Check guard_recall_kill_rate > 0.1
        if bm.get("guard_recall_kill_rate") is not None and bm["guard_recall_kill_rate"] > 0.1:
            issues.append(f"guard_recall_kill_rate={bm['guard_recall_kill_rate']:.3f}>0.1")

        if issues:
            regressions.append({
                "bucket": bucket_val,
                "issues": issues,
            })
    return regressions


# ── Curve computation ──────────────────────────────────────────────────


def compute_risk_coverage_curve(
    sweep_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """risk_coverage_curve: x=abstain_rate, y=FileRecall@1."""
    points = []
    for sr in sweep_results:
        m = sr["metrics"]
        points.append({
            "abstain_rate": m.get("abstain_rate", 0.0),
            "FileRecall@1": m.get("FileRecall@1", 0.0),
            "strategy_name": sr["strategy_name"],
        })
    points.sort(key=lambda p: p["abstain_rate"])
    return points


def compute_recall_vs_negative_curve(
    sweep_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """recall_vs_negative_curve: x=no_gold_nonempty_rate, y=FileRecall@1."""
    points = []
    for sr in sweep_results:
        m = sr["metrics"]
        points.append({
            "no_gold_nonempty_rate": m.get("no_gold_nonempty_rate", 0.0),
            "FileRecall@1": m.get("FileRecall@1", 0.0),
            "strategy_name": sr["strategy_name"],
        })
    points.sort(key=lambda p: p["no_gold_nonempty_rate"])
    return points


def compute_recall_vs_false_primary_curve(
    sweep_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """recall_vs_false_primary_curve: x=primary_false_positive_rate, y=FileRecall@1."""
    points = []
    for sr in sweep_results:
        m = sr["metrics"]
        points.append({
            "primary_false_positive_rate": m.get("primary_false_positive_rate", 0.0),
            "FileRecall@1": m.get("FileRecall@1", 0.0),
            "strategy_name": sr["strategy_name"],
        })
    points.sort(key=lambda p: p["primary_false_positive_rate"])
    return points


def compute_precision_vs_abstain_curve(
    sweep_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """precision_vs_abstain_curve: x=abstain_rate, y=SpanPrecision."""
    points = []
    for sr in sweep_results:
        m = sr["metrics"]
        points.append({
            "abstain_rate": m.get("abstain_rate", 0.0),
            "SpanPrecision": m.get("SpanPrecision", 0.0),
            "strategy_name": sr["strategy_name"],
        })
    points.sort(key=lambda p: p["abstain_rate"])
    return points


# ── Main ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="R23 Guard Parameter Sweep")
    parser.add_argument("--workspace", default=".", help="Workspace root directory")
    parser.add_argument("--r21-report", default="runs/r21-auto-wide-report.json", help="R21 report path")
    parser.add_argument("--fixtures", default="fixtures/r20_auto_wide", help="Fixtures directory")
    parser.add_argument("--out", default="runs/r23-guard-sweep.json", help="Output path")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    r21_report_path = Path(args.r21_report)
    if not r21_report_path.is_absolute():
        r21_report_path = (workspace / args.r21_report).resolve()
    fixtures_dir = workspace / args.fixtures
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (workspace / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Load R21 report ────────────────────────────────────────────────
    if not r21_report_path.exists():
        print(f"ERROR: R21 report not found: {r21_report_path}", file=sys.stderr)
        sys.exit(1)
    r21_report = load_json(r21_report_path)
    source_report_sha = sha256_of_file(r21_report_path)

    runs_dir = workspace / "runs"

    # ── Load R21 predictions ──────────────────────────────────────────
    rrf_preds = load_jsonl(runs_dir / "r21-auto-wide-rrf-predictions.jsonl")
    regex_preds = load_jsonl(runs_dir / "r21-auto-wide-regex-predictions.jsonl")
    symbol_preds = load_jsonl(runs_dir / "r21-auto-wide-symbol-predictions.jsonl")

    if not rrf_preds:
        print("ERROR: No R21 RRF predictions found", file=sys.stderr)
        sys.exit(1)

    # Index predictions by task_id
    rrf_by_task = {p["task_id"]: p for p in rrf_preds}
    regex_by_task = {p["task_id"]: p for p in regex_preds}
    symbol_by_task = {p["task_id"]: p for p in symbol_preds}

    # ── Load R20 labels ───────────────────────────────────────────────
    labels_path = fixtures_dir / "labels" / "auto_wide.jsonl"
    if not labels_path.exists():
        print(f"ERROR: Labels file not found: {labels_path}", file=sys.stderr)
        sys.exit(1)
    labels_list = load_jsonl(labels_path)
    gold = {l["task_id"]: l for l in labels_list}
    labels_sha = sha256_of_file(labels_path)

    # Filter gold to only tasks we have predictions for
    task_ids = set(rrf_by_task.keys())
    gold = {tid: g for tid, g in gold.items() if tid in task_ids}

    # ── Verify artifact manifest ──────────────────────────────────────
    artifact_manifest_sha, artifact_files_checked = verify_r21_artifact_manifest(runs_dir)

    # ── Load repos for language bucket ─────────────────────────────────
    lock_path = fixtures_dir / "repos.lock.jsonl"
    repos: dict[str, dict] = {}
    if lock_path.exists():
        for entry in load_jsonl(lock_path):
            repos[entry["repo_id"]] = entry

    # ── Compute raw RRF baseline metrics ──────────────────────────────
    print("Computing raw RRF baseline metrics...")
    rrf_metrics = compute_full_metrics(rrf_preds, gold, rrf_preds)

    # RRF bucket metrics
    rrf_bucket_metrics_all: dict[str, dict[str, dict[str, Any]]] = {}
    for bucket_key in ["repo_id", "query_category", "expected_behavior", "risk_tags", "intent_guess"]:
        bkm = compute_bucket_metrics(rrf_preds, gold, bucket_key)
        rrf_bucket_metrics_all[bucket_key] = bkm

    # Language bucket for RRF
    lang_buckets: dict[str, list[str]] = defaultdict(list)
    for tid, label in gold.items():
        rid = label.get("repo_id", "")
        if rid in repos:
            lang = repos[rid].get("language", {}).get("primary", "unknown")
        else:
            lang = "unknown"
        lang_buckets[lang].append(tid)
    rrf_lang_metrics: dict[str, dict[str, Any]] = {}
    for lang, tids in sorted(lang_buckets.items()):
        lang_gold = {tid: gold[tid] for tid in tids}
        lang_preds = [p for p in rrf_preds if p["task_id"] in tids]
        if not lang_preds:
            continue
        non_neg = {tid: g for tid, g in lang_gold.items() if g.get("gold_spans")}
        neg = {tid: g for tid, g in lang_gold.items() if not g.get("gold_spans")}
        m: dict[str, Any] = {"total_tasks": len(lang_preds)}
        if non_neg:
            m["FileRecall@1"] = file_recall_at_k(lang_preds, non_neg, 1)
            m["MRR"] = mrr(lang_preds, non_neg)
            m["SpanF0.5"] = span_f_beta_at_k(lang_preds, non_neg, 10, 0.5)
        if neg:
            m["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(lang_preds, neg, 10)
        rrf_lang_metrics[lang] = m
    rrf_bucket_metrics_all["language"] = rrf_lang_metrics

    # ── Define sweep parameters ────────────────────────────────────────
    sweep_strategies: list[dict[str, Any]] = []

    # 1. query_noise_threshold sweep
    for qnt in [0, 1, 2, 3, 4, 5, 6]:
        sweep_strategies.append({
            "strategy_name": f"query_noise_threshold_{qnt}",
            "params": {"query_noise_threshold": qnt},
        })

    # 2. rrf_score_threshold sweep
    for rst in [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1]:
        sweep_strategies.append({
            "strategy_name": f"rrf_score_threshold_{rst}",
            "params": {"rrf_score_threshold": rst},
        })

    # 3. regex_agreement_required
    sweep_strategies.append({
        "strategy_name": "regex_agreement_required",
        "params": {"regex_agreement_required": True},
    })

    # 4. symbol_agreement_required
    sweep_strategies.append({
        "strategy_name": "symbol_agreement_required",
        "params": {"symbol_agreement_required": True},
    })

    # 5. regex_or_symbol_agreement_required
    sweep_strategies.append({
        "strategy_name": "regex_or_symbol_agreement_required",
        "params": {"regex_or_symbol_agreement_required": True},
    })

    # 6. top1_top2_gap_threshold sweep
    for tgt in [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05]:
        sweep_strategies.append({
            "strategy_name": f"top1_top2_gap_threshold_{tgt}",
            "params": {"top1_top2_gap_threshold": tgt},
        })

    # 7. identifier_density_threshold sweep
    for idt in [0, 1, 2, 3]:
        sweep_strategies.append({
            "strategy_name": f"identifier_density_threshold_{idt}",
            "params": {"identifier_density_threshold": idt},
        })

    # 8. candidate_channel_count_threshold sweep
    for cct in [0, 1, 2, 3, 4]:
        sweep_strategies.append({
            "strategy_name": f"candidate_channel_count_threshold_{cct}",
            "params": {"candidate_channel_count_threshold": cct},
        })

    # 9. Combined strategies (most promising from R21/R22 analysis)
    sweep_strategies.append({
        "strategy_name": "query_noise_1_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 1, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 2, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_1_plus_symbol_agree",
        "params": {"query_noise_threshold": 1, "symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_symbol_agree",
        "params": {"query_noise_threshold": 2, "symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_1_plus_rrf_score_0.01",
        "params": {"query_noise_threshold": 1, "rrf_score_threshold": 0.01},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_rrf_score_0.01",
        "params": {"query_noise_threshold": 2, "rrf_score_threshold": 0.01},
    })
    sweep_strategies.append({
        "strategy_name": "rrf_score_0.01_plus_regex_or_symbol_agree",
        "params": {"rrf_score_threshold": 0.01, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "rrf_score_0.015_plus_regex_or_symbol_agree",
        "params": {"rrf_score_threshold": 0.015, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_1_plus_rrf_score_0.01_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 1, "rrf_score_threshold": 0.01, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_rrf_score_0.01_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 2, "rrf_score_threshold": 0.01, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_gap_0.01_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 2, "top1_top2_gap_threshold": 0.01, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "gap_0.01_plus_regex_or_symbol_agree",
        "params": {"top1_top2_gap_threshold": 0.01, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "ident_1_plus_regex_or_symbol_agree",
        "params": {"identifier_density_threshold": 1, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "channel_2_plus_regex_or_symbol_agree",
        "params": {"candidate_channel_count_threshold": 2, "regex_or_symbol_agreement_required": True},
    })
    sweep_strategies.append({
        "strategy_name": "query_noise_2_plus_rrf_score_0.015_plus_regex_or_symbol_agree",
        "params": {"query_noise_threshold": 2, "rrf_score_threshold": 0.015, "regex_or_symbol_agreement_required": True},
    })

    # ── Run sweep ──────────────────────────────────────────────────────
    print(f"Running guard parameter sweep: {len(sweep_strategies)} strategies...")
    sweep_results: list[dict[str, Any]] = []

    for strat in sweep_strategies:
        name = strat["strategy_name"]
        params = strat["params"]

        # Apply guard to each task
        guarded_preds = []
        for rrf_pred in rrf_preds:
            tid = rrf_pred["task_id"]
            regex_pred = regex_by_task.get(tid)
            symbol_pred = symbol_by_task.get(tid)
            guarded = apply_guard(rrf_pred, regex_pred, symbol_pred, params)
            guarded_preds.append(guarded)

        # Compute metrics
        metrics = compute_full_metrics(guarded_preds, gold, rrf_preds)

        # Compute bucket metrics
        bucket_metrics: dict[str, dict[str, dict[str, Any]]] = {}
        for bucket_key in ["repo_id", "query_category", "expected_behavior", "risk_tags", "intent_guess"]:
            bkm = compute_bucket_metrics(guarded_preds, gold, bucket_key, rrf_preds)
            bucket_metrics[bucket_key] = bkm

        # Language bucket
        lang_metrics: dict[str, dict[str, Any]] = {}
        for lang, tids in sorted(lang_buckets.items()):
            lang_gold = {tid: gold[tid] for tid in tids}
            lang_preds = [p for p in guarded_preds if p["task_id"] in tids]
            if not lang_preds:
                continue
            non_neg = {tid: g for tid, g in lang_gold.items() if g.get("gold_spans")}
            neg = {tid: g for tid, g in lang_gold.items() if not g.get("gold_spans")}
            lm: dict[str, Any] = {"total_tasks": len(lang_preds)}
            if non_neg:
                lm["FileRecall@1"] = file_recall_at_k(lang_preds, non_neg, 1)
                lm["MRR"] = mrr(lang_preds, non_neg)
                lm["SpanF0.5"] = span_f_beta_at_k(lang_preds, non_neg, 10, 0.5)
            if neg:
                lm["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(lang_preds, neg, 10)
            lang_rrf_preds = [p for p in rrf_preds if p["task_id"] in tids]
            lm["guard_recall_kill_rate"] = compute_guard_recall_kill_rate(
                lang_preds, lang_rrf_preds, lang_gold
            )
            lang_metrics[lang] = lm
        bucket_metrics["language"] = lang_metrics

        # positive_negative_ambiguous bucket
        pna_metrics: dict[str, dict[str, Any]] = {}
        for pna_val in ["primary_evidence", "abstain", "no_primary", "weak_candidates", "supporting_only"]:
            pna_tids = [tid for tid, g in gold.items() if g.get("expected_behavior") == pna_val]
            if not pna_tids:
                continue
            pna_gold = {tid: gold[tid] for tid in pna_tids}
            pna_preds = [p for p in guarded_preds if p["task_id"] in pna_tids]
            if not pna_preds:
                continue
            non_neg = {tid: g for tid, g in pna_gold.items() if g.get("gold_spans")}
            neg = {tid: g for tid, g in pna_gold.items() if not g.get("gold_spans")}
            pm: dict[str, Any] = {"total_tasks": len(pna_preds)}
            if non_neg:
                pm["FileRecall@1"] = file_recall_at_k(pna_preds, non_neg, 1)
                pm["MRR"] = mrr(pna_preds, non_neg)
            if neg:
                pm["no_gold_nonempty_rate"] = no_gold_nonempty_rate_at_k(pna_preds, neg, 10)
            pm["abstain_rate"] = abstain_rate(pna_preds)
            pm["primary_false_positive_rate"] = false_primary_on_negative_rate(pna_preds, pna_gold)
            pna_rrf_preds = [p for p in rrf_preds if p["task_id"] in pna_tids]
            pm["guard_recall_kill_rate"] = compute_guard_recall_kill_rate(
                pna_preds, pna_rrf_preds, pna_gold
            )
            pna_metrics[pna_val] = pm
        bucket_metrics["positive_negative_ambiguous"] = pna_metrics

        # Check bucket regressions
        bucket_regressions = []
        for bk, bm in bucket_metrics.items():
            rrf_bk = rrf_bucket_metrics_all.get(bk, {})
            regs = check_bucket_regressions(bm, rrf_bk)
            for reg in regs:
                reg["bucket_key"] = bk
                bucket_regressions.append(reg)

        promotion_blocked = len(bucket_regressions) > 0

        sweep_results.append({
            "strategy_name": name,
            "params": params,
            "metrics": metrics,
            "bucket_metrics": bucket_metrics,
            "bucket_regressions": bucket_regressions,
            "promotion_blocked_by_bucket_regression": promotion_blocked,
        })

        print(f"  {name}: abstain_rate={metrics.get('abstain_rate', 0):.3f} "
              f"FileRecall@1={metrics.get('FileRecall@1', 0):.3f} "
              f"no_gold_nonempty={metrics.get('no_gold_nonempty_rate', 0):.3f} "
              f"pfp={metrics.get('primary_false_positive_rate', 0):.3f} "
              f"guard_kill={metrics.get('guard_recall_kill_rate', 'N/A')} "
              f"blocked={promotion_blocked}")

    # ── Compute curves ─────────────────────────────────────────────────
    curves = {
        "risk_coverage_curve": compute_risk_coverage_curve(sweep_results),
        "recall_vs_negative_curve": compute_recall_vs_negative_curve(sweep_results),
        "recall_vs_false_primary_curve": compute_recall_vs_false_primary_curve(sweep_results),
        "precision_vs_abstain_curve": compute_precision_vs_abstain_curve(sweep_results),
    }

    # ── Compute bucket summary ────────────────────────────────────────
    bucket_summary: dict[str, dict[str, Any]] = {}
    for bk in ["repo_id", "query_category", "expected_behavior", "risk_tags",
                "intent_guess", "language", "positive_negative_ambiguous"]:
        # Aggregate across all strategies for this bucket key
        all_bucket_vals: set[str] = set()
        for sr in sweep_results:
            bm = sr.get("bucket_metrics", {}).get(bk, {})
            all_bucket_vals.update(bm.keys())

        bsum: dict[str, Any] = {}
        for bv in sorted(all_bucket_vals):
            # Collect metrics across strategies
            vals: dict[str, list[float]] = defaultdict(list)
            for sr in sweep_results:
                m = sr.get("bucket_metrics", {}).get(bk, {}).get(bv, {})
                for mk, mv in m.items():
                    if isinstance(mv, (int, float)):
                        vals[mk].append(float(mv))
            if vals.get("total_tasks", []):
                avg: dict[str, float] = {}
                for mk, mvs in vals.items():
                    avg[mk] = sum(mvs) / len(mvs) if mvs else 0.0
                bsum[bv] = avg
        bucket_summary[bk] = bsum

    # User-facing alias requested in R23 spec; R20/R21 field name is
    # query_category. Keep both names to avoid losing provenance.
    if "query_category" in bucket_summary:
        bucket_summary["query_type"] = bucket_summary["query_category"]

    # ── Best observations ──────────────────────────────────────────────
    observations: list[dict[str, Any]] = []

    # Best recall preservation with lowest false positive
    sorted_by_pfp = sorted(
        [sr for sr in sweep_results if sr["metrics"].get("FileRecall@1") is not None],
        key=lambda sr: (sr["metrics"].get("primary_false_positive_rate", 1.0), -sr["metrics"].get("FileRecall@1", 0.0))
    )
    if sorted_by_pfp:
        best = sorted_by_pfp[0]
        observations.append({
            "observation_type": "lowest_pfp_with_recall",
            "strategy_name": best["strategy_name"],
            "params": best["params"],
            "FileRecall@1": best["metrics"].get("FileRecall@1"),
            "primary_false_positive_rate": best["metrics"].get("primary_false_positive_rate"),
            "abstain_rate": best["metrics"].get("abstain_rate"),
            "guard_recall_kill_rate": best["metrics"].get("guard_recall_kill_rate"),
            "promotion_blocked_by_bucket_regression": best["promotion_blocked_by_bucket_regression"],
        })

    # Best no_gold_nonempty elimination
    sorted_by_ngne = sorted(
        [sr for sr in sweep_results if sr["metrics"].get("no_gold_nonempty_rate") is not None],
        key=lambda sr: (sr["metrics"].get("no_gold_nonempty_rate", 1.0), -sr["metrics"].get("FileRecall@1", 0.0))
    )
    if sorted_by_ngne:
        best = sorted_by_ngne[0]
        observations.append({
            "observation_type": "lowest_no_gold_nonempty",
            "strategy_name": best["strategy_name"],
            "params": best["params"],
            "no_gold_nonempty_rate": best["metrics"].get("no_gold_nonempty_rate"),
            "FileRecall@1": best["metrics"].get("FileRecall@1"),
            "abstain_rate": best["metrics"].get("abstain_rate"),
            "guard_recall_kill_rate": best["metrics"].get("guard_recall_kill_rate"),
            "promotion_blocked_by_bucket_regression": best["promotion_blocked_by_bucket_regression"],
        })

    # Best recall preservation (highest FileRecall@1 with guard_kill < 0.1)
    low_kill = [sr for sr in sweep_results
                if sr["metrics"].get("guard_recall_kill_rate") is not None
                and sr["metrics"]["guard_recall_kill_rate"] < 0.1]
    if low_kill:
        best_recall = max(low_kill, key=lambda sr: sr["metrics"].get("FileRecall@1", 0.0))
        observations.append({
            "observation_type": "best_recall_with_low_kill",
            "strategy_name": best_recall["strategy_name"],
            "params": best_recall["params"],
            "FileRecall@1": best_recall["metrics"].get("FileRecall@1"),
            "guard_recall_kill_rate": best_recall["metrics"].get("guard_recall_kill_rate"),
            "primary_false_positive_rate": best_recall["metrics"].get("primary_false_positive_rate"),
            "no_gold_nonempty_rate": best_recall["metrics"].get("no_gold_nonempty_rate"),
            "abstain_rate": best_recall["metrics"].get("abstain_rate"),
            "promotion_blocked_by_bucket_regression": best_recall["promotion_blocked_by_bucket_regression"],
        })

    # Best combined guard (query_noise + agreement)
    combined = [sr for sr in sweep_results
                if "query_noise" in sr["strategy_name"] and "agree" in sr["strategy_name"]]
    if combined:
        best_combined = min(combined, key=lambda sr: (
            sr["metrics"].get("primary_false_positive_rate", 1.0),
            -sr["metrics"].get("FileRecall@1", 0.0)
        ))
        observations.append({
            "observation_type": "best_combined_guard",
            "strategy_name": best_combined["strategy_name"],
            "params": best_combined["params"],
            "FileRecall@1": best_combined["metrics"].get("FileRecall@1"),
            "primary_false_positive_rate": best_combined["metrics"].get("primary_false_positive_rate"),
            "no_gold_nonempty_rate": best_combined["metrics"].get("no_gold_nonempty_rate"),
            "abstain_rate": best_combined["metrics"].get("abstain_rate"),
            "guard_recall_kill_rate": best_combined["metrics"].get("guard_recall_kill_rate"),
            "promotion_blocked_by_bucket_regression": best_combined["promotion_blocked_by_bucket_regression"],
        })

    # RRF baseline reference
    observations.append({
        "observation_type": "rrf_baseline_reference",
        "strategy_name": "rrf_raw",
        "params": {},
        "FileRecall@1": rrf_metrics.get("FileRecall@1"),
        "primary_false_positive_rate": rrf_metrics.get("primary_false_positive_rate"),
        "no_gold_nonempty_rate": rrf_metrics.get("no_gold_nonempty_rate"),
        "abstain_rate": rrf_metrics.get("abstain_rate"),
        "guard_recall_kill_rate": None,
        "promotion_blocked_by_bucket_regression": False,
    })

    # ── Count blocked buckets ──────────────────────────────────────────
    blocked_count = sum(1 for sr in sweep_results if sr["promotion_blocked_by_bucket_regression"])
    total_bucket_regressions = sum(len(sr["bucket_regressions"]) for sr in sweep_results)

    # ── Build report ──────────────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "workspace": str(workspace),
        "promotion_ready": False,
        "not_promotion_evidence": True,
        "source_report_sha": source_report_sha,
        "labels_sha": labels_sha,
        "artifact_manifest_sha": artifact_manifest_sha,
        "safety_checks": {
            "analysis_only_no_cli_invocations": True,
            "labels_only_score_phase": True,
            "artifact_manifest_exists": True,
            "artifact_manifest_sha_recorded": bool(artifact_manifest_sha),
            "artifact_files_sha_bytes_lines_verified": True,
            "artifact_files_checked": artifact_files_checked,
            "no_promotion_claims": True,
            "no_dense_llm_quiver_quality_claims": True,
            "promotion_ready": False,
            "not_promotion_evidence": True,
        },
        "sweep_count": len(sweep_strategies),
        "strategies": sweep_results,
        "curves": curves,
        "bucket_summary": bucket_summary,
        "observations": observations,
        "rrf_baseline_metrics": rrf_metrics,
        "blocked_bucket_counts": {
            "strategies_with_bucket_regression": blocked_count,
            "total_strategies": len(sweep_strategies),
            "total_bucket_regressions": total_bucket_regressions,
        },
        "phases": {
            "analysis": "score_only_no_cli",
            "labels_phase": "score_only",
            "guard_semantics": "based_on_raw_rrf_evidence_guard_fail_abstain",
            "agreement": "regex_symbol_predictions_evidence_presence",
            "score_threshold": "rrf_top_score",
            "gap_threshold": "top1_minus_top2_score",
            "identifier_density": "query_identifier_like_token_count",
            "candidate_channel_count": "top_evidence_channels_union",
            "routing": "no_labels_used_for_routing",
        },
        "tasks_count": len(rrf_preds),
        "labels_count": len(gold),
        "remote_calls": 0,
        "dense_or_llm_claims": False,
        "core_changes": False,
    }

    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    # ── Print summary ─────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"R23 Guard Parameter Sweep Results")
    print(f"{'='*70}")
    print(f"  sweep_count: {len(sweep_strategies)}")
    print(f"  strategies_with_bucket_regression: {blocked_count}/{len(sweep_strategies)}")
    print(f"  total_bucket_regressions: {total_bucket_regressions}")
    print(f"\n  RRF Baseline:")
    print(f"    FileRecall@1: {rrf_metrics.get('FileRecall@1', 0):.3f}")
    print(f"    primary_false_positive_rate: {rrf_metrics.get('primary_false_positive_rate', 0):.3f}")
    print(f"    no_gold_nonempty_rate: {rrf_metrics.get('no_gold_nonempty_rate', 0):.3f}")
    print(f"    abstain_rate: {rrf_metrics.get('abstain_rate', 0):.3f}")

    print(f"\n  Observations:")
    for obs in observations:
        print(f"    [{obs['observation_type']}] {obs['strategy_name']}: "
              f"FR@1={obs.get('FileRecall@1', 'N/A')}, "
              f"pfp={obs.get('primary_false_positive_rate', 'N/A')}, "
              f"ngne={obs.get('no_gold_nonempty_rate', 'N/A')}, "
              f"abstain={obs.get('abstain_rate', 'N/A')}, "
              f"kill={obs.get('guard_recall_kill_rate', 'N/A')}, "
              f"blocked={obs.get('promotion_blocked_by_bucket_regression', 'N/A')}")

    print(f"\n  Report: {out_path}")
    print(f"  promotion_ready: False")
    print(f"  not_promotion_evidence: True")


if __name__ == "__main__":
    main()
