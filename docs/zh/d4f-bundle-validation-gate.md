# D4f D4b Bundle 校验 / 门检查夹具（公开夹具 / 无校验产物）

## 范围与声明边界

D4f 是**D4b 真值 bundle 校验 / 门检查夹具**公开 artifact。D4f 是真实标签存在
之前的最后一个有用夹具：D4e 证明已填充 packet 可以在本地转换为 D4b bundle；
D4f 证明 D4b bundle 可以在本地校验并检查门前提，而无需发布标签、精确计数或指
标。默认提交的 artifact 是**公开夹具 / 无校验产物**，不是真实的 D4b bundle
校验运行，不是门检查通过，不是校准，不是一致性/置信区间计算，也不解锁 D5。

D4f 桥接关系为：

```text
D3 双评分卡 -> D4c 标注包 -> 人工标注 runbook（D4d）-> D4e 转换器 -> D4b 真值 bundle -> D4f 校验器 -> D5 聚合发布候选
```

D4f **不**默认读取私有 D4b bundle，**不**默认校验私有 D4b bundle，**不**默认
持久化任何私有 bundle，**不**在任何提交产物中发出标签/原始标签行/精确计数/
桶计数/单元计数/一致性指标值/置信区间数值，**不**接受包引用/任务 ID/仓库
ID/路径/跨度/代码片段/内容哈希/查询/候选文本/标注者 ID/模型输出/提供者
payload，**不**计算校准/标注者间一致性/置信区间，**不**通过任何公开发布门，
**不**解锁 D5，**不**声明真 E/S 校准，**不**执行模型/LLM 标注，且**不**改变
运行时行为、retriever、pack、model、backend、默认策略或 EvidenceCore 语义。

- 声明级别：`d4b_bundle_validation_gate_harness_only`。
- D4b bundle schema 源：`d4b_true_label_bundle_v1`。
- D4e 转换器源：`d4e_filled_packet_converter_harness.v1`。
- D4d runbook 协议：`d4d_human_annotation_runbook.v1`。
- 状态：`blocked_no_private_bundle_available_or_no_validation_run`；模式
  `public_harness_no_private_bundle_no_validation`；阶段 `D4f`。

D4f 是**eval/诊断专用**。它不是基准测试结果，不是下游 agent 价值声明，不是
runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer 系统声明。

- EvidenceCore 保持为 `path + line range + content_sha + score + why +
  channels`；D4f 不发出任何 EvidenceCore 记录，也不改变其语义。
- D4f 默认不读取 D4b bundle，也不运行校验：
  `private_bundle_read=false`、
  `private_bundle_validated=false`、
  `private_bundle_persisted=false`、
  `bundle_validation_run=false`、`labels_read=false`、
  `labels_persisted=false`、`raw_label_rows_emitted=false`、
  `exact_private_counts_emitted=false`、`bucket_counts_emitted=false`、
  `cell_counts_emitted=false`、`task_ids_emitted=false`、
  `repo_ids_emitted=false`、`paths_or_spans_emitted=false`、
  `snippets_emitted=false`、`content_sha_emitted=false`、
  `query_or_candidate_text_emitted=false`、`rater_ids_emitted=false`、
  `private_input_path_emitted=false`、
  `private_output_path_emitted=false`。
