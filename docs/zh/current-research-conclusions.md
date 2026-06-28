# OpenLocus 当前研究结论

日期：2026-06-28

状态：当前研究结论备忘录。本文不是 promotion request，不是默认策略变更申请，也不是 benchmark leaderboard 报告。

范围：覆盖 BEA-v1-P1-3 Agent-Generated Support Label Fill、BEA-v1-P1-2 Private Label Intake Validator、BEA-v1-P1-1 Private Labeling Queue Preparation、BEA-v1-P1-0 Support-Label Validator Dry Run、BEA-v1-P0-9 Readiness Consolidation、BEA-v1-P0-6/7/8 Parallel Trace Surfaces、BEA-v1-P0-5 Support-Link Labeling Harness、BEA-v1-P0-4 Support-Link Input Design、BEA-v1-P0-3 Scheduler Dataset Export、BEA-v1-P0-2 Actionability Matrix Refresh、BEA-v1-P0-1 Trace Gap Audit、BEA-v1-N3 Extra-Depth Merge-Order Design Simulation、BEA-v1-N2 Rank/Pack Actionability Decomposition、BEA-v1-N1 Frozen P4 + Span-Refiner Smoke、BEA-v1-P4L Locked Non-Python P4 Scheduler Validation、BEA-v1-P1 可行动性审计、BEA-FD1/FD2-A/FD2-A1、BEA-5 固定协议 success-quota No-Go / near-miss、B16-F 至 B16-J live-provider atom ablation、C5 外部 benchmark 检索 smoke、F1 utility smoke，以及 D5-A 自动化校准特征提取/heldout 验证。

## 0. 阅读规则

本文是当前结论，不是完整流水账。

- 完整时间线：[`research-log.md`](research-log.md)
- 长版总结：[`research-summary.md`](research-summary.md)
- 详细阶段文档：见 [`../current-research-conclusions.md`](../current-research-conclusions.md)

根目录 `docs/current-research-conclusions.md` 只作为双语索引入口；不要在里面写状态正文。

## 1. 当前一句话判断

OpenLocus 已经从 control-plane 脚手架进入真实实证阶段：现在有外部 benchmark run、live-provider coding-agent run、私有 per-record SCORE/event trace，以及在 license 与安全边界允许时公开的 scanner-validated sanitized analysis artifacts。

当前最可信的结论必须保守表述：

1. **Context pack 对 live coding-agent 有帮助。** B16-F 中 sparse control solve/test 为 0.25，而 same-budget BM25 与 BEA v0.3 context pack 均为 1.0。
2. **BEA 尚未在 downstream 上超过 same-budget BM25。** B16-F 中 BEA v0.3 与 same-budget BM25 在 solve/test 上打平，且 BEA 需要更多 token/latency。
3. **Support atom 很重要，但必须去掉混杂后才看清。** B16-G/H/I 里的 support-only 足够，是因为 support cue 过强。B16-J 去掉 role-bearing filename 泄漏后，才观察到 bounded target+support conjunction：target+support 8/8，support-only 2/8，target-only 0/8。
4. **BEA v0.3 是 mixed，不是 winner。** BEA-2 提升 file/MRR/success 但损失 span/latency；BEA-3 与 v0.2 基本打平，只带来极小 span/quality-per-latency 信号；BEA-4 在 120 成功记录上仍是 mixed。
5. **BEA-5 已作为固定协议 No-Go / near-miss 完成。** 最终固定协议 CI run `28003522632` 以 119/120 successful records fail-closed。本地 exact rerun 复现 artifact：186 attempted、119 successful、67 excluded、ContextBench 82、RepoQA 37、private SCORE rows 833。这是 failure decomposition 输入，不是 BEA-5 pass。
6. **BEA v1 已切到 actionability-aware 主线，但 v1-A/P5 selector 仍未获授权。** BEA-FD2-A1 证明 latency loss 在 candidate-selection 层不可行动；BEA-v1-P1 发现 `gold_file_absent` 的 selector-only lower-bound recoverability 仅为 1/119；BEA-v1-P2/P3/P4 显示 retrieval-action scheduling 在同一 119-record frame 上可在成本 gate 下改善 reach；BEA-v1-P4H/P4I/P4J/P4K 将不相交分母问题解析为 locked 272-record non-Python reservoir；BEA-v1-P4L 随后在该 locked denominator 上验证 frozen P4 scheduler；BEA-v1-N1 进一步发现 span-only repair 当前被 rank 阻塞（`D1_total=40`，`D1_top10_actionable=0`，`D1_rank_blocked=40`）；BEA-v1-N2 将这 40 条 rank-blocked records 全部归因为 extra-depth append/merge-order blocked；BEA-v1-N3 发现简单 merge-order designs 不足；BEA-v1-P0-1 审计 trace gaps；BEA-v1-P0-2 在不修改 P1 causal cell classes 的前提下刷新 actionability matrix；BEA-v1-P0-3 导出 scheduler/action-cost dataset contract；BEA-v1-P0-4 设计 support-link labeling input contract；BEA-v1-P1-2 基于 P1-1 queue 验证 private label intake contract；BEA-v1-P1-3 用 P1-2-valid agent-generated private proxy labels 填充该 queue，但这些不是 human labels、不是 support utility evidence，也不是 mechanism evidence。
7. **自动化 E/S 校准在推进，但不声明 human calibration。** D5-A0/A1/A2 提供 automated/proxy 特征和 heldout 验证证据；它们不等于 human-calibrated E/S。

