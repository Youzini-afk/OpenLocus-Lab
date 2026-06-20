# D5-A0 自动 E/S 校准 Smoke（公开仅聚合 artifact）

## 范围与声明边界

D5-A0 是 Step 6 dual-rubric 流水线在控制面之后的**首个实证 smoke**。它使用**已提交
的 r14 sanity 固定数据**（`fixtures/r14/tasks/sanity.jsonl` +
`fixtures/r14/labels/sanity.jsonl`）与**真实 OpenLocus retrieval 输出**（临时生成
到 `/tmp`，绝不提交）计算**自动 E/S 校准 smoke** 聚合指标，覆盖四种固定 retrieval
方法（regex、bm25、symbol、rrf）。

D5-A0 是 D4 系列控制面 harness 因缺少真实人工/手动 true E/S 标签而被阻塞后的实
证转折。先前轨迹过度要求把“新增人工标签”作为全局阻塞；D5-A0 停止了“仅控制面”阶
段，通过从 r14 sanity 固定数据中**已提交的 span 标签**（gold spans + hard
negatives）派生**自动 E 标签**与**确定性 S-proxy 标签**来产出实证结果。不采集任
何新人工标签。

D5-A 自动/程序化实证路径已激活（本 smoke）。D5-H / 人工参考 / 人工校准路径在人
工标签到位前仍属 out of scope；D5-A0 **不**解锁 default、policy、公开发布或人工
校准声明。

D5-A0 **不**采集新人工/手动标签，**不**声明 true E/S 校准，**不**审计人工参考标
签，**不**通过任何公开发布门，**不**提升任何 candidate，**不**解锁 D5-H / 人工参
考 / 人工校准声明，**不**解锁 default/policy/公开发布或人工校准声明，**不**改变运
行时行为、retriever、pack、model、backend、默认策略或 EvidenceCore 语义。D5-A0
**不**提交 raw predictions、raw retrieval 输出、per-candidate 行、path、span、
snippet、content hash、query、gold 标签、hard-negative 标签、repo ID、task ID 或
任何行级数据。

- 声明级别（claim_level）：`automated_e_s_calibration_smoke_only`。
- 状态（status）：成功时为 `automated_es_calibration_smoke_pass`；模式（mode）
  为 `public_aggregate_r14_retrieval_smoke`；阶段（phase）为 `D5-A0`。
- D5-A0 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游 agent 价值声
  明，**不是** runtime-clean 通用算法声明，**不是** OOD 时间性声明，也**不是**
  QuIVer 系统声明。

### D4 系列 -> D5-A0 关系

```text
D4 系列控制面 harness（D4a-D4f + D4-rollup）
-> D5-H / 人工参考 / 人工校准路径在人工标签到位前 out of scope
-> D5-A0 自动 E/S 校准 smoke（基于已提交 r14 sanity 标签）
   （D5-A 自动实证路径已激活；使用已提交标签；不采集新人工标签；
     不声明 true E/S 校准；不解锁 default/policy/公开发布/人工校准声明）
```

D5-A0 **不是** D5-H。D5-H / 人工参考 / 人工校准审计在真实人工/手动 true E/S 标签
采集前仍属 out of scope/不可用；D5-A 自动/程序化实证路径已激活并继续。D5-A0 仅通
过从已提交的 span 标签（这些标签最初是为 span-recall 指标采集的，不是为 true E/S
评分准则采集的）派生自动 E/S 标签，产出首个实证 smoke。因此 D5-A0 是 smoke，不是
校准，且**不**解锁 default/policy/公开发布或人工校准声明。

## 自动 E 标签流程

自动 E 标签从已提交的 r14 sanity span 标签（gold spans + hard negatives）确定
性派生。它**不是**真实人工 E-score，也**不是** D3 dual-rubric E-score。

每个 candidate（candidate = 一条来自真实 OpenLocus retrieval 输出的 EvidenceCore
行）的处理流程：

1. **无效 / 源缺失** candidate（无 `path`，或无有效 `1 <= start_line <= end_line`）
   -> `e_uncertain`。
2. **同时重叠 hard-negative 与 gold**（同 path 且行重叠同时命中 hard-negative span
   和 gold span）-> `conflict_uncertain`。
