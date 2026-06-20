# C4 外部 Benchmark Adapter —— Schema + Row-Mapping 就绪 v1

日期：2026-06-20（C4.1 schema 就绪）；2026-06-20（C4.2 ContextBench
verified subset row-mapping smoke）；2026-06-20（C4.3 SWE-Explore
row-mapping / line-budget aggregate smoke）；2026-06-20（C4.4 CORE-Bench
source readiness / no-go）；2026-06-20（C4.5 RepoQA
source/schema-contract readiness，adapter deferred）

C4.1 是 **外部 benchmark adapter / schema 就绪** 阶段，C4.2 是
**ContextBench verified subset row-mapping smoke** 阶段。两者都**不是**外部
benchmark 性能评估、**不是** benchmark 结果、**不是**下游 agent 价值证明，也
**不是** promotion 或默认策略变更。C4.1 产出一个 evaluator
（`eval/c4_external_benchmark_adapters.py`）与一个 canonical aggregate-only
公共 artifact
（`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`），
仅记录 adapter/schema 就绪状态。C4.2 新增一个针对 ContextBench verified
subset 的有界真实 row-mapping smoke，并输出单独的 aggregate-only artifact
（`artifacts/c4_external_benchmark_adapters/c4_contextbench_verified_row_mapping_report.json`）。
两个阶段均未持久化行级 benchmark 内容。

