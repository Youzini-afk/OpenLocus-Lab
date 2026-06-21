# F1-D 跨基准检索 Utility 稳健性 Smoke（公开仅聚合 Artifact）

## 范围与声明边界

F1-D 将 F1-C 从点估计扩展到 **诊断性 paired-bootstrap
置信/符号稳定性估计**。F1-D **重新运行真实有界外部数据**，对两个
基准形态的检索样本（ContextBench verified 20 行 + RepoQA 10 needle
Python）运行，在聚合之前拦截 per-unit score 指标（仅在内存或
`/tmp` 中），计算每个基准/方法的固定 retrieval-derived utility
proxy、跨基准加权均值，以及五个固定 effect 跨五个 metric 的
paired bootstrap 置信/符号稳定性统计。F1-D **不是**现有 C5 或 F1-C
aggregate artifact 的 rollup：它重新执行真实检索+评分管线，并在
C5-C/C5-E 聚合 helper 折叠 per-unit 数据之前在内存中捕获。

F1-D 明确 **不是**下游 utility 声明，**不是** true E/S 校准，**不
是**外部基准测试性能声明，**不是** leaderboard 条目，**不是**方法
winner 声明，**不是** promotion/default/runtime/retriever/pack/
backend/EvidenceCore 语义变更，**不是** live/provider 声明，**也
不是**正式外部基准置信区间。它 **不**进行任何 provider 调用，**不**
进行任何远程 provider 调用。bootstrap 统计是诊断性稳健性估计，**不
是**正式外部基准置信区间。

- 声明级别：`cross_benchmark_retrieval_utility_robustness_smoke_only`。
- 模式：`bounded_contextbench_repoqa_retrieval_robustness`；阶段
  `F1-D`。
- 状态枚举：成功时
  `cross_benchmark_retrieval_robustness_pass`（两个基准均通过
  且 bm25 在两者上均成功）；至少一个基准通过且 bm25 至少在一个上
  成功时 `partial`；无/阻塞/网络不可用时
  `unavailable_with_reason`；scanner 失败时
  `fail_forbidden_scan`；方法配置/形状无效时
  `fail_schema_contract`。
- F1-D 是 **eval/diagnostic only**。它 **不是** benchmark 结果、不
  是下游 utility、不是 true E/S 校准、不是外部基准测试性能声明、不
  是 leaderboard 条目、不是方法 winner、不是正式置信区间、也不是
  promotion。

### F1-C -> F1-D 关系

```text
F1-C 跨基准 retrieval-derived utility smoke
  （两个基准：ContextBench verified 20 行 + RepoQA 10 needle
   Python；重新运行真实有界外部数据；
   bm25/regex/symbol + empty_retrieval 零基线；
   跨基准加权均值；
   5 个固定 counterfactual effects；
   仅聚合公开 artifact；无 provider 调用；
   无 winner/best/default/E_S 记法；仅点估计）
-> F1-D 跨基准 retrieval utility 稳健性 smoke
   （相同两个基准；相同有界数据；
    per-unit 指标在聚合前在内存中拦截；
    保持样本计数的 paired 跨基准 bootstrap；
    5 个固定 effect x 5 个 metric = 25 条 bootstrap effect 记录；
    bootstrap CI p05/p50/p95 与符号稳定性分数；
    仅聚合公开 artifact；无 provider 调用；
    无 per-unit metric 数组；无 winner/best/default/E_S 记法）
```

## 基准

F1-D 对两个基准重新运行真实有界外部数据（与 F1-C 相同的有界子集）：

1. **`contextbench`** — ContextBench verified 子集（config
   `contextbench_verified`，split `train`）：20 个 verified 行，语言
   python，query mode `first_paragraph`，方法 `bm25,regex,symbol`。
2. **`repoqa`** — RepoQA Python needle：10 个 needle，方法
   `bm25,regex,symbol`。

