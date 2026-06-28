# BEA-v1-P1-1 Private Labeling Queue Preparation

Date: 2026-06-28

BEA-v1-P1-1 prepares a real private support-labeling queue from the P0-4 design records and the P1-0 validated harness path. The queue is emitted under `.openlocus/research-private/` and is not committed.

## Result

```text
status: private_labeling_queue_preparation_pass
self-test: 7 / 7
forbidden scan: pass
queue records: 18
```

The public artifact exposes only sanitized queue buckets and manifests. It does not publish queue item ids, design ids, paths, spans, snippets, provider payloads, or real labels.

## Decision

P1-1 authorizes real private support labeling against the generated queue. It does not authorize support counterfactual execution, support marginal-utility claims, P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p1_1_private_labeling_queue_preparation.py`
- Report: `artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json`

