# BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package

日期：2026-06-29

BEA-v1-N10CN 是 N10CM winning-hybrid cost-reduction refinement sweep 的 public-only audit/package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: winning_hybrid_cost_refinement_package_complete_n10co_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CN: 0
recomputes in N10CN: 0
N10CO authorized: true
```

## Packaged facts

- Winning reference `short75_225_top3_all_pm200`：top10/top20 `25 / 31`，cost10/cost20 `3300 / 6300`。
- Refined result `short75_225_top2_all_pm200`：top10/top20 `25 / 31`，cost10/cost20 `3200 / 6200`，相对 winning reference 节省 `100 / 100`，lost winning top10 hits 为 `0`。
- `short75_225_top1_all_pm200`、`short75_225_top3_all_pm150` 和 `short75_225_top3_all_pm175` 降至 `24 / 30`，并各丢失 1 个 winning top10 hit。
- N10CM 没有发现 `improves_winning` variants，并发现 1 个 `preserves_winning_at_lower_cost` variant。
- Candidate pool/order 保持不变。

## Boundary

N10CN 只打包 same-source N1 proxy result。Policy inputs 仅为 observable span-length bucket 与 candidate-position bucket；gold/outcome/direction/content/file identity 不是 policy inputs。N10CN 不授权 runtime/default enablement、existing evaluator hook-in、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、adaptive tuning、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CN 只授权 `BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid short75_225_top2_all_pm200`。

## Artifact

- Script: `eval/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package.py`
- Report: `artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json`
