# R25 Graph+Dense Ablation

**Date**: 2026-06-12
**Status**: Completed (eval-layer only; no Rust core or EvidenceCore changes)
**promotion_ready**: false
**not_promotion_evidence**: true
**remote_calls**: 0

## Overview

R25 is an eval-layer ablation study measuring the contribution of graph_basic and dense_mock strategies — individually and in combination with R21 RRF — on the R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories).

**Key honesty constraints**:
- dense_mock is non-semantic (deterministic blake3 vectors do NOT capture semantic similarity)
- QuIVer is not implemented (unavailable/not_measured; no numeric zero as quality result)
- TDB is a feature-gated placeholder (not applicable for this ablation)
- R20 labels are weak/mined (258 weak, 315 mined_high_confidence, 168 mined; no human_reviewed)

## Strategies

| Strategy | Description | Source |
|----------|-------------|--------|
| no_graph | R21 RRF baseline (loaded from artifacts) | R21 predictions |
| graph_basic | Derive top path via symbol→regex fallback, then `openlocus impact <path> --depth 1 --json` | Live CLI in isolated root |
| rrf_plus_graph | RRF fuse graph_basic + R21 rrf | Composite from base predictions |
| dense_mock | `openlocus dense build --provider mock` + `openlocus dense search` | Live CLI in isolated root |
| rrf_plus_dense_mock | RRF fuse dense_mock + R21 rrf | Composite from base predictions |
| rrf_plus_dense_mock_plus_graph | RRF fuse dense_mock + graph_basic + R21 rrf | Composite from base predictions |

**Unavailable strategies** (explicit unavailable/not_measured):
- quiver_recall, quiver_precision, quiver_mrr: quiver_not_implemented
- tdb_quiver_recall, tdb_quiver_precision: tdb feature-gated placeholder not applicable

## New Metrics

| Metric | Description |
|--------|-------------|
| added_gold_span | Lines added by expansion strategy that are in gold_spans (vs no_graph baseline) |
| added_false_span | Lines added by expansion strategy that are NOT in gold_spans (vs no_graph baseline) |
| graph_pollution_ratio | Ratio of graph evidence on forbidden paths vs total graph evidence |
| graph_token_waste_delta | Token waste change vs baseline (expansion - baseline) |
| dense_added_gold_span | Dense-specific added gold lines |
| dense_added_false_span | Dense-specific added false lines |
| combined_added_gold_span | Combined-strategy added gold lines |
| combined_added_false_span | Combined-strategy added false lines |

**Rule**: If added_false_span > added_gold_span, default expansion is blocked.

## Results

### Retrieval quality

| Metric | no_graph | graph_basic | rrf_plus_graph | dense_mock | rrf_plus_dense_mock | rrf_plus_dense_mock_plus_graph |
|--------|---------:|------------:|---------------:|-----------:|--------------------:|-------------------------------:|
| FileRecall@1 | 0.693 | 0.003 | 0.497 | 0.024 | 0.134 | 0.112 |
| FileRecall@3 | 0.791 | 0.013 | 0.762 | 0.110 | 0.719 | 0.698 |
| FileRecall@5 | 0.829 | 0.013 | 0.791 | 0.152 | 0.781 | 0.767 |
| MRR | 0.753 | 0.008 | 0.641 | 0.073 | 0.451 | 0.405 |
| SpanF0.5 | 0.185 | 0.000 | 0.172 | 0.000 | 0.077 | 0.068 |
| token_waste | 0.779 | 0.310 | 0.800 | 0.850 | 0.928 | 0.938 |
| no_gold_nonempty | 0.495 | 0.072 | 0.495 | 0.878 | 0.923 | 0.923 |
| abstain_rate | 0.182 | 0.785 | 0.182 | 0.134 | 0.034 | 0.034 |
| citation_validity | 1.0 inherited | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

### Ablation metrics

