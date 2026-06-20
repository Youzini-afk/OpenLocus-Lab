# D1 双评分相关性（仅评测层脚手架）

## 范围与声明边界

D1 是**仅评测层脚手架**。它定义并对一个候选相关性双评分诊断
rubric 进行自测。它**不**改变运行时行为、检索器排序、pack 构建、
模型调用、后端存储、默认策略或 EvidenceCore 语义。

- 声明级别：`eval_layer_rubric_scaffold_only`。
- Rubric 版本：`d1_dual_rubric_v0`。
- D1 仅使用**确定性合成 / 来源回溯 fixture**。它**不**读取真实
  P21/private records（推迟到后续 D2 校准阶段）。
- 这**不是**基准结果，**不是**下游 agent 价值声明，**不是**
  runtime-clean 通用算法声明，**不是** OOD 时间维度支持声明，
  **也不是** QuIVer 系统支持声明。
- EvidenceCore 仍为 `path + line range + content_sha + score + why +
  channels`；D1 不输出 EvidenceCore 记录，也不改变其语义。

## 双评分

D1 将候选相关性拆分为两个确定性小整数信号：

- **E-score**（语义 / 直接作答证据）：`semantic_direct_match` +
  `answer_bearing_span`（范围 0..2）。
- **S-score**（依赖 / 支撑结构证据）：`import_support` +
  `dependency_link_support` + `caller_support`（范围 0..3）。

引用有效性、来源/哈希过期、未引用、显式无证据为**弃决门**，在
E/S 桶分配*之前*触发（依据 oracle 评审：无效/过期引用必须强制
弃决，且 primary evidence 必须要求引用有效）。

### 阈值

- `E_HIGH >= 2`
- `S_HIGH >= 2`
- 当 E 或 S `>= 1` 但低于 high 时为弱证据/支撑。

### 分类顺序（fail-closed）

1. 无效引用、来源/哈希过期、未引用/无证据，或显式无证据 ->
   `abstained`。
2. E 高且引用有效 -> `primary_evidence`。
3. S 高且 E 低于 high -> `dependency_support`。
4. 弱非零 E 或 S -> `weak_candidates`。
5. 否则 -> `abstained`。

E 高优先于 S 高：E 与 S 同时为高且引用有效的候选归为
`primary_evidence`，而非 `dependency_support`。E 高但引用无效的
候选归为 `abstained`（fail-closed）。

## 桶与旧别名

规范桶：

- `primary_evidence`
- `dependency_support`
- `weak_candidates`
- `abstained`

旧别名映射（保留以兼容既有 expected-behavior 枚举）：

- `dependency_support` -> `supporting_only`
- `abstained` -> `abstain`

## 公开产物（仅聚合）

产物位于
`artifacts/d1_dual_rubric_relevance/d1_dual_rubric_relevance_report.json`，
仅含聚合数据：计数、分段计数、reason-code 计数、阈值、分类顺序、
桶名、旧别名、自测检查结果、no-claim 标志，以及 forbidden 扫描
摘要。

它**不**输出任务 ID、repo ID/名称、路径/span/snippet、行或字节范围、
内容哈希、原始候选文本、prompt/response、原始 private records、
label/qrels，或行级派生哈希。一个严格的禁止输出扫描器在写入
JSON 产物之前以 fail-closed 方式运行。

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
  `content_sha_emitted=false`、`raw_private_records_read=false`、
  `raw_private_records_persisted=false`、
  `row_level_hashes_emitted=false`、
  `per_candidate_rows_emitted=false`。

## 验证

```text
python3 -m py_compile eval/d1_dual_rubric_relevance.py   => PASS
python3 eval/d1_dual_rubric_relevance.py --self-test     => PASS (46/46 checks)
python3 eval/d1_dual_rubric_relevance.py \
  --out artifacts/d1_dual_rubric_relevance/\
d1_dual_rubric_relevance_report.json                     => PASS
  (status: scaffold_only_self_test_passed,
   forbidden_scan: pass, self_test_passed: true)
python3 scripts/validate_docs_i18n.py                     => PASS
```

## 注意事项

- D1 仅评测/诊断脚手架。它不提供任何经验支持、基准结果、下游
  agent 价值、runtime-clean 通用算法声明、OOD 时间维度支持，或
  QuIVer 系统支持。
- 合成自测 fixture 是确定性的，仅存在于内存中；除聚合计数外，它
  们从不被序列化到公开产物。
- 读取真实 P21/private records 被明确推迟到后续 D2 校准阶段。
