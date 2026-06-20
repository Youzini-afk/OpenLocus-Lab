# D3 双评分标签协议预注册（仅协议）

## 范围与声明边界

D3 是未来真实 E-score / S-score 标签采集与校准协议的**仅协议**
预注册。它是 D1（确定性双评分相关性脚手架）与 D2（代理可映射性）
之间、以及稍后 D4 本地/私有真实 E/S 校准运行之间的桥梁。

D3 **预注册**该协议。它**不**采集标签、**不**读取 private records、
**不**计算校准指标、**不**衡量 inter-rater agreement、**不**声称
真实 E/S 校准、**不**声称代理校准、**不**采集 model-assisted 标签。

- 声明级别：`dual_rubric_label_protocol_preregistration_only`。
- 评分版本：`d3_true_dual_rubric_label_protocol_v1`。
- 状态：`protocol_ready_no_labels_collected`；模式 `protocol_only`。

D3 是**仅评测/诊断协议**。它**不**改变运行时行为、检索器排序、pack
构建、模型调用、后端存储、默认策略或 EvidenceCore 语义。它**不是**
基准结果、**不是**下游 agent 价值声明、**不是** runtime-clean 通用
算法声明、**不是** OOD 时间维度声明，**也不是** QuIVer 系统声明。

- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D3 不输出 EvidenceCore 记录，也不改变其语义。
- D3 不采集标签：`labels_collected=false`、
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_measured=false`。
- D3 不读取 private records：`private_records_read=false`、
  `raw_private_records_read=false`、
  `private_records_persisted=false`。
- D3 不声称校准：`true_e_s_calibration_claimed=false`、
  `proxy_calibration_claimed=false`、
  `model_assisted_labels_collected=false`。

## CLI

D3 仅协议，不接受私有输入。**没有** `--input` 参数，也没有
`--allow-private-records` 标志。

```bash
python3 -m py_compile eval/d3_dual_rubric_preregistration.py
python3 eval/d3_dual_rubric_preregistration.py --self-test
python3 eval/d3_dual_rubric_preregistration.py \
    --out artifacts/d3_dual_rubric_preregistration/\
