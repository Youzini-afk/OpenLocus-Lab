# C5-A ContextBench Verified 检索性能 Smoke

日期：2026-06-21（C5-A 外部 benchmark 检索性能 smoke，基于 ContextBench
verified subset）

C5-A 是 OpenLocus 研究轨中**第一个外部-benchmark-形态的检索性能
smoke**。它从 HuggingFace datasets-server 读取有界的 ContextBench
verified subset，在临时 `/tmp` 工作区中检出引用仓库到 `base_commit`，
运行 OpenLocus 检索（初始 `bm25`，无 provider/model 调用），通过现有
`eval/score.py` 逻辑对 ContextBench `gold_context` spans 进行打分，
并**仅提交一个 aggregate 公共报告**。

C5-A 明确**不是**严格的 benchmark 结果，**不是**leaderboard 条目，
**不是**性能声称，**不是**promotion，**不是**默认/策略变更，也**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。

> **重要 claim 边界。** C5-A 输出 `claim_level =
> external_benchmark_retrieval_performance_smoke_only`。它**不**声称外部
> benchmark 结果、**不**声称 leaderboard 条目、**不**声称性能、**不**
> promotion、**不**默认变更、**不**runtime/retriever/pack/backend 变更、
> **不**EvidenceCore 语义变更，也**不**下游 agent 价值声称。所有
> no-claim / no-runtime-change 标志均为 false：
> `external_benchmark_performance_claimed=false`、
> `downstream_agent_value_proven=false`、`promotion_ready=false`、
> `default_should_change=false`、`runtime_behavior_changed=false`、
> `retriever_changed=false`、`pack_builder_changed=false`、
> `backend_changed=false`、`default_policy_changed=false`、
> `evidencecore_semantics_changed=false`、`provider_calls_made=false`、
> `remote_provider_calls_made=false`。

## 目标

将 C4 ContextBench 就绪/row-mapping smoke 转化为第一个真实外部 benchmark
检索性能 smoke：

- 从 HuggingFace datasets-server `/rows` 端点读取有界的 ContextBench
  verified subset；
- 将原始 ContextBench 行、queries/problem statements、repo URL/名称、
  base commits、gold paths/spans/contents、生成的 task/label/run JSONL、
  evidence rows 与克隆的源仓库**仅在**`/tmp` 或 CI 临时工作区中**临时**
  保留；
- 通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
  在 `base_commit` 检出引用仓库；
- 运行 OpenLocus 检索（初始 `bm25`，无 provider/model 调用）；
- 通过现有 `eval/score.py` 逻辑对 ContextBench `gold_context` spans
  打分；
- 仅提交一个 aggregate 公共报告。

这是经验性性能 smoke，**不是**另一个就绪/控制面阶段。它也**不是**严格的
benchmark 声称、promotion、默认策略变更或下游-agent 价值声称。

## D5-A0 -> B16-A -> C5-A 关系

```text
D5-A0 automated E/S calibration smoke (retrieval-only aggregate)
-> B16-A minimal deterministic/mock downstream paired-agent empirical run
   (real edit/test loop; deterministic mock agent; paired control/treatment
    arms; synthetic public micro tasks; aggregate-only public artifact;
    no live LLM, no provider/remote calls, no downstream agent value claim)
-> C5-A ContextBench verified retrieval performance smoke
   (real external benchmark retrieval smoke; transient /tmp clone +
    retrieval + score; aggregate-only public artifact; no provider calls;
    no raw rows/queries/repo URLs/commits/gold paths/spans/JSONL/evidence
    rows/cloned repos/stdout/stderr committed)
```

C5-A **不是** C5。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的
规划/可行性阶段，需要严格的 benchmark 设计、更大的样本量、多种方法与
统计分析。C5-A 仅通过在有界 ContextBench verified subset 上运行真实的
OpenLocus 检索 + 打分管线，产出第一个经验性外部-benchmark-形态的检索
smoke。

## 实现

### Evaluator

`eval/c5_contextbench_verified_performance_smoke.py` 提供 argparse CLI：