## 2. 已建立与未建立的边界

| 方向 | 已建立 | 未建立 |
|---|---|---|
| 外部检索 benchmark | ContextBench 和 RepoQA 的 smoke/matrix/scale run 可在 CI 中执行，并输出 aggregate-only artifact。 | 没有 leaderboard 或泛化 benchmark performance claim。 |
| BEA 算法 | BEA policy 能在真实外部 benchmark 数据上运行，并保留私有 SCORE trace。BEA v0.3 证据 mixed。 | 没有 winner/default/promotion claim。 |
| BEA v1 可行动性 | FD1 failure categories 已映射到 action layers；FD1 private replay 支持诚实 file-selector lower bound；P2/P3/P4 显示 retrieval-action scheduling 在同一 frame 上可在成本 gate 下改善 reach；P4J/P4K 锁定 272-record non-Python reservoir；P4L 在该 locked denominator 上验证 frozen P4 retrieval-action scheduler；N1 证明 span-only refiner 分母被 top-10 之外的 rank/pack 层阻塞；N2 将 rank/pack 机制定位为 extra-depth append/merge-order blocked；N3 显示简单 merge-order designs 不足；P0-1 将下一步 trace gaps 显式化；P0-2 将这些 gaps 映射到 P1 的 72-cell actionability matrix；P0-3 导出 aggregate scheduler/action-cost contract 与 optional private-row schema；P0-4 定义 support-link labeling input contract。 | BEA-v1-A selector、P5 selector/reranker、rank policy implementation、naive broad retrieval expansion、runtime/default promotion、method-winner 声明与 selector/reranker execution 均未由 P4L/N1/N2/N3/P0-1/P0-2/P0-3/P0-4 授权。 |
| Live-provider downstream 行为 | Context pack 在 bounded synthetic coding-agent tasks 上强于 sparse prompt。B16-J 隔离出了 target+support conjunction 信号。 | 没有 real-user downstream value proof，也没有 BEA-over-BM25 downstream advantage。 |
| 自动化校准 | 已有 automated/proxy calibration artifact 与 heldout feature check。 | 没有 human-calibrated E/S claim。 |
| 隐私与 artifact 纪律 | artifact 不再默认 aggregate-only；机制分析与 actionability 阶段应在 license 与安全边界允许时公开经过 scanner 验证、可供深度研究 agent 复盘的 sanitized per-record analysis records。字段可包括匿名 record id、benchmark/language/source bucket、arm name、action/state features、hit/miss boolean、rank 或 rank bucket、latency/pool/action-cost bucket、disagreement category、risk class 与 trace-gap/actionability 字段。外部数据集或 provider run 若禁止行级再分发，仍可退回 aggregate-only。私有 SCORE/event trace 保留在 `/tmp` 或 ignored path。 | 不公开 raw prompt、response、snippet、provider payload、secret/provider key/API key、未净化 private rows，或 source-linkable private data。 |

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