> **重要 claim 边界。** C4.1 输出 `claim_level =
> adapter_schema_readiness_only`。它**不**声称性能、promotion、默认策略变更、
> 外部 benchmark 结果、下游 agent 价值、OOD 时间泛化或 QuIVer systems 支持。
> 所有 no-claim 标志均为 false：`promotion_ready=false`、
> `default_should_change=false`、`evidencecore_semantics_changed=false`、
> `runtime_clean_general_algorithm_claimed=false`、
> `downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
> `quiver_systems_supported=false`。合成 self-test 行不提供任何经验支持。

## 目标

为两个外部 benchmark 提供一个真实（非 skeleton-only）的 adapter/schema 就绪
层，使未来基于 benchmark 的评估可以在不削弱公共 artifact 契约的前提下接入：

- **ContextBench** —— HuggingFace 数据集 `Contextbench/ContextBench`。
- **SWE-Explore** —— HuggingFace 数据集 `SWE-Explore-Bench/SWE-Explore-Bench`。

该 evaluator 实现：(1) 每个 benchmark 的内置已知 source/schema 元数据；(2) 合成
内存行 adapter，将 `public_task`（aggregate-safe 元数据）与 `private_label`
（行级 payload，永不序列化）分离；(3) 仅用于合成 self-test / 私有内存校验的
line range 归一化；(4) 针对所有公共 JSON 输出的严格 fail-closed forbidden
scanner；(5) 仅通过 stdlib `urllib`（无新依赖）的有界 HF datasets-server
schema smoke；(6) 排除时间戳、网络输出、原始行与本地路径的确定性 spec hash。

## 实现

### Evaluator

`eval/c4_external_benchmark_adapters.py` 提供 argparse CLI：

- `--self-test` —— 无网络合成 self-test（9 组断言）。
- `--benchmark {contextbench,swe_explore,all}` —— 默认 `all`。
- `--schema-smoke` —— 有界 HF datasets-server schema smoke；要求显式 `--out`
  以避免覆盖 canonical aggregate 报告。
- `--limit` —— 用 `/first-rows` 探测的 `(config, split)` 对的最大数量；默认
  3，硬上限 10。
- `--out` —— 默认
  `artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`。

不带 `--self-test` 且不带 `--schema-smoke` 运行时，从内置已知 source/schema
元数据加合成 self-test 状态生成 canonical aggregate 报告，无网络调用。

### Canonical artifact

`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`
（schema `c4_external_benchmark_adapters.v1`）是 canonical aggregate-only 公共
artifact。它记录 `schema_version`、`generated_by`、`claim_level`、所有
no-claim 标志为 false、`aggregate_only_public_artifact=true`、
`not_evidence=true`、`candidate_not_fact=true`、确定性 `spec_hash`、
`benchmarks.contextbench` 与 `benchmarks.swe_explore` 块、`safety_invariants`
（全 false）、`framing` 以及 `forbidden_scan.status == pass`。JSON 写入使用
`mkdir parents` + `json.dumps(..., indent=2, sort_keys=True) + "\n"`。

### Benchmark 规格（内置已知 schema 元数据）

**ContextBench**（`Contextbench/ContextBench`）：

- 已知 configs/splits：`default/train` 1136、`contextbench_verified/train` 500。
- 仅 schema 的字段名（关于 schema 的观察，非行级值）：`instance_id`、
  `original_inst_id`、`repo`、`repo_url`、`language`、`base_commit`、
  `gold_context`、`patch`、`test_patch`、`problem_statement`、`f2p`、`p2p`、
  `source`。
- 检测到的私有字段类别：`repo`、`repo_url`、`base_commit`、`gold_context`、
  `patch`、`test_patch`、`problem_statement`、`f2p`、`p2p`。
- License 状态：`unknown_dataset_license`。即使代码仓库为 Apache-2.0（HF 数据集
  card/API 未声明 dataset-level license），行级再分发也被禁用。

**SWE-Explore**（`SWE-Explore-Bench/SWE-Explore-Bench`）：

- 已知 config/split：`default/train` 848。
- 仅 schema 的字段名：`instance_id`、`repo_path`、`repo_dir`、`ground_truth`、
  `read_step_info`、`meta`、`dataset`。
- 检测到的私有字段类别：`repo_path`、`repo_dir`、`ground_truth`、
  `ground_truth.patch`、`ground_truth.test_patch`、`ground_truth.modified_files`、
  `ground_truth.core_files`、`ground_truth.line_ranges`、`read_step_info`、
  `read_step_info.file_maps`、`read_step_info.line_ranges`。
- License 状态：`cc-by-nc-nd-4.0`。即使代码仓库为 MIT（HF 数据集 license 为
  `cc-by-nc-nd-4.0`），行级再分发与派生 label 发布也被禁用。

### 合成内存行 adapter

`adapt_contextbench_row` 与 `adapt_swe_explore_row` 将每个合成行分离为一个
`public_task` 对象（aggregate-safe 元数据：存在性布尔、字段计数、仅类别桶 ——
从不是原始值）与一个 `private_label` 对象（全部行级 payload，仅在内存中为
self-test 与私有内存校验保留）。public task 从不携带行级
repo/commit/patch/test/problem/gold 值。两者都不会以行级值序列化到公共
artifact；只有跨多行的聚合计数/布尔可进入公共 artifact。

### Line range 归一化

`normalize_line_range` 接受 list/tuple/dict/`"S-E"`/`"S:E"` 形式，并拒绝
`start > end`、`start < 1`、非整数值与布尔值。Line range 归一化仅用于合成
self-test / 私有内存校验；对真实 benchmark 行，任何 path/span/line range 均为
私有/本地，永不写入公共 artifact、docs 或 schema smoke 输出。

### Forbidden-output scanner

`_scan_forbidden` 是针对公共 JSON 输出的严格递归 scanner。它禁止任何位置作为
dict key 出现的敏感 key 名（如 `instance_id`、`repo`、`patch`、
`ground_truth`、`content_sha`、`prompt`、`response`、`snippet`、
`gold_spans`、`private_labels`、`api_key`、`base_url`），并禁止
URL/hex-digest/secret-like/path-like/multiline/long-string 值。仅 schema 的
字段名列表允许出现在显式容器（`field_names_schema_only`、
`private_field_categories_detected`）下，因为它们是关于 schema 的观察，而非行
级数据。已知安全的 provenance 值路径（`spec_hash`、`generated_by`、
`dataset_id`、`schema_version`、`claim_level`）仅在 hex_digest/path_like 值检查
中被 allowlist。该 scanner 为 fail-closed：若公共报告会泄漏，则生成与 self-test
失败。artifact 仅记录 `forbidden_scan: {status: "pass"}` 加 category/path 计数
—— 从不记录泄漏值。

### 确定性 spec hash

`compute_spec_hash` 返回 canonical spec JSON 的 SHA-256。该 spec 排除时间戳、
网络输出、原始行与本地路径；仅包含 dataset_id、configs、schema 字段名、私有类
别、license gating 与字段类型摘要。该 hash 跨运行稳定：
`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`。

## 数据边界

公共 artifact 与 docs 保持 aggregate/schema-only。以下内容未被持久化到任何公共
artifact 或 doc：

- 原始 benchmark 行与 gold labels；
- 行级 task instance 值、instance ID、original_inst_id；
- repo URL、commit、repo 路径、repo 目录；
- 文件路径、span、line range、snippet；
- issue/problem statement、patch/test、prompt/response；
- provider payload、content_sha、原始 HF payload、响应体。

对每个 benchmark，公共 artifact 仅记录：dataset_id、config/split 行计数、仅
schema 字段名列表、字段类型摘要、检测到的私有字段类别（以点分 schema-only
类别名形式，非值）、license gating 字段
（`row_level_redistribution_allowed`、`derived_label_publication_allowed`）以及四
个状态（`discovery_status`、`schema_smoke_status`、
`adapter_self_test_status`、`public_release_status`）。

## Schema smoke 结果

有界 HF datasets-server schema smoke 仅使用 stdlib `urllib`（无新依赖），具有
显式有界超时，并以 `/splits` 作为 `/first-rows` 尝试的 source of truth。对
`/first-rows`，仅解析 features/schema 与行计数/截断布尔；原始行仅保留在本地，
永不返回或写入。网络/HF 失败时，smoke 产生状态 `unavailable` 或 `partial`，
并附带 sanitized reason category/status code —— 不存储原始响应体。

实际 schema smoke 命令已运行并通过 forbidden scan：

```text
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json
  => forbidden_scan: pass, new_network_calls: 4
  => first_rows_status: pass, row_level_data_returned: false