- D4f 不计算指标，不执行模型标注，也不通过发布门：
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_computed=false`、
  `inter_rater_agreement_measured=false`、
  `agreement_metric_values_emitted=false`、
  `confidence_intervals_computed=false`、
  `confidence_interval_values_emitted=false`、
  `model_or_llm_labeling_performed=false`、
  `model_assisted_labels_allowed=false`、
  `true_e_s_calibration_claimed=false`、
  `public_release_gate_passed=false`、`d5_unblocked=false`。

## 核心边界：D4f 是带阻塞公开产物的校验器夹具

- **默认提交的 D4f artifact** 是公开夹具 / 无校验产物。其状态为
  `blocked_no_private_bundle_available_or_no_validation_run`。它不读取任何
  私有 D4b bundle，不校验任何 bundle，不持久化任何私有 bundle，不读取任何
  标签，不发出任何标签/计数/指标/路径/ID/代码片段/标注者 ID，不计算任何校
  准/一致性/置信区间，不执行任何模型/LLM 标注，也不通过任何公开发布门。D5
  保持锁定。
- D4f 有私有校验器模式（可选，不提交），仅用于本地 `/tmp` 运行。私有输出永
  不提交。
- 校验器仅消费 D4e D4b bundle 输出形状；它拒绝包引用/路径/代码片段/
  content_sha/查询文本/候选文本/标注者 ID/提供者 payload/API 密钥/模型输出/
  原始一致性/置信区间数值/逐行哈希/未知键。它不需要源上下文，也不应接受源上
  下文。

### D4e -> D4f -> D5 关系

D4e 产生 `d4b_true_label_bundle_v1` 形状的 bundle（本地，`/tmp` 下，永不提
交）。D4f 消费该 bundle，校验其 schema，并运行门检查（schema、label_source、
rater_count、一致性可用性、CI 可用性、min-N 频段、k-min 频段）。D4f 是带阻
塞公开产物的校验器夹具：默认不运行任何校验，也不发出任何门报告。私有本地运
行（在 `/tmp` 下，永不提交）可校验 D4b bundle 并发出仅含门布尔和频段的私有
门报告（无标签、无精确计数、无指标）。

## CLI

```bash
python3 -m py_compile eval/d4f_bundle_validation_gate.py
python3 eval/d4f_bundle_validation_gate.py --self-test
python3 eval/d4f_bundle_validation_gate.py \
    --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json
# D4f 私有校验器（不提交；仅 /tmp）：
python3 eval/d4f_bundle_validation_gate.py \
    --allow-private-bundle \
    --input-bundle /local/private/d4b_bundle.json \
    --out /tmp/d4f_bundle_validation_report.json
# D4f 合成夹具自测（不提交；仅 /tmp）：
python3 eval/d4f_bundle_validation_gate.py \
    --allow-private-bundle --synthetic-harness-test \
    --input-bundle /tmp/synthetic_d4b_bundle.json \
    --out /tmp/d4f_synthetic_validation.json
