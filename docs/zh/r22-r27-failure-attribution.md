# R22/R27 Failure Attribution

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R22/R27 Failure Attribution

**Eval-layer research only. Does NOT change Rust core.**

Date: 2026-06-12
Schema: r22r27-v1

## Purpose

R22/R27 is a failure attribution analysis, not a quality/promotion exercise. It consumes R21 artifacts (predictions + report) and R20 labels to produce automatic failure clusters and expanded metrics. It does NOT re-run retrieval. It does NOT load labels in a run phase; this is analysis-only score phase.

**promotion_ready=false. not_promotion_evidence=true. Always.**

## Architecture

Strictly analysis-only SCORE phase:
- Loads R21 predictions (JSONL) + R21 report (JSON) + R20 labels (private JSONL).
- Never invokes openlocus CLI.
- Never loads labels during a run phase.
- Computes failure clusters based on cross-strategy comparison heuristics.
- Computes expanded per-strategy metrics.
- Detects bucket regressions by query_category/risk_tags/repo/language/expected_behavior.

## Failure Clusters (13 required keys)

| Cluster | Count | Description |
|---------|-------|-------------|
| RRF_INHERITED_BM25_FALSE_POSITIVE | 110 | No-gold tasks where BM25 and RRF both return false primary evidence. RRF inherits BM25's broad lexical matching without a negative gate. |
| GUARD_RECALL_KILL | 67 | Positive tasks where raw RRF hits gold but rrf_guarded_by_symbol misses/abstains. Symbol guard kills 22.8% recall (R21 report). |
| SYMBOL_EXTRACTION_MISS | 91 | Positive tasks where regex/RRF hits gold but symbol search misses. Heuristic symbol extraction fails for non-standard patterns. |
| REGEX_NORMALIZATION_BUG | 1 | R21 regex parse warnings (curly braces in route-style queries like `/models/{model_id}`) or route/config queries where regex fails but other strategies succeed. |
| AST_SPAN_BOUNDARY_BAD | 0 | AST chunking not run in R21. R9 showed FileRecall@5 regression. Recommended: run AST BM25 on R20 auto-wide. |
| DENSE_SEMANTIC_TRAP | 0 | Dense retrieval not evaluated. Mock provider only; no real embedding. Recommended: configure real provider. |
| TDB_QUIVER_SEMANTIC_TRAP | 0 | TDB/QuIVer behind feature gate; not evaluated. Recommended: enable TDB feature and run. |
| TDB_STALE_REJECTED | 0 | TDB not run; stale rejection unmeasured. Recommended: test TDB with file mutations. |
| TDB_STALE_LEAK | 0 | TDB not run; stale leak unmeasured. Recommended: test TDB under concurrent modification. |
| GRAPH_POLLUTION | 0 | Graph not evaluated in R21. R5 config edges are noisy. Recommended: run graph_basic on R20. |
| EVIDENCECORE_REJECTION_EXPECTED | 0 | EvidenceCore rejection data unavailable. R21 shows rate=0.0 for all strategies (clean run). metric_unavailable=true. |
| EVIDENCECORE_REJECTION_UNEXPECTED | 0 | No unexpected rejections observed. metric_unavailable=true. |
| BENCHMARK_ORACLE_SUSPECT | 62 | Weak-quality labels where strategies strongly disagree with oracle (all miss gold on positive, or all return evidence on no-gold). 62/258 weak labels are suspect. |

## Key Findings

1. **RRF inherits BM25 false positives on 110 no-gold tasks**: BM25's broad lexical matching produces false primary hits that RRF propagates without filtering. This is the largest actionable cluster.

2. **Symbol guard kills recall on 67 positive tasks**: rrf_guarded_by_symbol has guard_recall_kill_rate=0.228 (R21 report). The symbol channel returns empty on natural-language, issue-style, and vague queries, causing the guard to reject valid RRF evidence.

