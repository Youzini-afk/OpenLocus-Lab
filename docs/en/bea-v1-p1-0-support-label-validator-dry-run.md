# BEA-v1-P1-0 Support-Label Validator Dry Run

Date: 2026-06-27

BEA-v1-P1-0 validates the P0-5 private support-label harness end to end with a synthetic private fixture. The fixture is emitted under `.openlocus/research-private/` and is explicitly not real label data.

## Result

```text
status: support_label_validator_dry_run_pass
self-test: 6 / 6
forbidden scan: pass
synthetic labels validated: 18
```

The dry run proves that the private label schema, conjunction derivation, duplicate/id validation, sanitizer, and public summary path work end to end. It does not populate real labels and does not execute a support counterfactual.

## Decision

P1-0 authorizes real private support labeling using the validated schema and harness. Support counterfactual execution remains blocked until real private labels are complete and scanner-validated.

P1-0 does not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, downstream-value claims, support counterfactual execution, or support marginal-utility claims.

## Artifact

- Script: `eval/bea_v1_p1_0_support_label_validator_dry_run.py`
- Report: `artifacts/bea_v1_p1_0_support_label_validator_dry_run/bea_v1_p1_0_support_label_validator_dry_run_report.json`

