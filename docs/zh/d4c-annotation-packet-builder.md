# D4c 标注 Packet 构建夹具（公开夹具 / 无 Packet 产物）

## 范围与声明边界

D4c 是**标注 packet 构建夹具**公开产物。它通过构建带空标签槽的本地/
私有标注 packet，将私有源记录桥接到未来的人工标注。**默认提交的产物
是公开夹具 / 无 packet 产物**，而非真实 packet 构建结果。D4c 是 D4b
（冻结真实标签 bundle 输入契约）之后的衔接。D4c 的桥接为：

```text
private records -> human annotation packets -> D4b true-label bundle -> D5 aggregate release candidate
```

D4c **不**采集标签、**不**填充标签槽、**不**创建 D4b 真实标签 bundle、
**不**运行 packet->bundle 转换器、**不**计算校准指标、**不**进行
model/LLM 标注、默认**不**读取私有源记录、**不**输出 provider payload/
API key/secret/model output，也**不**改变运行时行为、检索器、pack、
模型、后端、默认策略或 EvidenceCore 语义。

- 声明级别：`annotation_packet_builder_harness_only`。
- D4b bundle schema target：`d4b_true_label_bundle_v1`（仅目标；D4c
  不运行转换器）。
- 状态：`blocked_no_private_source_records_available_or_no_packets_built`；
  模式 `public_harness_no_packets`；阶段 `D4c`。

D4c 是**仅评测/诊断**。它**不是**基准结果、**不是**下游 agent 价值
声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间维度
声明，也**不是** QuIVer 系统声明。

- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D4c 不输出 EvidenceCore 记录，也不改变其语义。
- D4c 默认不读取私有源记录：`private_source_records_read=false`、
  `private_source_records_persisted=false`、
  `annotation_packets_built=false`、`annotation_packets_persisted=false`、
  `private_packet_output_written=false`、
  `private_input_path_emitted=false`、`packet_output_path_emitted=false`、
  `packet_ids_emitted=false`、`task_ids_emitted=false`、
  `repo_ids_emitted=false`、`paths_or_spans_emitted=false`、
  `snippets_emitted=false`、`content_sha_emitted=false`、
  `query_text_emitted=false`、`candidate_text_emitted=false`、
  `private_packet_output_contains_sensitive_context=false`。
- D4c 不填充标签也不创建 bundle：
  `private_packet_schema_validated=false`、
  `private_packet_labels_filled=false`、`labels_collected=false`、
  `true_label_bundle_created=false`、
  `d4b_true_label_bundle_validated=false`、
  `d4b_bundle_converter_run=false`、
  `calibration_metrics_computed=false`、
  `model_or_llm_labeling_performed=false`、
  `provider_payloads_emitted=false`、
  `annotation_instructions_emitted=false`。D4c 不通过任何发布门：
  `true_e_s_calibration_claimed=false`、
  `public_release_gate_passed=false`。

## 核心边界：D4c 默认是 blocked / 无 packet

- **默认提交的 D4c 产物**是公开夹具 / 无 packet 产物。其状态为
  `blocked_no_private_source_records_available_or_no_packets_built`。
  它**不**读取私有源记录、**不**构建 packet、**不**持久化 packet、
  **不**填充标签、**不**创建 D4b bundle、**不**运行转换器、**不**
  计算校准、**不**进行 model/LLM 标注，也**不**通过任何公开发布门。
- D4c 不得声称构建了标注 packet，除非显式提供私有源记录并在本地
  `/tmp` 运行。
- 可选的私有 packet 构建模式仅本地且仅 `/tmp`；任何私有输出绝不提交。

### D4c -> 人工标注 -> D4b bundle 关系

D4c 从私有源记录构建标注 packet（含空标签槽）。人工 rater 随后填充空
槽。一个独立的 D4b 转换器（人工转录或本地 converter）将已填充的 packet
映射为 `d4b_true_label_bundle_v1`。D4c **不**运行该转换器、**不**
创建 bundle、**不**采集或声称标签。`d4b_mapping_contract` 记录转换器
未运行且未创建真实标签 bundle。