F1-D 重新运行真实网络 smoke（瞬时 HF 行 + GitHub clone + RepoQA
asset 下载 + 检索 + 评分到 `/tmp`）。它 **不**复用现有 C5-C、C5-E
或 F1-C aggregate artifact；它重新执行真实检索+评分管线，并在聚合
前在内存中拦截 per-unit 指标。

## Utility 公式（固定诊断 proxy；与 F1-C 不变）

F1-D 使用与 F1-C 相同的固定 retrieval-derived utility proxy（**不
是**下游 solve rate，**不是** E/S 校准）：

```text
utility = file_hit + 0.25*mrr + 0.5*span_f0.5 - miss_penalty
miss_penalty = 0.25 if file_recall@10 == 0 else 0
```

其中 `file_hit = file_recall@10`，`span_f0.5 = span_f0.5@10`。

`empty_retrieval` 是显式零上下文基线（无需检索运行）。所有 metric
与 utility 按构造为 0（它是 utility 公式的合成基线，**不是**检索
方法）。

## 跨基准加权均值

对每个方法，F1-D 计算跨两个基准的加权均值。权重为样本计数：
ContextBench 行计数与 RepoQA needle 计数。

```text
weighted_mean[metric] =
  (contextbench_value * contextbench_sample_count
   + repoqa_value * repoqa_sample_count)
  / (contextbench_sample_count + repoqa_sample_count)
```

`empty_retrieval` 在两个基准上 sample_count=0；其加权均值按构造为 0。

## Bootstrap effects

F1-D 使用五个固定 allowlist effect（仅 records 形态）：

1. **`bm25_vs_empty`**  — (bm25 - empty_retrieval)。
2. **`regex_vs_empty`** — (regex - empty_retrieval)。
3. **`symbol_vs_empty`** — (symbol - empty_retrieval)。
4. **`regex_vs_bm25`**  — (regex - bm25)。
5. **`symbol_vs_bm25`** — (symbol - bm25)。

effect 计算用于 `retrieval_utility` 的跨基准加权均值及每个聚合
metric（`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`retrieval_utility`）。

## 跨基准重采样（保持样本计数）

在每个 bootstrap replicate 内：

1. ContextBench paired unit 按 ContextBench 样本计数（20 行）**有放回
   重采样**。
2. RepoQA paired unit 按 RepoQA needle 计数（10 个）**有放回重采
   样**。
3. 对每个基准，从重采样的 per-unit metric 重新计算聚合 metric 均值
   与 retrieval utility。
4. 跨基准加权均值使用原始样本计数作为权重计算。
5. effect 为（treatment 跨基准加权均值 - baseline 跨基准加权均值）。

对于 paired effect（`regex_vs_bm25`、`symbol_vs_bm25`），重采样保持
treatment-baseline 配对：两者从同一重采样 unit index 提取（paired
complete-case 分析）。

对于 `*_vs_empty` effect，baseline 是合成零（所有 metric 为 0，
utility 按构造为 0）；effect 等于 treatment 值。

对于 `retrieval_utility`，bootstrap 从重采样的聚合 metric 均值重新
计算 utility（mean 的 utility），与 F1-C 的聚合语义一致。对于
`empty_retrieval` baseline，baseline utility 按构造为 0.0（**不是**
utility(0,0,0) 即 -0.25）。

## 公开 effect 记录字段

每条 bootstrap effect 记录仅包含以下字段：

- `effect_name`：固定 effect 标签。
- `metric`：固定 metric 标签。
- `point_estimate`：原始数据上的观测 effect。
- `bootstrap_mean`：bootstrap replicate effect 的均值。
- `ci_p05`：bootstrap replicate effect 的第 5 百分位。
- `ci_p50`：第 50 百分位（中位数）。
- `ci_p95`：第 95 百分位。
- `sign_positive_fraction`：effect > 0 的 replicate 比例。
- `sign_negative_fraction`：effect < 0 的 replicate 比例。
- `sign_zero_fraction`：effect == 0 的 replicate 比例。
- `sample_units`：两个基准的 paired unit 总数。
- `bootstrap_replicates`：bootstrap replicate 数。
- `bootstrap_seed`：固定 RNG seed。

## Metrics

聚合检索/评分 utility proxy metric（**不是**下游 agent metric）：

- `file_recall@10`
- `mrr`
- `span_f0.5@10`
- `success_rate`
- `retrieval_utility`（F1-C/F1-D 固定 utility proxy）

允许的方法标签：`empty_retrieval`、`bm25`、`regex`、`symbol`。

## 公开 artifact 形态

仅 records（仅聚合；无 per-unit metric 数组）：

- `benchmark_method_means`：固定 record 列表
  `{benchmark, method, sample_count, metrics}`。
- `cross_benchmark_method_means`：固定 record 列表
  `{method, contextbench_sample_count, repoqa_sample_count, metrics}`。
  包含 `empty_retrieval` 在位置 0（所有 metric 为 0）。
- `bootstrap_effect_records`：固定 record 列表（字段如上）。
- `input_summary`：`contextbench_row_limit`、`repoqa_needle_limit`、
  `methods`、`benchmarks`、聚合计数、`method_labels`、
  `effect_labels`、`metric_labels`、`contextbench_query_mode`、
  `repoqa_query_mode`、`repoqa_gold_target_mode`。
- `bootstrap_summary`：`bootstrap_replicates`、`bootstrap_seed`、
  `effect_count`、`metric_count`、`bootstrap_record_count`、
  `resampling_method`。

身份/边界字段：

- `schema_version` = `f1d_cross_benchmark_retrieval_robustness.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`methods_requested`、`methods_allowed`、`baseline_method`、
  `network_mode`、`openlocus_binary_source`。
