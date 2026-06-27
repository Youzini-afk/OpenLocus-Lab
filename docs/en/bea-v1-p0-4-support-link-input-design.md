# BEA-v1-P0-4 Support-Link Input Design

Date: 2026-06-27

BEA-v1-P0-4 converts the P0-1/P0-2 support-link gap into a scanner-validated labeling input contract. It does not label private rows, does not execute a counterfactual, does not call providers, does not run retrieval, and does not implement a policy.

## Result

```text
status: support_link_input_design_pass
self-test: 8 / 8
forbidden scan: pass
support-link design records: 18
label contract fields: 6
```

The artifact joins P0-1 `support_link_trace` gaps with the 18 P0-2 `blocked_missing_label` matrix cells. It publishes only sanitized design rows and a labeling contract. All target/support hit states remain `unknown_not_labeled`; the phase is input design only.

## Contract

The public contract defines these label fields:

- `support_relation_bucket`
- `target_hit_bucket`
- `support_hit_bucket`
- `conjunction_bucket`
- `support_evidence_role_bucket`
- `leakage_risk_bucket`

These fields are intended to support a later counterfactual phase without exposing raw paths, snippets, candidates, ranks, scores, task IDs, private record IDs, provider payloads, or source-linkable private data.

## Decision

P0-4 authorizes only support-link labeling input work. A later phase may use the contract to label private rows and then decide whether support counterfactual execution is justified. This phase does not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p0_4_support_link_input_design.py`
- Report: `artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json`