## CLI

```bash
python3 -m py_compile eval/d4c_annotation_packet_builder.py
python3 eval/d4c_annotation_packet_builder.py --self-test
python3 eval/d4c_annotation_packet_builder.py \
    --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json
```

默认模式（无 `--input`、无 `--allow-private-source-records`）：写入已提交
的公开夹具 / 无 packet 产物（若省略 `--out` 则用默认输出路径）。

私有 packet 构建模式仅是显式守卫夹具（仅 `/tmp`，绝不提交）：

```bash
# 不提交；仅 /tmp（私有 packet 构建器）：
python3 eval/d4c_annotation_packet_builder.py \
    --allow-private-source-records \
    --input /tmp/private_source_records.json \
    --out /tmp/d4c_annotation_packets.json
```

CLI 参数：`--self-test`、`--out`、`--allow-private-source-records`、
`--input`。

CLI 守卫矩阵（全部在任何输入被打开前校验）：

- `--input` 无 `--allow-private-source-records` => exit 2（无路径/
  basename 泄露）。
- `--allow-private-source-records` 无 `--input` => exit 2。
- `--allow-private-source-records` 有 `--input` 但无显式 `--out` =>
  exit 2。
- `--allow-private-source-records` 以已提交产物路径作为 `--out` =>
  读取前 exit 2。
- `--allow-private-source-records` 以非 `/tmp` 的 `--out` => 读取前
  exit 2。
- `--allow-private-source-records --input <path> --out /tmp/...` =>
  接受为仅本地 packet 构建。
- 强解析 `/tmp` 守卫：解析 `/tmp`；在读取私有输入前解析输出父目录；
  拒绝父 symlink 逃逸 `/tmp`（如 `/tmp/link_to_repo/out.json`）；拒绝
  已存在的输出文件 symlink；拒绝解析后逃逸 `/tmp` 的目标。所有输出
  守卫在输入被打开或 stat 前运行（validate-before-read）。
- 私有模式成功 stdout **不得**打印确切的 `/tmp` 输出路径。
- 私有模式错误**不得**打印原始异常、输入/输出路径/basename、原始 JSON
  或私有文本。固定消毒错误为：
  `error: failed to load private source records (schema/privacy/parse
  error; details suppressed)`。

## 产物身份（默认已提交产物）

已提交的产物位于
`artifacts/d4c_annotation_packet_builder/d4c_annotation_packet_builder_report.json`，
是公开夹具 / 无 packet 产物。身份 / 边界字段：

