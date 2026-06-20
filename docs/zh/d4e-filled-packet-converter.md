# D4e 已填充 Packet -> D4b Bundle 转换器夹具（公开夹具 / 无转换产物）

## 范围与声明边界

D4e 是**已填充 packet -> D4b 真值 bundle 转换器夹具**公开 artifact。D4e 在任
何真实人工标签存在之前，强化 D4d 人工标注与 D4b bundle 校验之间的转换控制平
面。默认提交的 artifact 是**公开夹具 / 无转换产物**，不是真实的已填充 packet
-> D4b bundle 转换运行，不是校准，不是一致性/置信区间计算，也不解锁 D5。

D4e 桥接关系为：

```text
D3 双评分卡 -> D4c 标注包 -> 人工标注 runbook（D4d）-> D4e 转换器 -> D4b 真值 bundle -> D5 聚合发布候选
```

D4e **不**默认读取私有已填充 packet，**不**默认将已填充 packet 转换为 D4b
bundle，**不**默认写入或提交 D4b bundle，**不**接受 D4c 源上下文字段，**不**
接受模型/代理/LLM 标签作为人工/手工标签，**不**在任何提交产物中发出包引用/任
务 ID/仓库 ID/路径/跨度/代码片段/内容哈希/查询/候选文本/标注者 ID，**不**计
算校准/标注者间一致性/置信区间，**不**通过任何公开发布门，**不**解锁 D5，**不**
声明真 E/S 校准，**不**执行模型/LLM 标注，且**不**改变运行时行为、retriever、
pack、model、backend、默认策略或 EvidenceCore 语义。

- 声明级别：`filled_packet_to_d4b_bundle_converter_harness_only`。
- D4c 数据包 schema 源：`d4c_annotation_packet_v1`。
- D4d runbook 协议：`d4d_human_annotation_runbook.v1`。
- D4b bundle schema 目标：`d4b_true_label_bundle_v1`。
- 状态：`blocked_no_filled_packets_available_or_no_conversion_run`；模式
  `public_harness_no_filled_packets_no_conversion`；阶段 `D4e`。

D4e 是**eval/诊断专用**。它不是基准测试结果，不是下游 agent 价值声明，不是
runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。

- EvidenceCore 保持为 `path + line range + content_sha + score + why +
  channels`；D4e 不发出任何 EvidenceCore 记录，也不改变其语义。
- D4e 默认不读取已填充 packet，也不运行转换：
  `private_filled_packets_read=false`、
  `filled_packets_validated=false`、
  `filled_packets_persisted=false`、
  `conversion_run=false`、
  `d4b_true_label_bundle_created=false`、
  `d4b_true_label_bundle_written=false`、
  `d4b_true_label_bundle_validated=false`、
  `labels_collected=false`、`labels_converted=false`、
  `raw_label_rows_emitted=false`、
  `packet_ids_emitted=false`、`task_ids_emitted=false`、
  `repo_ids_emitted=false`、`paths_or_spans_emitted=false`、
  `snippets_emitted=false`、`content_sha_emitted=false`、
  `query_or_candidate_text_emitted=false`、`rater_ids_emitted=false`、
  `private_input_path_emitted=false`、
  `private_output_path_emitted=false`、
  `exact_private_counts_emitted=false`。
- D4e 不计算指标，不执行模型标注，也不通过发布门：
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_measured=false`、
  `confidence_intervals_computed=false`、
  `model_or_llm_labeling_performed=false`、
  `model_assisted_labels_allowed=false`、
  `true_e_s_calibration_claimed=false`、
  `public_release_gate_passed=false`、`d5_unblocked=false`。

## 核心边界：D4e 是带阻塞公开产物的转换器夹具

- **默认提交的 D4e artifact** 是公开夹具 / 无转换产物。其状态为
  `blocked_no_filled_packets_available_or_no_conversion_run`。它不读取任何
  私有已填充 packet，不校验任何已填充 packet，不运行任何转换，不创建/写入/校
  验任何 D4b bundle，不采集/转换任何标签，不发出任何包引用/路径/代码片段/
  ID/标注者 ID，不计算任何校准/一致性/置信区间，不执行任何模型/LLM 标注，也
  不通过任何公开发布门。D5 保持锁定。
- D4e 有私有转换器模式（可选，不提交），仅用于本地 `/tmp` 运行。私有输出永不
  提交。
- 转换器仅消费已填充的标签槽位和 D4d attestation；它拒绝 D4c 源上下文字段
  （路径、跨度、代码片段、content_sha、查询文本、候选文本、packet 源上下文）。
  它不需要源上下文，也不应接受源上下文。

### D4d -> D4e -> D4b 关系

D4d 冻结 D4e 将使用的人工标注 runbook/checklist。D4e 将已填充的 D4c 数据包
（带人工填写的 E/S 槽位和 D4d attestation）映射为
`d4b_true_label_bundle_v1` 形状的 bundle。D4e 是带阻塞公开产物的转换器夹具：
默认不运行任何转换，不创建任何 bundle。当 D4d attestation 通过（无模型/代理
标签、schema 通过、/tmp 守卫通过）时，私有本地运行（在 `/tmp` 下，永不提交）
可将已填充 packet 转换为 D4b bundle。

## CLI

```bash
python3 -m py_compile eval/d4e_filled_packet_converter.py
python3 eval/d4e_filled_packet_converter.py --self-test
python3 eval/d4e_filled_packet_converter.py \
    --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json
