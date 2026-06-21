# C5-D RepoQA BM25 检索性能 Smoke

日期：2026-06-21（C5-D RepoQA 有界检索性能 smoke，基于 EvalPlus RepoQA/SNF
release asset `repoqa-2024-06-23.json.gz`）

C5-D 是 OpenLocus 研究轨中**第一个 RepoQA 形态的检索性能 smoke**。它从
`evalplus/repoqa_release` 下载 EvalPlus RepoQA release asset
`repoqa-2024-06-23.json.gz` 到**仅**`/tmp`，在内存中解压，解析有界的
Python needle subset，在临时 `/tmp` 目录下检出引用仓库到其 `commit_sha`，
运行 OpenLocus `bm25` 检索（无 provider/model 调用），通过现有
`eval/score.py` 逻辑对 needle path/line ranges 打分，并提交**仅一个 aggregate
公共报告**。

C5-D 明确**不是** benchmark 结果，**不是**leaderboard 条目，**不是**性能
声称，**不是**promotion，**不是**默认/策略变更，也**不是**
runtime/retriever/pack/backend/EvidenceCore 语义变更。它**不**输出 `winner`、
`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。

> **重要 claim 边界。** C5-D 输出 `claim_level =
> repoqa_retrieval_performance_smoke_only`。它**不**声称外部 benchmark 结果、
> **不**声称 leaderboard 条目、**不**声称性能、**不**promotion、**不**默认
> 变更、**不**runtime/retriever/pack/backend 变更、**不**EvidenceCore 语义
> 变更，也**不**下游 agent 价值声称。所有 no-claim / no-runtime-change 标志
> 均为 false：`external_benchmark_performance_claimed=false`、
> `leaderboard_entry_claimed=false`、
> `downstream_agent_value_proven=false`、`promotion_ready=false`、
> `default_should_change=false`、`runtime_behavior_changed=false`、
> `retriever_changed=false`、`pack_builder_changed=false`、
> `backend_changed=false`、`default_policy_changed=false`、
> `evidencecore_semantics_changed=false`、`provider_calls_made=false`、
> `remote_provider_calls_made=false`。

## 目标

运行第一个真实 RepoQA 检索性能 smoke，而不创建另一个仅就绪阶段。使用已知
的 EvalPlus RepoQA release asset，在内存中解析一个小的有界 Python needle
集，临时克隆引用仓库，运行 OpenLocus `bm25`，用 `eval/score.py` 对 needle
path/line ranges 打分，并仅发布 aggregate metrics。

### 为何 RepoQA，而非 SWE-Explore

- SWE-Explore C4.3 row-map smoke 在预览行中未找到可用的 line-budget/检索
  label 形状：无行级 labels，无文件映射，无行范围。
- SWE-Explore 在观察到的预览形状中也缺少自然的 query 和公共 clone URL，且
  其 license 边界更严格。
- RepoQA 有已知的 release asset 和自然的检索结构：
  `needle.description` 是 query，`needle.path` + start/end lines 是 gold
  target。

## C5-A -> C5-B -> C5-C -> C5-D 关系

```text
C5-A ContextBench verified retrieval performance smoke
  (single-method; bm25 default; bounded 5-row ContextBench verified
   subset; transient /tmp clone + retrieval + score; aggregate-only
   public artifact; no provider calls)
-> C5-B ContextBench verified retrieval method matrix smoke
   (multi-method matrix; default bm25,regex,symbol; 5-row per method;
    fixed baseline_method=bm25; per-method aggregate records;
    aggregate-only deltas vs bm25; aggregate-only public artifact;
    no provider calls; no winner/best_method/recommended_default)
-> C5-C ContextBench verified retrieval method matrix scale smoke
   (multi-method matrix; bm25,regex,symbol only; bounded 20-row per
    method; per-method aggregate records with optional
    aggregate_runtime_seconds; input_summary block; aggregate-only
    public artifact; no provider calls; no winner/best_method/
    recommended_default; status pass enum
    contextbench_method_matrix_scale_smoke_pass)
-> C5-D RepoQA BM25 retrieval performance smoke
   (single-method bm25 only; bounded 5-needle RepoQA Python subset;
    transient /tmp asset download + clone + retrieval + score;
    aggregate-only public artifact; no provider calls; no
    winner/best_method/recommended_default; status pass enum
    repoqa_retrieval_smoke_pass)