- `--self-test` —— 无网络合成 self-test（113 组断言）。
- `--row-limit` —— 评估的 ContextBench verified 行数；默认 5，硬上限 20。
- `--method` —— OpenLocus 检索方法；默认 `bm25`；允许 `bm25`、`regex`、
  `text`、`symbol`（无 provider 调用）。
- `--query-mode` —— query sanitizer 模式；默认 `first_paragraph`；允许
  `first_paragraph`、`first_sentence`、`raw`。
- `--language-filter` —— 语言过滤类别；默认 `python`；允许 `python`、
  `all`（仅为类别桶 —— 永不在内存范围外泄露原始行值）。
- `--openlocus` —— 可选的 OpenLocus 二进制路径（默认
  `target/release/openlocus`，然后回退到 `target/debug/openlocus`；
  解析为绝对路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>`
  运行）。
- `--out` —— 输出 artifact JSON 路径；默认
  `artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`。

未知/私有的参数会被拒绝，并显示固定的 `invalid arguments` 消息，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### Runtime 流程

1. Self-test 必须在任何 artifact 写入之前通过
   （`_refuse_on_self_test_failure`）。
2. 将 OpenLocus 二进制解析为绝对路径（先 release 后 debug 回退）。若
   缺失，产出真实的 `unavailable_with_reason`，
   `failure_reason_category=retrieval_failed`。
3. 从 HF datasets-server `/rows` 端点抓取有界 ContextBench verified 行
   （分页；仅 stdlib `urllib`；有界超时）。在内存中按
   `language_filter`（仅为类别桶）过滤。
4. 对每一行（有界至 `row_limit`）：
   - 将 `gold_context` JSON 解析为临时 `gold_paths` / `gold_lines`
     供 `eval/score.py` 使用（`content` 字段**绝不**读取或持久化）。
   - 将 `problem_statement` sanitizer 为检索 query（仅内存中；
     first paragraph / first sentence / raw；剥离 HTML 注释、HTML
     标签、markdown header、code fence；限制长度）。
   - 在每行的 `TemporaryDirectory` 下，通过
     `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
     克隆 `repo_url` 到 `base_commit`（有界超时）。
   - 在 `TemporaryDirectory` 下生成临时 task/label JSONL。
   - 通过 `eval/run_retrieval.py` 运行 OpenLocus 检索
     （`--method bm25 --cwd <repo_root>`）。
   - 运行 `eval/score.py` 并解析 aggregate metrics。
5. 在成功的行上聚合 metrics（每个 allowlisted 数值 metric 的均值）。
6. 构建 aggregate-only 公共报告，fail-closed forbidden scanner。

### 公共 artifact 身份

提交的 artifact 位于
`artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`，
是公共 aggregate-only smoke artifact。身份/边界字段：

