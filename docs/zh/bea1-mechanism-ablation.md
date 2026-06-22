# BEA-1 Mechanism Ablation Smoke

日期：2026-06-21（BEA-1 机制消融 smoke，基于全新有界 ContextBench verified
Python 行 + RepoQA Python needle，私有 per-record SCORE JSONL 轨迹存于
`/tmp`，公开产物仅聚合 records）

BEA-1 是 BEA-0 的**机制消融**后续。它对全新有界 external ContextBench
verified Python 行 + RepoQA Python needle 重新运行检索，运行 BEA-0 的
`bea_v0_budgeted` 策略以及三个同预算控制
（`same_budget_bm25_prefix`、`agreement_only_same_budget`、
`seeded_random_same_budget`）以及既有 baseline（`bm25_top10`、启用时
`rrf_bm25_regex_symbol_top10`），在同一组记录上、按 paired denominator
规则进行机制对比。公开产物为 records 形态的仅聚合：per-arm metric
records、baseline-vs-treatment delta records、机制对比 records，以及聚合
私有 SCORE manifest。

BEA-1 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，且**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它不会输出
`winner`、`best_method`、`recommended_default`、`method_winner`、
`calibration`，或任何暗示 policy/default 决策的字段。

> **重要 claim 边界**。BEA-1 输出 `claim_level =
> bea_v0_mechanism_ablation_smoke_only`。它不声明 external benchmark
> 结果，不声明 leaderboard 条目，不声明性能声明，不声明 method-winner，
> 不声明 calibration，不声明 promotion，不声明 default 变更，不声明
> runtime/retriever/pack/backend 变更，不声明 EvidenceCore 语义变更，且
> 不声明 downstream agent 价值。所有 no-claim / no-runtime-change flag
> 均为 false：`external_benchmark_performance_claimed=false`、
> `leaderboard_entry_claimed=false`、
> `downstream_agent_value_proven=false`、`calibration_claimed=false`、
> `method_winner_claimed=false`、`promotion_ready=false`、
> `default_should_change=false`、`runtime_behavior_changed=false`、
> `retriever_changed=false`、`pack_builder_changed=false`、
> `backend_changed=false`、`default_policy_changed=false`、
> `evidencecore_semantics_changed=false`、`provider_calls_made=false`、
> `remote_provider_calls_made=false`。

## 目标

将 BEA-0 转为一个小型真实机制消融。对全新有界 external ContextBench +
RepoQA 检索，保留私有 per-record SCORE JSONL 于 `/tmp`，并在同一组记录上
将 BEA v0 与机制特定控制进行对比。公开输出仍为 records 形态的仅聚合。

### 为什么这是真正机制消融，而非聚合校验

- 对全新 ContextBench verified Python 行 + RepoQA Python needle 重新运行
  多方法检索（`bm25`/`regex`/`symbol` + 可选 `rrf`），通过
  `eval/run_retrieval.py:run_query()`（fresh external run；不 bootstrap
  BEA-0 聚合 artifact）。
- 在每条记录上运行 5 个固定 arm（`bm25_top10`、`bea_v0_budgeted`、
  `same_budget_bm25_prefix`、`agreement_only_same_budget`、
  `seeded_random_same_budget`；启用 rrf 时还包括
  `rrf_bm25_regex_symbol_top10`），并按 paired denominator 规则进行机制
  对比。
- 同预算控制使用
  `K = len(bea_v0_budgeted.accepted_candidates)` 并按可用去重候选数封顶，
  因此 BEA-0 vs 控制仅在采集机制上不同，预算相同。
- 将私有 per-record SCORE JSONL 行写入 `/tmp`（或显式忽略的私有路径），
  含完整 per-record 详情，包括同预算控制 arm evidence 和 per-record
  same-budget K。
- 仅公开聚合 per-arm metric records + baseline-vs-treatment delta records
  + 机制对比 records + 聚合私有 SCORE manifest。

## BEA-0 -> BEA-1 关系

