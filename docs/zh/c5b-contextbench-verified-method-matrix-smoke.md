# C5-B ContextBench Verified 检索方法矩阵 Smoke

日期：2026-06-21（C5-B 外部 benchmark 检索方法矩阵 smoke，基于 ContextBench
verified subset，将 C5-A 单方法 smoke 扩展为有界多方法矩阵 smoke）

C5-B 是 C5-A 外部-benchmark-形态检索性能 smoke 的**有界多方法矩阵扩展**。
它从 HuggingFace datasets-server 读取有界的 ContextBench verified subset
**一次**，在临时 `/tmp` 工作区中检出引用仓库到 `base_commit`，并在请求的
方法矩阵（默认 `bm25,regex,symbol`；允许 `bm25,regex,text,symbol`；固定
`baseline_method=bm25`）上运行 OpenLocus 检索，通过现有 `eval/score.py`
逻辑对每种方法针对 ContextBench `gold_context` spans 打分。它**仅提交一个
aggregate 公共报告**，其中包含每方法 aggregate metrics（记录列表，**非**
动态方法键 dict）以及仅 aggregate 的、与固定 `bm25` baseline 的 delta。

C5-B 明确**不是**严格的 benchmark 结果，**不是**leaderboard 条目，**不是**
性能声称，**不是**promotion，**不是**默认/策略变更，也**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它**不**输出
`winner`、`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。
`baseline_is_policy_candidate=false` 与 `default_should_change=false` 是固定的。

> **重要 claim 边界。** C5-B 输出 `claim_level =
> external_benchmark_retrieval_method_matrix_smoke_only`。它**不**声称外部
> benchmark 结果、**不**声称 leaderboard 条目、**不**声称性能、**不**
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

将 C5-A 单方法 ContextBench verified 检索性能 smoke 扩展为有界多方法矩阵
smoke：

- 从 HuggingFace datasets-server `/rows` 端点读取有界的 ContextBench
  verified subset **一次**（跨所有方法共享）；
- 将原始 ContextBench 行、queries/problem statements、repo URL/名称、
  base commits、gold paths/spans/contents、生成的 task/label/run JSONL、
  evidence rows 与克隆的源仓库**仅在**`/tmp` 或 CI 临时工作区中**临时**
  保留；
- 通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
  在 `base_commit` 检出引用仓库；
- 在请求的方法矩阵上运行 OpenLocus 检索（默认 `bm25,regex,symbol`；允许
  `bm25,regex,text,symbol`；固定 `baseline_method=bm25`；无 provider/model
  调用）；
- 通过现有 `eval/score.py` 逻辑对每种方法针对 ContextBench `gold_context`
  spans 打分；
- 仅提交一个 aggregate 公共报告，其中包含每方法记录和仅 aggregate 的、与
  固定 `bm25` baseline 的 delta。

这是经验性方法矩阵 smoke，**不是**另一个就绪/控制面阶段。它也**不是**严格的
benchmark 声称、promotion、默认策略变更、leaderboard 条目或下游-agent 价值
声称。

## C5-A -> C5-B 关系

```text
C5-A ContextBench verified 检索性能 smoke
  （单方法；默认 bm25；有界 ContextBench verified subset；
   临时 /tmp clone + retrieval + score；aggregate-only 公共 artifact；
   无 provider 调用；不提交 raw rows/queries/repo URLs/commits/
   gold paths/spans/JSONL/evidence rows/cloned repos/stdout/stderr）
-> C5-B ContextBench verified 检索方法矩阵 smoke
   （多方法矩阵；默认 bm25,regex,symbol；允许
    bm25,regex,text,symbol；固定 baseline_method=bm25；
    跨方法共享行抓取；每方法 aggregate 记录；
    仅 aggregate 的与 bm25 的 delta；aggregate-only 公共 artifact；
    无 provider 调用；无 winner/best_method/recommended_default）