- `schema_version` = `c5_contextbench_verified_performance_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- `status`：`pass` | `partial` | `unavailable_with_reason` |
  `fail_schema_contract` | `fail_forbidden_scan`
- Safe true 标志（仅当实际为真时为 true）：
  `external_benchmark_rows_read`、
  `repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `performance_smoke`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- No-claim / no-runtime-change 标志（全为 false）：
  `external_benchmark_performance_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- License 字段（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- `method`、`query_mode`、`language_filter`、`network_mode`、
  `openlocus_binary_source`。
- `row_limit_requested`、`rows_fetched`、`rows_evaluated`、
  `rows_successful`、`rows_failed`、`network_calls`、`provider_calls=0`。
- `failure_reason_category`（仅在 `unavailable_with_reason` 状态下）。
- `failure_category_counts`：仅固定枚举类别。
- `metrics`：来自 `eval/score.py` 的 aggregate metric 均值/比率/计数，
  仅过滤为固定 allowlist（无动态行 ID 或路径）。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Aggregate metrics

`metrics` 块仅包含 allowlisted 的 aggregate metric 名称与数值（来自
`eval/score.py`）。无行级记录、无行 ID、无路径、无 span、无 snippet、无
content_sha。Allowlisted metric 名称：

- `total_tasks`、`successful`、`success_rate`、`avg_latency_ms`。
- `structural_validity`、`citation_validity`、
  `citation_hash_checked`、`citation_validation_mode`。
- `file_recall@1`、`file_recall@5`、`file_recall@10`、
  `file_precision@5`、`file_precision@10`、`mrr`。
- `line_precision@10`、`line_recall@10`、`span_f0.5@10`。
- `token_waste_ratio@10`、`wrong_span_rate@10`、
  `zero_overlap_evidence_rate@10`。

`failure_category_counts` 块仅包含固定枚举类别标签（永不行级值）：

- `network_fetch_failed`、`row_parse_failed`、
  `gold_context_parse_failed`、`language_filter_excluded`、
  `clone_failed`、`checkout_failed`、`task_jsonl_write_failed`、
  `label_jsonl_write_failed`、`retrieval_failed`、`score_failed`、
  `no_python_rows`、`row_limit_capped`、`scanner_self_test_failed`、
  `forbidden_leak_blocked`、`unexpected_exception`。

### 不可用模式

如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索失败、打分
失败等），artifact 记录真实的 `unavailable_with_reason`，带有真实的
`failure_reason_category` 与对应的 `failure_category_counts` 计数。绝不
写入 stale/fake pass。在不可用模式下：

- `status=unavailable_with_reason`。
- `metrics={}`（无 metrics）。
- `performance_smoke=false`。
- `openlocus_retrieval_executed=false`。
- `score_py_metrics_computed=false`。
- `repositories_materialized_transiently=false`。
- `external_benchmark_rows_read=true` 仅当失败前实际抓取了行。
- `aggregate_only_public_artifact=true` 与 `diagnostic_only=true`
  保持为 true。

## 隐私 / license 边界

公共 artifact 与文档保持 aggregate-only。以下内容**不**持久化于任何
公共 artifact 或文档中：

- 原始 ContextBench 行与 gold labels；
- 行级 task instance 值、instance ID、original_inst_id；
- repo URL、repo 名称、base commit、repo 路径；
- 文件路径、span、行范围、snippet、gold 内容；
- problem statement / query（仅内存中 sanitizer）；
- patch、test patch、f2p、p2p；
- 生成的 task/label/run JSONL（仅临时 `/tmp`）；
- OpenLocus evidence 行、snippet、路径、行范围、content_sha；
- 克隆的仓库/源文件（仅临时 `/tmp`）；
- 原始命令 stdout/stderr 或 stack trace。

公共 artifact 仅记录：来自 `eval/score.py` 的 aggregate metric
均值/比率/计数（allowlisted）、固定 failure-category 计数、固定配置
标签（仅 method、query_mode、language_filter 类别）、行计数、网络/
provider 调用计数，以及确定性的 `generated_by` 路径。

ContextBench 数据集 license 未知
（`unknown_dataset_license`）；行级再分发被禁用
（`row_level_redistribution_allowed=false`），派生行级发布被禁用
（`derived_row_level_publication_allowed=false`）。Aggregate metrics
发布允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 通过，无需 HuggingFace/GitHub。
- 真实性能 smoke 需要公共网络访问 HF datasets-server 与 GitHub 仓库。
  CI 是一个单独的显式 `workflow_dispatch` job，带有
  `enable_external_benchmark_network=true` 输入。它**不**默认在
  PR/push 上运行，不使用 provider secrets/vars，不使用 `OPENLOCUS`
  provider env，仅上传 aggregate 临时报告。
- 如果 `enable_external_benchmark_network` 为 false，workflow 是一个
  no-op，显示明确消息并 exit 0（self-test + py_compile 仍会运行；
  no-op 模式下不产出 aggregate 报告）。
- Workflow 在 smoke 之后校验报告的 claim 边界标志：
  `aggregate_only_public_artifact=true`、`diagnostic_only=true`；
  所有 no-claim / no-runtime-change 标志为 false；license 字段固定；
  `provider_calls=0`；`forbidden_scan.status=pass`；
  `self_test_passed=true`；`status` 属于 `(pass, partial,
  unavailable_with_reason)`（无 stale/fake pass；无
  `fail_schema_contract` / `fail_forbidden_scan`）。

## Forbidden scanner（公共，fail-closed）

严格的 forbidden-output scanner 在写入公共 JSON 前 fail-closed 运行。
以 B16-A scanner 为模型（无带字段名 token 的合约容器；无过宽容器豁免）。
拒绝 forbidden dict key（`path`、`span`、`file`、`repo`、`repo_url`、
`base_commit`、`instance_id`、`problem_statement`、`gold_context`、
`gold_paths`、`gold_lines`、`query`、`content_sha`、`snippet`、
`patch`、`diff`、`stdout`、`stderr`、`event_log`、`stack_trace`、
`api_key`、`base_url`、`provider_key`、`secret`、`token`、
`credential`、`rows`、`per_run`、`predictions`、`candidates`、
`evidence` 等）出现在任意位置，并拒绝值模式：任意 URL（无 URL
allowlist —— repo URL **绝不**泄露）、32+ 字符 hex digest、40 字符
commit SHA、形如 `astropy/astropy` 的 repo slug、secret-like 字符串、
带文件扩展名的 path-like 字符串、`/tmp/` 工作区路径值、`task_N`
任务标识符值、patch/diff 标记（`---`、`+++`、`@@`）、stack trace
（`Traceback (most recent call last)`）、多行字符串、原始 JSON 片段、
原始行范围 `12-34`，以及 self-test sentinel。

`failure_category_counts` 与 `metrics` 容器是 schema-key 容器，其
CHILD KEY 是固定类别标签或 allowlisted metric 名称（**非**行级值）；
forbidden_key 检查对这些子键放宽，但其下的值仍会被扫描（仅允许
int/float/短字符串）。

Scanner 仅对最终公共 aggregate artifact 运行。内部 task/label/run
JSONL（包含路径/span/query/gold）仅保留在内存/临时 `/tmp` 下，永不
针对公共合约扫描，永不提交。

## Self-tests

`--self-test` 运行 113 个确定性检查，覆盖 15 组（无网络；合成行 +
合成 score 数据）：

1. Artifact 身份字段（schema、claim、status、mode、phase、
   generated_by）。
2. Safe true 标志存在 + 正确值（7 个标志）。
3. No-claim / no-runtime-change false 标志（12 个标志）。
4. License 字段（4 个字段）。
5. Forbidden scanner 拒绝（25 个注入模式：repo URL、repo slug、
   commit SHA、repo key、repo_url key、base_commit key、instance_id
   key、problem_statement key、gold_context key、gold_paths key、
   gold_lines key、query key、path key、file path value、line range
   value、hex digest value、secret-like value、/tmp path value、
   task_id value、patch marker value、stack trace value、sentinel
   value、multiline value、raw JSON fragment、long string、
   forbidden field name as value）。
6. Forbidden scanner 允许安全值（method、query_mode、
   language_filter、network_mode、metric value、failure category
   count）。
7. Query sanitizer（first_paragraph / first_sentence / raw；HTML
   注释 / code fence / markdown header 剥离；长度上限；query 永不出现在
   公共 artifact 中）。
8. Gold context parser（提取 paths/lines；拒绝无效 JSON / 缺失文件 /
   倒置范围；gold_paths / gold_lines 永不出现在公共 artifact 中）。
9. Score metric allowlist（排除 row_id / path / content_sha；包含
   mrr / file_recall）。
10. Failure category counts 固定枚举（枚举内 key 通过；非枚举 key 由
    builder 拒绝）。
11. 行限制上限（默认 5；硬上限 20）。
12. 不可用报告（真实；无 stale/fake pass；无 metrics；forbidden scan
    pass）。
13. Fail-closed 生成（干净报告不 raise；泄露报告 raise；self-test
    失败拒绝 artifact 生成）。
14. 公共 artifact 自扫描干净（skeleton + 不可用）。
15. CLI 参数面（`--self-test`、`--row-limit`、`--method`、
    `--query-mode`、`--language-filter`、`--openlocus`、`--out`）。

## 验证

```text
python3 -m py_compile eval/c5_contextbench_verified_performance_smoke.py  => PASS
python3 eval/c5_contextbench_verified_performance_smoke.py --self-test  => PASS (113/113 checks)
python3 eval/c5_contextbench_verified_performance_smoke.py \
  --row-limit 5 --method bm25 --query-mode first_paragraph \
  --language-filter python \
  --out artifacts/c5_contextbench_verified_performance_smoke/\