```

C5-D **不是** C5。完整的 C5 外部-benchmark-评估阶段仍然是一个有界的规划/
可行性阶段，需要严格的 benchmark 设计、更大的样本量、多种方法与统计分析。
C5-D 仅通过在有界 RepoQA Python needle subset 上运行真实 OpenLocus 检索 +
打分管线，产出第一个经验性 RepoQA 形态的检索 smoke。

## 实现

### Evaluator

`eval/c5d_repoqa_bm25_retrieval_smoke.py` 提供 argparse CLI：

- `--self-test` —— 无网络合成 self-test（219 组断言）。
- `--needle-limit` —— 评估的 RepoQA Python needle 数；默认 5，硬上限 10。
- `--language-filter` —— 语言过滤类别；默认 `python`；仅允许 `python`
  （C5-D **不**静默回退到所有语言）。
- `--method` —— OpenLocus 检索方法；默认 `bm25`；仅允许 `bm25`。
- `--openlocus` —— 可选的 OpenLocus 二进制路径（默认
  `target/release/openlocus`，然后 `target/debug/openlocus` 回退；解析为
  绝对路径，因为 `run_retrieval.py` 使用 `--cwd <repo_root>` 运行）。
- `--out` —— 输出 artifact JSON 路径；默认
  `artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`。

未知/私有的参数会被拒绝，并显示固定的 `invalid arguments` 消息，不回显
私有路径或 basename（`SafeArgumentParser` 模式）。

### Runtime 流程

1. Self-test 必须在任何 artifact 写入之前通过
   （`_refuse_on_self_test_failure`）。
2. 将 OpenLocus 二进制解析为绝对路径（先 release 后 debug 回退）。若缺失，
   产出真实的 `unavailable_repo_clone_failed` 报告。
3. 下载 `repoqa-2024-06-23.json.gz` release asset 到内存字节（临时；**绝不**
   写入工作区或提交）。
4. 在内存中解压 + 解析 asset（临时；**绝不**写入工作区或提交）。
5. 在内存中解析 RepoQA needles：按 `language_filter=python` 过滤（仅为
   类别桶；**无**静默全语言回退）；每个 needle 是一个临时内存 dict，包含
   `repo_url`、`commit_sha`、`needle_path`、`needle_start_line`、
   `needle_end_line`、`needle_description`。若零 Python needle 找到，状态为
   `unavailable_no_python_needles`。
6. 对每个 needle（有界至 `needle_limit`）：
   - 将 `needle_description` sanitizer 为检索 query（仅内存中；提取
     `Purpose` 部分的第一句；剥离 markdown 粗体/斜体；限制长度）。
   - 在每行 `TemporaryDirectory` 下，通过
     `git clone --filter=blob:none --no-checkout` 然后 `git checkout`
     克隆 `repo_url` 到 `commit_sha`（有界超时）。
   - 在 `TemporaryDirectory` 下生成临时 task/label JSONL。
   - 通过 `eval/run_retrieval.py` 运行 OpenLocus 检索
     （`--method bm25 --cwd <repo_root>`）。
   - 运行 `eval/score.py` 并解析 aggregate metrics。
7. 在成功 needle 上聚合 metrics（每个 allowlisted 数值 metric 的均值）。
8. 构建 aggregate-only 公共报告，fail-closed forbidden scanner。

### 公共 artifact 身份

提交的 artifact 位于
`artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`，
是公共 aggregate-only smoke artifact。身份/边界字段：

- `schema_version` = `c5d_repoqa_retrieval_performance_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、`phase`
- `benchmark` = `repoqa`
- `dataset_release` = `repoqa-2024-06-23`
- `language_filter` = `python`
- `method` = `bm25`
- `query_mode` = `needle_description`
- `gold_target_mode` = `needle_path_line_range`
- `status`：`repoqa_retrieval_smoke_pass` | `partial` |
  `unavailable_asset_download_failed` |
  `unavailable_no_python_needles` |
  `unavailable_repo_clone_failed` | `fail_forbidden_scan` |
  `fail_schema_contract`
