# C5-C ContextBench Verified 检索方法矩阵 Scale Smoke

日期：2026-06-21（C5-C 外部 benchmark 检索方法矩阵 scale smoke，基于
ContextBench verified subset，将 C5-B 5 行方法矩阵 smoke 扩展为有界 20 行
方法矩阵 scale smoke）

C5-C 是 C5-B 外部-benchmark-形态检索方法矩阵 smoke 的**有界 20 行方法矩阵
scale 扩展**。它从 HuggingFace datasets-server **一次性**读取有界 20 行
ContextBench verified subset，在临时 `/tmp` 工作区中检出引用仓库到
`base_commit`，跨请求方法矩阵运行 OpenLocus 检索（默认
`bm25,regex,symbol`；C5-C 仅允许 `bm25,regex,symbol`；固定
`baseline_method=bm25`），通过现有 `eval/score.py` 逻辑对每种方法针对
benchmark label spans 打分，并提交**仅一个 aggregate 公共报告**，
其中包含每方法 aggregate metrics（记录，**非**动态方法名 key 的 dict）、
仅 aggregate 的与固定 `bm25` baseline 的 delta，以及一个 `input_summary` 块。

C5-C 明确**不是**严格的 benchmark 结果，**不是**leaderboard 条目，**不是**
性能声称，**不是**promotion，**不是**默认/策略变更，也**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它**不**输出 `winner`、
`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。
`baseline_is_policy_candidate=false` 与 `default_should_change=false` 固定。

> **重要 claim 边界。** C5-C 输出 `claim_level =
> external_benchmark_retrieval_method_matrix_scale_smoke_only`。它**不**声称
> 外部 benchmark 结果、**不**声称 leaderboard 条目、**不**声称性能、**不**
> promotion、**不**默认变更、**不**runtime/retriever/pack/backend 变更、
> **不**EvidenceCore 语义变更，也**不**下游 agent 价值声称。所有
> no-claim / no-runtime-change 标志均为 false：
> `external_benchmark_performance_claimed=false`、
> `leaderboard_entry_claimed=false`、
> `downstream_agent_value_proven=false`、`promotion_ready=false`、
> `default_should_change=false`、`baseline_is_policy_candidate=false`、
> `runtime_behavior_changed=false`、`retriever_changed=false`、
> `pack_builder_changed=false`、`backend_changed=false`、
> `default_policy_changed=false`、`evidencecore_semantics_changed=false`、
> `provider_calls_made=false`、`remote_provider_calls_made=false`。

## 目标

将 C5-B 单方法 ContextBench verified 检索方法矩阵 smoke（5 行）扩展为有界
20 行方法矩阵 scale smoke：

- 从 HuggingFace datasets-server `/rows` 端点**一次性**读取有界 20 行
  ContextBench verified subset（跨所有方法共享）；
- 将原始 ContextBench 行、queries/problem statements、repo URL/名称、
  base commit、gold paths/spans/contents、生成的 task/label/run JSONL、
  evidence rows 与克隆的源仓库**仅在**`/tmp` 或 CI 临时工作区中**临时**
  保留；
- 通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
  在 `base_commit` 检出引用仓库；
- 跨请求方法矩阵运行 OpenLocus 检索（默认 `bm25,regex,symbol`；C5-C 仅
  允许 `bm25,regex,symbol`；固定 `baseline_method=bm25`；无 provider/model
  调用）；
- 通过现有 `eval/score.py` 逻辑对每种方法针对 benchmark label spans 打分；
- 仅提交一个 aggregate 公共报告，其中包含每方法记录、仅 aggregate 的与
  固定 `bm25` baseline 的 delta，以及一个 `input_summary` 块。

这是经验性方法矩阵 scale smoke，**不是**另一个就绪/控制面阶段。它也**不是**
严格的 benchmark 声称、promotion、默认策略变更、leaderboard 条目或下游-agent
价值声称。

## C5-A -> C5-B -> C5-C 关系

```text
C5-A ContextBench verified retrieval performance smoke
  (single-method; bm25 default; bounded 5-row ContextBench verified
   subset; transient /tmp clone + retrieval + score; aggregate-only
   public artifact; no provider calls; no raw rows/queries/repo URLs/
   commits/gold paths/spans/JSONL/evidence rows/cloned repos/stdout/
   stderr committed)
