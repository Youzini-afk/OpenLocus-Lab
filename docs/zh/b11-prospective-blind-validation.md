# B11 Prospective Blind Validation

Date: 2026-06-18

B11 是冻结的 balanced policy `balanced_policy_v1_benchmark_routed`（B10）的第一次真正
**prospective** validation。此前的 validation（B6C/B6E/B6F/B8-lite/B9C）共享同一套 task
生成与研究 universe。B11 使用 **2026-06-18 policy freeze 之后生成的新 repos 与新
tasks**，不对 policies、thresholds 或 success criteria 做任何 retuning。

> **重要的 claim 边界。** B11 是 prospective stress test，**不是** promotion step。即使
> B11 成功，`promotion_ready=false`、`default_should_change=false`，且 `EvidenceCore` 语义
> 不变。B11 的结果只决定 balanced policy 是否是一个值得进一步研究（B12 mechanism
> decomposition、B13 distributionally robust policy search）的 credible algorithm candidate。

## Preregistration declaration

以下 artifacts、thresholds 与 criteria 在任何 prospective validation run 之前均已
**FROZEN**。B11 live runs 开始后不允许 retuning。任何 post-hoc analysis 必须标注为
exploratory，并需要单独一轮 validation。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 冻结 spec；sha256 在
  `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`）
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow predicate；
  sha256 `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`）
- `rmc_local_conservative_v0`（Conservative policy；冻结于
  `eval/b6_lite_interpretable_policy_search.py`）
- `p25.route_bucket_routed_v0`（P25 policy；冻结于 `eval/p25_bucket_policy.py`）
- B10B 10 个 predeclared acceptance gates（含
  `label_driven_ambiguous_min_denominator: 10` hard gate）
- B10B verdict 框架（`runtime_shadow_ambiguous_supported` +
  `support_claim` + `support_claim_reason`）
- 本文档中所有 success/failure/partial criteria

## Objective

测试冻结的 balanced policy 能否泛化到未见过的 repos、languages 与 model families。具体为：

> 在 prospective data 上，Balanced v1 是否在降低 false spans、PFP、LLM calls 的同时
> 保持 gold/SpanF0.5，且 worst-group metrics 不退化超过 predeclared thresholds？

## Scope

### Minimum viable B11（建议首轮）

- 8 repos，覆盖 5 种 languages
- ~120 tasks（每 repo 15 个）
- 4 个 model families
- 4 个 policies
- 预计 runtime：每个 model family 4-6 小时 CI

### Full B11（若 minimum viable 有前景）

- 12-16 repos，覆盖 5+ 种 languages
- 300-500 tasks
- 4 个 model families
- 4 个 policies

## Repos（新，未用于 B6B/B6C/B6E/B6F/B8-lite）

**已使用（排除）：** `py_flask`、`js_express`、`go_gin`、
`rust_ripgrep`、`go_cobra`、`py_httpx`、`js_axios`、`rust_mdbook`。

### Minimum viable B11 repo selection（8 repos，5 languages）

| repo_id | Public repo | Language | Tier | Domain |
| --- | --- | --- | --- | --- |
| `py_fastapi` | fastapi/fastapi | Python | nightly_medium | web framework |
| `py_pytest` | pytest-dev/pytest | Python | nightly_medium | testing framework |
| `ts_vite` | vitejs/vite | TypeScript | nightly_medium | build tool |
| `ts_hono` | honojs/hono | TypeScript | nightly_medium | web framework |
| `go_chi` | go-chi/chi | Go | nightly_medium | web framework |
| `go_prometheus` | prometheus/prometheus | Go | nightly_medium | monitoring |
| `rust_deno` | denoland/deno | Rust | weekly_large | runtime |
| `java_spring_petclinic` | spring-projects/spring-petclinic | Java | nightly_medium | web app |

### Full B11 additional repos（再增 4-8 个）

| repo_id | Public repo | Language | Tier | Domain |
| --- | --- | --- | --- | --- |
| `py_requests` | psf/requests | Python | nightly_medium | HTTP client |
| `py_rich` | Textualize/rich | Python | nightly_medium | terminal UI |
| `go_gh_cli` | cli/cli | Go | nightly_medium | CLI |
| `ts_vue_core` | vuejs/core | TypeScript | nightly_medium | framework |
| `kotlin_okhttp` | square/okhttp | Kotlin | nightly_medium | HTTP client |
| `c_curl` | curl/curl | C | nightly_medium | networking |
| `ruby_rails` | rails/rails | Ruby | weekly_large | framework |
| `cpp_json` | nlohmann/json | C++ | nightly_medium | header-only |

所有 repos 均为 public/open-source，并已列于 `eval/ci_repos/openlocus-ci-repos-v1.yaml`。

## Model adapters

