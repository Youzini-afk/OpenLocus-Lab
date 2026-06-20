# D4 系列 Harness 汇总 / D5 阻塞状态（公开纯汇总 artifact）

## 范围与声明边界

D4 系列汇总是**D4 系列 harness 汇总 / D5 阻塞状态**公开 artifact。它是
**纯汇总** artifact，**不是**新的研究阶段。它仅汇总已提交的 D4a-D4f 公开
状态/声明级别以及 D5 阻塞项。它不执行任何私有读取、不进行任何探针、不产生
任何 `/tmp` 输出、不采集标签、不计算指标、也不进行 D5 校准。

D4 系列控制面桥接关系为：

```text
D4a 执行门（试运行）-> D4b 真值 bundle 夹具 -> D4c 标注包构建夹具 -> D4d 人工标注 runbook -> D4e 已填充包转换器夹具 -> D4f bundle 校验门夹具 ->（D5 阻塞：无真实人工手动标签）
```

汇总**不**读取私有记录、数据包、标签或 bundle，**不**在任何提交产物中发出
标签/原始标签行/精确计数/一致性/置信区间数值，**不**接受包引用/任务 ID/
仓库 ID/路径/跨度/代码片段/内容哈希/查询/候选文本/标注者 ID/模型输出/提供者
payload，**不**计算校准/标注者间一致性/置信区间，**不**通过任何公开发布门，
**不**解锁 D5，**不**声明真 E/S 校准，**不**执行模型/LLM 标注，且**不**改变
运行时行为、retriever、pack、model、backend、默认策略或 EvidenceCore 语义。

- Schema 版本：`d4_series_rollup.v1`。
- 声明级别：`d4_series_harness_rollup_only`。
- 状态：`d5_blocked_no_real_human_manual_labels`；模式
  `public_rollup_no_private_reads`；阶段 `D4-rollup`。

汇总是**eval/诊断专用**。它不是基准测试结果，不是下游 agent 价值声明，不是
runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。

- EvidenceCore 保持为 `path + line range + content_sha + score + why +
  channels`；汇总不发出任何 EvidenceCore 记录，也不改变其语义。
- 汇总不读取私有记录/数据包/标签/bundle，也不采集标签：
  `private_records_read=false`、`private_packets_read=false`、
  `private_labels_read=false`、`private_bundles_read=false`、
  `labels_collected=false`。
- 汇总不计算指标，也不声明校准：
  `calibration_metrics_computed=false`、
  `agreement_metrics_computed=false`、
  `confidence_intervals_computed=false`、
  `true_e_s_calibration_claimed=false`。
- 汇总不通过任何发布门，也不解锁 D5：
  `d5_public_aggregate_candidate_allowed=false`。
- 无声明/无运行时变更标志（均为 false）：
  `promotion_ready=false`、`default_should_change=false`、
  `downstream_agent_value_proven=false`、
  `runtime_behavior_changed=false`、`retriever_changed=false`、
  `pack_builder_changed=false`、`model_calls_changed=false`、
  `backend_changed=false`、`default_policy_changed=false`、
  `evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `ood_temporal_supported=false`、`quiver_systems_supported=false`。

## 核心边界：纯汇总，D5 保持阻塞

- **默认提交的汇总 artifact** 是公开纯汇总 artifact。其状态为
  `d5_blocked_no_real_human_manual_labels`。它不读取任何私有记录/数据包/
  标签/bundle，不采集任何标签，不发出任何标签/计数/指标/路径/ID/代码片段/
  标注者 ID，不计算任何校准/一致性/置信区间，不执行任何模型/LLM 标注，也不
  通过任何公开发布门。D5 保持阻塞。
- 汇总没有私有模式。它没有 `/tmp` 输出路径。它没有私有输入的 CLI 守卫。它
  仅仅是六个已提交 D4 夹具 artifact 的公开聚合。
- 真实人工手动标签尚未采集。D5 未解锁。不允许任何 D5 公开聚合候选。

### D5 前提条件（全部为 false）

Artifact 同时以 flat boolean 和 `d5_prerequisites` 对象承载这些值，便于阅读；
两种表示必须完全一致。

```text
real_human_manual_labels_available=false
d4e_real_local_conversion_over_real_labels_run=false
d4f_real_local_validation_over_real_labels_run=false
min_n_gate_passed_for_real_labels=false
k_min_gate_passed_for_real_labels=false
agreement_gate_passed_for_real_labels=false
ci_gate_passed_for_real_labels=false
d5_public_aggregate_candidate_allowed=false
```

## 聚合的 D4 阶段（恰好六个，每个恰好一次）

汇总恰好列出六个 D4 阶段（D4a-D4f），每个恰好一次，附带其已提交的短格式
commit ID、`artifact_status` 与 `claim_level`。无私有路径，无计数，无指标，
无包/bundle 内容，无任务/仓库 ID，无标注者 ID。

| 阶段 | Commit | artifact_status | claim_level |
|---|---|---|---|
| D4a | `d62c13b` | `execution_gate_ready_no_labels_collected` | `dual_rubric_execution_gate_dry_run_only` |
| D4b | `6dd4024` | `blocked_no_true_label_bundle_available` | `true_label_bundle_execution_harness_only` |
| D4c | `3458716` | `blocked_no_annotation_packets_created` | `annotation_packet_builder_harness_only` |
| D4d | `55c9850` | `protocol_ready_no_raters_no_labels_no_packets` | `human_annotation_runbook_protocol_only` |
| D4e | `280d8bb` | `blocked_no_filled_packets_available_or_no_conversion_run` | `filled_packet_to_d4b_bundle_converter_harness_only` |
| D4f | `fea76d3` | `blocked_no_private_bundle_available_or_no_validation_run` | `d4b_bundle_validation_gate_harness_only` |

### 安全 true 布尔（控制面链 + 夹具完备性）

```text
control_plane_chain_complete=true
d4a_execution_gate_complete=true
d4b_true_label_bundle_harness_complete=true
d4c_annotation_packet_builder_harness_complete=true
d4d_human_annotation_runbook_complete=true
d4e_converter_harness_complete=true
d4f_bundle_validation_gate_harness_complete=true
aggregate_only_public_artifact=true
diagnostic_only=true
not_evidence=true
```

这些安全 true 标志仅表达控制面链与各 D4 夹具 artifact 已存在且已提交。它们
**不**是真实标签采集、真实转换、真实校验、门通过、校准、一致性、置信区间
或 D5 解锁的声明。

## CLI

```bash
python3 -m py_compile eval/d4_series_rollup.py
python3 eval/d4_series_rollup.py --self-test
python3 eval/d4_series_rollup.py \
    --out artifacts/d4_series_rollup/d4_series_rollup_report.json