-> C5-B ContextBench verified retrieval method matrix smoke
   (multi-method matrix; default bm25,regex,symbol; allowed
    bm25,regex,text,symbol; 5-row per method; fixed baseline_method=bm25;
    shared row fetch across methods; per-method aggregate records;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default)
-> C5-C ContextBench verified retrieval method matrix scale smoke
   (multi-method matrix; bm25,regex,symbol ONLY (no text);
    bounded 20-row per method; fixed baseline_method=bm25;
    shared row fetch across methods; per-method aggregate records with
    optional aggregate_runtime_seconds; aggregate-only deltas vs bm25;
    input_summary block; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default;
    status pass enum contextbench_method_matrix_scale_smoke_pass)
```

C5-C **不是** C5。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/
可行性阶段，需要严格的 benchmark 设计、更大的样本量、多种方法与统计分析。
C5-C 仅通过在有界 20 行 ContextBench verified subset 上跨请求方法矩阵运行
真实 OpenLocus 检索 + 打分管线，产出第一个经验性外部-benchmark-形态的检索
方法矩阵 scale smoke。

## 实现

### Evaluator

`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py` 提供 argparse
CLI：

- `--self-test` —— 无网络合成 self-test（179 组断言）。
- `--row-limit` —— 每方法评估的 ContextBench verified 行数；默认 20，硬上限
  20（C5-C 是有界 scale smoke：一次性使用完整 ContextBench verified 预览
  预算）。
- `--methods` —— 逗号分隔的 OpenLocus 检索方法；默认 `bm25,regex,symbol`；
  C5-C 仅允许 `bm25,regex,symbol`（C5-C **不**允许 `text` 方法，不同于
  C5-B）；未知方法被拒绝；重复项按首次出现顺序确定性去重。
- `--query-mode` —— query sanitizer 模式；默认 `first_paragraph`；允许
  `first_paragraph`、`first_sentence`、`raw`。
- `--language-filter` —— 语言过滤类别；默认 `python`；允许 `python`、`all`
  （仅为类别桶 —— 永不在内存范围外泄露原始行值）。
- `--openlocus` —— 可选的 OpenLocus 二进制路径（默认
  `target/release/openlocus`，然后 `target/debug/openlocus` 回退；解析为
  绝对路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>` 运行）。
- `--out` —— 输出 artifact JSON 路径；默认
  `artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`。

未知/私有的参数会被拒绝，并显示固定的 `invalid arguments` 消息，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### Runtime 流程

1. Self-test 必须在任何 artifact 写入之前通过
   （`_refuse_on_self_test_failure`）。
2. 解析方法（无效配置时抛出 `MethodConfigError`；失败时产出
   `unavailable_with_reason` 报告）。
3. 将 OpenLocus 二进制解析为绝对路径（先 release 后 debug 回退）。若
   缺失，产出真实的 `unavailable_with_reason`，
   `failure_reason_category=retrieval_failed`。
4. 从 HF datasets-server `/rows` 端点**一次性**抓取有界 20 行 ContextBench
   verified 行（分页；仅 stdlib `urllib`；有界超时）。在内存中按
   `language_filter`（仅为类别桶）过滤。此单次抓取跨所有方法共享。