```

默认模式：写入已提交的公开夹具 / 无校验 artifact（若省略 `--out` 则使用默认
输出路径）。

CLI 参数：`--self-test`、`--out`、`--allow-private-bundle`、
`--input-bundle`、`--synthetic-harness-test`。未知或类似私有输入的参数会以通
用 `invalid arguments` 消息拒绝，不回显私有路径或 basename
（SafeArgumentParser 模式）。

### 守卫要求

1. 默认无私有读取。
2. `--input-bundle` 不带 `--allow-private-bundle` 退出码 2。
3. `--allow-private-bundle` 不带 `--input-bundle` 退出码 2。
4. 私有模式要求显式 `--out`。
5. 提交产物路径在任何私有输入读取之前被拒绝。
6. 非 `/tmp` 的私有 `--out` 在任何私有输入读取之前被拒绝。
7. 解析后的 `/tmp` 守卫：父目录符号链接逃逸被拒绝；已存在的输出符号链接被拒
   绝；解析后的目标必须保持在 `/tmp` 下。
8. 在打开/stat 输入之前校验 CLI/输出守卫。
9. 清洗过的加载/解析/schema/隐私错误：
   `error: failed to load private bundle (schema/privacy/parse error; details suppressed)`。
10. 成功 stdout 不得包含精确输入路径、输出路径、basename、计数或指标。
11. 私有输出永不提交。

## 私有 D4b bundle 输入契约

D4f 消费 D4e D4b bundle 输出形状。D4f 不应需要包引用、源上下文或模型输出，
应拒绝它们。

必需的输入 bundle 形状：

```json
{
  "schema": "d4b_true_label_bundle_v1",
  "label_source": "human_manual_true_e_s",
  "rater_count": 2,
  "agreement_available": true,
  "confidence_intervals_available": true,
  "synthetic_harness_test": false,
  "local_private_conversion_executed": true,
  "real_human_labels_converted": true,
  "labels": [
    {
      "e_score": "E0|E1|E2",
      "s_score": "S0|S1|S2",
      "bucket": "primary_evidence|dependency_support|weak_candidates|abstained",
      "citation_valid": true,
      "rater_pair_present": true,
      "adjudicated": true
    }
  ]
}
```

允许的输入键：

- bundle：`schema`、`label_source`、`rater_count`、
  `agreement_available`、`confidence_intervals_available`、
  `synthetic_harness_test`、`local_private_conversion_executed`、
  `real_human_labels_converted`、`labels`。
- 标签：`e_score`、`s_score`、`bucket`、`citation_valid`、
  `rater_pair_present`、`adjudicated`。

拒绝的输入键/值：包引用；任务/仓库 ID；路径/跨度/代码片段；content_sha；
查询/候选文本；标注者 ID/姓名；提示/响应/模型输出/提供者 payload/API 密钥；
原始一致性指标值；置信区间数值；逐行哈希；未知键。D4f 仅校验 schema 和门可
用性，不计算指标。

## 私有 `/tmp` 输出契约

`/tmp` 下的私有输出仅可包含门布尔和频段（无标签、无精确计数、无指标）。它是
仅本地的且永不提交。

推荐私有报告：

```json
{
  "schema_version": "d4f_bundle_validation_gate_private_report.v1",
  "private_validation_report": true,
  "public_artifact": false,
  "do_not_commit": true,
  "synthetic_harness_test": false,
  "synthetic_bundle_validated_for_harness_only": false,
  "local_private_bundle_validation_run": true,
  "real_human_bundle_validated": true,
  "schema_gate_passed": true,
  "label_source_gate_passed": true,
  "rater_count_gate_passed": true,
  "agreement_availability_gate_passed": true,
  "ci_availability_gate_passed": true,
  "min_total_labels_gate_band": "met|not_met|not_evaluated",
  "k_min_gate_band": "met|not_met|not_evaluated",
  "small_cell_suppression_required": true,
  "exact_private_counts_emitted": false,
  "bucket_counts_emitted": false,
  "cell_counts_emitted": false,
  "agreement_metric_values_emitted": false,
  "confidence_interval_values_emitted": false,
  "public_release_gate_passed": false,
  "d5_unblocked": false
}
```

对于 `--synthetic-harness-test`，输出必须清晰标记：

- `synthetic_harness_test=true`
- `synthetic_bundle_validated_for_harness_only=true`
- `local_private_bundle_validation_run=false`
- `real_human_bundle_validated=false`

对于真实本地私有运行，`local_private_bundle_validation_run=true` 和
`real_human_bundle_validated=true` 仅在非合成标记、label_source 为 human
manual、输入 bundle 中 D4e real-conversion 标志
（`local_private_conversion_executed=true`、
`real_human_labels_converted=true`）为 true、输入 schema 通过、且 `/tmp`
守卫通过时才可为 true。文档必须说明：在合成夹具上的本地 real-mode flag-path
测试不是真实标签存在的证据。即使所有门本地通过，报告也始终保持
`public_release_gate_passed=false` 和 `d5_unblocked=false`。

如果 min-N 和 k-min 门在内部被测试，D4f 在内部计算精确 N 和每桶计数，但仅发
出频段（`met`、`not_met` 或 `not_evaluated`）；永不发出精确 N 或单元计数。

私有输出不得包含标签列表/标签行、精确计数、一致性/置信区间数值、包引用、任务/
仓库 ID、路径/跨度、代码片段、content_sha、查询/候选文本、标注者 ID、提供者
payload、API 密钥、模型输出、精确输入/输出路径或 basename。

## Artifact 身份（默认提交产物）

提交的产物位于
`artifacts/d4f_bundle_validation_gate/d4f_bundle_validation_gate_report.json`，
是公开夹具 / 无校验 artifact。身份/边界字段：

- `schema_version` = `d4f_bundle_validation_gate_harness.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`、
  `d4b_bundle_schema_source`、`d4e_converter_source`、
  `d4d_runbook_protocol`
- 默认 false 标志（全为 false）：`private_bundle_read`、
  `private_bundle_validated`、`private_bundle_persisted`、
  `bundle_validation_run`、`labels_read`、`labels_persisted`、
  `raw_label_rows_emitted`、`exact_private_counts_emitted`、
  `bucket_counts_emitted`、`cell_counts_emitted`、
  `calibration_metrics_computed`、`inter_rater_agreement_computed`、
  `inter_rater_agreement_measured`、`agreement_metric_values_emitted`、
  `confidence_intervals_computed`、`confidence_interval_values_emitted`、
  `public_release_gate_passed`、`d5_unblocked`、
  `true_e_s_calibration_claimed`、`private_input_path_emitted`、
  `private_output_path_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
  `paths_or_spans_emitted`、`snippets_emitted`、`content_sha_emitted`、
  `query_or_candidate_text_emitted`、`rater_ids_emitted`、
  `model_or_llm_labeling_performed`、`model_assisted_labels_allowed`。
