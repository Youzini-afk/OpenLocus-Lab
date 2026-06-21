# D5-A1 自动化校准特征表（公开仅聚合 Artifact）

## 范围与声明边界

D5-A1 从实证 smoke 推进到 **校准就绪弱监督特征**，通过机器读取已提交
的聚合 artifact 并计算确定性特征记录。D5-A1 是 **对真实先前 run 的
经验特征提取**，不是研究日志摘要，也不是校准。

D5-A1 明确 **不是**校准，**不是**已校准模型声明，**不是** policy/
default 推荐，**不是**方法 winner 声明，**不是**外部基准测试性能声
明，**不是**下游 agent 价值声明，**不是** leaderboard 条目，**也不
是** runtime/retriever/pack/backend/default-policy/EvidenceCore 语义
变更。它 **不**进行任何 provider 调用，**不**进行任何远程 provider
调用。bootstrap 统计与特征记录是面向未来校准/人工审查的弱监督特征，
**不是**已校准标签或 policy 推荐。

- 声明级别：`automated_calibration_feature_extraction_only`。
- 模式：`committed_aggregate_feature_extraction`；阶段 `D5-A1`。
- 状态枚举：成功时
  `automated_calibration_feature_table_pass`；必需输入 artifact 缺
  失、schema/status 不匹配或有不安全声明 flag 时
  `fail_input_contract`；scanner 失败时 `fail_forbidden_scan`。
- D5-A1 是 **eval/diagnostic only**。它 **不是**校准、**不是**已校准
  模型声明、**不是** policy/default 推荐、**不是** benchmark 结果、
  **不是**下游 utility、**不是** true E/S 校准、**不是**外部基准测
  试性能声明、**不是** leaderboard 条目、**不是**方法 winner、**也
  不是** promotion。

## 输入 artifact

D5-A1 机器读取已提交的聚合 artifact（不是研究日志或自由文档）：

### 必需输入

1. **F1-D** — `artifacts/f1d_cross_benchmark_retrieval_robustness/f1d_cross_benchmark_retrieval_robustness_report.json`
   （schema `f1d_cross_benchmark_retrieval_robustness.v1`，status
   `cross_benchmark_retrieval_robustness_pass`）。检索稳健性
   bootstrap 信号源（bm25_vs_empty、regex_vs_bm25、symbol_vs_bm25
   retrieval_utility point/CI/sign stability）。
2. **F1-C** — `artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`
   （schema `f1c_cross_benchmark_retrieval_utility.v1`，status
   `cross_benchmark_retrieval_utility_pass`）。跨基准 utility anchor。
3. **C5-C** — `artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`
   （schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`，
   status `contextbench_method_matrix_scale_smoke_pass`）。
   ContextBench 方法一致/分歧计数源。
4. **C5-F** — `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`
   （schema `c5f_repoqa_method_matrix_scale_smoke.v1`，status
   `repoqa_method_matrix_scale_smoke_pass`）。RepoQA 方法一致/分歧计
   数源。
5. **B16-E** — `artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`
   （schema `b16e_broader_live_provider_paired_smoke.v1`，status
   `broader_live_provider_paired_smoke_pass`）。Live provider delta 信
   号源（context_pack_signal_observed、solve_rate delta、families
   positive/zero/negative）。

### 可选输入（仅在存在且 claim-safe 时包含）

6. **D5-A0** — `artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`
   （schema `d5a_automated_es_calibration.v1`，status
   `automated_es_calibration_smoke_pass`）。自动化 E/S 校准 smoke
   anchor。
7. **B16-D** — `artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`
   （schema `b16d_less_trivial_live_provider_paired_smoke.v1`，status
   `live_provider_less_trivial_paired_smoke_pass`）。次要 live 信号。

缺失、无效、schema 不匹配、status 不匹配或 claim 不安全的可选输入
记录为 `skipped_optional`，仅带聚合原因类别（无原始路径/内容）。

## Fail-closed 输入验证

D5-A1 对每个输入 artifact 进行 fail-closed 验证：

- **必需 artifact 缺失** => status `fail_input_contract` 且 CLI 非零
  退出。
- **Schema 版本不匹配**（必需）=> `fail_input_contract`。
- **Status 不匹配**（必需）=> `fail_input_contract`。
- **不安全声明 flag**（任一
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、`calibrated_model_claimed`、
  `policy_recommendation_claimed`、`method_winner_claimed`、
  `external_benchmark_performance_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、runtime/retriever/pack/backend/default-policy/
  EvidenceCore 变更 flag）=> `fail_input_contract`。
