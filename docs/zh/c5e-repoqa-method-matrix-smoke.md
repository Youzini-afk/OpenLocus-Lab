# C5-E RepoQA 方法矩阵检索 Smoke

日期：2026-06-21（C5-E RepoQA 有界检索方法矩阵 smoke，基于 EvalPlus
RepoQA/SNF release asset `repoqa-2024-06-23.json.gz`，将 C5-D 单方法
RepoQA `bm25` smoke 扩展为 `bm25,regex,symbol` 有界多方法矩阵 smoke）

C5-E 是 C5-D RepoQA 检索性能 smoke 的**有界多方法矩阵扩展**。它从
`evalplus/repoqa_release` 下载 EvalPlus RepoQA release asset
`repoqa-2024-06-23.json.gz` 到内存字节（临时；**绝不**写入工作区），在内存
中解压，解析有界 RepoQA Python needle subset，在临时 `/tmp` 目录下（每方法+
每 needle 一次）检出引用仓库到其 `commit_sha`，跨请求方法矩阵运行 OpenLocus
检索（默认 `bm25,regex,symbol`；仅允许 `bm25,regex,symbol`；固定
`baseline_method=bm25`；无 provider 调用），通过现有 `eval/score.py` 逻辑对
每种方法针对 `needle.path`/`start_line`/`end_line` 打分，并提交**仅一个
aggregate 公共报告**，其中包含每方法 aggregate metrics（记录，**非**动态
方法名 key 的 dict）、仅 aggregate 的与固定 `bm25` baseline 的 delta，以及
每方法 `aggregate_runtime_seconds`。

C5-E 明确**不是** benchmark 结果，**不是**leaderboard 条目，**不是**性能
声称，**不是**promotion，**不是**默认/策略变更，也**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它**不**输出 `winner`、
`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。

> **重要 claim 边界。** C5-E 输出 `claim_level =
> repoqa_retrieval_method_matrix_smoke_only`。它**不**声称外部 benchmark 结果、
> **不**声称 leaderboard 条目、**不**声称性能、**不**promotion、**不**默认
> 变更、**不**runtime/retriever/pack/backend 变更、**不**EvidenceCore 语义
> 变更，也**不**下游 agent 价值声称。所有 no-claim / no-runtime-change 标志
> 均为 false。

## 目标

将 C5-D 从单方法 RepoQA `bm25` 扩展为 `bm25,regex,symbol` 有界方法矩阵。这是
经验性外部-benchmark-形态的检索工作：临时下载 EvalPlus RepoQA release asset，
在内存中解析 Python needle，临时克隆引用仓库，按方法运行 OpenLocus 检索，用
`eval/score.py` 打分，并仅发布 aggregate metrics。

## C5-A -> C5-B -> C5-C -> C5-D -> C5-E 关系

```text
C5-A ContextBench verified retrieval performance smoke (single-method)
-> C5-B ContextBench verified method matrix smoke (5-row, 3 methods)
-> C5-C ContextBench verified method matrix scale smoke (20-row, 3 methods)
-> C5-D RepoQA BM25 retrieval performance smoke (single-method bm25)
-> C5-E RepoQA method-matrix retrieval smoke
   (multi-method matrix; bm25,regex,symbol only (no text);
    bounded 5-needle RepoQA Python subset per method;
    transient /tmp asset download + clone + retrieval + score;
    per-method aggregate records with aggregate_runtime_seconds;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default;
    status pass enum repoqa_method_matrix_smoke_pass)