```text
BEA-0 Budgeted Evidence Acquisition v0（单一 treatment）
  （真正算法级检索/采集实验；对全新有界 real ContextBench verified Python
   行 + RepoQA Python needle 重新运行多方法检索；确定性
   bea_v0_budgeted 策略，含 action trace + budget states；私有
   per-record SCORE JSONL 存于 /tmp；公开产物仅聚合 baseline-vs-treatment
   delta；无 provider 调用；无 winner/method_winner/default/calibration
   声明）
-> BEA-1 Mechanism Ablation Smoke（机制对比）
   （真正机制消融；与 BEA-0 相同的 fresh external run 形态，但新增三个
    同预算控制：same_budget_bm25_prefix、agreement_only_same_budget、
    seeded_random_same_budget；paired denominator 规则；机制对比
    records；私有 per-record SCORE JSONL 存于 /tmp，含 same-budget K +
    控制 arm evidence；records 形态的仅聚合公开产物；无 provider 调用；
    无 winner/method_winner/default/calibration 声明）
```

BEA-1 不是 BEA-0。BEA-0 度量 BEA v0 vs `bm25_top10`（以及启用 rrf 时
`rrf_bm25_regex_symbol_top10`）；BEA-1 度量 BEA v0 vs 三个同预算控制，
这些控制隔离 BEA-0 的增益（若有）是否来自多源 agreement / 序贯预算采集
而非仅仅是读取更少候选。

## 实现

### 评估器

`eval/bea1_mechanism_ablation.py` 提供 argparse CLI：

- `--self-test` — 无网络合成 self-test（420 项断言检查）。
- `--contextbench-row-limit` — 要评估的 ContextBench verified Python
  行数；默认 5，硬上限 20。
- `--repoqa-needle-limit` — 要评估的 RepoQA Python needle 数；默认 3，
  硬上限 10。
- `--budget` — `bea_v0_budgeted` 策略与同预算控制的证据预算；默认 5，
  硬上限 20。
- `--methods` — 逗号分隔的检索方法；默认 `bm25,regex,symbol`；允许
  `bm25,regex,symbol`；`bm25` 必需。
- `--enable-rrf-baseline` — 可选 flag，启用
  `rrf_bm25_regex_symbol_top10` baseline arm（默认禁用；不要因 rrf
  阻塞）。
- `--enable-external-benchmark-network` — 允许真实 HuggingFace + GitHub
  网络访问（默认 false；无 provider secrets/vars）。
- `--openlocus` — 可选 OpenLocus binary 路径（默认
  `target/release/openlocus` 然后 `target/debug/openlocus` 回退）。
- `--out` — 输出 artifact JSON 路径；默认
  `artifacts/bea1_mechanism_ablation/bea1_mechanism_ablation_report.json`。
- `--private-score-dir` — 显式私有 SCORE JSONL 目录（默认新
  `/tmp/bea0_private_score_<pid>_<ts>`；必须在 `/tmp` 或被 gitignore
  的 `runs/` 目录下）。

未知/私有形态参数会被拒绝，并以通用 `invalid arguments` 消息回退
（`SafeArgumentParser` 模式）。

### 固定 arm（无动态 arm 名）

- `bm25_top10`：正常 BM25 top-10 baseline；去重后前 10 个 BM25 候选；无
  预算匹配。
- `rrf_bm25_regex_symbol_top10`：启用时的多方法 RRF baseline；去重后
  bm25/regex/symbol 上前 10 个 RRF 候选。
- `bea_v0_budgeted`：BEA-0 确定性策略，仅使用 runtime-clean 特征；可能
  accept/skip/rerank/stop，仅将私有 action trace 记录到 SCORE。
- `same_budget_bm25_prefix`：去重后前 `K` 个 BM25 候选；无 agreement
  reranking，无 BEA 序贯 coverage/defer/expand 规则。
- `agreement_only_same_budget`：与 BEA 相同的去重候选宇宙；按 agreement
  desc、min_rank asc、max_normalized_score desc、稳定候选顺序排序；取前
  `K`；无 BEA 序贯 coverage/defer/expand 规则。
- `seeded_random_same_budget`：确定性 PRNG，固定公开种子 `20240621`；从
  稳定排序后相同的去重候选宇宙中采样 `K`；种子或排序中无
  gold/labels/row IDs/provider/model 字段。

这些 arm 回答 BEA-0 的增益是否来自多源 agreement / 序贯预算采集，而非
仅仅是读取更少候选。

### 同预算定义

同预算控制使用 per-record 候选数 `K`，确切定义如下：

```text
K = len(bea_v0_budgeted.accepted_candidates)
K = min(K, available_deduped_candidate_count)
```

若 BEA 对某条记录接受零候选，同预算控制也选择零，且该记录在机制对比中
标记为不可用，除非所有固定 arm 均有有效的零候选指标。公开产物绝不序列化
accepted candidates 或 candidate lists；仅聚合 arm/对比 records 公开。