BEA-5 已作为严格固定协议 No-Go / near-miss 完成。最终协议前的 earlier attempts 均 fail-closed：

- `27962009344`：只有 72 条成功记录，且存在 RRF-missing 分类问题。
- `27964243698`：仍只有 72 条成功记录，因为 evaluator hard cap 低于 workflow 请求。
- `27966269054`：RRF-missing 已修，但成功记录仍为 72，低于 120-record scale gate。
- `27984961904`：fixed-tail success-quota 仍只有 72/120。
- `28003522632`：fixed-protocol recovery scan 得到 119/120，并 fail-closed。

最终协议使用显式 success-quota sampling，扫描排除 BEA-2/3/4 窗口后的全可用 Python frame：

- sampling mode：`success_quota`
- raw caps：ContextBench 480，RepoQA 240
- target successful records：120
- benchmark contribution gates：ContextBench >= 40，RepoQA >= 20
- public artifact 必须公开 attempted/success/excluded aggregate counts
- private SCORE rows 仍为 `records_successful × 7`
- private attempt/exclusion rows 保持私有，公开只给 manifest count

最终 artifact summary：`status=partial`、`quota_reached=false`、`records_successful=119`、`records_attempted_total=186`、`records_excluded=67`、`contextbench_successful=82`、`repoqa_successful=37`、`private_score_manifest.record_count=833`、`private_attempt_manifest.record_count=186`、`rrf_required_but_missing=0`、`forbidden_scan.status=pass`。

结论：BEA-5 没有通过严格 120-record gate。119-record near-miss artifact 应进入 BEA-4/5 failure decomposition；不要继续改 sampling，也不要做 v0.31 权重微调。

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

BEA-v0.4-P1 集合角色代理冒烟已完成为有效 P1 No-Go / 弱负向结果。Manual CI run `28017063082` 通过 fail-closed，成功记录 38 条（ContextBench 20、RepoQA 18），但 status 为 `no_go_proxy_unavailable`：target_proxy_available_rate=0.0，setwise_selection_diff_rate_vs_v03=0.105263（低于 0.25）。质量没有灾难性退化，但 v0.4-P1 没有优于 v0.3。参见 `docs/zh/bea-v04-p1-setwise-role-proxy-smoke.md`。

BEA-v0.4-P2 target-role proxy 修复冒烟也已完成为有效 No-Go。Manual CI run `28020331024` 通过 fail-closed，成功记录 38 条。P2 将 target_proxy_available_rate 从 0.0 修到 1.0，但 support_proxy_available_rate 降为 0.0，P2-vs-P1 selection difference 为 0.0，P2-vs-v0.3 selection difference 仍为 0.105263（低于 0.25）。质量安全通过，但 P2 不支持进入完整 v0.4 矩阵。参见 `docs/zh/bea-v04-p2-target-role-proxy-repair-smoke.md`。

BEA-v0.4-P3 support/complementarity proxy 修复冒烟已完成为最终有界 role-proxy No-Go。Manual CI run `28022595796` 通过 fail-closed，成功记录 38 条，status 为 `no_go_support_proxy_degenerate`：P3 让 target/support/pair availability 与 selection 全部达到 1.0，并实质改变 selection（vs v0.3 diff=0.5），但 support 过宽（平均 18.289474 个 support candidates/record），且质量相对 v0.3 退化（file_recall@10 -0.052632，MRR -0.155263）。这触发 role-proxy stop rule：不要运行 legacy role-proxy P4/P5，不要从 role-proxy 设计进入完整 v0.4 矩阵，也不要调 v0.31/v0.32。参见 `docs/zh/bea-v04-p3-support-complementarity-repair-smoke.md`。

BEA-FD1 failure decomposition 已完成。Manual CI run `28011901294` 精确重放 BEA-4 和 BEA-5，分解 239 条成功记录，写入 86040 条私有 decomposition rows，并发布 records-only 聚合表。