```

C5-E **不是** C5。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/
可行性阶段。C5-E 仅通过在有界 RepoQA Python needle subset 上跨请求方法矩阵
运行真实 OpenLocus 检索 + 打分管线，产出第一个经验性 RepoQA 形态的检索方法
矩阵 smoke。

## 实现

### Evaluator

`eval/c5e_repoqa_method_matrix_smoke.py` 提供 argparse CLI：

- `--self-test` —— 无网络合成 self-test（228 组断言）。
- `--needle-limit` —— 每方法评估的 RepoQA Python needle 数；默认 5，硬上限
  10。
- `--methods` —— 逗号分隔的 OpenLocus 检索方法；默认 `bm25,regex,symbol`；
  仅允许 `bm25,regex,symbol`（C5-E **不**允许 `text`）；未知方法被拒绝；
  重复项按首次出现顺序确定性去重。
- `--language-filter` —— 语言过滤类别；默认 `python`；仅允许 `python`
  （C5-E **不**静默回退到所有语言）。
- `--openlocus` —— 可选的 OpenLocus 二进制路径（默认
  `target/release/openlocus`，然后 `target/debug/openlocus` 回退；解析为
  绝对路径）。
- `--out` —— 输出 artifact JSON 路径；默认
  `artifacts/c5e_repoqa_method_matrix_smoke/c5e_repoqa_method_matrix_smoke_report.json`。

未知/私有的参数会被拒绝，并显示固定的 `invalid arguments` 消息，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### Runtime 流程

1. Self-test 必须在任何 artifact 写入之前通过。
2. 解析方法（无效配置时抛出 `MethodConfigError`；失败时产出
   `fail_schema_contract` 报告）。
3. 将 OpenLocus 二进制解析为绝对路径。若缺失，产出真实的
   `unavailable_with_reason` 报告。
4. 下载 `repoqa-2024-06-23.json.gz` release asset 到内存字节（临时；**绝不**
   写入工作区）。
5. 在内存中解压 + 解析 asset。
6. 在内存中解析 RepoQA needle：按 `language_filter=python` 过滤（**无**静默
   全语言回退）。
7. 对每种方法（`bm25,regex,symbol`），对每个 needle：在每方法+每 needle
   `TemporaryDirectory` 下克隆仓库到 `commit_sha`；生成临时 task/label JSONL；
   通过 `eval/run_retrieval.py` 运行 OpenLocus 检索；运行 `eval/score.py`。
8. 每方法在成功 needle 上聚合 metrics。
9. 计算与固定 `bm25` baseline 的 aggregate delta。
10. 构建 aggregate-only 公共报告，fail-closed forbidden scanner。

### 公共 artifact 身份

- `schema_version` = `c5e_repoqa_method_matrix_smoke.v1`
- `claim_level` = `repoqa_retrieval_method_matrix_smoke_only`
- `status`：`repoqa_method_matrix_smoke_pass` | `partial` |
  `unavailable_with_reason` | `fail_forbidden_scan` |
  `fail_schema_contract`
- `mode` = `repoqa_bounded_method_matrix_smoke`；`phase` = `C5-E`
- `benchmark` = `repoqa`；`dataset_release` = `repoqa-2024-06-23`
- `baseline_method` = `bm25`；`baseline_is_policy_candidate` = `false`
- Safe true 标志：`repoqa_method_matrix_smoke_performed`、
  `asset_downloaded_transiently`、`repoqa_needles_parsed_in_memory`、
  `repositories_materialized_transiently`、`openlocus_retrieval_executed`、
  `score_py_metrics_computed`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- 无声明 / 无运行时变更标志（全为 false）：见 claim 边界。
- `method_results`：记录列表（**非**以方法名为 key 的 dict），包含 `method`、
  `status`、`needles_evaluated`、`needles_successful`、`needles_failed`、
  `metrics`（allowlisted）、`failure_category_counts`、
  `aggregate_runtime_seconds`。
- `smoke_metric_deltas_vs_baseline`：固定记录，包含 `baseline_method=bm25`、
  `method`、`metric`（allowlisted）、`delta`。
- License 字段固定：`dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。

### Aggregate metrics

每方法 allowlisted metric 名称：`file_recall@10`、`mrr`、`span_f0.5@10`、
`success_rate`。

### 不可用模式

如果网络 smoke 无法完成，artifact 记录真实的 `unavailable_with_reason`，
带真实的 `failure_reason_category`。绝不写入 stale/fake pass。`method_results`
是每方法记录的列表，每个带 `status=unavailable_with_reason`、`metrics={}`、
零 needle 计数；`smoke_metric_deltas_vs_baseline=[]`。

## 隐私 / license 边界

Release asset 下载到内存字节（临时；**绝不**写入工作区或提交）。原始 repo
记录、repo 名称/URL、commit SHA、entrypoint 路径、topics、content、
dependency、needle 名称/描述/路径/start/end lines、生成的 task/label/run
JSONL、evidence 行、克隆仓库与 stdout/stderr 仅保留在 `/tmp` 或内存中，
**绝不**提交或上传。

RepoQA 数据集 license 未知
（`unknown_dataset_license`）；行级再分发被禁用，派生行级发布被禁用。
Aggregate metrics 发布允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 通过，无需 GitHub/网络。
- 真实 smoke 需要公共网络访问 GitHub（asset 下载 + repo 克隆）。CI 是一个
  单独的显式 `workflow_dispatch` job，带
  `enable_external_benchmark_network=true`。它**不**默认在 PR/push 上运行，
  不使用 provider secrets/vars，不使用 provider model env，仅上传 aggregate 报告。
