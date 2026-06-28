# BEA-v1-P1-4 Automated-Label Reliability Audit

Date: 2026-06-28

BEA-v1-P1-4 validates the P1-3 agent-generated private support labels through the P1-2 intake path and audits whether those automated labels are informative enough to authorize a P1-5 support-link denominator audit. It does not run a support counterfactual.

## Result

```text
status: no_go_p1_4_low_evidence_labels
self-test: 10 / 10
forbidden scan: pass
private label rows: 18
P1-2 intake-valid rows: 18
label errors: 0
agent-generated origin rows: 18 / 18
deterministic method rows: 18 / 18
human_calibrated=false rows: 18 / 18
informative labels: 0 / 18
known conjunction labels: 0 / 18
unknown-both-hit labels: 18 / 18
```

P1-4 confirms that the automated labels are intake-compatible and have the required origin metadata, but they are intentionally conservative: target/support hit buckets remain `unknown_not_labeled` and conjunction remains `ambiguous_unlabeled` for every row.

## Decision

The P1-5 denominator audit is not authorized because the automated labels fail the informativeness thresholds: informative label rate is below 0.50, known conjunction rate is below 0.25, and unknown-both-hit rate is above 0.50.

P1-4 authorizes only automated-label reliability auditing. It does not authorize support counterfactual execution, support marginal-utility claims, P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p1_4_automated_label_reliability_audit.py`
- Report: `artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json`
