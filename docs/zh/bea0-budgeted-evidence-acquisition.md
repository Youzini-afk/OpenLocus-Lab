# BEA-0 Budgeted Evidence Acquisition v0

日期：2026-06-21（BEA-0 budgeted evidence acquisition v0，基于全新有界
ContextBench verified Python 行 + RepoQA Python needle，私有 per-record
SCORE JSONL 轨迹存于 `/tmp`，公开产物仅聚合计）

BEA-0 是 OpenLocus 研究轨中**第一个真正的算法级检索/采集实验**，将一个
确定性 budgeted 采集策略与私有 per-record SCORE JSONL 轨迹配对，公开仅
发布聚合的 baseline-vs-treatment delta。它对全新有界 ContextBench
verified Python 行 + RepoQA Python needle 重新运行检索，收集多方法候选
（`bm25`/`regex`/`symbol`，可选 `rrf`），运行确定性
`bea_v0_budgeted` 策略（在证据预算下），并计算每条 arm 的聚合
检索/采集指标，含相对 `bm25_top10`（启用 rrf 时还包括
`rrf_bm25_regex_symbol_top10`）的 baseline-vs-treatment delta。

BEA-0 明确**不是** benchmark 结果，**不是** leaderboard 条目，**不是**
性能声明，**不是** method-winner 声明，**不是** calibration 声明，**不是**
promotion，**不是** default/policy 变更，且**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它不会输出
`winner`、`best_method`、`recommended_default`、`method_winner`，或任何
暗示 policy/default 决策的字段。

> **重要 claim 边界**。BEA-0 输出 `claim_level =
> bea_v0_budgeted_acquisition_smoke_only`。它不声明 external benchmark
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

从 readiness/control-plane/aggregate-validation 工作转向一个真正的算法级
检索/采集实验，并保留私有 per-record SCORE 轨迹。BEA-0 实现并运行一个
确定性 budgeted 采集策略，对全新 external benchmark 数据重新运行，将私有
per-record SCORE JSONL 保留在 `/tmp`（绝不提交、绝不上传），仅公开聚合的
baseline-vs-treatment delta。

### 为什么这是真正的采集实验，而非聚合校验

- 对全新 ContextBench verified Python 行 + RepoQA Python needle 重新运行
  多方法检索（`bm25`/`regex`/`symbol` + 可选 `rrf`），通过
  `eval/run_retrieval.py:run_query()`。
- 为每条记录构建候选列表（method source、rank、score、normalized
  score、path、span、content_sha、extension）。
- 运行确定性 `bea_v0_budgeted` 策略，该策略只消费 runtime-clean 候选
  特征（无 gold labels、无 row IDs、无 benchmark labels、无 previous
  outcomes、无 provider/model 名、无私有 route buckets），生成 action
  trace + 在预算下的 accepted/final 候选列表。
- 使用 `eval/score.py` 函数对每条 arm 每条记录的合成内存 prediction
  record 计算指标。
- 将私有 per-record SCORE JSONL 行写入 `/tmp`（或显式忽略的私有路径），
  含完整 per-record 详情。
- 仅公开聚合的 per-arm 指标 + baseline-vs-treatment delta。

## C3 -> BEA-0 关系

```text
C3 Budgeted Evidence Acquisition v0（仅 replay）
  （基于 C1 private-records adapter 的 replay-only 策略实验；从预计算
   P21 per-strategy outcomes 中选择；无 fresh retrieval；无采集循环；
   diagnostic-rank-only；无 winner）
-> BEA-0 Budgeted Evidence Acquisition v0（真正采集循环）
   （真正算法级检索/采集实验；对全新有界 real ContextBench verified
    Python 行 + RepoQA Python needle 重新运行检索；确定性
    bea_v0_budgeted 策略，含 action trace + budget states；私有
    per-record SCORE JSONL 存于 /tmp；公开产物仅聚合 baseline-vs-
    treatment delta；无 provider 调用；无 winner/method_winner/
    default/calibration 声明）
```

BEA-0 不是 C3。C3 仅 replay，从预计算 P21 outcomes 中选择；BEA-0 真正
重新运行检索，并在预算下采集证据，附带私有 per-record SCORE 轨迹。

## 实现

### 评估器

`eval/bea0_budgeted_evidence_acquisition.py` 提供 argparse CLI：