c5_contextbench_verified_performance_smoke_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_performance_smoke, phase: C5-A,
   method: bm25, query_mode: first_paragraph, language_filter: python,
   rows_fetched: 5, rows_evaluated: 5, rows_successful: 5, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   performance_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   downstream_agent_value_proven: false,
   promotion_ready: false, default_should_change: false,
   runtime_behavior_changed: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   provider_calls_made: false, remote_provider_calls_made: false,
   dataset_license_status: unknown_dataset_license,
   row_level_redistribution_allowed: false,
   derived_row_level_publication_allowed: false,
   aggregate_metrics_publication: aggregate_only_smoke)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 真实 smoke 结果（2026-06-21）

```text
python3 eval/c5_contextbench_verified_performance_smoke.py \
  --row-limit 5 --method bm25 --query-mode first_paragraph \
  --language-filter python \
  --out artifacts/c5_contextbench_verified_performance_smoke/\
c5_contextbench_verified_performance_smoke_report.json
  => status: pass, forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 5, rows_evaluated: 5, rows_successful: 5, rows_failed: 0
  => network_calls: 1, provider_calls: 0
  => external_benchmark_rows_read: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => performance_smoke: true
```

5 行 ContextBench verified 行从 HF datasets-server 临时抓取，在内存中
适配，引用仓库在临时 `/tmp` 目录下克隆到其 `base_commit`，在每个仓库
上运行 OpenLocus `bm25` 检索，`eval/score.py` 产出 aggregate 检索
metrics。Aggregate metric 均值（file recall、MRR、span/line metrics、
zero-overlap、structural/citation validity）在 5 个成功行上计算，并写入
提交的 artifact。无原始 ContextBench 行、queries、repo URL/名称、base
commit、gold paths/spans/contents、生成的 task/label/run JSONL、
evidence 行、克隆仓库或 stdout/stderr 被提交或上传。

