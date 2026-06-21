# F1-B Retrieval-Derived Counterfactual Utility Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/f1b-retrieval-derived-counterfactual-utility.md`
> 一一对应。

## 范围与声明边界

F1-B 将 F1 从纯合成 context variants 推进到 **retrieval-derived**
counterfactual utility：使用真实 ContextBench verified rows、临时公开
repo clones、真实 OpenLocus retrieval 输出及 `eval/score.py` 指标，估计
candidate-set variants 的聚合边际效用。这是实证工作，不是控制面
artifact。

F1-B 明确**不是**下游效用声明，**不是** true E/S 校准，**不是**外部
基准测试性能声明，**不是** leaderboard 条目，**不是** promotion/
default/runtime/retriever/pack/backend/EvidenceCore 语义改动，也**不
是** live/provider 声明。它**不**进行任何 provider 调用，**不**进行
任何远程 provider 调用。

- 声明级别（claim_level）：
  `retrieval_derived_counterfactual_utility_smoke_only`。
- 模式（mode）：
  `public_aggregate_contextbench_retrieval_counterfactual`；阶段
  （phase）为 `F1-B`。
- 状态枚举：成功时为
  `retrieval_derived_counterfactual_utility_smoke_pass`；部分成功时
  为 `partial`；无/阻塞/网络不可用时为
  `unavailable_with_reason`；scanner 失败时为
  `fail_forbidden_scan`。
- F1-B 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游效
  用，**不是** true E/S 校准，**不是**外部基准测试性能声明，**不
  是** leaderboard 条目，也**不是** promotion。

### F1 -> F1-B 关系

```text
F1 counterfactual evidence utility smoke（合成/mock 任务）
-> F1-B retrieval-derived counterfactual utility smoke
   （真实 ContextBench verified rows；临时 /tmp clones；
    真实 OpenLocus retrieval；eval/score.py 指标；
    candidate-set variants 来自真实 retrieval；
    仅聚合公开 artifact；无 provider 调用）
```

## Candidate-set variants

F1-B 使用五个固定白名单 candidate-set variants（仅 records-shaped；
无动态 dict 镜像）：

1. **`baseline_empty_candidate_set`** — 空 candidate set（无
   retrieval）。所有指标按构造为零。
2. **`bm25_topk`** — BM25 retrieval candidates。
3. **`regex_topk`** — regex retrieval candidates。
4. **`symbol_topk`** — symbol retrieval candidates。
5. **`bm25_plus_symbol_topk`** — BM25 + symbol union candidates
   （通过 per-method 指标 max 近似聚合）。

### 延迟 variant

`bm25_plus_distractor_topk` **已延迟**。安全实现需要 per-candidate
身份跟踪（哪个 candidate 来自哪个方法，哪个是 distractor），这在公开
artifact 中有 candidate 身份泄露风险。它在 F1-B 中被省略，延迟到可以
安全跟踪 candidate provenance 而不泄露 per-candidate 行的未来阶段。

## Counterfactual effects

F1-B 使用四个固定白名单 counterfactual effects（仅 records-shaped；
每个固定记录一个指标）：

1. **`bm25_candidates_vs_empty`** — (bm25_topk - baseline_empty)。
2. **`regex_candidates_vs_empty`** — (regex_topk - baseline_empty)。
3. **`symbol_candidates_vs_empty`** — (symbol_topk - baseline_empty)。
4. **`symbol_added_to_bm25`** — (bm25_plus_symbol_topk - bm25_topk)。

### 延迟 effect

`distractor_added_to_bm25` **已延迟**（原因同上延迟 variant）。

## 指标

聚合 retrieval/score 效用指标（**不是**下游 agent 指标）：

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`

## CLI

```bash
python3 -m py_compile eval/f1b_retrieval_derived_counterfactual_utility_smoke.py
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py --self-test
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
    --out artifacts/f1b_retrieval_derived_counterfactual_utility/\
f1b_retrieval_derived_counterfactual_utility_report.json
# 覆盖 row limit 和 methods：
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
    --row-limit 5 --methods bm25,regex,symbol \
    --out /tmp/f1b_smoke_report.json