- `contextbench_row_limit_requested`、`repoqa_needle_limit_requested`、
  `contextbench_rows_fetched`、`repoqa_needles_seen`。
- `bootstrap_replicates_requested`、`bootstrap_seed`。
- `methods_count`、`methods_attempted`、`methods_successful`、
  `methods_succeeded`、`methods_failed`。
- 安全 true flag（仅当实际为 true 时）：
  `retrieval_utility_robustness_smoke`、`contextbench_rows_read`、
  `repoqa_needles_read`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`bootstrap_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- 始终为 false 的 no-claim flag：
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
- `contextbench_failure_category_counts`：仅 ContextBench 失败类别
  计数（与 RepoQA 保持分离）。
- `repoqa_failure_category_counts`：仅 RepoQA 失败类别计数（与
  ContextBench 保持分离）。
- `network_calls`、`provider_calls`（始终为 0）。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。
- `framing`：固定 no-claim framing 字段
  （包含 `is_formal_benchmark_confidence_interval: false`）。

## CLI

```bash
python3 -m py_compile eval/f1d_cross_benchmark_retrieval_robustness.py
python3 eval/f1d_cross_benchmark_retrieval_robustness.py --self-test
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol --bootstrap-replicates 1000 \
    --out artifacts/f1d_cross_benchmark_retrieval_robustness/\
f1d_cross_benchmark_retrieval_robustness_report.json
# 覆盖 openlocus binary 与 bootstrap seed：
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
    --contextbench-row-limit 20 --repoqa-needle-limit 10 \
    --methods bm25,regex,symbol \
    --bootstrap-replicates 1000 --bootstrap-seed 20240621 \
    --openlocus target/release/openlocus \
    --out /tmp/f1d_smoke_report.json
