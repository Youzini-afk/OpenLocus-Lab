# D2 双评分聚合校准（仅代理可映射性）

## 范围与声明边界

D2 是 D1 之后有界的**代理**（proxy）聚合校准。它**不**声称真实
E/S 校准。它以两种严格分离的模式运行：

- **D2a（默认，已提交）**：公开聚合可映射性清单。仅读取已提交的
  C3/B12 公开聚合产物；**不**读取 private records。声明级别：
  `public_aggregate_mappability_only`。
- **D2b（可选，未提交）**：显式本地/私有代理校准冒烟。需要
  `--allow-private-records --input <path> --limit N --out /tmp/...`。
  `/tmp` `--out` 路径必须显式提供；私有模式会拒绝 committed artifact
  路径。**绝不**序列化输入路径/基名/文件大小/mtime。仅输出带小单元
  抑制的聚合代理桶计数。

D2 是**仅评测/诊断**。它**不**改变运行时行为、检索器排序、pack
构建、模型调用、后端存储、默认策略或 EvidenceCore 语义。

- 代理分数（`proxy_e_score`、`proxy_s_score`）**不是**真实 E/S 校准，
  **不是**改进的检索，**不是**下游 agent 价值，**不是**基准结果，
  **不是**默认变更，**也不是** runtime-clean 通用算法声明。
- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D2 不输出 EvidenceCore 记录，也不改变其语义。
- D2a（默认）模式**不**声称代理校准：
  `proxy_calibration_claimed=false`、
  `true_e_s_calibration_claimed=false`。

## 代理术语

D2 全程使用**代理**（proxy）术语。它绝不声称真实 E/S 校准。

- `proxy_e_score`：小整数代理语义 / 直接作答证据分数，从
  `candidate_baseline` 策略的 P21 outcome 指标（`span_f0_5`、
  `added_gold_span`、`primary_false_positive_rate`）映射，仅存于内存。
  范围 0..3。
- `proxy_s_score`：小整数代理依赖 / 支撑结构证据分数，从 route
  features（`candidate_support_exists`、`local_anchor`、
  `rrf_backed_by_anchor`、`symbol_regex_agree`、
  `dense_support_present`）映射，仅存于内存。范围 0..5。
- `proxy_e_band` / `proxy_s_band`：`none` / `weak` / `high`。
- `proxy_bucket`：`proxy_primary_evidence` /
  `proxy_dependency_support` / `proxy_weak_candidates` /
  `proxy_abstained` / `proxy_unmappable`。

### 缺失字段

缺失的代理字段变为 `proxy_unmappable`，**非**负面证据。一条缺少
`candidate_baseline` outcome 或缺少核心 route features
（`candidate_support_exists`、`local_anchor`）的记录被归类为
`proxy_unmappable`，而非零证据。

### 阈值

- `PROXY_E_HIGH >= 2`（满分 3）
- `PROXY_S_HIGH >= 2`（满分 5）
- 当代理 E 或 S `>= 1` 但低于 high 时为弱。

### 分类顺序（fail-closed）

1. 缺失必需代理字段 -> `proxy_unmappable`。
2. 代理 E 高 -> `proxy_primary_evidence`。
3. 代理 S 高且代理 E 低于 high -> `proxy_dependency_support`。
4. 弱非零代理 E 或 S -> `proxy_weak_candidates`。
5. 否则 -> `proxy_abstained`。

代理 E 高优先于代理 S 高：代理 E 与 S 同时为高的记录归为
`proxy_primary_evidence`，而非 `proxy_dependency_support`。

## D2a：公开聚合可映射性清单（默认，已提交）

已提交的产物位于
`artifacts/d2_dual_rubric_aggregate_calibration/d2_dual_rubric_aggregate_calibration_report.json`，
是 D2a 默认产物。它：

- 检查已提交的 C3/B12 公开聚合产物（仅通用标签
  `c3_public_aggregate`、`b12_public_aggregate`；不序列化文件系统
  路径）；
- 报告公开聚合是否包含候选级代理字段（它们**不**包含 — 按构造
  仅聚合）：
  `public_aggregates_have_candidate_level_proxy_fields=false`；
- 报告 `private_input_required_for_proxy_calibration=true`；
- **不**读取 private records：`private_records_read=false`；
- **不**声称代理校准：
  `proxy_calibration_claimed=false`；
- **不**声称真实 E/S 校准：
  `true_e_s_calibration_claimed=false`。

### D2a 产物字段（仅聚合）

- `schema_version` = `d2_dual_rubric_aggregate_calibration.v1`
- `generated_by`、`generated_at`、`claim_level`、`rubric_version`、
  `status`、`mode`
- `artifact_classes_checked` = `["c3_public_aggregate",
  "b12_public_aggregate"]`（仅通用标签）
- `public_artifacts_checked`、`public_artifact_status_counts`
- `public_aggregates_have_candidate_level_proxy_fields=false`
- `private_input_required_for_proxy_calibration=true`
- `proxy_calibration_claimed=false`、
  `true_e_s_calibration_claimed=false`
- `private_records_read=false`、`private_records_persisted=false`、
  `local_input_path_emitted=false`
- `proxy_field_terminology`、`proxy_e_signal_names`、
  `proxy_s_signal_names`、`proxy_bucket_names`
- `self_test_checks`、`self_test_passed`
- No-claim / 安全标志（所有变更/泄露布尔为 false；诊断布尔为 true）
- `forbidden_scan` 摘要

## D2b：可选私有代理校准冒烟（未提交）

D2b 仅在显式 opt-in 时可用：