d3_dual_rubric_preregistration_report.json
```

## 产物章节（全部仅类别，仅聚合/协议）

已提交的产物位于
`artifacts/d3_dual_rubric_preregistration/d3_dual_rubric_preregistration_report.json`，
仅协议。身份 / 边界字段：

- `schema_version` = `d3_dual_rubric_preregistration.v1`
- `generated_by`、`generated_at`、`claim_level`、`rubric_version`、
  `status`、`mode`
- 标签协议 false 标志（全为 false）：`labels_collected`、
  `private_records_read`、`raw_private_records_read`、
  `private_records_persisted`、`true_e_s_calibration_claimed`、
  `proxy_calibration_claimed`、`model_assisted_labels_collected`、
  `inter_rater_agreement_measured`、`calibration_metrics_computed`。
- No-claim / no-runtime-change 标志（全为 false）：`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `model_calls_changed`、`backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。

### sampling_frame_protocol

- `eligible_record_sources` = `["local_private_p21_records",
  "local_private_d2b_proxy_smoke_candidates"]`（仅类别标签；无文件系统
  路径）。
- `sampling_axes` = `["proxy_bucket", "proxy_e_band", "proxy_s_band",
  "abstain_or_unmappable_status"]`。
- `stratification_required=true`。
- `max_records_per_batch_local_only=50`。
- `raw_record_material_private_only=true`。

### annotation_rubric

- `e_score_levels`：`E0`（无语义/直接作答证据）、`E1`（弱或部分）、
  `E2`（强，引用有效）。
- `s_score_levels`：`S0`（无依赖/支撑结构证据）、`S1`（弱或部分）、
  `S2`（强）。
- `definitions`：abstention gate（引用有效性/陈旧/uncited/no-evidence
  在 E/S 桶分配前触发）、E/S 序数刻度。
- `bucket_mapping`：`primary_evidence`（E2 引用有效）、
  `dependency_support`（S2 且 E 低于 E2）、`weak_candidates`
  （非零 E 或 S 但低于 high 阈值）、`abstained`（无证据或 abstention
  gate 触发）。
- `abstract_examples`：仅批准的抽象类别字符串 ——
  `direct_definition_of_requested_symbol`、
  `caller_import_relation_without_answer_bearing_text`、
  `same_module_but_insufficient_evidence`。无具体 repo/path/snippet
  内容。自测强制 examples 精确匹配该批准枚举；未批准的具体/类路径示例
  校验失败且被禁止扫描器拒绝。

### future_execution_gates

D4 是独立的受控阶段。执行真实 E/S 标签采集须满足全部 gate：

- `explicit_private_opt_in_required=true`。
- `local_output_path_required=true`；`output_location_category=
  tmp_only_local_private`。
- `no_committed_raw_labels=true`。
- `k_min=5`。
- `min_total_labels=50`。
- `inter_rater_agreement_required=true`。
- `agreement_metrics_aggregate_only=["cohens_kappa",
  "krippendorff_alpha"]`（仅聚合指标）。
- `confidence_intervals_required=true`。

### public_release_thresholds

- `min_total_n=50`。
- `k_min_per_cell=5`。
- `small_cell_policy="suppress_or_merge_to_other"`。
- `confidence_intervals_required=true`。
- `per_row_raw_label_outputs=false`。

### privacy_contract

- `no_task_ids=true`、`no_repo_ids_or_names=true`、
  `no_file_paths=true`、`no_spans_or_line_ranges=true`、
  `no_snippets_or_excerpts=true`、`no_content_hashes=true`、
  `no_prompts_or_responses=true`、`no_model_outputs=true`、
  `no_private_labels=true`、`no_raw_annotation_rows=true`、
  `no_per_row_hashes=true`、`no_local_filesystem_paths=true`。
- `forbidden_field_categories` 列出禁止字段名（`task_id`、`repo_id`、
  `repo`、`path`、`span`、`line_range`、`start_line`、`end_line`、
  `content_sha`、`snippet`、`excerpt`、`candidate_text`、`query`、
  `prompt`、`response`、`model_output`、`label`、`raw_label`、
  `annotation_row`、`per_row_hash`、`local_filesystem_path`）。

### phase_graph

D1..D6 仅作为类别字符串（无执行数据）：

- D1 `dual_rubric_relevance_scaffold`
- D2 `dual_rubric_proxy_aggregate_calibration`
- D3 `dual_rubric_label_protocol_preregistration`
- D4 `local_private_true_e_s_calibration_execution_gated`
- D5 `aggregate_calibration_release_candidate_gated`
- D6 `runtime_integration_decision_gated`

### forbidden_scan 摘要

严格的禁止输出扫描器在写入 JSON 产物前以 fail-closed 方式运行。它
拒绝禁止的字典键（path/span/content_sha/snippet/query/task_id/
repo_id/repo/label/raw_label/annotation_row/per_row_hash/model_output
等）出现在任意位置，并拒绝取值模式：任何 URL（无 URL 白名单）、
32/40/64 字符十六进制摘要、类密钥串、类路径 `src/foo.py` 和
`/private/foo.jsonl`、多行串、原始 JSON 片段、原始行范围 `12-34`。
它允许安全的协议字符串（`local_private_p21_records`、`proxy_bucket`、
`E0` 等）。

## No-claim / 安全标志

- `aggregate_only_public_artifact=true`、`diagnostic_only=true`、
  `not_evidence=true`。
- `runtime_behavior_changed=false`、`retriever_changed=false`、
  `pack_builder_changed=false`、`model_calls_changed=false`、
  `backend_changed=false`、`default_policy_changed=false`。
- `promotion_ready=false`、`default_should_change=false`、
  `evidencecore_semantics_changed=false`、
  `runtime_clean_general_algorithm_claimed=false`、
  `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
  `quiver_systems_supported=false`。
- `labels_collected=false`、`private_records_read=false`、
  `raw_private_records_read=false`、`private_records_persisted=false`、
  `true_e_s_calibration_claimed=false`、
  `proxy_calibration_claimed=false`、
  `model_assisted_labels_collected=false`、
  `inter_rater_agreement_measured=false`、
  `calibration_metrics_computed=false`。

## 验证

```text
python3 -m py_compile eval/d3_dual_rubric_preregistration.py           => PASS
python3 eval/d3_dual_rubric_preregistration.py --self-test            => PASS (96/96 项检查)
python3 eval/d3_dual_rubric_preregistration.py \
  --out artifacts/d3_dual_rubric_preregistration/\
d3_dual_rubric_preregistration_report.json                            => PASS
  (status: protocol_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_records_read: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   calibration_metrics_computed: false,
   inter_rater_agreement_measured: false,
   model_assisted_labels_collected: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

## 注意事项

- D3 是仅协议预注册。它仅评测/诊断。它**不**改变运行时、检索器、
  pack、模型、后端或默认策略；它**不**改变 EvidenceCore 语义。它
  **不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，**也不是**
  QuIVer 系统声明。
- D3 **不**采集标签、**不**读取 private records、**不**计算校准
  指标、**不**衡量 inter-rater agreement、**不**声称真实 E/S 校准、
  **不**声称代理校准、**不**采集 model-assisted 标签。D3 仅是该
  协议的*预注册*。
- D4 是**可能**执行本地/私有真实 E/S 校准的第一个阶段，且仅当全部
  `future_execution_gates` 满足时。D3 不自动 gate 或触发 D4；D4 需
  单独显式决策。
- 任何未来校准输出的公开发布须满足 `min_total_n=50`、
  `k_min_per_cell=5`、小单元抑制（`suppress_or_merge_to_other`）、
  置信区间以及 `per_row_raw_label_outputs=false`。
- D3 中任何示例均为批准的抽象类别字符串；不输出也不会输出具体
  repo/path/snippet 内容。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**
  触碰。