```

默认模式：运行真实网络 smoke（临时 HF rows + GitHub clones +
retrieval + score 写入 `/tmp`）。若网络/openlocus 不可用，产出真实的
`unavailable_with_reason` 报告。绝不进行 provider 调用。

CLI 参数：`--self-test`、`--out`、`--row-limit`（默认 5，硬上限
10）、`--methods`（默认 `bm25,regex,symbol`）、`--query-mode`（默认
`first_paragraph`）、`--language-filter`（默认 `python`）、
`--openlocus`。未知/私有外观参数被以通用 `invalid arguments` 消息拒绝
（SafeArgumentParser 模式）。

## 复用 helpers

F1-B 导入 C5-A helpers（向后兼容；C5-A **不**被修改）：

- `c5_contextbench_verified_performance_smoke._fetch_contextbench_rows`
- `c5_contextbench_verified_performance_smoke._sanitize_query`
- `c5_contextbench_verified_performance_smoke._parse_gold_context`
- `c5_contextbench_verified_performance_smoke._write_transient_jsonl`
- `c5_contextbench_verified_performance_smoke._resolve_openlocus_binary`
- `c5_contextbench_verified_performance_smoke._clone_and_checkout`
- `c5_contextbench_verified_performance_smoke._run_retrieval_and_score`
- `c5_contextbench_verified_performance_smoke._filter_score_metrics`

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/f1b_retrieval_derived_counterfactual_utility/f1b_retrieval_derived_counterfactual_utility_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` =
  `f1b_retrieval_derived_counterfactual_utility_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`methods`、`query_mode`、`language_filter`、
  `network_mode`、`openlocus_binary_source`。
- Safe true flags（仅当实际为 true 时）：
  `retrieval_derived_counterfactual_utility_smoke`、
  `external_benchmark_rows_read`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- Always-false no-claim flags：
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `downstream_agent_value_proven`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- `variant_results`：固定记录列表
  `{variant, row_count, file_recall@10, mrr, span_f0.5@10,
  success_rate, failure_category_counts}`。
- `counterfactual_effects`：固定记录列表
  `{baseline_variant, treatment_variant, effect_name, metric, delta}`。
- `method_inputs`：固定记录列表 `{method, row_count}`。
- `input_summary`：`row_limit_requested`、`methods`、`query_mode`、
  `language_filter`、`variants`、`effects`、`metrics`、聚合 row 计数。
- `failure_category_counts`：仅固定类别计数。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。
- `framing`：固定 no-claim framing 字段。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝
forbidden dict key 在任何位置出现（`task_id`、`repo_url`、
`base_commit`、`query`、`gold`、`gold_paths`、`gold_lines`、
`gold_context`、`path`、`file`、`snippet`、`code`、`patch`、`diff`、
`stdout`、`stderr`、`content_sha`、`candidate`、`evidence`、`winner`、
`best`、`recommended_default`、`api_key`、`base_url`、`provider_key`、
`secret`、`token`、`model_id_raw`、`E_primary`、`S_support` 等）及
value 模式：任意 URL（无 URL 允许列表）、32+ 字符 hex digest、40 字符
commit SHA、secret-like 字符串、带文件扩展名的 path-like 字符串、
`/tmp/` 工作区路径、`task_N` 任务标识、repo slug、patch/diff 标记、
堆栈跟踪、多行字符串、raw JSON 片段、raw 行范围、raw model 路由前缀
及 self-test sentinel。

**不**输出 `winner` / `best` / `recommended_default` 字段。**不**使用
E/S 校准记法（`E_primary` / `S_support`）。

scanner 仅对最终公开聚合 artifact 运行。内部 task/label/run JSONL（含
路径/span/query/gold）仅保留在内存或 `/tmp`，绝不对公开契约扫描，绝
不提交。

## Self-tests

- Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
- Safe true flags 存在；no-claim flags 为 false。
- Variants 和 effects 为固定白名单。
- Records-shaped 容器（`variant_results`、`counterfactual_effects`、
  `method_inputs` 为列表；无动态 dict 镜像）。
- Variant 指标提取（空 candidate set -> 零；合成 score 指标提取；
  缺失指标 -> 0.0）。
- Variant 聚合（row 计数；mean 计算）。
- Counterfactual effects 计算（records-shaped；bm25_vs_empty 和
  symbol_added_to_bm25 的 delta 正确）。
- scanner 拒绝：repo URL、文件路径、commit SHA、repo slug、task_id key、
  query key、gold key、content_sha key、candidate key、evidence key、
  winner key、best key、recommended_default key、raw 路由前缀、
  URL value、tmp 路径、stdout key、provider key、sentinel canary。
- scanner 允许：variant 名称、effect 名称、metric 名称、method 名称、
  variant_results 记录、counterfactual_effects 记录、failure category
  token。
- fail-closed 生成：干净 report 不 raise；泄漏 report raise
  SystemExit；self-test 失败拒绝生成 artifact。
- 公开 artifact 自扫描干净（无任何 forbidden key）。
- CLI 参数面。

## 验证

```text
python3 -m py_compile eval/f1b_retrieval_derived_counterfactual_utility_smoke.py  => PASS
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py --self-test  => PASS (95/95 checks)
python3 eval/f1b_retrieval_derived_counterfactual_utility_smoke.py \
  --out artifacts/f1b_retrieval_derived_counterfactual_utility/\
f1b_retrieval_derived_counterfactual_utility_report.json  => PASS
  (status: retrieval_derived_counterfactual_utility_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   rows_fetched: 5, rows_successful: 5,
   retrieval_derived_counterfactual_utility_smoke: true,
   external_benchmark_rows_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 注意事项

- F1-B 是公开仅聚合 retrieval-derived counterfactual utility smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、
  pack、backend 或 default policy；它**不**改变 EvidenceCore 语义。
  它**不是**基准测试结果，**不是**下游效用，**不是** true E/S 校
  准，**不是**外部基准测试性能声明，**不是** leaderboard 条目，也
  **不是** promotion。
- F1-B **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。它使用真实 ContextBench verified rows、临时 GitHub clones、真实
  OpenLocus retrieval 和 `eval/score.py` 指标。所有临时数据（rows、
  queries、gold labels、retrieval JSONL、scoring JSONL、repo URLs、
  commits、paths、spans、candidates、stdout/stderr）仅保留在内存或
  `/tmp`，**绝不**提交或上传。
- F1-B **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- F1-B **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- F1-B **不**声明外部基准测试性能。
  `external_benchmark_performance_claimed=false`。
- F1-B **不**输出 winner/best/recommended-default 字段。
- F1-B **不**使用 E/S 校准记法（`E_primary` / `S_support`）。
- `bm25_plus_distractor_topk` variant 和 `distractor_added_to_bm25`
  effect **已延迟**（安全实现需要 per-candidate 身份跟踪，有泄露风
  险；延迟到未来阶段）。
- `bm25_plus_symbol_topk` variant 使用近似聚合（per-method 指标
  max），而非真正的 union candidate set。这是 smoke 级近似，**不
  是**精确 union 指标。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  smoke-claimed 标志（`retrieval_derived_counterfactual_utility_smoke`、
  `external_benchmark_rows_read`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`）**仅**在真实网络 run 实际执行时为
  true。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