- `--self-test` — 无网络合成 self-test（212 项断言检查）。
- `--contextbench-row-limit` — 要评估的 ContextBench verified Python
  行数；默认 10，硬上限 20。
- `--repoqa-needle-limit` — 要评估的 RepoQA Python needle 数；默认 5，
  硬上限 10。
- `--budget` — `bea_v0_budgeted` 策略的证据预算；默认 10，硬上限 20。
- `--methods` — 逗号分隔的检索方法；默认 `bm25,regex,symbol`；允许
  `bm25,regex,symbol`；`bm25` 必需（treatment 的主 rank 特征）。
- `--enable-rrf-baseline` — 可选 flag，启用
  `rrf_bm25_regex_symbol_top10` baseline arm（默认禁用；不要因 rrf
  阻塞）。
- `--enable-external-benchmark-network` — 允许真实 HuggingFace + GitHub
  网络访问以进行 ContextBench 行获取 + RepoQA asset 下载 + repo clone
  （默认 false；无 provider secrets/vars）。
- `--openlocus` — 可选 OpenLocus binary 路径（默认
  `target/release/openlocus` 然后 `target/debug/openlocus` 回退；解析为
  绝对路径，因为 `run_retrieval.py` 以 `--cwd <repo_root>` 运行）。
- `--out` — 输出 artifact JSON 路径；默认
  `artifacts/bea0_budgeted_evidence_acquisition/bea0_budgeted_evidence_acquisition_report.json`。
- `--private-score-dir` — 显式私有 SCORE JSONL 目录（默认新
  `/tmp/bea0_private_score_<pid>_<ts>`；必须在 `/tmp` 或被 gitignore
  的 `runs/` 目录下）。

未知/私有形态参数会被拒绝，并以通用 `invalid arguments` 消息回退，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### BEA v0 budgeted 策略（runtime-clean，确定性）

Treatment 策略 `bea_v0_budgeted` 只消费在评分前可用的 runtime-clean
候选特征：

- method source（`bm25` / `regex` / `symbol`）；
- 候选在 method 内的 rank；
- score 或 normalized score（如可用，在每个 method 的 evidence list
  内归一化：max score -> 1.0）；
- 跨 method 的 rank agreement（多少个不同 method 返回同一
  `(path, start_line, end_line)` span）；
- 重复 path/span overlap（method 内及跨 method）；
- 候选总数；
- 已接受 file/path 覆盖；
- 剩余预算；
- 廉价 path kind/file extension 元数据。

它不得使用 gold files/lines/labels、row IDs、benchmark 专属 answer
hints、同一记录的 previous outcome、provider/model 名、或私有 route
buckets。评估器验证 routing invariance：当向候选列表添加合成
gold/label/row-id/model-family/previous-outcome 字段时，候选策略产生
IDENTICAL 的 accepted/action_trace/budget_states（因为策略忽略它们）。

算法：

1. 计算每 span 的 agreement：多少个不同 method 返回同一
   `(path, start_line, end_line)` span。构建每 span 的摘要，含 max
   normalized_score、min rank、agreement count、method set。
2. 对去重后的 span 列表排序：
   (a) agreement count DESC（多 method agreement 优先）；
   (b) 跨 method 的 min rank ASC（rank 越低越早）；
   (c) max normalized_score DESC（score 越高越优先）。
3. 在 `budget` 接受候选的预算下迭代排序后的列表。对每个候选：
   - 若预算耗尽：emit `stop_budget_exhausted` 并 break。
   - 若 span 有 `agreement==1` 且 `min_rank>5` 且
     `max_norm_score<0.01`：emit `skip_low_support`（跳过，不
     accept）。
   - 若 span 有 `agreement>=2` 且 path 已在 `accepted_paths`：
     emit `rerank_by_agreement` 并 defer（推入 deferred 池）。
   - 否则：emit `accept_candidate` 并追加到 accepted；标记 path。
4. 主循环后，若预算仍有剩余，将 deferred `rerank_by_agreement` 候选作为
   `expand_same_file` action 处理（在预算下保留额外同文件候选）。

初始 action：`accept_candidate`、`skip_low_support`、
`rerank_by_agreement`、`stop_budget_exhausted`。可选（如容易）：
`expand_same_file`（在预算下保留额外同文件候选）。

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
   （self-test + py_compile 仍运行；no-op 模式下除 unavailable artifact
   外不产生 aggregate 报告）。