# D4e 私有转换器（不提交；仅 /tmp）：
python3 eval/d4e_filled_packet_converter.py \
    --allow-private-filled-packets \
    --input-filled-packets /local/private/filled_packets.json \
    --out /tmp/d4b_true_label_bundle.json
# D4e 合成夹具自测（不提交；仅 /tmp）：
python3 eval/d4e_filled_packet_converter.py \
    --allow-private-filled-packets --synthetic-harness-test \
    --input-filled-packets /tmp/synthetic_filled_packets.json \
    --out /tmp/d4e_synthetic_bundle.json
```

默认模式：写入已提交的公开夹具 / 无转换 artifact（若省略 `--out` 则使用默认
输出路径）。

CLI 参数：`--self-test`、`--out`、`--allow-private-filled-packets`、
`--input-filled-packets`、`--synthetic-harness-test`。未知或类似私有输入的
参数会以通用 `invalid arguments` 消息拒绝，不回显私有路径或 basename
（SafeArgumentParser 模式）。

### 守卫要求

1. 默认无私有读取。
2. `--input-filled-packets` 不带 `--allow-private-filled-packets` 退出码 2。
3. `--allow-private-filled-packets` 不带 `--input-filled-packets` 退出码 2。
4. 私有模式要求显式 `--out`。
5. 提交产物路径在任何私有输入读取之前被拒绝。
6. 非 `/tmp` 的私有 `--out` 在任何私有输入读取之前被拒绝。
7. 解析后的 `/tmp` 守卫：父目录符号链接逃逸被拒绝；已存在的输出符号链接被拒
   绝；解析后的目标必须保持在 `/tmp` 下。
8. 在打开/stat 输入之前校验 CLI/输出守卫。
9. 清洗过的加载/解析/schema/隐私错误：
   `error: failed to load private filled packets (schema/privacy/parse error; details suppressed)`。
10. 成功 stdout 不得包含精确输入路径、输出路径、basename 或标签文本。
11. 私有输出永不提交。

## 私有已填充 packet 输入契约

D4e 消费一个最小的纯标签已填充 packet 批次，带 D4d attestation。D4e 不应需要
D4c 源上下文，应拒绝它。

必需的批次 schema：

```json
{
  "schema": "d4e_filled_annotation_packets_v1",
  "source_packet_schema": "d4c_annotation_packet_v1",
  "d4d_runbook_attestation": {
    "protocol": "d4d_human_annotation_runbook.v1",
    "two_independent_human_raters": true,
    "independent_before_adjudication": true,
    "no_llm_or_model_labels": true,
    "no_proxy_labels_as_true_labels": true,
    "local_only_storage": true
  },
  "packets": [
    {
      "packet_ref": "local-only opaque",
      "label_slots": {
        "e_score": "E0|E1|E2",
        "s_score": "S0|S1|S2",
        "bucket": "primary_evidence|dependency_support|weak_candidates|abstained",
        "citation_valid": true,
        "rater_pair_present": true,
        "adjudicated": true
      }
    }
  ]
}
```

允许的输入键：

- 批次：`schema`、`source_packet_schema`、`d4d_runbook_attestation`、
  `packets`。
- attestation：`protocol`、`two_independent_human_raters`、
  `independent_before_adjudication`、`no_llm_or_model_labels`、
  `no_proxy_labels_as_true_labels`、`local_only_storage`。
- packet：`packet_ref`、`label_slots`。
- 标签槽位：`e_score`、`s_score`、`bucket`、`citation_valid`、
  `rater_pair_present`、`adjudicated`。

拒绝的输入键/值：路径/跨度/代码片段/内容哈希；查询/候选文本；任务/仓库 ID；
标注者 ID/姓名；提示/响应/模型输出/提供者 payload/API 密钥；源上下文字段。
D4e 仅消费已填充标签和 attestation。

## 私有 D4b bundle 输出契约

`/tmp` 下的私有输出可包含标签，因为它是仅本地的且永不提交。

推荐输出：

```json
{
  "schema": "d4b_true_label_bundle_v1",
  "label_source": "human_manual_true_e_s",
  "rater_count": 2,
  "agreement_available": true,
  "confidence_intervals_available": false,
  "synthetic_harness_test": false,
  "synthetic_labels_converted_for_harness_only": false,
  "local_private_conversion_executed": true,
  "real_human_labels_converted": true,
  "labels": [
    {
      "e_score": "E0",
      "s_score": "S1",
      "bucket": "dependency_support",
      "citation_valid": true,
      "rater_pair_present": true,
      "adjudicated": true
    }
  ]
}
```

对于 `--synthetic-harness-test`，输出必须清晰标记：

- `synthetic_harness_test=true`
- `synthetic_labels_converted_for_harness_only=true`
- `local_private_conversion_executed=false`
- `real_human_labels_converted=false`

对于真实本地私有运行，`local_private_conversion_executed=true` 和
`real_human_labels_converted=true` 仅在非合成、D4d attestation 通过、无模型/代
理标签、输入 schema 通过、且 `/tmp` 守卫通过时才可为 true。文档必须说明：在合
成夹具上的本地 real-mode flag-path 测试不是真实标签存在的证据。

私有输出不得包含包引用、任务/仓库 ID、路径/跨度、代码片段、content_sha、查
询/候选文本、标注者 ID、提供者 payload、API 密钥、模型输出、精确输入/输出路
径或 basename。

## Artifact 身份（默认提交产物）

提交的产物位于
`artifacts/d4e_filled_packet_converter/d4e_filled_packet_converter_report.json`，
是公开夹具 / 无转换 artifact。身份/边界字段：

- `schema_version` = `d4e_filled_packet_converter_harness.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`、
  `d4c_packet_schema_source`、`d4d_runbook_protocol`、
  `d4b_bundle_schema_target`
- 默认 false 标志（全为 false）：`private_filled_packets_read`、
  `filled_packets_validated`、`filled_packets_persisted`、
  `conversion_run`、`d4b_true_label_bundle_created`、
  `d4b_true_label_bundle_written`、`d4b_true_label_bundle_validated`、
  `labels_collected`、`labels_converted`、`raw_label_rows_emitted`、
  `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
  `paths_or_spans_emitted`、`snippets_emitted`、`content_sha_emitted`、
  `query_or_candidate_text_emitted`、`rater_ids_emitted`、
  `private_input_path_emitted`、`private_output_path_emitted`、
  `exact_private_counts_emitted`、`calibration_metrics_computed`、
  `inter_rater_agreement_measured`、`confidence_intervals_computed`、
  `public_release_gate_passed`、`d5_unblocked`、
  `true_e_s_calibration_claimed`、`model_or_llm_labeling_performed`、
  `model_assisted_labels_allowed`。