### Paired denominator 规则

机制对比是 paired 的。一条对比仅包含 baseline 和 treatment arm 在同一
记录上均有有效指标的记录。若任一固定机制 arm 对某条记录失败，则：

- 从每条机制对比中排除该记录，并增加 `paired_exclusion_count`（以及
  `record_excluded_from_paired_denominator` failure category）；或
- 若排除导致低于最小 paired 计数，则将运行标记为 `partial`。

每条公开 `mechanism_contrast_records` 行必须包含 `record_count`，以便
delta 可解释。公开产物不序列化 per-record inclusion masks。

### 运行流程

1. Self-test 必须在任何 artifact 写入前通过
   （`_refuse_on_self_test_failure`）。
2. 解析 OpenLocus binary 为绝对路径（release 然后 debug 回退）。若缺失，
   生成 truthful `unavailable_with_reason` 报告。
3. 解析私有 SCORE JSONL 目录（默认新 `/tmp/bea0_private_score_*`；显式
   `--private-score-dir` 必须在 `/tmp` 或被 gitignore 的 `runs/` 目录
   下）。
4. 若 `--enable-external-benchmark-network` 为 false，写入 truthful
   `unavailable_with_reason` 报告，含
   `failure_reason_category=contextbench_fetch_failed`，并以 exit 0 退出
   （self-test + py_compile 仍运行；no-op 模式下生成 unavailable
   artifact）。
5. ContextBench arm：从 HF datasets-server `/rows` 获取有界 Python 行
   （默认 5 行；硬上限 20）。对每行：解析 `gold_context`（transient），
   净化 `problem_statement`（transient），在 per-row
   `TemporaryDirectory` 下于 `base_commit` 克隆 repo，运行多方法检索，
   运行所有固定 arm，计算 per-arm 指标，将私有 SCORE 行写入 `/tmp`。
6. RepoQA arm：下载 `repoqa-2024-06-23.json.gz` 到内存字节（transient），
   在内存中解压，解析有界 Python needle（默认 3；硬上限 10；NO silent
   all-language fallback）。对每条 needle：净化 `needle_description`
   （transient），在 per-needle `TemporaryDirectory` 下于 `commit_sha`
   克隆 repo，运行多方法检索，运行所有固定 arm，计算 per-arm 指标，将
   私有 SCORE 行写入 `/tmp`。
7. 在成功记录间聚合 per-arm 指标（每项 allowlisted 数值指标的均值）。
   计算 baseline-vs-treatment delta（每条 treatment arm vs 固定
   `bm25_top10` baseline）。在 paired denominator 上计算机制对比 records
   （BEA v0 vs 每个同预算控制）。
8. 构建 aggregate-only 公开报告，含 fail-closed forbidden scan。
9. Fail-closed：`provider_calls` 必须为 0；当网络启用且至少一条记录成功
   时，私有 SCORE record count 必须匹配 `records_successful`；
   forbidden scan 必须通过。

### 公开 artifact 身份

提交的 artifact
`artifacts/bea1_mechanism_ablation/bea1_mechanism_ablation_report.json`
是公开 aggregate-only smoke artifact。身份/边界字段：

- `schema_version` = `bea1_mechanism_ablation.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`
- `methods` = 使用的检索方法列表
- `budget` = 证据预算
- `enable_rrf_baseline` = bool
- `fixed_arms` = 固定 arm ID 列表（无动态 arm 名）
- `baseline_arm` = `bm25_top10`（固定）
- `treatment_arm` = `bea_v0_budgeted`（固定）
- `seeded_random_seed` = `20240621`（固定公开常量）
- `status`：`bea1_mechanism_ablation_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`
- Safe true flag（仅当确实为 true 时为 true）：
  `mechanism_ablation_performed`、`bea_v0_acquisition_performed`、
  `private_score_records_written`、`external_benchmark_rows_read`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- No-claim / no-runtime-change flag（均为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `calibration_claimed`、`method_winner_claimed`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- License 字段（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- `contextbench_row_limit_requested`、`repoqa_needle_limit_requested`、
  `records_evaluated`、`records_successful`、`records_failed`、
  `paired_exclusion_count`、`network_calls`、`provider_calls=0`、
  `aggregate_runtime_seconds`。
- `arm_metric_records`：固定形态 `{arm, metric, value}` records 列表
  （每 arm/metric 一条）。
