# R29 R26 Auto-Stress Strategy Matrix

## Summary

R29 runs R26's 1100 public stress tasks through a 16-strategy matrix to maximize failure discovery. This is NOT promotion evidence; it is a failure-surface probe.

## Key Properties

- **schema_version**: r29-v1
- **promotion_ready**: false
- **not_promotion_evidence**: true
- **core_changes**: false
- **remote_calls**: 0
- **quiver_implemented**: false
- **dense_mock_is_semantic_quality**: false
- **labels_loaded_after_run**: true
- **run_phase_public_only**: true
- **score_phase_labels_only**: true
- **r26_source_artifacts_validated**: true
- **citation_validity_all_strategies**: 1.0 (or fail closed)
- **artifact_manifest_verified**: true

## Strategy Matrix

### Implemented (16)

**Base R21-style (4):**
1. `regex` — openlocus search regex
2. `bm25` — openlocus search bm25
3. `symbol` — openlocus search symbol
4. `rrf` — openlocus retrieve (RRF fusion)

**Composite R21-style (6):**
5. `bm25_regex` — RRF fuse bm25+regex
6. `bm25_symbol` — RRF fuse bm25+symbol
7. `rrf_guarded_by_symbol` — RRF only if symbol has evidence
8. `rrf_guarded_by_regex` — RRF only if regex has evidence
9. `rrf_guarded_by_symbol_regex` — RRF only if symbol or regex has evidence
10. `query_noise_plus_rrf_agree_min` — noise guard + agreement threshold

**R24/R25-style (6):**
11. `dense_mock` — openlocus dense build/search --provider mock
12. `dense_mock_plus_rrf` — RRF fuse dense_mock + rrf
13. `graph_basic` — derive top path → openlocus impact --depth 1
14. `rrf_plus_graph` — RRF fuse graph_basic + rrf
15. `rrf_plus_dense_mock` — RRF fuse dense_mock + rrf
16. `rrf_plus_dense_mock_plus_graph` — RRF fuse dense_mock + graph_basic + rrf

### Unavailable (5)

| Strategy | Reason |
|---|---|
| `dense_real_if_available` | not_configured_or_policy_disabled |
| `tdb_quiver_if_available` | quiver_not_implemented |
| `tdb_quiver_plus_rrf` | quiver_not_implemented |
| `tdb_quiver_guarded_by_symbol_regex` | quiver_not_implemented |
| `fast_context_if_available` | not wired as standalone matrix strategy |

No fake numeric quality is output for unavailable strategies.

## Run/Score Separation

- **RUN phase**: loads only `fixtures/r26_auto_stress/tasks/auto_stress.jsonl` and `repos.lock.jsonl` + safety checks + dataset manifest. Does NOT load `labels/auto_stress.jsonl` until all run artifacts are written, citations validated, and manifest written.
- **SCORE phase**: loads labels and computes metrics, failure clusters, span contributions, bucket regressions.

## Citation Validation

- Every implemented strategy's emitted evidence is validated via `openlocus citations validate` while isolated roots still exist.
- Composite/fusion strategy evidence is also revalidated.
- No synthetic EvidenceCore channels (e.g., "RRF") are added to evidence.
- If any citation is invalid, the run exits non-zero.

## Isolation

- Allowlisted source files from R26 repos.lock are copied into isolated temp roots.
- No docs/eval/fixtures/runs/.git included. Symlinks disallowed.
- `.openlocus/policy.toml` written in isolated root.
- Runtime traces cleaned between queries (dense embeddings preserved after build).

## R26 Provenance Validation

Before run:
- `safety_checks.passed=true`
- `summary.total_tasks=1100`; declared label count is recorded but label file content is not read until score phase
- `not_promotion_evidence=true`, `core_changes=false`, `remote_calls=0`
- `dense_or_llm_claims=false`
- Tasks SHA matches manifest if present; labels SHA is validated only after run artifacts/citations/manifest are written.

## Metrics