- 无声明 / 无运行时变更标志（全为 false）：
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `model_calls_changed`、`backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 夹具/控制 true 标志（仅这些，全为 true）：
  `bundle_validation_harness_available`、`private_cli_guard_validated`、
  `tmp_output_resolved_guard_validated`、`sanitized_error_guard_validated`、
  `d4b_bundle_schema_contract_defined`、`gate_check_contract_defined`、
  `min_n_gate_referenced`、`k_min_gate_referenced`、
  `agreement_availability_gate_referenced`、`ci_availability_gate_referenced`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。
- `d4b_bundle_schema_contract`：`schema`、`required_label_source`、
  `bundle_allowed_keys`、`label_object_allowed_keys`、`e_score_levels`、
  `s_score_levels`、`bucket_names`、`rejects_unknown_keys=true`、
  `rejects_packet_refs_paths_snippets_raters=true`。
- `gate_check_contract`：`min_total_labels_gate_referenced=true`、
  `k_min_gate_referenced=true`、
  `agreement_availability_gate_referenced=true`、
  `ci_availability_gate_referenced=true`、
  `min_rater_count_gate_referenced=true`、`min_rater_count=2`、
  `min_total_labels_gate=50`、`k_min_cell_gate=5`、
  `gate_band_values=[met, not_met, not_evaluated]`、
  `small_cell_suppression_required=true`、
  `exact_counts_never_emitted=true`、`metrics_never_computed=true`、
  `validator_not_run_by_default=true`。
- `d4d_runbook_contract`：`protocol`、`required_attestation_fields`、
  `attestation_must_be_all_true=true`、
  `no_llm_or_model_labels_required=true`、
  `no_proxy_labels_as_true_labels_required=true`、
  `local_only_storage_required=true`。
- `d4e_converter_contract`：`converter_source`、`target_bundle_schema`、
  `private_only=true`、`output_location=tmp_only_local_private`、
  `committed=false`。
- `validation_harness_info`：`available=true`、`opt_in_required=true`、
  `output_location=tmp_only_local_private`、`committed=false`、
  `validates_d4b_bundle_schema=true`、`runs_gate_checks_only=true`、
  `rejects_packet_refs_paths_snippets_raters=true`、
  `rejects_model_proxy_llm_labels=true`、`claims_calibration=false`、
  `computes_agreement_or_ci=false`。
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
`provider_payload`、`api_key`、`agreement_metric`、`kappa`、
`confidence_interval`、`ci_value`、`ci_lower`、`ci_upper` 等）在任何位置出
现，并拒绝值模式：任何 URL（无 URL 白名单）、32/40/64 字符十六进制摘要、类密
钥字符串、类路径 `src/foo.rs` 和 `/private/foo.jsonl`、多行字符串、原始 JSON
片段、原始行范围 `12-34` 以及自测 sentinel。

契约容器（`d4b_bundle_schema_contract`、`gate_check_contract`、
`d4d_runbook_contract`、`d4e_converter_contract`）是**精确字符串白名单**：
仅允许经批准的 schema/协议标识符、E/S 等级、桶名、标签槽位字段名、attestation
字段名、human-manual label source 标识符、D4e 转换器源标识符、私有报告 schema
标识符、经批准的 D4b bundle 字段名 token、门频段值以及经批准的类别字符串
（如 `tmp_only_local_private`）。任意短字符串（如实现符号或私有文本）即使在
契约容器内**也会被拒绝**（无过宽容器豁免）。敏感字段名（`content_sha`、
`query_text`、`packet_ref`、`source_packet_schema`、`d4d_runbook_attestation`、
`packets`）在任何位置作为键、在契约外作为值，均被拒绝。

## 私有输出守卫（与公开扫描器和私有 bundle 输入守卫均不同）

私有 D4f 门报告输出守卫与公开扫描器和私有 bundle 输入守卫均不同：

- 允许门布尔/频段（报告是门检查报告，不是 bundle）；
- 允许 schema/类别名称（如 `tmp_only_local_private`、
  `d4f_bundle_validation_gate_private_report.v1`、`met`/`not_met`/
  `not_evaluated`）；
- 拒绝标签列表/标签行；
- 拒绝精确计数（`total_labels`、`label_count`、`bucket_count`、
  `cell_count`、`n`、`count` 等）；
- 拒绝一致性/置信区间数值；
- 拒绝任务/仓库/路径/代码片段/哈希/查询/标注者字段；
- 拒绝输入/输出路径/basename；
- 校验 schema_version 恰为
  `d4f_bundle_validation_gate_private_report.v1`；
- 校验 `private_validation_report=true`、`public_artifact=false`、
  `do_not_commit=true`、`small_cell_suppression_required=true`；
- 校验 `public_release_gate_passed=false`、`d5_unblocked=false`；
- 校验 `*_emitted=false` 标志（精确计数/桶/单元/一致性值/置信区间值）；
- 校验合成/真实标志为真（合成 => harness-only 且无真实校验；真实 => 未标记
  为合成）。

## 自测

- 所有默认 false/true 标志（默认 artifact 不读取 D4b bundle，不运行校验，
  无标签，无计数，无指标，无声明；夹具/控制标志为 true；诊断标志为
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
- D4b bundle 输入守卫（有效合成 bundle 通过；非 dict/未知 schema/错误
  label_source/多余顶层键/path/snippet/content_sha/query_text/
  candidate_text/rater_id/task_id/packet_ref/provider_payload/api_key/
  model_output/agreement_metric/confidence_interval/per_row_hash/未知标签
  键/无效 e_score/无效 bucket/非布尔 citation_valid/rater_count 低于最小/
  非布尔 agreement_available/合成但 local_conversion=true 被拒绝）。
- 门检查逻辑（有效 bundle：schema/label_source/rater_count/一致性/CI 门通
  过，频段发出；小 bundle min-N not_met；大 bundle min-N met；k_min 门所有
  桶 >= k_min 时 met；某桶 1 <= count < k_min 时 not_met；无效 bundle：所有
  门 not_evaluated；缺失一致性/CI 标志失败；无精确计数键发出）。
- 真实模式 flag-path 决策逻辑（合成 CLI false；bundle 合成 false；真实通过
  true；非人工 label source false；D4e 非真实转换 false；无效 schema false；
  tmp 守卫失败 false）。
- 有效合成 D4b bundle 在 `/tmp` 私有模式中被接受。
- 合成报告标记为 harness-only 且无真实校验声明。
- 有效 real-mode flag path 在合成夹具上可在非 synthetic 标志、label source
  为 human manual、D4e real-conversion 标志为 true 时仅在本地设置 local
  validation true；文档标记为 flag-path 测试，不是真实标签存在的证据。
- 私有报告输出守卫拒绝：labels 键、path 键、snippet 键、rater_id 键、错误
  schema_version、public_release_gate_passed true、d5_unblocked true、合成但
  local_validation true、agreement_metric 键、confidence_interval 键、
  total_labels 键、无效频段值；清洁报告通过。
- stdout/stderr/输出元数据不含精确输入/输出路径或 basename。
- 公开 artifact 扫描器故障关闭（拒绝禁止键 + 值模式；契约容器拒绝未批准字符
  串；经批准的 schema/level/bucket/slot/attestation/bundle-key token/频段值
  通过）。
- 自测失败阻止公开 artifact 生成。

## 验证

```text
python3 -m py_compile eval/d4f_bundle_validation_gate.py    => PASS
python3 eval/d4f_bundle_validation_gate.py --self-test      => PASS (352/352 checks)
python3 eval/d4f_bundle_validation_gate.py \
  --out artifacts/d4f_bundle_validation_gate/\