python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json
  => forbidden_scan: pass, new_network_calls: 3
  => first_rows_status: pass, row_level_data_returned: false
```

`/tmp` smoke 输出遵循与已提交 artifact 相同的 aggregate-only 边界。网络
schema smoke 失败也是可接受的，只要产生 sanitized 的 `partial`/`unavailable`
输出且 self-test 通过；在本次运行中，smoke 端点可达，并从公共 HF
datasets-server 元数据返回可解析 schema。

## 验证

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS（15 组）
python3 eval/c4_external_benchmark_adapters.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_external_benchmark_adapter_report.json                     => PASS（forbidden_scan: pass）
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json                       => PASS
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json                        => PASS
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_contextbench_verified_row_mapping_report.json              => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true)
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_swe_explore_row_mapping_report.json                       => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true,
   adapter_assertions_passed: true)
```

Self-test 组（15）：ContextBench adapter 分离、SWE-Explore adapter 分离、line
range 归一化、forbidden scan 拒绝注入、no-claim 标志全为 false、spec hash 确
定性、aggregate-only 报告、forbidden scan 在生成时阻断泄漏、schema smoke 报告
形态、row-map smoke aggregate-only（sentinel 干净）、row-map smoke 无行
unavailable、row-map smoke isolation failure fail-closed、swe row-map smoke
aggregate-only（sentinel 干净）、swe row-map line-budget only-counts、swe
row-map isolation failure fail-closed。

## C4.2 ContextBench verified subset row-mapping smoke

C4.2 新增一个针对 ContextBench verified subset
（`contextbench_verified/train`）的有界**真实 row-mapping smoke**。它通过
`_http_get_json()`（仅 stdlib `urllib`）读取真实 HF datasets-server
`/first-rows` 预览行，并对每个预览行在函数作用域内调用现有
`adapt_contextbench_row(row)` adapter。真实行仅存在于函数作用域/内存；它们被
适配后立即丢弃。公共 artifact 仅记录 aggregate-only 计数、布尔与固定失败类别
—— 从不记录原始行、样本行、行值、行级 hash、path、span、line range、
snippet、problem statement、patch/test、prompt/response、provider payload、
content_sha 或原始 HF payload。

### CLI

- `--row-map-smoke`（与 `--self-test` 和 `--schema-smoke` 互斥）。
- `--row-limit` 默认 10，硬上限 20。
- `--config` 默认 `contextbench_verified`；row-map smoke 仅支持
  `contextbench_verified`。
- `--split` 默认 `train`。
- `--out` 未显式设置时默认为
  `artifacts/c4_external_benchmark_adapters/c4_contextbench_verified_row_mapping_report.json`
  （从而不会覆盖 C4.1 canonical 报告）。

