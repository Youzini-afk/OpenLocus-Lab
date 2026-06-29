# BEA-v1-N10CL Winning Hybrid Adapter Smoke Public Package

日期：2026-06-29

BEA-v1-N10CL 是 N10CK default-off adapter smoke 的 public-only package。它只读取 public artifacts，不进行 private reads、不 recompute，也不添加 new variants。

## 结果

```text
status: winning_hybrid_adapter_package_complete_n10cm_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CL: 0
recomputes in N10CL: 0
N10CM authorized: true
```

## Packaged adapter smoke facts

- N10CK 使用了现有 default-off eval-only adapter/helper path。
- Winning hybrid：`short75_225_top3_all_pm200`。
- 结果：top10/top20 span overlap `25 / 31`，cost10/cost20 `3300 / 6300`，lost short75/225 hits `0`，file-hit top10 count `34`。
- Candidate pool/order 保持不变。
- N10CK 匹配 N10CJ/N10CI/N10CG expected aggregate values。

## Default-off and hook boundary

N10CL 打包 N10CK boundary：adapter default enabled `false`，private read by default `false`，policy default changed `false`，runtime config changed `false`，runtime default enabled `false`，existing evaluator hook-in `false`，runtime/retrieval/selector hook `false`，且 adapter/helper modules 未被 N10CK 修改。

## Handoff

N10CL 只授权 `BEA-v1-N10CM Winning Hybrid Next-Step Decision`：在 continued mechanism exploration 与 formal default-off variant evaluator for the winning hybrid 之间做选择。它不授权 runtime/default enablement、existing evaluator hook-in、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、adaptive tuning、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cl_winning_hybrid_adapter_smoke_package.py`
- Report: `artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json`
