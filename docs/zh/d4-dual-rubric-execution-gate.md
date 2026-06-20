# D4a 双评分执行门 / 试运行（仅公开门产物）

## 范围与声明边界

D4a 是**执行门 / 试运行**公开产物。它校验未来本地/私有真实
E-score / S-score 标签校准（D4b）运行前所需的控制平面。D4a 是 D3
（仅预注册标签协议）之后的试运行衔接。

D4a **不**采集真实标签、默认**不**读取私有标签 bundle、**不**计算真实
校准指标、**不**衡量 inter-rater agreement、**不**声称真实/代理校准，
也**不**改变运行时行为、检索器、pack、模型、后端、默认策略或
EvidenceCore 语义。

- 声明级别：`dual_rubric_execution_gate_dry_run_only`。
- 评分版本：`d3_true_dual_rubric_label_protocol_v1`（D3 协议已校验；D4a
  不重新定义评分）。
- 状态：`execution_gate_ready_no_labels_collected`；模式
  `public_gate_dry_run`；阶段 `D4a`；下一阶段
  `D4b_local_private_label_collection_smoke`。

D4a 是**仅评测/诊断**。它**不是**基准结果、**不是**下游 agent 价值
声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间维度
声明，也**不是** QuIVer 系统声明。

- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D4a 不输出 EvidenceCore 记录，也不改变其语义。
- D4a 不采集标签：`labels_collected=false`、
  `calibration_metrics_computed=false`、
  `inter_rater_agreement_measured=false`、
  `agreement_metrics_computed=false`、
  `confidence_intervals_computed=false`。
- D4a 默认不读取私有 bundle：`private_label_bundle_read=false`、
  `private_records_read=false`、`raw_private_records_read=false`、
  `raw_labels_persisted=false`、`raw_label_rows_emitted=false`、
  `private_label_bundle_persisted=false`、
  `private_output_path_emitted=false`、
  `private_input_path_emitted=false`、`private_output_committed=false`。
- D4a 不声称校准：`true_e_s_calibration_claimed=false`、
  `proxy_calibration_claimed=false`。D4a 不通过任何发布门：
  `public_release_gate_passed=false`、
  `real_label_bundle_gate_passed=false`。

## 核心边界：D4a 不是 D4b

- **D4a** 仅执行门 / 试运行公开产物。它校验 CLI/隐私守卫、D3 协议
  常量、合成内存内门逻辑、fail-closed 扫描与文档边界。
- **D4b** 是真实本地/私有标签采集/校准。D4a **不**执行 D4b。默认提交
  的 D4a 产物**不**读取私有标签、**不**采集标签、**不**计算校准/
  agreement/CI 指标，也**不**声称真实/代理校准。

私有试运行模式是仅本地的测试夹具：仅在显式 opt-in 且 `/tmp` 输出时，
可校验一个本地/私有标签-bundle 形状的 JSON，但其输出仅本地、**绝不**
提交。

## CLI

```bash
python3 -m py_compile eval/d4_dual_rubric_execution_gate.py
python3 eval/d4_dual_rubric_execution_gate.py --self-test
python3 eval/d4_dual_rubric_execution_gate.py \
    --out artifacts/d4_dual_rubric_execution_gate/\
d4_dual_rubric_execution_gate_report.json
```

默认模式（无 `--input`、无 `--allow-private-labels`）：写入已提交的公开
门产物（若省略 `--out` 则用默认输出路径）。

私有试运行模式仅是显式守卫夹具：

```bash
# 不提交；仅 /tmp：
python3 eval/d4_dual_rubric_execution_gate.py \
    --allow-private-labels --input /tmp/private_bundle.json \
    --out /tmp/d4a_gate_smoke.json
```

CLI 守卫矩阵（全部在任何输入被打开前校验）：

- `--input` 无 `--allow-private-labels` => exit 2（无路径/basename 泄露）。
- `--allow-private-labels` 无 `--input` => exit 2。
- `--allow-private-labels` 有 `--input` 但无显式 `--out` => exit 2。
- `--allow-private-labels` 以已提交产物路径作为 `--out` => 读取前
  exit 2。
