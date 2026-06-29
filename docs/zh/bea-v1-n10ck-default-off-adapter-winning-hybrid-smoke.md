# BEA-v1-N10CK Default-Off Adapter Smoke for Winning Hybrid

日期：2026-06-29

BEA-v1-N10CK 是 winning hybrid `short75_225_top3_all_pm200` 的 implementation smoke，使用现有 default-off eval-only span-window adapter path。它不是 runtime/default promotion，也不 hook existing validated evaluators。

## 结果

```text
status: winning_hybrid_adapter_smoke_pass_n10cl_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
winning hybrid: short75_225_top3_all_pm200
top10/top20 span overlap: 25 / 31
cost10/cost20: 3300 / 6300
lost short75/225 hits: 0
file-hit top10 count: 34
candidate pool/order changed: false
N10CL authorized: true
```

## Adapter semantics

N10CK 使用 default-off eval-only adapter/helper path。对 existing order 中每个 evidence item：

- short original span（`<=10` lines）：expand before `75`、after `225`；
- top3 evidence positions：无论 span length 如何，应用 all-span pm200（`200 / 200`）；
- 如果两条规则同时适用，使用更宽的 top3 pm200 window；
- 其他情况不 expansion。

Gold 只在 projection 后用于 evaluation。Candidate pool 与 order 保持不变。

## Boundary

N10CK 不修改 runtime/default behavior，不 hook existing validated evaluators，不运行 retrieval/reruns/OpenLocus，不 generate/add/remove/reorder candidates，不进行 adaptive tuning，也不声明 heldout/generalization、method-winner 或 downstream-value claims。

## Handoff

N10CK 只授权 `BEA-v1-N10CL Winning Hybrid Adapter Smoke Package`，即不进行额外 private reads 的 public audit/package。

## Artifact

- Script: `eval/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke.py`
- Report: `artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json`