| Model family | Model ID | Output mode | Rationale |
| --- | --- | --- | --- |
| Kimi（reference） | `[mk]Kimi-K2.7-Code` | `tool_call` | Primary reference；在 B1/B6C/B6E/B6F 中已确立 |
| Qwen（secondary） | `[mk]Qwen3.6-27B` | `json_schema_strict` | 按 B9B/B9C 健康-stable；方向与 Kimi 一致 |
| DeepSeek Flash（recall） | `[mk]DeepSeek-V4-Flash` | `json_schema_strict` | 按 B9D 健康-stable；recall-oriented profile |
| DeepSeek Pro（conservative） | `[mk]DeepSeek-V4-Pro` | `json_schema_strict` | 按 B9D 健康-stable；conservative profile |

**GLM-5.2 被排除**（按 B9A/B6D 噪声大；`schema_valid` 0.75-0.833，
`infra_failure` 0.25-0.5）。GLM 仍为 opt-in/exploratory，不在 critical path。

**Output mode 是 model-adapter 配置参数，**不是** OpenLocus algorithm 变量**
（见 project memory 237）。不做 output-mode leaderboards。

## Policies compared

| Policy | Spec ID | Description |
| --- | --- | --- |
| Local baseline | （无 LLM） | 纯本地检索（regex + BM25 + symbol + RRF）；无 LLM calls |
| P25 | `p25.route_bucket_routed_v0` | Benchmark-routed bucket policy；依赖 `task_bucket`/`task_risk_tags` |
| Balanced v1 | `balanced_policy_v1_benchmark_routed` | 冻结 balanced policy；ambiguous→`weak_only`，否则 P25；依赖 `task_bucket`/`task_risk_tags` |
| Conservative | `rmc_local_conservative_v0` | 冻结 conservative policy；避免 false positives 但损失 recall |

## Task generation

Tasks 在 policy freeze（2026-06-18）**之后**生成，使用现有 CI task 生成 pipeline
（`eval/ci_repos/openlocus-ci-repos-v1.yaml` + openlocus CLI）。Tasks 是确定性的/从 repo 内容
挖掘的（非人工编写）。Task generation 在 RUN phase **不**读取 labels（与现有 P21/P25/P30
evaluators 的 RUN/SCORE 分离一致）。

## Metrics

### Primary metrics

- `SpanF0.5`
- `MRR`
- Gold retention（`added_gold_span`）
- False spans（`added_false_span`）
- PFP（`primary_false_positive_rate`）
- LLM calls（`model_calls`）
- Cost（估算的 provider cost）
- Latency（p50/p95）

### Aggregation

- Overall mean（跨所有 tasks）
- **Worst-group**，按：
  - Model family（Kimi/Qwen/DeepSeek Flash/DeepSeek Pro）
  - Repo（8 或 12-16 个 repos）
  - Language（Python/TypeScript/Go/Rust/Java + 其他）
  - Task bucket（positive/negative/ambiguous/hard-distractor）

### Statistical

- 95% bootstrap confidence intervals（10,000 次 resamples，按 repo 分层）
- Leave-one-repo-out sensitivity
- Leave-one-model-family-out sensitivity
- Paired deltas（Balanced v1 vs. 每个 baseline）
- Holm-Bonferroni correction（用于多重比较）

### RobustUtility

```text
RobustUtility = min_group(
    SpanF0.5
    - λ * PFP
    - μ * normalized_cost
    - ν * normalized_latency
)
```

建议参数（predeclared；可在 sensitivity analysis 中变化）：
- `λ = 1.0`
- `μ = 0.1`
- `ν = 0.1`

## Predeclared success/failure/partial criteria

所有 deltas 均为 `Balanced_v1 - baseline`（正 = 改善，负 = 退化），按 task 计算后聚合。

### Success（须全部成立）

- Balanced v1 保持 gold：`Δgold_span vs P25 ≥ -max(1, 0.01 * P25_gold)`
- Balanced v1 保持 SpanF0.5：`ΔSpanF0.5 vs P25 ≥ -0.02`
- Balanced v1 降低 false spans：`Δfalse_spans vs P25 < 0`
- Balanced v1 降低 PFP：`ΔPFP vs P25 ≤ 0`
- Balanced v1 降低 LLM calls：`ΔLLM_calls vs P25 < 0`
- Worst-group metrics 不退化超过 thresholds：
  - Worst-group `Δgold_span ≥ -max(2, 0.02 * P25_gold)`
  - Worst-group `ΔSpanF0.5 ≥ -0.05`
  - Worst-group `ΔPFP ≤ +0.05`

### Failure（任一即触发）

- Balanced v1 在 overall gold 上退化：`Δgold_span < -max(2, 0.02 * P25_gold)`
- Balanced v1 在 overall SpanF0.5 上退化：`ΔSpanF0.5 < -0.05`
- Worst-group `Δgold_span < -max(3, 0.03 * P25_gold)`
- Worst-group `ΔSpanF0.5 < -0.10`