- `--allow-private-labels` 以非 `/tmp` 的 `--out` => 读取前 exit 2。
- `--allow-private-labels --input <path> --out /tmp/...` => 接受为仅本地
  试运行。
- 私有模式成功 stdout **不得**打印确切的 `/tmp` 输出路径。
- 私有模式错误**不得**打印原始异常、输入路径/basename、原始 JSON 或
  标签文本。

## 产物身份（默认已提交产物）

已提交的产物位于
`artifacts/d4_dual_rubric_execution_gate/d4_dual_rubric_execution_gate_report.json`，
是公开门试运行。身份 / 边界字段：

- `schema_version` = `d4_dual_rubric_execution_gate.v1`
- `generated_by`、`generated_at`、`claim_level`、`rubric_version`、
  `status`、`mode`、`phase`、`next_phase`
- `d3_protocol_checked=true`、`d3_protocol_version=
  d3_true_dual_rubric_label_protocol_v1`、`d3_required_gates_present=true`
- 默认 false 标志（全为 false）：`labels_collected`、
  `private_label_bundle_read`、`private_label_bundle_persisted`、
  `private_records_read`、`raw_private_records_read`、
  `raw_labels_persisted`、`raw_label_rows_emitted`、
  `private_output_path_emitted`、`private_input_path_emitted`、
  `private_output_committed`、`calibration_metrics_computed`、
  `inter_rater_agreement_measured`、`agreement_metrics_computed`、
  `confidence_intervals_computed`、`true_e_s_calibration_claimed`、
  `proxy_calibration_claimed`、`public_release_gate_passed`、
  `real_label_bundle_gate_passed`。
- 执行控制标志（仅已校验的试运行控制为 true）：
  `execution_controls_validated`、`private_cli_guard_validated`、
  `tmp_output_guard_validated`、`validate_before_read_guard_validated`、
  `sanitized_error_guard_validated`、
  `small_cell_suppression_gate_validated`、`min_total_n_gate_validated`、
  `agreement_required_gate_validated`、`confidence_interval_gate_validated`。
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
  `agreement_required=true`、`confidence_intervals_required=true`。
- `gate_category_names`：`primary_evidence`、`dependency_support`、
  `weak_candidates`、`abstained`。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写 JSON 前 fail-closed）。

## 门逻辑（合成、内存内）

D4a 仅对合成的内存内聚合摘要校验门阈值。它**不**计算校准指标、
inter-rater agreement 或置信区间。门（常量来自 D3）：

- min-N：`total_labels >= 50`（`min_total_labels`）。
- small-cell 抑制：每个发布单元 `n >= k_min`（5）；任何单元低于 5 则
  fail/suppress 公开发布门。
- agreement 必需：存在第二 rater 且 agreement 可用（不可用 => fail）。
- 置信区间必需：CI 可用（缺失 => fail）。
- 全部条件满足 => 私有试运行门状态 pass。

公开产物仅可包含门类别名、阈值、布尔与合成自测聚合 pass/fail 计数。
**不得**包含来自任何私有输入的真实私有样本量。

## 私有试运行 bundle schema（仅本地、已消毒）

私有试运行模式接受一个合成/私有形状的**聚合**摘要（计数与布尔），而**非**
原始行。它**不**要求真实标签。仅允许以下键：

- `schema` = `d4_private_label_bundle_dry_run_v1`
- `total_labels`（int >= 0）
- `cells`（`{category, n}` 列表，`category` 为固定门类别名，`n` 为
  int >= 0）
- `second_rater_present`、`agreement_available`、
  `confidence_intervals_available`（布尔）
- `min_cell_n`（可选 int >= 0）

此 allowlist 之外的任何键（如 `rater_id`、`raw_label`、
`annotation_row`、`path`）触发 fail-closed。若格式错误，返回固定消毒
错误：
`error: failed to load private labels (schema/privacy/parse error;
details suppressed)`。

私有试运行输出 JSON **不得**包含：输入/输出路径、basename、原始标签、
rater ID、annotation 行、行 hash，或确切的真实私有样本量。它仅包含门
pass/fail 布尔、固定阈值、固定门类别名与已消毒标志。

## 禁止扫描器（fail-closed）

