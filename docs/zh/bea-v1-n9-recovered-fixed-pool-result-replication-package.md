# BEA-v1-N9 Recovered Fixed-Pool Result Replication Package

日期：2026-06-29

BEA-v1-N9 是 recovered fixed-pool rank-order result 的 public replication 与 claim-boundary package。它只读取 public N6XFR-E、N7、N8、N5 与 N6F artifacts。它不读取或扫描 private storage，不 recompute outcomes，不 rerun retrieval，不生成 candidates，不增加 arms，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，也不推广 runtime/default behavior。

## 结果

```text
status: recovered_fixed_pool_result_replication_package_complete
self-test: 15 / 15
forbidden scan: pass
case count: 40
arm count: 4
public rows: 160
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best top20 recovery: 34 / 40
regressions: 0
threshold passed: true
```

## Replication chain

- N6XFR-E 在 recovered 40-case denominator 上产出 recovered fixed-pool result。
- N7 审计 public N6XFR-E result，并授权 independent recompute。
- N8 使用 same private rows 与 same four arms 独立 recompute，且 per-arm top-10、top-20 与 regression counts 均匹配 N6XFR-E。
- N9 在不进行新 empirical execution 的情况下打包 public replication chain 与 claim boundary。

## Recompute 所需 private input

复现计算仍需要 ignored project-private storage 中的 same recovered N2 rank-pack rows。这些 rows 不被提交，其 path/name/content 不公开，N9 也不读取它们。

## Limitations

- Single recovered 40-case denominator。
- Recompute 需要 private local rows。
- 尚未在 broader denominator 上验证。
- 不是 runtime/default policy。
- 不是 selector/reranker result。
- 不是 downstream-value evidence。
- Arm semantics 依赖 rank<=20 primary / rank>20 extra-depth decomposition。

## 决策

N9 只授权 `BEA-v1-N10 Broader Frozen Denominator Validation Preflight`。它不授权 capture、private reads、recompute、retrieval、reruns、new-arm search、selector/reranker execution、P5、BEA-v1-A、runtime/default promotion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n9_recovered_fixed_pool_result_replication_package.py`
- Report: `artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json`