- `schema_version` = `d4c_annotation_packet_builder_harness.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`d4b_bundle_schema_target`
- 默认 false 标志（全为 false）：`private_source_records_read`、
  `private_source_records_persisted`、`annotation_packets_built`、
  `annotation_packets_persisted`、`private_packet_output_written`、
  `packet_output_path_emitted`、`private_input_path_emitted`、
  `packet_ids_emitted`、`task_ids_emitted`、`repo_ids_emitted`、
  `paths_or_spans_emitted`、`snippets_emitted`、`content_sha_emitted`、
  `query_text_emitted`、`candidate_text_emitted`、
  `private_packet_output_contains_sensitive_context`、
  `private_packet_schema_validated`、`private_packet_labels_filled`、
  `labels_collected`、`true_label_bundle_created`、
  `d4b_true_label_bundle_validated`、`d4b_bundle_converter_run`、
  `calibration_metrics_computed`、`model_or_llm_labeling_performed`、
  `provider_payloads_emitted`、`annotation_instructions_emitted`、
  `true_e_s_calibration_claimed`、`public_release_gate_passed`。
- 夹具/控制标志（恰好六个，全为 true）：
  `private_packet_builder_harness_available`、
  `private_cli_guard_validated`、`tmp_output_resolved_guard_validated`、
  `sanitized_error_guard_validated`、`packet_schema_contract_defined`、
  `d4b_mapping_contract_defined`。
- no-claim / no-runtime-change 标志（全为 false）：`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `model_calls_changed`、`backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。
- `private_source_record_schema_contract`：category-only 契约
  （schema `d4c_private_source_records_v1`、`private_only=true`、
  `may_contain_sensitive_context=true`）。
- `packet_schema_contract`：schema `d4c_annotation_packet_v1`、
  `private_only=true`、`may_contain_sensitive_context=true`、
  `required_label_slots` = `[e_score, s_score, bucket, citation_valid,
  rater_pair_present, adjudicated]`、`target_bundle_schema=
  d4b_true_label_bundle_v1`。
- `d4b_mapping_contract`：`target_bundle_schema=d4b_true_label_bundle_v1`、
  `packet_label_slots` = 同六个槽、
  `packet_to_bundle_requires_manual_transcription_or_local_converter=true`、
  `converter_not_run=true`、`true_label_bundle_created=false`。
- `private_packet_builder_harness`：仅 `/tmp`、opt-in、不提交、不填充
  标签、不创建 D4b bundle、不运行转换器、不声称校准。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## 私有源记录契约（仅本地）

私有源记录是 JSON 对象，schema 为 `d4c_private_source_records_v1` 且
含 `records` 列表。每条记录恰好需要：`private_record_ref`、
`candidate_ref`、`query_text`、`candidate_text`、
`candidate_bucket_hint`、`evidence`。`evidence` 条目恰好需要：`path`、
`start_line`、`end_line`、`content_sha`、`snippet`。
`candidate_bucket_hint` 必须是 `primary_evidence`/`dependency_support`/
`weak_candidates`/`abstained`/`unknown` 之一。`start_line`/`end_line`
为正整数且 `start_line <= end_line`。`content_sha` 为 32/40/64 位十六
进制。loader 拒绝未知键（如 `provider_payload`、`api_key`、`secret`、
`model_output`、`prompt_response`、labels/label 行）而非支持并剥离。
若畸形，固定消毒错误为：
`error: failed to load private source records (schema/privacy/parse
error; details suppressed)`。

## 私有 packet 输出契约（敏感上下文，仅 /tmp）

私有标注 packet **可**含人工标注所需的敏感上下文：

- 本地 packet ref / 本地私有 ref；
- query/candidate 文本；
- 路径、行 span、snippet、内容 hash；
- 标注说明；
- 空标签槽 `e_score`、`s_score`、`bucket`、`citation_valid`、
  `rater_pair_present`、`adjudicated`。

规则：

- 显式 `/tmp` 输出，绝不提交；
- 成功 stdout 不得打印确切路径；
- builder 不自动填充标签；标签槽必须为 null/空；
- 不创建 D4b bundle；
- 不计算 calibration/agreement/CI 指标；
- 不进行 model/LLM 标注；
- 不含 provider/API secret 或 provider payload；
- packet 元数据/stdout/stderr 中不含确切输入/输出路径或 basename。
- 安全本地守卫标志：`private_packet_output=true`、
  `public_artifact=false`、`do_not_commit=true`、
  `labels_filled_by_builder=false`、`d4b_bundle_created=false`、
  `d4b_bundle_converter_run=false`、
  `true_label_bundle_created=false`、
  `calibration_metrics_computed=false`、
  `model_or_llm_labeling_performed=false`。

bucket hint 仅可作为源 `candidate_bucket_hint` 或指引出现，不得作为已
填充的 `bucket` 标签槽。

## 扫描器分离（两套扫描器）

1. **公开产物扫描器**：严格、fail-closed。拒绝 task/repo ID、packet
   ID/ref、路径、span、snippet、content SHA、query/candidate 文本、
   标签、本地路径、hash、原始 JSON 片段、多行字符串、URL 及自测
   sentinel。字段名 token（如 `e_score`、`content_sha`）仅可作为值
   出现在显式契约字段名容器（`packet_schema_contract`、
   `d4b_mapping_contract`、`private_source_record_schema_contract`）
   内部，其余位置一律拒绝。它不会被削弱以让私有 packet 通过。
2. **私有 packet 守卫**：不同。仅允许在私有 packet 中出现路径/snippet/
   内容 hash/query/candidate 文本/标注说明/空标签槽；强制私有模式
   `/tmp` 位置、packet schema（`d4c_annotation_packet_v1`）、空标签
   槽、无已填充 E0/E1/E2/S0/S1/S2 值、无 D4b bundle、无转换器、无
   校准、无 model 标注，并拒绝 provider secret/API key/provider
   payload/model output。

## 禁止扫描器（公开，fail-closed）

严格禁止输出扫描器在写入公开 JSON 前 fail-closed 运行。拒绝禁止的 dict
键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
`start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
`query`、`query_text`、`prompt`、`response`、`model_output`、
`label`、`labels`、`raw_label`、`annotation_row`、`rater_id`、
`annotator_id`、`packet_ref`、`packet_id`、`private_record_ref`、
`candidate_ref`、`label_slots`、`annotation_instructions`、`e_score`、
`s_score`、`bucket`、`provider_payload`、`api_key` 等），并拒绝值模式：
任何 URL（无 URL 白名单）、32/40/64 位十六进制摘要、secret-like 字符串、
路径式 `src/foo.rs` 与 `/private/foo.jsonl`、多行字符串、原始 JSON
片段、原始行范围 `12-34` 及自测 sentinel。仅允许安全的协议/身份/band
字符串（`d4c_annotation_packet_builder_harness.v1`、`D4c`、
`d4b_true_label_bundle_v1` 等）。契约字段名容器使用精确字符串白名单，
不是通用 schema-container 豁免。

