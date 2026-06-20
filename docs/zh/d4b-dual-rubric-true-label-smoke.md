# D4b 双评分真实标签 Smoke 测试夹具（公开夹具 / 无标签产物）

## 范围与声明边界

D4b 是**真实标签 smoke 测试夹具**公开产物。它冻结本地/私有真实
E-score / S-score 标签 bundle 的输入契约，并强化执行控制。**默认提交的
产物是公开夹具 / 无标签产物**，而非真实真实标签 smoke 结果。D4b 是 D4a
（校验执行门 / 试运行控制平面）之后的衔接。

D4b **不**伪造标签、**不**接受代理/合成/LLM 标签作为真实标签、默认**不**
读取私有真实标签 bundle、**不**计算真实校准指标、**不**衡量 inter-rater
agreement、**不**声称真实/代理校准，也**不**改变运行时行为、检索器、
pack、模型、后端、默认策略或 EvidenceCore 语义。

- 声明级别：`true_label_bundle_execution_harness_only`。
- 评分版本：`d3_true_dual_rubric_label_protocol_v1`（D3 协议已校验；D4b
  不重新定义评分）。
- 状态：`blocked_no_true_label_bundle_available`；模式
  `public_harness_no_labels`；阶段 `D4b`。

D4b 是**仅评测/诊断**。它**不是**基准结果、**不是**下游 agent 价值
声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间维度
声明，也**不是** QuIVer 系统声明。

- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D4b 不输出 EvidenceCore 记录，也不改变其语义。
- D4b 不采集标签：`labels_collected=false`、
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_measured=false`、
  `confidence_intervals_computed=false`。
- D4b 默认不读取真实标签 bundle：`true_label_bundle_read=false`、
  `true_label_bundle_validated=false`、
  `true_label_bundle_persisted=false`、`raw_label_rows_emitted=false`、
  `private_input_path_emitted=false`、`private_output_path_emitted=false`、
  `private_output_committed=false`、`exact_private_counts_emitted=false`。
- D4b 不声称校准：`true_e_s_calibration_claimed=false`、
  `local_private_true_label_smoke_executed=false`、
  `synthetic_labels_accepted_as_true=false`、
  `proxy_labels_accepted_as_true=false`、
  `llm_labels_accepted_as_true=false`、
  `model_assisted_labels_allowed=false`。D4b 不通过任何发布门：
  `public_release_gate_passed=false`、
  `real_label_bundle_gate_passed=false`。

## 核心边界：D4b 默认是 blocked / 无标签

- **默认提交的 D4b 产物**是公开夹具 / 无标签产物。其状态为
  `blocked_no_true_label_bundle_available`。它**不**采集标签、**不**
  读取真实标签 bundle、**不**校验任何 bundle 为真实标签、**不**计算校准
  指标、**不**衡量 inter-rater agreement、**不**声称真实/代理校准，也
  **不**通过任何公开发布/真实 bundle 门。
- D4b 不得声称执行了真实标签 smoke，除非显式提供并在本地 `/tmp` 运行
  一个真实人工/手动真实 E/S 标签 bundle。**合成、代理与 LLM 标签不作为
  真实标签被接受。**它们仅可出现在自测与可选的私有模式夹具测试中，且
  `local_private_true_label_smoke_executed=false`。
- 可选的私有 smoke 模式仅本地且仅 `/tmp`；任何私有输出绝不提交。

### `local_private_true_label_smoke_executed` 可为 true 前的最低真实输入

`local_private_true_label_smoke_executed` 仅在本地私有运行（绝不提交）且
以下**全部**满足时才可为 `true`：

- 人工/手动真实 E/S 标签（bundle `label_source` 恰为
  `human_manual_true_e_s`）；
- 评分为 D3 双评分协议（`d3_true_dual_rubric_label_protocol_v1`）；
- `rater_count >= 2` 且经 adjudication；
- bundle 通过 D4b schema 契约（无 ID/路径/snippet/rater ID/原始行元数据/
  未知键）；
- 运行仅本地、位于 `/tmp`、无行输出。

任一条件失败，或运行使用 `--synthetic-harness-test`，则该标志为
`false`。**合成/代理/LLM 标签在任何标志下均不被接受为真实标签。**

## CLI

```bash
python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py
python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --out artifacts/d4b_dual_rubric_true_label_smoke/\
d4b_dual_rubric_true_label_smoke_report.json
```

默认模式（无 `--input`、无 `--allow-private-labels`）：写入已提交的公开
夹具 / 无标签产物（若省略 `--out` 则用默认输出路径）。

私有 smoke 模式仅是显式守卫夹具（仅 `/tmp`，绝不提交）：

```bash
# 不提交；仅 /tmp（真实本地私有 smoke）：
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --allow-private-labels --input /tmp/private_bundle.json \
    --out /tmp/d4b_smoke.json