- `delta_records`：固定形态
  `{baseline_arm, treatment_arm, metric, delta}` records 列表（每条
  treatment arm vs `bm25_top10`）。
- `mechanism_contrast_records`：固定形态
  `{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`
  records 列表（BEA v0 vs 每个同预算控制，在 paired denominator 上）。
- `private_score_manifest`：aggregate-only manifest 块，含
  `records_written`、`record_count`、`schema_version`、`manifest_hash`、
  `storage_class`、`path_publicly_serialized=false`。私有 SCORE 路径绝不
  序列化。
- `failure_category_counts`：仅固定 enum 类别。
- `failure_reason_category`（仅在 unavailable 状态出现）。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false`、
  `calibration_claimed=false`、`method_winner_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Per-arm metric records

`arm_metric_records` 块对每 arm/metric 含一条固定形态 record：
`{arm, metric, value}`。允许的指标：`file_recall@10`、`mrr`、
`span_f0.5@10`、`success_rate`、`candidate_count_read`、
`evidence_budget_used`、`action_steps`、`latency_seconds`、
`quality_per_candidate`。无动态 arm dict。

### Delta records

`delta_records` 块对每 treatment/metric 含一条固定形态 record：
`{baseline_arm, treatment_arm, metric, delta}`。每条 treatment arm
（`bea_v0_budgeted`、`same_budget_bm25_prefix`、
`agreement_only_same_budget`、`seeded_random_same_budget`，启用时还包括
`rrf_bm25_regex_symbol_top10`）与固定 `bm25_top10` baseline 比较。

### 机制对比 records

`mechanism_contrast_records` 块含固定形态 records：
`{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`。
固定对比 ID：

- `bea_vs_same_budget_bm25`：`bea_v0_budgeted` vs
  `same_budget_bm25_prefix`。
- `bea_vs_agreement_only`：`bea_v0_budgeted` vs
  `agreement_only_same_budget`。
- `bea_vs_seeded_random`：`bea_v0_budgeted` vs
  `seeded_random_same_budget`。

一条对比仅包含两条 arm 在同一记录上均有有效指标的记录（paired
denominator 规则）。每条 record 含 `record_count`，以便 delta 可解释。

### Unavailable 状态

若网络 smoke 无法完成（ContextBench 获取失败、RepoQA asset 下载失败、
解析失败、无 Python 行/needle、repo 克隆失败、retrieval 失败、私有 SCORE
写入失败等），artifact 记录 truthful `unavailable_with_reason`，含真实
`failure_reason_category` 及对应 `failure_category_counts` increment。
绝不写入 stale/fake pass。

在 unavailable 模式下，`arm_metric_records=[]`、`delta_records=[]`、
`mechanism_contrast_records=[]`、
`mechanism_ablation_performed=false`，但
`aggregate_only_public_artifact=true` 和 `diagnostic_only=true` 保持
true。

## 隐私 / license 边界

公开 artifact 与 docs 保持仅聚合。以下内容未被持久化到任何公开 artifact
或 doc：

- `repoqa-2024-06-23.json.gz` release asset（仅下载到 `/tmp`，在内存中
  解压，绝不提交或上传）；
- 原始 ContextBench 行 / RepoQA needle、query/problem statement、repo
  URL/name、base commit / commit SHA、gold path/span/content；
- 生成的 task/label/run JSONL（仅 transient `/tmp`）；
- OpenLocus evidence 行、snippet、path、line range、content_sha；
- 克隆的 repo/source file（仅 transient `/tmp`）；
- 原始命令 stdout/stderr 或 stack trace；
- per-record 指标或 per-record 失败记录；
- row ID / needle ID / row-level 值的 hash；
- 私有 per-record SCORE JSONL 行（仅写入 `/tmp` 或显式忽略的私有路径；
  私有 SCORE 路径绝不序列化到公开 artifact、docs 或 CI artifact）；
- action trace、budget state、accepted candidate、final candidate、
  candidate list、score outcome（私有 per-record 字段，仅 transient
  保留于 `/tmp`）。

公开 artifact 仅记录：聚合 per-arm metric records、baseline-vs-treatment
delta records、机制对比 records（含 `record_count`）、聚合私有 SCORE
manifest（records_written、record_count、schema_version、manifest_hash、
storage_class、path_publicly_serialized=false）、固定 failure-category
count、固定 config label（`methods`、`budget`、`fixed_arms`、
`baseline_arm`、`treatment_arm`、`seeded_random_seed`）、record count、
paired exclusion count、network/provider 调用计数，以及确定性
`generated_by` 路径。