5. ContextBench arm：从 HF datasets-server `/rows` 获取有界 Python 行
   （默认 10 行；硬上限 20；仅 stdlib `urllib`）。对每行：解析
   `gold_context`（transient），将 `problem_statement` 净化为检索 query
   （transient），在 per-row `TemporaryDirectory` 下于 `base_commit`
   克隆 repo，通过 `eval/run_retrieval.py:run_query()` 运行多方法检索，
   运行 baseline + treatment，计算 per-arm 指标，将私有 SCORE 行写入
   `/tmp`。
6. RepoQA arm：下载 `repoqa-2024-06-23.json.gz` 到内存字节（transient），
   在内存中解压，解析有界 Python needle（默认 5；硬上限 10；NO silent
   all-language fallback）。对每条 needle：净化 `needle_description`
   （transient），在 per-needle `TemporaryDirectory` 下于 `commit_sha`
   克隆 repo，运行多方法检索，运行 baseline + treatment，计算 per-arm
   指标，将私有 SCORE 行写入 `/tmp`。
7. 在成功记录间聚合 per-arm 指标（每项 allowlisted 数值指标的均值）。
   计算 baseline-vs-treatment delta。
8. 构建 aggregate-only 公开报告，含 fail-closed forbidden scan。
9. Fail-closed：`provider_calls` 必须为 0；当网络启用且至少一条记录成功
   时，私有 SCORE record count 必须匹配 `records_successful`；
   forbidden scan 必须通过。

### 公开 artifact 身份

提交的 artifact
`artifacts/bea0_budgeted_evidence_acquisition/bea0_budgeted_evidence_acquisition_report.json`
是公开 aggregate-only smoke artifact。身份/边界字段：

- `schema_version` = `bea0_budgeted_evidence_acquisition.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`
- `methods` = 使用的检索方法列表
- `budget` = 证据预算
- `enable_rrf_baseline` = bool
- `baseline_arms` = `[bm25_top10]`（或启用 rrf 时为
  `[bm25_top10, rrf_bm25_regex_symbol_top10]`）
- `treatment_arm` = `bea_v0_budgeted`
- `status`：`bea_v0_smoke_pass` | `partial` | `unavailable_with_reason` |
  `fail_forbidden_scan` | `fail_schema_contract`
- Safe true flag（仅当确实为 true 时为 true）：
  `bea_v0_acquisition_performed`、`multi_method_candidates_collected`、
  `budgeted_policy_executed`、`private_score_records_written`、
  `external_benchmark_rows_read`、`repositories_materialized_transiently`、
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
  `network_calls`、`provider_calls=0`、`aggregate_runtime_seconds`。
- `arm_metric_records`：per-arm 聚合指标，仅 allowlisted。
- `delta_records`：per-arm baseline-vs-treatment delta，仅 allowlisted。
- 私有 SCORE manifest（仅聚合；不序列化路径）：
  `private_score_records_written`（仅当确实写入时为 true）、
  `private_score_record_count`、`private_score_schema_version`、
  `private_score_manifest_hash`（内存中 manifest schema 的 sha256，绝非
  row 内容的 sha256）、`private_score_storage_class`（`tmp_private` 或
  `ignored_private`）、`private_score_path_publicly_serialized=false`。
- `failure_category_counts`：仅固定 enum 类别。
- `failure_reason_category`（仅在 unavailable 状态出现）。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false`、
  `calibration_claimed=false`、`method_winner_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Per-arm 聚合指标

`arm_metric_records` 块对每条 arm（`bm25_top10`、`bea_v0_budgeted`，可选
`rrf_bm25_regex_symbol_top10`）包含一项。每项仅含 allowlisted 指标名：

- `file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`（来自
  `eval/score.py` 函数，作用于合成内存 prediction record）。
- `candidate_count_read`（该 arm 收集的总候选数）。
- `evidence_budget_used`（该 arm 实际保留的候选数）。
- `action_steps`（action trace 长度；baseline 等于 evidence 数）。
- `latency_seconds`（该 arm 的 per-record 平均 latency）。
- `quality_per_candidate`（`span_f0.5@10 / candidate_count_read`）。

### Baseline-vs-treatment delta

`delta_records` 块含每项指标的 delta（treatment - baseline）：

- `bea_v0_budgeted` vs `bm25_top10`（treatment 运行时始终存在）。
- `rrf_bm25_regex_symbol_top10` vs `bm25_top10`（仅当 rrf baseline
  启用时）。

