# BEA-v1-N10DK N10T-Order Rank-Promotion Public Package

日期：2026-06-30

BEA-v1-N10DK 是 N10DJ N10T-order file-reach rank-promotion smoke 的 public-only package。它只读取 public artifacts，不进行 private reads、recompute 或 new rank-promotion variants。

## 结果

```text
status: n10t_order_rank_promotion_public_package_complete_n10dl_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DK: 0
recomputes in N10DK: 0
N10DL authorized: true
```

## Packaged conclusions

- N10DJ 在 same N10T-best-order candidate list 上完成 8 个 fixed variants。
- Anchor file top10/top20 为 `34 / 44`；anchor projected span top10/top20 为 `30 / 36`。
- 朴素 deeper-rank promotion 有害：
  - `promote_rank11_20_before_rank6_10`：file/span `24 / 44` 和 `22 / 36`。
  - `interleave_top10_with_rank11_20_1to1_after_top5`：file/span `29 / 44` 和 `26 / 36`。
  - `promote_rank21_50_after_top5_before_rank6_10`：file/span `23 / 30` 和 `22 / 27`。
- Distinct-fill rank11-50/rank11-100 与 max-per-file-2 variants 为 neutral：file `34 / 44`，projected span `30 / 36`。

解释：不要盲目 promote fixed deeper bands。下一步有价值的问题是：为什么 correct files 仍不在 N10T top10 中，以及哪些 observable structure 能预测 safe promotion。

## Boundary

N10DK 不授权 runtime/default behavior、heldout/generalization claims、retrieval/rerun、candidate generation/materialization/add/remove、selector/reranker execution、P5、BEA-v1-A、method-winner claims、downstream-value claims 或 broad private reads。

## Handoff

N10DK 只授权 `BEA-v1-N10DL N10T Top10 File-Reach Residual Analysis`，范围由下一份 oracle contract 限定为 same scoped rows。

## Artifact

- Script: `eval/bea_v1_n10dk_n10t_order_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dk_n10t_order_rank_promotion_public_package/bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json`