ContextBench + RepoQA dataset license 未知
（`unknown_dataset_license`）；row-level redistribution 被禁用
（`row_level_redistribution_allowed=false`），derived row-level
publication 被禁用
（`derived_row_level_publication_allowed=false`）。Aggregate 指标
publication 允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 在无 HuggingFace/GitHub 时通过。
- 真正采集需要公开网络访问 HF datasets-server 与 GitHub。CI 为独立的显式
  `workflow_dispatch` job，带
  `enable_external_benchmark_network=true`。它默认不在 PR/push 上运行，
  不使用 provider secrets/vars、不使用 provider model env，且仅上传
  aggregate 报告。私有 SCORE JSONL 绝不上传。
- 若 `enable_external_benchmark_network` 为 false，workflow 为 no-op，
  输出清晰消息并以 exit 0 退出（self-test + py_compile 仍运行；生成
  unavailable aggregate artifact）。
- Workflow 在 smoke 后验证报告的 claim 边界 flag（fail-closed：网络启用
  CI 不可在 unavailable/no record 时通过）：要求 status 在
  （`bea1_mechanism_ablation_pass`、`partial`）中、`records_successful >=
  3`、每条机制对比 `record_count >= 3`、
  `forbidden_scan.status=pass`、`provider_calls=0`、私有 SCORE manifest
  存在且 `path_publicly_serialized=false`，任何位置无
  `winner`/`best_method`/`recommended_default`/`method_winner`/
  `calibration` 字段，任何位置无 BEA-1 私有字段。

## 禁止扫描器（公开，fail-closed）

严格 forbidden-output 扫描器在写入公开 JSON 前 fail-closed 运行。复用
BEA-0/C5-A/C5-D 禁止扫描器原语进行原始 key/value leak 检测，并新增
BEA-1 专属 claim 边界禁止 key（`calibration`、`method_winner`、
`best_method`、`recommended_default`、`winner`、`leaderboard`、
`promotion` 等）于任何位置。BEA-1 还放宽了对嵌套
`private_score_manifest.manifest_hash` sha256 hex 字符串的误报（合法聚合
manifest hash；可公开）。

`failure_category_counts`、`arm_metric_records`、`delta_records`、
`mechanism_contrast_records`、`private_score_manifest` 容器为 schema-key
容器，其子 key 为固定 category label 或 allowlisted metric/arm name；
forbidden_key 检查对这些子 key 放宽，但其下的 value 仍被扫描。

扫描器仅对最终公开聚合 artifact 运行。内部 task/label/run JSONL、私有
SCORE JSONL、以及 per-record 候选列表 / action trace / budget state /
accepted candidate / 同预算控制 arm evidence（含 path/span/query/gold）
仅保留在内存/transient `/tmp` 下，绝不对照公开契约扫描，且绝不提交。

## Self-test

`--self-test` 运行 28 组共 420 项确定性检查（无网络；合成候选 + 合成
gold record + 合成指标）：

1. Artifact 身份字段（schema、claim、status、mode、phase、generated_by、
   treatment_arm、baseline_arm、seeded_random_seed）。
2. Safe true flag 存在且值正确（8 项）。
3. No-claim / no-runtime-change false flag（15 项）。
4. License 字段（4 项）。
5. 私有 SCORE manifest aggregate-only 字段（manifest 存在、
   records_written、record_count、schema_version、storage_class、
   path_not_publicly_serialized、manifest_hash 为 sha256 hex、14 项
   forbidden private key 缺失）。
6. Row/needle/budget 硬上限（ContextBench 默认 5 / 上限 20；RepoQA
   默认 3 / 上限 10；budget 默认 5 / 上限 20；拒绝 0）。
7. Method 校验（默认；要求 bm25；拒绝 dense）。
8. Same-budget K 确切（min of bea_accepted 和 deduped；bea 接受零时为零；
   无 deduped 时为零；两者皆零时为零）。
9. same_budget_bm25_prefix arm（返回 K；K=0 时为零；首个 path 为
   path1）。
10. agreement_only_same_budget arm（返回 K；K=0 时为零；首个为高
    agreement span）。
11. seeded_random_same_budget arm（返回 K；K=0 时为零；确定性；K=3
    确定性；K 超过 deduped 时返回全部）。