3. **仅重叠 hard-negative** -> `e_hard_negative`。
4. **重叠 gold** -> `e_positive`。
5. **同 gold 文件但无 gold 重叠**（candidate path 匹配某 gold 文件 path，但
   candidate 行不与任何 gold span 重叠）-> `e_wrong_span_gold_file`。
6. **非 gold 文件且 span 有效** -> `e_negative_non_gold_file`。
7. **缺失标签**绝不作为负样本；某 task 缺标签时，candidate 按上述 path 判定走对应
   分支（或当无效时落到 `e_uncertain`）。

E 标签类别：`e_positive`、`e_hard_negative`、`conflict_uncertain`、
`e_wrong_span_gold_file`、`e_negative_non_gold_file`、`e_uncertain`。

## S-proxy 标签流程

S-proxy 标签是**确定性 support-shape 信号**，**不是**真实人工 S-score，也**不是**
D3 dual-rubric S-score。它保守：仅对确定性 support-shape 信号给正。

每个 candidate 的处理流程：

1. **E-positive** -> `s_proxy_not_evaluated_for_e_positive`（避免与 S-positive
   support 混淆）。
2. **E-hard-negative / conflict-uncertain / e-uncertain** -> `s_proxy_none`（避免
   把 hard-negative 或无效 shape 与正向 support 混淆）。
3. **e_wrong_span_gold_file** -> `s_proxy_positive`（同 gold 文件 support shape）。
4. **同 gold 文件上 gold span 的邻接**（在 gold span 边界 +/-5 行内，无重叠）->
   `s_proxy_positive`（确定性邻接 support shape；不输出距离）。
5. **其他** -> `s_proxy_none`。

S-proxy 类别：`s_proxy_positive`、`s_proxy_none`、`s_proxy_uncertain`、
`s_proxy_not_evaluated_for_e_positive`。`s_proxy_uncertain` 为完整性定义；保守流
程在当前 smoke 中不输出它。

## CLI

```bash
python3 -m py_compile eval/d5a_automated_es_calibration.py
python3 eval/d5a_automated_es_calibration.py --self-test
python3 eval/d5a_automated_es_calibration.py \
    --out artifacts/d5a_automated_es_calibration/\
d5a_automated_es_calibration_report.json
# CLI 覆盖（默认：已提交 r14 sanity 固定数据 + target/debug/openlocus）：
python3 eval/d5a_automated_es_calibration.py \
    --tasks fixtures/r14/tasks/sanity.jsonl \
    --labels fixtures/r14/labels/sanity.jsonl \
    --openlocus target/debug/openlocus \
    --cwd . \
    --candidate-limit 50 \
    --out /tmp/d5a_smoke_report.json
```

默认模式：写入已提交的公开仅聚合 artifact（如省略 `--out`，使用默认输出路径）。默
认模式按方法调用 `eval/run_retrieval.py`，将输出写入临时 `/tmp/d5a_retrieval_*`
目录并读取这些临时输出（绝不提交）。

CLI 参数：`--self-test`、`--out`、`--tasks`、`--labels`、`--openlocus`、`--cwd`、
`--candidate-limit`。未知/类似私有的参数会被拒绝，并返回固定通用消息
`invalid arguments`，不回显私有路径或 basename（SafeArgumentParser 模式）。

`--self-test` 使用内存合成 predictions/labels，无需外部 openlocus；覆盖所有 span
重叠场景、冲突场景、S-proxy 场景、forbidden scanner（拒绝 + 通过）、no-claim 标志
不变式与聚合分母一致性。

### 守卫要求

1. 默认模式读取已提交的 r14 sanity 固定数据（已提交标签；不采集新人工标签）。
2. Retrieval 输出仅在 `/tmp` 下临时生成，绝不提交
   （`raw_retrieval_outputs_committed=false`、
   `transient_retrieval_outputs_only=true`）。
3. 已提交 artifact 仅包含聚合 counts/rates；无 per-candidate 行、无 path、无
   span、无 snippet、无 content_sha、无 query、无 gold 标签、无 hard-negative 标
   签、无 task/repo ID、无行级数据。