- Safe true 标志（仅当实际为真时为 true）：
  `repoqa_retrieval_smoke_performed`、`asset_downloaded_transiently`、
  `repoqa_needles_parsed_in_memory`、
  `repositories_materialized_transiently`、
  `openlocus_retrieval_executed`、`score_py_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- No-claim / no-runtime-change 标志（全为 false）：
  `external_benchmark_performance_claimed`、
  `leaderboard_entry_claimed`、`downstream_agent_value_proven`、
  `promotion_ready`、`default_should_change`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `provider_calls_made`、`remote_provider_calls_made`。
- License 字段（固定）：
  `dataset_license_status=unknown_dataset_license`、
  `row_level_redistribution_allowed=false`、
  `derived_row_level_publication_allowed=false`、
  `aggregate_metrics_publication=aggregate_only_smoke`。
- `needle_limit_requested`、`needles_seen`、`needles_evaluated`、
  `needles_successful`、`needles_failed`、`network_calls`、
  `provider_calls=0`、`aggregate_runtime_seconds`。
- `aggregate_metrics`：仅 allowlisted metric 名称（`file_recall@10`、
  `mrr`、`span_f0.5@10`、`success_rate`）。
- `failure_category_counts`：仅固定枚举类别。
- `failure_reason_category`（仅在不可用状态下）。
- `framing`：显式 `external_benchmark_performance_claimed=false`、
  `leaderboard_entry_claimed=false`、`promotion_claimed=false` 等。
- `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

### Aggregate metrics

`aggregate_metrics` 块仅包含 allowlisted 的 aggregate metric 名称与数值（来自
`eval/score.py`）。无行级记录、无 needle ID、无 repo 名称、无 commit SHA、
无路径、无 span、无 snippet、无 content_sha。Allowlisted metric 名称：

