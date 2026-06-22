# OpenLocus 当前研究结论

日期：2026-06-22

状态：当前研究结论备忘录。本文不是 promotion request，不是默认策略变更申请，也不是 benchmark leaderboard 报告。

范围：覆盖 BEA-5 quota-sampling 实施中状态、B16-F 至 B16-J live-provider atom ablation、C5 外部 benchmark 检索 smoke、F1 utility smoke，以及 D5-A 自动化校准特征提取/heldout 验证。

## 0. 阅读规则

本文是当前结论，不是完整流水账。

- 完整时间线：[`research-log.md`](research-log.md)
- 长版总结：[`research-summary.md`](research-summary.md)
- 详细阶段文档：见 [`../current-research-conclusions.md`](../current-research-conclusions.md)

根目录 `docs/current-research-conclusions.md` 只作为双语索引入口；不要在里面写状态正文。

## 1. 当前一句话判断

OpenLocus 已经从 control-plane 脚手架进入真实实证阶段：现在有外部 benchmark run、live-provider coding-agent run、私有 per-record SCORE/event trace，以及 aggregate-only 的公开 artifact。

当前最可信的结论必须保守表述：

1. **Context pack 对 live coding-agent 有帮助。** B16-F 中 sparse control solve/test 为 0.25，而 same-budget BM25 与 BEA v0.3 context pack 均为 1.0。
2. **BEA 尚未在 downstream 上超过 same-budget BM25。** B16-F 中 BEA v0.3 与 same-budget BM25 在 solve/test 上打平，且 BEA 需要更多 token/latency。
3. **Support atom 很重要，但必须去掉混杂后才看清。** B16-G/H/I 里的 support-only 足够，是因为 support cue 过强。B16-J 去掉 role-bearing filename 泄漏后，才观察到 bounded target+support conjunction：target+support 8/8，support-only 2/8，target-only 0/8。
4. **BEA v0.3 是 mixed，不是 winner。** BEA-2 提升 file/MRR/success 但损失 span/latency；BEA-3 与 v0.2 基本打平，只带来极小 span/quality-per-latency 信号；BEA-4 在 120 成功记录上仍是 mixed。
5. **BEA-5 尚未完成。** 之前 raw disjoint scale 尝试 fail-closed，因为旧 raw-slice 设计下只得到 72 条 successful/evaluable records。当前修复是显式 success-quota sampling，并公开 aggregate yield/exclusion 计数。现在不声明 BEA-5 scale result。
6. **自动化 E/S 校准在推进，但不声明 human calibration。** D5-A0/A1/A2 提供 automated/proxy 特征和 heldout 验证证据；它们不等于 human-calibrated E/S。

## 2. 已建立与未建立的边界

| 方向 | 已建立 | 未建立 |
|---|---|---|
| 外部检索 benchmark | ContextBench 和 RepoQA 的 smoke/matrix/scale run 可在 CI 中执行，并输出 aggregate-only artifact。 | 没有 leaderboard 或泛化 benchmark performance claim。 |
| BEA 算法 | BEA policy 能在真实外部 benchmark 数据上运行，并保留私有 SCORE trace。BEA v0.3 证据 mixed。 | 没有 winner/default/promotion claim。 |
| Live-provider downstream 行为 | Context pack 在 bounded synthetic coding-agent tasks 上强于 sparse prompt。B16-J 隔离出了 target+support conjunction 信号。 | 没有 real-user downstream value proof，也没有 BEA-over-BM25 downstream advantage。 |
| 自动化校准 | 已有 automated/proxy calibration artifact 与 heldout feature check。 | 没有 human-calibrated E/S claim。 |
| 隐私与 artifact 纪律 | 公开 artifact aggregate-only；私有 SCORE/event trace 保留在 `/tmp` 或 ignored path。 | 不公开 raw prompt、response、path、snippet、provider payload、gold label 或 per-record rows。 |

## 3. BEA 结论

### 3.1 BEA-0 与 BEA-1

BEA-0 建立了真实运行模式：外部 benchmark/retrieval run、确定性 BEA policy、私有 SCORE JSONL、records-only 公开 artifact。

BEA-1 机制消融显示：BEA v0 没有超过 same-budget BM25/agreement controls，但超过 seeded random。这说明机制不是随机少读上下文，但也还没有强过同预算 lexical controls。

### 3.2 BEA-2 与 BEA-3

BEA-2 引入 diversity/risk scoring，在 bounded slice 上提升 file recall、MRR 和 success rate，但损失 span_f0.5 与 latency。

BEA-3 加入 anchor/span/latency-aware scoring。固定 CI run `27942492278` 中，v0.3 与 v0.2 在 file/MRR/success 上基本打平，只带来极小 span 与 quality-per-latency 改善。这是弱/mixed evidence。

### 3.3 BEA-4

BEA-4 冻结 BEA v0.3 并运行更大的外部 scale smoke。有效结果是 fixed CI run `27957586271`；早期 run `27955873768` 因公开 `delta_records` 形状有重复而被 supersede。