## 自测

- 所有默认 false/true 标志如上（默认产物无 packet、无读取、无标签、无
  指标、无声明；六个夹具标志为 true；诊断标志为 true）。
- 产物身份字段（`schema_version`、`claim_level`、`status`、`mode`、
  `phase`、`d4b_bundle_schema_target`）。
- 公开契约已定义（`private_source_record_schema_contract`、
  `packet_schema_contract`、`d4b_mapping_contract`）。
- 公开扫描器 fail-closed（禁止键 + 值模式）。
- 契约白名单：批准的 schema 标识符与 label-slot token 仅可作为值出现在
  显式契约容器内（`packet_schema_contract.required_label_slots`）；
  `compute_loss` 或私有文本等任意字符串即使在契约容器内也会被拒绝；
  字段名作为键在契约外被拒绝（`{"e_score":"E2"}`、
  `{"content_sha":"abc"}`、`{"query_text":"..."}`、
  `{"packet_ref":"..."}`），作为值在契约外也被拒绝。
- 私有源记录 schema 校验：有效记录通过；未知 schema/键、
  provider_payload/api_key/secret/model_output/prompt_response/labels、
  缺字段、非法 bucket hint、空 query_text、start_line>end_line、非正
  整数行、非法 content_sha、多余 evidence 键、空 evidence 被拒绝。
- CLI 守卫矩阵包括 validate-before-read、已提交输出读取前拒绝、非
  `/tmp` 读取前拒绝、input 无 allow 读取前拒绝。
- 解析 `/tmp` symlink 逃逸拒绝（父 symlink 逃逸与已存在输出文件
  symlink）。
- 带敏感 basename + sentinel 的消毒错误（stdout/stderr/输出无泄露）。
- 合成私有输入（含 path/snippet/content_sha）写入 `/tmp` packet，含
  敏感上下文、标签槽为空、无已填充 E/S 值、无 D4b bundle、无校准、无
  model 标注、元数据/stdout 中无确切输入/输出路径或 basename，且输出
  不提交。
- 私有 packet 输出仅在 `/tmp` 私有模式含敏感上下文，公开产物中绝不
  含。