- 无声明 / 无运行时变更标志（全为 false）：
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `model_calls_changed`、`backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 夹具/控制 true 标志（仅这些，全为 true）：
  `converter_harness_available`、`private_cli_guard_validated`、
  `tmp_output_resolved_guard_validated`、`sanitized_error_guard_validated`、
  `filled_packet_schema_contract_defined`、`d4d_attestation_required`、
  `d4b_bundle_schema_contract_defined`、`d4b_mapping_contract_defined`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。
- attestation 作用域字段：`default_public_mode_input_attestation_evaluated=false`，
  因为默认公开模式不读取输入；`private_conversion_d4d_attestation_required=true`，
  因为任何私有 filled-packet 转换都必须带 D4d attestation。
- `filled_packet_schema_contract`：`schema`、`source_packet_schema_ref`、
  `private_only=true`、`may_contain_filled_label_slots=true`、
  `required_label_slots`、`required_attestation_fields`、
  `rejects_source_context_fields=true`。
- `d4d_runbook_contract`：`protocol`、`required_attestation_fields`、
  `attestation_must_be_all_true=true`、
  `no_llm_or_model_labels_required=true`、
  `no_proxy_labels_as_true_labels_required=true`、
  `local_only_storage_required=true`。
- `d4b_bundle_schema_contract`：`schema`、`required_label_source`、
  `bundle_allowed_keys`、`label_object_allowed_keys`、`e_score_levels`、
  `s_score_levels`、`bucket_names`、`rejects_unknown_keys=true`、
  `rejects_packet_refs_paths_snippets_raters=true`。
- `d4b_mapping_contract`：`target_bundle_schema`、`packet_label_slots`、
  `source_packet_schema_ref`、`runbook_protocol`、
  `packet_to_bundle_requires_human_or_local_converter=true`、
  `converter_not_run_by_default=true`、`d4b_true_label_bundle_created=false`。
- `converter_harness_info`：`available=true`、`opt_in_required=true`、
  `output_location=tmp_only_local_private`、`committed=false`、
  `converts_filled_packets_to_d4b_bundle=true`、
  `rejects_source_context_fields=true`、
  `rejects_model_proxy_llm_labels=true`、`claims_calibration=false`。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写 JSON 前故障关闭）。

## 禁止内容扫描器（公开，故障关闭）

在写入公开 JSON 之前，运行一个严格的禁止输出扫描器，故障关闭。它拒绝禁止的 dict
键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
`start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
`query`、`query_text`、`prompt`、`response`、`model_output`、`label`、
`labels`、`raw_label`、`annotation_row`、`rater_id`、`annotator_id`、
`packet_ref`、`packet_id`、`private_record_ref`、`candidate_ref`、
`label_slots`、`annotation_instructions`、`e_score`、`s_score`、`bucket`、
`source_packet_schema`、`d4d_runbook_attestation`、`packets`、
`provider_payload`、`api_key` 等）在任何位置出现，并拒绝值模式：任何 URL（无
URL 白名单）、32/40/64 字符十六进制摘要、类密钥字符串、类路径 `src/foo.rs`
和 `/private/foo.jsonl`、多行字符串、原始 JSON 片段、原始行范围 `12-34` 以
及自测 sentinel。

