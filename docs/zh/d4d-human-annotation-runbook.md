# D4d 人工标注 Runbook / Checklist 协议（公开纯协议 artifact）

## 范围与声明边界

D4d 是**人工标注 runbook / checklist 协议**公开 artifact。D4d 在任何 D4e
转换器或 D5 聚合发布候选之前，冻结未来人工标注者应如何标注 D4c 标注包（填写
双评分卡 E/S 槽位）。默认提交的 artifact 是**公开纯协议 runbook**，不是标签
采集，不是数据包构建，不是已填充数据包，不是 D4b bundle，不是转换器运行，也不
是校准。

D4d 桥接关系为：

```text
D3 双评分卡 -> D4c 标注包 -> 人工标注 runbook（D4d）-> D4e 转换器 -> D4b 真值 bundle -> D5 聚合发布候选
```

D4d 通过冻结人工标注 checklist 来为 D4e 做准备：填写哪些槽位、使用哪些评分等级、
哪些来源被禁止、裁决如何进行、哪些发布门必须通过。D4e（包->bundle 转换器）需要
一个已填充数据包契约，且该契约之前需要一份人工标注 runbook/checklist；D4d 提供
该 runbook。

D4d **不**读取私有数据包，**不**读取私有数据包输出，**不**读取私有源记录，**不**
生成或持久化标注包，**不**招募或识别标注者，**不**发出标注者 ID，**不**采集标签，
**不**创建已填充数据包，**不**创建 D4b 真值 bundle，**不**运行包->bundle 转换器，
**不**校验 D4b bundle，**不**计算校准指标，**不**度量标注者间一致性，**不**计算
置信区间，**不**通过任何公开发布门，**不**解锁 D5，**不**声明真 E/S 校准，**不**
执行模型/LLM 标注，**不**允许模型辅助标签，**不**发出私有路径/代码片段，**不**
发出包/任务/仓库 ID 或内容哈希，**不**发出查询/候选文本，且**不**改变运行时行为、
retriever、pack、model、backend、默认策略或 EvidenceCore 语义。

- 声明级别：`human_annotation_runbook_protocol_only`。
- D3 评分卡版本：`d3_true_dual_rubric_label_protocol_v1`。
- D4c 数据包 schema 目标：`d4c_annotation_packet_v1`。
- D4b bundle schema 目标：`d4b_true_label_bundle_v1`。
- 状态：`protocol_ready_no_raters_no_labels_no_packets`；模式
  `public_runbook_protocol_only`；阶段 `D4d`。

D4d 是**eval/诊断专用**。它不是基准测试结果，不是下游 agent 价值声明，不是
runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。

- EvidenceCore 保持为 `path + line range + content_sha + score + why +
  channels`；D4d 不发出任何 EvidenceCore 记录，也不改变其语义。
- D4d 不读取私有数据包，也不采集标签：
  `private_packets_read=false`、
  `private_packet_output_read=false`、
  `private_source_records_read=false`、
  `annotation_packets_generated=false`、
  `annotation_packets_persisted=false`、
  `raters_recruited=false`、`raters_identified=false`、
  `rater_ids_emitted=false`、`labels_collected=false`、
  `filled_packets_created=false`、`private_paths_or_snippets_emitted=false`、
  `packet_ids_emitted=false`、`task_ids_emitted=false`、
  `repo_ids_emitted=false`、`content_sha_emitted=false`、
  `query_or_candidate_text_emitted=false`。
- D4d 不创建 bundle，不运行转换器，不计算指标，不执行模型标注，也不通过发布门：
  `d4b_true_label_bundle_created=false`、
  `d4b_bundle_converter_run=false`、
  `d4b_true_label_bundle_validated=false`、
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_measured=false`、
  `confidence_intervals_computed=false`、
  `model_or_llm_labeling_performed=false`、
  `model_assisted_labels_allowed=false`、
  `true_e_s_calibration_claimed=false`、
  `public_release_gate_passed=false`、`d5_unblocked=false`。

## 核心边界：D4d 是纯协议

- **默认提交的 D4d artifact** 是公开纯协议 runbook。其状态为
  `protocol_ready_no_raters_no_labels_no_packets`。它不读取任何私有数据包，不生成
  任何数据包，不招募/识别任何标注者，不采集任何标签，不创建任何已填充数据包，不
  创建任何 D4b bundle，不运行任何转换器，不计算任何校准，不度量任何一致性/置信
  区间，不执行任何模型/LLM 标注，也不通过任何公开发布门。D5 保持锁定。
- D4d 没有私有模式，没有 `--input`，也不读取私有数据包/源记录。没有可选私有构建器
  （与 D4c 不同）。
- runbook/checklist 内容是纯类别且抽象的：没有数据包示例、代码片段、路径、任务 ID、
  仓库名、标注者 ID/姓名、URL 或私有示例。

### D4d -> D4e -> D4b 关系

D4d 冻结 D4e 将使用的人工标注 runbook/checklist。D4e（包->bundle 转换器，未来）将
已填充的 D4c 数据包（带人工填写的 E/S 槽位）映射为 `d4b_true_label_bundle_v1`。D4d
**不**运行该转换器，**不**创建 bundle，也**不**采集或声明标签。D4d 通过在任意转换
之前冻结人工 checklist 来为 D4e 做准备。

## CLI

```bash
python3 -m py_compile eval/d4d_human_annotation_runbook.py
python3 eval/d4d_human_annotation_runbook.py --self-test
python3 eval/d4d_human_annotation_runbook.py \
    --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json
