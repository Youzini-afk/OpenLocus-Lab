# BEA-v1-N10CQ Refined Hybrid Mechanism Decomposition

日期：2026-06-29

BEA-v1-N10CQ 是 refined hybrid `short75_225_top2_all_pm200` 的 direct empirical same-source mechanism decomposition。它不是 new variant sweep。它只读取 same scoped N1 span rows，并比较 exactly five fixed reference policies。

## 结果

```text
status: refined_hybrid_mechanism_decomposition_complete_n10cr_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
policies evaluated: 5
refined hybrid: 25 / 31
top1 result: 24 / 30
top3 result: 25 / 31
pm200 all-spans result: 25 / 30
N10CR authorized: true
```

## Mechanism facts

- `short75_225`: `24 / 30`，cost10/cost20 `3000 / 6000`。
- `short75_225_top1_all_pm200`: `24 / 30`，cost10/cost20 `3100 / 6100`。
- `short75_225_top2_all_pm200`: `25 / 31`，cost10/cost20 `3200 / 6200`。
- `short75_225_top3_all_pm200`: `25 / 31`，cost10/cost20 `3300 / 6300`。
- `pm200_all_spans`: `25 / 30`，cost10/cost20 `4000 / 8000`。

Top2 vs top1 恰好恢复 1 个 top10 case：rank2 override recovers the case，rank1 insufficient，且该 case 是 non-short-span。Top3 vs top2 增加 0 个 top10 recoveries。Refined hybrid 下剩余 top10 misses 合计 188：file not in top10 `167`，same-file no span overlap `9`，span overlap beyond top10 `12`，not span reachable `0`。

## Boundary

Gold/outcome/miss-direction 仅用于 post-hoc bucketed evaluation，不作为 policy。N10CQ 不 add/remove/reorder candidates，不运行 retrieval/rerun/OpenLocus，不生成 candidates，不进行 adaptive tuning，不执行 selector/reranker logic，不进入 P5/BEA-v1-A，不启用 runtime/default behavior，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## Handoff

N10CQ 只授权 `BEA-v1-N10CR Mechanism-Guided Refined Hybrid Sweep`：same scoped rows、fixed variants derived from N10CQ，且无 runtime/default 或 broad claims。

## Artifact

- Script: `eval/bea_v1_n10cq_refined_hybrid_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json`
