# R21 Auto-Wide Strategy Matrix

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R21 Auto-Wide Strategy Matrix

**Eval-layer research only. Does NOT change Rust core.**

Date: 2026-06-12
Schema: r21-v1

## Purpose

R21 is a failure-discovery matrix, not a quality/promotion exercise. It runs 10 retrieval strategies across 741 R20 auto-wide tasks spanning 9 repos and 25 query categories, then scores against weak/mined labels. The goal is to map failure surfaces: where strategies fail, what types of queries cause false positives, and which guard patterns reduce negatives without killing recall.

**promotion_ready=false. not_promotion_evidence=true. Always.**

## Implemented Strategies (10)

| # | Strategy | Type | Description |
|---|----------|------|-------------|
| 1 | regex | base | `openlocus search regex` |
| 2 | bm25 | base | `openlocus search bm25` |
| 3 | symbol | base | `openlocus search symbol` |
| 4 | rrf | base | `openlocus retrieve` (RRF fusion) |
| 5 | bm25_regex | composite | RRF fuse bm25+regex predictions |
| 6 | bm25_symbol | composite | RRF fuse bm25+symbol predictions |
| 7 | rrf_guarded_by_symbol | guard | RRF only if symbol has evidence |
| 8 | rrf_guarded_by_regex | guard | RRF only if regex has evidence |
| 9 | rrf_guarded_by_symbol_regex | guard | RRF only if symbol OR regex has evidence |
| 10 | query_noise_plus_rrf_agree_min | guard+noise | R17 noise guard + RRF agree (threshold=0.0) |

## Unavailable Strategies (10)

| Strategy | Reason |
|----------|--------|
| ast_chunk_bm25 | AST chunking is experimental opt-in; no R21 runner support |
| ast_chunk_rrf | Depends on ast_chunk_bm25 |
| graph_basic | Graph depth=1 only; not evaluated in auto-wide matrix |
| graph_rrf | Depends on graph_basic |
| dense_mock | Mock provider produces deterministic blake3 vectors; no retrieval quality |
| dense_real_if_available | No real embedding provider configured; remote denied by default |
| tdb_quiver_if_available | TDB behind optional feature gate; not in default build |
| tdb_quiver_plus_rrf | Depends on tdb_quiver_if_available |
| tdb_quiver_guarded_by_symbol_regex | Depends on tdb_quiver_if_available |
| fast_context_if_available | Fast-context is 4-turn orchestration scaffold; not a standalone strategy |

## Key Findings (741 tasks, 9 repos, R20 auto-wide)

### Failure Surfaces

1. **All strategies have non-zero no-gold false positives**: Even guards that suppress RRF false positives still return evidence on 16.7-49.5% of no-gold tasks (`expected_behavior in {abstain,no_primary}`). No strategy eliminates false positives entirely.

2. **BM25/RRF are no-gold-heavy**: BM25 `no_gold_nonempty_rate=0.495`, RRF `0.495`. These methods are recall-strong but precision-weak on no-answer/abstain tasks. RRF inherits BM25's no-gold behavior.

3. **Symbol is precision-best but abstains most**: symbol `no_gold_nonempty_rate=0.167` (lowest among base methods) but `abstain_rate=0.517` (highest). When symbol fires, it's precise; when it doesn't, there's no fallback.

4. **rrf_guarded_by_symbol kills recall**: guard_recall_kill_rate=0.228 — the guard eliminates 23% of RRF's recall hits. The symbol-availability gate is too strict for the auto-wide query distribution.

5. **query_noise_plus_rrf_agree_min is the best guard balance in R21**: `no_gold_nonempty_rate=0.221` (vs RRF 0.495) with `FileRecall@1=0.693` preserved (same as raw RRF). This is a failure-surface observation, not a promotion result.

6. **Regex parse failures**: Tasks with regex metacharacters (e.g., `/models/{model_id}`) fail for regex/rrf methods. This is expected CLI behavior, not a safety violation.

7. **R20 label quality limits conclusions**: 258/741 labels are "weak", 315 "mined_high_confidence", 168 "mined". No human_reviewed labels. All metrics are failure-surface probes.

### Strategy Comparison (selected metrics)

| Strategy | FileRecall@1 | MRR | no_gold_nonempty_rate | abstain_rate | primary_false_positive_rate |
|----------|-------------|-----|-------------------|-------------|--------------------------|
| regex | 0.524 | 0.583 | 0.279 | 0.306 | 0.279 |
| bm25 | 0.388 | 0.455 | 0.495 | 0.366 | 0.495 |
| symbol | 0.575 | 0.585 | 0.167 | 0.517 | 0.167 |
| rrf | 0.693 | 0.753 | 0.495 | 0.182 | 0.495 |
| bm25_regex | 0.612 | 0.671 | 0.495 | 0.182 | 0.495 |
| bm25_symbol | 0.551 | 0.643 | 0.495 | 0.224 | 0.495 |
| rrf_guarded_by_symbol | 0.561 | 0.598 | 0.167 | 0.517 | 0.167 |
| rrf_guarded_by_regex | 0.693 | 0.753 | 0.279 | 0.306 | 0.279 |
| rrf_guarded_by_symbol_regex | 0.693 | 0.753 | 0.279 | 0.306 | 0.279 |
| query_noise_plus_rrf_agree_min | 0.693 | 0.753 | 0.221 | 0.350 | 0.221 |

### Citation Validity

All 10 strategies achieve citation_validity=1.0 (Rust `openlocus citations validate` hash+range+path). Composite/guard strategies are built from validated base predictions and are also Rust citation-validated before isolated root cleanup.

### Unavailable Metrics

- verified_current_rate: freshness field unavailable in CLI output
- source_materialization_rejection_rate: raw candidate denominator unavailable
- stale_candidate_rejected: EvidenceCore runtime data not exposed
- policy_denied_rejected: EvidenceCore runtime data not exposed

## Safety Architecture

- **RUN phase**: reads only tasks + repo lock; never reads labels
- **SCORE phase**: reads only predictions/evidence/rejections/trace + labels; never calls CLI
- **Isolated roots**: allowlist-copy per repo_id under temp dir; policy.toml from repo lock
- **Canary tokens**: 4 hardcoded tokens checked via regex in each isolated root
- **Citation validation**: Rust validator runs BEFORE isolated root cleanup
- **Forbidden paths**: predictions/evidence cannot contain fixtures/eval/docs/runs/.openlocus/target/.git/__pycache__
- **Composite strategies**: built from base predictions only; no CLI, no labels

## Caveats

- R21 is a failure-discovery matrix, not a quality/promotion exercise
- R20 labels are weak/mined (no human_reviewed); metrics are probes, not evidence
- 741 tasks across 25 categories and 9 repos — broad but not deep
- Query distribution is synthetic/mined; not representative of real user queries
- Composite/guard strategy effectiveness depends on base method coverage
- No LLM, dense, graph, TDB, or fast-context strategies are included
- Latency for composite strategies is 0ms (built from existing predictions, no CLI)
- One task (r20aw-0625) fails regex parse due to `{model_id}` metacharacters