4. 严格故障关闭 forbidden scanner 在写入 JSON artifact 前立即执行
   （`_enforce_no_forbidden`）。
5. 自测失败会拒绝成功的 artifact 生成（`_refuse_on_self_test_failure`）。

## Artifact 身份（默认已提交 artifact）

位于
`artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`
的已提交 artifact 是公开仅聚合 smoke artifact。身份 / 边界字段：

- `schema_version` = `d5a_automated_es_calibration.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`
- 安全 true 标志（恰好这些，全部为 true）：
  `aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`、
  `automated_e_s_calibration_smoke_claimed`、`automated_d5a_path_active`、
  `uses_existing_committed_labels`、`self_test_executed`、
  `transient_retrieval_outputs_only`。
- 无声明 / 无运行时变更标志（全部为 false）：
  `automated_e_s_calibration_claimed`、
  `human_e_s_calibration_claimed`、`new_human_labels_collected`、
  `human_reference_audit_claimed`、`promotion_ready`、
  `default_should_change`、`evidencecore_semantics_changed`、
  `runtime_clean_general_algorithm_claimed`、
  `downstream_agent_value_proven`、
  `external_benchmark_performance_claimed`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`model_calls_changed`、`backend_changed`、
  `default_policy_changed`、`true_e_s_calibration_claimed`、
  `raw_predictions_committed`、`raw_retrieval_outputs_committed`、
  `per_candidate_rows_emitted`、`public_release_gate_passed`、
  `d5_human_reference_calibration_unblocked`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- `input_summary`：`fixture_name`（`r14_sanity`）、`task_count`、
  `label_source_category_counts`（按 `label_quality` 聚合 counts）、
  `methods_evaluated`（`[regex, bm25, symbol, rrf]`）。Label-source 类别键仅允许
  显式 bucket：`human_reviewed`、`mined`、`mined_high_confidence`、`unknown`，
  以及折叠 fallback `other_unapproved_label_source_category`。未批准的逐行来源
  字符串绝不会作为公开 artifact 键输出。
- `retrieval_summary`：`methods_attempted`、`methods_succeeded`、
  `candidate_count_total`、`retrieval_invocation`
  （`run_retrieval_subprocess`）、`retrieval_output_location`
  （`tmp_only_transient`）、`raw_retrieval_outputs_committed=false`。
- `automated_label_summary`：`candidates_labeled_total`、
  `candidates_unlabeled_total`（始终为 0）、`e_label_categories`、
  `s_proxy_label_categories`、`e_label_category_counts`、
  `s_proxy_label_category_counts`、聚合 E 标签 rate 与 S-proxy rate。
- `method_aggregate_metrics`：按方法的 dict 列表，包含 `candidates_seen`、各类
  别 count、各类别 rate，以及 `denominators` 对象（`candidate_total`、
  `e_label_denominator`、`s_label_denominator`）。无 per-candidate 行、无 path、
  无 span。
- `e_label_categories` 与 `s_proxy_label_categories` 是精确契约容器（仅允许
  short-token 白名单）。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写 JSON 前故障关闭）。

## Forbidden scanner（公开，故障关闭）

严格 forbidden-output scanner 在写入公开 JSON 前故障关闭执行。拒绝禁止的 dict 键
（`task_id`、`repo_id`、`repo`、`path`、`file`、`span`、`start_line`、`end_line`、
`content_sha`、`snippet`、`candidate_text`、`query`、`query_text`、`prompt`、
`response`、`model_output`、`label`、`labels`、`raw_label`、`annotation_row`、
`rater_id`、`annotator_id`、`packet_ref`、`packet_id`、`private_record_ref`、
`candidate_ref`、`candidate`、`per_row_hash`、`row_hash`、`provider_payload`、
`api_key`、`agreement_metric`、`kappa`、`confidence_interval`、`ci_value`、
`ci_lower`、`ci_upper`、`gold`、`gold_span`、`gold_spans`、`hard_negative`、
`hard_negatives`、`evidence`、`candidate_row`、`predictions`、`retrieval_output`、
`retrieval_outputs` 等）出现在任何位置，并拒绝值模式：任何 URL（无 URL 白名单）、
32/40/64 字符十六进制摘要、类似密钥的字符串、路径形式 `src/foo.rs` 与
`/private/foo.jsonl`、多行字符串、原始 JSON 片段、原始行范围 `12-34`，以及自测
sentinel。