### Aggregate-only 输出形态

row-map smoke artifact（`c4_contextbench_verified_row_mapping.v1`、
`claim_level=adapter_row_mapping_readiness_only`）记录：

- `mode: contextbench_verified_row_mapping_smoke`、`benchmark: contextbench`、
  `dataset_id`、`config`、`split`、`row_limit_requested`；
- `rows_seen`、`rows_mapped`、`rows_failed`、`truncated_rows_observed`；
- `field_presence_counts`：schema 字段名 -> 非空行计数（字段名是仅 schema 的
  观察用作计数桶 key，从不是行级值）；
- `public_task_presence_counts`：`has_original_inst_id`、`has_f2p`、
  `has_p2p`、`has_repo_locator`、`has_private_label_payload` -> True 计数；
- `private_field_presence_counts`：私有类别名 -> 非空行计数（类别名是仅 schema
  的观察，从不是值）；
- `failure_category_counts`：仅固定类别（`missing_required_field`、
  `wrong_type`、`mapping_error`、`private_field_leak`、`public_artifact_leak`、
  `unexpected_exception`、`no_rows_returned`、`endpoint_unavailable`）；
- `private_label_isolation_verified`、`adapter_assertions_passed`、
  `raw_rows_persisted: false`、`row_level_values_emitted: false`、
  `row_level_hashes_emitted: false`、`raw_response_stored: false`；
- `status: pass|partial|unavailable|fail_forbidden_leak|fail_schema_contract`；
- 所有 no-claim 标志为 false、`aggregate_only_public_artifact=true`、
  `not_evidence=true`、`candidate_not_fact=true`、
  `forbidden_scan.status=pass`。

forbidden scanner 扩展了 `SCHEMA_KEY_CONTAINER_KEYS` allowlist，使计数容器 dict
（`field_presence_counts`、`public_task_presence_counts`、
`private_field_presence_counts`、`failure_category_counts`）可使用仅 schema 字段
名字符串作为计数桶 key。scanner 仍禁止公共输出中任何位置的行级值、path、span、
hash、URL 与 secret。每次写入前运行 fail-closed forbidden scan。

### 真实 row-map smoke 结果（2026-06-20）

```text
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_contextbench_verified_row_mapping_report.json
  => rows_seen: 10, rows_mapped: 10, rows_failed: 0
  => status: pass, forbidden_scan: pass
  => private_label_isolation_verified: true
  => adapter_assertions_passed: true
  => raw_rows_persisted: false, row_level_values_emitted: false,
     row_level_hashes_emitted: false, raw_response_stored: false
```

所有 13 个 schema 字段名在全部 10 行中非空；所有 5 个 public-task presence
布尔在全部 10 行中为 True；所有 12 个私有字段类别在全部 10 行中非空。未持久化
任何行级值、hash、path、span、snippet、problem statement、patch/test、
prompt/response、provider payload、content_sha 或原始 HF payload。

## C4.3 SWE-Explore row-mapping / line-budget aggregate smoke

C4.3 新增一个针对 SWE-Explore（`default/train`）的有界**真实 row-mapping /
line-budget shape readiness smoke**。它通过 `_http_get_json()`（仅 stdlib
`urllib`）读取真实 HF datasets-server `/first-rows` 预览行，并对每个预览行在
函数作用域内调用现有 `adapt_swe_explore_row(row)` adapter。真实行仅存在于函数
作用域/内存；它们被适配后立即丢弃。公共 artifact 仅记录 aggregate-only 计数、
布尔、固定失败类别与 line-budget shape readiness 计数/布尔 —— 从不记录原始行、
样本行、行值、行级 hash、文件路径/文件名、line range/span/region、patch/
test_patch/code snippet、modified/core 文件名、meta 原始内容、label/派生 label、
provider payload、content_sha 或原始 HF payload。

### CLI

- `--row-map-smoke --benchmark swe_explore`（与 `--self-test` 和
  `--schema-smoke` 互斥；row-map smoke 拒绝 `--benchmark all`）。
- `--row-limit` 默认 10，硬上限 20。
- `--config` 对 `--benchmark swe_explore` 默认为 `default`（仅支持 `default`）；
  对 `--benchmark contextbench` 默认为 `contextbench_verified`。