5. 对每种方法（限定为 `bm25,regex,symbol`）：
   - 对每一行（限定为 20）：
     - 将 benchmark label context JSON 解析为临时 `gold_paths` / `gold_lines`
       供 `eval/score.py` 使用（label `content` 字段**绝不**读取或持久化）。
     - 将 `problem_statement` sanitizer 为检索 query（仅内存中；
       first paragraph / first sentence / raw；剥离 HTML 注释、HTML
       标签、markdown header、code fence；限制长度）。
     - 在每行 `TemporaryDirectory` 下，通过
       `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
       克隆 `repo_url` 到 `base_commit`（有界超时）。
     - 在 `TemporaryDirectory` 下生成临时 task/label JSONL。
     - 通过 `eval/run_retrieval.py` 运行 OpenLocus 检索
       （`--method <method> --cwd <repo_root>`）。
     - 运行 `eval/score.py` 并解析 aggregate metrics。
   - 在成功行上聚合 metrics（每个 allowlisted 数值 metric 的均值）。
   - 记录 `aggregate_runtime_seconds`（该方法完整运行的墙钟时间）。
6. 计算与固定 `bm25` baseline 的 aggregate delta。
7. 构建 aggregate-only 公共报告，fail-closed forbidden scanner。

### 公共 artifact 身份

提交的 artifact 位于
`artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`，
是公共 aggregate-only scale-smoke artifact。身份/边界字段：

- `schema_version` = `c5c_contextbench_verified_method_matrix_scale_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- `status`：`contextbench_method_matrix_scale_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan`
- Safe true 标志（仅当实际为真时为 true）：
  `retrieval_scale_smoke_performed`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`aggregate_only_public_artifact`、
  `diagnostic_only`。（C5-C **不**使用 C5-B 的 `method_matrix_smoke`
  标志或 C5-A 的 `external_benchmark_rows_read`/
  `repositories_materialized_transiently`/`performance_smoke` 标志。）
- No-claim / no-runtime-change 标志（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `baseline_is_policy_candidate`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- License 字段（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- `methods_requested`、`methods_allowed`、`baseline_method`、
  `query_mode`、`language_filter`、`network_mode`、
  `openlocus_binary_source`。
- `row_limit_requested`、`rows_fetched`、`methods_count`、
  `methods_attempted`、`methods_successful`、`methods_succeeded`、
  `methods_failed`、`network_calls`、`provider_calls=0`。
- `input_summary`：`row_limit`、`methods`、`query_mode`、
  `language_filter`、`rows_fetched`、`rows_evaluated`、
  `rows_successful`、`rows_failed`（仅 aggregate 计数）。
- `failure_reason_category`（仅在 `unavailable_with_reason` 状态下）。
- `failure_category_counts`：仅固定枚举类别。
- `method_results`：固定记录（dict 列表，**非**以方法名为 key 的 dict），
  包含 `method`、`status`、`rows_evaluated`、`rows_successful`、
  `rows_failed`、`metrics`（仅 allowlisted）、`failure_category_counts`，
  以及可选的 `aggregate_runtime_seconds`。
- `smoke_metric_deltas_vs_baseline`：固定记录，包含
  `baseline_method=bm25`、`method`、`metric`（allowlisted）、`delta`。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Aggregate metrics

每个方法结果记录中的 `metrics` 块仅包含 allowlisted 的 aggregate metric
名称与数值（来自 `eval/score.py`）。无行级记录、无行 ID、无路径、无 span、
无 snippet、无 content_sha。Allowlisted metric 名称：

- `file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。

`failure_category_counts` 块仅包含固定枚举类别标签（永不行级值）：

- `network_fetch_failed`、`row_parse_failed`、
  `label_context_parse_failed`、`language_filter_excluded`、
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
- `method_results` 是每方法记录的列表，每个带
  `status=unavailable_with_reason`、`metrics={}` 与零行计数。
- `smoke_metric_deltas_vs_baseline=[]`（无 delta）。
- `retrieval_scale_smoke_performed=false`。
- `openlocus_retrieval_executed=false`。
- `score_py_metrics_computed=false`。
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
- 原始命令 stdout/stderr 或 stack trace；
- 行级 metrics 或行级失败记录；
- 行/repo/candidate hash。

公共 artifact 仅记录：来自 `eval/score.py` 的 aggregate metric
均值/比率/计数（allowlisted）、固定 failure-category 计数、固定配置
标签（仅 method、query_mode、language_filter 类别）、行计数、网络/
provider 调用计数、可选的每方法 aggregate runtime 秒数，以及确定性的
`generated_by` 路径。

ContextBench 数据集 license 未知
（`unknown_dataset_license`）；行级再分发被禁用
（`row_level_redistribution_allowed=false`），派生行级发布被禁用
（`derived_row_level_publication_allowed=false`）。Aggregate metrics
发布允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 通过，无需 HuggingFace/GitHub。
- 真实 scale smoke 需要公共网络访问 HF datasets-server 与 GitHub 仓库。
  CI 是一个单独的显式 `workflow_dispatch` job，带
  `enable_external_benchmark_network=true` 输入。它**不**默认在
  PR/push 上运行，不使用 provider secrets/vars，不使用
  `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env，仅上传 aggregate 临时报告。