契约容器（`methods_evaluated`、`methods_attempted`、`methods_succeeded`、
`e_label_categories`、`s_proxy_label_categories`）是**精确字符串白名单**：仅允许
已批准 short token（方法名 `regex`/`bm25`/`symbol`/`rrf`、fixture 类别
`r14_sanity`、E 标签类别 token、S-proxy 类别 token，以及 retrieval 类别 token
`run_retrieval_subprocess`/`tmp_only_transient`）在其中出现。任意短字符串（如
`compute_loss` 或私有文本）即使在契约容器内也被拒绝（无过宽容器豁免）；敏感字段名
（`content_sha`、`query_text`、`candidate`、`gold`、`hard_negative`、`evidence`、
`predictions`、`retrieval_output` 等）即使在契约容器内也被拒绝，且作为键在任何位
置也被拒绝。

`label_source_category_counts` 也使用键白名单：已批准的 committed fixture 元数据类别
可作为 key 计数；任何未批准类别会在公开 artifact 输出前折叠为
`other_unapproved_label_source_category`。Scanner 会拒绝该 count 容器下未批准的动态键。

Scanner 仅对最终公开聚合 artifact 执行。内部 raw predictions（包含
`path`/`start_line`/`end_line`/`content_sha`/`query` 等）仅临时读入内存，绝不扫描，
绝不提交。

## 自测

- Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
- 安全 true 标志（全部为 true）；无声明 / 无运行时变更 false 标志（全部为
  false）。
- 自动 E 标签流程：gold 重叠 -> `e_positive`；hard-negative 重叠 ->
  `e_hard_negative`；冲突重叠（gold 与 hard-negative）-> `conflict_uncertain`；
  同 gold 文件错 span -> `e_wrong_span_gold_file`；非 gold 文件 ->
  `e_negative_non_gold_file`；无效 / 源缺失 / 行范围错误 -> `e_uncertain`；缺
  失标签绝不作为负样本。
- S-proxy 标签流程：E-positive -> `s_proxy_not_evaluated_for_e_positive`；
  `e_wrong_span_gold_file` -> `s_proxy_positive`；gold span 邻接 ->
  `s_proxy_positive`；`e_hard_negative`/`conflict_uncertain`/`e_uncertain` ->
  `s_proxy_none`；非 gold 文件且远离 gold -> `s_proxy_none`。
- 聚合分母一致性：denom > 0 时 E 标签 rate 之和为 1.0（允许浮点误差）；E count 之
  和等于 `candidates_seen`；S count 之和等于 `candidates_seen`；
  `candidates_seen` 与三个分母一致。
- Forbidden scanner 拒绝：所有禁止的 dict 键；URL 值；32/40/64 字符十六进制摘要
  值；secret sentinel 值；类似密钥值；路径形式值；前导斜杠路径值；jsonl 路径值；
  多行值；原始 JSON 片段值；行范围值；冒号行范围值；契约容器内未批准字符串；契约
  容器内敏感字段名；契约容器内 URL。
- Forbidden scanner 通过：`methods_evaluated` 内已批准方法 token；
  `e_label_categories` 内已批准 E 标签 token；`s_proxy_label_categories` 内已
  批准 S-proxy token。
- Label-source 键加固：批准的 `mined` 被保留；未批准的 label-quality sentinel
  折叠为固定 fallback 且不输出原始字符串；scanner 拒绝
  `label_source_category_counts` 下未批准的动态键。
- 故障关闭生成：干净公开 report 不抛异常；泄漏公开 report 抛 SystemExit；自测失
  败拒绝 artifact 生成（失败时抛异常，通过时不抛）；自测失败不带成功状态。
- 公开 artifact 自扫描干净（无任何禁止键）。
- CLI 参数表面：`--self-test`、`--out`、`--tasks`、`--labels`、`--openlocus`、
  `--cwd`、`--candidate-limit` 是仅有的选项（加 `-h`/`--help`）。