BEA-FD2-A 直接 FD1-objective setwise acquisition 冒烟已完成为 bounded No-Go。Manual CI run `28025382422` 通过 fail-closed，成功记录 38 条，status 为 `no_go_no_fd1_loss_reduction`：FD1-weighted treatment 强烈改变 selection（相对 v0.3 diff=0.710526），但 composite FD1 loss 增加（0.756181 vs v0.3 0.397802、coverage-only 0.748783），且 file_recall@10/MRR 相对 v0.3 退化。不要从这个 objective 进入 FD2-B。参见 `docs/zh/bea-fd2a-direct-fd1-objective-setwise-smoke.md`。

BEA-FD2-A1 failure attribution replay 已完成。Manual CI run `28027342996` 重放 FD2-A 并归因 38/38 条退化记录。主导机制是 `latency_category_non_actionable_or_dominating`，覆盖 38/38 条记录；候选可用性不是限制（`candidate_availability_limit=0/38`，38/38 记录都有更好候选）。参见 `docs/zh/bea-fd2a1-failure-attribution-replay.md`。

BEA-v1-P1 Actionability Audit 已完成。Manual CI run `28076434237` 重新生成并验证 FD1 private decomposition（86040 行、239 个 composite record groups），公开 status 为 `no_go_retrieval_availability_limit`。审计将全部 12 个 FD1 categories 映射到 6 个 action layers，并从 private replay 计算 file-selector ceiling：`gold_file_absent` denominator=119，lower-bound recoverable count=1，lower-bound rate=0.004184，unrecoverable candidate-unavailable lower-bound count=118，retrieval-availability rate=0.991597。不要基于这份 evidence 启动 BEA-v1-A coverage-preserving selector。

BEA-v1-P2 Candidate Availability / Retrieval Reach Smoke 已完成。Manual CI run `28093864524` 重建 FD1 private replay，并在 119 条 file-miss 分母上运行 4 个 retrieval-reach arms。状态为 `no_go_retrieval_reach_latency_or_pool_cost`：runtime-clean expansion 能找回额外文件，但 broad expansion 成本过高。Baseline 达到 32/119；depth-only 达到 59/119（新增 27，lift 0.226891，pool 3.41×，latency 1.18×）；query-anchor 达到 60/119（新增 28）但成本越界；combined depth+query 达到 81/119（新增 49，lift 0.411765），但违反 pool/latency safety（pool 10.13×，latency 3.89×）。

下一步不再修 proxy、不再做直接 aggregate-FD1-loss weighting，也不再诊断 FD2-A、做 selector-only v1-A 或 naive broad retrieval expansion。FD2-A1 已解释 latency-objective failure；v1-P1 显示 selector-only file coverage 缺少足够依据；v1-P2 显示 candidate availability 可以改善但必须约束 retrieval expansion；BEA-v1-P3 显示下一瓶颈是 retrieval-action latency，而不是 candidate relevance scoring。

BEA-v1-P4 Latency-Aware Retrieval Action Scheduler Smoke 已完成。Manual CI run `28118888584` 在重新生成 FD1 private replay 后，通过 fail-closed，在 119 条 file-miss 分母上运行 4 个固定 arms。状态为 `bea_v1_p4_latency_aware_retrieval_scheduler_pass`：P4 达到 56/119（新增 24），保留 P2 depth-only 增益的 >=75%，pool 2.056×，latency 1.750×，比 P3 latency 低 19.38%，hard-cap violations 为 0，并在 119/119 条记录上减少 action。这验证 retrieval-action scheduling 是 runtime-clean candidate-availability lever，但不是 default-policy/method-winner/runtime-promotion 声明；selector relevance 仍未解决（mean first-gold rank 25.625，48 条记录超出 budget）。参见 `docs/zh/bea-v1-p4-latency-aware-retrieval-scheduler-smoke.md`。