```

默认模式（唯一模式）：写入已提交的公开纯协议 runbook artifact（若省略 `--out` 则
使用默认输出路径）。

CLI 参数：`--self-test`、`--out`。**没有** `--input`，也**没有**
`--allow-private-source-records`；D4d 是纯协议，从不读取私有数据包或源记录。未知或
类似私有输入的参数会以通用 `invalid arguments` 消息拒绝，不回显私有路径或 basename。

## Runbook / checklist 章节

runbook 内容是纯类别且抽象的。七个必需章节，每个都带有经批准的抽象类别 token
checklist：

1. **前置条件** — 仅 D3 评分卡；D4c 数据包 schema 是数据包输入源；D4b bundle schema
   是输出目标；数据包保持本地/私有；无公开数据包内容；D4d 不采集标签。
2. **标注者设置** — 至少两名独立人工标注者；裁决前独立工作；公开 artifact 中无标注
   者 ID；本地标注者身份映射仅私有；训练仅使用抽象示例。
3. **标注规则** — 仅填写 `e_score`、`s_score`、`bucket`、`citation_valid`、
   `rater_pair_present`、`adjudicated`；D3 E0/E1/E2 与 S0/S1/S2 定义；主要证据要求
   引用有效；依赖支持是结构性/支持性证据，而非直接答案证据；在无效/陈旧/证据不足时
   弃权。
4. **禁止的标注来源** — 无 LLM/模型生成标签；无代理标签作为真值；无基于模型名称的
   规则；无基准私有桶作为运行时策略；无下游价值声明。
5. **本地存储 / 隐私** — 数据包与已填充数据包仅本地；公开 artifact 中无包 ID/任务
   ID/仓库 ID/路径/代码片段/内容哈希/查询/候选文本；本地输出在 `/tmp` 或经批准的私
   有工作区下；无已提交的数据包或标签。
6. **裁决** — 分歧类别仅本地；裁决在独立标签之后进行；公开输出仅在 D5 门通过时才可
   包含聚合分歧计数；公开 artifact 中无分歧示例。
7. **发布门** — 最小总标签数 `N >= 50`；每个公开单元 k-最小 `k >= 5`；要求一致性
   指标；要求置信区间；小单元被抑制/合并；仅聚合公开发布候选；D5 保持锁定直到所有门
   通过。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/d4d_human_annotation_runbook/d4d_human_annotation_runbook_report.json`，
是公开纯协议 runbook artifact。身份/边界字段：

- `schema_version` = `d4d_human_annotation_runbook.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`、
  `d3_rubric_version`、`d4c_packet_schema_target`、`d4b_bundle_schema_target`