- 如果 `enable_external_benchmark_network` 为 false，workflow 是一个
  no-op，显示明确消息并 exit 0（self-test + py_compile 仍会运行；
  no-op 模式下不产出 aggregate 报告）。
- Workflow 在 smoke 之后校验报告的 claim 边界标志：
  `aggregate_only_public_artifact=true`、`diagnostic_only=true`；
  所有 no-claim / no-runtime-change 标志为 false；license 字段固定；
  `provider_calls=0`；`forbidden_scan.status=pass`；
  `self_test_passed=true`；`status` 属于
  `(contextbench_method_matrix_scale_smoke_pass, partial,
  unavailable_with_reason)`（无 stale/fake pass；无
  `fail_forbidden_scan`）。

## Forbidden scanner（公共，fail-closed）

严格的 forbidden-output scanner 在写入公共 JSON 前 fail-closed 运行。
复用 C5-A forbidden scanner 原语进行原始 key/value 泄露检测，并 ADD
C5-C 专属检查：

- 拒绝 forbidden dict key（`path`、`span`、`file`、`repo`、`repo_url`、
  `base_commit`、`instance_id`、`problem_statement`、benchmark label-context keys、
  `gold_paths`、`gold_lines`、`query`、`content_sha`、`snippet`、
  `patch`、`diff`、`stdout`、`stderr`、`event_log`、`stack_trace`、
  `api_key`、`base_url`、`provider_key`、`secret`、`token`、
  `credential`、`rows`、`per_run`、`predictions`、`candidates`、
  `evidence`、`row`、`repo_name`、`repo_slug`、`query_text`、`gold`、
  `gold_path`、`gold_span`、`gold_snippet`、`stdout_text`、
  `stderr_text`、`evidence_row`、`evidence_rows`、`retrieved_path`、
  `retrieved_paths`、`retrieved_snippet`、`cloned_repo_path`、
  `cloned_repo`、`per_row_metrics`、`row_metrics` 等）出现在任意位置。
- 拒绝推荐/策略字段出现在任意位置：`winner`、`best_method`、
  `recommended_default`、`recommended_method`、`preferred_method`、
  `default_method`、`policy_decision`、`decision`、`ranking`、`rank`。
- 拒绝值模式：任意 URL（无 URL allowlist —— repo URL **绝不**泄露）、
  32+ 字符 hex digest、40 字符 commit SHA、形如 `astropy/astropy` 的 repo
  slug、secret-like 字符串、带文件扩展名的 path-like 字符串、`/tmp/`
  工作区路径值、`task_N` 任务标识符值、patch/diff 标记（`---`、`+++`、
  `@@`）、stack trace、多行字符串、原始 JSON 片段、原始行范围 `12-34`，
  以及 self-test sentinel。
- 拒绝 `method_results` 为以方法名为 key 的 dict（必须是记录列表）；
  拒绝缺失/非 allowlisted `method` 的记录；拒绝 `text` 作为方法（C5-C 仅
  允许 `bm25,regex,symbol`）。

`failure_category_counts`、`metrics` 与
`smoke_metric_deltas_vs_baseline` 容器是 schema-key 容器，其 CHILD KEY
是固定类别标签或 allowlisted metric 名称（**非**行级值）；forbidden_key
检查对这些子键放宽，但其下的值仍会被扫描（仅允许 int/float/短字符串）。

Scanner 仅对最终公共 aggregate artifact 运行。内部 task/label/run JSONL
（包含路径/span/query/gold）仅保留在内存/临时 `/tmp` 下，永不针对公共
合约扫描，永不提交。

## Self-tests

`--self-test` 运行 179 个确定性检查，覆盖 19 组（无网络；合成行 +
合成 score 数据）：