契约容器（`filled_packet_schema_contract`、`d4d_runbook_contract`、
`d4b_bundle_schema_contract`、`d4b_mapping_contract`）是**精确字符串白名单**：
仅允许经批准的 schema/协议标识符、E/S 等级、桶名、标签槽位字段名、attestation
字段名、human-manual label source 标识符和经批准的 D4b bundle 字段名 token。
任意短字符串（如实现符号或私有文本）即使在契约容器内**也会被拒绝**（无过宽容
器豁免）。敏感字段名（`content_sha`、`query_text`、`packet_ref`、
`source_packet_schema`、`d4d_runbook_attestation`、`packets`）在任何位置作
为键、在契约外作为值，均被拒绝。

## 私有输出守卫（与公开扫描器不同）

私有 D4b bundle 输出守卫与公开扫描器不同：

- 允许标签字段和 E/S 值（bundle 是真实的 D4b bundle，可在本地包含标签）；
- 拒绝路径/代码片段/content_sha/查询/候选文本；
- 拒绝最终 D4b bundle 中的包引用；
- 拒绝标注者 ID；
- 拒绝提供者 payload/API 密钥/模型输出；
- 校验 schema 恰为 `d4b_true_label_bundle_v1`；
- 校验 `label_source` 恰为 `human_manual_true_e_s`；
- 校验合成夹具元数据或真实本地标志为真（合成 => harness-only 且无真实转换；
  真实 => 未标记为合成）；
- 校验输出元数据中无精确输入/输出路径或 basename。

## 自测

- 所有默认 false/true 标志（默认 artifact 不读取已填充 packet，不运行转换，
  不创建 bundle，无标签，无指标，无声明；夹具/控制标志为 true；诊断标志为
  true）。
- 默认无私有读取。
- CLI 守卫矩阵（input 无 allow、allow 无 input、allow 无 --out、提交产物路径、
  非 `/tmp` 输出、synthetic 无 allow、traversal）。
- 读取前校验（在无效 out / 提交 out / 非 `/tmp` out / synthetic 无 allow /
  input 无 allow / allow 无 input 时不访问输入）。
- 解析后的 `/tmp` 符号链接逃逸拒绝（父目录符号链接逃逸、已存在输出符号链接逃
 逸、有效 `/tmp` 守卫通过）。
- 清洗过的格式错误输入和未知/类似私有输入参数错误（无 sentinel、basename 或
  私有路径泄漏）。