- `--split` 默认 `train`。
- `--out` 对 SWE-Explore 默认为
  `artifacts/c4_external_benchmark_adapters/c4_swe_explore_row_mapping_report.json`
  （对 ContextBench 为 C4.2 路径），从而不会覆盖 C4.1 canonical schema artifact。

### Aggregate-only 输出形态

SWE row-map smoke artifact（`c4_swe_explore_row_mapping.v1`、
`claim_level=adapter_row_mapping_readiness_only`）记录：

- `mode: swe_explore_row_mapping_line_budget_smoke`、
  `benchmark: swe_explore`、`dataset_id`、`config`、`split`、
  `row_limit_requested`；
- `rows_seen`、`rows_mapped`、`rows_failed`、`truncated_rows_observed`；
- `field_names_schema_only`、`field_presence_counts`（仅 SWE schema 字段名；
  字段名是仅 schema 的观察用作计数桶 key，从不是行级值）；
- `public_task_presence_counts`：`has_repo_path`、`has_repo_dir`、
  `has_ground_truth`、`has_read_step_info`、`has_meta` -> True 计数；
- `private_field_presence_counts`：私有类别名 -> 非空行计数，包含嵌套
  `ground_truth_patch`、`ground_truth_test_patch`、
  `ground_truth_modified_files`、`ground_truth_core_files`、
  `ground_truth_line_ranges`、`read_step_info_file_maps`、
  `read_step_info_line_ranges`（类别名是仅 schema 的观察，从不是值）；
- `line_budget_readiness`：仅 aggregate 计数/布尔 ——
  `line_level_labels_present_count`、`region_like_structures_present_count`、
  `file_level_labels_present_count`、`rows_with_file_maps`、
  `rows_with_modified_files`、`rows_with_core_files`、
  `budget_evaluation_shape_supported`、`line_budget_values_emitted: false`、
  `paths_or_ranges_emitted: false`（从不是 path 或 range 字符串）；
- 固定 `failure_category_counts` 包含 `line_budget_shape_error` 及现有类别
  （`missing_required_field`、`wrong_type`、`mapping_error`、
  `private_field_leak`、`public_artifact_leak`、`unexpected_exception`、
  `no_rows_returned`、`endpoint_unavailable`）；
- `private_label_isolation_verified`、`adapter_assertions_passed`、
  `raw_rows_persisted: false`、`row_level_values_emitted: false`、
  `row_level_hashes_emitted: false`、`raw_response_stored: false`、
  `derived_labels_published: false`；
- license gating：`license_status: cc-by-nc-nd-4.0`、
  `row_level_redistribution_allowed: false`、
  `derived_label_publication_allowed: false`、
  `public_release_status: blocked_by_license`；
- 所有 no-claim 标志为 false、`aggregate_only_public_artifact=true`、
  `not_evidence=true`、`candidate_not_fact=true`、
  `forbidden_scan.status=pass`；
- `status: pass|partial|unavailable|fail_forbidden_leak|fail_schema_contract`。

forbidden scanner 在 `SCHEMA_KEY_CONTAINER_KEYS` allowlist 中添加了
`line_budget_readiness`，使其计数 key（固定 readiness 标签，非字段名或 path）被
接受。scanner 仍禁止公共输出中任何位置的行级值、path、span、hash、URL 与
secret。每次写入前运行 fail-closed forbidden scan。注入的 `"12-34"` line range
字符串与 path-like 值仍会被拒绝。

### 真实 row-map smoke 结果（2026-06-20）

```text
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_swe_explore_row_mapping_report.json
  => rows_seen: 10, rows_mapped: 10, rows_failed: 0
  => status: pass, forbidden_scan: pass
  => private_label_isolation_verified: true
  => adapter_assertions_passed: true
  => raw_rows_persisted: false, row_level_values_emitted: false,
     row_level_hashes_emitted: false, raw_response_stored: false,
     derived_labels_published: false
```