```

C5-B **不是** C5。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/
可行性阶段，需要严格的 benchmark 设计、更大的样本量、多种方法与统计分析。
C5-B 仅通过在有界 ContextBench verified subset 上运行真实的 OpenLocus
检索 + 打分管线跨请求的方法矩阵，产出第一个经验性外部-benchmark-形态的
检索方法矩阵 smoke。

## 实现

### Evaluator

`eval/c5b_contextbench_verified_method_matrix_smoke.py` 提供 argparse CLI：

- `--self-test` —— 无网络合成 self-test（154 组断言）。
- `--row-limit` —— 每方法评估的 ContextBench verified 行数；默认 5，硬上限
  10（C5-B 比 C5-A 更严格，因为每行跨多种方法评估）。
- `--methods` —— 逗号分隔的 OpenLocus 检索方法；默认 `bm25,regex,symbol`；
  允许 `bm25,regex,text,symbol`；未知方法被拒绝；重复方法被确定性去重
  （保留首次出现顺序）。
- `--query-mode` —— query sanitizer 模式；默认 `first_paragraph`；允许
  `first_paragraph`、`first_sentence`、`raw`。
- `--language-filter` —— 语言过滤类别；默认 `python`；允许 `python`、
  `all`（仅为类别桶 —— 永不在内存范围外泄露原始行值）。
- `--openlocus` —— 可选的 OpenLocus 二进制路径（默认
  `target/release/openlocus`，然后回退到 `target/debug/openlocus`；
  解析为绝对路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>`
  运行）。
- `--out` —— 输出 artifact JSON 路径；默认
  `artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`。

未知/私有的参数会被拒绝，并显示固定的 `invalid arguments` 消息，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### 复用 C5-A helper

C5-B 是一个独立脚本，将 C5-A 作为 helper 模块导入
（`import c5_contextbench_verified_performance_smoke as c5a`）。它复用了
显式可安全共享的 C5-A 原语：

- 行抓取：`c5a._fetch_contextbench_rows`（分页 HF datasets-server `/rows`
  访问；仅 stdlib `urllib`；有界超时）。
- Query sanitizer：`c5a._sanitize_query`（仅内存中；first paragraph /
  first sentence / raw；剥离 HTML 注释、HTML 标签、markdown header、code
  fence；限制长度）。
- Gold context 解析：`c5a._parse_gold_context`（临时
  `gold_paths`/`gold_lines`；`content` 字段**绝不**读取或持久化）。
- 克隆 + 检出：`c5a._clone_and_checkout`（每行 `TemporaryDirectory`；
  `git clone --filter=blob:none --no-checkout` 然后 `git checkout`；
  有界超时）。
- 临时 JSONL 写入：`c5a._write_transient_jsonl`（仅在 `TemporaryDirectory`
  下）。
- 检索 + 打分 runner：`c5a._run_retrieval_and_score`
  （`eval/run_retrieval.py` 然后 `eval/score.py`；仅 aggregate JSON）。
- OpenLocus 二进制解析：`c5a._resolve_openlocus_binary`
  （release 然后 debug 回退；绝对路径）。
- 失败类别：`c5a.FAILURE_CATEGORIES`（固定 enum）。
- Score metric allowlist：`c5a.SCORE_METRIC_ALLOWLIST`（C5-B 的
  `METHOD_METRIC_ALLOWLIST` 是严格子集）。
- Scanner 原语：`c5a._scan_forbidden`（原始 key/value 泄露检测）、
  `c5a._refuse_on_self_test_failure`、`c5a._now_iso`、`c5a._write_json`、
  `c5a._check`。
- Query 模式 / 语言过滤器：`c5a.ALLOWED_QUERY_MODES`、
  `c5a.DEFAULT_QUERY_MODE`、`c5a.ALLOWED_LANGUAGE_FILTERS`、
  `c5a.DEFAULT_LANGUAGE_FILTER`。
- License 字段：`c5a.LICENSE_FIELDS`。

### C5-B 拥有的 schema / claim 字段

C5-B 拥有自己的 schema、claim 字段、方法矩阵聚合、方法 allowlist 校验与
矩阵 self-test：

- `SCHEMA_VERSION = "c5b_contextbench_verified_method_matrix_smoke.v1"`
- `GENERATED_BY = "eval/c5b_contextbench_verified_method_matrix_smoke.py"`
- `CLAIM_LEVEL = "external_benchmark_retrieval_method_matrix_smoke_only"`
- `MODE = "contextbench_verified_retrieval_method_matrix_smoke"`
- `PHASE = "C5-B"`
- `ALLOWED_METHODS = ("bm25", "regex", "text", "symbol")`
- `DEFAULT_METHODS = ("bm25", "regex", "symbol")`
- `BASELINE_METHOD = "bm25"`
- `DELTA_METRIC_ALLOWLIST = ("file_recall@10", "mrr", "span_f0.5@10",
  "success_rate")`（C5-A `SCORE_METRIC_ALLOWLIST` 的严格子集）。
