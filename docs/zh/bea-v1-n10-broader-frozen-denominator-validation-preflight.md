# BEA-v1-N10 Broader Frozen Denominator Validation Preflight

日期：2026-06-29

BEA-v1-N10 是 preflight-only 检查：判断 recovered N6XFR-E/N8 fixed-pool result 是否能用 already-existing N2-equivalent rank-pack rows 在 broader frozen denominator 上验证。它读取 public artifacts，并只读取 known recovered-private outputs 的 bucketed metadata。它不读取 private content，不计算 new arm outcomes，不 rerun N6XFR-E/N8，不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不生成 candidates，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，也不推广 runtime/default behavior。

## 结果

```text
status: no_go_n10_broader_rank_pack_denominator_unavailable
self-test: 14 / 14
forbidden scan: pass
recovered result: 25 / 40 top-10, 34 / 40 top-20, 0 regressions
candidate denominators checked: 4
broader N2-equivalent rank-pack rows available: false
blocker: no_broader_n2_equivalent_rank_pack_rows
N11 authorized: false
```

## Candidate denominators

- `n2_recovered_40_rank_blocked`：exact recovered rank-pack fields 可用，但这是同一个 40-case denominator，并不更广。
- `p4l_locked_272`：broader context 存在，但 public artifacts 或 metadata-only checks 中没有 N2-equivalent rank-pack fields。
- `n1_candidate_gold_trace_272`：broader trace context 存在，但 public artifacts 或 metadata-only checks 中没有 N2-equivalent rank-pack fields。
- `n1_span_rows_213`：span context 存在，但 public artifacts 或 metadata-only checks 中没有 N2-equivalent rank-pack fields。

## 决策

N10 是 No-Go，因为在当前 read-only preflight boundary 下不存在 broader N2-equivalent rank-pack row denominator。Next allowed phase 为 `none_until_broader_n2_equivalent_rank_pack_rows_exist`。

N10 不授权 N11、private content reads、retrieval、reruns、candidate generation/materialization、selector/reranker execution、P5、BEA-v1-A、counterfactuals、runtime/default promotion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n10_broader_frozen_denominator_validation_preflight.py`
- Report: `artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json`
