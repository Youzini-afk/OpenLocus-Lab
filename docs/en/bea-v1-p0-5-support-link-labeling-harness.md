# BEA-v1-P0-5 Support-Link Labeling Harness

Date: 2026-06-27

BEA-v1-P0-5 turns the P0-4 support-link input contract into a private labeling harness. It can emit an unlabeled JSONL template under `.openlocus/research-private/` and can validate a completed private label JSONL without exposing raw rows.

This phase does not label records by itself, does not execute a support counterfactual, does not call providers, does not run retrieval, and does not implement a policy.

## Result

```text
status: support_link_labeling_harness_contract_pass
self-test: 9 / 9
forbidden scan: pass
harness records: 18
private template rows: 18
private labels supplied: false
```

The public artifact contains only sanitized harness rows, summary gates, and a private-template manifest. The emitted private template lives in the ignored project-local research-private directory and is not committed.

## Private Schema

The private label rows use schema `bea_v1_p0_5_support_link_private_label.v1` and require the P0-4 label fields plus annotation status. The harness validates allowed enum values, duplicate design IDs, unknown design IDs, and whether `conjunction_bucket` is derived from `target_hit_bucket` and `support_hit_bucket`.

## Decision

P0-5 closes the private labeling harness contract, but not the labels themselves. A later phase may fill the private template and rerun this harness with `--private-labels-jsonl`; support counterfactual execution remains unauthorized until private labels are complete and scanner-validated.

P0-5 does not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, downstream-value claims, support counterfactual execution, or support marginal-utility claims.

## Artifact

- Script: `eval/bea_v1_p0_5_support_link_labeling_harness.py`
- Report: `artifacts/bea_v1_p0_5_support_link_labeling_harness/bea_v1_p0_5_support_link_labeling_harness_report.json`