d4f_bundle_validation_gate_report.json                     => PASS
  (status: blocked_no_private_bundle_available_or_no_validation_run,
   forbidden_scan: pass, self_test_passed: true,
   private_bundle_read: false,
   bundle_validation_run: false,
   d5_unblocked: false,
   public_release_gate_passed: false,
   bundle_validation_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   d4b_bundle_schema_contract_defined: true,
   gate_check_contract_defined: true,
   min_n_gate_referenced: true,
   k_min_gate_referenced: true,
   agreement_availability_gate_referenced: true,
   ci_availability_gate_referenced: true,
   mode: public_harness_no_private_bundle_no_validation, phase: D4f,
   d4b_bundle_schema_source: d4b_true_label_bundle_v1,
   d4e_converter_source: d4e_filled_packet_converter_harness.v1,
   d4d_runbook_protocol: d4d_human_annotation_runbook.v1)
# 私有 /tmp 合成 smoke（不提交）：
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle --synthetic-harness-test \
  --input-bundle /tmp/synthetic_d4b_bundle.json \
  --out /tmp/d4f_synthetic_validation.json                      => PASS
  (synthetic_harness_test=true,
   synthetic_bundle_validated_for_harness_only=true,
   local_private_bundle_validation_run=false,
   real_human_bundle_validated=false,
   schema_gate_passed=true, public_release_gate_passed=false,
   d5_unblocked=false)
