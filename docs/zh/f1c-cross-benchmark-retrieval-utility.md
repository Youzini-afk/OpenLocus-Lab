# F1-C Cross-Benchmark Retrieval-Derived Utility Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/f1c-cross-benchmark-retrieval-utility.md`
> 一一对应。

## 范围与声明边界

F1-C 是 **跨基准测试** retrieval-derived utility smoke。它对两个
benchmark 形态的检索样本（ContextBench verified 20 行 + RepoQA 10
needle Python）**重新运行真实有界外部数据**，然后按 benchmark/
method 计算固定 retrieval-derived utility proxy、跨基准加权均值与
counterfactual effects。F1-C **不是**现有 C5 aggregate JSON artifact 的
rollup：它调用真实的 C5-C ContextBench matrix runner 与 C5-E RepoQA
matrix runner，物化临时 `/tmp` clone，运行真实 OpenLocus retrieval，
并运行 `eval/score.py`。

F1-C 明确**不是**下游效用声明，**不是** true E/S 校准，**不是**外部
基准测试性能声明，**不是** leaderboard 条目，**不是**方法 winner
声明，**不是** promotion/default/runtime/retriever/pack/backend/
EvidenceCore 语义改动，也**不是** live/provider 声明。它**不**进行
任何 provider 调用，**不**进行任何远程 provider 调用。

- 声明级别（claim_level）：
  `cross_benchmark_retrieval_derived_utility_smoke_only`。
- 模式（mode）：
  `bounded_contextbench_repoqa_retrieval_utility`；阶段
  （phase）为 `F1-C`。
- 状态枚举：成功时为
  `cross_benchmark_retrieval_utility_pass`（两基准都 pass 且 bm25
  在两基准上都成功）；部分成功时为 `partial_with_exclusions`
  （至少一个基准 pass 且 bm25 至少在一个基准上成功）；
  无/阻塞/网络不可用时为 `unavailable_with_reason`；scanner 失败
  时为 `fail_forbidden_scan`；方法配置/形状无效时为
  `fail_schema_contract`。
- F1-C 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游效
  用，**不是** true E/S 校准，**不是**外部基准测试性能声明，**不
  是** leaderboard 条目，**不是**方法 winner，也**不是** promotion。

### F1-B -> F1-C 关系

```text
F1-B retrieval-derived counterfactual utility smoke
  （单一基准：ContextBench verified 5 行；
   5 个 candidate-set variants；4 个 effects；bm25/regex/symbol；
   无 provider 调用）
-> F1-C cross-benchmark retrieval-derived utility smoke
   （两个基准：ContextBench verified 20 行 + RepoQA 10 needle Python；
    重新运行真实有界外部数据；
    bm25/regex/symbol + empty_retrieval 零基线；
    跨基准加权均值；
    5 个固定 counterfactual effects；
    仅聚合公开 artifact；无 provider 调用；
    无 winner/best/default/E_S 记法）
```

## 基准测试

F1-C 对两个基准重新运行真实有界外部数据：

1. **`contextbench`** — ContextBench verified subset（config
   `contextbench_verified`，split `train`）：20 行 verified，语言
   python，query mode `first_paragraph`，方法 `bm25,regex,symbol`。
   复用 C5-C matrix 执行原语
   （`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py`）。
2. **`repoqa`** — RepoQA Python needles：10 needle，方法
   `bm25,regex,symbol`。复用 C5-E matrix 执行原语
   （`eval/c5e_repoqa_method_matrix_smoke.py`）。

F1-C 重新运行真实网络 smoke（临时 HF rows + GitHub clones + RepoQA
asset download + retrieval + score 写入 `/tmp`）。它**不**复用现有
C5-C 或 C5-E aggregate artifact；它重新执行真实 retrieval+score
管线。

## 效用公式（固定诊断 proxy）

F1-C 按 benchmark/method 使用固定 retrieval-derived utility proxy
（**不是**下游 solve rate，**不是** E/S 校准）：

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

其中 `file_hit = file_recall@10`，`span_f0.5 = span_f0.5@10`。

`empty_retrieval` 是显式零上下文基线（无需 retrieval run）。所有指标
与效用按构造为 0（它是效用公式的合成基线，**不是**检索方法）。

## 跨基准加权均值

对每个方法，F1-C 跨两个基准计算加权均值。权重为样本计数：
ContextBench 行计数与 RepoQA needle 计数。

```text
weighted_mean[metric] =
  (contextbench_value * contextbench_sample_count
   + repoqa_value * repoqa_sample_count)
  / (contextbench_sample_count + repoqa_sample_count)
```

`empty_retrieval` 在两个基准上 sample_count=0；其加权均值按构造为 0。

## Counterfactual effects

F1-C 使用五个固定白名单 counterfactual effects（仅 records-shaped；
每个固定记录一个指标）：