有效结果可为 improvement、相同质量但更少预算、no-delta、或质量损失但含
causal action-trace 失败模式。Artifact 对任一情形均诚实。

### Unavailable 状态

若网络 smoke 无法完成（ContextBench 获取失败、RepoQA asset 下载失败、
解析失败、无 Python 行/needle、repo 克隆失败、retrieval 失败、私有
SCORE 写入失败等），artifact 记录 truthful `unavailable_with_reason`，
含真实 `failure_reason_category` 及对应 `failure_category_counts`
increment。绝不写入 stale/fake pass。

在 unavailable 模式下，`arm_metric_records=[]`、`delta_records=[]`、
`bea_v0_acquisition_performed=false`，但
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
  私有 SCORE 路径绝不序列化到公开 artifact、docs 或 CI artifact）。

公开 artifact 仅记录：来自 `eval/score.py` + 确定性 budgeted 采集策略
accounting 的聚合 per-arm metric mean/rate/count（allowlisted）、
baseline-vs-treatment delta（allowlisted）、固定 failure-category count、
固定 config label（`methods`、`budget`、`baseline_arms`、
`treatment_arm`）、record count、network/provider 调用计数、私有 SCORE
manifest aggregate-only 字段（`private_score_records_written`、
`private_score_record_count`、`private_score_schema_version`、
`private_score_manifest_hash`、`private_score_storage_class`、
`private_score_path_publicly_serialized=false`），以及确定性
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
- 真正采集需要公开网络访问 HF datasets-server 与 GitHub（asset 下载 +
  repo clone）。CI 为独立的显式 `workflow_dispatch` job，带
  `enable_external_benchmark_network=true`。它默认不在 PR/push 上运行，
  不使用 provider secrets/vars、不使用 provider model env，且仅上传
  aggregate 报告。私有 SCORE JSONL 绝不上传。
- 若 `enable_external_benchmark_network` 为 false，workflow 为 no-op，
  输出清晰消息并以 exit 0 退出（self-test + py_compile 仍运行；生成
  unavailable aggregate artifact）。
- Workflow 在 smoke 后验证报告的 claim 边界 flag（fail-closed：网络启用
  CI 不可在 unavailable/no record 时通过；要求 status 在
  （`bea_v0_smoke_pass`，`partial`）中、`records_successful > 0`、
  `forbidden_scan.status=pass`、`provider_calls=0`、
  `private_score_record_count == records_successful`，且任何位置无
  `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration`
  字段）。

## 禁止扫描器（公开，fail-closed）

严格 forbidden-output 扫描器在写入公开 JSON 前 fail-closed 运行。复用
C5-A/C5-D 禁止扫描器原语进行原始 key/value leak 检测，并新增 BEA-0 专属
检查：

- 拒绝 BEA-0 专属禁止 dict key（`private_score_path`、`score_path`、
  `private_score_file`、`private_record_id`、`private_record_hash`、
  `action_trace`、`action_steps_trace`、`budget_state`、
  `budget_states`、`accepted_candidates`、`final_candidates`、
  `candidate_list`、`candidates`、`score_outcome`、
  `per_record_metrics`、`runtime_query_features`、
  `query_feature_summary`、`query_features`、`benchmark_row_id`、
  `benchmark_record_id`、`benchmark_label`、`phase_run_id`、`run_id`、
  `task_id`、`row_id`、`needle_id`、`instance_id`、`provider_name`、
  `model_name`、`model_family`、`provider_payload`、`private_bucket`、
  `route_bucket`、`task_bucket`）于任何位置。
- 拒绝 recommendation / policy 字段于任何位置：`winner`、`best_method`、
  `recommended_default`、`recommended_method`、`preferred_method`、
  `default_method`、`policy_decision`、`decision`、`ranking`、`rank`。
- 拒绝 value 模式：任何 URL（无 URL allowlist — repo URL 绝不 leak）、
  32+ 字符 hex digest（除在 `private_score_manifest_hash` 等 safe
  value path 下）、40 字符 commit SHA、`psf/black` 形 repo slug、
  secret-like 字符串、带文件扩展名的 path-like 字符串、`/tmp/`
  workspace path value、`task_N`/`needle_N` task-identifier value、
  patch/diff marker（`---`、`+++`、`@@`）、stack trace、多行字符串、
  raw JSON 片段、raw line range `585-639`，以及 self-test sentinel。

