# P52C 诊断性本地验证器评分模拟器

- Schema: `p52c-local-verifier-scoring-simulator-v1`
- 用途：仅用于诊断的评分模拟，**不是**验证器通过/失败判定，**不是**证据（Evidence），**不是**准入/默认/晋升决策。
- P52C 不调用 LLM，不构造提示词，不进行远程调用；仅通过 P52A/P52B 已有的有界辅助工具读取本地源码。
- 评分完全与 gold/标签/结果无关；gold 与结果仅在固定分桶后的 `score_phase_diagnostic_correlation` 中使用。

## 方法概述

1. 加载 `p25-policy-records-ephemeral-v1` 临时记录（或确定性自测记录）。
2. 通过 P46/P49 规范化候选，通过 P52A 解析有界仓库根目录。
3. 复用 P52A 的源码物化结果与 P52B 的源码形态特征。
4. 使用固定公式 `p52c_diagnostic_score_v0` 对候选打分；不可用特征不被计入，也不产生虚假证据。
5. 仅发布聚合桶：`diagnostic_score_high` / `diagnostic_score_medium` / `diagnostic_score_low` / `diagnostic_score_unavailable`；不公开单个候选分数。
6. 按公共维度（元数据风险桶、源码特征桶、path_kind、subtype、RRF backing、公共桶/风险标签、策略、打包策略）输出聚合细分。

## 安全声明

- P52C 不产生 evidence，不进行 evidence 验证。
- P52C 不做 verifier pass/fail 判定，不提供 local verifier score。
- P52C 不证明 P51/P53 质量。
- 源码读取是有界的；不存储原始源码、片段、路径、行范围或摘要。

## 典型指标

| 指标 | 含义 |
|---|---|
| `p52c_score_availability` | `available_source_backed` / `partial_source_backed` / `partial_metadata_only` / `unavailable_no_source_reads` / `unavailable_missing_candidate_pool` |
| `source_backed_score_candidate_denominator` | 以源码特征打分的候选数 |
| `metadata_only_candidate_denominator` | 仅基于元数据打分的候选数 |
| `score_unavailable_candidate_count/rate` | 因元数据缺失而无可用工分的候选数/比例 |
| `diagnostic_score_bucket_counts/rates` | 高/中/低/不可用四个分桶的聚合计数与比例 |
| `score_bin_distribution` | 分数区间（`<= -3`、`-2_-1`、`0_1`、`2_3`、`>= 4`）分布 |
| `score_phase_diagnostic_correlation` | 固定分桶后按桶统计的 gold_file / gold_span / file_right_span_wrong / no_gold 比例，以及可选的现有角色 delta |

## 输出文件

- JSON 报告：`artifacts/p52c_local_verifier_scoring_simulator/p52c_local_verifier_scoring_simulator_report.json`
- 英文详细报告：`docs/en/p52c-local-verifier-scoring-simulator.md`