### Overall and by bucket (source_category, expected_behavior, oracle_type, repo_id, risk_tags)

- FileRecall@1/3/5
- MRR
- SpanF0.5 / SpanPrecision / SpanRecall
- token_waste
- abstain_rate
- no_gold_nonempty_rate
- primary_false_positive_rate
- hard_distractor_hit_rate
- must_not_primary_violation_rate
- weak_candidate_rate
- guard_recall_kill_rate (for guard strategies)
- candidate_count_avg
- materialized_span_count_avg
- citation validity counts
- Latency p50/p95 (if available from run traces)

### Added span metrics (graph/dense/composites vs fresh RRF baseline)

- `added_gold_span`
- `added_false_span`
- `tasks_with_additions`
- `default_expansion_blocked = added_false_span > added_gold_span`

## Failure Clusters

All 14 required clusters are computed:
- RRF_INHERITED_BM25_FALSE_POSITIVE
- GUARD_RECALL_KILL
- SYMBOL_EXTRACTION_MISS
- REGEX_NORMALIZATION_BUG
- DENSE_MOCK_NOISE
- DENSE_SEMANTIC_TRAP_FALSE_POSITIVE
- GRAPH_NEIGHBOR_FALSE_POSITIVE
- GRAPH_ADDS_NO_GOLD
- HARD_DISTRACTOR_CONFUSION
- NEGATIVE_NONEXISTENT_FALSE_PRIMARY
- STALE_INDEX_LIKE_FALSE_PRIMARY
- TEST_SOURCE_CONFUSION
- FRONTEND_BACKEND_CONFUSION
- BENCHMARK_ORACLE_SUSPECT

Each cluster: count, affected_strategies, representative_examples, bucket_distribution, suspected_cause, recommended_next_tests.

## Bucket Regressions

- Compare candidate/guard/composite vs RRF baseline per bucket.
- Regression types: recall drop, false-primary increase, no-gold-nonempty increase, must-not-primary increase, abstain spike on primary_evidence.
- Report: total bucket regressions, strategies_with_bucket_regression, worst buckets.

## Private Field Scan

Artifact JSONL must NOT include: source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.


## Full-run results (2026-06-12)

R29 full run completed on all 1100 R26 auto-stress tasks. Safety gates passed. Citation validity is 1.0 for every implemented strategy. This is failure-surface evidence only, not promotion evidence.

### Strategy metrics

| Strategy | FileRecall@1 | FileRecall@5 | MRR | SpanF0.5 | primary_false_positive_rate | no_gold_nonempty_rate | abstain_rate | token_waste | guard_recall_kill_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| regex | 0.615 | 0.820 | 0.692 | 0.229 | 0.135 | 0.135 | 0.563 | 0.695 | — |
| bm25 | 0.514 | 0.762 | 0.615 | 0.164 | 0.444 | 0.444 | 0.405 | 0.695 | — |
| symbol | 0.686 | 0.727 | 0.704 | 0.291 | 0.080 | 0.080 | 0.671 | 0.247 | — |
| rrf | 0.803 | 0.923 | 0.858 | 0.250 | 0.453 | 0.453 | 0.343 | 0.693 | — |
| query_noise_plus_rrf_agree_min | 0.803 | 0.923 | 0.857 | 0.250 | 0.106 | 0.106 | 0.588 | 0.691 | 0.003 |
| dense_mock | 0.016 | 0.123 | 0.055 | 0.000 | 0.874 | 0.874 | 0.139 | 0.844 | — |
| dense_mock_plus_rrf | 0.169 | 0.869 | 0.516 | 0.105 | 0.906 | 0.906 | 0.059 | 0.900 | — |
| graph_basic | 0.011 | 0.019 | 0.015 | 0.000 | 0.039 | 0.039 | 0.883 | 0.273 | — |
| rrf_plus_graph | 0.631 | 0.915 | 0.761 | 0.238 | 0.453 | 0.453 | 0.343 | 0.708 | — |
| rrf_plus_dense_mock | 0.169 | 0.869 | 0.516 | 0.105 | 0.906 | 0.906 | 0.059 | 0.900 | — |
| rrf_plus_dense_mock_plus_graph | 0.164 | 0.858 | 0.482 | 0.104 | 0.906 | 0.906 | 0.059 | 0.900 | — |

