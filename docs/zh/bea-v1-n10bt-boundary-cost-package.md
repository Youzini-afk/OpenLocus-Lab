# BEA-v1-N10BT Boundary-Cost Package

日期：2026-06-29

BEA-v1-N10BT 是 N10BS boundary-cost refinement sweep 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: boundary_cost_package_complete_n10bu_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BT: 0
recomputes in N10BT: 0
N10BU authorized: true
```

## Packaged boundary-cost facts

Fixed ratio：`25/75`。Costs：`65`、`70`、`75`、`80`、`85`、`90`、`95`。

| Total cost | top10/top20 | Lost plateau core | Preserved plateau |
| ---: | ---: | ---: | --- |
| 65 | 19 / 22 | 1 | false |
| 70 | 19 / 22 | 1 | false |
| 75 | 19 / 23 | 1 | false |
| 80 | 20 / 24 | 0 | true |
| 85 | 20 / 24 | 0 | true |
| 90 | 20 / 24 | 0 | true |
| 95 | 20 / 24 | 0 | true |

Boundary summary：minimum preserving cost `80`；boundary 以下第一个失败值 `75`；margin `5`；monotonicity bucket `nondecreasing_top10`。Chosen research point 是 `cost80_before25_after75`，明确不是 runtime/default recommendation，也不是 method-winner claim。

## Handoff

N10BT 只授权 `BEA-v1-N10BU Boundary Case Mechanism Decomposition`：same scoped rows，比较 fixed 25/75 在 costs 75 与 80 的结果，并且只对在 80 恢复但在 75 miss 的 1 个 case 做 bucketed mechanism 分析。

## Artifact

- Script: `eval/bea_v1_n10bt_boundary_cost_package.py`
- Report: `artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json`