BEA-v1-P4H Disjoint Scheduler Validation 已完成为 No-Go。Manual CI run `28132121958` 在 full-frame 不相交扫描修复 `0dfeb27` 后通过 fail-closed，但 status 为 `no_go_p4h_insufficient_denominator`：精确 BEA-4/5 raw-key 排除移除了 239 条 prior records，扫描取到 266 条 ContextBench 和 100 条 RepoQA rows，尝试 127 条非 prior candidate rows，只找到 73 条 baseline file-miss heldout records（ContextBench 61，RepoQA 12），低于固定 80-record gate。Scheduler arms 未执行（`retrieval_policy_executed=false`，`private_scheduler_rows=0`）。这不推翻 P4 same-frame pass，但意味着 P4 尚未在不相交 heldout 分母上验证，也不授权 P5 selector/reranker、BEA-v1-A 或 runtime promotion。参见 `docs/zh/bea-v1-p4h-disjoint-scheduler-validation.md`。

BEA-v1-P4I Disjoint Denominator Reservoir Audit 已完成为 No-Go。Manual CI run `28137455572` 通过 fail-closed，但 status 为 `no_go_disjoint_denominator_reservoir_insufficient`：审计取到 366 条 raw rows，从 FD1 中精确排除 239 条 BEA-4/5 prior raw keys，尝试 127 条非 prior rows，观察到 54 条 baseline-reached rows，只找到 73 条 FD1-excluded file-miss reservoir records。`reservoir_upper_bound_count=73`，`qualified_denominator_reservoir_count=0`，`p4h_overlap_resolved=false`。这确认 P4H blocker 是当前受支持 ContextBench/RepoQA Python frame 的 source/reservoir limitation，不只是 fixed-tail sampling。不要从 P4I 运行 frozen P4H rerun、P5 selector/reranker、BEA-v1-A 或 broad retrieval expansion。参见 `docs/zh/bea-v1-p4i-disjoint-denominator-reservoir-audit.md`。

BEA-v1-P4J Cross-Source File-Miss Reservoir Unlock Audit 已完成为 unqualified No-Go。Manual CI run `28146407493` 在 diagnostic patch `18126f4` 后通过 fail-closed，但 status 为 `no_go_cross_source_reservoir_unqualified`：P4J 找到较大的 cross-source FD1-excluded upper-bound reservoir（`denominator_count=333`，`reservoir_upper_bound_count=333`，`cross_source_non_python_reservoir_count=272`，`cross_source_python_reservoir_count=61`），共取到 780 rows、尝试 618 rows。但 `qualified_cross_source_reservoir_count=0` 且 `p4h_p4i_overlap_resolved=false`，因此 333 条不是 locked all-prior-disjoint denominator。P4J 证明 source story 不止 Python frame，但仍不授权 locked-P4 validation、frozen P4 rerun、P5 selector/reranker、BEA-v1-A、runtime promotion 或 broad retrieval expansion。参见 `docs/zh/bea-v1-p4j-cross-source-reservoir-unlock-audit.md`。

BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit 已完成为 design-ready only。Manual CI run `28151914531` 通过 fail-closed，status 为 `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`：P4K 重建 P4H `73/73`、P4I `73/73`、P4J `333/333`（61 Python + 272 non-Python），发现与 P4H/P4I 的 overlap 为 61，并锁定 post-overlap cross-source reservoir `272/80`，全部来自 non-Python。`locked_p4_validation_design_authorized=true` 只出现在 `stop_go_records`；`scheduler_validation_authorized=false`、`locked_p4_validation_executed=false`、`frozen_p4_rerun_authorized=false`、`p5_authorized=false`、`v1_a_authorized=false`。P4K 本身解决了 P4J blocker，并且只授权设计后续 locked-denominator P4 validation phase；下面单独的 P4L phase 执行了该 validation。参见 `docs/zh/bea-v1-p4k-exact-overlap-resolution-locked-reservoir-audit.md`。