`failure_category_counts`、`aggregate_metrics`、`arm_metric_records`、`delta_records`
容器为 schema-key 容器，其子 key 为固定 category label 或 allowlisted
metric/arm name（非 row-level 值）；forbidden_key 检查对这些子 key
放宽，但其下的 value 仍被扫描（必须仅是 int/float/短字符串）。

扫描器仅对最终公开聚合 artifact 运行。内部 task/label/run JSONL、私有
SCORE JSONL、以及 per-record 候选列表 / action trace / budget state /
accepted candidate（含 path/span/query/gold）仅保留在内存/transient
`/tmp` 下，绝不对照公开契约扫描，且绝不提交。

## Self-test

`--self-test` 运行 26 组共 212 项确定性检查（无网络；合成候选 + 合成
gold record + 合成指标）：

1. Artifact 身份字段（schema、claim、status、mode、phase、generated_by、
   treatment_arm、baseline_arms）。
2. Safe true flag 存在且值正确（10 项）。
3. No-claim / no-runtime-change false flag（15 项）。
4. License 字段（4 项）。
5. 私有 SCORE manifest aggregate-only 字段（records_written、
   record_count、schema_version、storage_class、
   path_not_publicly_serialized、manifest_hash 为 sha256 hex、14 项
   forbidden private key 缺失）。
6. Row/needle limit 硬上限（ContextBench 默认 10 / 上限 20；RepoQA
   默认 5 / 上限 10；拒绝 0）。
7. Budget 硬上限（默认 10；上限 20；在 20 截断；拒绝 0）。
8. Method 校验（默认；dedup 保序；要求 bm25；拒绝 dense；拒绝空）。
9. Path 扩展名 helper（py、rs、none、小写）。
10. BEA v0 budgeted 策略机制（接受非空；首个接受为高 agreement；含
    accept_candidate action；跳过 low_support；budget state 非空；
    budget_remaining 递减）。
11. 策略尊重预算上限（budget=3、budget=1、budget=0、空候选）。
12. 策略 runtime-clean invariance（在候选中加入合成 gold/label/row-id/
    model-family/previous-outcome 字段时，accepted list + action
    trace 完全一致）。
13. Per-arm 指标 + delta（bm25 file_recall/mrr/success_rate = 1.0；
    空 evidence = 0；delta 为正）。
14. 聚合均值（file_recall=1.0；candidate_count_read=4；空=0）。
15. Arm 指标 allowlist 过滤（排除 path/row_id/content_sha/arm；含
    mrr）。
16. Failure category count 固定 enum（enum 内 key 通过；非 enum key
    被 builder 拒绝）。
17. Unavailable 报告（status、failure_reason_category、无 smoke flag、
    无 perf claim、空 arm_metric_records/delta_records、无私有 score path、scan
    通过）。
18. 扫描器拒绝禁止内容（BEA-0 专属禁止 key；repo URL/slug/commit SHA/
    file path/tmp path/multiline value）。
19. 扫描器允许 safe value（schema_version、methods、budget、
    arm_metric_records、delta_records、private_score_manifest_hash、
    failure_category）。
20. Fail-closed 生成（干净报告不 raise；private_score_path raise；
    action_trace raise；accepted_candidates raise；winner raise；
    best_method raise；self-test 失败拒绝 artifact 生成）。
21. 公开 artifact 自扫描干净（skeleton + unavailable）。
22. CLI 参数面（`--self-test`、`--contextbench-row-limit`、
    `--repoqa-needle-limit`、`--budget`、`--methods`、`--openlocus`、
    `--out`、`--private-score-dir`、`--enable-rrf-baseline`）。
23. 私有 SCORE writer round-trip（两行；解析为 JSON；path-leak 被扫描器
    检测）。
24. Arm 指标 allowlist 子集（全部 9 项 allowlisted key 出现在过滤后
    输出）。
25. Aggregate runtime seconds 存在（pass 报告含数值；unavailable
    省略）。
26. 任何位置无 winner/best_method/recommended_default/method_winner/
    calibration（5 项）。

## 验证