| Metric | graph | dense | rrf_plus_graph | rrf_plus_dense | combined |
|--------|------:|------:|---------------:|---------------:|---------:|
| added_gold_span | 0 | 2 | 0 | 2 | 2 |
| added_false_span | 435 | 20,273 | 435 | 20,273 | 20,695 |
| default_expansion_blocked | true | true | true | true | true |

### Graph-specific metrics

| Metric | Value |
|--------|-------|
| Path derivation: symbol | 358/741 (48.3%) |
| Path derivation: regex | 156/741 (21.1%) |
| Path derivation: none | 227/741 (30.6%) |
| Impact failures (no top path) | 227 |
| Impact no evidence (top path found but impact empty) | 355 |
| graph_pollution_ratio | 0.000 |
| graph_token_waste_delta | -0.469 |

## Key findings

1. **graph_basic produces net-negative contribution**: Added 0 gold spans and 435 false spans. The graph expansion (depth=1 impact from top path) introduces evidence from related files that are not in gold, without recovering any gold spans that RRF missed. Default expansion blocked.

2. **dense_mock is net-negative as expected**: Added 2 gold spans and 20,273 false spans. Non-semantic mock vectors produce massive noise. The 2 gold span hits are likely coincidental proximity. Default expansion blocked.

3. **rrf_plus_graph dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.497 because graph evidence competes with RRF evidence in the RRF score calculation. The graph evidence, while citation-valid, is mostly unrelated to the query intent.

4. **rrf_plus_dense_mock also dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.134. Dense mock evidence floods the RRF pool with irrelevant candidates that push RRF hits down.

5. **Graph pollution is zero**: No graph evidence was returned on forbidden paths. graph_pollution_ratio=0.000.

6. **Graph has low token waste when it fires**: graph_basic token_waste=0.310 vs no_graph=0.779, but this is because graph_basic mostly abstains (0.785 abstain rate) and when it does return evidence, it's from impact which tends to be narrow.

7. **Citation validity remains 1.0**: graph_basic, dense_mock, and composite strategies are revalidated in R25 with Rust hash/range/path citation validation. no_graph inherits R21 validation after R25 verifies the R21 artifact manifest path/sha/bytes/jsonl line counts before baseline use.

8. **QuIVer/TDB are honestly reported as unavailable/not_measured**: No numeric zero quality results for QuIVer. TDB is not applicable for this ablation.

## Safety

- All safety checks passed
- Labels not loaded until after run complete (strict RUN/SCORE phase separation)
- R21 artifact manifest path/sha/bytes/jsonl line count verified before using RRF baseline
- Citation validator hash/range/path for graph/dense/composite strategies with evidence; no_graph inherits R21 validation after manifest verification
- Artifact manifest path/sha/bytes/line count verified
- Artifact scans for private fields: 0 issues
- Artifact scans for canary tokens: 0 issues
- Source-leak canary (regex over isolated source before dense build): 1 seeded self-test hit proves the scanner can detect regex hits; then 36 leakage checks produce 0 hits and 0 failures. R25 does not claim a dense-path canary; R24 owns dense-path canary hardening.
- promotion_ready=false, not_promotion_evidence=true, remote_calls=0
- R20 labels weak/mined caveat recorded

## Caveats

- R20 labels are weak/mined (no human_reviewed); not promotion evidence
- dense_mock is non-semantic; no real embedding quality claim
- Graph impact is depth=1 only; deeper impact not tested
- Graph path derivation uses symbol→regex fallback; not LSP/SCIP
- Impact returns empty evidence for 355/514 tasks with top path (no graph edges found)
- graph_basic abstains on 78.5% of tasks (no path or no impact)
- Combined strategies show additive noise: graph + dense false spans accumulate
- Runs artifacts are gitignored; report not committed

## Commands

```bash
python3 eval/r25_graph_dense_ablation.py \
    --workspace . \
    --fixtures fixtures/r20_auto_wide \
    --openlocus target/debug/openlocus \
    --r21-report runs/r21-auto-wide-report.json \
    --out runs/r25-graph-dense-ablation-report.json
```
