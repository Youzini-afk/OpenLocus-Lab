# BEA-v1-N10R Targeted N2 Rank-Pack Row Generation Preflight

日期：2026-06-29

BEA-v1-N10R 是一个 actionable preflight，用来判断是否能在不执行 full P4L rerun 的情况下生成 additional N2-equivalent rank-pack rows。它可以读取 scoped private N1/N2/P4L row schemas 与 counts，并检查 N2 builder code；但不执行 OpenLocus、N2、P4L、retrieval、candidate generation、selector/reranker logic、P5、BEA-v1-A，也不写入 generated private rows。

## 结果

```text
status: no_go_n10r_target_denominator_insufficient
self-test: 15 / 15
forbidden scan: pass
known-good N2 rows: 40
N1 span rows: 213
N1 candidate/gold trace rows: 272
P4L private arm outcome rows: 1088
targeted N2 builder entrypoint identified: true
targeted denominator filter supported: false
can run without full P4L rerun: false
N10S authorized: false
```

## Findings

- Recovered N2 rank-pack rows schema-valid，并提供 40 known-good rows。
- N1/P4L private inputs 提供 broader row counts，但它们还不是 N2-equivalent rank-pack rows。
- Static inspection 找到了 N2 row builder helper 与 candidate-order semantics，但可用 N2 CLI 是 monolithic full locked-denominator reconstruction runner。
- Existing builder 中没有 targeted denominator filter 或 targeted canary entrypoint。
- 因此 N10R 不能授权 N10S canary generation：blocker 不是 builder 不可用，而是 exact N2/D2 denominator 已在 full locked 272 run 中耗尽为 40 条；继续扩大需要新的 denominator definition。

## 决策

N10R 以 No-Go 关闭，blocker 为 `n2_d2_filter_exhausted_full_denominator`。Next allowed phase 为 `none_for_n2_equivalent_broader_validation_without_new_denominator_definition`。

N10R 不从 N1 span evidence materialize broader rows，不写 generated private rows，不运行 OpenLocus/N2/P4L/retrieval，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，不推广 runtime/default policy，也不提出 method-winner/downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight.py`
- Report: `artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json`
