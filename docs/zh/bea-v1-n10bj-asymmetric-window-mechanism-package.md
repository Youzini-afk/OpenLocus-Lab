# BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package

日期：2026-06-29

BEA-v1-N10BJ 是 N10BI pm50 vs `before25_after75` direction decomposition 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: asymmetric_window_mechanism_package_complete_n10bk_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BJ: 0
recomputes in N10BJ: 0
N10BK authorized: true
```

## Packaged mechanism facts

- Fixed symmetric `pm50`：top10/top20 `19 / 23`，cost proxy `1000`。
- Asymmetric `before25_after75`：top10/top20 `20 / 24`，cost proxy `1000`。
- Net gain：`+1 / +1`。
- Top10 gained cases：`1`；top10 lost cases：`0`。
- Gained buckets：`before_gold_gap=1`，`after_gold_gap=0`，`already_overlap=0`，`other=0`。
- Lost buckets：全部为 `0`。

该 package 确认 no-gold policy boundary：fixed global windows、无 per-row adaptation、无 gold/miss-direction signal 用于选择 per-record windows。

## Handoff

N10BJ 只授权 `BEA-v1-N10BK Neighboring Asymmetry Micro-Sweep`：same scoped N1 rows、仅 same cost proxy `1000`，并且只包含预声明 variants `before0_after100`、`before25_after75`、`before50_after50`、`before75_after25`、`before100_after0`。N10BK 用于 direction sensitivity mapping，不是选择默认值。N10BJ 不授权 new cost budgets、adaptive per-row choices、runtime/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bj_asymmetric_window_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json`
