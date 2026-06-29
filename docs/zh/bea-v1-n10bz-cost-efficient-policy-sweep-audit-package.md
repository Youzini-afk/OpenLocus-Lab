# BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package

日期：2026-06-29

BEA-v1-N10BZ 是 N10BY same-source cost-efficient span-window policy sweep 的 public-only audit/package。它只读取 public artifacts。不进行 private reads、不 recompute、不做 extra sweeps、不添加 new variants、不 adaptive tuning、不运行 retrieval/rerun/OpenLocus、不生成 candidates，也不进行 runtime/default promotion。

## 结果

```text
status: cost_efficient_policy_sweep_package_complete_n10ca_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BZ: 0
recomputes in N10BZ: 0
N10CA authorized: true
```

## Packaged N10BY facts

- N10BY 已完成，包含 12 个预声明 variants。
- Anchor `cost80_before20_after60`：top10/top20 `20 / 24`，top10 cost `800`，top20 cost `1600`。
- Lower-cost fixed 70/72/75/78 variants：全部为 `19 / 23`，各丢失一个 anchor top10 hit。
- Rank-conditioned variants：全部为 `19 / 20`，lost anchor counts 为 `1 / 1 / 2`。
- `top10_only_cost80_before20_after60`：`20 / 21`。
- `top5_only_cost80_before20_after60`：`12 / 13`。
- `top20_only_cost80_before20_after60`：`20 / 24`，但相对 anchor 没有相关的 top10 cost reduction。
- Cost-reduction successes：`0`；recall-improvement successes：`0`；successful variants：`0`。

结论：该 fixed-window cost-efficient policy sweep 未发现超过 cost80 anchor 的改进。Cost80 目前看起来是 same-source N1 rows 上 fixed-window-family 的边界。这是有用的 negative research，不是停止条件。

## Handoff

N10BZ 只授权 `BEA-v1-N10CA Next Mechanism Search Outside Fixed-Window Family`：bounded next mechanism search，若可行则 same-source empirical。它不授权 runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package.py`
- Report: `artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json`
