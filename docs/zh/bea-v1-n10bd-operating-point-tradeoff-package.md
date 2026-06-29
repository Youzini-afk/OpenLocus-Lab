# BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package

日期：2026-06-29

BEA-v1-N10BD 是 N10BC operating-point tradeoff decomposition 的 public-only audit/package。它只读取 public artifacts。它不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不改变 runtime/default behavior。

## 结果

```text
status: operating_point_tradeoff_package_complete_n10be_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BD: 0
recomputes in N10BD: 0
N10BE authorized: true
```

## Packaged tradeoff facts

| Step | Variant | Cumulative top10/top20 | Marginal top10/top20 | Marginal cost | Cost bucket | Lost previous hits |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| baseline | baseline | 9 / 10 | +9 / +10 | 0 | baseline | 0 |
| low_cost | pm30 | 18 / 22 | +9 / +12 | +600 | low | 0 |
| balanced | before25_after75 | 20 / 24 | +2 / +2 | +400 | medium | 0 |
| max_recall | pm200 | 25 / 30 | +5 / +6 | +3000 | very_high | 0 |

Candidate pool 与 candidate order 保持不变。

## Mechanism package

所有 marginal top-10 gains 都是 before/after gold-window gap recoveries：

- baseline -> low_cost：8 before-gold gap，1 after-gold gap。
- low_cost -> balanced：2 before-gold gap。
- balanced -> max_recall：3 before-gold gap，2 after-gold gap。

因此，N10BD 打包 N10BC 的解释：max_recall 与 lower-cost points 使用相同机制，不是 qualitatively new mechanism。

## Handoff

N10BD 只授权 `BEA-v1-N10BE Cost-Aware Operating-Point Decision Smoke`：same scoped N1 rows，无 new variants，budget buckets 为 `strict_budget <=600 -> low_cost`、`moderate_budget <=1000 -> balanced`、`recall_budget <=4000 -> max_recall`，并且只输出 public aggregate/bucket，不作 runtime/default recommendation。

## Artifact

- Script: `eval/bea_v1_n10bd_operating_point_tradeoff_package.py`
- Report: `artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json`