# 不提交；仅 /tmp（合成夹具自测）：
python3 eval/d4b_dual_rubric_true_label_smoke.py \
    --allow-private-labels --synthetic-harness-test \
    --input /tmp/harness_bundle.json --out /tmp/d4b_harness.json
```

CLI 参数：`--self-test`、`--out`、`--allow-private-labels`、`--input`、
`--synthetic-harness-test`（默认 false）。

CLI 守卫矩阵（全部在任何输入被打开前校验）：

- `--input` 无 `--allow-private-labels` => exit 2（无路径/basename 泄露）。
- `--allow-private-labels` 无 `--input` => exit 2。
- `--allow-private-labels` 有 `--input` 但无显式 `--out` => exit 2。
- `--allow-private-labels` 以已提交产物路径作为 `--out` => 读取前
  exit 2。
- `--allow-private-labels` 以非 `/tmp` 的 `--out` => 读取前 exit 2。
- `--synthetic-harness-test` 无 `--allow-private-labels` => exit 2。
- `--allow-private-labels --input <path> --out /tmp/...` => 接受为仅本地
  smoke。
- 强解析 `/tmp` 守卫：解析 `/tmp`；在读取私有输入前解析输出父目录；
  拒绝父 symlink 逃逸 `/tmp`（如 `/tmp/link_to_repo/out.json`）；拒绝
  已存在的输出文件 symlink；拒绝解析后逃逸 `/tmp` 的目标。所有输出
  守卫在输入被打开或 stat 前运行。
- 私有模式成功 stdout **不得**打印确切的 `/tmp` 输出路径。
- 私有模式错误**不得**打印原始异常、输入/输出路径/basename、原始 JSON
  或标签文本。固定消毒错误为：
  `error: failed to load private true labels (schema/privacy/parse
  error; details suppressed)`。

## 产物身份（默认已提交产物）

已提交的产物位于
`artifacts/d4b_dual_rubric_true_label_smoke/d4b_dual_rubric_true_label_smoke_report.json`，
是公开夹具 / 无标签产物。身份 / 边界字段：

- `schema_version` = `d4b_dual_rubric_true_label_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`rubric_version`、
  `status`、`mode`、`phase`
- `d3_protocol_checked=true`、`d3_protocol_version=
  d3_true_dual_rubric_label_protocol_v1`、`d3_required_gates_present=true`
- 默认 false 标志（全为 false）：`labels_collected`、
  `true_label_bundle_read`、`true_label_bundle_validated`、
  `true_label_bundle_persisted`、
  `local_private_true_label_smoke_executed`、
  `calibration_metrics_computed`、`inter_rater_agreement_measured`、
  `confidence_intervals_computed`、`true_e_s_calibration_claimed`、
  `public_release_gate_passed`、`real_label_bundle_gate_passed`、
  `raw_label_rows_emitted`、`private_input_path_emitted`、
  `private_output_path_emitted`、`private_output_committed`、
  `exact_private_counts_emitted`、`synthetic_labels_accepted_as_true`、
  `proxy_labels_accepted_as_true`、`llm_labels_accepted_as_true`、
  `model_assisted_labels_allowed`。
- 夹具/控制标志（恰好这五个，全为 true）：
  `private_execution_harness_available`、`private_cli_guard_validated`、
  `tmp_output_resolved_guard_validated`、`sanitized_error_guard_validated`、
  `bundle_schema_contract_defined`。