# 私有 /tmp real-mode flag-path smoke（不提交；在合成夹具上，D4e real-conversion
# 标志设为 true）：
python3 eval/d4f_bundle_validation_gate.py \
  --allow-private-bundle \
  --input-bundle /tmp/real_flagpath_d4b_bundle.json \
  --out /tmp/d4f_real_flagpath_validation.json                  => PASS
  (synthetic_harness_test=false,
   local_private_bundle_validation_run=true,
   real_human_bundle_validated=true,
   public_release_gate_passed=false,
   d5_unblocked=false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## 注意事项

- D4f 仅是 D4b bundle 校验 / 门检查夹具公开 artifact。它是
  eval/诊断专用。它**不**改变运行时、retriever、pack、model、backend 或默认策
  略；也**不**改变 EvidenceCore 语义。它不是基准测试结果，不是下游 agent 价值
  声明，不是 runtime-clean 通用算法声明，不是 OOD 时间性声明，也不是 QuIVer
  系统声明。
- D4f 默认是带阻塞公开产物的夹具。默认提交产物**不**读取任何私有 D4b
  bundle，**不**运行任何校验，**不**持久化任何私有 bundle，**不**读取任何
  标签，**不**计算任何校准/一致性/置信区间，**不**执行任何模型/LLM
  标注，也**不**通过任何公开发布门。D5 保持锁定。夹具/控制 true 标志仅对已
  校验的夹具/控制为 true，而非任何真实 bundle 校验或门通过声明。
- D4f **不是**提交输出中的真实 bundle 校验，**不是**门通过，**不是**校准，
  **不是**一致性/置信区间计算，也**不**解锁 D5。它是真实标签存在之前的最后
  一个有用夹具：D4e 证明已填充 packet 可以在本地转换为 D4b bundle；D4f 证明
  D4b bundle 可以在本地校验并检查门前提，而无需发布标签、精确计数或指标。
- D4f 有私有校验器模式（可选，不提交）。私有输出仅写入 `/tmp` 且永不提交。
  私有报告仅含门布尔和频段（无标签、无精确计数、无指标）。在合成夹具上的
  real-mode flag-path 测试（在本地设置
  `local_private_bundle_validation_run=true` 和
  `real_human_bundle_validated=true`）仅是 flag-path 测试，**不**是真实标签
  存在的证据。真实人工标签尚未采集；D5 保持锁定。
- 校验器仅消费 D4e D4b bundle 输出形状；它拒绝包引用/路径/代码片段/
  content_sha/查询文本/候选文本/标注者 ID/提供者 payload/API 密钥/模型输出/
  原始一致性/置信区间数值/逐行哈希/未知键。D4f 仅校验 schema 和门可用性，
  不计算指标。
- min-N 和 k-min 门在内部计算（精确 N 和每桶计数），但报告仅发出频段
  （`met`/`not_met`/`not_evaluated`）；永不发出精确 N 或单元计数。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；夹具/控制 true 标志是唯一为 true 的控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4f 是夹具/仅阻塞 artifact；结论
  无变化）。