- `METHOD_METRIC_ALLOWLIST = DELTA_METRIC_ALLOWLIST`（每方法 metrics 限于
  同一 allowlist）。
- `FORBIDDEN_RECOMMENDATION_FIELDS = {"winner", "best_method",
  "recommended_default", "recommended_method", "preferred_method",
  "default_method", "policy_decision", "decision", "ranking", "rank"}`
  （这些 key **绝不**出现在公共 artifact 的任何位置）。

### Runtime 流程

1. Self-test 必须在任何 artifact 写入之前通过
   （`c5a._refuse_on_self_test_failure`）。
2. 解析 `--methods`（C5-B 拥有的 `parse_methods`）：空/None -> 默认
   `["bm25", "regex", "symbol"]`；每个 token 必须在 `ALLOWED_METHODS` 中；
   重复方法被确定性去重（保留首次出现顺序）；空 token 被跳过。无效配置时，
   产出 `fail_schema_contract` 报告。
3. 校验 `--row-limit`（C5-B 硬上限 10）。
4. 将 OpenLocus 二进制解析为绝对路径（release 然后 debug 回退）。如果缺失，
   产出真实的 `unavailable_with_reason`，带
   `failure_reason_category=retrieval_failed`。
5. 从 HF datasets-server `/rows` 端点抓取有界 ContextBench verified 行
   **一次**（跨所有方法共享；分页；仅 stdlib `urllib`；有界超时）。在内存中
   按 `language_filter`（仅为类别桶）过滤。
6. 对请求方法矩阵中的每种方法：
   - 对每一行（有界到 `row_limit`）：
     - 将 `gold_context` JSON 解析为临时 `gold_paths`/`gold_lines`
       （`content` 字段**绝不**读取或持久化）。
     - 将 `problem_statement` sanitizer 为检索 query（仅内存中；
       first paragraph / first sentence / raw；剥离 HTML 注释、HTML 标签、
       markdown header、code fence；限制长度）。
     - 在每行 `TemporaryDirectory` 下通过
       `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
       克隆 `repo_url` 到 `base_commit`（有界超时）。
     - 在 `TemporaryDirectory` 下生成临时 task/label JSONL。
     - 通过 `eval/run_retrieval.py`
       （`--method <method> --cwd <repo_root>`）运行 OpenLocus 检索。
     - 运行 `eval/score.py` 并解析 aggregate metrics。
   - 在成功行上聚合该方法的 metrics（每个 allowlisted 数值 metric 的均值；
     `success_rate` 由 `rows_successful / rows_evaluated` 重新计算）。
   - 构建一个方法结果记录（list 元素，**非** dict key）。
7. 计算与固定 `baseline_method=bm25` 的 aggregate delta
   （delta = method_metric - baseline_metric；仅对
   `DELTA_METRIC_ALLOWLIST` metrics；baseline 排除在 delta 列表外；
   baseline 缺失时为空列表 —— 无 fake zero）。
8. 从方法结果计算总体状态（全成功 -> pass；混合 -> partial；无成功 ->
   unavailable_with_reason）。
9. 构建 aggregate-only 公共报告，带 fail-closed C5-B forbidden scan。

### 公共 artifact 身份

提交的 artifact 位于
`artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`，
是公共 aggregate-only smoke artifact。身份/边界字段：

- `schema_version` = `c5b_contextbench_verified_method_matrix_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- `status`：`pass` | `partial` | `unavailable_with_reason` |
  `fail_schema_contract` | `fail_forbidden_scan`
- `methods_requested`、`methods_allowed`、`baseline_method`、`query_mode`、
  `language_filter`、`network_mode`、`openlocus_binary_source`。
- `row_limit_requested`、`rows_fetched`、`methods_count`、
  `methods_attempted`、`methods_successful`、`methods_succeeded`、
  `methods_failed`、`network_calls`、
  `provider_calls=0`。