- **输入 `forbidden_scan.status`** 若存在必须为 `pass` => 否则
  `fail_input_contract`。
- **可选 artifact** 仅在存在且 claim-safe 时包含；否则记录为
  `skipped_optional`，仅带聚合原因类别。

## 提取的信号

D5-A1 从输入 artifact 提取确定性信号（每个信号一条固定记录）：

### 检索稳健性信号（来自 F1-D）

- `bm25_vs_empty_retrieval_utility`：point_estimate、ci_p05、ci_p50、
  ci_p95、sign_positive/negative/zero_fraction、sample_units、
  bootstrap_replicates、bootstrap_seed。
- `regex_vs_bm25_retrieval_utility`：负向稳定性。
- `symbol_vs_bm25_retrieval_utility`：负向稳定性。

### 外部基准一致/分歧信号（来自 C5-C + C5-F）

- `bm25_positive_on_both_benchmarks`：bm25 file_recall@10 在
  ContextBench 与 RepoQA 上均 > 0。仅计数。
- `regex_symbol_negative_on_both_benchmarks`：regex 与 symbol
  file_recall@10 在两个基准上均 == 0。仅计数。
- `benchmark_method_agreement`：methods_agree 计数与 methods_disagree
  计数（C5-C 与 C5-F 在正/负方向上一致）。

### Live provider delta 信号（来自 B16-E）

- `b16e_context_pack_signal`：context_pack_signal_observed、
  solve_rate_delta、families_evaluated、families_positive、
  families_zero、families_negative。

### 可选信号（来自 D5-A0 / B16-D，若加载）

- `d5a0_automated_calibration_smoke_anchor`：D5-A0 smoke anchor。
- `b16d_secondary_live_signal`：B16-D 次要 live 信号。

## 校准特征

D5-A1 计算确定性校准特征记录（面向未来校准/人工审查的弱监督特征，
**不是**已校准标签）：

- `bm25_vs_empty_retrieval_utility_magnitude`：量级 bucket
  （`strong_positive` / `weak_positive` / `zero` / `negative`）。
- `bm25_vs_empty_sign_stability`：符号稳定性 bucket
  （`stable_positive` / `majority_positive` / `minority_positive` /
  `never_positive`）。
- `regex_vs_bm25_sign_stability`：负向符号稳定性 bucket。
- `symbol_vs_bm25_sign_stability`：负向符号稳定性 bucket。
- `live_provider_solve_rate_delta`：solve rate delta bucket
  （`strong_positive` / `weak_positive` / `zero` / `negative`）。
- `live_provider_family_distribution`：family 分布 bucket
  （`all_families_positive` / `mixed_families` /
  `all_families_negative` / `all_families_zero`）。
- `cross_signal_alignment`：跨信号对齐标签（见下）。

## 跨信号对齐标签（固定 allowlist）

- `retrieval_robust_positive_plus_live_positive`：bm25_vs_empty
  sign_positive >= 0.95 且 B16-E context_pack_signal_observed 且
  solve_rate_delta > 0 且 families_positive > 0。
- `retrieval_negative_methods_plus_live_not_supported`：regex/symbol
  vs_bm25 sign_negative >= 0.95 且 live 信号缺失或非正。
- `retrieval_only_insufficient`：检索信号存在但无 live 信号。
- `conflicting_signals`：检索与 live 信号冲突（如检索稳健正但
  live 负，或检索负但 live 正）。

## 就绪 bucket（固定 allowlist）

- `ready_for_manual_review`：retrieval_robust_positive + live_positive
  （最强信号）。
- `needs_more_live_downstream`：检索正但 live 信号缺失或弱。
- `retrieval_only_insufficient`：仅检索信号，无 live。
- `conflicting_signals`：检索与 live 冲突。
- `insufficient_signal`：无任何信号。