1. **`bm25_vs_empty`**  — (bm25 - empty_retrieval)。
2. **`regex_vs_empty`** — (regex - empty_retrieval)。
3. **`symbol_vs_empty`** — (symbol - empty_retrieval)。
4. **`regex_vs_bm25`**  — (regex - bm25)。
5. **`symbol_vs_bm25`** — (symbol - bm25)。

effects 针对 `retrieval_utility` 和每个聚合指标
（`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`retrieval_utility`）的跨基准加权均值计算。

## 指标

聚合 retrieval/score 效用 proxy 指标（**不是**下游 agent 指标）：

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`
- `retrieval_utility`（F1-C 固定效用 proxy）

允许的 method 标签：`empty_retrieval`、`bm25`、`regex`、`symbol`。

## CLI

```bash
python3 -m py_compile eval/f1c_cross_benchmark_retrieval_utility.py
python3 eval/f1c_cross_benchmark_retrieval_utility.py --self-test
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --out artifacts/f1c_cross_benchmark_retrieval_utility/\
f1c_cross_benchmark_retrieval_utility_report.json
# 覆盖 openlocus 二进制：
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --openlocus target/release/openlocus \
    --out /tmp/f1c_smoke_report.json
```

默认模式：运行真实跨基准网络 smoke（临时 HF rows + RepoQA asset
download + GitHub clones + retrieval + score 写入 `/tmp`）。若网络/
openlocus 不可用，产出真实的 `unavailable_with_reason` 报告。绝不
进行 provider 调用。

CLI 参数：`--self-test`、`--out`、`--contextbench-row-limit`
（默认 20，硬上限 20）、`--repoqa-needle-limit`（默认 10，硬上限
10）、`--methods`（默认 `bm25,regex,symbol`）、`--openlocus`。
未知/私有外观参数被以通用 `invalid arguments` 消息拒绝
（SafeArgumentParser 模式）。

## 复用 helpers

F1-C 导入 C5-C、C5-E、C5-A 与 C5-D helpers（向后兼容；均未被修改）：

- ContextBench matrix 执行：`c5c._run_single_method`、
  `c5c._public_failure_counts`、`c5c.PUBLIC_FAILURE_CATEGORIES`、
  `c5c.STATUS_PASS`（仅用于状态镜像）。
- RepoQA matrix 执行：`c5e._run_single_method`、`c5e.STATUS_PASS`
  （仅用于状态镜像）。
- ContextBench 原语：`c5a._fetch_contextbench_rows`、
  `c5a.DEFAULT_QUERY_MODE`、`c5a.DEFAULT_LANGUAGE_FILTER`、
  `c5a._resolve_openlocus_binary`。
- RepoQA 原语：`c5d._download_asset_to_bytes`、
  `c5d._decompress_asset`、`c5d._parse_repoqa_needles`、
  `c5d.ASSET_URL`、`c5d.DEFAULT_LANGUAGE_FILTER`、
  `c5d.FAILURE_CATEGORIES`。
- Scanner 原语：`c5a._RE_URL_VALUE`、`c5a._RE_HEX_DIGEST`、
  `c5a._RE_SECRET_LIKE` 等；`c5c._scan_c5c`、
  `c5c.FORBIDDEN_RECOMMENDATION_FIELDS`；`c5e._scan_c5e`。

F1-C 报告身份为 F1-C（`schema_version=f1c_cross_benchmark_retrieval_utility.v1`、
`claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`、
`mode=bounded_contextbench_repoqa_retrieval_utility`、`phase=F1-C`）。
F1-C 会把上游 component status 规范化为 F1-C component buckets：
`pass`、`partial` 或 `unavailable`。上游 C5-C/C5-E/C5-F status enum
**不会**出现在公开 artifact 中，包括 `benchmark_results.status` 内。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` = `f1c_cross_benchmark_retrieval_utility.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`methods_requested`、`methods_allowed`、`baseline_method`、
  `network_mode`、`openlocus_binary_source`。
- `contextbench_row_limit_requested`、`repoqa_needle_limit_requested`、
  `contextbench_rows_fetched`、`repoqa_needles_seen`。
- `methods_count`、`methods_attempted`、`methods_successful`、
  `methods_succeeded`、`methods_failed`。
- Safe true flags（仅当实际为 true 时）：
  `retrieval_derived_counterfactual_utility_smoke`、
  `contextbench_rows_read`、`repoqa_needles_read`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- Always-false no-claim flags：
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`method_winner_claimed`、
  `baseline_is_policy_candidate`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- `benchmark_results`：固定记录列表
  `{benchmark, method, status, rows_evaluated|needles_evaluated,
  rows_successful|needles_successful, rows_failed|needles_failed,
  metrics, failure_category_counts}`。
