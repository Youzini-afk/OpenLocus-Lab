# P30-H3 真实 Smoke：按 action 拆分 span 成本

- 成功 runs：`6`
- 总任务：`108`
- 诊断用途：`promotion_ready=false`，`default_should_change=false`

## 聚合对比

| policy | gold | false | false/gold | 平均 ΔSpanF0.5 | 平均 ΔPFP | primary false | non-primary false | unclassified false |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `candidate_baseline` | 27 | 102 | 3.78 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `bucket_routed_v0` | 19 | 45 | 2.37 | -0.0023 | -0.1019 | 4 | 41 | 0 |
| `admission_v3_h1` | 18 | 88 | 4.89 | -0.0362 | -0.1296 | 87 | 1 | 0 |
| `admission_v3_h2` | 15 | 90 | 6.00 | -0.0386 | -0.1389 | 90 | 0 | 0 |

## 主要诊断

- P25 `bucket_routed_v0` 仍是这轮 smoke 的最强 reference：false spans 从 `102` 降到 `45`，gold spans 从 `27` 降到 `19`。
- P30-H1/H2 虽然降低 PFP，但 span-level false cost 远高于 P25。
- H3 说明：P30-H1/H2 的 false-span 成本主要来自 **primary local-admit actions**，不是 non-primary actions。
- 最大问题是 `admit_symbol_regex_union`，以及 H2 中的 `admit_rrf_primary`。
- `supporting_only` 的 false-span 成本低，但会杀 gold；它的代价是 recall loss，不是 false-span pollution。

## false 成本最高的 actions

### `bucket_routed_v0`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `llm_abstain_filter` | non_primary | 63 | 15 | 35 | 2.33 |
| `llm_filter` | non_primary | 33 | 0 | 6 | n/a |
| `llm_span_narrow` | primary | 9 | 4 | 4 | 1.00 |
| `candidate_baseline` | unclassified | 3 | 0 | 0 | n/a |

### `admission_v3_h1`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `admit_symbol_regex_union` | primary | 12 | 18 | 87 | 4.83 |
| `abstain` | non_primary | 27 | 0 | 1 | n/a |
| `apply_llm_filter` | non_primary | 33 | 0 | 0 | n/a |
| `supporting_only` | non_primary | 36 | 0 | 0 | n/a |

### `admission_v3_h2`

| action | kind | selected | gold | false | false/gold |
|---|---|---:|---:|---:|---:|
| `admit_symbol_regex_union` | primary | 9 | 15 | 60 | 4.00 |
| `admit_rrf_primary` | primary | 3 | 0 | 30 | n/a |
| `apply_llm_filter` | non_primary | 48 | 0 | 0 | n/a |
| `supporting_only` | non_primary | 33 | 0 | 0 | n/a |
| `weak_candidate_only` | non_primary | 15 | 0 | 0 | n/a |

## 下一步

P30-H4 不应该只是继续“整体收紧”，而要使用 action-specific budget：

- `admit_symbol_regex_union`：必须要求更强 span-level agreement，否则降级。
- `admit_rrf_primary`：只有 RRF 有本地 span agreement 且 bucket 低风险时才能 primary。
- `supporting_only`：把 gold-kill 当成 recall loss 明确计入，不要当免费安全动作。
- 在 P30 同时赢过 false spans、gold retention 和 SpanF0.5 前，P25 `bucket_routed_v0` 仍保持 reference。

## 安全说明

- H3 是 SCORE/ACCOUNT 阶段的聚合诊断，不参与同轮 routing。
- 公开 artifacts 只包含聚合指标；不存 raw query、snippet、prompt、response、gold span、private label 或 per-task routing。
