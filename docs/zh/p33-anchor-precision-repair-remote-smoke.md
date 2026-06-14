# P33 Anchor Precision Repair 真实 Remote Smoke

## 摘要

- 汇总 runs：`6/6` 成功。
- 任务观测数：`108`（`48` positive，`60` no-gold）。
- 仅诊断：`promotion_ready=false`、`default_should_change=false`、`candidate_not_fact=true`。

## 主要发现

P33 确认了 P31-H2/P30-H3 的张力：symbol/regex 派生 anchors 可以有高 reach，但同批 anchor buckets 仍携带很高 false-span cost。没有任何 observed bucket 适合 primary admission。

## 关键 anchor buckets

| bucket | tasks | positive/no-gold | GoldSpanReach@5 | added_gold | added_false | false_per_gold | net_span_value_2x | class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `symbol_regex_agree_span` | 9 | 9/0 | 1.0 | 15 | 60 | 4.0 | -105 | `insufficient_denominator` |
| `symbol_regex_agree_span_low_risk` | 9 | 9/0 | 1.0 | 15 | 60 | 4.0 | -105 | `insufficient_denominator` |
| `rrf_anchor_agree_span` | 60 | 48/12 | 0.875 | 48 | 528 | 11.0 | -1008 | `blocked_high_false_cost` |
| `symbol_regex_disagree` | 39 | 30/9 | 0.9 | 27 | 363 | 13.444444444444445 | -699 | `blocked_high_false_cost` |
| `regex_only` | 15 | 9/6 | 0.6666666666666666 | 6 | 135 | 22.5 | -264 | `insufficient_denominator` |
| `query_noise_low` | 93 | 45/48 | 0.8666666666666667 | 45 | 450 | 10.0 | -855 | `blocked_high_false_cost` |
| `query_noise_high` | 9 | 3/6 | 1.0 | 3 | 78 | 26.0 | -153 | `insufficient_denominator` |
| `positive_bucket` | 12 | 12/0 | 1.0 | 18 | 87 | 4.833333333333333 | -156 | `blocked_high_false_cost` |

## Calibration summary

| cell | tasks | positive/no-gold | GoldSpanReach@5 | added_gold | added_false | false_per_gold | net_span_value_2x |
|---|---:|---:|---:|---:|---:|---:|---:|
| `a3_r0_s2` | 48 | 48/0 | 0.875 | 48 | 417 | 8.6875 | -786 |

本轮 smoke 中唯一有数据的 calibration cell 是 `a3_r0_s2`：span-agreement、low-risk、RRF-span-backed。它覆盖 `42/48` 个 positive spans，但 `false_per_gold≈8.69`，说明即使看似最强的 local-anchor cell，也不能不加预算 guard 就 primary。

## 解释

- `symbol_regex_agree_span` 在该 bucket 内覆盖全部 9 个 positive observations，但 `false_per_gold=4.0`，`net_span_value_2x=-105`。
- `symbol_regex_disagree` 仍有高 reach（`27/30`），但 false cost 更差（`false_per_gold≈13.44`）。
- `regex_only` 风险尤其高（`false_per_gold=22.5`）。
- `query_noise_low` 本身不构成安全条件（`false_per_gold=10.0`）。

## P33 -> P32/H4 handoff

同批 P33 没有发现 primary-safe bucket，只给出 budget candidates：

- 保留 `symbol_regex_union` 作为 candidate expansion source；
- 在 `admit_symbol_regex_union` 或 `admit_rrf_primary` 之前要求更严格 action budget；
- 区分 span agreement、file-only、disagree cases；
- 不要把 query-noise-low 或 RRF-span-backed 当成充分安全证据。

## 安全说明

- P33 本身没有远程调用；远程调用只来自外层 P21 workflow。
- Private P31 candidate pools 和 SCORE gold spans 只存在于 runner temp records。
- 本报告只保存聚合 counts/rates。
- 不保存 task IDs、candidate coordinates、gold spans、raw snippets、prompts、responses、route features、provider keys 或 base URLs。
