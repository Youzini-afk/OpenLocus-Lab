# BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe

日期：2026-06-30

BEA-v1-N10ER 是 **bounded public CI score/guard safety probe** —— N10EQ
checkpoint `7963831` 之后的真实执行阶段。它在 held-out 的 manifest-listed
public CI sample 上执行 N10EQ 设计的 safety probe，将 N10EQ 设计的 7 个
safety features 计算为 **仅 aggregate buckets**，并输出 sanitized
aggregate-only report。它逐字复用 N10EN 的 retrieval/order plumbing（frozen
transforms、clone、generate-tasks、OpenLocus search），**不** 改变 N10EN
的语义或 artifacts。

## 默认行为

当 `enable_public_github_network` 为 `false`（默认）时，N10ER 输出
fail-closed/unavailable artifact，**不** clone、build 或 search：

```text
status: n10er_safety_probe_unavailable_network_disabled
network_run: false
clone_run: false
search_run: false
n10er_execution_authorized: false
```

安全默认不触碰网络，不改动 repo，不读取 private diagnostic inputs。

## CI 结果

GitHub Actions run `28457213423` 执行了显式启用 public GitHub network 的
`canary_small_heldout`。状态为
`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized`：样本满足
minimums（`public_task_count=80`、`scored_task_count=60`、`task_with_gold_count=40`），
heldout overlap check 通过（`overlap_zero`），但 safety signal 未复现。risk bucket
足够大（`task_count=26`），但在该 bucket 内 full/guard/diffaware 都丢失 `0` 个
baseline top-10 hits，`guard_would_preserve_full_loss_count=0`。

Arm aggregates：baseline `37/39/40/40`；full `36/39/40/40`，lost baseline top10
`1`；guard `38/39/40/40`，lost baseline top10 `0`；diffaware `37/39/40/40`，lost
baseline top10 `1`。这些 arm aggregates 只是上下文；N10ER top-level status 由
safety signal gate 决定。

## N10EQ source lock

```text
n10eq_checkpoint: 7963831
n10ep_checkpoint: 0a54b49（upstream source lock）
status: n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized
n10er_contract_authorized: true
n10er_execution_authorized: false（design-only contract）
next_phase: BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe
source_locked: true
```

## 启用运行（held-out public CI sample）

当设置 `--enable-public-github-network` 时，N10ER：

- 只 clone **manifest-listed public repos**（复用 `ci_clone_and_lock_repo`）；
- 先用 `--no-labels` 生成 public tasks（RUN 阶段看不到 gold）；
- build/使用 checkout 的本地 OpenLocus CLI 临时 materialize public candidates
  （BM25 limit 100；old-pool 代理 = regex-top20 ∪ symbol-top20 file identities）；
- **逐字复用 N10EN** 的四个 frozen transforms（baseline、full novel-first、
  guarded top5、diffaware），**不** 改动 N10EN；
- 固定 RUN-phase orders，**之后** 生成 score-phase labels 并对固定 orders
  打分（labels/gold 仅用于 aggregate 打分，绝不用于 policy）；
- 将 7 个 safety probe features 计算为 aggregate buckets；
- 仅上传 sanitized aggregate-only report。

held-out sample 使用 `canary_small_heldout` target/scored/gold `80/50/30`，
`canary_medium_heldout` 使用 `160/100/60`。held-out 选择使用 N10EN reference repo prefix 之后的
manifest-listed repos。N10ER 会私下检查这些 repo 是否与该 N10EN reference
prefix 重叠，公开只发布 overlap count/bucket aggregates，不发布 repo/task identities。

## 状态词汇

```text
n10er_safety_probe_pass_signal_reproduced_n10es_authorized
n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10er_safety_probe_inconclusive_insufficient_risk_bucket_n10es_authorized
n10er_safety_probe_inconclusive_insufficient_sample_n10es_authorized
n10er_safety_probe_unavailable_network_disabled  # 默认关闭（exit 0）
no_go_n10eq_gate_failed                          # contract failure（exit 1）
fail_no_public_tasks_generated                   # infra failure（exit 1）
fail_run_phase_candidate_generation              # infra failure（exit 1）
fail_clone_or_build                              # infra failure（exit 1）
fail_forbidden_scan                               # privacy failure（exit 1）
fail_schema_contract                              # schema failure（exit 1）
fail_contract_violation                           # contract failure（exit 1）
```

