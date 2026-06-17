#!/usr/bin/env python3
"""B4/B9 Model-Robust Evidence Conversion aggregate analyzer.

This is an aggregate-only, deterministic research report.  It separates
``algorithm_spec`` (model-independent strategy definitions) from
``model_adapter`` (model + output-mode health) and re-encodes the already
published live quality cells from B1, B1C, B2 and B3.  The current
implementation is a curated aggregate recoder/analyzer, not a raw artifact
ingester: it preserves already-published aggregate quality cells and computes
bounded robustness summaries over them.

The public artifact is aggregate-only.  No task IDs, candidate IDs, paths,
line ranges, digests, snippets, prompts, responses, private labels or gold spans
are emitted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "b4-b9-model-robust-evidence-conversion-v0"
GENERATED_BY = "b4_b9_model_robust_evidence_conversion"

DEFAULT_OUT = Path(
    "artifacts/b4_b9_model_robust_evidence_conversion/"
    "b4_b9_model_robust_evidence_conversion_report.json"
)
DEFAULT_DOCS = {
    "en": Path("docs/en/b4-b9-model-robust-evidence-conversion.md"),
    "zh": Path("docs/zh/b4-b9-model-robust-evidence-conversion.md"),
}

# ---------------------------------------------------------------------------
# Safety: forbidden keys and forbidden value patterns
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS = frozenset(
    {
        "task_id",
        "candidate_id",
        "path",
        "query",
        "start_line",
        "end_line",
        "content_sha",
        "snippet",
        "prompt",
        "response",
        "labels",
        "gold_spans",
        "decision_records",
        "candidate_meta",
        "api_key",
        "base_url",
        "provider",
        "provider_url",
        "raw_response",
        "line_range",
        "candidate_path",
        "private_labels",
        "label",
        "digest",
        "test_id",
        "repo_id",
    }
)

# Note: relative doc paths (e.g. "docs/en/foo.md") intentionally do not start
# with "/" or a drive letter, so they are not flagged.
_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"^(?:/|[A-Za-z]:\\)"),  # absolute paths
    re.compile(r"^https?://", re.I),
    re.compile(r"^sk-[A-Za-z0-9_-]+"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"base[_-]?url", re.I),
    re.compile(r"provider[_-]?url", re.I),
]

_LONG_STRING_THRESHOLD = 256

SOURCE_REPORTS = {
    "b1": "docs/en/b1-live-llm-rich-candidate-run.md",
    "b1c": "docs/en/b1c-cross-model-rich-candidate-rerun.md",
    "b2": "docs/en/b2-contrastive-pack-quality-experiment.md",
    "b3": "docs/en/b3-rmc-quality-experiment.md",
    "b3_artifact": "artifacts/b3_rmc_quality_experiment/b3_rmc_quality_experiment_report.json",
    "model_profiles": "eval/p21_model_profiles.json",
}

# ---------------------------------------------------------------------------
# Fixture: documented aggregate live cells from B1/B1C/B2/B3.
# No forbidden keys; run_ids are numeric public workflow run identifiers.
# ---------------------------------------------------------------------------

AGGREGATE_CELLS: list[dict[str, Any]] = [
    # -------------------- B1: Kimi-K2.7-Code tool_call --------------------
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "candidate_baseline_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "baseline",
        "task_count": 24,
        "added_gold_span": 8,
        "added_false_span": 43,
        "mean_span_f05": 0.1099,
        "mean_pfp": 0.1250,
        "false_per_gold": 5.375,
        "latency_p50_ms": 2310,
        "input_chars": 34024,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27674929320, 27674930653, 27674932153, 27674933629],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 9,
        "added_false_span": 5,
        "mean_span_f05": 0.2849,
        "mean_pfp": 0.0625,
        "false_per_gold": 0.556,
        "latency_p50_ms": 2310,
        "input_chars": 34024,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27674929320, 27674930653, 27674932153, 27674933629],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 7,
        "mean_span_f05": 0.1884,
        "mean_pfp": 0.0625,
        "false_per_gold": 1.000,
        "latency_p50_ms": 2310,
        "input_chars": 34024,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27674929320, 27674930653, 27674932153, 27674933629],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "p25_bucket_routed_v0_plain",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "policy",
        "task_count": 24,
        "added_gold_span": 8,
        "added_false_span": 6,
        "mean_span_f05": 0.1139,
        "mean_pfp": 0.0417,
        "false_per_gold": 0.750,
        "latency_p50_ms": 2310,
        "input_chars": 34024,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27674929320, 27674930653, 27674932153, 27674933629],
    },
    # -------------------- B1: Kimi json_schema_strict --------------------
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "candidate_baseline_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "baseline",
        "task_count": 24,
        "added_gold_span": 8,
        "added_false_span": 44,
        "mean_span_f05": 0.1099,
        "mean_pfp": 0.1250,
        "false_per_gold": 5.500,
        "latency_p50_ms": 3529,
        "input_chars": 34714,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27675200878, 27675202356, 27675203807, 27675205460],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 9,
        "added_false_span": 8,
        "mean_span_f05": 0.2829,
        "mean_pfp": 0.1250,
        "false_per_gold": 0.889,
        "latency_p50_ms": 3529,
        "input_chars": 34714,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27675200878, 27675202356, 27675203807, 27675205460],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 10,
        "mean_span_f05": 0.1884,
        "mean_pfp": 0.1250,
        "false_per_gold": 1.429,
        "latency_p50_ms": 3529,
        "input_chars": 34714,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27675200878, 27675202356, 27675203807, 27675205460],
    },
    {
        "experiment_id": "b1",
        "algorithm_spec_id": "p25_bucket_routed_v0_plain",
        "model_adapter_id": "kimi_k2_7_code_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "policy",
        "task_count": 24,
        "added_gold_span": 8,
        "added_false_span": 9,
        "mean_span_f05": 0.0914,
        "mean_pfp": 0.0833,
        "false_per_gold": 1.125,
        "latency_p50_ms": 3529,
        "input_chars": 34714,
        "source_report": SOURCE_REPORTS["b1"],
        "run_ids": [27675200878, 27675202356, 27675203807, 27675205460],
    },
    # -------------------- B1C: cross-model, topk_plain_v0 --------------------
    # Kimi tool_call reference is intentionally encoded from B2 for the
    # topk_plain pack-layout because B2 is the dedicated pack-layout contrast.
    # Qwen and GLM results below are plumbing/health evidence only.
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "qwen3_6_27b_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 16,
        "added_gold_span": 2,
        "added_false_span": 1,
        "mean_span_f05": 0.0482,
        "mean_pfp": 0.0000,
        "false_per_gold": 0.500,
        "latency_p50_ms": 3006,
        "input_chars": 31011,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679321065, 27679322323, 27679323715, 27679325182],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "qwen3_6_27b_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 16,
        "added_gold_span": 2,
        "added_false_span": 1,
        "mean_span_f05": None,
        "mean_pfp": 0.0000,
        "false_per_gold": 0.500,
        "latency_p50_ms": 3006,
        "input_chars": 31011,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679321065, 27679322323, 27679323715, 27679325182],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "qwen3_6_27b_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 15,
        "added_gold_span": 0,
        "added_false_span": 0,
        "mean_span_f05": 0.0000,
        "mean_pfp": 0.0000,
        "false_per_gold": None,
        "latency_p50_ms": 43478,
        "input_chars": 30893,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679882877, 27679884241, 27679886001, 27679887698],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "qwen3_6_27b_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 15,
        "added_gold_span": 0,
        "added_false_span": 0,
        "mean_span_f05": None,
        "mean_pfp": 0.0000,
        "false_per_gold": None,
        "latency_p50_ms": 43478,
        "input_chars": 30893,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679882877, 27679884241, 27679886001, 27679887698],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "glm_5_2_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 13,
        "added_gold_span": 0,
        "added_false_span": 0,
        "mean_span_f05": 0.0000,
        "mean_pfp": 0.0000,
        "false_per_gold": None,
        "latency_p50_ms": 2166,
        "input_chars": 31580,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679326330, 27679327829, 27679329334, 27679330585],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "glm_5_2_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 13,
        "added_gold_span": 0,
        "added_false_span": 0,
        "mean_span_f05": None,
        "mean_pfp": 0.0000,
        "false_per_gold": None,
        "latency_p50_ms": 2166,
        "input_chars": 31580,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679326330, 27679327829, 27679329334, 27679330585],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "glm_5_2_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 7,
        "mean_span_f05": 0.2192,
        "mean_pfp": 0.0625,
        "false_per_gold": 1.000,
        "latency_p50_ms": 2575,
        "input_chars": 30922,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679889143, 27679890671, 27679892076, 27679893465],
    },
    {
        "experiment_id": "b1c",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "glm_5_2_json_schema_strict",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 5,
        "added_false_span": 9,
        "mean_span_f05": None,
        "mean_pfp": 0.0625,
        "false_per_gold": 1.800,
        "latency_p50_ms": 2575,
        "input_chars": 30922,
        "source_report": SOURCE_REPORTS["b1c"],
        "run_ids": [27679889143, 27679890671, 27679892076, 27679893465],
    },
    # -------------------- B2: pack-layout contrast, Kimi tool_call --------------------
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "span_narrow_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 9,
        "added_false_span": 6,
        "mean_span_f05": 0.2691,
        "mean_pfp": 0.0625,
        "false_per_gold": 0.667,
        "latency_p50_ms": 3642,
        "input_chars": 31484,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27676829411, 27676830935, 27676832373, 27676833797],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "filter_topk_plain_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 8,
        "mean_span_f05": 0.1751,
        "mean_pfp": 0.0625,
        "false_per_gold": 1.143,
        "latency_p50_ms": 3642,
        "input_chars": 31484,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27676829411, 27676830935, 27676832373, 27676833797],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "span_narrow_topk_scores_provenance_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_scores_provenance_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 9,
        "added_false_span": 7,
        "mean_span_f05": 0.2829,
        "mean_pfp": 0.1250,
        "false_per_gold": 0.778,
        "latency_p50_ms": 5547,
        "input_chars": 39120,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27677245697, 27677246972, 27677248171, 27677249614],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "filter_topk_scores_provenance_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_scores_provenance_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 9,
        "mean_span_f05": 0.1884,
        "mean_pfp": 0.1250,
        "false_per_gold": 1.286,
        "latency_p50_ms": 5547,
        "input_chars": 39120,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27677245697, 27677246972, 27677248171, 27677249614],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "span_narrow_contrastive_competitor_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "contrastive_competitor_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 9,
        "added_false_span": 8,
        "mean_span_f05": 0.2694,
        "mean_pfp": 0.1250,
        "false_per_gold": 0.889,
        "latency_p50_ms": 2824,
        "input_chars": 40144,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27677251043, 27677252254, 27677253878, 27677255224],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "filter_contrastive_competitor_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "contrastive_competitor_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 10,
        "mean_span_f05": 0.1751,
        "mean_pfp": 0.1250,
        "false_per_gold": 1.429,
        "latency_p50_ms": 2824,
        "input_chars": 40144,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27677251043, 27677252254, 27677253878, 27677255224],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "span_narrow_hard_distractor_contrast_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "hard_distractor_contrast_v0",
        "role": "span_narrow",
        "task_count": 24,
        "added_gold_span": 7,
        "added_false_span": 5,
        "mean_span_f05": 0.2820,
        "mean_pfp": 0.1250,
        "false_per_gold": 0.714,
        "latency_p50_ms": 3074,
        "input_chars": 41494,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27676835457, 27676837060, 27676838404, 27676839848],
    },
    {
        "experiment_id": "b2",
        "algorithm_spec_id": "filter_hard_distractor_contrast_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "hard_distractor_contrast_v0",
        "role": "filter",
        "task_count": 24,
        "added_gold_span": 5,
        "added_false_span": 7,
        "mean_span_f05": 0.1880,
        "mean_pfp": 0.1250,
        "false_per_gold": 1.400,
        "latency_p50_ms": 3074,
        "input_chars": 41494,
        "source_report": SOURCE_REPORTS["b2"],
        "run_ids": [27676835457, 27676837060, 27676838404, 27676839848],
    },
    # -------------------- B3: RMC policy, Kimi tool_call --------------------
    {
        "experiment_id": "b3",
        "algorithm_spec_id": "p25_bucket_routed_v0_plain",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0+hard_distractor_contrast_v0",
        "role": "policy",
        "task_count": 12,
        "added_gold_span": 8,
        "added_false_span": 7,
        "mean_span_f05": 0.0890,
        "mean_pfp": 0.0417,
        "false_per_gold": 0.875,
        "latency_p50_ms": None,
        "input_chars": None,
        "source_report": SOURCE_REPORTS["b3"],
        "run_ids": [27682471959, 27682473463, 27682474976, 27682476342],
    },
    {
        "experiment_id": "b3",
        "algorithm_spec_id": "rmc_hybrid_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0+hard_distractor_contrast_v0",
        "role": "policy",
        "task_count": 12,
        "added_gold_span": 7,
        "added_false_span": 8,
        "mean_span_f05": 0.0820,
        "mean_pfp": 0.0833,
        "false_per_gold": 1.143,
        "latency_p50_ms": None,
        "input_chars": None,
        "source_report": SOURCE_REPORTS["b3"],
        "run_ids": [27682471959, 27682473463, 27682474976, 27682476342],
    },
    {
        "experiment_id": "b3",
        "algorithm_spec_id": "rmc_llm_pack_routed_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "topk_plain_v0+hard_distractor_contrast_v0",
        "role": "policy",
        "task_count": 12,
        "added_gold_span": 7,
        "added_false_span": 8,
        "mean_span_f05": 0.0820,
        "mean_pfp": 0.0833,
        "false_per_gold": 1.143,
        "latency_p50_ms": None,
        "input_chars": None,
        "source_report": SOURCE_REPORTS["b3"],
        "run_ids": [27682471959, 27682473463, 27682474976, 27682476342],
    },
    {
        "experiment_id": "b3",
        "algorithm_spec_id": "rmc_local_conservative_v0",
        "model_adapter_id": "kimi_k2_7_code_tool_call",
        "pack_layout": "n/a",
        "role": "policy",
        "task_count": 12,
        "added_gold_span": 4,
        "added_false_span": 18,
        "mean_span_f05": 0.0226,
        "mean_pfp": 0.0000,
        "false_per_gold": 4.500,
        "latency_p50_ms": None,
        "input_chars": None,
        "source_report": SOURCE_REPORTS["b3"],
        "run_ids": [27682471959, 27682473463, 27682474976, 27682476342],
    },
]

# ---------------------------------------------------------------------------
# Algorithm specs (model-independent definitions)
# ---------------------------------------------------------------------------

ALGORITHM_SPECS: dict[str, dict[str, Any]] = {
    "candidate_baseline_topk_plain_v0": {
        "name": "Candidate baseline over topk_plain_v0",
        "role": "baseline",
        "pack_layout": "topk_plain_v0",
        "description": (
            "Top-k candidate baseline without LLM span narrowing or filtering."
        ),
    },
    "p25_bucket_routed_v0_plain": {
        "name": "P25 bucket_routed_v0 over topk_plain_v0",
        "role": "policy",
        "pack_layout": "topk_plain_v0",
        "description": (
            "Existing P25 bucket-routed policy that chooses span_narrow, filter, "
            "or candidate baseline from public task/risk buckets."
        ),
    },
    "span_narrow_topk_plain_v0": {
        "name": "Span narrow over topk_plain_v0",
        "role": "span_narrow",
        "pack_layout": "topk_plain_v0",
        "description": "LLM span narrowing with ordinary top-k bounded snippets.",
    },
    "span_narrow_topk_scores_provenance_v0": {
        "name": "Span narrow over topk_scores_provenance_v0",
        "role": "span_narrow",
        "pack_layout": "topk_scores_provenance_v0",
        "description": (
            "LLM span narrowing with retrieval score/provenance/channel metadata."
        ),
    },
    "span_narrow_contrastive_competitor_v0": {
        "name": "Span narrow over contrastive_competitor_v0",
        "role": "span_narrow",
        "pack_layout": "contrastive_competitor_v0",
        "description": (
            "LLM span narrowing with competitor slots but no hard-distractor proxies."
        ),
    },
    "span_narrow_hard_distractor_contrast_v0": {
        "name": "Span narrow over hard_distractor_contrast_v0",
        "role": "span_narrow",
        "pack_layout": "hard_distractor_contrast_v0",
        "description": (
            "LLM span narrowing with metadata-selected hard-distractor proxies."
        ),
    },
    "filter_topk_plain_v0": {
        "name": "Filter over topk_plain_v0",
        "role": "filter",
        "pack_layout": "topk_plain_v0",
        "description": "LLM filter over ordinary top-k bounded snippets.",
    },
    "filter_topk_scores_provenance_v0": {
        "name": "Filter over topk_scores_provenance_v0",
        "role": "filter",
        "pack_layout": "topk_scores_provenance_v0",
        "description": "LLM filter with retrieval score/provenance metadata.",
    },
    "filter_contrastive_competitor_v0": {
        "name": "Filter over contrastive_competitor_v0",
        "role": "filter",
        "pack_layout": "contrastive_competitor_v0",
        "description": "LLM filter with competitor slots.",
    },
    "filter_hard_distractor_contrast_v0": {
        "name": "Filter over hard_distractor_contrast_v0",
        "role": "filter",
        "pack_layout": "hard_distractor_contrast_v0",
        "description": "LLM filter with hard-distractor proxies.",
    },
    "rmc_hybrid_v0": {
        "name": "RMC hybrid v0",
        "role": "policy",
        "pack_layout": "topk_plain_v0+hard_distractor_contrast_v0",
        "description": (
            "Fixed RMC policy: weak for unsupported cases, plain span narrow for "
            "positive supported cases, hard-distractor filter for no-gold/hard cases."
        ),
    },
    "rmc_llm_pack_routed_v0": {
        "name": "RMC LLM pack routed v0",
        "role": "policy",
        "pack_layout": "topk_plain_v0+hard_distractor_contrast_v0",
        "description": (
            "Fixed RMC policy: plain span narrow for positives, hard-distractor "
            "filter for no-gold/hard/ambiguous cases."
        ),
    },
    "rmc_local_conservative_v0": {
        "name": "RMC local conservative v0",
        "role": "policy",
        "pack_layout": "n/a",
        "description": (
            "Fixed RMC policy: suppress negative/hard/no-gold/ambiguous cases to "
            "weak candidate only with no extra LLM call."
        ),
    },
}

# ---------------------------------------------------------------------------
# Model adapter health
# ---------------------------------------------------------------------------

MODEL_ADAPTER_OVERRIDES: dict[str, dict[str, Any]] = {
    "kimi_k2_7_code_tool_call": {
        "quality_interpretable": True,
        "health": "healthy_primary_reference",
        "notes": (
            "Primary Breakthrough Sprint reference: full schema stability, low "
            "fallback, strong span-narrow signal."
        ),
    },
    "kimi_k2_7_code_json_schema_strict": {
        "quality_interpretable": True,
        "health": "healthy_but_slower_and_weaker",
        "notes": (
            "Schema-stable but slower and leaves more false spans than tool_call."
        ),
    },
    "qwen3_6_27b_tool_call": {
        "quality_interpretable": False,
        "health": "degraded_rate_limit",
        "notes": (
            "Both Qwen output modes hit substantial rate-limit/fallback noise; "
            "do not include in quality aggregate until lower-concurrency fix."
        ),
    },
    "qwen3_6_27b_json_schema_strict": {
        "quality_interpretable": False,
        "health": "degraded_rate_limit",
        "notes": (
            "Severe rate-limit/fallback noise and very high latency; not quality-"
            "interpretable."
        ),
    },
    "glm_5_2_tool_call": {
        "quality_interpretable": False,
        "health": "degraded_bad_response",
        "notes": (
            "Tool-call mode produced bad-response-status-code noise; not suitable "
            "for quality aggregate."
        ),
    },
    "glm_5_2_json_schema_strict": {
        "quality_interpretable": True,
        "health": "secondary_cross_family_validation",
        "notes": (
            "Viable for controlled cross-family comparison, but weaker than Kimi "
            "tool_call."
        ),
    },
}

ADAPTER_PROFILE_MAP: dict[str, tuple[str, str]] = {
    "kimi_k2_7_code_tool_call": ("kimi_k2_7_code", "tool_call"),
    "kimi_k2_7_code_json_schema_strict": (
        "kimi_k2_7_code",
        "json_schema_strict",
    ),
    "qwen3_6_27b_tool_call": ("qwen3_6_27b_code_balanced", "tool_call"),
    "qwen3_6_27b_json_schema_strict": (
        "qwen3_6_27b_code_balanced",
        "json_schema_strict",
    ),
    "glm_5_2_tool_call": ("glm_5_2_reasoning_code", "tool_call"),
    "glm_5_2_json_schema_strict": (
        "glm_5_2_reasoning_code",
        "json_schema_strict",
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den is None:
        return None
    if den == 0:
        return None
    return num / den


def _avg(values: Sequence[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def _min(values: Sequence[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return min(clean) if clean else None


def _max(values: Sequence[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return max(clean) if clean else None


def _round4(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_model_adapters() -> dict[str, dict[str, Any]]:
    profiles_path = REPO / SOURCE_REPORTS["model_profiles"]
    profiles = _load_json(profiles_path)
    llm_profiles: dict[str, dict[str, Any]] = {}
    if isinstance(profiles, dict):
        for prof in profiles.get("llm_profiles", []):
            pid = prof.get("profile_id")
            if pid:
                llm_profiles[pid] = prof

    adapters: dict[str, dict[str, Any]] = {}
    for adapter_id, override in MODEL_ADAPTER_OVERRIDES.items():
        if adapter_id not in ADAPTER_PROFILE_MAP:
            raise ValueError(f"missing explicit adapter profile mapping: {adapter_id}")
        profile_id, output_mode = ADAPTER_PROFILE_MAP[adapter_id]
        prof = llm_profiles.get(profile_id, {})
        adapters[adapter_id] = {
            "adapter_id": adapter_id,
            "parent_profile_id": profile_id,
            "output_mode": output_mode,
            "model_id": prof.get("model_id"),
            "family": prof.get("family"),
            "cost_class": prof.get("cost_class"),
            "latency_class": prof.get("latency_class"),
            "quality_interpretable": override["quality_interpretable"],
            "health": override["health"],
            "notes": override["notes"],
        }
    return adapters


def _walk_forbidden(obj: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key) in FORBIDDEN_KEYS:
                violations.append(f"{path}.{key}")
            violations.extend(_walk_forbidden(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_walk_forbidden(value, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        if len(obj) > _LONG_STRING_THRESHOLD:
            violations.append(f"{path}:long_string")
        elif any(p.search(obj) for p in _FORBIDDEN_VALUE_PATTERNS):
            violations.append(f"{path}:private_like_value")
    return violations


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bad schema_version")

    must_true = [
        "aggregate_only_public_artifact",
        "llm_output_not_evidence",
        "not_evidence",
    ]
    for key in must_true:
        if report.get(key) is not True:
            raise ValueError(f"{key} must be true")

    must_false = [
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "llm_direct_evidence_allowed",
        "raw_prompts_in_report",
        "raw_responses_in_report",
        "raw_snippets_in_report",
        "raw_paths_in_report",
        "raw_line_ranges_in_report",
        "raw_digests_in_report",
        "task_ids_in_report",
        "candidate_ids_in_report",
    ]
    for key in must_false:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")

    violations = _walk_forbidden(report)
    if violations:
        raise ValueError(
            "forbidden public content: " + ", ".join(violations[:10])
        )

    cells = report.get("aggregate_cells") or []
    for cell in cells:
        for key in (
            "experiment_id",
            "algorithm_spec_id",
            "model_adapter_id",
            "task_count",
        ):
            if key not in cell:
                raise ValueError(f"aggregate cell missing {key}")

    adapters = report.get("model_adapters") or {}
    for aid, adata in adapters.items():
        if "quality_interpretable" not in adata:
            raise ValueError(f"adapter {aid} missing quality_interpretable")

    for rec in report.get("recommendations") or []:
        target_type = rec.get("target_type")
        if target_type == "algorithm_spec":
            if not rec.get("algorithm_spec_id") or rec.get("model_adapter_id"):
                raise ValueError("algorithm recommendation target is malformed")
        elif target_type == "model_adapter":
            if not rec.get("model_adapter_id") or rec.get("algorithm_spec_id"):
                raise ValueError("adapter recommendation target is malformed")
        else:
            raise ValueError(f"bad recommendation target_type: {target_type}")


# ---------------------------------------------------------------------------
# Robustness summaries
# ---------------------------------------------------------------------------

# Default claim level per algorithm spec.  These are bounded, aggregate-only
# research claims taken from the B1/B1C/B2/B3 reports.
DEFAULT_CLAIMS: dict[str, str] = {
    "candidate_baseline_topk_plain_v0": "observed_only",
    "p25_bucket_routed_v0_plain": "observed_only",
    "span_narrow_topk_plain_v0": "low_n_directional_signal",
    "span_narrow_topk_scores_provenance_v0": "fragile_signal",
    "span_narrow_contrastive_competitor_v0": "fragile_signal",
    "span_narrow_hard_distractor_contrast_v0": "not_supported",
    "filter_topk_plain_v0": "observed_only",
    "filter_topk_scores_provenance_v0": "fragile_signal",
    "filter_contrastive_competitor_v0": "fragile_signal",
    "filter_hard_distractor_contrast_v0": "not_supported",
    "rmc_hybrid_v0": "not_supported",
    "rmc_llm_pack_routed_v0": "not_supported",
    "rmc_local_conservative_v0": "not_supported",
}

BASELINE_SPEC_FOR_ROLE: dict[str, str] = {
    "span_narrow": "candidate_baseline_topk_plain_v0",
    "filter": "candidate_baseline_topk_plain_v0",
    "policy": "p25_bucket_routed_v0_plain",
    "baseline": "candidate_baseline_topk_plain_v0",
}


def _comparison_group_id(cell: dict[str, Any]) -> str:
    return f"{cell.get('experiment_id')}::{cell.get('model_adapter_id')}"


def _baseline_spec_for_cell(cell: dict[str, Any]) -> str | None:
    algo_id = str(cell.get("algorithm_spec_id") or "")
    experiment_id = str(cell.get("experiment_id") or "")
    role = str(cell.get("role") or "")

    if algo_id == "candidate_baseline_topk_plain_v0":
        return None
    if experiment_id == "b2":
        if algo_id == "span_narrow_topk_plain_v0":
            return None
        if algo_id == "filter_topk_plain_v0":
            return None
        if role == "span_narrow":
            return "span_narrow_topk_plain_v0"
        if role == "filter":
            return "filter_topk_plain_v0"
    if experiment_id == "b3":
        if algo_id == "p25_bucket_routed_v0_plain":
            return None
        return "p25_bucket_routed_v0_plain"
    return BASELINE_SPEC_FOR_ROLE.get(role)


def _effect_status(delta_span_f05: float | None, adapter_count: int) -> str:
    if delta_span_f05 is None or adapter_count == 0:
        return "insufficient_data"
    if delta_span_f05 > 0.04:
        if adapter_count < 3:
            return "low_n_directional_signal"
        return "directional_signal"
    if delta_span_f05 > 0.0:
        if adapter_count < 3:
            return "low_n_fragile_signal"
        return "fragile_signal"
    if adapter_count == 1:
        return "single_adapter_caution"
    return "negative_or_flat"


def _variance_status(delta_values: list[float]) -> str:
    values = [v for v in delta_values if v is not None]
    if len(values) < 2:
        return "insufficient_model_overlap"
    span = max(values) - min(values)
    if span <= 0.02:
        return "low"
    if span <= 0.05:
        return "medium"
    return "high"


def _leave_one_status(delta_values: list[float]) -> tuple[str, dict[str, Any]]:
    values = [v for v in delta_values if v is not None]
    if len(values) < 2:
        return "insufficient_model_overlap", {
            "leave_one_delta_min": None,
            "leave_one_delta_max": None,
        }
    leave_one_means: list[float] = []
    for idx in range(len(values)):
        rest = values[:idx] + values[idx + 1 :]
        leave_one_means.append(sum(rest) / len(rest))
    lo = min(leave_one_means)
    hi = max(leave_one_means)
    if all(v > 0 for v in leave_one_means):
        status = "leave_one_positive_low_n" if len(values) < 3 else "stable_positive"
    elif all(v <= 0 for v in leave_one_means):
        status = "leave_one_non_positive"
    else:
        status = "fragile_leave_one_mixed"
    return status, {
        "leave_one_delta_min": _round4(lo),
        "leave_one_delta_max": _round4(hi),
    }


def _insufficient_leave_one() -> tuple[str, dict[str, Any]]:
    return "insufficient_model_overlap", {
        "leave_one_delta_min": None,
        "leave_one_delta_max": None,
    }


def _matched_baseline_index(cells: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in cells:
        out[(cell["algorithm_spec_id"], _comparison_group_id(cell))] = cell
    return out


def _target_recommendation(
    target_type: str,
    target_id: str,
    claim_level: str,
    recommendation: str,
) -> dict[str, Any]:
    if target_type == "algorithm_spec":
        return {
            "target_type": target_type,
            "algorithm_spec_id": target_id,
            "claim_level": claim_level,
            "recommendation": recommendation,
        }
    if target_type == "model_adapter":
        return {
            "target_type": target_type,
            "model_adapter_id": target_id,
            "claim_level": claim_level,
            "recommendation": recommendation,
        }
    raise ValueError(f"bad recommendation target_type: {target_type}")


def _cells_by_algorithm(cells: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        out[cell["algorithm_spec_id"]].append(cell)
    return dict(out)


def _cells_by_adapter(cells: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for cell in cells:
        out[cell["model_adapter_id"]] = cell
    return out


def _compute_effects(
    cells: list[dict[str, Any]], adapters: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    quality_adapter_ids = {
        aid for aid, adata in adapters.items() if adata["quality_interpretable"]
    }
    by_algo = _cells_by_algorithm(cells)
    baseline_index = _matched_baseline_index(cells)

    effects: list[dict[str, Any]] = []
    per_algo_summary: dict[str, dict[str, Any]] = {}

    for algo_id, algo_cells in by_algo.items():
        if algo_id == "candidate_baseline_topk_plain_v0":
            continue
        spec = ALGORITHM_SPECS.get(algo_id, {})
        role = spec.get("role") or "unknown"

        deltas: dict[str, float] = {}
        per_adapter: dict[str, dict[str, Any]] = {}
        quality_deltas_by_adapter: dict[str, list[float]] = defaultdict(list)

        for cell in algo_cells:
            adapter_id = cell["model_adapter_id"]
            algo_span = cell.get("mean_span_f05")
            group_id = _comparison_group_id(cell)
            baseline_id = _baseline_spec_for_cell(cell)
            base_cell = (
                baseline_index.get((baseline_id, group_id))
                if baseline_id is not None
                else None
            )
            base_span = base_cell.get("mean_span_f05") if base_cell else None

            if adapter_id not in per_adapter:
                per_adapter[adapter_id] = {
                    "quality_interpretable": adapter_id in quality_adapter_ids,
                    "cells": [],
                    "matched_delta_count": 0,
                    "mean_span_f05": None,
                    "delta_span_f05_vs_baseline": None,
                }
            per_adapter[adapter_id]["cells"].append(
                {
                    "experiment_id": cell.get("experiment_id"),
                    "comparison_group_id": group_id,
                    "mean_span_f05": algo_span,
                    "baseline_spec_id": baseline_id,
                    "baseline_mean_span_f05": base_span,
                    "matched_baseline": base_span is not None,
                }
            )
            spans = [c["mean_span_f05"] for c in per_adapter[adapter_id]["cells"]]
            per_adapter[adapter_id]["mean_span_f05"] = _round4(_avg(spans))

            if algo_span is None or adapter_id not in quality_adapter_ids:
                continue
            delta = (
                _round4(algo_span - base_span)
                if base_span is not None
                else None
            )
            if delta is not None:
                quality_deltas_by_adapter[adapter_id].append(delta)

        for adapter_id, adapter_deltas in quality_deltas_by_adapter.items():
            adapter_mean_delta = _round4(_avg(adapter_deltas))
            if adapter_mean_delta is not None:
                deltas[adapter_id] = adapter_mean_delta
            per_adapter[adapter_id]["matched_delta_count"] = len(adapter_deltas)
            per_adapter[adapter_id]["delta_span_f05_vs_baseline"] = adapter_mean_delta

        quality_deltas = list(deltas.values())
        adapter_count = len(quality_deltas)
        mean_delta = _round4(_avg(quality_deltas))
        variance = _variance_status(quality_deltas)
        effect_st = _effect_status(mean_delta, adapter_count)
        leave_one, leave_one_range = _leave_one_status(quality_deltas)
        representative_baseline_id = BASELINE_SPEC_FOR_ROLE.get(
            role, "candidate_baseline_topk_plain_v0"
        )

        effects.append(
            {
                "algorithm_spec_id": algo_id,
                "role": role,
                "baseline_spec_id": representative_baseline_id,
                "baseline_matching": "comparison_group_id",
                "model_adapter_count": adapter_count,
                "model_averaged_delta_span_f05": mean_delta,
                "effect_status": effect_st,
                "effect_range_by_model": {
                    "min_delta_span_f05": _round4(_min(quality_deltas)),
                    "max_delta_span_f05": _round4(_max(quality_deltas)),
                    **leave_one_range,
                },
                "per_model_delta": per_adapter,
            }
        )

        per_algo_summary[algo_id] = {
            "role": role,
            "model_adapter_count": adapter_count,
            "model_averaged_delta_span_f05": mean_delta,
            "effect_status": effect_st,
            "model_effect_variance_status": variance,
            "leave_one_model_status": leave_one,
            "repo_variance_status": "unavailable_aggregate_only",
            "claim_level": DEFAULT_CLAIMS.get(algo_id, "observed_only"),
        }

    return effects, per_algo_summary


def _build_recommendations(
    per_algo_summary: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    recs = [
        _target_recommendation(
            "algorithm_spec",
            "span_narrow_topk_plain_v0",
            "low_n_directional_signal",
            "Positive on matched aggregate cells, but not general: verify on a "
            "broader public corpus and held-out models before any default change.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "span_narrow_hard_distractor_contrast_v0",
            "not_supported",
            "Not globally supported as a span-narrow pack; route hard-distractor "
            "contrast only to selective filter/no-gold cases after repair.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "filter_hard_distractor_contrast_v0",
            "not_supported",
            "Hard-distractor filter lost gold in this bounded sample; do not adopt "
            "globally without repair.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "span_narrow_topk_scores_provenance_v0",
            "fragile_signal",
            "Fragile trade-off: higher SpanF0.5 but more false spans, higher PFP, "
            "and higher latency. Use selectively, not as default.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "rmc_hybrid_v0",
            "not_supported",
            "Fixed RMC hybrid did not beat P25; needs interpretable policy search "
            "or narrower bucket-specific routing.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "rmc_llm_pack_routed_v0",
            "not_supported",
            "Fixed RMC LLM routing did not beat P25; needs searched routing.",
        ),
        _target_recommendation(
            "algorithm_spec",
            "rmc_local_conservative_v0",
            "not_supported",
            "Local conservative route avoided false positives but collapsed recall.",
        ),
        _target_recommendation(
            "model_adapter",
            "qwen3_6_27b_tool_call",
            "not_supported",
            "Adapter degraded/rate-limit; exclude from quality aggregation until a "
            "lower-concurrency fix is validated.",
        ),
        _target_recommendation(
            "model_adapter",
            "qwen3_6_27b_json_schema_strict",
            "not_supported",
            "Adapter degraded/rate-limit; exclude from quality aggregation until a "
            "lower-concurrency fix is validated.",
        ),
        _target_recommendation(
            "model_adapter",
            "glm_5_2_json_schema_strict",
            "observed_only",
            "Usable as secondary cross-family validation; do not use as primary reference.",
        ),
    ]
    return recs


# ---------------------------------------------------------------------------
# Optional B3 artifact ingestion (ignored if it is only a self-test artifact)
# ---------------------------------------------------------------------------

def _maybe_load_b3_artifact_cells() -> list[dict[str, Any]]:
    path = REPO / SOURCE_REPORTS["b3_artifact"]
    data = _load_json(path)
    if not isinstance(data, dict):
        return []
    if data.get("live_quality_experiment") is True and data.get("status") == "ok":
        # Real B3 artifact: could be mapped here.  The committed artifact is
        # self-test-only, so this branch is reserved for future real artifacts.
        return []
    return []


# ---------------------------------------------------------------------------
# Report construction
# ---------------------------------------------------------------------------

def build_report(self_test: bool) -> dict[str, Any]:
    adapters = _load_model_adapters()
    cells = list(AGGREGATE_CELLS) + _maybe_load_b3_artifact_cells()

    effects, per_algo_summary = _compute_effects(cells, adapters)
    recommendations = _build_recommendations(per_algo_summary)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "status": "self_test_only" if self_test else "ok",
        "self_test": bool(self_test),
        "aggregate_only_public_artifact": True,
        "not_evidence": True,
        "llm_output_not_evidence": True,
        "llm_direct_evidence_allowed": False,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "raw_prompts_in_report": False,
        "raw_responses_in_report": False,
        "raw_snippets_in_report": False,
        "raw_paths_in_report": False,
        "raw_line_ranges_in_report": False,
        "raw_digests_in_report": False,
        "task_ids_in_report": False,
        "candidate_ids_in_report": False,
        "algorithm_specs": {
            k: {"algorithm_spec_id": k, **v}
            for k, v in sorted(ALGORITHM_SPECS.items())
        },
        "model_adapters": adapters,
        "aggregate_cells": cells,
        "robustness_summary": {
            "model_averaged_treatment_effects": effects,
            "algorithm_claim_levels": {
                k: v["claim_level"]
                for k, v in sorted(per_algo_summary.items())
            },
            "effect_status_by_algorithm": {
                k: v["effect_status"]
                for k, v in sorted(per_algo_summary.items())
            },
            "model_effect_variance_status": {
                k: v["model_effect_variance_status"]
                for k, v in sorted(per_algo_summary.items())
            },
            "leave_one_model_status": {
                k: v["leave_one_model_status"]
                for k, v in sorted(per_algo_summary.items())
            },
            "repo_variance_status": {
                k: v["repo_variance_status"]
                for k, v in sorted(per_algo_summary.items())
            },
        },
        "recommendations": recommendations,
        "source_reports": sorted(set(SOURCE_REPORTS.values())),
    }
    validate_report(report)
    _run_internal_assertions(report)
    return report


def _run_internal_assertions(report: dict[str, Any]) -> None:
    violations = _walk_forbidden(report)
    assert not violations, f"forbidden keys/values found: {violations[:5]}"

    adapters = report["model_adapters"]
    for aid in (
        "qwen3_6_27b_tool_call",
        "qwen3_6_27b_json_schema_strict",
    ):
        assert (
            adapters[aid]["quality_interpretable"] is False
        ), f"{aid} must not be quality-interpretable"

    kimi_claim = report["robustness_summary"]["algorithm_claim_levels"].get(
        "span_narrow_topk_plain_v0", "observed_only"
    )
    assert kimi_claim in (
        "directional_signal",
        "low_n_directional_signal",
        "candidate_for_materialization_experiment",
    ), f"unexpected Kimi topk_plain claim: {kimi_claim}"

    rmc_specs = ("rmc_hybrid_v0", "rmc_llm_pack_routed_v0", "rmc_local_conservative_v0")
    claim_levels = report["robustness_summary"]["algorithm_claim_levels"]
    for spec in rmc_specs:
        assert (
            claim_levels.get(spec) == "not_supported"
        ), f"fixed RMC variant {spec} must be not_supported"

    # Model-averaged delta for the primary span-narrow spec should be positive.
    effects = report["robustness_summary"]["model_averaged_treatment_effects"]
    for eff in effects:
        if eff["algorithm_spec_id"] == "span_narrow_topk_plain_v0":
            delta = eff.get("model_averaged_delta_span_f05")
            assert delta is not None and delta > 0, (
                f"expected positive model-averaged delta for span_narrow_topk_"
                f"plain_v0, got {delta}"
            )

    # Path/URL safety: every source_report value must be a relative repo path.
    for sr in report["source_reports"]:
        assert not (
            sr.startswith("/") or sr.startswith("http://") or sr.startswith("https://")
        ), f"source_report must be relative: {sr}"


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown_en(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B4/B9 Model-Robust Evidence Conversion")
    lines.append("")
    lines.append(f"Date: {_now()[:10]}")
    lines.append("")
    lines.append(
        "This aggregate-only report separates ``algorithm_spec`` (model-"
        "independent strategy definitions) from ``model_adapter`` (model + output-"
        "mode health).  It re-encodes the live quality cells documented in B1, "
        "B1C, B2 and B3."
    )
    lines.append("")
    lines.append(
        "B4/B9 is not a gate, not a precondition-only stage, and does not change "
        "``EvidenceCore``.  LLM outputs are still candidates, not Evidence."
    )
    lines.append("")
    lines.append("## Algorithm spec vs model adapter")
    lines.append("")
    lines.append(
        "An **algorithm_spec** describes what the research harness does: pack "
        "layout, role (span_narrow, filter, policy), and routing rule.  It is "
        "intentionally independent of the model."
    )
    lines.append("")
    lines.append(
        "A **model_adapter** adds the actual model, output mode, and observed "
        "call health.  An adapter can be `quality_interpretable=true` (clean "
        "fallback profile, usable for quality averaging) or degraded (rate-limit, "
        "bad response) and therefore excluded from the quality aggregate."
    )
    lines.append("")
    lines.append("## Model adapter health")
    lines.append("")
    lines.append("| Adapter | Interpretable | Health | Notes |")
    lines.append("| --- | --- | --- | --- |")
    for aid, adata in sorted(report["model_adapters"].items()):
        interp = "yes" if adata["quality_interpretable"] else "no"
        notes = adata["notes"]
        lines.append(
            f"| `{aid}` | {interp} | `{adata['health']}` | {notes} |"
        )
    lines.append("")
    lines.append("## Aggregate live quality cells")
    lines.append("")
    lines.append(
        "| Algorithm spec | Adapter | Role | Tasks | Gold | False | SpanF0.5 | PFP | Source |"
    )
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for cell in report["aggregate_cells"]:
        lines.append(
            f"| `{cell['algorithm_spec_id'][:42]}` | `{cell['model_adapter_id']}` "
            f"| {cell['role']} | {cell['task_count']} | {cell['added_gold_span']} "
            f"| {cell['added_false_span']} | {_fmt(cell.get('mean_span_f05'))} "
            f"| {_fmt(cell.get('mean_pfp'))} | {cell['source_report']} |"
        )
    lines.append("")
    lines.append("## Model-averaged treatment effects")
    lines.append("")
    lines.append(
        "Effects are computed only over adapters marked `quality_interpretable`. "
        "The delta is mean SpanF0.5 of the algorithm spec minus the matching "
        "baseline for the same adapter."
    )
    lines.append("")
    lines.append(
        "| Algorithm spec | Adapters | Avg Δ SpanF0.5 | Effect | Leave-one-model | Variance |"
    )
    lines.append("| --- | ---: | ---: | --- | --- | --- |")
    claim_levels = report["robustness_summary"]["algorithm_claim_levels"]
    variance_status = report["robustness_summary"]["model_effect_variance_status"]
    loo_status = report["robustness_summary"]["leave_one_model_status"]
    for eff in report["robustness_summary"]["model_averaged_treatment_effects"]:
        algo_id = eff["algorithm_spec_id"]
        lines.append(
            f"| `{algo_id}` | {eff['model_adapter_count']} "
            f"| {_fmt(eff.get('model_averaged_delta_span_f05'))} "
            f"| `{eff['effect_status']}` / `{claim_levels.get(algo_id, 'n/a')}` "
            f"| `{loo_status.get(algo_id, 'n/a')}` "
            f"| `{variance_status.get(algo_id, 'n/a')}` |"
        )
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.append("| Algorithm / adapter | Claim | Recommendation |")
    lines.append("| --- | --- | --- |")
    for rec in report["recommendations"]:
        target = rec.get("algorithm_spec_id") or rec.get("model_adapter_id")
        target = f"{rec['target_type']}::{target}"
        lines.append(
            f"| `{target}` | `{rec['claim_level']}` | {rec['recommendation']} |"
        )
    lines.append("")
    lines.append("## Safety notes")
    lines.append("")
    lines.append(
        "- Public artifact is aggregate-only; no task IDs, candidate IDs, paths, "
        "line ranges, digests, snippets, prompts, responses, or private labels."
    )
    lines.append(
        "- ``promotion_ready=false``, ``default_should_change=false``, "
        "``evidencecore_semantics_changed=false``, "
        "``llm_direct_evidence_allowed=false``."
    )
    lines.append(
        "- Repo variance is not available at this aggregate level; per-repo "
        "breakdowns remain in the source docs only."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_markdown_zh(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B4/B9 模型稳健证据转换")
    lines.append("")
    lines.append(f"日期：{_now()[:10]}")
    lines.append("")
    lines.append(
        "本报告为仅聚合的研究产物，将 ``algorithm_spec``（模型无关的策略定义）"
        "与 ``model_adapter``（模型 + 输出模式的健康状态）分离，并重编码 B1、"
        "B1C、B2、B3 中已发布的 live quality 聚合结果。"
    )
    lines.append("")
    lines.append(
        "B4/B9 不是门控、不是仅前置条件阶段、不改变 ``EvidenceCore``；LLM "
        "输出仍是候选，不是证据。"
    )
    lines.append("")
    lines.append("## algorithm_spec 与 model_adapter")
    lines.append("")
    lines.append(
        "**algorithm_spec** 描述研究 harness 做了什么：pack layout、role "
        "（span_narrow、filter、policy）与路由规则，故意与模型无关。"
    )
    lines.append("")
    lines.append(
        "**model_adapter** 补充实际模型、输出模式与调用健康状态。adapter 可"
        "以是 `quality_interpretable=true`（干净、可用于质量平均）或已降级"
        "（rate-limit、bad response），后者应排除在质量聚合之外。"
    )
    lines.append("")
    lines.append("## 模型 adapter 健康状态")
    lines.append("")
    lines.append("| Adapter | 可解释 | 健康 | 备注 |")
    lines.append("| --- | --- | --- | --- |")
    for aid, adata in sorted(report["model_adapters"].items()):
        interp = "是" if adata["quality_interpretable"] else "否"
        lines.append(
            f"| `{aid}` | {interp} | `{adata['health']}` | {adata['notes']} |"
        )
    lines.append("")
    lines.append("## 聚合 live quality cells")
    lines.append("")
    lines.append(
        "| Algorithm spec | Adapter | Role | Tasks | Gold | False | SpanF0.5 | PFP | Source |"
    )
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for cell in report["aggregate_cells"]:
        lines.append(
            f"| `{cell['algorithm_spec_id'][:42]}` | `{cell['model_adapter_id']}` "
            f"| {cell['role']} | {cell['task_count']} | {cell['added_gold_span']} "
            f"| {cell['added_false_span']} | {_fmt(cell.get('mean_span_f05'))} "
            f"| {_fmt(cell.get('mean_pfp'))} | {cell['source_report']} |"
        )
    lines.append("")
    lines.append("## 模型平均处理效应")
    lines.append("")
    lines.append(
        "仅对标记为 `quality_interpretable` 的 adapter 计算效应。delta 等于该 "
        "算法 spec 的 mean SpanF0.5 减去同一 adapter 下对应 baseline 的 mean "
        "SpanF0.5。"
    )
    lines.append("")
    lines.append(
        "| Algorithm spec | Adapters | Avg Δ SpanF0.5 | Effect / Claim | Leave-one-model | Variance |"
    )
    lines.append("| --- | ---: | ---: | --- | --- | --- |")
    claim_levels = report["robustness_summary"]["algorithm_claim_levels"]
    variance_status = report["robustness_summary"]["model_effect_variance_status"]
    loo_status = report["robustness_summary"]["leave_one_model_status"]
    for eff in report["robustness_summary"]["model_averaged_treatment_effects"]:
        algo_id = eff["algorithm_spec_id"]
        lines.append(
            f"| `{algo_id}` | {eff['model_adapter_count']} "
            f"| {_fmt(eff.get('model_averaged_delta_span_f05'))} "
            f"| `{eff['effect_status']}` / `{claim_levels.get(algo_id, 'n/a')}` "
            f"| `{loo_status.get(algo_id, 'n/a')}` "
            f"| `{variance_status.get(algo_id, 'n/a')}` |"
        )
    lines.append("")
    lines.append("## 建议")
    lines.append("")
    lines.append("| Algorithm / adapter | Claim | Recommendation |")
    lines.append("| --- | --- | --- |")
    for rec in report["recommendations"]:
        target = rec.get("algorithm_spec_id") or rec.get("model_adapter_id")
        target = f"{rec['target_type']}::{target}"
        lines.append(
            f"| `{target}` | `{rec['claim_level']}` | {rec['recommendation']} |"
        )
    lines.append("")
    lines.append("## 安全说明")
    lines.append("")
    lines.append(
        "- 公开产物仅限聚合指标；不包含 task ID、candidate ID、path、line range、"
        "digest、snippet、prompt、response 或私有 label。"
    )
    lines.append(
        "- ``promotion_ready=false``、``default_should_change=false``、"
        "``evidencecore_semantics_changed=false``、"
        "``llm_direct_evidence_allowed=false``。"
    )
    lines.append(
        "- 本聚合报告不提供 repo 级方差；per-repo 细节保留在源文档中。"
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / DEFAULT_OUT)
    p.add_argument(
        "--doc-en", type=Path, default=REPO / DEFAULT_DOCS["en"]
    )
    p.add_argument(
        "--doc-zh", type=Path, default=REPO / DEFAULT_DOCS["zh"]
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(self_test=args.self_test)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown_en(report, args.doc_en)
    _write_markdown_zh(report, args.doc_zh)

    print(
        json.dumps(
            {
                "status": report["status"],
                "aggregate_cells": len(report["aggregate_cells"]),
                "algorithm_specs": len(report["algorithm_specs"]),
                "model_adapters": len(report["model_adapters"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
