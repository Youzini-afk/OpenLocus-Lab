# P50 固定测试集验证 / 反过拟合闸门

- Schema: `p50-fixed-suite-validation-v1`
- 阶段：P50 固定测试集验证 / 反过拟合闸门
- 状态：脚手架
- 自测：可用
- P50 远程调用次数：0
- P50 源码读取：false

## 目的

P50 是一个**评估纪律阶段（evaluation discipline phase）**，而不是策略改进阶段。 它把固定的评测集合作为分析单元，检查该集合是否足够健康、稳定，以作为后续策略工作的反过拟合闸门。

P48 在此闸门建立后只作为**诊断性 request-more-context overlay** 被 carry forward；它不构成 evidence 准入、不改变默认策略，也不证明候选已经完成 Evidence 转化。

## 方法

1. 加载由 P21/P25/P30/P31/P33-B 生成的临时 `p25-policy-records-ephemeral-v1` 记录（或使用确定性自测记录）。
2. 使用与 P46/P47 相同的 `p46.normalize_task()` 例程规范化记录。
3. 计算两个确定性、稳定的哈希：
   - `suite_manifest_hash` 覆盖每个任务的私有标识符和公开元数据。
   - `evaluator_config_hash` 覆盖 schema 版本、K 值、策略/变体名称和评估器设置。
   只公布哈希摘要；原始成分保持私有。
4. 仅报告聚合的集合构成：任务数、仓库数、正例/无金标拆分、公开分桶/风险标签分布和可用性标识。不公布仓库 ID。
5. 比较来自 P46 聚合助手的 `bucket_routed_v0` 和 `admission_v3_h4b` 路由表。
6. carry forward P46 可达性/成本/物化诊断与 P47 跨度几何诊断，并保持其非证据性质。
7. 当 P48 evaluator 可用时，只 carry forward 其聚合 overlay 摘要；P50 质量闸门不把 P48 lane 纳入通过条件。

## 输出约定

- `promotion_ready=false`
- `default_should_change=false`
- `evidencecore_semantics_changed=false`
- `candidate_not_fact=true`
- `remote_calls_by_p50=0`
- `source_reads_attempted_by_p50=false`
- `score_phase_only_metrics=true`
- `aggregate_only_public_artifact=true`
- `p48_variant_availability="available"` 或 `"not_implemented"`，取决于当前环境是否能导入 P48；两者都不表示默认策略变化。

## 质量闸门

仅当以下条件全部满足时，`quality_gate_status="pass"`：

- `real_evaluation` 为 true，
- 至少 6 个任务、覆盖至少 2 个仓库，
- 至少一个正例任务和一个无金标任务，
- 候选池和金标跨度可用，
- 比较的路由策略在选择动作/结果/成本上均无 fallback。

否则报告 `insufficient_fixed_suite`。 这是健康信号，不导致 CI 失败。

## 安全

- P50 不发起远程模型调用。
- P50 不读取源码文件。
- 公开产物只包含按公开分桶、风险标签和策略聚合的计数/比例。
- 不保存 task ID、candidate ID、path、span、gold span、私有 label、route feature、snippet、prompt、response、仓库 ID 或 provider key。