所有 7 个 SWE schema 字段名在全部 10 行中非空；所有 5 个 public-task presence
布尔在全部 10 行中为 True。嵌套私有类别（`ground_truth_patch`、
`ground_truth_modified_files` 等）在真实 HF `default/train` 预览行中被观察到
为缺失 —— 这是准确的 schema 观察，不是错误。因此 artifact 记录
`budget_evaluation_shape_supported=false`：C4.3 是 row-mapping/privacy boundary
smoke 加一个负向 line-budget shape observation，不是正向 line-budget readiness
 证据。未持久化任何行级值、hash、文件路径、line range、span、snippet、patch/test、
 meta 原始内容、label、provider payload、content_sha 或原始 HF payload。

## C4.4 CORE-Bench source readiness / no-go

C4.4 是针对 CORE-Bench（arXiv:2606.11864v1 —— "CORE-Bench: A Comprehensive
Benchmark for Code Retrieval in the Era of Agentic Coding"）的 **source-
readiness no-go** 阶段。它**不是** adapter 或 schema 就绪模块：实际 HF 数据集
文件/schema 不可用，因此 C4.4 仅输出一份 **source-readiness no-go** 报告。不
声称任何 adapter 支持或 schema 就绪。

### 错误目标消歧

目标是 agentic-coding CORE-Bench（HF placeholder `zhangfw123/CORE-Bench`），
**不是**旧的 `siegelz/core-bench` 科学复现 benchmark。artifact 记录
`wrong_target_disambiguated=true` 与 `not_siegelz_core_bench=true`。

### 已确认的外部发现

- 论文 arXiv/HTML 已确认（arXiv:2606.11864v1）。
- HF 数据集 repo `zhangfw123/CORE-Bench` 为 public、非 gated、MIT-tagged（来自
  README frontmatter `license: mit`）。
- HF repo 当前仅包含 `.gitattributes` 和 `README.md`（`sibling_count=2`）；未发
  布实际数据集文件。
- datasets-server preview/viewer/search/filter/statistics 不可用；`/is-valid`
  返回 false；`/splits` 不可用；`/first-rows` 不可用。
- 未确认官方 GitHub/project page。
- 论文 aggregate facts（来自 arXiv Table 1，paper-level 非 row-level）：3 个
  level（code understanding 172,961 queries；issue-to-edit localization
  5,061 queries / 632 repos / 52,712 qrels；broader context retrieval 2,580
  queries / 97 repos / 106,479 qrels）；共 180,602 queries；106,479
  broader-context labels。

### Artifact

`artifacts/c4_external_benchmark_adapters/c4_core_bench_source_readiness_report.json`
（schema `c4_core_bench_source_readiness.v1`、
`claim_level=source_readiness_no_go_only`）。状态为
`blocked_dataset_placeholder_empty`（非 `pass`/`support`）。
`source_confirmation_status=paper_and_placeholder_confirmed_dataset_unavailable`。
`adapter_support_claimed=false`、`schema_readiness_claimed=false`、
`schema_smoke_attempted=true`、`schema_smoke_passed=false`、
`row_map_smoke_attempted=false`、`row_level_redistribution_allowed=false`、
`derived_label_publication_allowed=false`。所有 no-claim 标志为 false；
`aggregate_only_public_artifact=true`、`not_evidence=true`、
`candidate_not_fact=true`、`forbidden_scan.status=pass`。

### Source probes

脚本 `eval/c4_core_bench_source_readiness.py` 仅通过 stdlib `urllib` 运行有界
网络 probe（超时 10s，无新依赖）：HF dataset API、HF tree API、datasets-server
`/is-valid`、`/splits`、`/first-rows`。不存储原始响应体；仅解析 aggregate 元数
据与状态类别。`--offline` 模式下，不进行网络调用，报告从已确认的静态发现构建。

### Follow-up requirements

要解除 CORE-Bench adapter/schema 就绪的阻塞，需要：发布实际数据集文件、暴露
schema 与 splits、发布 qrels/corpus/query 文件、提供 license 与再分发声明、
确认官方 GitHub 或 project page。

## C4.5 RepoQA source/schema-contract readiness（adapter deferred）

C4.5 是针对 EvalPlus **RepoQA** benchmark（任务：**Searching Needle
Function / SNF**；arXiv:2406.06025；OpenReview `hK9YSrFuGf`）的
**source/schema-contract readiness，adapter deferred** 阶段。它**不是** adapter
模块、**不是** schema 就绪模块、**不是** public-row-schema 就绪模块、也
**不是** benchmark 结果模块。官方 schema contract 可从 source/docs/loader
获知，但完整 adapter/row-map benchmark 支持**已推迟**，等待对
derived-qrels/version/license 的有意识决策。未将 RepoQA 添加到
`eval/c4_external_benchmark_adapters.py`。