```text
python3 -m py_compile eval/bea0_budgeted_evidence_acquisition.py  => PASS
python3 eval/bea0_budgeted_evidence_acquisition.py --self-test  => PASS (212/212 checks)
python3 eval/bea0_budgeted_evidence_acquisition.py \
  --contextbench-row-limit 2 --repoqa-needle-limit 1 \
  --budget 5 --methods bm25,regex,symbol \
  --enable-rrf-baseline --enable-external-benchmark-network \
  --openlocus target/debug/openlocus \
  --out artifacts/bea0_budgeted_evidence_acquisition/\
bea0_budgeted_evidence_acquisition_report.json  => PASS
  (status: bea_v0_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: bea_v0_budgeted_acquisition, phase: BEA-0,
   methods: bm25,regex,symbol, budget: 5,
   enable_rrf_baseline: true,
   baseline_arms: [bm25_top10, rrf_bm25_regex_symbol_top10],
   treatment_arm: bea_v0_budgeted,
   records_evaluated: 3, records_successful: 3, records_failed: 0,
   network_calls: 2, provider_calls: 0,
   bea_v0_acquisition_performed: true,
   multi_method_candidates_collected: true,
   budgeted_policy_executed: true,
   private_score_records_written: true,
   private_score_record_count: 3,
   private_score_schema_version: bea0_private_score.v1,
   private_score_storage_class: tmp_private,
   private_score_path_publicly_serialized: false,
   external_benchmark_rows_read: true,
   repositories_materialized_transiently: true,
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

## 真实有界手动 CI run `27934507148`结果（2026-06-21）

使用 `--contextbench-row-limit 2 --repoqa-needle-limit 1 --budget 5
--methods bm25,regex,symbol --enable-rrf-baseline
--enable-external-benchmark-network --openlocus target/release/openlocus`
的有界手动 CI run `27934507148`成功完成。提交的 artifact 镜像该 sanitized aggregate
报告。

```text
python3 eval/bea0_budgeted_evidence_acquisition.py \
  --contextbench-row-limit 2 --repoqa-needle-limit 1 \
  --budget 5 --methods bm25,regex,symbol \
  --enable-rrf-baseline --enable-external-benchmark-network \
  --openlocus target/release/openlocus
  => status: bea_v0_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => records_evaluated: 3, records_successful: 3, records_failed: 0
  => network_calls: 2, provider_calls: 0
  => bea_v0_acquisition_performed: true
  => multi_method_candidates_collected: true
  => budgeted_policy_executed: true
  => private_score_records_written: true
  => private_score_record_count: 3
  => private_score_storage_class: tmp_private
  => private_score_path_publicly_serialized: false
  => arm_metric_records arm=bm25_top10:    file_recall@10=0.666667, mrr=0.666667,
     span_f0.5@10=0.059187, success_rate=0.666667,
     candidate_count_read=13.333333, evidence_budget_used=6.666667,
     action_steps=6.666667, latency_seconds=0.444333,
     quality_per_candidate=0.002959
  => arm_metric_records arm=rrf_bm25_regex_symbol_top10:
     file_recall@10=0.666667, mrr=0.666667, span_f0.5@10=0.059187,
     success_rate=0.666667, candidate_count_read=13.333333,
     evidence_budget_used=6.666667, action_steps=6.666667,
     latency_seconds=1.314, quality_per_candidate=0.002959
  => arm_metric_records arm=bea_v0_budgeted: file_recall@10=0.666667,
     mrr=0.666667, span_f0.5@10=0.086849, success_rate=0.666667,
     candidate_count_read=13.333333, evidence_budget_used=3.333333,
     action_steps=4.0, latency_seconds=4.253045,
     quality_per_candidate=0.004343
  => delta_records treatment_arm=bea_v0_budgeted（vs bm25_top10）:
     file_recall@10=0.0, mrr=0.0, span_f0.5@10=+0.027662,
     success_rate=0.0, evidence_budget_used=-3.333334,
     action_steps=-2.666667, quality_per_candidate=+0.001384,
     latency_seconds=+3.808712, candidate_count_read=0.0
  => aggregate_runtime_seconds: 25.65