## 验证

```text
python3 -m py_compile eval/d5a_automated_es_calibration.py    => PASS
python3 eval/d5a_automated_es_calibration.py --self-test      => PASS (157/157 checks)
python3 eval/d5a_automated_es_calibration.py \
  --out artifacts/d5a_automated_es_calibration/\
d5a_automated_es_calibration_report.json                     => PASS
  (status: automated_es_calibration_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_r14_retrieval_smoke, phase: D5-A0,
   methods_succeeded: [regex, bm25, symbol, rrf],
   candidate_count_total: 3152,
   uses_existing_committed_labels: true,
   automated_d5a_path_active: true,
   new_human_labels_collected: false,
   human_e_s_calibration_claimed: false,
   automated_e_s_calibration_claimed: false,
   raw_retrieval_outputs_committed: false,
   per_candidate_rows_emitted: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   model_calls_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   runtime_clean_general_algorithm_claimed: false,
   downstream_agent_value_proven: false,
   external_benchmark_performance_claimed: false,
   d5_human_reference_calibration_unblocked: false,
   public_release_gate_passed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## 注意事项

- D5-A0 是公开仅聚合 smoke artifact。它是 eval/诊断专用。它**不**改变运行时、
  retriever、pack、model、backend 或默认策略；也**不**改变 EvidenceCore 语义。它
  不是基准测试结果，不是下游 agent 价值声明，不是 runtime-clean 通用算法声明，
  不是 OOD 时间性声明，也不是 QuIVer 系统声明。
- D5-A0 使用已提交的 r14 sanity 标签（gold spans + hard negatives）派生**自动 E
  标签**与**确定性 S-proxy 标签**。这些**不是**真实人工/手动 E/S 分数，也**不
  是** D3 dual-rubric E/S 分数。它们是从已提交 span 标签派生的 smoke-only 聚合信
  号。
- D5-A0 **不**采集新人工/手动标签，**不**审计人工参考标签，**不**声明 true E/S
  校准，**不**通过任何公开发布门，也**不**解锁 D5-H / 人工参考 / 人工校准声明或
  default/policy/公开发布声明。D5-H / 人工参考 / 人工校准审计在真实人工/手动
  true E/S 标签采集前仍属 out of scope/不可用；D5-A 自动实证路径已激活并继续。
- D5-A0 按方法调用 `eval/run_retrieval.py`，输出写入临时 `/tmp/d5a_retrieval_*`
  目录并读取这些临时输出（绝不提交）。已提交 artifact 仅包含聚合 counts/rates；
  无 per-candidate 行、无 path、无 span、无 snippet、无 content_sha、无 query、
  无 gold 标签、无 hard-negative 标签、无 task/repo ID、无行级数据。
- 聚合指标是 smoke-only，取决于 (a) 已提交 r14 sanity 固定数据形状（gold spans
  + hard negatives）、(b) 四种固定 retrieval 方法（regex、bm25、symbol、rrf）、
  (c) 上述确定性 E/S 标签流程。它们**不**可跨不同 fixture、标签集、方法或流程比
  较，也**不**是基准测试性能声明。
- `e_uncertain` 仅对无效/源缺失 candidate 输出；在当前 r14 sanity smoke 中，所
  有 retrieval 输出结构上有效，因此 `e_uncertain_count=0` 是预期的。这**不**意味
  每个 candidate 都正确；它只意味着每个 candidate 都有有效 path 与行范围。
- `s_proxy_uncertain` 为完整性定义，但保守流程在当前 smoke 中不输出它。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）保持
  true；smoke-claimed / 使用已提交标签 / D5-A 路径已激活标志
  （`automated_e_s_calibration_smoke_claimed`、`automated_d5a_path_active`、
  `uses_existing_committed_labels`、`self_test_executed`、
  `transient_retrieval_outputs_only`）是仅有的额外 true 标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` 已更新以澄清：D5-H / 人工参考 / 人工校准在人
  工标签到位前仍属 out of scope，而 D5-A 自动实证路径已激活；不改变任何
  promotion/default/runtime 声明。