BEA-v1-P4L Locked Non-Python P4 Scheduler Validation 已完成为 scheduler-validation pass。Manual CI run `28184096209` 在 heartbeat workflow patch `e98839b` 和 P4-treatment hard-cap gate fix `6034b3d` 后通过 fail-closed。P4L 精确重建 locked denominator（`333/61/272`，non-Python locked denominator `272`），执行四个 frozen scheduler arms，并只在 `/tmp` 写出 1088 条 private arm-outcome rows。Baseline reach 为 `0/272`，P2 depth-only reference 为 `55/272`，P3 constrained reference 为 `55/272`，frozen P4 latency-aware scheduler 为 `52/272`。P4 保留 P2 gain 的 `0.945455`，`p4_vs_p3_latency_ratio=0.656763`，`p4_latency_reduction_vs_p3=0.343237`，`p4_pool_growth_ratio=2.176782`，且 P4-treatment hard-cap violations 为 0。这验证 frozen P4 retrieval-action scheduler 在 locked non-Python denominator 上成立，但仍不授权 P5、BEA-v1-A selector/reranker work、runtime/default promotion、method-winner 声明、broad retrieval expansion 或 frozen P4 rerun。参见 `docs/zh/bea-v1-p4l-locked-non-python-scheduler-validation.md`。

BEA-v1-N1 Frozen P4 + Span-Refiner Smoke 已完成为 rank-blocked No-Go。Manual CI run `28245155237` 在 checkpoint `0ddc2e8` 上通过 fail-closed，status 为 `no_go_n1_inadequate_top10_actionable_denominator`。N1 重放 FD1 private decomposition，重建 frozen P4L/P4K denominator，并在 locked 272-record non-Python denominator 上通过 D0 scheduler preservation：baseline `0`，P2 `55`，P3 `55`，P4 `52`，P4 treatment hard-cap `0`。D1 total / pool span-opportunity 充分，为 `40`，但 D1 top-10 actionable 为 `0`，D1 rank-blocked 为 `40`。全文件同文件 refiner 在局部 gold-file span 上改善 8/40、退化 0/40，但 40 条全部在 top-10 之外；因为 N1 禁止 reorder，canonical `SpanF0.5@10` 不能给 span refinement 记功。这把下一步 BEA-v1 问题转向 rank/pack actionability，而不是 span-only refinement、P5、BEA-v1-A 或 runtime promotion。参见 `docs/zh/bea-v1-n1-frozen-p4-span-refiner-smoke.md`。

BEA-v1-N2 Rank/Pack Actionability Decomposition 已完成为有界 decomposition pass。实证来源是 CI `28272769423`（checkpoint `7c90213`）；提交的公开 artifact 只对 closed N1 artifact 中非 gating 的 D0 latency 展示字段做了本地 records-only 修正，代码修复为 `a5b519b`。N2 精确重建 closed N1 rank-blocked denominator（`D2=40`），分类全部 40 条 records，发现 first gold-file rank bucket 为 `rank_21_50=40/40`，top-20 recovery `0/40`，top-50/top-100 recovery `40/40`，unique-file top-10 recovery `0/40`，evidence materializable `40/40`，hard-cap violations `0`，primary blocker 为 `extra_depth_append_blocked=40/40`。这只授权 extra-depth merge-order **design**，不授权 implementation、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或 frozen P4 rerun。参见 `docs/zh/bea-v1-n2-rank-pack-actionability-decomposition.md`。

BEA-v1-N3 Extra-Depth Merge-Order Design Simulation 已完成为 inconclusive design result。Manual CI `28278662782` 精确重建 D3（`40/40`）并通过 scanner，但最佳简单 merge-order arms 只将 `10/40` 移入 top-10（`0.25 < 0.50` pass gate）。它不授权 implementation、新 retrieval、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion 或 downstream-value 声明。参见 `docs/zh/bea-v1-n3-extra-depth-merge-order-design-simulation.md`。