```

默认模式：写入已提交的公开纯汇总 artifact（若省略 `--out` 则使用默认输出
路径）。

CLI 参数：`--self-test`、`--out`。未知/类似私有的参数以通用的 `invalid
arguments` 消息拒绝，不回显私有路径或基名（SafeArgumentParser 模式）。汇总
**没有** `--allow-private-*`、**没有** `--input-*`、也**没有**
`--synthetic-*` 标志：它是纯汇总，不读取任何私有输入。

## artifact 标识（默认提交 artifact）

提交到
`artifacts/d4_series_rollup/d4_series_rollup_report.json` 的 artifact 是
公开纯汇总 artifact。标识/边界字段：

- `schema_version` = `d4_series_rollup.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- `d4_phases`：恰好六个条目的列表；每个条目恰好有四个键 `phase`、`commit`、
  `artifact_status`、`claim_level`。此列表是一个**精确**契约容器（见下文
  扫描器）。
- 安全 true 布尔（恰好这些，全部为 true）：
  `control_plane_chain_complete`、`d4a_execution_gate_complete`、
  `d4b_true_label_bundle_harness_complete`、
  `d4c_annotation_packet_builder_harness_complete`、
  `d4d_human_annotation_runbook_complete`、
  `d4e_converter_harness_complete`、
  `d4f_bundle_validation_gate_harness_complete`、
  `aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`。
- D5 前提条件标志（全部为 false）：见上文。
- 无读取/无声明/无运行时变更标志（全部为 false）：见上文。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前故障关闭）。

## 禁止内容扫描器（公开，故障关闭）

