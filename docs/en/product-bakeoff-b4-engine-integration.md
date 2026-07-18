# Product Bakeoff B4 Analysis and Publication Engine Integration

Date: 2026-07-18

Status: `product_bakeoff_b4_analysis_publication_engine_complete_no_runtime_no_holdout_no_execution`

This checkpoint implements and fault-tests the B4 comparative-analysis surface before any repository is selected or any treatment output exists. The machine-readable aggregate is [`product_bakeoff_b4_engine_integration.json`](../../artifacts/product_bakeoff_b4_engine_integration/product_bakeoff_b4_engine_integration.json).

## Closed matrix contract

The runner contract accepts exactly 1,728 identity-free task outcomes: 576 paired tasks times three arms. It binds every outcome to the public panel/task schedule, requires the exact role and cold/warm assignment, rejects duplicate or missing cells, requires all 2,160 raw operation groups and 432 index builds, and requires the exact closed pre-score gate set with zero provider/network calls. Repository slugs, task slugs, queries, oracle rows, source locations, excerpts, and raw output are not part of this surface.

This is deliberately not yet the raw repository execution adapter. Phase 3 must still translate validated private execution receipts into this closed matrix and prove that translation against synthetic and Linux qualification fixtures.

## Cluster analysis and decision behavior

The scorer treats the 144 repositories as paired clusters. It computes task-success, task-utility, status/target, context-F0.5, and harmful-evidence effects; ordinary 95% and simultaneous 97.5% intervals; twelve-panel direction counts; paired warm-query and peak-RSS ratio intervals; quality/resource competition ranks; and the Pareto frontier.

The harmful-evidence gate does not treat zero observed events as zero uncertainty. In addition to the paired risk-difference estimate, it uses a conservative simultaneous Wilson upper bound for candidate-only harm. Ranking is completed before deployment gates. Exact ties share rank, and a safety or resource failure cannot remove effects, ranks, or the Pareto result.

## Aggregate publication

The success schema always contains all three arm aggregates, both planned comparisons, both interval levels, panel directions, quality/resource ranks, Pareto membership, gate outcomes, and any Phase C shortlist. The failed-closeout schema contains only safe aggregate progress and failure class; a pre-boundary failure cannot publish treatment counts, while a post-boundary failure cannot authorize restart, resume, retry, or recomputation.

Synthetic tests cover a qualifying comparative result, an exact three-way tie, resource-gate failure, harmful-evidence failure, incomplete/duplicate matrices, schedule drift, bool-as-int contamination, publication tampering, and private-key injection. In the exact-tie case all arms share rank 1, the Pareto frontier remains populated, and the shortlist is empty rather than the comparative result disappearing.

## Current boundary

No runtime is qualified, no private repository/task/oracle holdout exists, and formal execution is not authorized. The next local phase is the raw repository execution adapter plus offline source, runtime, corpus, readiness, attempt-boundary, and disconnect-safe control plane. The compute server remains unnecessary until that phase is CI-green.