12. seeded_random + agreement_only 在 gold/label/row-id 污染下的
    runtime-clean invariance。
13. arm_metric_records 固定形态（每条 record 恰好含 {arm, metric,
    value}；metric allowlisted；value 数值；arm 固定）。
14. delta_records 固定形态（每条 record 恰好含 {baseline_arm,
    treatment_arm, metric, delta}；baseline_arm=bm25_top10；metric
    allowlisted；delta 数值）。
15. mechanism_contrast_records 固定形态 + record_count（每条 record
    恰好含 {contrast, baseline_arm, treatment_arm, metric, delta,
    record_count}；contrast 固定；treatment_arm=bea_v0_budgeted；
    record_count 正；delta 数值）。
16. Failure category count 固定 enum（enum 内 key 通过；非 enum key
    被 builder 拒绝）。
17. Unavailable 报告（status、failure_reason_category、无 smoke flag、
    无 perf claim、空 arm_metric_records/delta_records/
    mechanism_contrast_records、private_score_manifest 存在且
    path_publicly_serialized=false、scan 通过）。
18. 扫描器拒绝禁止内容（BEA-0 专属禁止 key；repo URL/slug/commit SHA/
    file path/tmp path/multiline value）。
19. 扫描器允许 safe value（schema_version、methods、budget、
    arm_metric_records、delta_records、mechanism_contrast_records、
    private_score_manifest、failure_category）。
20. Fail-closed 生成（干净报告不 raise；private_score_path raise；
    action_trace raise；accepted_candidates raise；winner raise；
    best_method raise；calibration raise；self-test 失败拒绝 artifact
    生成）。
21. 公开 artifact 自扫描干净（skeleton + unavailable）。
22. CLI 参数面（`--self-test`、`--contextbench-row-limit`、
    `--repoqa-needle-limit`、`--budget`、`--methods`、`--openlocus`、
    `--out`、`--private-score-dir`、`--enable-rrf-baseline`、
    `--enable-external-benchmark-network`）。
23. 私有 SCORE writer round-trip（两行；解析为 JSON；path-leak 被扫描器
    检测）。
24. Paired denominator 规则（缺失某 arm 的记录在涉及该 arm 的对比中被
    排除；record_count 反映 paired denominator）。
25. Aggregate runtime seconds 存在（pass 报告含数值；unavailable
    省略）。
26. 任何位置无 winner/best_method/recommended_default/method_winner/
    calibration（5 项）。
27. Fixed arms 出现在 fixed_arms 列表中（rrf 禁用时 5 个 arm；rrf 禁用时
    排除 rrf）。
28. 扫描器拒绝 BEA-1 专属禁止 key（calibration、method_winner、
    best_method、recommended_default、winner 等）。

## 验证

```text
python3 -m py_compile eval/bea1_mechanism_ablation.py  => PASS
python3 eval/bea1_mechanism_ablation.py --self-test  => PASS (420/420 checks)
python3 eval/bea1_mechanism_ablation.py \
  --enable-external-benchmark-network \
  --contextbench-row-limit 5 --repoqa-needle-limit 3 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea1_mechanism_ablation/\
bea1_mechanism_ablation_report.json  => PASS
  (status: bea1_mechanism_ablation_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: bounded_external_retrieval_mechanism_ablation, phase: BEA-1,
   methods: bm25,regex,symbol, budget: 5,
   enable_rrf_baseline: true,
   fixed_arms: [bm25_top10, bea_v0_budgeted, same_budget_bm25_prefix,
                agreement_only_same_budget, seeded_random_same_budget,
                rrf_bm25_regex_symbol_top10],
   baseline_arm: bm25_top10, treatment_arm: bea_v0_budgeted,
   seeded_random_seed: 20240621,
   records_evaluated: 8, records_successful: 8, records_failed: 0,
   paired_exclusion_count: 0,
   network_calls: 2, provider_calls: 0,
   mechanism_ablation_performed: true,
   bea_v0_acquisition_performed: true,
   private_score_records_written: true,
   private_score_manifest.record_count: 8,
   private_score_manifest.storage_class: tmp_private,
   private_score_manifest.path_publicly_serialized: false,
   external_benchmark_rows_read: true,
   openlocus_retrieval_executed: true,
   score_py_metrics_computed: true,
   aggregate_only_public_artifact: true,
   diagnostic_only: true,
   external_benchmark_performance_claimed: false,
   leaderboard_entry_claimed: false,
   downstream_agent_value_proven: false,
   calibration_claimed: false, method_winner_claimed: false,
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

## 真实有界本地运行结果（2026-06-21）

使用 `--enable-external-benchmark-network
--contextbench-row-limit 5 --repoqa-needle-limit 3 --budget 5 --methods
bm25,regex,symbol --enable-rrf-baseline` 的有界本地运行成功完成。提交的
artifact 镜像该 sanitized aggregate 报告。

```text
python3 eval/bea1_mechanism_ablation.py \
  --enable-external-benchmark-network \
  --contextbench-row-limit 5 --repoqa-needle-limit 3 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea1_mechanism_ablation/\