1. 方法解析器（拒绝未知；去重；默认恰好 bm25,regex,symbol；跳过空 token；
   C5-C 拒绝 `text` 方法）。
2. 硬上限 row_limit=20（默认 20；上限 20；5 与 20 透传；拒绝 0）。
3. 方法结果记录（拒绝未知方法；拒绝 `text` 方法；接受 allowlisted 方法；
   拒绝非 allowlisted metric；allowlist 是 C5-A 子集；接受
   `aggregate_runtime_seconds`；拒绝非数值 runtime；拒绝意外 key）。
4. Delta 仅对 allowlisted metric 与 baseline bm25（排除 baseline 方法；
   仅 allowlisted metric；baseline 为 bm25；值正确性；baseline 缺失时为空；
   验证器拒绝 baseline 方法/非数值/非 allowlisted metric）。
5. 无 best_method / 推荐字段（scanner 拒绝全部 10 个推荐字段；干净报告
   缺失全部；`baseline_is_policy_candidate=false`；
   `default_should_change=false`）。
6. Scanner 拒绝非 allowlisted 的动态方法 key（dict 形状；非 dict 记录；
   缺失方法；非 allowlisted 方法；`text` 方法；接受干净列表）。
7. Scanner 拒绝 row/repo/query/gold/path/span/snippet/content_sha/
   stdout/stderr key（45 个 forbidden key）；拒绝 repo URL 值；拒绝 repo
   slug 值；拒绝 commit SHA 值。
8. 状态语义（全部通过 =>
   `contextbench_method_matrix_scale_smoke_pass`；混合 => `partial`；无 =>
   `unavailable_with_reason`；空 => `unavailable_with_reason`；pass 枚举
   是独立字符串）。
9. 生成在 scanner 失败时失败（干净报告不 raise；泄露 repo raise；
   `best_method` raise；`winner` raise；`recommended_default` raise；
   `method_results` dict raise；self-test 失败拒绝 artifact 生成）。
10. Artifact 身份字段（schema、claim、status、mode、phase、generated_by；
    self-test 通过时状态 pass）。
11. Safe true 标志存在 + 正确值（5 个标志；无 C5-B
    `method_matrix_smoke` 标志；无 C5-A
    `external_benchmark_rows_read` 标志）。
12. No-claim / no-runtime-change false 标志（14 个标志）。
13. License 字段（4 个字段）。
14. 不可用报告（真实；无 stale/fake pass；无 delta；forbidden scan pass；
    全部 method_results 不可用；有 input_summary）。
15. 公共 artifact 自扫描干净（skeleton + 不可用）。
16. CLI 参数面（`--self-test`、`--row-limit`、`--methods`、
    `--query-mode`、`--language-filter`、`--openlocus`、`--out`）。
17. `ALLOWED_METHODS` 恰好 `bm25,regex,symbol`；排除 `text`。
18. `input_summary` 形状（有 row_limit、methods、query_mode、
    language_filter、aggregate 计数）。
19. 方法结果记录中的 `aggregate_runtime_seconds`（存在；数值；
    scanner 接受）。

## 验证

```text
python3 -m py_compile eval/c5c_contextbench_verified_method_matrix_scale_smoke.py  => PASS
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py --self-test  => PASS (179/179 checks)
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py \
  --row-limit 20 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --out artifacts/c5c_contextbench_verified_method_matrix_scale/\
c5c_contextbench_verified_method_matrix_scale_report.json  => PASS
  (status: contextbench_method_matrix_scale_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_bounded_scale_method_matrix, phase: C5-C,
   methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0,
   rows_fetched: 20, rows_evaluated: 20, rows_successful: 20, rows_failed: 0,
   network_calls: 1, provider_calls: 0,
   retrieval_scale_smoke_performed: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false,
   promotion_ready: false, default_should_change: false,
   baseline_is_policy_candidate: false,
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

手动 CI run `27905621090`
（`c5-contextbench-method-matrix-scale-smoke`，
`enable_external_benchmark_network=true`，`row_limit=20`，
`methods=bm25,regex,symbol`）在 workflow 对 network-enabled run 改为
fail-closed 后成功完成。已提交 artifact 现在镜像该 sanitized aggregate CI report。

```text
status: contextbench_method_matrix_scale_smoke_pass
self_test_passed: true (179/179 checks)
forbidden_scan: pass
rows_fetched: 20
methods_successful: 3
methods_failed: 0
bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0
regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
regex-minus-bm25 file_recall@10 delta: -0.35
symbol-minus-bm25 file_recall@10 delta: -0.35
```

较早的手动 run `27905321437` 上传了绿色的 `unavailable_with_reason`
artifact。该结果被当作 fail-open bug，而不是经验性成功。workflow 现在要求
network-enabled C5-C CI 必须产出 `contextbench_method_matrix_scale_smoke_pass`
或 `partial`，`rows_fetched > 0`，且至少一个方法成功；否则 job 会以 sanitized
失败类别失败。


```text
python3 eval/c5c_contextbench_verified_method_matrix_scale_smoke.py \
  --row-limit 20 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --out artifacts/c5c_contextbench_verified_method_matrix_scale/\