- no-claim / no-runtime-change 标志（全为 false）：`promotion_ready`、
  `default_should_change`、`downstream_agent_value_proven`、
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `model_calls_changed`、`backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、
  `runtime_clean_general_algorithm_claimed`、`ood_temporal_supported`、
  `quiver_systems_supported`。
- 诊断标志（全为 true）：`aggregate_only_public_artifact`、
  `diagnostic_only`、`not_evidence`。
- `gate_thresholds`：`k_min=5`、`min_total_labels=50`、
  `min_rater_count=2`、`agreement_required=true`、
  `confidence_intervals_required=true`。
- `gate_category_names`：`primary_evidence`、`dependency_support`、
  `weak_candidates`、`abstained`。
- `bundle_schema_contract`：仅本地的真实标签 bundle 契约
  （schema `d4b_true_label_bundle_v1`、必需
  `label_source=human_manual_true_e_s`、拒绝
  `proxy`/`synthetic`/`llm`/`model_assisted`、允许的 bundle/label 键、
  E/S 等级、bucket 名）。
- `private_execution_harness`：仅 `/tmp`、opt-in、不提交、不声称校准。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写 JSON 前 fail-closed）。

## 私有真实标签 bundle 契约（仅本地）

真实本地私有真实标签 bundle 是一个 JSON 对象，其 `labels` 为人工/手动
真实 E/S 标注。loader 拒绝 ID/路径/snippet/rater ID/原始行元数据/未知键，
而非支持并剥离。仅允许以下 bundle 键：

- `schema` = `d4b_true_label_bundle_v1`
- `label_source` = `human_manual_true_e_s`（恰好；`proxy`/`synthetic`/
  `llm`/`model_assisted` 作为真实标签被拒绝）
- `rater_count`（int >= 2）
- `agreement_available`、`confidence_intervals_available`（布尔）
- `labels`（label 对象列表）

每个 label 对象必须**仅**含以下六个键：

- `e_score` 取 `E0`/`E1`/`E2`
- `s_score` 取 `S0`/`S1`/`S2`
- `bucket` 取 `primary_evidence`/`dependency_support`/`weak_candidates`/
  `abstained`
- `citation_valid`、`rater_pair_present`、`adjudicated`（布尔）

allowlist 之外的任何键（如 `rater_id`、`raw_label`、`annotation_row`、
`path`、`task_id`、`snippet`）触发 fail-closed。若格式错误，返回固定消毒
错误：
`error: failed to load private true labels (schema/privacy/parse error;
details suppressed)`。

## 私有输出规则（仅 band，绝不确切计数）

私有 smoke 输出 JSON 仅 `/tmp` 且绝不提交。它**不得**包含：输入/输出路径
或 basename、label 行、ID、路径、snippet、原始 E/S 行、rater ID、
annotation 行、行 hash、prompts/responses/model outputs，或确切真实私有
计数。因 bundle **输入**契约使用 `labels` 键，任何**输出**不得输出
`labels` 键（禁止扫描器拒绝它）。

私有输出以 band 与门布尔替代确切计数：

- `label_count_band`：`min_n_met`（>= 50 标签）/ `below_min_n`（< 50）。
- `bucket_count_bands`：每个固定 bucket，`k_met`（计数 >= k_min=5）/
  `below_k`（0 < 计数 < k_min，小单元抑制）/ `suppressed`
  （计数 == 0，空单元抑制）。
- `gate_results`：min-N / bucket-cell / second-rater / agreement / CI /
  overall 的布尔。
- `input_attestation_required=true`。
- 合成/内存夹具自测：`synthetic_harness_test=true` 且
  `local_private_true_label_smoke_executed=false`（即使 bundle 为
  human-manual 形状）。真实本地私有运行（无 synthetic 标志、
  `label_source=human_manual_true_e_s`、有效 schema）可设
  `local_private_true_label_smoke_executed=true` 仅本地（绝不提交）。

## 门逻辑（基于已校验的 human-manual bundle）

D4b 对已校验的 human-manual bundle 校验门阈值。它**不**计算校准指标、
inter-rater agreement 或置信区间。门（常量来自 D3）：

- min-N：`len(labels) >= 50`（`min_total_labels`）。
- small-cell 抑制：每个固定 bucket 单元 `n >= k_min`（5）；任何单元低于 5
  则 fail/suppress（band `below_k`）；空单元为 `suppressed`。
- second rater 必需：`rater_count >= 2`。
- agreement 必需：`agreement_available` 为 true。
- 置信区间必需：`confidence_intervals_available` 为 true。
- 全部条件满足 => overall 门 pass。

公开产物仅可包含门类别名、阈值、布尔、band 与合成自测聚合 pass/fail 计数。
**不得**包含来自任何私有输入的真实私有样本量或 label 行。

## 禁止扫描器（fail-closed）

严格的禁止输出扫描器在写任何 JSON 前 fail-closed 运行。拒绝禁止的 dict
键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
`start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
`query`、`prompt`、`response`、`model_output`、`label`、`labels`、
`raw_label`、`annotation_row`、`rater_id`、`annotator_id`、
`disagreement_example`、`per_row_hash` 等）于任何位置，并拒绝值模式：任何
URL（无 URL allowlist）、32/40/64 字符 hex 摘要、类 secret 字符串、类路径
`src/foo.py` 与 `/private/foo.jsonl`、多行字符串、原始 JSON 片段、原始
行范围 `12-34`，以及自测 sentinel。允许安全的门/协议/band 字符串
（`primary_evidence`、`k_min`、`D4b`、`min_n_met`、
`d3_true_dual_rubric_label_protocol_v1` 等）。

## 自测

- 全部上述默认 false/true 标志（默认产物无标签、无读取、无指标、无声明；
  五个夹具标志为 true）。
- D3 协议常量/门已校验（`k_min=5`、`min_total_labels=50`、
  `min_rater_count=2`、agreement/CI 必需）。
- bundle schema 契约已定义；proxy/synthetic/llm/model_assisted 标签源作
  为真实标签被拒绝。
- CLI 守卫矩阵，含 validate-before-read、已提交输出于读取前拒绝、
  非 `/tmp` 于读取前拒绝、`--synthetic-harness-test` 无 allow 被拒绝。
