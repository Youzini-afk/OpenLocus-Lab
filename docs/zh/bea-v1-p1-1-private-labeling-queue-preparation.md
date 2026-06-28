# BEA-v1-P1-1 Private Labeling Queue Preparation

日期：2026-06-28

BEA-v1-P1-1 基于 P0-4 design records 与 P1-0 已验证的 harness path，准备真实 private support-labeling queue。该 queue 生成在 `.openlocus/research-private/` 下，不提交。

## 结果

```text
status: private_labeling_queue_preparation_pass
self-test: 7 / 7
forbidden scan: pass
queue records: 18
```

Public artifact 只暴露 sanitized queue buckets 与 manifests。不公开 queue item ids、design ids、paths、spans、snippets、provider payloads 或真实 labels。

## 决策

P1-1 授权基于生成 queue 进行真实 private support labeling。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p1_1_private_labeling_queue_preparation.py`
- Report：`artifacts/bea_v1_p1_1_private_labeling_queue_preparation/bea_v1_p1_1_private_labeling_queue_preparation_report.json`