## 推荐的下一步测量（仅测量，非 policy/default）

- `manual_reference_audit`：人工参考审查是迈向校准就绪的下一步弱
  监督。
- `heldout_benchmark_scale`：在 heldout 子集上扩展检索基准以确认
  bootstrap 稳定性泛化。
- `live_downstream_scale`：扩展 live 下游 paired smoke。

推荐 **仅测量**。它们 **不是** policy/default/method winner 推荐。
D5-A1 绝不推荐 default、policy、方法 winner 或 promotion。

## 公开 artifact 形态

仅 records 形态列表（无动态 dict 镜像）：

- `input_artifact_records`：固定 record 列表
  `{phase, schema_version, status, required, claim_safe, loaded,
  skipped_reason_category, unit_count}`。
- `signal_records`：固定 record 列表（每个提取信号一条）。
- `calibration_feature_records`：固定 record 列表
  `{feature_name, feature_bucket, feature_value, feature_unit}`。
- `readiness_bucket_records`：固定 record 列表
  `{bucket, bucket_count}`（allowlist 中每个 bucket 一条；选中的
  bucket 计数 1，其余 0）。
- `recommended_next_measurement_records`：固定 record 列表
  `{measurement, measurement_rationale}`。

身份/边界字段：

- `schema_version` = `d5a1_automated_calibration_feature_table.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`。
- `cross_signal_alignment`、`readiness_bucket`。
- `input_summary`：`required_input_count`、`optional_input_count`、
  `required_loaded_count`、`optional_loaded_count`、
  `optional_skipped_count`、`input_phases`。
- 安全 true flag（仅当实际为 true 时）：
  `automated_calibration_feature_extraction_performed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- 始终为 false 的 no-claim flag：
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、`calibrated_model_claimed`、
  `policy_recommendation_claimed`、`method_winner_claimed`、
  `external_benchmark_performance_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。
- `framing`：固定 no-claim framing 字段
  （`is_calibration: false`、`is_policy_recommendation: false`）。

## CLI

```bash
python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py
python3 eval/d5a1_automated_calibration_feature_table.py --self-test
python3 eval/d5a1_automated_calibration_feature_table.py \
    --out artifacts/d5a1_automated_calibration_feature_table/\
d5a1_automated_calibration_feature_table_report.json
```

无需网络/provider workflow（D5-A1 仅读取已提交 artifact）。CLI 参数：
`--self-test`、`--out`。未知/私有的参数以通用 `invalid arguments` 消息
拒绝（SafeArgumentParser 模式）。

## 复用的 helper

D5-A1 导入 F1-D helper（向后兼容；均未修改）：

- F1-D scanner：`f1d._scan_f1d`（组合 F1-C/C5-A/C5-C/C5-E scanner 与
  F1-D 特定检查）；D5-A1 添加 D5-A1 特定 forbidden key 与 record-shape
  检查。
- F1-D 安全 value path 常量用于抑制假阳性。

D5-A1 **不**修改 F1-D 结果语义。

## Forbidden scanner（公开，fail-closed）

在写入公开 JSON 前运行严格的 forbidden-output scanner。它组合：

- F1-D forbidden scanner（本身组合 F1-C/C5-A/C5-C/C5-E scanner 与
  F1-D 特定 forbidden key、record-shape 检查与 value-pattern 检查）。
- D5-A1 特定 forbidden key：原始输入 artifact 路径/内容
  （`input_artifact_path`、`input_artifact_content`、
  `input_artifact_json`、`raw_input`、`raw_artifact`），校准声明 key
  （`calibrated_model`、`calibrated_label`、`calibration_applied`、
  `calibration_performed`），policy/default 推荐 key
  （`policy_recommendation`、`recommended_policy`、
  `recommended_default`、`recommended_method`、`default_method`、
  `winner`、`best_method`、`best_arm`、`best_family`、
  `preferred_method`、`preferred_policy`），原始 B16 任务文本/provider
  payload（`task_text`、`task_prompt`、`provider_payload`、
  `raw_payload`），per-unit metric 数组 key（`per_row_metrics`、
  `per_needle_metrics`、`row_metrics`、`needle_metrics`、`row_hashes`、
  `needle_hashes`、`per_unit_metrics`、`per_unit_utility`）。