- `cross_benchmark_method_results`：固定记录列表
  `{method, contextbench_sample_count, repoqa_sample_count, metrics}`。
  位置 0 为 `empty_retrieval`（所有指标为 0）。
- `counterfactual_effects`：固定记录列表
  `{effect_name, baseline_method, treatment_method, metric, delta}`。
- `input_summary`：`contextbench_row_limit`、`repoqa_needle_limit`、
  `methods`、`benchmarks`、聚合计数、`method_labels`、
  `effect_labels`、`metric_labels`、`contextbench_query_mode`、
  `repoqa_query_mode`、`repoqa_gold_target_mode`。
- `contextbench_failure_category_counts`：仅固定 ContextBench 失败
  类别计数（与 RepoQA 保持分离）。
- `repoqa_failure_category_counts`：仅固定 RepoQA 失败类别计数
  （与 ContextBench 保持分离）。
- `network_calls`、`provider_calls`（始终为 0）。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。
- `framing`：固定 no-claim framing 字段。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。它
组合：

- C5-A forbidden scanner 原语（raw key/value 泄露检测）。
- C5-C 特定 forbidden keys（额外 ContextBench row keys、
  recommendation fields、dynamic dict-keyed method_results 拒绝）。
- C5-E 特定 forbidden keys（RepoQA 形态 row/needle/repo/commit
  keys）。
- F1-C 特定 forbidden keys：`winner`、`best`、`best_method`、
  `best_variant`、`recommended_default`、`preferred_variant`、
  `preferred_method`、`best_arm`、`best_family`、
  `E_primary`、`S_support`、`e_score`、`s_score`、`model_id_raw`、
  `routing_prefix`。
- F1-C records 形状检查：`benchmark_results`、
  `cross_benchmark_method_results`、`counterfactual_effects` 必须为
  records 列表（**不是** dict-keyed 镜像）。
- F1-C value 模式检查：拒绝 raw model 路由前缀。

**不**输出 `winner` / `best_method` / `recommended_default` 字段。
**不**使用 E/S 校准记法（`E_primary` / `S_support`）。

scanner 仅对最终公开聚合 artifact 运行。内部 task/label/run JSONL（含
路径/span/query/gold）仅保留在内存或 `/tmp`，绝不对公开契约扫描，绝
不提交。

## 失败类别保持分离

ContextBench 与 RepoQA 失败类别保持分离（**不**合并不兼容枚举）：

- `contextbench_failure_category_counts`：ContextBench 类别
  （`network_fetch_failed`、`clone_failed`、`checkout_failed`、
  `label_context_parse_failed`、`row_parse_failed`、
  `retrieval_failed`、`score_failed`、`no_python_rows` 等）。
- `repoqa_failure_category_counts`：RepoQA 类别
  （`asset_download_failed`、`asset_decompress_failed`、
  `asset_parse_failed`、`no_python_needles`、`needle_parse_failed`、
  `repo_clone_failed`、`repo_checkout_failed`、`retrieval_failed`、
  `score_failed` 等）。

## Self-tests

- Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
- Safe true flags 存在；no-claim flags 为 false。
- Methods / effects / metrics / benchmarks 为固定白名单。
- Records-shaped 容器（`benchmark_results`、
  `cross_benchmark_method_results`、`counterfactual_effects` 为列表；
  无动态 dict 镜像）。
- Method parser（拒绝 unknown/text；dedup；默认）。
- Row/needle limit 硬上限（20 / 10）。
- 效用计算：empty_retrieval -> 0；零 file_recall -> miss_penalty
  0.25；非零 file_recall -> 无 miss_penalty。
- 跨基准加权均值（相等指标；不同指标；empty_retrieval 零）。
- Counterfactual effects（records-shaped；bm25_vs_empty 与
  regex_vs_bm25 的 utility delta 正确）。
- 失败类别保持分离（ContextBench vs RepoQA 枚举）。
- scanner 拒绝：repo URL、文件路径、commit SHA、repo slug、task_id key、
  query key、gold key、content_sha key、candidate key、evidence key、
  winner key、best_method key、recommended_default key、
  E_primary key、S_support key、model_id_raw key、routing_prefix
  key、raw 路由前缀 value、URL value、tmp 路径、stdout key、
  provider key、secret canary、repo key、commit_sha key、needle_path
  key、needle_description key。
- scanner 允许：method/benchmark/effect/metric 名称、query mode 标签
  （`first_paragraph`、`needle_description`、
  `needle_path_line_range`）、benchmark_results records、
  cross_benchmark_method_results records、counterfactual_effects
  records。
- scanner 拒绝 benchmark_results / cross_benchmark_method_results /
  counterfactual_effects 的 dict-keyed 镜像。
