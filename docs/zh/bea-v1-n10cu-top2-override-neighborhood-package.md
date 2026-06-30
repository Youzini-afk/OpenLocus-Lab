# BEA-v1-N10CU Top2 Override Neighborhood Public Package

日期：2026-06-30

BEA-v1-N10CU 是 N10CT top2 override window neighborhood sweep 的 public-only package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: top2_override_neighborhood_package_complete_n10cv_authorized
self-test: 11 / 11
forbidden scan: pass
private reads in N10CU: 0
recomputes in N10CU: 0
N10CV authorized: true
```

## Packaged facts

- N10CT completed with 9 fixed variants：pm200、pm225、pm250、pm275、pm300、pm325、pm350、pm375、pm400。
- pm200：top10/top20 `25 / 31`，cost10/cost20 `3200 / 6200`。
- pm275：top10/top20 `26 / 32`，cost10/cost20 `3500 / 6500`；它是第一个/最小 tested pm，能保持 `26 / 32`，lost pm300 top10 hits `0`，且成本低于 pm300。
- pm300：top10/top20 `26 / 32`，cost10/cost20 `3600 / 6600`。
- pm325、pm350、pm375：均为 `26 / 32`。
- pm400：top10/top20 `27 / 33`，cost10/cost20 `4000 / 7000`，相对 pm300 提升 `+1 / +1`。
- Candidate pool/order 不变；没有 top3 override，也没有 medium/long extra gates。

## Boundary

N10CU 只是 same-source N1 proxy packaging。它不授权 private reads、recompute、new variants、runtime/default enablement、existing evaluator hooks、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、top3 override、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CU 只授权 `BEA-v1-N10CV Follow-up Around pm400 Gain`，下一步需由 oracle contract 限定为 pm400 gain mechanism analysis 或 pm400-neighborhood exploration。

## Artifact

- Script: `eval/bea_v1_n10cu_top2_override_neighborhood_package.py`
- Report: `artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json`