3. **Symbol extraction misses 91 positive tasks**: Regex or RRF find gold but symbol search does not. Heuristic regex-based symbol extraction fails for non-standard definitions (Go methods, Python decorators, JS arrow functions, re-exports).

4. **Regex normalization bug on 1 task**: The Rust regex crate treats curly braces (`{model_id}`) as repetition quantifiers, causing parse errors on route-style queries. This is a known limitation.

5. **62 weak labels are suspect**: 258/741 R20 labels are "weak" quality. On 62 of these, strategies strongly disagree with the oracle, suggesting the label (not the strategy) may be incorrect.

6. **Unrun strategy clusters have count=0**: Dense, TDB/QuIVer, graph, and AST strategies were not evaluated in R21. These clusters have count=0 with recommended_next_tests. No data is fabricated.

7. **206 bucket regressions detected**: Multiple strategies have high no_gold_nonempty (>0.3) or recall gaps vs RRF (>0.15) in specific buckets. promotion_blocked_by_bucket_regression=true.

## Expanded Per-Strategy Metrics

| Metric | regex | bm25 | symbol | rrf | bm25_regex | bm25_symbol | rrf_guarded_by_symbol | rrf_guarded_by_regex | rrf_guarded_by_symbol_regex | query_noise_plus_rrf_agree_min |
|--------|-------|------|--------|-----|------------|-------------|----------------------|----------------------|----------------------------|-------------------------------|
| FileRecall@1 | 0.524 | 0.388 | 0.575 | 0.693 | 0.612 | 0.551 | 0.561 | 0.693 | 0.693 | 0.693 |
| FileRecall@3 | 0.604 | 0.489 | 0.578 | 0.791 | 0.711 | 0.711 | 0.620 | 0.791 | 0.791 | 0.791 |
| FileRecall@5 | 0.679 | 0.551 | 0.615 | 0.829 | 0.751 | 0.767 | 0.650 | 0.829 | 0.829 | 0.829 |
| MRR | 0.583 | 0.455 | 0.585 | 0.753 | 0.671 | 0.643 | 0.598 | 0.753 | 0.753 | 0.753 |
| no_gold_nonempty | 0.279 | 0.495 | 0.167 | 0.495 | 0.495 | 0.495 | 0.167 | 0.279 | 0.279 | 0.221 |
| abstain_rate | 0.306 | 0.366 | 0.517 | 0.182 | 0.182 | 0.224 | 0.517 | 0.306 | 0.306 | 0.350 |
| guard_recall_kill | — | — | — | — | — | — | 0.228 | 0.000 | 0.000 | 0.000 |
| citation_validity | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

## Safety

- promotion_ready=false, not_promotion_evidence=true
- source_report_sha, labels_sha, artifact_manifest_sha all verified
- R21 artifacts exist and manifest checks pass
- No labels loaded in a run phase; analysis-only score phase
- No runs artifacts intended for git (gitignored)
- No promotion claims, no dense/LLM/QuIVer quality claims
- Unrun strategy clusters have count=0; no fabricated data

## Caveats

- R20 labels are weak/mined quality (258 weak, 315 mined_high_confidence, 168 mined). Not human-reviewed.
- Gold paths in labels are relative (no repo_id prefix); prediction paths have repo_id prefix. Path matching uses suffix comparison.
- Span-level metrics are computed independently and may differ slightly from R21 report due to path matching differences.
- Unrun cluster counts are 0 by construction; these are not negative results, they are unmeasured.
- Token waste is high (~0.98 for RRF) reflecting that most predicted span lines don't overlap gold spans.
- This is failure attribution, not a quality/promotion exercise.

## Usage

```bash
python3 eval/r22_r27_failure_attribution.py \
    --workspace . \
    --r21-report runs/r21-auto-wide-report.json \
    --fixtures fixtures/r20_auto_wide \
    --out runs/r22-r27-failure-attribution.json
```

