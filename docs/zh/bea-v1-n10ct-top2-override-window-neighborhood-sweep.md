# BEA-v1-N10CT Top2 Override Window Neighborhood Sweep

日期：2026-06-30

BEA-v1-N10CT 是围绕 N10CR/N10CS positive `top2_pm300_short75_225` 结果的 direct empirical same-source sweep。它只读取 same scoped N1 span rows 以及 public N10CS/N10CR/N10CP artifacts。它不运行 retrieval/reruns/OpenLocus，不生成、添加、移除或重排 candidates，不添加 rank/order arms，不使用 top3 overrides，不增加 medium/long gates，不进行 adaptive tuning，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: top2_override_window_neighborhood_sweep_complete_n10cu_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 9
minimum pm for 26/32: 275
max observed top10/top20: 27 / 33
N10CU authorized: true
```

## Variant findings

所有 variants 使用相同 base rule：short spans 使用 before75/after225，top2 positions 使用 symmetric all-span pmX override。

| Variant | top10/top20 | cost10/cost20 | Decision |
| --- | ---: | ---: | --- |
| short75_225_top2_all_pm200 | 25 / 31 | 3200 / 6200 | no_improvement_pm300_retained |
| short75_225_top2_all_pm225 | 25 / 31 | 3300 / 6300 | no_improvement_pm300_retained |
| short75_225_top2_all_pm250 | 25 / 31 | 3400 / 6400 | no_improvement_pm300_retained |
| short75_225_top2_all_pm275 | 26 / 32 | 3500 / 6500 | preserves_pm300_at_lower_cost |
| short75_225_top2_all_pm300 | 26 / 32 | 3600 / 6600 | no_improvement_pm300_retained |
| short75_225_top2_all_pm325 | 26 / 32 | 3700 / 6700 | no_improvement_pm300_retained |
| short75_225_top2_all_pm350 | 26 / 32 | 3800 / 6800 | no_improvement_pm300_retained |
| short75_225_top2_all_pm375 | 26 / 32 | 3900 / 6900 | no_improvement_pm300_retained |
| short75_225_top2_all_pm400 | 27 / 33 | 4000 / 7000 | improves_pm300 |

保持 26/32 的最小 pm window 是 pm275。测试中最大 window pm400 提升到 27/33。

## Boundary

N10CT 仅为 same-source N1 proxy evidence。Policy inputs 是 fixed windows 与 candidate position；gold/outcome/miss-direction/content/file identity 不是 policy inputs。Candidate pool/order 保持不变。该结果不授权 runtime/default behavior、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、top3 overrides、medium/long extra gates、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CT 只授权 `BEA-v1-N10CU Top2 Override Neighborhood Public Package`，即不进行 private reads、recompute 或 new variants 的 public package。

## Artifact

- Script: `eval/bea_v1_n10ct_top2_override_window_neighborhood_sweep.py`
- Report: `artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json`