### 错误目标消歧

Canonical 目标是 EvalPlus RepoQA/SNF，**不是** `Nutanix/RepoQA-neo4j`、
`microsoft/SCBench:scbench_repoqa`、`CodeRepoQA`、`SWE-QA-Bench`、
`CoReQA`、`RepoExec`、`RepoBench` 或 `SWE-QA-Pro`。artifact 记录
`wrong_target_disambiguated=true` 及排除目标列表与原因。

### 已确认的外部发现

- 论文：arXiv:2406.06025、OpenReview `hK9YSrFuGf`。
- Homepage/leaderboard：`https://evalplus.github.io/repoqa.html`。
- 代码仓库：`https://github.com/evalplus/repoqa`（Apache-2.0）。
- 数据集发布仓库：`https://github.com/evalplus/repoqa_release`
  （Apache-2.0）。
- 当前 loader 默认 release：tag `2024-06-23`，asset
  `repoqa-2024-06-23.json.gz`（monolithic `.json.gz`；**未**下载或解压）。
- 论文兼容 release：tag `2024-04-20`，asset
  `repoqa-2024-04-20.json.gz`。
- 论文 aggregate facts（paper-level，非 row-level）：5 languages x 10
  repos x 10 needles = 500 code-search tasks over 50 repositories。
- Version skew：论文描述 5 languages；当前 loader 默认
  （`2024-06-23`）新增 Go 支持（6 languages）。
- 官方 schema contract：顶层形态为 language -> repo records。Repo record
  字段：`repo`、`commit_sha`、`entrypoint_path`、`topic`、`content`、
  `dependency`、`needles`。Needle 字段：`path`、`name`、`start_byte`、
  `end_byte`、`start_line`、`end_line`、`description`。SNF
  task/model-output 字段为 adapter-derived，在真实数据中为行级/私有。
- 未确认官方 HF dataset/Data Viewer/qrels/corpus/query split。数据集为
  monolithic source-containing JSON.gz。

### Artifact

`artifacts/c4_external_benchmark_adapters/c4_repoqa_source_readiness_report.json`
（schema `c4_repoqa_source_readiness.v1`、`claim_level =
source_schema_contract_readiness_adapter_deferred_only`）。状态为
`source_confirmed_schema_contract_ready_adapter_deferred`（非
`pass`/`support`）。
`adapter_support_claimed=false`、`schema_readiness_claimed=false`、
`public_row_schema_readiness_claimed=false`、
`schema_contract_readiness_claimed=true`、
`row_map_smoke_attempted=false`、`row_map_smoke_passed=false`、
`benchmark_result_claimed=false`。
`release_asset_downloaded=false`、`release_asset_decompressed=false`、
`release_asset_body_read=false`、`monolithic_json_rows_read=false`、
`row_level_redistribution_allowed=false`、
`derived_label_publication_allowed=false`。所有 no-claim 标志为 false；
`aggregate_only_public_artifact=true`、`not_evidence=true`、
`candidate_not_fact=true`、`forbidden_scan.status=pass`。

### Source probes

脚本 `eval/c4_repoqa_source_readiness.py` 仅通过 stdlib `urllib` 运行有界
网络 probe（超时 10s，无新依赖）：GitHub code repo API、GitHub release repo
API、GitHub release API（tag `2024-06-23`）获取 asset metadata（仅
name/size/content_type；asset body **未**下载或解压），以及对 arXiv abs、
homepage、OpenReview URL 的 HEAD/GET 状态 probe。不存储原始响应体；仅解析
aggregate 元数据与状态类别。`--offline` 模式下，不进行网络调用，报告从已确认
的静态发现构建。

### Schema contract field-name categories

Schema contract 字段名（`repo`、`content`、`needles`、`path`、`start_line`、
`description` 等）仅记录在显式 schema-contract 容器
（`repo_record_contract_fields`、`needle_contract_fields`、
`task_record_contract_fields`、`model_output_contract_fields`、
`adapter_derived_private_field_categories`、`schema_contract_field_names`）
下。它们是关于 schema contract 的观察，非行级数据。forbidden scanner 在此
允许，但在 row-like dict key/value 上下文中拒绝。