- 解析 `/tmp` symlink 逃逸拒绝（父 symlink 逃逸与已存在输出文件
  symlink）。
- 敏感 basename + `SECRET_LABEL_SENTINEL` 的消毒错误：stdout/stderr/
  输出中无泄露。
- 有效合成 human-manual 形状 bundle 仅作为夹具测试被接受
  （`synthetic_harness_test=true`、
  `local_private_true_label_smoke_executed=false`）。
- proxy/synthetic/LLM 源作为真实标签 smoke 被拒绝。
- 含 task_id/path/snippet/rater_id/raw_label/未知键的无效 bundle 被拒绝。
- 缺少第二 rater fail；N<50 fail；bucket 单元<5 fail/suppress
  （band `below_k`）；空 bucket 抑制（band `suppressed`）；缺 CI/agreement
  fail；对有效合成 human-manual 形状 bundle 全部门 pass。
- 私有输出无 label 行、ID、路径、basename、原始 E/S 行、确切计数或
  `labels` 键。
- 禁止扫描器 fail-closed，且自测失败时拒绝成功生成产物。

## 校验

```text
python3 -m py_compile eval/d4b_dual_rubric_true_label_smoke.py    => PASS
python3 eval/d4b_dual_rubric_true_label_smoke.py --self-test      => PASS (206/206 项检查)
python3 eval/d4b_dual_rubric_true_label_smoke.py \
  --out artifacts/d4b_dual_rubric_true_label_smoke/\
d4b_dual_rubric_true_label_smoke_report.json                     => PASS
  (status: blocked_no_true_label_bundle_available,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, true_label_bundle_read: false,
   true_label_bundle_validated: false,
   local_private_true_label_smoke_executed: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false,
   synthetic_labels_accepted_as_true: false,
   proxy_labels_accepted_as_true: false,
   llm_labels_accepted_as_true: false,
   model_assisted_labels_allowed: false,
   public_release_gate_passed: false,
   real_label_bundle_gate_passed: false,
   private_execution_harness_available: true,
   private_cli_guard_validated: true,
   tmp_output_resolved_guard_validated: true,
   sanitized_error_guard_validated: true,
   bundle_schema_contract_defined: true,
   mode: public_harness_no_labels, phase: D4b,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
/tmp 私有 smoke（合成 human-manual 形状 bundle）              => PASS
  (synthetic_harness_test=true,
   local_private_true_label_smoke_executed=false,
   输出/stdout/stderr 中无输入/输出路径、basename、原始标签、
   sentinel、确切计数或 labels 键)
/tmp 私有 smoke（基于合成 fixture 的真实模式 flag-path 测试）    => PASS
  (synthetic_harness_test=false,
   local_private_true_label_smoke_executed=true 仅本地，
   true_label_bundle_read=true, true_label_bundle_validated=true,
   不提交)
CLI 守卫矩阵（缺 allow/input/out、已提交输出、非 /tmp 输出、
  synthetic 无 allow）                                            => PASS (全部 exit 2)
解析 /tmp symlink 逃逸守卫（父 symlink、
  已存在输出文件 symlink）                                        => PASS (exit 2)
python3 scripts/validate_docs_i18n.py                            => PASS
git diff --check                                                 => PASS
```

## 注意事项

- D4b 仅真实标签 smoke 测试夹具公开产物。它仅评测/诊断。它**不**改变
  运行时、检索器、pack、模型、后端或默认策略；它**不**改变 EvidenceCore
  语义。它**不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，也**不是**
  QuIVer 系统声明。
- D4b 默认是 blocked / 无标签。默认提交产物**不**采集标签、**不**读取
  真实标签 bundle、**不**校验任何 bundle 为真实标签、**不**计算校准指标、
  **不**衡量 inter-rater agreement、**不**声称真实/代理校准，也**不**
  通过任何公开发布/真实 bundle 门。夹具/控制标志仅对已校验的夹具/控制
  为 true，**不**对任何真实校准为 true。
- 合成/代理/LLM 标签**不**被接受为真实标签。它们仅可出现在自测与可选的
  私有模式夹具测试中，且 `local_private_true_label_smoke_executed=false`。
- 私有 smoke 模式仅 `/tmp` 且**绝不**提交。它仅校验一个本地/私有真实
  标签-bundle 形状 JSON 的结构/门；它**不**计算或声称真实校准指标。真实
  本地私有运行可设 `local_private_true_label_smoke_executed=true` 仅本地，
  并在该本地输出中如实记录 `true_label_bundle_read=true` 和
  `true_label_bundle_validated=true`。上方校验命令使用合成 fixture 测试该
  flag path；它**不是**真实人工标签存在的公开证据。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持为 true；五个夹具/控制标志是仅有的 true 控制标志。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4b 是夹具/blocked 产物；
  结论无变化）。