### Failure clusters

| Cluster | Count |
|---|---:|
| DENSE_MOCK_NOISE | 577 |
| RRF_INHERITED_BM25_FALSE_POSITIVE | 299 |
| DENSE_SEMANTIC_TRAP_FALSE_POSITIVE | 219 |
| GRAPH_ADDS_NO_GOLD | 90 |
| SYMBOL_EXTRACTION_MISS | 63 |
| GUARD_RECALL_KILL | 62 |
| FRONTEND_BACKEND_CONFUSION | 57 |
| HARD_DISTRACTOR_CONFUSION | 43 |
| NEGATIVE_NONEXISTENT_FALSE_PRIMARY | 41 |
| TEST_SOURCE_CONFUSION | 41 |
| REGEX_NORMALIZATION_BUG | 36 |
| GRAPH_NEIGHBOR_FALSE_POSITIVE | 26 |
| STALE_INDEX_LIKE_FALSE_PRIMARY | 0 |
| BENCHMARK_ORACLE_SUSPECT | 0 |

### Bucket regressions

- total_bucket_regressions: 448
- strategies_with_bucket_regression: bm25, bm25_regex, bm25_symbol, dense_mock, dense_mock_plus_rrf, graph_basic, regex, rrf_guarded_by_symbol, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph, symbol

### Span contribution against fresh RRF baseline

| Strategy | added_gold_span | added_false_span | tasks_with_additions | default_expansion_blocked |
|---|---:|---:|---:|---|
| dense_mock | 2 | 20038 | 309 | true |
| dense_mock_plus_rrf | 2 | 20038 | 309 | true |
| graph_basic | 0 | 437 | 100 | true |
| rrf_plus_graph | 0 | 437 | 100 | true |
| rrf_plus_dense_mock | 2 | 20038 | 309 | true |
| rrf_plus_dense_mock_plus_graph | 2 | 20467 | 311 | true |

### Main conclusions

- RRF remains the strongest recall channel on R26 stress, but it has high false-primary/no-gold risk (primary_false_positive_rate=0.453).
- `query_noise_plus_rrf_agree_min` preserves RRF recall on R26 and reduces primary_false_positive_rate to 0.106 with guard_recall_kill_rate=0.003, but R23 bucket-regression evidence still blocks promotion.
- Symbol remains the best precision anchor in this matrix: highest SpanF0.5 among reported strategies (0.291), low false-primary (0.080), but high abstain (0.671).
- Dense mock is a noise/failure probe, not semantic quality: dense_mock primary_false_positive_rate=0.874 and dense+RRF raises it to 0.906.
- Graph basic remains default-blocked: 0 added gold spans vs 437 added false spans.
- All graph/dense expansion variants are default-blocked by `added_false_span > added_gold_span`.

## Caveats

- No promotion, no default change, failure-surface only.
- R26 labels are weak/mined/deterministic/stress — not human-verified.
- dense_mock is candidate-channel safety smoke, not semantic quality.
- graph_basic is deterministic depth=1, not precise call/type graph.
- QuIVer/TDB unavailable; no fabricated numeric quality.
- Fresh run only; no skip-run support.

## Usage

```bash
python3 eval/r29_r26_stress_matrix.py \
    --workspace . \
    --fixtures fixtures/r26_auto_stress \
    --openlocus target/debug/openlocus \
    --out runs/r29-r26-stress-matrix-report.json

# Smoke test with limited tasks:
python3 eval/r29_r26_stress_matrix.py \
    --workspace . \
    --fixtures fixtures/r26_auto_stress \
    --openlocus target/debug/openlocus \
    --out runs/r29-r26-stress-matrix-report.json \
    --limit 20
```
