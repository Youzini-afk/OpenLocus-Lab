# BEA-v1-N10CR Mechanism-Guided Local Saturation Sweep

日期：2026-06-29

BEA-v1-N10CR 是对 scoped N1 span rows 的 direct empirical same-source sweep。它在转向 rank/file-reach 机制之前，测试 refined hybrid 的 local-window family 是否已经饱和。它保持 candidate order 不变，也不 add/remove candidates。

## 结果

```text
status: mechanism_guided_local_saturation_sweep_complete_n10cs_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
variants evaluated: 8
refined anchor: 25 / 31 at 3200 / 6200
pm200 all-spans: 25 / 30 at 4000 / 8000
best variant: top2_pm300_short75_225
best result: 26 / 32 at 3600 / 6600
overall local saturation: false
N10CS authorized: true
```

## Key finding

Local span-window family **还没有饱和**。机制引导 variant `top2_pm300_short75_225` 将 refined anchor 从 `25 / 31` 提升到 `26 / 32`，且没有改变 candidate order，也没有新增 candidates。

## Variant results

- `anchor_refined_top2_pm200_short75_225`：`25 / 31`，cost10/cost20 `3200 / 6200`。
- `anchor_pm200_all_spans`：`25 / 30`，cost10/cost20 `4000 / 8000`。
- `top2_pm200_short90_270`：`25 / 31`，cost10/cost20 `3680 / 7280`。
- `top2_pm200_short100_300`：`25 / 31`，cost10/cost20 `4000 / 8000`。
- `top2_pm200_short75_225_medium40_120`：`25 / 31`，cost10/cost20 `3200 / 6200`。
- `top2_pm200_short75_225_medium75_225`：`25 / 31`，cost10/cost20 `3200 / 6200`。
- `top2_pm200_short75_225_medium75_225_long75_225`：`25 / 31`，cost10/cost20 `3200 / 6200`。
- `top2_pm300_short75_225`：`26 / 32`，cost10/cost20 `3600 / 6600`。

Winning local variant 将 same-file/no-span-overlap remaining cases 从 9 降到 8，同时保持 fixed order。最大的剩余 blocker 仍然是 file reach/rank：best variant 下 `file_not_in_top10` 仍为 167。

## Boundary

N10CR 不改变 candidate order，不 add/remove candidates，不运行 retrieval/rerun/OpenLocus，不生成 candidates，不执行 selector/reranker logic，不进入 P5/BEA-v1-A，不启用 runtime/default behavior，也不作 heldout/generalization、method-winner 或 downstream-value claims。Gold/outcome information 只用于 aggregate evaluation，不作为 policy。

## Handoff

N10CR 只授权 `BEA-v1-N10CS Local Saturation Sweep Public Package`。它不授权 runtime/default promotion、existing evaluator hook-in、retrieval/rerun、candidate generation、rank/file promotion 或 broad claims。

## Artifact

- Script: `eval/bea_v1_n10cr_mechanism_guided_local_saturation_sweep.py`
- Report: `artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json`
