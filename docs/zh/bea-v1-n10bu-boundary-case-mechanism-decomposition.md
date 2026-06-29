# BEA-v1-N10BU Boundary Case Mechanism Decomposition

日期：2026-06-29

BEA-v1-N10BU 是对固定 `25/75` ratio 在 total cost 75 miss、但在 total cost 80 recover 的单个 plateau-core case 的 direct empirical decomposition。它只读取 same scoped N1 span rows 和 public N10BT/N10BS/N10BR artifacts。它不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: boundary_case_mechanism_decomposition_complete_n10bv_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
boundary comparison: cost75 19/23 vs cost80 20/24
recovered-at-80/missed-at-75 cases: 1
N10BV authorized: true
```

## Boundary comparison

| Cost | top10/top20 | Lost plateau core | File-hit top10 count | Transition count |
| ---: | ---: | ---: | ---: | ---: |
| 75 | 19 / 23 | 1 | 34 | 1 recovered at 80 |
| 80 | 20 / 24 | 0 | 34 | 1 recovered at 80 |

## Mechanism facts

对于这个 recovered-at-80/missed-at-75 的单个 case：

- gap bucket：`before_gold_gap`
- distance-to-expanded-window bucket：`near_1_5`
- file hit remains top10：true
- span overlap is just outside the 75-cost window：true
- recovered at cost 80：true

所有事实均为 bucket/count only。Public artifact 不包含 private path、line number、span、snippet、gold content、candidate list、exact rank 或 row identifier。

## Handoff

N10BU 只授权 `BEA-v1-N10BV Boundary Case Mechanism Package`，即该 one-case boundary mechanism result 的 public package。

## Artifact

- Script: `eval/bea_v1_n10bu_boundary_case_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10bu_boundary_case_mechanism_decomposition/bea_v1_n10bu_boundary_case_mechanism_decomposition_report.json`