一个严格的禁止输出扫描器在写入公开 JSON 前以故障关闭方式运行。拒绝禁止的
字典键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
`start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
`query`、`query_text`、`prompt`、`response`、`model_output`、`label`、
`labels`、`raw_label`、`annotation_row`、`rater_id`、`annotator_id`、
`packet_ref`、`packet_id`、`private_record_ref`、`candidate_ref`、
`label_slots`、`annotation_instructions`、`e_score`、`s_score`、`bucket`、
`source_packet_schema`、`d4d_runbook_attestation`、`packets`、
`provider_payload`、`api_key`、`agreement_metric`、`kappa`、
`confidence_interval`、`ci_value`、`ci_lower`、`ci_upper`、
`total_labels`、`label_count`、`bucket_count`、`cell_count` 等）出现在任何
位置，并拒绝值模式：任何 URL（无 URL 白名单）、32/40/64 字符十六进制摘要、
类似密钥的字符串、路径形式 `src/foo.rs` 和 `/private/foo.jsonl`、多行字符
串、原始 JSON 片段、原始行范围 `12-34` 和 `12:34`，以及自测哨兵。

`d4_phases` 列表是一个**精确字符串白名单**契约容器：只有已批准的阶段 ID
（`D4a`-`D4f`、`D4-rollup`）、六个短 commit ID、六个阶段级
`artifact_status` 字符串、以及六个阶段级 `claim_level` 字符串可作为**值**
出现在其中。任意短字符串（如实现符号、`compute_loss`、私有文本）即使在契约
容器内也被拒绝（无过宽容器豁免）。敏感字段名（`content_sha`、
`query_text`、`packet_ref`、`source_packet_schema`、
`d4d_runbook_attestation`、`packets`）即使在契约容器内也被拒绝（它们不在
批准白名单中），且作为键在任何位置也被拒绝。任何位置都不允许 URL。

## 自测

- artifact 标识字段（`schema_version`、`claim_level`、`status`、
  `mode`、`phase`、`generated_by`）。
- 所有安全 true 标志为 true（控制面链 + 各 D4 夹具完备 + 仅聚合/诊断/非
  证据）。
- 所有 D5 前提条件标志为 false。
- 所有无读取/无声明/无运行时变更 false 标志为 false。
- `d4_phases` 恰好有六个条目；D4a-D4f 每个恰好出现一次；无重复；无多余或
  缺失的阶段 ID。
- 每个 `d4_phases` 条目恰好有四个键 `phase`、`commit`、`artifact_status`、
  `claim_level`。
- 各阶段的 `commit`、`artifact_status`、`claim_level` 与精确预期字符串
  匹配。
- `control_plane_chain_complete=true`。
- 公开 artifact 禁止内容扫描器：
  - 拒绝禁止的字典键（`task_id`、`repo_id`、`repo`、`path`、`span`、
    `start_line`、`end_line`、`content_sha`、`snippet`、
    `candidate_text`、`query`、`query_text`、`prompt`、`response`、
    `model_output`、`label`、`raw_label`、`annotation_row`、
    `rater_id`、`annotator_id`、`packet_ref`、`packet_id`、
    `private_record_ref`、`candidate_ref`、`per_row_hash`、`row_hash`、
    `provider_payload`、`api_key`、`agreement_metric`、
    `confidence_interval`、`ci_value`、`ci_lower`、`ci_upper`、`kappa`、
    `total_labels`、`label_count`、`bucket_count`、`cell_count`）；
  - 拒绝值模式（URL、32/40/64 字符十六进制摘要、类似密钥、路径形式、前导
    斜杠路径、`.jsonl` 路径、多行、原始 JSON 片段、行范围 `12-34`、行范围
    `12:34`、自测哨兵）；
  - 拒绝 `d4_phases` 契约容器内未批准字符串（无过宽容器豁免）；
  - 拒绝敏感字段名作为**值**出现在契约容器内；
  - 拒绝契约容器内 URL（无 URL 白名单）；
  - 允许契约容器内已批准的阶段/commit/状态/声明级别字符串。
- 故障关闭生成：干净公开报告不抛异常；泄漏报告抛异常；自测失败时拒绝并抛
  异常，自测通过时不抛；失败自测不携带成功状态；通过自测携带成功状态。
- 公开报告自扫描干净；任何位置无禁止键。
- CLI 参数面：`--self-test`、`--out`；无其他参数。

## 验证

```text
python3 -m py_compile eval/d4_series_rollup.py    => PASS
python3 eval/d4_series_rollup.py --self-test     => PASS (147/147 checks)
python3 eval/d4_series_rollup.py \
  --out artifacts/d4_series_rollup/d4_series_rollup_report.json  => PASS
  (status: d5_blocked_no_real_human_manual_labels,
   forbidden_scan: pass, self_test_passed: true,
   control_plane_chain_complete: true,
   d5_public_aggregate_candidate_allowed: false,
   real_human_manual_labels_available: false,
   mode: public_rollup_no_private_reads, phase: D4-rollup,
   d4_phases: [D4a d62c13b, D4b 6dd4024, D4c 3458716,
               D4d 55c9850, D4e 280d8bb, D4f fea76d3])
python3 scripts/validate_docs_i18n.py             => PASS
git diff --check                                 => PASS
```

## 注意事项

- D4 系列汇总是公开纯汇总 artifact。它是 eval/诊断专用。它**不**改变
  运行时、retriever、pack、model、backend 或默认策略；也**不**改变
  EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值声明，不是
  runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。
- 汇总仅聚合已提交的 D4a-D4f 公开状态/声明级别。它**不**重新运行任何 D4
  夹具，**不**采集标签，**不**计算校准/一致性/置信区间，**不**校验任何
  bundle，也**不**解锁 D5。D5 保持阻塞，因为真实人工手动标签尚未采集。
- `d4_phases` 中的 `artifact_status` 字符串是 D4 系列汇总契约指定的汇总摘
  要形式。D4c 汇总摘要状态为
  `blocked_no_annotation_packets_created`；位于
  `artifacts/d4c_annotation_packet_builder/` 的底层已提交 D4c artifact 报告
  了更完整的状态
  `blocked_no_private_source_records_available_or_no_packets_built`
  （相同的阻塞语义，更完整的措辞）。D4a、D4b、D4d、D4e 和 D4f 的汇总状态
  与底层已提交 artifact 逐字匹配。全部六个 `claim_level` 值与全部六个短
  commit ID 与底层已提交 artifact 逐字匹配。
- 安全 true 标志仅表达控制面链与各 D4 夹具 artifact 已存在且已提交。它们
  **不**是真实标签采集、真实转换、真实校验、门通过、校准、一致性、置信区间
  或 D5 解锁的声明。
- 所有无声明/无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持 true；安全 true 标志是唯一为 true 的标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（汇总为纯汇总/D5 阻塞
  artifact；结论无变化）。