- `method_results`：记录列表（**非**以方法名为 key 的 dict）：
  ```json
  {"method":"bm25","status":"pass","rows_evaluated":5,
   "rows_successful":5,"rows_failed":0,"metrics":{...},
   "failure_category_counts":{...}}
  ```
- `smoke_metric_deltas_vs_baseline`：记录列表，每条记录对应一个 metric
  （仅 baseline 以外的方法；仅 `DELTA_METRIC_ALLOWLIST` metrics）：
  ```json
  {"baseline_method":"bm25","method":"regex",
   "metric":"mrr","delta":-0.075}
  ```
- `failure_reason_category`（仅在 `unavailable_with_reason` /
  `fail_schema_contract` 状态）。
- `failure_category_counts`：仅固定 enum 类别（跨方法聚合）。
- Safe true 标志（仅当实际为真时为 true）：
  `external_benchmark_rows_read`、`repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `method_matrix_smoke`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- 无声明 / 无运行时变更标志（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`baseline_is_policy_candidate`、
  `runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、
  `backend_changed`、`default_policy_changed`、
  `evidencecore_semantics_changed`、`provider_calls_made`、
  `remote_provider_calls_made`。
- License 字段（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Aggregate metrics

每个方法结果记录中的 `metrics` 块仅包含 allowlisted 的 aggregate metric
名称与数值，来自 `eval/score.py`。无行级记录、无 row ID、无路径、无 span、
无 snippet、无 content_sha。Allowlisted metric 名称（C5-A
`SCORE_METRIC_ALLOWLIST` 的严格子集）：