```bash
python3 eval/d2_dual_rubric_aggregate_calibration.py \
    --allow-private-records --input /tmp/private.json \
    --limit 100 --out /tmp/d2b_proxy_smoke.json
```

D2b：

- 需要 `--allow-private-records` **且** `--input`；单独使用任一均以
  非零退出码退出（退出码 2）；
- 需要显式的 `/tmp` 下 `--out`；私有模式拒绝 committed artifact 路径和
  任何非 `/tmp` 输出；
- 使用 C1 适配器（`c1_private_records.load_private_records`）瞬态
  读取 private records（仅存于内存）；
- 抑制 loader 异常细节，避免 malformed private input 通过 stderr 泄露输入
  路径或基名；
- **绝不**序列化输入路径、基名、文件大小或 mtime；
- 仅输出聚合代理桶计数、代理 E/S 分段计数，以及带小单元抑制的
  代理 E x S 分段交叉表；
- 输出仅写入 `/tmp` — D2b 输出**绝不**提交；
- 声明级别：`dual_rubric_proxy_calibration_smoke_only`；
- `proxy_calibration_claimed=true`（冒烟已运行），但
  `true_e_s_calibration_claimed=false`（代理，非真实 E/S）。

### 小单元抑制

私有聚合交叉表使用 `k_min`（默认 5，可通过 `--k-min` 配置）进行
小单元抑制。计数 < `k_min` 的单元被从交叉表中省略。当任何单元被
抑制时 `small_cells_suppressed=true`；`suppressed_cell_count` 报告
被抑制单元的数量（**非**其个别计数）。

## 公开产物契约（仅聚合）

D2a 与 D2b 产物均为仅聚合。它们**绝不**输出：

- 任务 ID、repo ID/名称、路径/span/snippet、行或字节范围；
- 内容哈希、原始候选文本、prompt/response；
- 原始 private records、label/qrels、每条记录诊断；
- 行级派生哈希、私有桶行；
- 本地输入路径、基名、文件大小或 mtime。

一个严格的禁止输出扫描器在写入任何产物之前以 fail-closed 方式
运行。它拒绝禁止的字典键（`path`、`span`、`content_sha`、
`snippet`、`query`、`task_id`、`repo_id`、`repo`、`label`、
`qrels`、`gold`、`prompt`、`response`、`private_record_hash`、
`p31_score_gold` 等）与禁止的取值模式（URL、32/40/64 字符十六进制
摘要、类密钥串、类路径 `src/foo.py`、`/private/foo.jsonl`、多行串、
原始 JSON 片段、原始行范围 `12-34`）。

### No-claim / 安全标志

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
- `candidate_text_emitted=false`、`paths_or_spans_emitted=false`、
  `content_sha_emitted=false`、
  已提交 D2a 中 `raw_private_records_read=false`（仅显式 `/tmp` D2b
  冒烟中为 `true`）、
  `raw_private_records_persisted=false`、
  `row_level_hashes_emitted=false`、
  `per_candidate_rows_emitted=false`。

## 验证

```text
python3 -m py_compile eval/d2_dual_rubric_aggregate_calibration.py   => PASS
python3 eval/d2_dual_rubric_aggregate_calibration.py --self-test     => PASS (78/78 项检查)
python3 eval/d2_dual_rubric_aggregate_calibration.py \
  --out artifacts/d2_dual_rubric_aggregate_calibration/\
d2_dual_rubric_aggregate_calibration_report.json                     => PASS
  (status: public_aggregate_mappability_only,
   forbidden_scan: pass, self_test_passed: true,
   proxy_calibration_claimed: false,
   true_e_s_calibration_claimed: false,
   private_records_read: false)
# CLI 守卫：--input 不带 --allow-private-records 非零退出           => PASS (退出码 2)
# CLI 守卫：--allow-private-records 不带 --input 非零退出           => PASS (退出码 2)
# CLI 守卫：私有模式不带显式 /tmp --out 非零退出                  => PASS (退出码 2)
# CLI 守卫：私有模式使用 committed artifact --out 非零退出         => PASS (退出码 2)
# CLI 守卫：私有加载错误抑制路径/基名细节                         => PASS
# D2b 冒烟（--allow-private-records --input /tmp/... --out /tmp/...）=> PASS（仅 /tmp，未提交）
python3 scripts/validate_docs_i18n.py                                 => PASS
git diff --check                                                      => PASS
```

## 注意事项

- D2 仅评测/诊断。它**不**改变运行时、检索器、pack、模型、后端或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是**基准结果、
  **不是**下游 agent 价值声明、**不是** runtime-clean 通用算法声明、
  **不是** OOD 时间维度声明，**也不是** QuIVer 系统声明。
- 代理分数**不是**真实 E/S 校准，**不是**改进的检索，**不是**下游
  agent 价值，**不是**基准结果，**不是**默认变更。
- D2a（默认）仅公开聚合可映射性，**非**代理校准。它**不**读取
  private records。
- D2b（可选）仅是私有代理校准冒烟。其输出仅写入 `/tmp` 且**绝不**
  提交。它**不**声称真实 E/S 校准。仅在该显式本地/私有模式下记录
  `raw_private_records_read=true`，同时 `raw_private_records_persisted=false`
  仍保持为 false。
- 缺失代理字段变为 `proxy_unmappable`，**非**负面证据。
- 小单元抑制（`k_min`）省略稀疏交叉表单元；被抑制的单元计数绝不
  输出。
- 既有 mode-only dirty 文件（`eval/ci_clone_and_lock_repo.py`、
  `eval/ci_make_repo_matrix.py`、
  `eval/p59_contrastive_pack_coverage_counterfactual.py`）**未被**
  触碰。