### Follow-up requirements

要解除 RepoQA adapter/row-map 就绪的阻塞，需要：derived-qrels 设计决策、
version 选择决策、license 与再分发声明、row-map smoke 设计、adapter 集成
决策。

### 验证

```text
python3 -m py_compile eval/c4_repoqa_source_readiness.py   => PASS
python3 eval/c4_repoqa_source_readiness.py --self-test     => PASS（9 组）
python3 eval/c4_repoqa_source_readiness.py --offline \
  --out /tmp/c4_repoqa_offline.json                         => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: offline_static_findings_only,
   forbidden_scan: pass, new_network_calls: 0)
python3 eval/c4_repoqa_source_readiness.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_repoqa_source_readiness_report.json                     => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: sources_confirmed_via_probe,
   forbidden_scan: pass, new_network_calls: 6)
```

Self-test 组（9）：错误目标消歧；offline report shape；schema-contract
allowlist vs row-key leak；schema container strict pass/fail（批准字符串
pass；未批准 function/path 值、dict row-like object、schema container 内
forbidden dict key 均 fail）；leak injection 拒绝（repo/function 名、path、
commit SHA、line/byte range、description/question/answer、snippet、raw
JSON fragment、content hash/provider payload）；release metadata 允许但
content sample/digest 禁止；source URL 允许；report aggregate-only；
fail-closed generation。

## 注意事项

- C4.1/C4.2/C4.3 仅是 adapter/row-mapping 就绪。它**不**校验行级语义、label 或下游
  agent 价值。schema smoke 仅确认公共 HF datasets-server schema 端点可达且可解
  析；row-map smoke 仅确认 adapter 边界成立（public task 无私有 attr；private
  label 仅在内存中保留私有值）。两者均**不**确认 benchmark 质量、label 正确性
  或对任何下游评估的适用性。不做任何性能声明。
- C4.4 仅是 source-readiness no-go。它**不**声称 adapter 支持或 schema 就绪。
  CORE-Bench HF 数据集当前为 placeholder（仅 `.gitattributes` + `README.md`）；
  实际数据集文件/schema 不可用。在实际 dataset 内容与条款发布前，行级再分发和
  派生 label 发布保持禁用。
- C4.5 仅是 source/schema-contract readiness，adapter deferred。它**不**声称
  adapter 支持、schema 就绪、public row schema 就绪、row-map smoke pass 或
  benchmark result。官方 schema contract 可从 source/docs/loader 获知，但
  monolithic JSON.gz **未**下载或解压；未读取或持久化行级数据。行级再分发
  与派生 label 发布保持禁用，等待对 derived-qrels/version/license 的有意识
  决策。
- ContextBench 数据集 license 未知，即使代码仓库为 Apache-2.0；行级再分发被禁用。
- SWE-Explore HF 数据集 license 为 `cc-by-nc-nd-4.0`；行级再分发与派生 label
  发布均被禁用。
- 合成 self-test 行不提供任何经验支持。
- `spec_hash` 是确定性的，排除时间戳/网络/原始行/本地路径；它**不是**
  content_sha，也不是行级证据。
- 行级 hash 是行级派生数据，从不输出。

## 下一步

- 未来的外部 benchmark 评估（独立于 C4.1/C4.2/C4.3/C4.4/C4.5）需要一个显式的、evidence-gated
  的 preregistration，并尊重每个 benchmark 的 license gating 与 OpenLocus 公共
  artifact 契约。
- C4.4 后续：等待实际 CORE-Bench 数据集文件、schema 与 splits 发布后，才可考虑
  adapter/schema 就绪。
- C4.5 后续：RepoQA adapter/row-map 就绪已推迟，等待对
  derived-qrels/version/license 的有意识决策。monolithic JSON.gz **未**下载
  或解压；未读取或持久化行级数据。
- C4.1/C4.2/C4.3/C4.4/C4.5 不产生 promotion、不产生默认策略变更、不产生 EvidenceCore 语义变更、
  不产生 runtime-clean 通用算法声明、不产生下游 agent 价值声明、不产生 OOD 时间
  声明，也不产生 QuIVer systems 声明。