- 默认 false 标志（全为 false）：`private_packets_read`、
  `private_packet_output_read`、`private_source_records_read`、
  `annotation_packets_generated`、`annotation_packets_persisted`、
  `raters_recruited`、`raters_identified`、`rater_ids_emitted`、
  `labels_collected`、`filled_packets_created`、
  `d4b_true_label_bundle_created`、`d4b_bundle_converter_run`、
  `d4b_true_label_bundle_validated`、`calibration_metrics_computed`、
  `inter_rater_agreement_measured`、`confidence_intervals_computed`、
  `public_release_gate_passed`、`d5_unblocked`、
  `true_e_s_calibration_claimed`、`model_or_llm_labeling_performed`、
  `model_assisted_labels_allowed`、`private_paths_or_snippets_emitted`、
  `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
  `content_sha_emitted`、`query_or_candidate_text_emitted`。
- 无声明 / 无运行时变更标志（全为 false）：`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`model_calls_changed`、
  `backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 协议 true 标志（仅这些，全为 true）：
  `runbook_protocol_defined`、`checklist_schema_defined`、
  `rater_independence_required`、`d3_rubric_required`、
  `d4c_packet_schema_referenced`、`d4b_bundle_schema_referenced`、
  `local_only_storage_required`、`no_llm_labeling_required`、
  `adjudication_policy_defined`、`disagreement_handling_defined`、
  `min_n_gate_referenced`、`k_min_gate_referenced`、
  `agreement_gate_referenced`、`ci_gate_referenced`、
  `aggregate_only_public_release_required`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。
- `runbook_protocol_contract`：七个章节，带纯类别 checklist；`d3_rubric_version`、
  `d4c_packet_schema_target`、`d4b_bundle_schema_target`。
- `rubric_contract`：`d3_rubric_version`、`e_score_levels=[E0,E1,E2]`、
  `s_score_levels=[S0,S1,S2]`、`bucket_names=[primary_evidence,
  dependency_support, weak_candidates, abstained]`、
  `required_label_slots=[e_score,s_score,bucket,citation_valid,
  rater_pair_present,adjudicated]`。
- `label_slot_contract`：`required_label_slots`（六个槽位）、
  `target_packet_schema=d4c_annotation_packet_v1`、
  `target_bundle_schema=d4b_true_label_bundle_v1`、
  `no_filled_packets_created=true`。
- `release_gate_contract`：`gate_names=[min_total_labels,k_min,
  agreement_metric,confidence_intervals,small_cell_suppression]`、
  `min_total_labels=50`、`k_min=5`、`min_rater_count=2`、
  `agreement_required=true`、`confidence_intervals_required=true`、
  `small_cell_suppression_required=true`、
  `aggregate_only_public_release_required=true`、
  `d5_blocked_until_all_gates_pass=true`、`public_release_gate_passed=false`。
- `prohibited_labeling_sources_contract`：`prohibited_sources`（无
  LLM/模型标签，无代理标签作为真值，无模型名称规则，无基准私有桶作为运行时策略，无下
  游价值声明）、`model_or_llm_labeling_performed=false`、
  `model_assisted_labels_allowed=false`。
- `rater_setup_contract`：`min_rater_count=2`、
  `rater_independence_required=true`、`rater_independence_rules`、
  `local_rater_mapping_private_only=true`、`rater_ids_emitted=false`、
  `raters_recruited=false`、`raters_identified=false`。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写 JSON 前故障关闭）。

## 禁止内容扫描器（公开，故障关闭）

在写入公开 JSON 之前，运行一个严格的禁止输出扫描器，故障关闭。它拒绝禁止的 dict
键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、`start_line`、
`end_line`、`content_sha`、`snippet`、`candidate_text`、`query`、`query_text`、
`prompt`、`response`、`model_output`、`label`、`labels`、`raw_label`、
`annotation_row`、`rater_id`、`annotator_id`、`packet_ref`、`packet_id`、
`private_record_ref`、`candidate_ref`、`label_slots`、`annotation_instructions`、
`e_score`、`s_score`、`bucket`、`provider_payload`、`api_key` 等）在任何位置出现，
并拒绝值模式：任何 URL（无 URL 白名单）、32/40/64 字符十六进制摘要、类密钥字符串、类
路径 `src/foo.rs` 和 `/private/foo.jsonl`、多行字符串、原始 JSON 片段、原始行范围
`12-34` 以及自测 sentinel。

契约容器（`checklist`、`e_score_levels`、`s_score_levels`、`bucket_names`、
`required_label_slots`、`gate_names`、`prohibited_sources`、
`rater_independence_rules`）是**精确字符串白名单**：仅允许经批准的 schema 标识符、
E/S 等级、桶名、标签槽位字段名、门名和经批准的抽象 runbook 类别 token。任意短字符
串（如实现符号或私有文本）即使在契约容器内**也会被拒绝**（无过宽容器豁免）。字段名
在任何位置作为键、在契约外作为值，均被拒绝。

## 自测

- 所有默认 false/true 标志（默认 artifact 不读数据包，无标注者，无标签，无指标，无
  声明；协议标志为 true；诊断标志为 true）。
- artifact 身份字段（`schema_version`、`claim_level`、`status`、`mode`、`phase`、
  `d3_rubric_version`、`d4c_packet_schema_target`、`d4b_bundle_schema_target`）。
- 必需的 runbook 章节存在（七个章节，具有精确 id 和非空且仅含经批准类别 token 的
  checklist）。
- 评分卡 / 标签槽位 / 门契约精确（E0/E1/E2、S0/S1/S2、桶名、标签槽位、门名、schema
  引用）。
- 发布门常量（`min_total_labels >= 50`、`k_min >= 5`、`min_rater_count >= 2`）；
  `d5_unblocked=false`、`public_release_gate_passed=false`。
- 禁止的标注来源（无 LLM/代理/模型标签；无模型名称规则；无基准私有桶作为运行时策
  略；无下游价值声明）；`model_or_llm_labeling_performed=false`、
  `model_assisted_labels_allowed=false`。
- 无私有读取 / 无数据包 / 无标签 / 无标注者（所有 false 标志），且公开报告中任何位
  置均无敏感键。
- 公开扫描器故障关闭：拒绝禁止键 + 值模式（路径/代码片段/content_sha/查询/标注者
  ID/包引用/原始标签/模型输出/提供者 payload/本地路径/URL/哈希/多行/原始 JSON/行范
  围）；契约容器拒绝未批准字符串（包括 `content_sha`、`query_text`、`packet_ref` 即
  使在容器内）；经批准的抽象类别字符串通过。
- 故障关闭的生成在扫描器泄漏时抛出；干净的公开报告不抛出；若自测失败则生成拒绝成
  功。
- CLI 选项面：恰好 `--self-test` 和 `--out`；无 `--input`，无
  `--allow-private-source-records`。

## 验证

```text
python3 -m py_compile eval/d4d_human_annotation_runbook.py    => PASS
python3 eval/d4d_human_annotation_runbook.py --self-test      => PASS (274/274 checks)
python3 eval/d4d_human_annotation_runbook.py \
  --out artifacts/d4d_human_annotation_runbook/\