Top-level result 回答 low-novelty + strong-baseline full-displacement /
guard-preservation safety signal 是否复现。Arm aggregate outcomes 仍会报告，但不单独决定 phase status。
workflow 在 contract/privacy/build/clone failures 上失败，而不在有效的 no-signal
或 inconclusive research result（包括 insufficient sample）上失败。

## Safety feature buckets（7 个，仅 aggregate）

| Feature | Buckets |
|---|---|
| `top5_novel_candidate_item_count_bucket` | 0_to_2 / 3 / 4_to_5 |
| `baseline_prefix_strength` | strong_prefix_le_5 / weak_prefix_gt_5 / no_baseline_hit |
| `baseline_gold_proxy` | baseline_hit_proxy / baseline_miss_proxy |
| `full_displacement_risk` | low_novelty_strong_prefix_displacement_risk / other_no_displacement_risk |
| `guard_preservation_ref` | guard_preserved_baseline / guard_lost_or_no_baseline |
| `candidate_available_beyond_top10` | candidate_available_beyond_top10 / candidate_missing_or_within_top10 |
| `arm_selection` | full_novel_first / guarded_top5_novel_distinct |

所有 features 都在 aggregate buckets 上计算；不发布 per-task raw
candidates/paths/ranks/gold。`gold_used_for_policy_bool=false`。

## Pass/fail gates（9 个，N10EQ/N10ER 设计）

1. `n10er_private_execution_inputs_aggregate_publication_only` —— private bounded-CI orders/candidates/retrieval/labels 可在 freeze 后内部使用；禁止 raw publication。
2. `n10er_displacement_risk_aggregate_only` —— 无 per-task raw 输出。
3. `n10er_no_threshold_tuning` —— 冻结 threshold >= 4 不变。
4. `n10er_no_method_winner_claim` —— 不推广 guard/full/diffaware。
5. `n10er_no_runtime_default_change` —— safety probe 保持 opt-in/eval-only。
6. `risk_bucket_sufficiency_gate` —— risk bucket 至少有 5 个 tasks。
7. `low_novelty_strong_baseline_signal_gate` —— full 比 guard 丢失更多 baseline hits，且 guard 至少保留 1 个 full loss。
8. `guard_reference_non_regression_gate` —— guard 在 risk bucket 中不比 full/diffaware 丢失更多 baseline hits。
9. `displacement_mechanism_classification_gate` —— risk-bucket displacement classification 完整。

所有 gates 在 aggregate buckets 上评估；`gate_uses_gold_for_policy_bool=false`。

## Execution boundary

N10ER 可在 RUN-phase orders 固定**之后** 私有地 produce/read
orders/candidates/retrieval output/per-task diagnostics/score-phase labels。
这些保持私有/临时；public artifact 仅 aggregate。
`n10en_artifact_mutated_bool=false`、
`n10en_semantics_reused_verbatim_bool=true`、
`n10en_private_task_ids_read_bool=false`、`frozen_rule_changed_bool=false`、
`threshold_tuned_bool=false`、`public_artifact_aggregate_only_bool=true`。

## Boundary

N10ER 只授权在 held-out manifest-listed public sample 上执行 bounded
public CI safety probe，以及 **N10ES audit** handoff（下一阶段）。它 **不**
授权：N10ER re-run、threshold tuning、新 policy experiments、frozen-rule
变更、推广 guard/full/diffaware、runtime/default 变更、method-winner claims、
downstream/scaled retrieval、selector/reranker、provider/model network、
raw diagnostic publication、CI variant execution 或对 frozen rule 的任何更改。
这些 claim/stop 字段全部为 `false`。`n10er_contract_authorized_bool=true`
（来自 N10Q）但 `n10er_execution_authorized_bool` 仅在本次运行显式启用网络时
为 `true`。

Next allowed phase：**BEA-v1-N10ES Bounded Public CI Safety Probe Audit**。

## Workflow

- Workflow：`.github/workflows/bea-v1-n10er-bounded-public-ci-score-guard-safety-probe.yml`
- Inputs：`enable_public_github_network`（默认 `false`）、
  `stage`（`canary_small_heldout` / `canary_medium_heldout`）、
  `max_repos`（可选）。仅上传 sanitized aggregate JSON。

## Artifact

- Helper：`eval/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe.py`
- Report：`artifacts/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe/bea_v1_n10er_bounded_public_ci_score_guard_safety_probe_report.json`
