# P31-H2 Strategy Reach Matrix 真实 Remote Smoke

## 摘要

- 汇总 6 个成功 runs；排除 1 个 artifact 上传失败 run（`27507065788`，GitHub `ECONNRESET`）。
- 总任务数：`108`
- Positive tasks：`48`
- 仅诊断：`promotion_ready=false`、`default_should_change=false`、`candidate_not_fact=true`。

## 主要发现

`symbol_regex_union` 的 candidate reach ceiling 最高，但不能因此把它当成安全 primary evidence。

K=5：

| strategy | GoldFileReach | GoldSpanReach | CandidateAbsentRate | FileRightSpanWrongRate | UniqueGoldSpanReach |
|---|---:|---:|---:|---:|---:|
| `candidate_baseline` | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.0000 |
| `rrf_primary` | 0.4375 | 0.4375 | 0.5625 | 0.0000 | 0.0000 |
| `symbol_regex_union` | 0.9375 | 0.8750 | 0.0625 | 0.0667 | 0.3750 |
| `llm_span_narrow` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |
| `llm_filter` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |
| `llm_abstain_filter` | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 0.0000 |

具体计数：

- `candidate_baseline`：K=5 span reach 为 `24/48`。
- `rrf_primary`：K=5 span reach 为 `21/48`。
- `symbol_regex_union`：K=5 span reach 为 `42/48`。
- `symbol_regex_union` unique span reach：`18/48`。

## 组合 reach

| combination | UnionGoldSpanReach@5 | UnionGoldFileReach@5 |
|---|---:|---:|
| `candidate_baseline__plus__llm_span_narrow` | 0.5000 | 0.5000 |
| `candidate_baseline__plus__rrf_primary` | 0.5000 | 0.5000 |
| `candidate_baseline__plus__symbol_regex_union` | 0.8750 | 0.9375 |
| `candidate_baseline__plus__symbol_regex_union__plus__rrf_primary` | 0.8750 | 0.9375 |
| `symbol_regex_union__plus__rrf_primary` | 0.8750 | 0.9375 |

有效的 ceiling 提升几乎全部来自加入 `symbol_regex_union`：

- `candidate_baseline + rrf_primary`：span reach `0.5000`。
- `candidate_baseline + llm_span_narrow`：span reach `0.5000`。
- `candidate_baseline + symbol_regex_union`：span reach `0.8750`。

## 同批策略背景

| policy | added_gold_span | added_false_span |
|---|---:|---:|
| `bucket_routed_v0` | 16 | 44 |
| `admission_v3_h1` | 18 | 87 |
| `admission_v3_h2` | 15 | 90 |

这解释了 P31 与 P30-H3 的关系：

- P31-H2 说明 `symbol_regex_union` 对 candidate reach 很有价值。
- P30-H3 说明 local primary-admit actions，尤其 `admit_symbol_regex_union`，主导 false-span cost。
- 因此下一步不是丢掉 `symbol_regex_union`，而是把它作为 candidate expansion 进行 repair/calibration，并在 primary admission 前加 action budget。

## 解释边界

允许的结论：

> 在本轮 smoke 中，`symbol_regex_union` 是高 reach 的候选扩展来源，但同批 reach 不能证明它适合作为 primary evidence。

禁止的结论：

- 不 promote `symbol_regex_union` 为默认。
- 不改变 EvidenceCore。
- 不用同批 reach matrix 直接路由未来任务。
- 不把 candidate reach 等同于 evidence quality。

## 下一步

继续：

1. `P33 Reach-Preserving Precision Anchor Repair`：修复/校准 symbol/regex anchors，测试能否保留高 reach 且不增加 false primary。
2. `P32 / P30-H4 Action-Specific Span Budget`：在 `symbol_regex_union` 或 `rrf_primary` 升为 primary 前要求预算化 guard。

## 安全说明

- P31-H1 private candidate pools 与 gold spans 只存在于 runner ephemeral records。
- 本报告只存聚合 counts/rates。
- 不存 task IDs、candidate paths/spans、gold spans、raw snippets、prompts、responses 或 provider fields。
