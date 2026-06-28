# BEA-v1-P1-2 Private Label Intake Validator

Date: 2026-06-28

BEA-v1-P1-2 validates the project-private support-label intake path over the P1-1 queue. It checks that the private queue rows are readable from `.openlocus/research-private/`, match the required queue and private-label schemas, join the public sanitized queue shape, and can accept real private labels without publishing private ids or source-linkable data.

## Result

```text
status: private_label_intake_validator_contract_pass
self-test: 8 / 8
forbidden scan: pass
valid private queue records: 18
valid real labels: 0
```

No real private labels were supplied in this run. The public artifact therefore reports only the validator contract, private queue intake manifest, private label intake manifest, gates, and empty sanitized real-label summaries.

## Decision

P1-2 authorizes private support-label intake validation only. It does not authorize support counterfactual execution, support marginal-utility claims, P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p1_2_private_label_intake_validator.py`
- Report: `artifacts/bea_v1_p1_2_private_label_intake_validator/bea_v1_p1_2_private_label_intake_validator_report.json`