d4d_human_annotation_runbook_report.json                     => PASS
  (status: protocol_ready_no_raters_no_labels_no_packets,
   forbidden_scan: pass, self_test_passed: true,
   private_packets_read: false,
   annotation_packets_generated: false,
   labels_collected: false,
   filled_packets_created: false,
   d4b_true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   inter_rater_agreement_measured: false,
   confidence_intervals_computed: false,
   model_or_llm_labeling_performed: false,
   model_assisted_labels_allowed: false,
   raters_recruited: false, raters_identified: false,
   rater_ids_emitted: false,
   public_release_gate_passed: false, d5_unblocked: false,
   runbook_protocol_defined: true,
   checklist_schema_defined: true,
   rater_independence_required: true,
   d3_rubric_required: true,
   d4c_packet_schema_referenced: true,
   d4b_bundle_schema_referenced: true,
   local_only_storage_required: true,
   no_llm_labeling_required: true,
   adjudication_policy_defined: true,
   disagreement_handling_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_gate_referenced: true,
   ci_gate_referenced: true,
   aggregate_only_public_release_required: true,
   mode: public_runbook_protocol_only, phase: D4d,
   d3_rubric_version: d3_true_dual_rubric_label_protocol_v1,
   d4c_packet_schema_target: d4c_annotation_packet_v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## 注意事项

- D4d 仅是人工标注 runbook / checklist 协议公开 artifact。它是 eval/诊断专用。它不
  改变运行时、retriever、pack、model、backend 或默认策略；也不改变 EvidenceCore 语
  义。它不是基准测试结果，不是下游 agent 价值声明，不是 runtime-clean 通用算法声
  明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。
- D4d 默认是纯协议。默认提交的 artifact 不读取任何私有数据包，不生成任何数据包，不
  招募/识别任何标注者，不采集任何标签，不创建任何已填充数据包，不创建任何 D4b
  bundle，不运行任何转换器，不计算任何校准，不度量任何一致性/置信区间，不执行任何
  模型/LLM 标注，也不通过任何公开发布门。D5 保持锁定。协议 true 标志仅对已定义的协
  议控制为 true，而非任何真实的标签采集或 bundle 声明。
- D4d 不是标签采集，不是数据包生成，不是已填充数据包创建，不是 D4b 真值 bundle 创
  建，不是转换器，不是校准，不是一致性度量，也不解锁 D5。它冻结为 D4e 做准备的人工
  标注 runbook/checklist。
- D4d 没有私有模式，没有 `--input`，也不读取私有数据包/源记录。与 D4c 不同，没有可
  选私有构建器。runbook 内容是纯类别且抽象的；公开 artifact 中没有数据包示例、代码
  片段、路径、ID、标注者姓名或 URL。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；协议 true 标志是唯一为 true 的控制标志。
- 没有修改任何运行时/retriever/pack/model/backend/默认策略文件。
  `current-research-conclusions` 未更新（D4d 是纯协议 artifact；无结论变更）。