BEA-v1-P0-1 Trace Gap Audit 已完成为 scanner-validated trace-surface phase。该审计读取已提交的 FD1、P1、FD2-A1、P4L、N2 与 N3 artifacts，并发布 sanitized per-gap rows。状态为 `trace_gap_audit_pass`：rank/pack 与 merge-order 复盘已有 sanitized rows，但下一步 BEA-v1 机制工作仍需要 action-cost scheduler export、support-link labels、same-file redundancy trace、risk-penalty trace 与 ordered-prefix stop trace。它只授权 actionability-matrix refresh 与 scheduler/support trace dataset 工作；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-trace-gap-audit.md`。

BEA-v1-P0-2 Actionability Matrix Refresh 已完成为基于 P1 matrix 与 P0-1 trace gaps 的 records-only join。状态为 `actionability_matrix_refresh_pass`：刷新 72 个 cells，self-test `6/6`，scanner 通过，且 P1 causal cell classes 未改变。Readiness summary 为 `ready_sanitized_trace=10`、`blocked_private_export=11`、`blocked_missing_label=18`、`blocked_missing_trace=12`、`blocked_aggregate_only=3`、`not_applicable_by_layer=18`。它只授权 scheduler dataset export、support-link input design、redundancy/risk/stop trace preservation；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p0-2-actionability-matrix-refresh.md`。

BEA-v1-P0-3 Scheduler Dataset Export 已完成为 contract export。状态为 `scheduler_dataset_export_contract_pass`：self-test `8/8`，scanner 通过，4 条 sanitized aggregate scheduler arm rows，12 条 sanitized subgroup denominator rows，并包含 P0-2 action-cost join rows。Full private arm-row export 仍为 optional，本轮未满足，因为历史 P4L private JSONL 是在之前环境生成的，本机项目内 private directory 不存在该文件。它只授权在 `.openlocus/research-private/` 下恢复/重跑 private arm rows 或 support-link input design；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p0-3-scheduler-dataset-export.md`。

BEA-v1-P0-4 Support-Link Input Design 已完成为 labeling-contract phase。状态为 `support_link_input_design_pass`：self-test `8/8`，scanner 通过，18 条 sanitized support-link design records，6 个 label contract fields。它将 P0-1 的 `support_link_trace` gaps 与 P0-2 的 `blocked_missing_label` cells join 起来，但所有 target/support hit states 仍是 `unknown_not_labeled`；没有执行 counterfactual，也没有声明 support marginal utility。它只授权 support-link labeling input work；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明或 support counterfactual execution。参见 `docs/zh/bea-v1-p0-4-support-link-input-design.md`。

BEA-v1-P0-5 Support-Link Labeling Harness 已完成为 private labeling harness contract。状态为 `support_link_labeling_harness_contract_pass`：self-test `9/9`，scanner 通过，18 条 harness records，并在 ignored 的项目内 research-private directory 下生成 18 条 private template rows。Private labels 尚未提供，因此 full private-label validation gate 仍是 optional false。它只授权 private support labeling 或 label validation；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明、support counterfactual execution 或 support marginal-utility 声明。参见 `docs/zh/bea-v1-p0-5-support-link-labeling-harness.md`。

BEA-v1-P0-6/7/8 Parallel Trace Surfaces 已完成为 contract exports。P0-6 状态为 `same_file_redundancy_trace_surface_contract_pass`，P0-7 状态为 `risk_penalty_trace_surface_contract_pass`，P0-8 状态为 `ordered_prefix_stop_trace_surface_contract_pass`；self-test `5/5`，三个 reports scanner 均通过，每个 trace surface 6 条 contract records。这些 phase 定义 same-file redundancy、risk-penalty removal 与 ordered-prefix stop decisions 的 schemas，但 private trace rows 尚未填充。它们只授权 trace-surface review 或 private trace validation；不授权 policy tuning、counterfactual execution、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p0-6-7-8-parallel-trace-surfaces.md`。

BEA-v1-P0-9 Readiness Consolidation 已完成为 next-experiment gate。状态为 `readiness_consolidation_pass_labeling_authorized_only`：self-test `5/5`，scanner 通过，检查 8 个 P0 inputs。它确认所有 P0 artifacts 都能加载并通过 scanner，但后段 surfaces 仍是 contract-only，而不是已填充的 mechanism evidence。它只授权 private labeling 或 private trace validation；不授权 support counterfactual execution、trace counterfactuals、policy tuning、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p0-9-readiness-consolidation.md`。

BEA-v1-P1-0 Support-Label Validator Dry Run 已完成。状态为 `support_label_validator_dry_run_pass`：self-test `6/6`，scanner 通过，并通过 P0-5 harness 验证 18 条 synthetic private labels。Synthetic fixture 只写入 `.openlocus/research-private/`，并明确不是真实 label data。P1-0 授权使用已验证 schema 进行真实 private support labeling，但不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p1-0-support-label-validator-dry-run.md`。