- `file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。

`failure_category_counts` 块仅包含固定枚举类别标签（永不行级值）：

- `asset_download_failed`、`asset_decompress_failed`、
  `asset_parse_failed`、`no_python_needles`、
  `needle_parse_failed`、`language_filter_excluded`、
  `repo_clone_failed`、`repo_checkout_failed`、
  `task_jsonl_write_failed`、`label_jsonl_write_failed`、
  `retrieval_failed`、`score_failed`、`needle_limit_capped`、
  `scanner_self_test_failed`、`forbidden_leak_blocked`、
  `unexpected_exception`。

### 不可用状态

如果网络 smoke 无法完成（asset 下载失败、解压失败、解析失败、无 Python
needle、repo 克隆失败、检索失败、打分失败等），artifact 记录真实的
`unavailable_*`，带有真实的 `failure_reason_category` 与对应的
`failure_category_counts` 计数。绝不写入 stale/fake pass。不可用状态为：

- `unavailable_asset_download_failed`：asset 下载或解压或解析失败。
- `unavailable_no_python_needles`：零 Python needle 找到（**无**静默全语言
  回退）。
- `unavailable_repo_clone_failed`：repo 克隆/检出或检索或打分失败。

在不可用模式下，`aggregate_metrics={}`、
`repoqa_retrieval_smoke_performed=false`、
`aggregate_only_public_artifact=true` 与 `diagnostic_only=true` 保持为 true。

## 隐私 / license 边界

公共 artifact 与文档保持 aggregate-only。以下内容**不**持久化于任何公共
artifact 或文档中：

- `repoqa-2024-06-23.json.gz` release asset（下载到 `/tmp` 仅，在内存中
  解压，**绝不**提交或上传）；
- 原始 repo 记录、repo 名称/URL、commit SHA、entrypoint 路径、topics、
  content、dependency、functions；
- needle 名称、描述、路径、start/end lines、start/end bytes、global_* 字段、
  code_ratio；
- 生成的 task/label/run JSONL（仅临时 `/tmp`）；
- OpenLocus evidence 行、snippet、路径、行范围、content_sha；
- 克隆的仓库/源文件（仅临时 `/tmp`）；
- 原始命令 stdout/stderr 或 stack trace；
- 每 needle metrics 或每 needle 失败记录；
- needle ID / 行 ID / 行级值 hash。

公共 artifact 仅记录：来自 `eval/score.py` 的 aggregate metric 均值/比率/
计数（allowlisted）、固定 failure-category 计数、固定配置标签（`benchmark`、
`dataset_release`、`language_filter`、`method`、`query_mode`、
`gold_target_mode`）、needle 计数、网络/provider 调用计数，以及确定性的
`generated_by` 路径。

RepoQA 数据集 license 未知
（`unknown_dataset_license`）；行级再分发被禁用
（`row_level_redistribution_allowed=false`），派生行级发布被禁用
（`derived_row_level_publication_allowed=false`）。Aggregate metrics 发布
允许作为 aggregate-only smoke
（`aggregate_metrics_publication=aggregate_only_smoke`）。

## 网络 / CI 策略

- 默认无网络 self-test 通过，无需 GitHub/网络。
- 真实 smoke 需要公共网络访问 GitHub（asset 下载 + repo 克隆）。CI 是一个
  单独的显式 `workflow_dispatch` job，带
  `enable_external_benchmark_network=true` 输入。它**不**默认在 PR/push 上
  运行，不使用 provider secrets/vars，不使用 provider model env，仅上传
  aggregate 临时报告。
- 如果 `enable_external_benchmark_network` 为 false，workflow 是一个 no-op，
  显示明确消息并 exit 0（self-test + py_compile 仍会运行；no-op 模式下不
  产出 aggregate 报告）。
- Workflow 在 smoke 之后校验报告的 claim 边界标志（fail-closed 如 C5-C：
  network-enabled CI 不可在 unavailable/无 needle 时通过）：要求 status
  `repoqa_retrieval_smoke_pass` 或 `partial`、`needles_seen > 0`、
  `needles_successful > 0`、`forbidden_scan.status=pass`。

## Forbidden scanner（公共，fail-closed）

严格的 forbidden-output scanner 在写入公共 JSON 前 fail-closed 运行。复用
C5-A forbidden scanner 原语进行原始 key/value 泄露检测，并 ADD C5-D 专属
检查：

- 拒绝 RepoQA 专属 forbidden dict key（`repo`、`commit_sha`、
  `entrypoint_path`、`topic`、`content`、`dependency`、`needles`、
  `needle`、`needle_name`、`needle_path`、`needle_description`、
  `needle_id`、`name`、`start_line`、`end_line`、`start_byte`、
  `end_byte`、`global_start_line`、`global_end_line`、
  `global_start_byte`、`global_end_byte`、`code_ratio`、`path`、
  `description`、`row`、`repo_name`、`repo_slug`、`repo_url`、
  `base_commit`、`instance_id`、`task_id`、`query`、`query_text`、
  `problem_statement`、`gold`、`gold_path`、`gold_span`、`gold_snippet`、
  `gold_paths`、`gold_lines`、`gold_context`、`snippet`、`snippets`、
  `content_sha`、`stdout`、`stderr`、`stdout_text`、`stderr_text`、
  `evidence`、`evidence_row`、`evidence_rows`、`retrieved_path`、
  `retrieved_paths`、`retrieved_snippet`、`cloned_repo_path`、
  `cloned_repo`、`per_row_metrics`、`row_metrics`、
  `per_needle_metrics`、`needle_metrics`、`patch`、`diff` 等）出现在任意位置。
- 拒绝推荐/策略字段出现在任意位置：`winner`、`best_method`、
  `recommended_default`、`recommended_method`、`preferred_method`、
  `default_method`、`policy_decision`、`decision`、`ranking`、`rank`。
- 拒绝值模式：任意 URL（无 URL allowlist —— repo URL **绝不**泄露）、
  32+ 字符 hex digest、40 字符 commit SHA、形如 `psf/black` 的 repo slug、
  secret-like 字符串、带文件扩展名的 path-like 字符串、`/tmp/` 工作区
  路径值、`task_N`/`needle_N` 任务标识符值、patch/diff 标记（`---`、
  `+++`、`@@`）、stack trace、多行字符串、原始 JSON 片段、原始行范围
  `585-639`，以及 self-test sentinel。

`failure_category_counts` 与 `aggregate_metrics` 容器是 schema-key 容器，
其 CHILD KEY 是固定类别标签或 allowlisted metric 名称（**非**行级值）；
forbidden_key 检查对这些子键放宽，但其下的值仍会被扫描（仅允许
int/float/短字符串）。

Scanner 仅对最终公共 aggregate artifact 运行。内部 task/label/run JSONL
（包含路径/span/query/gold）仅保留在内存/临时 `/tmp` 下，永不针对公共
合约扫描，永不提交。

## Self-tests

`--self-test` 运行 219 个确定性检查，覆盖 23 组（无网络；合成 gzip fixture
+ 合成 score 数据）：

1. Artifact 身份字段（schema、claim、status、mode、phase、generated_by、
   benchmark、dataset_release、query_mode、gold_target_mode；self-test 通过时
   状态 pass）。
2. Safe true 标志存在 + 正确值（8 个标志）。
3. No-claim / no-runtime-change false 标志（13 个标志）。
4. License 字段（4 个字段）。
5. Needle limit 硬上限 10（默认 5；上限 10；5 透传；拒绝 0）。
6. 方法 allowlist（仅 bm25）。
7. 语言过滤（仅 python，无静默全语言回退：对无 python needle 的 asset 用
   python 过滤返回 `unavailable_no_python_needles`，**非**回退到所有语言）。
8. gzip JSON fixture 内存解析（通过；有 python key）。
9. Needle 提取校验字段（repo_url、commit_sha、needle_path、行范围、
   description）。
10. 畸形 needle 映射到固定失败类别（无 repo、无 commit_sha、无 path、倒置
    范围、无 description）。
11. Needle 上限（15 needle 上限到 10；低于可用无 cap）。
12. Query sanitizer（提取 Purpose；剥离 markdown 粗体；上限 300；无 Purpose
    时回退）。
13. Score metric allowlist（排除 row_id/path/content_sha/avg_latency_ms；
    包含 file_recall/mrr；allowlist 是 C5-A 子集）。
14. 合成 score 聚合（有 file_recall/success_rate；success_rate 重计算；无
    needle 时为空）。
15. Failure category counts 固定枚举（枚举内 key 通过；非枚举 key 由 builder
    拒绝）。
16. 不可用状态（asset_download_failed、no_python_needles、
    repo_clone_failed；每个有正确状态枚举、无 smoke 标志、无 metrics、无 perf
    claim、scan pass）。
17. Scanner 拒绝 forbidden 内容（60+ forbidden key，包含 RepoQA 专属
    repo/commit_sha/entrypoint_path/topic/content/dependency/needles/
    needle/needle_name/needle_path/needle_description/start_line/
    end_line/start_byte/end_byte/global_*/code_ratio/path/description；
    10 个推荐字段；repo URL 值；repo slug 值；commit SHA 值；file path
    值；line range 值；hex digest 值；/tmp path 值；multiline 值；raw JSON
    fragment）。
18. Scanner 允许安全值（benchmark、dataset_release、method、
    language_filter、query_mode、gold_target_mode、network_mode、
    aggregate_metrics、failure_category_count）。
19. Fail-closed 生成（干净报告不 raise；泄露 repo raise；best_method raise；
    winner raise；recommended_default raise；commit_sha raise；
    needle_description raise；self-test 失败拒绝 artifact 生成）。
20. 公共 artifact 自扫描干净（skeleton + 不可用）。
21. CLI 参数面（`--self-test`、`--needle-limit`、`--language-filter`、
    `--method`、`--openlocus`、`--out`）。
22. Aggregate runtime seconds 存在（pass 报告有数值；不可用为 null）。
23. 无 winner/best_method/recommended_default 出现（10 个字段）。

## 验证

```text
python3 -m py_compile eval/c5d_repoqa_bm25_retrieval_smoke.py  => PASS
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py --self-test  => PASS (219/219 checks)
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py \
  --needle-limit 5 --language-filter python --method bm25 \
  --out artifacts/c5d_repoqa_bm25_retrieval_smoke/\