- D5-A1 record-shape 检查：`input_artifact_records`、`signal_records`、
  `calibration_feature_records`、`readiness_bucket_records`、
  `recommended_next_measurement_records` 必须是 record 列表（**不是**
  dict-keyed mirror）。
- D5-A1 value-pattern 检查：拒绝 raw model routing prefix（复用自
  F1-D）。

不输出 `winner`/`best_method`/`recommended_default`/
`calibrated_model`/`policy_recommendation` 字段。不提交 per-unit metric
数组、原始输入 artifact 路径/内容或 B16 任务文本。

## Self-test

- Artifact 身份字段（schema、claim、status、mode、phase、
  generated_by）。
- 安全 true flag 存在；no-claim flag 为 false。
- Records 形态容器（所有 5 个 D5-A1 record 容器为列表；无动态 dict
  mirror）。
- 就绪 bucket allowlist（所有 5 个 bucket；选中计数 1）。
- 推荐测量仅测量（均在 `manual_reference_audit` /
  `heldout_benchmark_scale` / `live_downstream_scale` allowlist 内；无
  policy/default/winner/promotion）。
- 输入契约验证：干净输入 claim-safe；不安全声明 flag 检测到；输入
  forbidden_scan 失败检测到。
- 信号提取：检索信号（3）、基准信号（3）、live provider 信号（1）。
- 跨信号对齐：retrieval_robust_positive_plus_live_positive；检索正+
  live 负时冲突；无 live 时 retrieval-only 不足。
- 校准特征：records 形态；cross_signal_alignment bucket。
- 就绪 bucket 计算：ready_for_manual_review；conflicting；
  retrieval_only_insufficient；无信号时 insufficient_signal。
- 完整 pass 报告构建；forbidden scan 干净；self-scan 干净。
- Fail-closed 输入契约（status fail_input_contract；特征提取 false）。
- Scanner 拒绝：repo URL、commit SHA、repo slug、task_id key、query key、
  winner key、best_method key、recommended_default key、calibrated_model
  key、policy_recommendation key、per_row_metrics key、per_needle_metrics
  key、provider_payload key、task_text key、input_artifact_path key、
  raw routing prefix value、tmp path、provider key、secret sentinel、
  dict-keyed D5-A1 容器。
- Scanner 允许：method/benchmark/signal/feature/bucket/measurement/phase
  标签、signal_records 列表。
- Fail-closed 生成：干净报告不 raise；泄露报告 raise SystemExit；
  calibrated_model/policy_recommendation 泄露 raise SystemExit。
- CLI 参数表面。

## 验证

```text
python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py  => PASS
python3 eval/d5a1_automated_calibration_feature_table.py --self-test  => PASS (128/128 checks)
python3 eval/d5a1_automated_calibration_feature_table.py \
  --out artifacts/d5a1_automated_calibration_feature_table/\
d5a1_automated_calibration_feature_table_report.json  => PASS
  (status: automated_calibration_feature_table_pass,
   forbidden_scan: pass, self_test_passed: true,
   cross_signal_alignment: retrieval_robust_positive_plus_live_positive,
   readiness_bucket: ready_for_manual_review,
   signals: 9, features: 7, bucket_records: 5, measurements: 2,
   automated_calibration_feature_extraction_performed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   external_benchmark_performance_claimed: false,
   method_winner_claimed: false,
   leaderboard_entry_claimed: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   calibrated_model_claimed: false,
   policy_recommendation_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地特征提取 run 产生以下聚合记录（不提交原始 task/row/needle ID/
repo URL/commit/path/span/source/snippet/prompt/response/provider
payload/per-unit metric 数组/B16 任务文本/私有标签/content hash/
candidate/evidence 行）：

```text
status: automated_calibration_feature_table_pass
forbidden_scan: pass
cross_signal_alignment: retrieval_robust_positive_plus_live_positive
readiness_bucket: ready_for_manual_review
input_artifact_records:
  F1-D: required=true, loaded=true, claim_safe=true, unit_count=30
  F1-C: required=true, loaded=true, claim_safe=true, unit_count=30
  C5-C: required=true, loaded=true, claim_safe=true, unit_count=20
  C5-F: required=true, loaded=true, claim_safe=true, unit_count=10
  B16-E: required=true, loaded=true, claim_safe=true, unit_count=16
  D5-A0: required=false, loaded=true, claim_safe=true, unit_count=4
  B16-D: required=false, loaded=true, claim_safe=true, unit_count=8