如果未来环境中网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、
检索失败、打分失败），artifact 记录真实的 `unavailable_with_reason`，
带有真实的 `failure_reason_category` 与对应的 `failure_category_counts`
计数。绝不写入 stale/fake pass。

## 注意事项

- C5-A 是公共 aggregate-only 外部 benchmark 检索性能 smoke artifact。
  它是 eval/diagnostic only。它**不**改变 runtime、retriever、pack、
  backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、
  **不是**promotion、**不是**默认变更、**不是**runtime-clean 通用
  算法声称、**不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，
  也**不是**下游 agent 价值声称。
- C5-A **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的
  网络调用是对公共 HF datasets-server（抓取有界 ContextBench verified
  行）与对公共 GitHub（在临时 `/tmp` 目录下克隆引用仓库到其
  `base_commit`）。`provider_calls=0`、`provider_calls_made=false`、
  `remote_provider_calls_made=false`。
- C5-A 使用**有界 ContextBench verified subset**（默认 5 行；硬上限 20
  行）。这是 smoke，**不是**严格的 benchmark 评估。Aggregate metrics
  是小样本上的点估计，**不应**被解读为 benchmark 结果、leaderboard 条目
  或性能声称。
- C5-A 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`。克隆的
  仓库、生成的 task/label/run JSONL、evidence 行与 stdout/stderr 仅
  保留在 `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅包含
  aggregate 计数/比率/均值。
- C5-A **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别
  的诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-A **不**证明下游 agent 价值。检索 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  无 runtime/retriever/pack/model/backend/default-policy 文件被修改；
  无 promotion/default/runtime claim 变更。

## 下一步

- C5-A 是第一个外部-benchmark-形态的检索性能 smoke。完整的 C5
  外部-benchmark-评估阶段仍然是一个有界的规划/可行性阶段，需要严格的
  benchmark 设计、更大的样本量、多种方法与统计分析。
- 无 promotion、无默认变更、无 EvidenceCore 语义变更、无
  runtime-clean 通用算法声称、无下游 agent 价值声称、无 OOD 时间泛化
  声称，也无 QuIVer systems 声称来自 C5-A。
