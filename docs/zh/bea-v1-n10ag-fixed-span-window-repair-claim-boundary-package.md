# BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package

日期：2026-06-29

BEA-v1-N10AG 是 N10AF 之后的 public-only claim-boundary package。它读取 committed public N10AB、N10AC、N10AD、N10AE、N10AF、N10X 与 N10Z artifacts。不进行 private reads，不进行 private scans，也不 recompute metrics。

## 结果

```text
status: fixed_span_window_repair_claim_boundary_package_complete_n10ah_authorized
self-test: 15 / 15
forbidden scan: pass
denominator: 213
baseline top10 span overlap: 9
pm50 top10 span overlap: 19
pm50 top20 span overlap: 23
pm50 delta top10: +10
pm50 original span-hit loss: 0
pm20 top10 span overlap: 15
pm100 top10 span overlap: 21
N10AD aggregate match: true
N10AD N10AB code call count: 0
N10AF positive-delta subgroups: 7
N10AF baseline-hit negative-delta subgroups: 0
```

## Locked claim boundary

Allowed claim：scoped N1 span-surface fixed-pool pm50 span-window repair smoke/robustness pass。

Forbidden claims 仍然禁止：runtime/default promotion、method winner、downstream value、P5/BEA-v1-A、broad generalization、selector/reranker、retrieval/rerun、candidate generation、gold-as-policy 与 adaptive tuning。

## Motivation chain

N10X 显示 unexpanded span-level proxy 低于 threshold。N10Z 将 gap 分解为 same-file span-window misalignment。N10AA 定义 fixed, gold-free pm50 repair。N10AB 通过 direct smoke，N10AC 完成 audit，N10AD 独立 recompute，N10AE 打包 replication，N10AF 通过 subgroup robustness。

## 决策

N10AG 只授权 `BEA-v1-N10AH Default-Off Implementation Feasibility Preflight`，scope 为 `default_off_implementation_feasibility_preflight_only`。它不授权 actual runtime implementation、runtime/default promotion、private reads、retrieval/reruns、candidate generation/materialization、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package.py`
- Report: `artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json`