c5d_repoqa_bm25_retrieval_smoke_report.json  => PASS
  (status: repoqa_retrieval_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: repoqa_bounded_bm25_retrieval_smoke, phase: C5-D,
   method: bm25, language_filter: python,
   query_mode: needle_description, gold_target_mode: needle_path_line_range,
   needles_seen: 5, needles_evaluated: 5, needles_successful: 5, needles_failed: 0,
   network_calls: 1, provider_calls: 0,
   repoqa_retrieval_smoke_performed: true,
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
python3 eval/c5d_repoqa_bm25_retrieval_smoke.py \
  --needle-limit 5 --language-filter python --method bm25 \
  --out artifacts/c5d_repoqa_bm25_retrieval_smoke/\
c5d_repoqa_bm25_retrieval_smoke_report.json
  => status: repoqa_retrieval_smoke_pass,
     forbidden_scan: pass, self_test_passed: true
  => needles_seen: 5, needles_evaluated: 5, needles_successful: 5, needles_failed: 0
  => network_calls: 1, provider_calls: 0
  => repoqa_retrieval_smoke_performed: true
  => asset_downloaded_transiently: true
  => repoqa_needles_parsed_in_memory: true
  => repositories_materialized_transiently: true
  => openlocus_retrieval_executed: true
  => score_py_metrics_computed: true
  => aggregate_metrics: file_recall@10=0.6, mrr=0.46,
     span_f0.5@10=0.041634, success_rate=1.0
  => aggregate_runtime_seconds: 4.244
```

`repoqa-2024-06-23.json.gz` release asset 下载到内存字节（临时；**绝不**写入
工作区），5 个 RepoQA Python needle 在内存中解析，引用仓库在临时 `/tmp`
目录下克隆到其 `commit_sha`，对每个仓库运行 OpenLocus `bm25` 检索，
`eval/score.py` 产出 aggregate 检索 metrics。Aggregate metric 均值在 5 个
成功 needle 上计算，并写入提交的 artifact。无原始 repo 记录、repo 名称/
URL、commit SHA、entrypoint 路径、topics、content、dependency、needle 名称/
描述/路径/start/end lines、生成的 task/label/run JSONL、evidence 行、克隆
仓库或 stdout/stderr 被提交或上传。

如果未来环境中网络 smoke 无法完成（asset 下载失败、解压失败、解析失败、无
Python needle、repo 克隆失败、检索失败、打分失败），artifact 记录真实的
`unavailable_*`，带有真实的 `failure_reason_category` 与对应的
`failure_category_counts` 计数。绝不写入 stale/fake pass。

## 注意事项

- C5-D 是公共 aggregate-only RepoQA BM25 检索性能 smoke artifact。它是
  eval/diagnostic only。它**不**改变 runtime、retriever、pack、backend 或
  默认策略；它**不**改变 EvidenceCore 语义。它**不是** benchmark 结果、
  **不是**leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**
  默认变更、**不是**runtime-clean 通用算法声称、**不是**OOD 时间泛化声称、
  **不是**QuIVer systems 声称，也**不是**下游 agent 价值声称。
- C5-D **不**输出 `winner`、`best_method`、`recommended_default` 或任何
  暗示策略/默认决策的字段。
- C5-D **不**运行 provider 调用，**不**运行远程 provider 调用。唯一的网络
  调用是对公共 GitHub（下载 `repoqa-2024-06-23.json.gz` release asset 与在
  临时 `/tmp` 目录下克隆引用仓库到其 `commit_sha`）。`provider_calls=0`、
  `provider_calls_made=false`、`remote_provider_calls_made=false`。
- C5-D 使用**有界 RepoQA Python needle subset**（默认 5 needle；硬上限
  10）。这是 smoke，**不是**严格的 benchmark 评估。Aggregate metrics 是有界
  样本上的点估计，**不应**被解读为 benchmark 结果、leaderboard 条目或性能
  声称。
- C5-D 下载 `repoqa-2024-06-23.json.gz` release asset 到内存字节（临时；
  **绝不**写入工作区或提交）并在内存中解压。克隆的仓库、生成的
  task/label/run JSONL、evidence 行与 stdout/stderr 仅保留在 `/tmp` 下，
  **绝不**提交或上传。提交的 artifact 仅包含 aggregate 计数/比率/均值。
- C5-D **不**静默从 Python 回退到所有语言。若
  `language_filter=python` 且零 Python needle 找到，artifact 为真实的
  `unavailable_no_python_needles`。
- C5-D **不**声称外部 benchmark 性能。Aggregate metrics 是 smoke 级别
  的诊断，**不是**benchmark 结果。
  `external_benchmark_performance_claimed=false`。
- C5-D **不**证明下游 agent 价值。检索 smoke 不演练任何下游 agent。
  `downstream_agent_value_proven=false`。
- RepoQA 数据集 license 未知
  （`unknown_dataset_license`）；行级再分发被禁用
  （`row_level_redistribution_allowed=false`），派生行级发布被禁用
  （`derived_row_level_publication_allowed=false`）。Aggregate metrics 发布
  允许作为 aggregate-only smoke
  （`aggregate_metrics_publication=aggregate_only_smoke`）。
- 所有 no-claim / no-runtime-change 标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true。
  未修改任何 runtime/retriever/pack/model/backend/default-policy 文件；
  无 promotion/default/runtime 声明变更。

## 下一步

- C5-D 是第一个 RepoQA 形态的检索性能 smoke。完整的 C5 外部-benchmark-
  评估阶段仍然是一个有界的规划/可行性阶段，需要严格的 benchmark 设计、更
  大的样本量、多种方法与统计分析。
- 无 promotion、无默认变更、无 EvidenceCore 语义变更、无 runtime-clean
  通用算法声称、无下游 agent 价值声称、无 OOD 时间泛化声称，也无 QuIVer
  systems 声称来自 C5-D。