bea1_mechanism_ablation_report.json
  => status: bea1_mechanism_ablation_pass,
     forbidden_scan: pass, self_test_passed: true
  => records_evaluated: 8, records_successful: 8, records_failed: 0
  => paired_exclusion_count: 0
  => network_calls: 2, provider_calls: 0
  => mechanism_ablation_performed: true
  => bea_v0_acquisition_performed: true
  => private_score_records_written: true
  => private_score_manifest.record_count: 8
  => private_score_manifest.storage_class: tmp_private
  => private_score_manifest.path_publicly_serialized: false
  => aggregate_runtime_seconds: 69.961

  arm_metric_records（8 条记录的均值）:
    bm25_top10:                    file_recall@10=0.5,    mrr=0.296875,
                                    span_f0.5@10=0.035962, success_rate=0.5,
                                    candidate_count_read=12.5, evidence_budget_used=6.25,
                                    action_steps=6.25, latency_seconds=0.4225,
                                    quality_per_candidate=0.001798
    rrf_bm25_regex_symbol_top10:   file_recall@10=0.5,    mrr=0.296875,
                                    span_f0.5@10=0.035962, success_rate=0.5,
                                    candidate_count_read=12.5, evidence_budget_used=6.25,
                                    action_steps=6.25, latency_seconds=1.42125,
                                    quality_per_candidate=0.001798
    bea_v0_budgeted:               file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.75, latency_seconds=4.408469,
                                    quality_per_candidate=0.002859
    same_budget_bm25_prefix:       file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.002859
    agreement_only_same_budget:    file_recall@10=0.375, mrr=0.28125,
                                    span_f0.5@10=0.057174, success_rate=0.375,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.002859
    seeded_random_same_budget:     file_recall@10=0.25,  mrr=0.1875,
                                    span_f0.5@10=0.020161, success_rate=0.25,
                                    candidate_count_read=12.5, evidence_budget_used=3.125,
                                    action_steps=3.125, latency_seconds=0.0,
                                    quality_per_candidate=0.001008

  mechanism_contrast_records（mrr，paired record_count=8）:
    bea_vs_same_budget_bm25:   delta(mrr)=0.0     （bea 与 same-budget BM25 prefix 持平）
    bea_vs_agreement_only:    delta(mrr)=0.0     （bea 与 agreement-only 持平）
    bea_vs_seeded_random:     delta(mrr)=+0.09375（bea 胜过 seeded random）