```

默认模式：运行真实跨基准网络 smoke（瞬时 HF 行 + RepoQA asset 下载 +
GitHub clone + 检索 + 评分到 `/tmp`）。如果网络/openlocus 不可用，
它产生 truthful 的 `unavailable_with_reason` 报告。绝不进行 provider
调用。

CLI 参数：`--self-test`、`--out`、`--contextbench-row-limit`
（默认 20，硬上限 20）、`--repoqa-needle-limit`（默认 10，硬上限
10）、`--methods`（默认 `bm25,regex,symbol`）、
`--bootstrap-replicates`（默认 1000，硬上限 2000）、
`--bootstrap-seed`（默认 20240621）、`--openlocus`。
未知/私有的参数以通用 `invalid arguments` 消息拒绝
（SafeArgumentParser 模式）。

## 复用的 helper

F1-D 导入 F1-C、C5-C、C5-E、C5-A 与 C5-D helper（向后兼容；均未被
修改）：

- F1-C utility 公式：`f1c._compute_utility`、
  `f1c._extract_method_metrics`、`f1c._filter_metrics`、
  `f1c._compute_utility`（保证公式同一性）。
- F1-C 配置：`f1c.parse_methods`、`f1c.MethodConfigError`、
  `f1c._validate_contextbench_row_limit`、
  `f1c._validate_repoqa_needle_limit`、F1-C 常量
  （METRIC_NAMES、EFFECTS、ALLOWED_METHODS 等）。
- F1-C scanner：`f1c._scan_f1c`（组合 C5-A/C5-C/C5-E scanner 与
  F1-C 特定检查）；F1-D 添加 F1-D 特定 forbidden key 与 record-shape
  检查。
- ContextBench 矩阵执行：F1-D 镜像 C5-C `_run_single_method` 循环，
  但在聚合前在内存中捕获 per-unit 指标（**不**调用会折叠 per-unit
  数据的 `c5c._run_single_method`）。复用
  `c5c._public_failure_counts`、`c5c.PUBLIC_FAILURE_CATEGORIES`、
  `c5c.STATUS_PASS`。
- RepoQA 矩阵执行：F1-D 镜像 C5-E `_run_single_method` 循环，但在
  聚合前在内存中捕获 per-unit 指标。复用 `c5e.STATUS_PASS`。
- ContextBench 原语：`c5a._fetch_contextbench_rows`、
  `c5a.DEFAULT_QUERY_MODE`、`c5a.DEFAULT_LANGUAGE_FILTER`、
  `c5a._resolve_openlocus_binary`、`c5a._parse_gold_context`、
  `c5a._sanitize_query`、`c5a._clone_and_checkout`、
  `c5a._write_transient_jsonl`、`c5a._run_retrieval_and_score`。
- RepoQA 原语：`c5d._download_asset_to_bytes`、
  `c5d._decompress_asset`、`c5d._parse_repoqa_needles`、
  `c5d._sanitize_needle_description`、`c5d._clone_and_checkout`、
  `c5d._write_transient_jsonl`、`c5d._run_retrieval_and_score`、
  `c5d.ASSET_URL`、`c5d.DEFAULT_LANGUAGE_FILTER`、
  `c5d.FAILURE_CATEGORIES`。
- Scanner 原语：`c5a._RE_URL_VALUE`、`c5a._RE_HEX_DIGEST`、
  `c5a._RE_SECRET_LIKE` 等；`c5c._scan_c5c`、
  `c5c.FORBIDDEN_RECOMMENDATION_FIELDS`；`c5e._scan_c5e`。

F1-D 报告身份为 F1-D（`schema_version=f1d_cross_benchmark_retrieval_robustness.v1`、
`claim_level=cross_benchmark_retrieval_utility_robustness_smoke_only`、
`mode=bounded_contextbench_repoqa_retrieval_robustness`、阶段
`F1-D`）。F1-D **不**修改 F1-C 结果语义。

## Forbidden scanner（公开，fail-closed）

在写入公开 JSON 前运行严格的 forbidden-output scanner。它组合：

- F1-C forbidden scanner（本身组合 C5-A/C5-C/C5-E scanner 与 F1-C
  特定 forbidden key、record-shape 检查与 value-pattern 检查）。
- F1-D 特定 forbidden key：F1-C record 容器名
  （`benchmark_results`、`cross_benchmark_method_results`、
  `counterfactual_effects`）— F1-D 使用自己的容器名；
  per-unit metric 数组 key（`per_row_metrics`、
  `per_needle_metrics`、`row_metrics`、`needle_metrics`、
  `row_hashes`、`needle_hashes`、`per_unit_metrics`、
  `per_unit_utility`）。
- F1-D record-shape 检查：`benchmark_method_means`、
  `cross_benchmark_method_means`、`bootstrap_effect_records` 必须是
  record 列表（**不是** dict-keyed mirror）。
- F1-D value-pattern 检查：拒绝 raw model routing prefix（复用自
  F1-C）。

不输出 `winner`/`best_method`/`recommended_default` 字段。不使用
E/S 校准记法（`E_primary`/`S_support`）。不提交 per-unit metric 数
组、row hash 或 per-row/per-needle 数据。

scanner 仅对最终公开仅聚合 artifact 运行。内部 task/label/run JSONL
与 per-unit 指标（包含 path/span/query/gold）仅保留在内存或
`/tmp` 中，绝不针对公开契约扫描，绝不提交。

## 失败类别保持分离

ContextBench 与 RepoQA 失败类别保持分离（**不**合并不兼容枚举）：

- `contextbench_failure_category_counts`：ContextBench 类别
  （`network_fetch_failed`、`clone_failed`、`checkout_failed`、
  `label_context_parse_failed`、`row_parse_failed`、
  `retrieval_failed`、`score_failed`、`no_python_rows` 等）。
- `repoqa_failure_category_counts`：RepoQA 类别
  （`asset_download_failed`、`asset_decompress_failed`、
  `asset_parse_failed`、`no_python_needles`、
  `needle_parse_failed`、`repo_clone_failed`、
  `repo_checkout_failed`、`retrieval_failed`、`score_failed` 等）。

## Self-test

- Artifact 身份字段（schema、claim、status、mode、phase、
  generated_by）。
- 安全 true flag 存在；no-claim flag 为 false。
- 方法/effect/metric/benchmark 为固定 allowlist。
- Records 形态容器（`benchmark_method_means`、
  `cross_benchmark_method_means`、`bootstrap_effect_records` 为
  列表；无动态 dict mirror；无 F1-C 容器 key）。
- 方法 parser（拒绝 unknown/text；去重；默认）。
- Row/needle limit 硬上限（20 / 10）。
- Bootstrap replicate 硬上限（2000）与默认（1000）。
- Bootstrap seed 默认（20240621）。
- Utility 计算：empty_retrieval -> 0；零 file_recall ->
  miss_penalty 0.25；非零 file_recall -> 无 miss_penalty。
- Per-unit 聚合（mean 的 utility != per-unit utility 的 mean）。
- 跨基准加权均值（不同 metric；empty_retrieval 为零）。
- Bootstrap 计算（点估计、均值、CI、符号分数、sample_units、
  相同 seed 的确定性）。
- Bootstrap effect 记录数 = effect * metric = 5 * 5 = 25。
- Bootstrap effect 记录字段（精确集合）。
- Paired unit 构建器（按 index 匹配；empty baseline；部分重叠）。
- 百分位 helper（单值、空、p0/p50/p100）。
- 失败类别保持分离（ContextBench vs RepoQA 枚举）。
- Scanner 拒绝：repo URL、commit SHA、repo slug、task_id key、
  query key、winner key、best_method key、E_primary key、raw routing
  prefix value、tmp path、provider key、F1-C 容器 key、per-unit
  metric 数组 key、row hash。
- Scanner 允许：method/benchmark/effect/metric 名、bootstrap 字段、
  benchmark_method_means 记录、bootstrap_effect_records 记录。
- Scanner 拒绝 F1-D 容器的 dict-keyed mirror。
- Fail-closed 生成：干净报告不 raise；泄露报告 raise SystemExit；
  winner/ES 记法/per-unit key 泄露 raise SystemExit；self-test 失败
  拒绝 artifact 生成。
- 公开 artifact self-scan 干净。
- Pass/partial 报告形态（benchmark_method_means 计数；
  cross_benchmark_method_means 包含 empty_retrieval；
  bootstrap_effect_records 计数；bootstrap_summary 记录计数匹配）。
- CLI 参数表面（包含 `--bootstrap-replicates`、`--bootstrap-seed`）。

## 验证

```text
python3 -m py_compile eval/f1d_cross_benchmark_retrieval_robustness.py  => PASS
python3 eval/f1d_cross_benchmark_retrieval_robustness.py --self-test  => PASS (185/185 checks)
python3 eval/f1d_cross_benchmark_retrieval_robustness.py \
  --contextbench-row-limit 20 --repoqa-needle-limit 10 \
  --methods bm25,regex,symbol --bootstrap-replicates 1000 \
  --out artifacts/f1d_cross_benchmark_retrieval_robustness/\