c5c_contextbench_verified_method_matrix_scale_report.json
  => status: contextbench_method_matrix_scale_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 20, rows_evaluated: 20, rows_successful: 20, rows_failed: 0
  => methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => retrieval_scale_smoke_performed: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
```

20 行 ContextBench verified 行从 HF datasets-server **一次性**临时抓取（跨
全部 3 个方法共享），在内存中适配，引用仓库在临时 `/tmp` 目录下克隆到其
`base_commit`（每方法+每行一次），对每个仓库运行每种方法（`bm25`、
`regex`、`symbol`）的 OpenLocus 检索，`eval/score.py` 为每种方法产出
aggregate 检索 metrics。Aggregate metric 均值在每方法 20 个成功行上计算，
并写入提交的 artifact。无原始 ContextBench 行、queries、repo URL/名称、
base commit、gold paths/spans/contents、生成的 task/label/run JSONL、
evidence 行、克隆仓库或 stdout/stderr 被提交或上传。

如果未来环境中网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索
失败、打分失败），artifact 记录真实的 `unavailable_with_reason`，带有真实
的 `failure_reason_category` 与对应的 `failure_category_counts` 计数。绝不
写入 stale/fake pass。

## 注意事项

- C5-C 是公共 aggregate-only 外部 benchmark 检索方法矩阵 scale smoke
  artifact。它是 eval/diagnostic only。它**不**改变 runtime、retriever、
  pack、backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、**不是**
  promotion、**不是**默认变更、**不是**runtime-clean 通用算法声称、
  **不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，也**不是**下游
  agent 价值声称。
- C5-C **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的
  网络调用是对公共 HF datasets-server（**一次性**抓取有界 ContextBench
  verified 行，跨所有方法共享）与对公共 GitHub（在临时 `/tmp` 目录下克隆
  引用仓库到其 `base_commit`，每方法+每行一次）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-C 使用**有界 20 行 ContextBench verified subset**（每方法默认 20 行；
  硬上限 20）。这是 scale smoke，**不是**严格的 benchmark 评估。Aggregate
  metrics 是有界样本上的点估计，**不应**被解读为 benchmark 结果、
  leaderboard 条目或性能声称。
- C5-C 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`，每方法+每行
  一次（因为每种方法针对相同的行运行但在隔离工作区中）。克隆的仓库、生成
  的 task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在 `/tmp` 下，
  **绝不**提交或上传。提交的 artifact 仅包含 aggregate 计数/比率/均值与
  可选的每方法 aggregate runtime 秒数。
- C5-C **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别
  的诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-C **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。
  `baseline_is_policy_candidate=false`、`default_should_change=false`。
- C5-C **不**证明下游 agent 价值。检索 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

## 下一步

- C5-C 是有界 20 行外部-benchmark-形态的检索方法矩阵 scale smoke。完整
  的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/可行性阶段，需要严格的
  benchmark 设计、更大的样本量、多种方法与统计分析。
- 无 promotion、无默认变更、无 EvidenceCore 语义变更、无 runtime-clean
  通用算法声称、无下游 agent 价值声称、无 OOD 时间泛化声称，也无 QuIVer
  systems 声称来自 C5-C。
