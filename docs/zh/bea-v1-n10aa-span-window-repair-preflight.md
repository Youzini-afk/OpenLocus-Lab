# BEA-v1-N10AA Span-Window Repair Preflight

日期：2026-06-29

BEA-v1-N10AA 是 fixed span-window repair smoke 的 design/preflight 阶段。它只读取 public N10Z/N10X/N10Y artifacts。不读取 private data，不进行 span expansion evaluation，也不执行 repair。

## 结果

```text
status: span_window_repair_preflight_pass_n10ab_authorized
self-test: 14 / 14
forbidden scan: pass
file-hit/no-top10-span gap: 25
same-file before-gold bucket: 17
same-file after-gold bucket: 8
same-file/no-overlap dominates: true
variants: 3
primary variant: fixed_symmetric_span_expansion_pm50_lines
baseline N10X best-arm span top10: 9
N10AB threshold: pm50 top10 expanded span overlap >= 11
```

## N10AB repair design

- Primary variant：`fixed_symmetric_span_expansion_pm50_lines`。
- Optional sensitivity variants：`fixed_symmetric_span_expansion_pm20_lines` 与 `fixed_symmetric_span_expansion_pm100_lines`。
- 规则：对 N10T best arm 后 top 10 内的每个 evidence span，按固定窗口对称扩展，并将 lower bound clamp 到 1。
- 不允许使用 gold signal 选择扩展量、向 gold 偏移或调整窗口。
- 不允许 content-aware adjustment、path changes、candidate addition/removal、candidate generation、retrieval、rerun、selector/reranker 或 new-arm search。

## N10AB metric contract

Primary metric 为 `top10_expanded_span_overlap_count_pm50`。Baseline 是 N10X best-arm top-10 span overlap count `9`。只有 pm50 top-10 expanded span overlap count 至少为 `11` 时，N10AB 才通过。Secondary metrics 包括 top-20 expanded overlap、相对于 N10X 的 delta，以及 expansion-overreach buckets。Public output 不得包含 line numbers。

## 决策

N10AA 只授权 `BEA-v1-N10AB Fixed Span-Window Repair Smoke` 使用 same private span rows。N10AA 本身不授权 private read，也不授权 repair execution。Retrieval/reruns、OpenLocus execution、candidate generation/materialization、new-arm search、selector/reranker execution、P5、BEA-v1-A、counterfactuals、runtime/default promotion、method-winner claims 与 downstream-value claims 均仍未授权。

## Artifact

- Script: `eval/bea_v1_n10aa_span_window_repair_preflight.py`
- Report: `artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json`