BEA-4 得到 120 条成功记录与 840 条私有 SCORE row。它证明 v0.3 能在更大规模、required RRF 与 unique public record table 约束下运行，但结果仍是 mixed。这是稳健性证据，不是默认策略决策。

### 3.4 BEA-5

BEA-5 仍在进行中。三个 full CI attempt 在 result writeback 前 fail-closed：

- `27962009344`：只有 72 条成功记录，且存在 RRF-missing 分类问题。
- `27964243698`：仍只有 72 条成功记录，因为 evaluator hard cap 低于 workflow 请求。
- `27966269054`：RRF-missing 已修，但成功记录仍为 72，低于 120-record scale gate。

当前设计改为对更大的 disjoint raw scan 做显式 success-quota sampling：

- sampling mode：`success_quota`
- raw caps：ContextBench 480，RepoQA 240
- target successful records：120
- benchmark contribution gates：ContextBench >= 40，RepoQA >= 20
- public artifact 必须公开 attempted/success/excluded aggregate counts
- private SCORE rows 仍为 `records_successful × 7`
- private attempt/exclusion rows 保持私有，公开只给 manifest count

除非 quota CI 通过，否则没有 BEA-5 scale 结论。

## 4. B16 downstream/context-pack 结论

### 4.1 B16-F

B16-F 在 live-provider paired smoke (`27945253824`) 中比较 sparse、same-budget BM25 context pack 和 BEA v0.3 context pack。Context pack 明显强于 sparse，但 BEA 与 BM25 打平。

结论：context 有帮助；BEA selection superiority 未显示。

### 4.2 B16-G 与 B16-H

B16-G 与 B16-H 发现 support-only 可以解决全部任务。B16-H 去掉 target-file-only action 约束后，support-only 仍 8/8。这说明 synthetic support cue 本身过于 decisive。

结论：这些 run 主要诊断任务/cue 设计问题，不是真正的 target+support 机制证明。

### 4.3 B16-I

B16-I 尝试构造 non-decisive support cue，但 support-only 仍然 8/8。设计意图失败。

结论：support cue 仍泄露了足够解题信息。

### 4.4 B16-J

B16-J 使用 role-neutral candidate filenames，并加入 full-prompt leakage self-tests。CI run `27953321504` 首次观察到预期 bounded conjunction pattern：

- target+support：8/8
- support-only：2/8
- target-only：0/8
- conjunction-required count：6/8

结论：去掉 filename/role 泄漏和过强 support 文本后，live-provider smoke 支持 target+support conjunction 机制。但这仍是 bounded synthetic evidence，不是 real-user downstream value proof。

## 5. 外部 benchmark 与 utility 结论

C5 与 F1 阶段证明项目可以在 CI 中运行真实外部 retrieval/utility smoke：

- ContextBench 与 RepoQA 检索 matrix/scale 阶段输出 aggregate retrieval metrics。
- F1-C 与 F1-D 将 retrieval-derived utility 扩展到跨 benchmark 与 bootstrap robustness。
- 这些阶段支持实证评估基础设施与 bounded findings。

它们不构成 leaderboard performance 或 default-policy readiness。

## 6. D5-A 自动化校准结论

D5-A 不再被缺少人工 label 全局阻塞。只要 claim 明确，自动化路径有效。

- D5-A0：automated E/S calibration smoke。
- D5-A1：从已提交 empirical artifacts 做确定性特征提取。
- D5-A2：在 ContextBench rows 21–40 与 RepoQA needles 11–20 上做 heldout validation。

当前 claim：存在 automated/proxy calibration evidence。不声明 human-calibrated E/S。

## 7. 当前 guardrails

以下 flag 仍为 false，除非未来阶段明确验证：

- promotion_ready
- default_should_change
- method_winner_claimed
- benchmark_performance_claimed
- downstream_agent_value_proven
- human_e_s_calibration_claimed
- evidencecore_semantics_changed
- runtime_clean_general_algorithm_claimed
- ood_temporal_supported
- quiver_systems_supported

## 8. 当前下一步

直接下一步是完成 BEA-5 quota-sampling：

1. 完成 quota-sampling implementation 的本地验证。
2. 交 @oracle review。
3. commit quota fix。
4. 跑 full BEA-5 quota CI。
5. 若通过，写回包含 aggregate yield/exclusion counts 的结果。
6. 若失败，诚实记录失败；不弱化 gate。

BEA-5 之后再选择：

- frozen policy 的更广外部稳健性，
- 针对已观察 BEA failure mode 的 v0.4 algorithm change，
- 或只有在测试新机制时才继续 downstream smoke，不能重复 B16-J。

## 9. 一句话结论

OpenLocus 现在已有真实实证管线和 bounded target+support downstream signal，但 BEA 仍是 mixed 且不是默认/winner；当前研究问题是 frozen BEA v0.3 在显式 success-quota external sampling 下是否仍稳健。
