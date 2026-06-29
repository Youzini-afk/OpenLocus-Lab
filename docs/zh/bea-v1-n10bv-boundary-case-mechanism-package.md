# BEA-v1-N10BV Boundary Case Mechanism Package

日期：2026-06-29

BEA-v1-N10BV 是 N10BU one-case boundary mechanism decomposition 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: boundary_case_mechanism_package_complete_n10bw_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BV: 0
recomputes in N10BV: 0
N10BW authorized: true
```

## Packaged boundary-case facts

Fixed `25/75` cost75 vs cost80 comparison：

| Cost | top10/top20 | Lost plateau core | File-hit top10 count |
| ---: | ---: | ---: | ---: |
| 75 | 19 / 23 | 1 | 34 |
| 80 | 20 / 24 | 0 | 34 |

Transition counts：recovered-at-80/missed-at-75 `1`；reverse count `0`。

Boundary case mechanism：before_gold_gap `1`，after_gold_gap `0`，already_overlap `0`，other `0`，distance bucket `near_1_5`，file_hit_top10 `true`，just_outside_75_window `true`，recovered_at_80 `true`。

Public artifact 不包含 exact lines、spans、paths、snippets、gold content、candidate lists、ranks 或 private row identifiers。

## Handoff

N10BV 只授权 `BEA-v1-N10BW Adapter Operating-Point Smoke for cost80_before25_after75`：default-off eval-only adapter path、same scoped N1 span rows、仅 fixed operating point，且无 runtime/default promotion 或 existing evaluator hook-in。

## Artifact

- Script: `eval/bea_v1_n10bv_boundary_case_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bv_boundary_case_mechanism_package/bea_v1_n10bv_boundary_case_mechanism_package_report.json`