f1d_cross_benchmark_retrieval_robustness_report.json  => PASS
  (status: cross_benchmark_retrieval_robustness_pass,
   forbidden_scan: pass, self_test_passed: true,
   contextbench_rows_fetched: 20, repoqa_needles_seen: 10,
   network_calls: 2, provider_calls: 0,
   bootstrap_record_count: 25,
   retrieval_utility_robustness_smoke: true,
   contextbench_rows_read: true,
   repoqa_needles_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   bootstrap_computed: true,
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

本地真实网络 run 产生以下聚合指标与 bootstrap 统计（不提交
row/needle/repo/commit/query/gold/path/span/snippet/source/JSONL/
evidence/stdout/stderr/clone-path/row-id/hash/per-unit-metric-array/
provider/model-routing-prefix/winner/best/default/recommended 字段）：

```text
status: cross_benchmark_retrieval_robustness_pass
contextbench_rows_fetched: 20
repoqa_needles_seen: 10
network_calls: 2
forbidden_scan: pass
provider_calls: 0
bootstrap_replicates: 1000
bootstrap_seed: 20240621
bootstrap_record_count: 25
contextbench/bm25: file_recall@10=0.35, mrr=0.143107, span_f0.5@10=0.020838, success_rate=1.0, retrieval_utility=0.396196
contextbench/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
contextbench/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0, retrieval_utility=0.602712
repoqa/regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
repoqa/symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark bm25: file_recall@10=0.4, mrr=0.218477, span_f0.5@10=0.020831, success_rate=1.0, retrieval_utility=0.465035
cross_benchmark regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
cross_benchmark symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, retrieval_utility=-0.25
bm25_vs_empty [retrieval_utility]: point=+0.465035, mean=+0.463491, ci=[+0.298938, +0.464512, +0.624026], sign+=1.0, sign-=0.0, sign0=0.0
regex_vs_empty [retrieval_utility]: point=-0.25, mean=-0.25, ci=[-0.25, -0.25, -0.25], sign+=0.0, sign-=1.0, sign0=0.0
symbol_vs_empty [retrieval_utility]: point=-0.25, mean=-0.25, ci=[-0.25, -0.25, -0.25], sign+=0.0, sign-=1.0, sign0=0.0
regex_vs_bm25 [retrieval_utility]: point=-0.715035, mean=-0.713491, ci=[-0.874026, -0.714511, -0.548938], sign+=0.0, sign-=1.0, sign0=0.0
symbol_vs_bm25 [retrieval_utility]: point=-0.715035, mean=-0.713491, ci=[-0.874026, -0.714511, -0.548938], sign+=0.0, sign-=1.0, sign0=0.0
bm25_vs_empty [file_recall@10]: point=+0.4, mean=+0.398833, ci=[+0.266667, +0.4, +0.533333], sign+=1.0, sign-=0.0, sign0=0.0
```

点估计与 F1-C 的跨基准加权均值 delta 一致（`bm25_vs_empty`
retrieval_utility = +0.465035，`regex_vs_bm25` = -0.715035），确认
utility 公式与聚合与 F1-C 不变。bootstrap CI 与符号稳定性分数在这些
点估计之上扩展了诊断性稳健性信息。

这是跨基准 retrieval utility 稳健性 smoke，覆盖极小的有界
ContextBench + RepoQA 子集。它不是下游 utility、不是正式外部基准结
果、不是正式置信区间、不是方法 winner、也不是 default/promotion 信
号。

## Caveats

- F1-D 是公开仅聚合跨基准 retrieval utility 稳健性 smoke artifact。
  它是 eval/diagnostic only。它 **不**改变 runtime、retriever、
  pack、backend 或 default policy；它 **不**改变 EvidenceCore 语义。
  它 **不是** benchmark 结果、**不是**下游 utility、**不是** true
  E/S 校准、**不是**外部基准测试性能声明、**不是** leaderboard 条
  目、**不是**方法 winner、**不是**正式置信区间、**也不是**
  promotion。
- F1-D 重新运行真实有界外部数据（ContextBench verified 20 行 +
  RepoQA 10 needle Python）。它 **不**组合现有 C5-C、C5-E 或 F1-C
  aggregate artifact；它重新执行真实检索+评分管线，并在聚合前在内存
  中拦截 per-unit 指标。
- F1-D **不**进行任何 provider 调用，**不**进行任何远程 provider 调
  用。所有瞬时数据（row、needle、query、gold label、retrieval JSONL、
  scoring JSONL、repo URL、commit、path、span、candidate、
  stdout/stderr、per-unit 指标）仅保留在内存或 `/tmp` 中，**绝不**
  提交或上传。
- Per-unit 指标仅存在于内存或 `/tmp`；公开 artifact 仅输出聚合均值
  与 bootstrap 统计。不提交 per-row 或 per-needle metric 数组。
- F1-D **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- F1-D **不**声明 true E/S 校准。
  `true_e_s_calibration_claimed=false`。
- F1-D **不**声明外部基准测试性能。
  `external_benchmark_performance_claimed=false`。
- F1-D **不**声明方法 winner。
  `method_winner_claimed=false`。
- F1-D **不**输出 winner/best_method/recommended_default 字段。
- F1-D **不**使用 E/S 校准记法（`E_primary`/`S_support`）。
- F1-D **不**输出 F1-C record 容器名（`benchmark_results`、
  `cross_benchmark_method_results`、`counterfactual_effects`）；它
  使用自己的容器名（`benchmark_method_means`、
  `cross_benchmark_method_means`、`bootstrap_effect_records`）。
- Utility 公式是固定诊断 proxy（与 F1-C 不变）。它 **不是**下游 solve
  rate，**不是**校准 agent utility，**不是** promotion metric。
  miss_penalty（file_recall@10 == 0 时 0.25）可产生负 utility 值；这
  是有意的（零 recall 与非零 success_rate 是退化信号）。
- `empty_retrieval` 是合成零上下文基线。不为其执行检索运行；所有
  metric 与 utility 按构造为 0（覆盖公式对零 recall 情况的
  miss_penalty，与 F1-C 一致）。
- bootstrap 统计是诊断性稳健性估计，**不是**正式外部基准置信区间。
  它们反映有界 smoke 样本的变异性，而非完整基准评估的总体级不确定性。
  `is_formal_benchmark_confidence_interval=false`。
- 跨基准重采样保持基准样本计数（ContextBench 20，RepoQA 10）。这是
  smoke 级诊断，**不是**正式 meta-analysis。
- `success_rate` metric 是退化的（对成功完成检索的 real method 始终
  为 1.0，因为 per-unit 指标仅对成功 unit 捕获）。bootstrap 正确反
  映这一点（例如 `regex_vs_bm25` 在 `success_rate` 上 point=0.0
  且 sign_zero_fraction=1.0）。
- ContextBench 与 RepoQA 失败类别在公开 artifact 中保持分离；其不兼
  容枚举 **不**合并。
- 所有 no-claim / no-runtime-change flag 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  smoke 声明 flag（`retrieval_utility_robustness_smoke`、
  `contextbench_rows_read`、`repoqa_needles_read`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `bootstrap_computed`）仅在真实网络 run 实际执行时为 true。
- 未修改 runtime/retriever/pack/model/backend/default-policy 文件。
  无 promotion/default/runtime 声明变更。