- `file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。

`smoke_metric_deltas_vs_baseline` 记录每条只包含一个 allowlisted metric，按
`method_metric - baseline_metric` 为 baseline 以外的每种方法计算。baseline
方法本身排除在 delta 列表外（方法不与自己比较）。如果 baseline 方法缺失或
没有 metrics，则不输出 delta（空列表，**非** fake zero）。

`failure_category_counts` 块（顶层和每方法结果记录中都有）仅包含固定 enum
类别标签（**非**行级值）：

- `network_fetch_failed`、`row_parse_failed`、
  `gold_context_parse_failed`、`language_filter_excluded`、
  `clone_failed`、`checkout_failed`、`task_jsonl_write_failed`、
  `label_jsonl_write_failed`、`retrieval_failed`、`score_failed`、
  `no_python_rows`、`row_limit_capped`、`scanner_self_test_failed`、
  `forbidden_leak_blocked`、`unexpected_exception`。

### 状态语义

- `pass`：所有请求方法都有至少一个成功的评估行且 scanner 通过。
- `partial`：至少一个方法成功且至少一个方法失败/不可用。
- `unavailable_with_reason`：无方法完成检索+打分。
- `fail_schema_contract`：无效方法配置、意外 metric key、不安全 artifact
  结构。
- `fail_forbidden_scan`：scanner 失败。

### 不可用模式

如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索失败、打分
失败等），artifact 记录真实的 `unavailable_with_reason`，带真实的
`failure_reason_category` 与对应的 `failure_category_counts` 计数。绝不
写入 stale/fake pass。在不可用模式下：

- `status=unavailable_with_reason`。
- `method_results` 是一个记录列表，每请求方法一条，每条
  `status=unavailable_with_reason` 且 `metrics={}` 为空。
- `smoke_metric_deltas_vs_baseline=[]`（无 delta）。
- `method_matrix_smoke=false`。
- `openlocus_retrieval_executed=false`。
- `score_py_metrics_computed=false`。
- `repositories_materialized_transiently=false`。
- `external_benchmark_rows_read=true` 仅当失败前实际抓取了行。
- `aggregate_only_public_artifact=true` 与 `diagnostic_only=true`
  保持 true。

## 隐私 / license 边界

公共 artifact 与 docs 保持 aggregate-only。以下**不**持久化在任何公共
artifact 或 doc 中：

- 原始 ContextBench 行与 gold label；
- 行级 task instance 值、instance ID、original_inst_id；
- repo URL、repo 名称、base commit、repo 路径、cloned repo 路径；
- 文件路径、span、行范围、snippet、gold content；
- problem statement / query（仅内存中 sanitizer）；
- patch、test patch、f2p、p2p；
- 生成的 task/label/run JSONL（仅在 `/tmp` 临时）；
- OpenLocus evidence 行、snippet、路径、行范围、content_sha；
- retrieved 路径/snippet/content_sha；
- 每行 metrics、行级 hash；
- 原始日志、stdout、stderr；
- 克隆仓库/源文件（仅在 `/tmp` 临时）。

公共 artifact 仅记录：来自 `eval/score.py` 的 aggregate metric 均值/比率/
计数（allowlisted）、与固定 `bm25` baseline 的仅 aggregate delta
（allowlisted）、固定失败类别计数、固定配置标签
（methods_requested/methods_allowed 类别、方法结果方法名、query_mode、
language_filter 类别）、行计数、网络/provider 调用计数与确定性的
`generated_by` 路径。

ContextBench 数据集 license 未知
（`unknown_dataset_license`）；行级再分发被禁用
（`row_level_redistribution_allowed=false`），派生行级发布被禁用
（`derived_row_level_publication_allowed=false`）。Aggregate metrics
发布允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 在无 HuggingFace/GitHub 时通过。
- 真实矩阵 smoke 需要公共网络访问 HF datasets-server 与 GitHub repo。CI
  是单独的显式 `workflow_dispatch` 作业，带
  `enable_external_benchmark_network=true` 输入。它**不**在 PR/push 时默认
  运行，无 provider secrets/vars，无 `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING`
  env，仅上传 aggregate 临时报告。
- 如果 `enable_external_benchmark_network` 为 false，workflow 是 no-op，
  显示明确消息并以 0 退出（self-test + py_compile 仍运行；no-op 模式下不
  产出 aggregate 报告）。
- Workflow 在 smoke 后校验报告的 claim 边界标志：
  `aggregate_only_public_artifact=true`、`diagnostic_only=true`；所有
  无声明 / 无运行时变更标志为 false；`baseline_is_policy_candidate=false`、
  `default_should_change=false`、`leaderboard_entry_claimed=false`；
  license 字段固定；`provider_calls=0`；
  `forbidden_scan.status=pass`；`self_test_passed=true`；`status` 在
  （pass, partial, unavailable_with_reason）中（无 stale/fake pass；无
  `fail_schema_contract` / `fail_forbidden_scan`）；无 `winner`、
  `best_method` 或 `recommended_default` 字段。

## Forbidden scanner（公共，fail-closed）

C5-B 复用 C5-A forbidden scanner 原语进行原始 key/value 泄露检测（URL、
hex digest、repo slug、/tmp 路径、patch marker、stack trace、secret 等），
并**新增** C5-B 特定检查：

- 如果 `method_results` 是以方法名为 key 的 dict，则拒绝（C5-B 要求记录
  列表，**非** dict）。dict 形态会将方法名作为动态 dict key 泄露。
- 拒绝每个 `method` 值不在 `ALLOWED_METHODS` 中的方法结果记录（防御性，
  防止篡改以伪造非 allowlisted 方法）。
- 拒绝任何位置的 `FORBIDDEN_RECOMMENDATION_FIELDS` key（`winner`、
  `best_method`、`recommended_default`、`recommended_method`、
  `preferred_method`、`default_method`、`policy_decision`、`decision`、
  `ranking`、`rank`）。
- 拒绝任何位置的 C5-B 特定额外 forbidden key：`row`、`rows_data`、
  `raw_row`、`raw_rows`、`repo_name`、`repo_slug`、`query_text`、`gold`、
  `gold_path`、`gold_span`、`gold_snippet`、`snippet`、`snippets`、
  `content_sha`、`stdout`、`stderr`、`stdout_text`、`stderr_text`、
  `evidence_row`、`evidence_rows`、`retrieved_path`、`retrieved_paths`、
  `retrieved_snippet`、`cloned_repo_path`、`cloned_repo`、
  `per_row_metrics`、`row_metrics`。

C5-B scanner 还过滤掉一个 C5-A false positive：方法名字符串 `"text"`
作为值出现在 `methods_allowed`/`methods_requested` 下时，会被 C5-A
scanner 标记为 `forbidden_field_name_value`（因为 `text` 是 C5-A 合约中的
forbidden CONTENT/KEY 名）。在 C5-B 中，`text` 也是一个合法的 OpenLocus
检索方法名，因此它可以作为值出现在 `methods_allowed`/`methods_requested`
下。C5-B scanner 过滤掉该单点 false positive（仅针对 C5-B 特定安全值路径
上的 `forbidden_field_name_value` 违规）；所有其他 C5-A 违规保留。

`failure_category_counts`、`metrics` 与 `smoke_metric_deltas_vs_baseline` 容器是 C5-B
schema-key 容器，其 CHILD KEY 是固定类别标签或 allowlisted metric 名称
（**非**行级值）；forbidden_key 检查对这些子键放宽，但其下的值仍会被
扫描。

Scanner 仅对最终的公共 aggregate artifact 运行。内部 task/label/run JSONL
（包含 path/span/query/gold）仅保留在 `/tmp` 下的内存/临时中，永不针对
公共合约扫描，永不提交。

## Self-tests

`--self-test` 运行 154 个确定性检查，跨 18 组（无网络；合成行 + 合成打分
数据）：

1. 方法 parser（拒绝未知方法；确定性去重重复方法；默认
   `bm25,regex,symbol`；跳过空 token；保留首次出现顺序）。
2. 硬上限 `row_limit=10` 强制（默认 5；硬上限 10；拒绝零；超过 10 时
   截断；在 5 时通过）。
3. 方法结果记录要求 allowlisted 方法值（拒绝未知方法；拒绝非 allowlisted
   metric key；接受 allowlisted 方法；方法 metric allowlist 是 C5-A
   score allowlist 的子集）。
4. Delta 仅针对 allowlisted metrics 与 baseline `bm25`（排除 baseline
   方法；仅 `DELTA_METRIC_ALLOWLIST` metrics；baseline 方法为 `bm25`；
   regex mrr 的 delta 值正确性；baseline 缺失时为空；delta validator 拒绝
   baseline 方法；拒绝非数值）。
5. 无 `best_method` / 推荐字段（scanner 拒绝每个 forbidden 推荐
   字段 key；clean report 缺失每个字段；
   `baseline_is_policy_candidate=false`；`default_should_change=false`）。
6. Scanner 拒绝非 allowlisted 的动态方法 key（如果存在 dict 形态）（拒绝
   `method_results` 为 dict；拒绝非 dict 记录；拒绝缺失方法；拒绝非
   allowlisted 方法；接受 clean 记录列表）。
7. Scanner 拒绝 row/repo/query/gold/path/span/snippet/content_sha/
   stdout/stderr key（35 个 forbidden key 注入）。
8. 状态语义（全成功 -> pass；混合 -> partial；无成功 -> unavailable；
   空 -> unavailable）。
9. 如果 scanner 失败，生成失败（clean report 不抛出；泄露 report 抛出；
   `best_method` 抛出；`method_results` dict 抛出；self-test 失败拒绝
   artifact 生成）。
10. Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
11. Safe true 标志存在 + 正确值（7 个标志）。
12. 无声明 / 无运行时变更 false 标志（14 个标志）。
13. License 字段（4 个字段）。
14. 不可用报告（真实；无 stale/fake pass；无 delta；所有方法结果
    unavailable；forbidden scan pass）。
15. 公共 artifact 自扫描干净（clean + unavailable）。
16. CLI 参数表面（`--self-test`、`--row-limit`、`--methods`、
    `--query-mode`、`--language-filter`、`--openlocus`、`--out`）。
17. Schema 合约失败（`fail_schema_contract` 状态；无 method_results；
    forbidden scan pass）。
18. `ALLOWED_METHODS` 恰好为 `bm25,regex,text,symbol`。

## 验证

```text
python3 -m py_compile eval/c5b_contextbench_verified_method_matrix_smoke.py  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py --self-test  => PASS (161/161 checks)
cargo build --locked --release -p openlocus-cli  => PASS
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \
  --row-limit 5 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --openlocus target/release/openlocus \
  --out artifacts/c5b_contextbench_verified_method_matrix/\
