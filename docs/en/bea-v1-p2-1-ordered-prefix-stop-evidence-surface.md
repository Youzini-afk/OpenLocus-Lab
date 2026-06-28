# BEA-v1-P2-1 Ordered-Prefix Stop Evidence Surface

Date: 2026-06-28

BEA-v1-P2-1 consolidates committed ordered-prefix / early-stop evidence into scanner-safe public rows. It distinguishes aggregate-only evidence from private-trace readiness and does not run policy changes, policy tuning, selector/reranker changes, implementation, runtime promotion, or counterfactuals.

## Result

```text
status: no_go_p2_1_ordered_prefix_only_aggregate
self-test: 8 / 8
forbidden scan: pass
sanitized stop evidence rows: populated
source artifact coverage: >= 2
early-stop failure-category rows: > 0
private trace rows: unavailable locally
private-trace readiness: false
```

The surface extracts aggregate rows from P0-8, FD1, BEA-3/4/5, and v0.4 P1/P2/P3 artifacts. These rows are useful as committed evidence that early-stop / ordered-prefix behavior exists, but most fields remain aggregate proxies. The optional project-private ordered-prefix trace JSONL is not present locally, so row-level prefix position, cost, budget, marginal gain, and continue-counterfactual readiness does not pass.

All public per-row identifiers are regenerated as anonymous local ids after row merging, so ids are unique within the artifact and do not expose source ids.

## Decision

P2-1 is data-surface extraction only. It does not authorize ordered-prefix stop-policy changes, trace counterfactual execution, support counterfactual execution, policy tuning, implementation, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p2_1_ordered_prefix_stop_evidence_surface.py`
- Report: `artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json`