- D4d attestation 必需（有效 attestation 通过；缺失 attestation 拒绝；缺失字
  段拒绝；多余字段拒绝；错误协议拒绝；`no_llm_or_model_labels=false` 拒绝；
  `no_proxy_labels_as_true_labels=false` 拒绝；
  `local_only_storage=false` 拒绝；
  `two_independent_human_raters=false` 拒绝；
  `independent_before_adjudication=false` 拒绝）。
- 已填充 packet 含 path/snippet/content_sha/query/candidate/rater_id/task_id/
  provider_payload/api_key/model_output/annotation_instructions 被拒绝。
- 有效合成已填充 packet 批次在 `/tmp` 中转换为 D4b bundle。
- 合成输出标记为 harness-only 且无真实转换声明。
- 有效 real-mode flag path 在合成夹具上可在非 synthetic 标志且 attestation
  通过时仅在本地设置 local conversion true；文档标记为 flag-path 测试，不是真
  实标签存在的证据。
- 输出 bundle 不含包引用/路径/代码片段/查询/候选文本。
- stdout/stderr/输出元数据不含精确输入/输出路径或 basename。
- 公开 artifact 扫描器故障关闭（拒绝禁止键 + 值模式；契约容器拒绝未批准字符
  串；经批准的 schema/level/bucket/slot/attestation/bundle-key token 通过）。
- 自测失败阻止公开 artifact 生成。

## 验证

```text
python3 -m py_compile eval/d4e_filled_packet_converter.py    => PASS
python3 eval/d4e_filled_packet_converter.py --self-test      => PASS (307/307 checks)
python3 eval/d4e_filled_packet_converter.py \
  --out artifacts/d4e_filled_packet_converter/\
d4e_filled_packet_converter_report.json                     => PASS
  (status: blocked_no_filled_packets_available_or_no_conversion_run,
   forbidden_scan: pass, self_test_passed: true,
   private_filled_packets_read: false,
   conversion_run: false,
   d4b_true_label_bundle_created: false,
   d4b_true_label_bundle_written: false,
   labels_converted: false,
   d5_unblocked: false,
   converter_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   filled_packet_schema_contract_defined: true,
   d4d_attestation_required: true,
   d4b_bundle_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_filled_packets_no_conversion, phase: D4e,
   d4c_packet_schema_source: d4c_annotation_packet_v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## 注意事项

- D4e 仅是已填充 packet -> D4b bundle 转换器夹具公开 artifact。它是
  eval/诊断专用。它**不**改变运行时、retriever、pack、model、backend 或默认策
  略；也**不**改变 EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值
  声明，不是 runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer
  系统声明。
- D4e 默认是带阻塞公开产物的夹具。默认提交产物**不**读取任何私有已填充
  packet，**不**运行任何转换，**不**创建/写入/校验任何 D4b bundle，**不**采
  集/转换任何标签，**不**计算任何校准/一致性/置信区间，**不**执行任何模型/LLM
  标注，也**不**通过任何公开发布门。D5 保持锁定。夹具/控制 true 标志仅对已
  校验的夹具/控制为 true，而非任何真实标签转换或 bundle 声明。
- D4e **不是**提交输出中的真实标签转换，**不是**校准，**不是**一致性/置信区
  间计算，也**不**解锁 D5。它在任何真实人工标签存在之前，强化 D4d 人工标注与
  D4b bundle 校验之间的转换控制平面。
- D4e 有私有转换器模式（可选，不提交）。私有输出仅写入 `/tmp` 且永不提交。在
  合成夹具上的 real-mode flag-path 测试（在本地设置
  `local_private_conversion_executed=true` 和
  `real_human_labels_converted=true`）仅是 flag-path 测试，**不**是真实标签存
  在的证据。真实人工标签尚未采集；D5 保持锁定。
- 转换器仅消费已填充的标签槽位和 D4d attestation；它拒绝 D4c 源上下文字段
  （路径、跨度、代码片段、content_sha、查询文本、候选文本、packet 源上下文）。
  D4d attestation 必须恰为 `d4d_human_annotation_runbook.v1`，且所有六个必需
  标志为 true（两名独立人工标注者、裁决前独立、无 LLM/模型标签、无代理标签作
  为真值、仅本地存储）；模型/代理/LLM 标签被拒绝作为人工/手工标签。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；夹具/控制 true 标志是唯一为 true 的控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4e 是夹具/仅阻塞 artifact；结论
  无变化）。