c5b_contextbench_verified_method_matrix_report.json  => PASS
  (status: pass, forbidden_scan: pass, self_test_passed: true,
   mode: contextbench_verified_retrieval_method_matrix_smoke, phase: C5-B,
   methods: [bm25, regex, symbol], methods_attempted: 3,
   methods_successful: 3, methods_succeeded: 3, methods_failed: 0,
   rows_fetched: 5, network_calls: 1, provider_calls: 0,
   baseline_method: bm25, baseline_is_policy_candidate: false,
   default_should_change: false,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   method_matrix_smoke: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
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
python3 eval/c5b_contextbench_verified_method_matrix_smoke.py \
  --row-limit 5 --methods bm25,regex,symbol \
  --query-mode first_paragraph --language-filter python \
  --openlocus target/release/openlocus \
  --out artifacts/c5b_contextbench_verified_method_matrix/\
c5b_contextbench_verified_method_matrix_report.json
  => status: pass, forbidden_scan: pass, self_test_passed: true
  => rows_fetched: 5, methods: [bm25, regex, symbol]
  => methods_attempted: 3, methods_successful: 3, methods_succeeded: 3,
     methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => baseline_method: bm25
  => external_benchmark_rows_read: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => method_matrix_smoke: true
```

5 个 ContextBench verified 行从 HF datasets-server 临时抓取**一次**（跨 3
种方法共享），在内存中适配，引用仓库在临时 `/tmp` 目录下克隆到其
`base_commit`，对每个仓库运行 OpenLocus `bm25`、`regex`、`symbol` 检索，
`eval/score.py` 产出每种方法的 aggregate 检索 metrics。aggregate metric
均值（file recall@10、MRR、span F0.5@10、success_rate）跨每方法 5 个成功
行计算，并以每方法记录形式写入提交的 artifact。与固定 `bm25` baseline 的
仅 aggregate delta 为 `regex` 与 `symbol` 计算。无原始 ContextBench 行、
queries、repo URL/名称、base commit、gold paths/spans/contents、生成的
task/label/run JSONL、evidence 行、克隆仓库或 stdout/stderr 被提交或上传。

如果网络 smoke 在未来环境中无法完成（网络/HF/GitHub 失败、克隆超时、检索
失败、打分失败），artifact 记录真实的 `unavailable_with_reason`，带真实
的 `failure_reason_category` 与对应的 `failure_category_counts` 计数。绝不
写入 stale/fake pass。

## 注意事项

- C5-B 是公共 aggregate-only 外部 benchmark 检索方法矩阵 smoke artifact。
  它是 eval/diagnostic only。它**不**改变 runtime、retriever、pack、
  backend 或默认策略；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是**leaderboard 条目、**不是**性能声称、**不是**
  promotion、**不是**默认变更、**不是**runtime-clean 通用算法声称、
  **不是**OOD 时间泛化声称、**不是**QuIVer systems 声称，也**不是**下游
  agent 价值声称。
- C5-B **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。固定 `baseline_method` 为 `bm25`、
  `baseline_is_policy_candidate=false`、`default_should_change=false`。
- C5-B **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的
  网络调用是对公共 HF datasets-server（抓取有界 ContextBench verified 行
  **一次**，跨方法共享）与对公共 GitHub（在临时 `/tmp` 目录下每方法克隆
  引用仓库到其 `base_commit`）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-B 使用**有界 ContextBench verified subset**（默认 5 行；硬上限 10 行；
  每方法）。这是 smoke，**不是**严格的 benchmark 评估。Aggregate metrics
  是小样本上的点估计，**不应**被解读为 benchmark 结果、leaderboard 条目、
  性能声称或方法推荐。
- C5-B 在临时 `/tmp` 目录下检出引用仓库到其 `base_commit`。克隆的仓库、
  生成的 task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在
  `/tmp` 下，**绝不**提交或上传。提交的 artifact 仅包含 aggregate
  计数/比率/均值与仅 aggregate 的 delta。
- C5-B **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别的
  诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-B **不**证明下游 agent 价值。检索矩阵 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- ContextBench 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics
  发布允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

## 下一步

- C5-B 是第一个外部-benchmark-形态的检索方法矩阵 smoke，扩展 C5-A 的单方法
  smoke。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/可行性阶段，
  需要严格的 benchmark 设计、更大的样本量、多种方法与统计分析。
- 不因 C5-B 产生 promotion、默认变更、EvidenceCore 语义变更、runtime-clean
  通用算法声称、下游 agent 价值声称、OOD 时间泛化声称或 QuIVer systems
  声称。