BEA-v1-P1-1 Private Labeling Queue Preparation 已完成。状态为 `private_labeling_queue_preparation_pass`：self-test `7/7`，scanner 通过，并在 `.openlocus/research-private/` 下生成 18 条 project-private queue records。Public artifact 只暴露 sanitized queue buckets 与 manifests。P1-1 授权基于生成 queue 进行真实 private labeling，但不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p1-1-private-labeling-queue-preparation.md`。

BEA-v1-P1-2 Private Label Intake Validator 已完成。状态为 `private_label_intake_validator_contract_pass`：self-test `8/8`，scanner 通过，valid private queue records `18`，valid real labels `0`。它验证 queue/intake contract，证明 P1-1 private queue 可读取并 join，但本阶段未供应 labels。它只授权 private label intake validation；不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p1-2-private-label-intake-validator.md`。

BEA-v1-P1-3 Agent-Generated Support Label Fill 已完成。状态为 `agent_generated_support_label_fill_pass`：self-test `10/10`，scanner 通过，private queue rows read `18`，agent-generated private labels written `18`，P0-5-compatible labels `18`，P1-2 intake-valid labels `18`，label errors `0`。这些是 automated queue/design-field proxy labels，且 `target_hit_bucket=support_hit_bucket=unknown_not_labeled`；它们不是 human labels，不是 human-calibrated E/S，不是 support utility evidence，也不是 mechanism evidence。它们不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。参见 `docs/zh/bea-v1-p1-3-agent-generated-support-label-fill.md`。

不要运行 B16-K、legacy role-proxy P4/P5、从失败 FD2-A objective 继续 FD2-B、v0.31/v0.32 权重微调、D5-A readiness 扩展、QuIVer/dense/graph quality experiments、另一个 BEA scale smoke、BEA-v1-A selector-only implementation、从 P4L/N1/N2/N3 进入 P5 selector/reranker、runtime/default promotion、method-winner 声明、frozen P4 rerun 或 unconstrained broad retrieval expansion。

## 9. 一句话结论

OpenLocus 现在已有真实实证管线和 bounded target+support downstream signal，但 BEA 仍是 mixed 且不是默认/winner；BEA-5 固定 quota 少 1 条成功记录，BEA-FD1 已完成 BEA-4/5 failure decomposition，P1/P2/P3 关闭了 role-proxy 路线，FD2-A/FD2-A1 关闭了直接 FD1-loss weighting，BEA-v1-P1 拒绝 selector-only v1-A，P2/P3/P4 显示 retrieval-action scheduling 能在成本 gate 下改善候选可达性，P4L 在 locked 272-record non-Python denominator 上验证了 frozen P4 scheduler，N1 显示 span-only repair 当前被 top-10 之外的 rank/pack 层阻塞，N2 将该 blocker 定位为 extra-depth append/merge-order design，N3 显示简单 merge-order designs 不足，P0-1 标出 trace gaps，P0-2 将这些 gaps 映射到 72-cell actionability matrix，P0-3 导出 scheduler/action-cost dataset contract，P0-4 定义 support-link labeling input contract，P0-5 构建 private labeling harness，P0-6/7/8 关闭剩余 trace-surface contracts，P0-9 汇总 next-experiment gate，P1-0 验证 synthetic private support-label path，P1-1 准备 real private labeling queue，P1-2 验证 intake，P1-3 用 P1-2-valid automated proxy labels 填充 queue——但不授权 P5、v1-A、implementation、runtime promotion、method-winner 声明、broad retrieval expansion、support counterfactual execution、policy tuning 或 support marginal-utility 声明。