- 私有 packet 守卫拒绝已填充标签槽、provider payload 键及 secret-like
  值；干净 packet 通过。
- 禁止扫描器 fail-closed 且自测失败时拒绝生成。

## 校验

```text
python3 -m py_compile eval/d4c_annotation_packet_builder.py    => PASS
python3 eval/d4c_annotation_packet_builder.py --self-test      => PASS (233/233 项检查)
python3 eval/d4c_annotation_packet_builder.py \
  --out artifacts/d4c_annotation_packet_builder/\
d4c_annotation_packet_builder_report.json                     => PASS
  (status: blocked_no_private_source_records_available_or_no_packets_built,
   forbidden_scan: pass, self_test_passed: true,
   private_source_records_read: false,
   annotation_packets_built: false,
   private_packet_output_written: false,
   private_packet_output_contains_sensitive_context: false,
   labels_collected: false,
   true_label_bundle_created: false,
   d4b_bundle_converter_run: false,
   calibration_metrics_computed: false,
   model_or_llm_labeling_performed: false,
   provider_payloads_emitted: false,
   public_release_gate_passed: false,
   private_packet_builder_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   packet_schema_contract_defined: true,
   d4b_mapping_contract_defined: true,
   mode: public_harness_no_packets, phase: D4c,
   d4b_bundle_schema_target: d4b_true_label_bundle_v1)
/tmp 私有 packet 构建（合成源记录）                                => PASS
  (annotation_packets_built=true,
   private_packet_output_contains_sensitive_context=true,
   private_packet_guard: pass, 标签槽全为 null,
   敏感上下文（path/snippet/content_sha/query_text/
   candidate_text/annotation_instructions/packet_ref）存在于
   /tmp 输出但不在公开产物中，
   元数据/stdout/stderr 中无输入/输出路径或 basename,
   无 provider secret、无 D4b bundle、无转换器、无校准、无
   model 标注、不提交)
CLI 守卫矩阵（input 无 allow、allow 无 input、无显式 out、
  已提交输出、非 /tmp 输出）                                       => PASS (全部 exit 2)
解析 /tmp symlink 逃逸守卫（父 symlink、
  已存在输出文件 symlink）                                         => PASS (exit 2)
畸形私有输入消毒错误                                               => PASS (exit 2，无泄露)
python3 scripts/validate_docs_i18n.py                            => PASS
git diff --check                                                 => PASS
```

## 注意事项

- D4c 仅标注 packet 构建夹具公开产物。它仅评测/诊断。它**不**改变
  运行时、检索器、pack、模型、后端或默认策略；它**不**改变
  EvidenceCore 语义。它**不是**基准结果、**不是**下游 agent 价值
  声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间维度
  声明，也**不是** QuIVer 系统声明。
- D4c 默认是 blocked / 无 packet。默认提交产物**不**读取私有源记录、
  **不**构建 packet、**不**持久化 packet、**不**填充标签、**不**
  创建 D4b bundle、**不**运行转换器、**不**计算校准、**不**进行
  model/LLM 标注，也**不**通过任何公开发布门。夹具/控制标志仅对已
  校验的夹具/控制为 true，**并非**任何真实 packet 构建或标签声明。
- D4c **不是**标签采集、**不是** D4b 真实标签 bundle 创建、**不是**
  校准、**不是**发布就绪。它为人工 rater 构建带空标签槽的 packet；
  它不运行 packet->bundle 转换器。
- 私有 packet 构建模式仅 `/tmp` 且**绝不**提交。与 D4b 不同，D4c 私有
  packet 输出**可**有意含人工标注所需的敏感上下文（本地 packet ref、
  query/candidate 文本、evidence path/span/snippet/content_sha、标注
  说明、空标签槽），但**仅**在 `/tmp` 下。默认公开产物绝不读取私有
  记录且不含任何 packet/私有内容。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、
  `not_evidence`）保持为 true；六个夹具/控制标志是仅有的 true 控制
  标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4c 是夹具/blocked 产物；
  结论无变化）。
