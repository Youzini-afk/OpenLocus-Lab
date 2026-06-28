# BEA-v1-P1-4 Automated-Label Reliability Audit

日期：2026-06-28

BEA-v1-P1-4 通过 P1-2 intake 路径验证 P1-3 agent-generated private support labels，并审计这些自动标签是否足够 informative，能否授权 P1-5 support-link denominator audit。它不运行 support counterfactual。

## 结果

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

P1-4 确认自动标签可通过 intake，且具备必需的 origin metadata；但这些标签有意保持保守：所有 rows 的 target/support hit buckets 都是 `unknown_not_labeled`，conjunction 都是 `ambiguous_unlabeled`。

## 决策

P1-5 denominator audit 未获授权，因为自动标签未通过 informativeness thresholds：informative label rate 低于 0.50，known conjunction rate 低于 0.25，unknown-both-hit rate 高于 0.50。

P1-4 只授权 automated-label reliability auditing。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p1_4_automated_label_reliability_audit.py`
- Report：`artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json`
