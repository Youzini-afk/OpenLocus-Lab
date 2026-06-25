# BEA-v1-N1：冻结 P4 + Span-Refiner 冒烟实验

日期：2026-06-25

BEA-v1-N1 是 BEA v1 层级化可行动证据获取（Report 4）的第一个 span 阶段。它只是**检索层 span 冒烟实验**：重新生成/重放 FD1 与冻结 P4L locked denominator，验证文件与调度行为保持不变，私下构造 wrong-span 分母，并测试一个只能在冻结 P4 已选中文件内调整行范围的 post-P4 span refiner。

## 绑定来源上下文

- P4L 来源 checkpoint：`f1bac81`；CI `28184096209`。
- 锁定 non-Python 分母：272。
- 来源 reach：baseline 0，P2 55，P3 55，P4 52。
- P4 retained P2 gain：0.945455。
- P4/P3 latency ratio：0.656763。
- P4 treatment hard-cap violations：0。

Network-enabled N1 是真实 empirical replay，不是手工行输入的 control plane。它在 `/tmp` 下重新生成 FD1 private decomposition，验证 86040 行 / 239 组 FD1 replay 与 manifest hash，重建 P4L locked non-Python denominator，私下重读原始 benchmark frame 以恢复 gold line ranges，使用私有 candidate `path/start_line/end_line` 运行冻结 P4 policy，形成 D1，然后诚实输出 pass/preflight/exploratory/No-Go。若 infrastructure、parser、clone、replay、private-write 或 invariant 检查失败，evaluator 输出 `fail_schema_contract`。保留的手工 private-input CLI 仅用于 debug，不是 network CI 合约。

## 双分母设计

- **D0 调度保持分母** = P4L 锁定 non-Python 272。D0 证明 N1 的 instrumentation/wrapping 保持冻结调度器行为。它**不是** span 成功分母。
- **D1 P4-compatible wrong-span 分母** = 私有记录集合：可重建 gold 行范围、冻结 P4 reach 到 gold 文件、冻结 P4 对 selected/packed evidence 有候选 `start_line`/`end_line`，且 refiner 前 P4 在 gold 文件上的 evidence 与 gold 行范围为零重叠或重叠不足。

D1 充分性：`>=20` 为充分/可进入 pass preflight，`10-19` 为 exploratory，`<10` 为 No-Go。

## Refiner 约束

N1 refiner 只能在 P4 之后运行，并且必须保持文件集合不变。它只能在冻结 P4 已选择/已 reach 的文件内部收窄或扩展行范围。它不得添加、剔除或重排文件；不得改变调度动作；不得使用 gold lines 做 refinement；不得运行 selector/reranker/P5/BEA-v1-A；不得把 latency 放入 candidate relevance。

## 公共 artifact 合约

公共报告只包含聚合指标和经过 scanner 验证的 sanitized per-record analysis rows。公共行只使用匿名本地 ID 和桶化字段：

- `anonymous_local_id`
- `denominator`
- `arm`
- `source_bucket`
- `language_bucket`
- `pre_span_bucket`
- `post_span_bucket`
- `span_delta_bucket`
- `file_reach_preserved`
- `evidencecore_valid`
- `hard_cap_violation`

公共 artifact 禁止包含：raw prompts/responses/snippets/provider payloads、精确 paths/spans、gold labels/lines、raw candidate lists、可识别 task IDs/row IDs/repo names、可链接 content hashes、private paths、未清洗的私有逐记录行。Private manifests 只公开 counts/hash provenance；不会序列化私有 trace 路径。

## 状态词表

- `unavailable_with_reason` — 仅默认无网络；不是 pass/no-go 实证结果。
- `fail_schema_contract` — instrumentation、parser、replay、private-write 或 invariant 失败时 fail-closed。
- `fail_forbidden_scan` — 公共 artifact privacy scanner 阻止写出。
- `no_go_n1_locked_denominator_unavailable` — live P4L/P4K locked-denominator reconstruction 出现漂移，因此 N1 不运行 span 主张。
- `n1_preflight_pass_wrong_span_denominator_adequate` — D0 保持且 D1 充分，但 refiner 改善门槛尚未建立正向 span 结果。
- `n1_exploratory_insufficient_power` — D0 保持但 D1 只有 10-19。
- `no_go_n1_inadequate_wrong_span_denominator` — D0 保持但 D1 低于 10。
- `bea_v1_n1_frozen_p4_span_refiner_pass` — D0 保持、D1 充分、文件保持 invariant 通过，且 refiner 后 span 指标改善。

## 指标

公共指标表分为两块：

1. `d0_scheduler_preservation_records` — 272 记录分母上的冻结 P4L 调度保持聚合指标。
2. `d1_span_efficacy_records` — D1 wrong-span 分母上的 pre/post 检索 span 指标，使用 `eval/score.py` 的 canonical span metrics。

## 明确非主张

这不是默认策略变更、下游 agent 评估、selector/reranker 结果、P5 结果、BEA-v1-A 结果、method-winner 主张、provider 结果或完整 benchmark 主张。它只是针对 frozen-P4-compatible wrong-span case 的有界检索层 span 冒烟实验。