```

有界手动 CI run `27934507148`对 2 行 ContextBench verified Python 行 + 1 条 RepoQA
Python needle 重新运行检索，收集多方法候选（bm25/regex/symbol）以及可选
rrf baseline，在 budget=5 下运行确定性 `bea_v0_budgeted` 策略，将 3 行
私有 per-record SCORE JSONL 写入
`/tmp/bea0_private_score_<pid>_<ts>/bea0.private.jsonl`（transient；
绝不提交或上传），并仅提交聚合 per-arm 指标 + baseline-vs-treatment
delta。Treatment 在使用约一半 evidence budget
（`evidence_budget_used=3.33` vs `6.67`）的情况下，与 `bm25_top10` 和
`rrf_bm25_regex_symbol_top10` 保持 file_recall@10 / mrr / success_rate
持平，并将 `span_f0.5@10` 提升 `+0.028`、`quality_per_candidate` 提升
`+0.0014`。这是对有界样本的诚实 smoke 级聚合 delta，不是 benchmark
结果、leaderboard 条目、性能声明、method-winner 声明、calibration 声明、
promotion、default 变更、runtime/retriever/pack/backend/EvidenceCore 语义
变更，或 downstream agent 价值声明。

若未来环境中网络 smoke 无法完成（ContextBench 获取失败、RepoQA asset
下载失败、解析失败、无 Python 行/needle、repo 克隆失败、retrieval 失败、
私有 SCORE 写入失败），artifact 记录 truthful
`unavailable_with_reason`，含真实 `failure_reason_category` 及对应
`failure_category_counts` increment。绝不写入 stale/fake pass。

## Caveats

- BEA-0 是公开 aggregate-only budgeted evidence acquisition v0 smoke
  artifact。它是 eval/diagnostic only。它不更改 runtime、retriever、
  pack、backend 或 default policy；它不更改 EvidenceCore 语义。它不是
  benchmark 结果、不是 leaderboard 条目、不是性能声明、不是
  method-winner 声明、不是 calibration 声明、不是 promotion、不是
  default 变更、不是 runtime-clean general algorithm 声明、且不是
  downstream agent 价值声明。
- BEA-0 不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`，或任何暗示 policy/default 决策的字段。
- BEA-0 不运行 provider 调用，也不运行 remote provider 调用。唯一的
  网络调用是对公开 HuggingFace datasets-server 与 GitHub（下载 RepoQA
  release asset 并在 transient `/tmp` 目录下于 commit SHA 克隆引用
  repo）。`provider_calls=0`、`provider_calls_made=false`、
  `remote_provider_calls_made=false`。
- BEA-0 使用**有界 ContextBench verified Python 子集**（默认 10 行；硬
  上限 20）和**有界 RepoQA Python needle 子集**（默认 5 条 needle；
  硬上限 10）。这是 smoke，不是严格 benchmark 评估。聚合指标为有界样本
  上的点估计，不应解读为 benchmark 结果、leaderboard 条目、性能声明、
  method-winner 声明或 calibration。
- BEA-0 仅在 `/tmp`（或显式忽略的私有路径，位于被 gitignore 的
  `runs/` 目录下）写入私有 per-record SCORE JSONL。私有 SCORE 路径绝不
  序列化到公开 artifact、docs 或 CI artifact。公开 artifact 仅记录聚合
  SCORE manifest 字段（`private_score_records_written`、
  `private_score_record_count`、`private_score_schema_version`、
  `private_score_manifest_hash`、`private_score_storage_class`、
  `private_score_path_publicly_serialized=false`）。
- BEA-0 不会从 Python 静默回退到所有语言。若
  `language_filter=python` 且无 Python 行/needle，artifact 为 truthful
  `unavailable_with_reason`，含真实 failure category。
- BEA-0 不声明 external benchmark 性能。聚合指标为 smoke 级 diagnostic，
  非 benchmark 结果。`external_benchmark_performance_claimed=false`。
- BEA-0 不声明 method winner。Treatment 为确定性 budgeted 采集策略，
  含诚实 baseline-vs-treatment delta；delta 可为正、零或负。
  `method_winner_claimed=false`。
- BEA-0 不证明 downstream agent 价值。采集 smoke 不演练任何 downstream
  agent。`downstream_agent_value_proven=false`。
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

- BEA-0 是首个带私有 per-record SCORE 轨迹的真正算法级检索/采集实验。
  完整的 BEA-1 / BEA-2 阶段将需要更大样本、多预算设置、统计分析以及更
  丰富的策略特征（如 score calibration、anchor agreement、span-overlap
  geometry）。
- 从 BEA-0 不推导任何 promotion、default 变更、EvidenceCore 语义变更、
  runtime-clean general algorithm claim、method-winner claim、
  calibration claim、downstream agent 价值 claim。