- 如果 `enable_external_benchmark_network` 为 false，workflow 是一个 no-op，
  显示明确消息并 exit 0。
- Fail-closed 如 C5-C：network-enabled CI 不可在 unavailable/无 needle 时
  通过；要求 `status` 在（`repoqa_method_matrix_smoke_pass`，`partial`）、
  `needles_seen > 0`、`methods_successful > 0`、
  `forbidden_scan.status=pass`。

## Forbidden scanner（公共，fail-closed）

复用 C5-D forbidden scanner 原语 + C5-E 专属检查：拒绝 `method_results` 为
以方法名为 key 的 dict；拒绝推荐/策略字段（`winner`、`best_method`、
`recommended_default` 等）出现在任意位置；拒绝 RepoQA 专属 forbidden key
（repo、commit_sha、entrypoint_path、topic、content、dependency、needles、
needle、needle_name、needle_path、needle_description、start_line、end_line、
start_byte、end_byte、global_*、code_ratio、path、description 等）出现在任意
位置；拒绝值模式（URL、hex digest、commit SHA、repo slug、/tmp 路径等）。

## Self-tests

`--self-test` 运行 228 个确定性检查，覆盖 20 组（无网络；合成数据）。

## 验证

```text
python3 -m py_compile eval/c5e_repoqa_method_matrix_smoke.py  => PASS
python3 eval/c5e_repoqa_method_matrix_smoke.py --self-test  => PASS (228/228 checks)
python3 eval/c5e_repoqa_method_matrix_smoke.py \
  --needle-limit 5 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5e_repoqa_method_matrix_smoke/\
c5e_repoqa_method_matrix_smoke_report.json  => PASS
  (status: repoqa_method_matrix_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: repoqa_bounded_method_matrix_smoke, phase: C5-E,
   methods: [bm25, regex, symbol], methods_successful: 3, methods_failed: 0,
   needles_seen: 5, network_calls: 1, provider_calls: 0,
   repoqa_method_matrix_smoke_performed: true,
   asset_downloaded_transiently: true,
   repoqa_needles_parsed_in_memory: true,
   repositories_materialized_transiently: true,
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

手动 CI run `27907731742`（`c5-repoqa-method-matrix-smoke`，`enable_external_benchmark_network=true`，`needle_limit=5`，`methods=bm25,regex,symbol`，`language_filter=python`）成功完成。已提交 artifact 现在镜像该 sanitized aggregate CI report。workflow validator 是 fail-closed：network-enabled CI 在上传前要求 `repoqa_method_matrix_smoke_pass` 或 `partial`、`needles_seen > 0`、`methods_successful > 0`，且 `forbidden_scan.status=pass`。

```text
python3 eval/c5e_repoqa_method_matrix_smoke.py \
  --needle-limit 5 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5e_repoqa_method_matrix_smoke/\
c5e_repoqa_method_matrix_smoke_report.json
  => status: repoqa_method_matrix_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => needles_seen: 5, methods_successful: 3, methods_failed: 0
  => network_calls: 1, provider_calls: 0
  => repoqa_method_matrix_smoke_performed: true
  => method_results:
     bm25: file_recall@10=0.6, mrr=0.46, span_f0.5@10=0.041634, success_rate=1.0, runtime=9.416s
     regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, runtime=6.969s
     symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0, runtime=11.436s
  => smoke_metric_deltas_vs_baseline: 8 records (regex×4 + symbol×4)
```

## 注意事项

- C5-E 是公共 aggregate-only RepoQA 检索方法矩阵 smoke artifact。它是
  eval/diagnostic only。它**不**改变 runtime、retriever、pack、backend 或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是** benchmark 结果、
  **不是**leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**
  默认变更、**不是**runtime-clean 通用算法声称、**不是**OOD 时间泛化声称、
  **不是**QuIVer systems 声称，也**不是**下游 agent 价值声称。
- C5-E **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。
- C5-E **不**运行 provider 调用，**不**运行远程 provider 调用。
- C5-E 使用**有界 RepoQA Python needle subset**（每方法默认 5 needle；硬
  上限 10）。这是 smoke，**不是**严格的 benchmark。
- C5-E **不**静默从 Python 回退到所有语言。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。