严格的禁止输出扫描器在写任何 JSON 前 fail-closed 运行。拒绝禁止的 dict
键（`task_id`、`repo_id`、`repo`、`path`、`span`、`line_range`、
`start_line`、`end_line`、`content_sha`、`snippet`、`candidate_text`、
`query`、`prompt`、`response`、`model_output`、`label`、`raw_label`、
`annotation_row`、`rater_id`、`annotator_id`、`disagreement_example`、
`per_row_hash` 等）于任何位置，并拒绝值模式：任何 URL（无 URL
allowlist）、32/40/64 字符 hex 摘要、类 secret 字符串、类路径
`src/foo.py` 与 `/private/foo.jsonl`、多行字符串、原始 JSON 片段、原始
行范围 `12-34`，以及自测 sentinel。允许安全的门/协议字符串
（`primary_evidence`、`k_min`、`D4a`、
`d3_true_dual_rubric_label_protocol_v1` 等）。

## 自测

- 全部上述默认 false/true 标志。
- D3 协议常量/门已校验（`k_min=5`、`min_total_labels=50`、
  agreement/CI 必需）。
- CLI 守卫矩阵，含 validate-before-read、已提交输出于读取前拒绝、
  非 `/tmp` 于读取前拒绝。
- 敏感 basename + `SECRET_LABEL_SENTINEL` 的消毒错误：stdout/stderr/
  输出中无泄露。
- 私有输出路径不序列化。
- 禁止扫描器拒绝敏感键/值并 fail-closed。
- 门逻辑测试：min-N、small-cell、agreement、CI 与 pass 用例。
- 自测失败时拒绝成功生成产物。

## 校验

```text
python3 -m py_compile eval/d4_dual_rubric_execution_gate.py    => PASS
python3 eval/d4_dual_rubric_execution_gate.py --self-test      => PASS (153/153 项检查)
python3 eval/d4_dual_rubric_execution_gate.py \
  --out artifacts/d4_dual_rubric_execution_gate/\
d4_dual_rubric_execution_gate_report.json                     => PASS
  (status: execution_gate_ready_no_labels_collected,
   forbidden_scan: pass, self_test_passed: true,
   labels_collected: false, private_label_bundle_read: false,
   private_output_committed: false,
   calibration_metrics_computed: false,
   true_e_s_calibration_claimed: false, proxy_calibration_claimed: false,
   public_release_gate_passed: false,
   execution_controls_validated: true,
   mode: public_gate_dry_run, phase: D4a,
   next_phase: D4b_local_private_label_collection_smoke,
   rubric_version: d3_true_dual_rubric_label_protocol_v1)
/tmp 私有试运行 smoke（合成 bundle）                            => PASS
  (输出/stdout/stderr 中无输入/输出路径、basename、原始标签、
   sentinel 或确切私有样本量)
CLI 守卫矩阵（缺 allow/input/out、已提交输出、非 /tmp 输出）    => PASS (全部 exit 2)
python3 scripts/validate_docs_i18n.py                          => PASS
git diff --check                                                => PASS
```

## 注意事项

- D4a 仅执行门 / 试运行公开产物。它仅评测/诊断。它**不**改变运行时、
  检索器、pack、模型、后端或默认策略；它**不**改变 EvidenceCore 语义。
  它**不是**基准结果、**不是**下游 agent 价值声明、**不是**
  runtime-clean 通用算法声明、**不是** OOD 时间维度声明，也**不是**
  QuIVer 系统声明。
- D4a **不是** D4b。默认提交产物**不**采集标签、**不**读取私有标签
  bundle、**不**计算校准指标、**不**衡量 inter-rater agreement、**不**
  声称真实/代理校准，也**不**通过任何公开发布门。
- 私有试运行模式仅 `/tmp` 且**绝不**提交。它仅校验一个本地/私有标签-
  bundle 形状 JSON 的结构/门；它**不**计算或声称真实校准指标。
- 所有 no-claim / no-runtime-change 标志保持为 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`、`not_evidence`）
  保持为 true；执行控制标志仅对已校验的试运行控制为 true。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  `current-research-conclusions` **未**更新（D4a 是门/试运行；结论无
  变化）。
