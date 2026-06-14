# R44 Failure Clusters

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R44 Failure Clusters

| Cluster | Count | Recommended next fix |
|---|---:|---|
| BENCHMARK_ORACLE_SUSPECT | 0 | covered by R30 baseline; re-evaluate in R43 full matrix |
| DENSE_MOCK_NOISE | 577 | covered by R30 baseline; re-evaluate in R43 full matrix |
| DENSE_SEMANTIC_TRAP_FALSE_POSITIVE | 219 | covered by R30 baseline; re-evaluate in R43 full matrix |
| FRONTEND_BACKEND_CONFUSION | 57 | covered by R30 baseline; re-evaluate in R43 full matrix |
| GRAPH_ADDS_NO_GOLD | 90 | covered by R30 baseline; re-evaluate in R43 full matrix |
| GRAPH_NEIGHBOR_FALSE_POSITIVE | 26 | covered by R30 baseline; re-evaluate in R43 full matrix |
| GUARD_RECALL_KILL | 62 | covered by R30 baseline; re-evaluate in R43 full matrix |
| HARD_DISTRACTOR_CONFUSION | 43 | covered by R30 baseline; re-evaluate in R43 full matrix |
| NEGATIVE_NONEXISTENT_FALSE_PRIMARY | 41 | covered by R30 baseline; re-evaluate in R43 full matrix |
| REGEX_NORMALIZATION_BUG | 36 | covered by R30 baseline; re-evaluate in R43 full matrix |
| RRF_INHERITED_BM25_FALSE_POSITIVE | 299 | covered by R30 baseline; re-evaluate in R43 full matrix |
| STALE_INDEX_LIKE_FALSE_PRIMARY | 0 | covered by R30 baseline; re-evaluate in R43 full matrix |
| SYMBOL_EXTRACTION_MISS | 63 | covered by R30 baseline; re-evaluate in R43 full matrix |
| TEST_SOURCE_CONFUSION | 41 | covered by R30 baseline; re-evaluate in R43 full matrix |
| QUIVER_BQ_DISTRIBUTION_MISMATCH | 1 | test sharded/proto only; no default expansion |
| QUIVER_GLOBAL_INDEX_MIXING_FAILURE | 1 | continue per-view/language/source-test sharding bakeoff |
| LLM_DERIVED_VIEW_HALLUCINATION | 0 | when real LLM is used, require schema and source span validation |
| GRAPH_ADDS_NO_GOLD | 1 | keep graph out of primary expansion; use as explanation/rerank feature only |
| REGEX_NORMALIZATION_BUG | None | do_not_use_raw_regex_for_user_query_by_default |
| SYMBOL_EXTRACTION_MISS | None | validate R39 repair on R26/R38 before integration |
| DENSE_REAL_SEMANTIC_TRAP | 4 | run real embeddings supporting-only on R38 traps |