### Partial（既非 success 也非 failure）

- 混合结果：部分 metrics 改善，部分退化，但未超过 failure thresholds。B11 之后应进入
  B12（mechanism decomposition）以理解哪些条件驱动了混合结果。

## CI workflow design

### New stage：`b11_prospective`

向 `.github/workflows/real-provider-benchmark.yml` 新增 stage `b11_prospective`。该 stage
在新 B11 repos 上以冻结的 policies 运行 P21，随后运行 B11 report aggregator 与
B10B replay。

### Workflow inputs

- `stage`：`b11_prospective`
- `dataset`：`b11_prospective_v1`
- `llm_model`：`[mk]Kimi-K2.7-Code`、`[mk]Qwen3.6-27B`、
  `[mk]DeepSeek-V4-Flash`、`[mk]DeepSeek-V4-Pro` 之一
- `enable_remote_models`：`true`
- `repo_id`：可选（用于单 repo 运行）

### Run matrix

- 4 个 model families × 8 个 repos（minimum viable）= 32 次 runs，或
- 4 个 model families × 1 个 8-repo batch = 4 次 runs（每次 run 覆盖全部 repos）
- 每次 run 产出 P21 ephemeral records + B10B replay report

### B10B integration

- B10B `--records` 在每次 B11 run 之后于 CI 中运行（已通过 commit `2cbdd0c` 集成到 P21
  step）
- 这给 B10B 带来首次 empirical validation
  （`replay_source="ci_ephemeral_records"`）
- 若 B10B 通过所有 10 个 predeclared gate，则从 “mechanics-validated” 升级为
  “empirically-supported”
- 若 B10B 失败，B11 仍继续（B10B 仅是 ambiguous-branch shadow；B11 测试的是
  benchmark-routed policy）

## B11 report aggregator

新 evaluator：`eval/b11_prospective_validation.py`

读取 4 个 model × N 个 repo runs 的 P21 输出，并计算：

- Per-policy metrics（Local、P25、Balanced v1、Conservative）
- Overall mean + worst-group
- Bootstrap CIs
- Leave-one-repo-out、leave-one-model-family-out
- `RobustUtility`
- Verdict（`success` / `failure` / `partial`）

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_calls_by_replay=0 (for B10B replay)
model_calls_by_replay=0 (for B10B replay)
aggregate_only_public_artifact=true
policy_search_performed=false (no policy tuning during B11)
quality_strategy_tuned=false
```

## What's autonomous vs. needs user action

### Autonomous（现在即可完成）

- B11 plan 文档（本文件）
- B11 CI workflow 定义
- B11 report aggregator 脚本（skeleton + self-test）
- Repo selection（来自现有 CI manifest）
- Model adapter 配置（现有 profiles）

### Needs workflow_dispatch

- 实际 live LLM runs（需要 `enable_remote_models=true` +
  `OPENLOCUS_ALLOW_REMOTE=1`）
- 用户触发每个 model family run

### Needs user review

- 结果解读
- 决定是否进入 B12（mechanism decomposition）或 B13
  （distributionally robust policy search）
- 决定是否从 minimum viable 扩展到 full B11

## Artifacts

- `artifacts/b11_prospective_validation/b11_prospective_validation_report.json`
- `artifacts/b11_prospective_validation/b11_prospective_validation_plan.json`
  （本 preregistration，机器可读）
- `artifacts/real_provider_ci/b10b_runtime_shadow_replay_report.json`（来自
  B11 runs 的 B10B empirical data）

## Self-test

```bash
python3 eval/b11_prospective_validation.py --self-test
```

在不进行 live runs 的情况下验证 report aggregator 机制（仅 synthetic fixture；
`replay_source="synthetic_fixture"`；verdict 为 `partial` 或
`insufficient_data`）。

## What B11 does NOT prove

- B11 **不**证明 balanced policy 已准备好 promotion。
- B11 **不**证明 runtime-shadow predicate（B10B）受到 empirical
  support（这要求 B10B 在真实 CI records 上通过 gate）。
- B11 **不**改变 `EvidenceCore` 语义。
- B11 **不**改变任何 defaults。
- B11 **不**在未经单独 user review 的情况下授权 B12/B13。

## Next steps after B11

- **B11 success**：进入 B12（mechanism decomposition）以理解 balanced policy 为何有效；
  随后 B13（distributionally robust policy search）以优化 worst-group。
- **B11 failure**：balanced policy 很可能 overfit 到 B6C/B6E/B6F
  universe。在合并的 B6C+B11 data 上以 distributionally robust objectives 重新启动
  policy search（B13）。
- **B11 partial**：进入 B12 以识别哪些条件驱动了混合结果；B12 据此决定是否调整 policy
  （B13）或接受部分泛化。