- fail-closed 生成：干净 report 不 raise；泄漏 report raise
  SystemExit；winner/ES-notation 泄露 raise SystemExit；self-test 失败
  拒绝生成 artifact。
- 公开 artifact 自扫描干净。
- Pass/partial report 形状（benchmark_results 计数；
  cross_benchmark_method_results 含 empty_retrieval；
  counterfactual_effects 计数）。
- CLI 参数面。

## 验证

```text
python3 -m py_compile eval/f1c_cross_benchmark_retrieval_utility.py  => PASS
python3 eval/f1c_cross_benchmark_retrieval_utility.py --self-test  => PASS (167/167 checks)
python3 eval/f1c_cross_benchmark_retrieval_utility.py \
  --contextbench-row-limit 20 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol \
  --out artifacts/f1c_cross_benchmark_retrieval_utility/\
f1c_cross_benchmark_retrieval_utility_report.json  => PASS
  (status: cross_benchmark_retrieval_utility_pass,
   forbidden_scan: pass, self_test_passed: true,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   retrieval_derived_counterfactual_utility_smoke: true,
   contextbench_rows_read: true,
   repoqa_needles_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
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
   evidencecore_semantics_changed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

本地真实网络 run 产出以下聚合指标（不提交任何 row/needle/repo/commit/
query/gold/path/span/snippet/source/JSONL/evidence/stdout/stderr/
clone-path/row-id/hash/provider/model-routing-prefix/winner/best/
default/recommended 字段）：

```text
status: cross_benchmark_retrieval_utility_pass
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
contextbench/bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0, retrieval_utility=0.396196
contextbench/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
contextbench/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0, retrieval_utility=0.602712
repoqa/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark bm25: file_recall@10=0.4, mrr=0.218477, span_f0.5@10=0.020831, success_rate=1.0, retrieval_utility=0.465035
cross_benchmark regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
bm25_vs_empty [retrieval_utility]: delta=+0.465035
regex_vs_empty [retrieval_utility]: delta=-0.25
symbol_vs_empty [retrieval_utility]: delta=-0.25
regex_vs_bm25 [retrieval_utility]: delta=-0.715035
symbol_vs_bm25 [retrieval_utility]: delta=-0.715035
```

这是在微型有界 ContextBench + RepoQA 子集上的跨基准 retrieval-derived
utility smoke。它不是下游效用，不是正式外部 benchmark 结果，不是方法
winner，也不是 default/promotion 信号。

## 注意事项

- F1-C 是公开仅聚合跨基准 retrieval-derived utility smoke artifact。
  它是 eval/诊断专用。它**不**改变 runtime、retriever、pack、backend
  或 default policy；它**不**改变 EvidenceCore 语义。它**不是**基准
  测试结果，**不是**下游效用，**不是** true E/S 校准，**不是**外部
  基准测试性能声明，**不是** leaderboard 条目，**不是**方法 winner，
  也**不是** promotion。
- F1-C 重新运行真实有界外部数据（ContextBench verified 20 行 + RepoQA
  10 needle Python）。它**不**组合现有 C5-C 或 C5-E aggregate
  artifact；它重新执行真实 retrieval+score 管线。
- F1-C **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有临时数据（rows、needles、queries、gold labels、retrieval
  JSONL、scoring JSONL、repo URLs、commits、paths、spans、candidates、
  stdout/stderr）仅保留在内存或 `/tmp`，**绝不**提交或上传。
- F1-C **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- F1-C **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- F1-C **不**声明外部基准测试性能。
  `external_benchmark_performance_claimed=false`。
- F1-C **不**声明方法 winner。
  `method_winner_claimed=false`。
- F1-C **不**输出 winner/best_method/recommended_default 字段。
- F1-C **不**使用 E/S 校准记法（`E_primary` / `S_support`）。
- 效用公式是固定诊断 proxy。它**不是**下游 solve rate，**不是**已校准
  agent utility，**不是** promotion 指标。miss_penalty（当
  file_recall@10 == 0 时为 0.25）可能产生负效用值；这是有意的（零
  recall 且非零 success_rate 是退化信号）。
- `empty_retrieval` 是合成零上下文基线。不对其执行 retrieval run；
  所有指标与效用按构造为 0。
- 跨基准加权均值使用样本计数作为权重（ContextBench 行计数、RepoQA
  needle 计数）。这是 smoke 级聚合；**不是**正式 meta-analysis。
- ContextBench 与 RepoQA 失败类别在公开 artifact 中保持分离
  （`contextbench_failure_category_counts` 与
  `repoqa_failure_category_counts`）；其不兼容枚举**不**合并。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  smoke-claimed 标志（`retrieval_derived_counterfactual_utility_smoke`、
  `contextbench_rows_read`、`repoqa_needles_read`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`）**仅**
  在真实网络 run 实际执行时为 true。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
