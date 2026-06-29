# BEA-v1-N10CB Same-File Span Cluster Bridge Audit Package

Date: 2026-06-29

BEA-v1-N10CB is a public-only audit/package for the N10CA same-file span cluster bridge smoke. It reads public artifacts only. It performs no private reads, no recompute, no new variants, no adaptive tuning, no retrieval/rerun/OpenLocus execution, no candidate generation/add/remove/reorder, and no runtime/default promotion.

## Result

```text
status: cluster_bridge_audit_package_complete_n10cc_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CB: 0
recomputes in N10CB: 0
N10CC authorized: true
```

## Packaged N10CA facts

- N10CA completed with 9 predeclared variants.
- Top10-bridge variants all produced top10/top20 `15 / 16` and lost 5 cost80 anchor top10 hits.
- Top20-bridge variants all produced top10/top20 `15 / 19` and lost 5 cost80 anchor top10 hits.
- `top10_no_bridge_pad20` produced top10/top20 `15 / 16` and lost 5 cost80 anchor top10 hits.
- Best observed result was `15 / 19`, below the cost80 anchor `20 / 24` and pm200 anchor `25 / 30`.
- `cluster_bridge_improves_anchor_count=0` and `cluster_bridge_cost_efficient_count=0`.
- Candidate pool/order remained unchanged; no candidate add/remove/reorder occurred; gold was not used for cluster formation.

Mechanism conclusion: under the predeclared variants, same-file cluster/bridge underperforms the local-window anchor. The positive signal in the current same-source N1 surface still appears to be local single-candidate boundary expansion, not multi-candidate bridging.

## Handoff

N10CB authorizes only `BEA-v1-N10CC Next Mechanism Search Outside Fixed-Window and Cluster-Bridge Families`. It does not authorize runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cb_cluster_bridge_audit_package.py`
- Report: `artifacts/bea_v1_n10cb_cluster_bridge_audit_package/bea_v1_n10cb_cluster_bridge_audit_package_report.json`