```

有界本地运行对 5 行 ContextBench verified Python 行 + 3 条 RepoQA Python
needle 重新运行检索，收集多方法候选（bm25/regex/symbol）以及可选 rrf
baseline，在 budget=5 下运行确定性 `bea_v0_budgeted` 策略以及三个同预算
控制，将 8 行私有 per-record SCORE JSONL 写入
`/tmp/bea0_private_score_<pid>_<ts>/bea1.private.jsonl`（transient；绝不
提交或上传），并仅提交聚合 per-arm metric records + baseline-vs-treatment
delta records + 机制对比 records（含 `record_count=8`）。

关键机制消融发现（smoke 级，**非** benchmark/calibration/method-winner
声明）：

- BEA v0 与 `agreement_only_same_budget` 在 paired denominator 上产生
  IDENTICAL 的 file_recall@10 / mrr / span_f0.5@10 / success_rate，且
  `evidence_budget_used=3.125` 相同。这表明 BEA v0 在此有界样本上相对
  纯 agreement-only rank（相同预算）的增益为零；BEA v0 的序贯
  coverage/defer/expand 规则未改变 accepted set 与更简单的 agreement-only
  排序的差异。
- BEA v0 与 `same_budget_bm25_prefix` 也产生 IDENTICAL 的
  file_recall@10 / mrr / span_f0.5@10 / success_rate，表明 BEA v0 的
  基于 agreement 的 reranking 在此有界样本上与 BM25-prefix 选择无差异
  （高 agreement span 也是 top BM25 span）。
- `seeded_random_same_budget` 在 mrr 上以 `delta(mrr)=+0.09375` 劣于
  BEA v0 与 agreement-only 控制，确认在此有界样本上基于确定性
  agreement 的选择在相同预算下优于随机选择。

这些是对有界样本的诚实 smoke 级聚合 delta，不是 benchmark 结果、
leaderboard 条目、性能声明、method-winner 声明、calibration 声明、
promotion、default 变更、runtime/retriever/pack/backend/EvidenceCore 语义
变更，或 downstream agent 价值声明。

若未来环境中网络 smoke 无法完成（ContextBench 获取失败、RepoQA asset
下载失败、解析失败、无 Python 行/needle、repo 克隆失败、retrieval 失败、
私有 SCORE 写入失败），artifact 记录 truthful
`unavailable_with_reason`，含真实 `failure_reason_category` 及对应
`failure_category_counts` increment。绝不写入 stale/fake pass。

## Caveats

- BEA-1 是公开 aggregate-only 机制消融 smoke artifact。它是
  eval/diagnostic only。它不更改 runtime、retriever、pack、backend 或
  default policy；它不更改 EvidenceCore 语义。它不是 benchmark 结果、不是
  leaderboard 条目、不是性能声明、不是 method-winner 声明、不是
  calibration 声明、不是 promotion、不是 default 变更、不是
  runtime-clean general algorithm 声明、且不是 downstream agent 价值
  声明。
- BEA-1 不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`，或任何暗示 policy/default 决策的字段。
- BEA-1 不运行 provider 调用，也不运行 remote provider 调用。
  `provider_calls=0`、`provider_calls_made=false`、
  `remote_provider_calls_made=false`。
- BEA-1 使用**有界 ContextBench verified Python 子集**（默认 5 行；硬
  上限 20）和**有界 RepoQA Python needle 子集**（默认 3 条 needle；硬
  上限 10）。这是 smoke，不是严格 benchmark 评估。聚合指标为有界样本上的
  点估计，不应解读为 benchmark 结果、leaderboard 条目、性能声明、
  method-winner 声明或 calibration。
- BEA-1 仅在 `/tmp`（或显式忽略的私有路径，位于被 gitignore 的 `runs/`
  目录下）写入私有 per-record SCORE JSONL。私有 SCORE 路径绝不序列化到
  公开 artifact、docs 或 CI artifact。公开 artifact 仅记录聚合 SCORE
  manifest 字段（`records_written`、`record_count`、`schema_version`、
  `manifest_hash`、`storage_class`、`path_publicly_serialized=false`）。
- BEA-1 不会从 Python 静默回退到所有语言。若
  `language_filter=python` 且无 Python 行/needle，artifact 为 truthful
  `unavailable_with_reason`，含真实 failure category。
- BEA-1 不声明 external benchmark 性能。聚合指标为 smoke 级 diagnostic，
  非 benchmark 结果。`external_benchmark_performance_claimed=false`。
- BEA-1 不声明 method winner。机制对比为诚实 baseline-vs-treatment
  delta；delta 可为正、零或负。`method_winner_claimed=false`。
- BEA-1 不证明 downstream agent 价值。机制消融 smoke 不演练任何
  downstream agent。`downstream_agent_value_proven=false`。
- BEA-1 不 bootstrap BEA-0 聚合 artifact。它重新运行 fresh external
  retrieval；不读取或不依赖 BEA-0 artifact。
- ContextBench + RepoQA dataset license 未知
  （`unknown_dataset_license`）；row-level redistribution 被禁用
  （`row_level_redistribution_allowed=false`），derived row-level
  publication 被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate 指标
  publication 允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有 no-claim / no-runtime-change flag 保持 false；diagnostic flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime claim 变更。EvidenceCore 语义不变。

## 下一步

- BEA-1 是首个机制消融 smoke。完整的 BEA-2 / BEA-3 阶段将需要更大样本、
  多预算设置、统计分析、score calibration 以及更丰富的策略特征（如
  anchor agreement、span-overlap geometry）。
- 从 BEA-1 不推导任何 promotion、default 变更、EvidenceCore 语义变更、
  runtime-clean general algorithm claim、method-winner claim、
  calibration claim、downstream agent 价值 claim。
