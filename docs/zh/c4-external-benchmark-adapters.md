# C4 外部 Benchmark Adapter —— Schema 就绪 v1

日期：2026-06-20

C4.1 是 **外部 benchmark adapter / schema 就绪** 阶段。它**不是**外部
benchmark 性能评估，**不是** benchmark 结果，**不是**下游 agent 价值证明，也
**不是** promotion 或默认策略变更。该阶段产出一个新 evaluator
（`eval/c4_external_benchmark_adapters.py`）与一个 canonical aggregate-only
公共 artifact
（`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`），
仅记录 adapter/schema 就绪状态。行级 benchmark 内容未被持久化。

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
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS（9 组）
python3 eval/c4_external_benchmark_adapters.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_external_benchmark_adapter_report.json                     => PASS（forbidden_scan: pass）
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json                       => PASS
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json                        => PASS
```

Self-test 组（9）：ContextBench adapter 分离、SWE-Explore adapter 分离、line
range 归一化、forbidden scan 拒绝注入、no-claim 标志全为 false、spec hash 确
定性、aggregate-only 报告、forbidden scan 在生成时阻断泄漏、schema smoke 报告
形态。

## 注意事项

- C4.1 仅是 adapter/schema 就绪。它**不**校验行级语义、label 或下游 agent 价值。
  schema smoke 仅确认公共 HF datasets-server schema 端点可达且可解析；它**不**确
  认 benchmark 质量、label 正确性或对任何下游评估的适用性。
- ContextBench 数据集 license 未知，即使代码仓库为 Apache-2.0；行级再分发被禁用。
- SWE-Explore HF 数据集 license 为 `cc-by-nc-nd-4.0`；行级再分发与派生 label
  发布均被禁用。
- 合成 self-test 行不提供任何经验支持。
- `spec_hash` 是确定性的，排除时间戳/网络/原始行/本地路径；它**不是**
  content_sha，也不是行级证据。

## 下一步

- 未来的外部 benchmark 评估（独立于 C4.1）需要一个显式的、evidence-gated 的
  preregistration，并尊重每个 benchmark 的 license gating 与 OpenLocus 公共
  artifact 契约。
- C4.1 不产生 promotion、不产生默认策略变更、不产生 EvidenceCore 语义变更、不
  产生 runtime-clean 通用算法声明、不产生下游 agent 价值声明、不产生 OOD 时间
  声明，也不产生 QuIVer systems 声明。