signal_records:
  bm25_vs_empty_retrieval_utility (F1-D): point=+0.465035, ci=[+0.298938, +0.464512, +0.624026], sign+=1.0, units=30
  regex_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  symbol_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  bm25_positive_on_both_benchmarks (C5-C+C5-F): bm25_positive_on_both=true
  regex_symbol_negative_on_both_benchmarks (C5-C+C5-F): regex_negative=true, symbol_negative=true
  benchmark_method_agreement (C5-C+C5-F): agree=3, disagree=0
  b16e_context_pack_signal (B16-E): solve_rate_delta=+0.875, families_positive=4
  d5a0_automated_calibration_smoke_anchor (D5-A0)
  b16d_secondary_live_signal (B16-D)
calibration_feature_records:
  bm25_vs_empty_retrieval_utility_magnitude: bucket=weak_positive, value=0.465035
  bm25_vs_empty_sign_stability: bucket=stable_positive, value=1.0
  regex_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  symbol_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  live_provider_solve_rate_delta: bucket=strong_positive, value=0.875
  live_provider_family_distribution: bucket=all_families_positive, value=4
  cross_signal_alignment: bucket=retrieval_robust_positive_plus_live_positive
readiness_bucket_records:
  ready_for_manual_review: count=1
  needs_more_live_downstream: count=0
  retrieval_only_insufficient: count=0
  conflicting_signals: count=0
  insufficient_signal: count=0
recommended_next_measurement_records:
  manual_reference_audit
  heldout_benchmark_scale
```

这是对已提交聚合 artifact 的自动化校准特征提取。它不是校准、不是已
校准模型声明、不是 policy/default/method winner 推荐、不是 benchmark
结果、不是下游 utility、也不是 promotion。

## 注意事项

- D5-A1 是公开仅聚合自动化校准特征表 artifact。它是 eval/diagnostic
  only。它 **不**改变 runtime、retriever、pack、backend 或 default
  policy；它 **不**改变 EvidenceCore 语义。它 **不是**校准、**不是**
  已校准模型声明、**不是** policy/default 推荐、**不是** benchmark 结
  果、**不是**下游 utility、**不是** true E/S 校准、**不是**外部基
  准测试性能声明、**不是** leaderboard 条目、**不是**方法 winner、
  **也不是** promotion。
- D5-A1 机器读取已提交聚合 artifact。它 **不**摘要研究日志或自由文
  档。它 **不**重新运行任何检索或评分管线。
- D5-A1 **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有输入数据从已提交聚合 artifact 读取（仅聚合计数与指标）。
- D5-A1 **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- D5-A1 **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- D5-A1 **不**声明已校准模型。
  `calibrated_model_claimed=false`。
- D5-A1 **不**作出 policy/default 推荐。
  `policy_recommendation_claimed=false`。
- D5-A1 **不**声明方法 winner。
  `method_winner_claimed=false`。
- 特征是面向未来校准/人工审查的弱监督特征，**不是**已校准标签。就绪
  bucket 是诊断 bucket，**不是** promotion/default 门槛。
- 推荐的下一步测量仅测量（人工参考审查、heldout 基准扩展、live 下游
  扩展）。它们 **不是** policy/default/method winner 推荐。
- 跨信号对齐与就绪 bucket 是输入 artifact 信号的确定性函数。它们
  **不是**已校准标签，**不是** policy 决策。
- 所有 no-claim / no-runtime-change flag 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  `automated_calibration_feature_extraction_performed=true` 仅在特征
  提取实际执行时。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  无 promotion/default/runtime 声明变更。
