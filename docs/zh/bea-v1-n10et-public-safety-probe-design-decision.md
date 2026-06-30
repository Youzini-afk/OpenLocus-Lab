# BEA-v1-N10ET Public Safety Probe Design/Decision

日期：2026-06-30

BEA-v1-N10ET 是 BEA-v1-N10E safety-probe 分支的 **public-only 收尾 design/decision**
阶段。它位于 N10ES checkpoint `8c04a0a` 之后——N10ES 已将 N10ER bounded public CI
score/guard safety probe 打包为有效 research negative，并明确只授权 N10ET。N10ET
**不执行任何操作**，**只**读取 public artifacts/docs/current
conclusions/research logs/README 与 git metadata：

- 已提交的 N10ES public aggregate report（audit package）；
- 已提交的 N10ER public aggregate report（用于直接确认锁定事实，仅 public
  aggregate 字段）；
- N10ES/N10ER evaluator/workflow，仅用于 schema/status 校验（绝不执行——不
  rerun/recompute）；
- N10ES/N10ER EN/ZH docs、EN/ZH current-research-conclusions、EN/ZH
  research-log/summary 与 README public readback；
- git metadata：记录 N10ES 结果的 `8c04a0a` checkpoint，以及记录 N10ER 结果 /
  CI run `28457213423`（head `2e7894e`）的 `c8fd353` checkpoint。

禁止：任何 private reads（`.openlocus/research-private/`、`/tmp` rerun 路径、CI raw
logs、repo clones、raw candidates/orders/labels/paths/queries/tasks/repos、per-task
diagnostics、N10EO private rerun data），任何 CI rerun，任何
retrieval/recompute，任何 candidate generation，任何 selector/reranker execution，
任何 threshold tuning，任何 promotion，任何 runtime/default change 或任何
method-winner claim。

## N10ES / N10ER source lock

```text
n10es checkpoint: 8c04a0a
n10er checkpoint: c8fd353（记录 N10ER 结果的 git commit）
n10er CI run: 28457213423（head 2e7894e）
n10er status: n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10es status: n10es_public_safety_probe_audit_package_complete_n10et_authorized
n10es next_allowed_phase: BEA-v1-N10ET Public Safety Probe Design/Decision
n10eq checkpoint: 7963831（上游，来自 N10ES source lock）
n10ep checkpoint: 0a54b49（上游，来自 N10ES source lock）
n10eo checkpoint: 6f8eeda（上游）
n10es source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
source_locked: true
```

## 结果

```text
status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
self-test: 74 / 74
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
clone/build/search: false
n10es source locked: true
next allowed phase: BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
                   Route Design / Schema Preflight
```

## 锁定的 N10ER public aggregates（从 N10ES audit 重新确认；不 recompute）

```text
sample: public_task_count=80, scored_task_count=60, task_with_gold_count=40, repo_count=2
heldout overlap: overlap_zero（overlap_count=0）
citation validity: 7772 / 7772
arm aggregates（top10/top20/top50/top100，lost baseline top10）：
  baseline:  37 / 39 / 40 / 40（lost 0）
  full:      36 / 39 / 40 / 40（lost 1）
  guard:     38 / 39 / 40 / 40（lost 0）
  diffaware: 37 / 39 / 40 / 40（lost 1）
risk bucket: task_count=26
risk losses full/guard/diffaware: 0 / 0 / 0
guard_would_preserve_full_loss_count: 0
```

## Decision（BEA-v1-N10E safety-probe 分支收尾）

1. **BEA-v1-N10E / difference-aware 仍是 local same-source hypothesis。**
   difference-aware rule（`top5_novel_candidate_item_count >= 4` 选 guarded，否则
   full）在同源 N10DZ/N10EB sample 上达到 `13/60`，但在 N10EN public CI canary 上
   回归（`37/40` vs baseline `39/40`），且其 held-out safety signal 在 N10ER public
   CI sample 上未复现（risk bucket `26`，losses `0/0/0`）。它仍是 local same-source
   hypothesis，不是可迁移的方法。
2. **N10ER / N10ES 是有效 public held-out negative。** N10ER held-out public CI
   safety probe（CI run `28457213423`）在足够大的 risk bucket（`task_count=26`，
   full/guard/diffaware losses `0/0/0`，`guard_would_preserve_full_loss_count=0`）
   内复现零 baseline-displacement signal。N10ES 将其锁定为有效 research negative，
   不是 CI failure。(N10ER, N10ES) 这一对是 N10EO low-novelty full-displacement /
   guard-preservation safety signal 的有效 public held-out negative。
3. **不推广 guard/full/diffaware，不调阈值，不 rerun N10ER。** 不推广
   guard/full/diffaware，不调阈值，不 rerun N10ER，不执行 CI variant，不执行
   selector/reranker，不做新 policy experiment，不改 runtime/default，不 claim
   method-winner，不做 downstream/scaled retrieval，不发布 raw diagnostic。所有这类
   stop/go 字段均为 `false`。

## 下一 route —— BEA-v1-HAAE-R0（仅 design/schema preflight）

N10ET 设计（不执行）并 **只** 授权下一 route：**BEA-v1-HAAE-R0 —— Hierarchical
Actionable Evidence Acquisition Route Design / Schema Preflight**。HAAE-R0 只是
design/schema preflight：它设计 evidence-acquisition actions 如何按层次组织
（anchor / span-window / candidate-source / scheduler / safety-probe），同时保留
`EvidenceCore` 并在 current-source evidence 不可用时弃权，并在未来任何
execution-authorized 阶段开启之前 preflight 该 route 的 public schema、source
inputs、claim boundary 与 stop/go contract。

HAAE-R0 只读取 public artifacts/docs 与 git metadata：已关闭的 N10ES/N10ER/N10EQ/
N10EP/N10EO public aggregates、BEA-v1 actionability-matrix / trace-surface
contracts，以及 research-design schemas。它不进行任何 private reads、CI rerun、
retrieval/recompute、candidate generation 或 selector/reranker execution。

### HAAE-R0 明确的 non-identity

HAAE-R0 明确 **不是** 以下任何一项（每条 route record 与 stop/go record 都携带对应
的 non-identity boolean）：

- **not BEA-v1-A** —— 它不是 coverage-preserving selector route。
- **not selector-only** —— 它不是 selector-only design。
- **not selector/reranker execution** —— 它不执行 selector 或 reranker。
- **not P5** —— 它不是 P5 selector/reranker 阶段。
- **not runtime/default promotion** —— 它不改 runtime/default 行为。

## Risk controls

| Risk | Mitigation |
|---|---|
| promotion from a valid research negative | guard_full_diffaware_promotion_authorized_bool=false；method_winner_claim_authorized_bool=false；不推广任何 arm |
| hindsight threshold tuning from no-signal | threshold_tuning_authorized_bool=false；frozen rule 不变；任何 threshold design 必须使用 held-out public evidence |
| N10ER rerun creep | n10er_re_run_authorized_bool=false；ci_variant_execution_authorized_bool=false；recompute_authorized_bool=false；rerun_authorized_bool=false |
| HAAE-R0 漂移为 selector / P5 / runtime | 每条 HAAE-R0 route record 都带 non-identity booleans；selector_reranker_authorized_bool=false；runtime_default_change_authorized_bool=false；bea_v1_a_authorized_bool=false；p5_authorized_bool=false |
| runtime/default creep | runtime_default_change_authorized_bool=false；任何 HAAE route 保持 opt-in/eval-only；无 runtime 或 default 变更 |
| private diagnostic leakage | N10ET 只读取 public aggregate artifacts/docs/git metadata；forbidden_scan 阻断 raw per-task/paths/orders/labels 键与 private rerun 路径；aggregate_buckets_only_bool=true |
| aggregate overinterpretation from two cases / no-signal | N10ET 是 public-only 收尾 design/decision；无 promotion、无 rule change、无 method-winner claim；HAAE-R0 仅 design/schema-preflight |

## Pass/fail gates（20 个逻辑检查 / 21 条 artifact gate records，仅审计）

1. `n10es_public_source_locked` —— N10ES public report 已锁定，status 与所有锁定 aggregates 匹配。
2. `n10er_public_facts_locked` —— N10ER checkpoint / CI run / status 与锁定值匹配。
3. `n10es_metric_audit_no_recompute` —— metrics 从 N10ES audit 重新确认；不 recompute。
4. `n10et_no_threshold_tuning` —— frozen threshold 不变。
5. `n10et_no_method_winner_claim` —— 不推广 guard/full/diffaware。
6. `n10et_no_runtime_default_change` —— 收尾保持 public/eval-only。
7. `n10et_no_promotion_or_frozen_rule_change` —— 不 promotion，不改 rule。
8. `n10et_no_ci_rerun_retrieval_recompute_candidate_generation` —— 不 CI rerun、retrieval、recompute 或 candidate generation。
9. `n10et_no_private_input_read` —— 不读取 private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos 或 per-task diagnostics。
10. `n10et_no_selector_reranker_no_p5_no_bea_v1_a` —— 不 selector/reranker、不 P5、不 BEA-v1-A。
11. `n10et_no_n10er_rerun` —— 不 rerun N10ER。
12. `n10et_interpretation_consistent_with_locked_aggregates` —— 解释由锁定 aggregates 推出。
13. `n10es_stop_go_next_phase_match` —— N10ES 明确 handoff 到 N10ET。
14. `n10er_stop_go_next_phase_match` —— N10ER 明确 handoff 到 N10ES。
15. `docs_readback_match_gate` —— EN/ZH N10ET + N10ES docs 与锁定结果一致。
16. `readme_readback_match_gate` —— README 与锁定结果一致。
17. `current_conclusions_match_gate` —— EN/ZH current conclusions 与锁定结果一致。
18. `research_log_match_gate` —— EN/ZH research logs 与锁定结果一致。
19. `research_summary_match_gate` —— EN/ZH research summaries 与锁定结果一致。
20. `haae_r0_authorized_design_only_schema_preflight_gate` 加独立 artifact `haae_r0_non_identity_gate` —— 只授权 HAAE-R0 design/schema preflight，并带 non-identity booleans。

所有 gate 都是 aggregate-only，`gate_uses_gold_for_policy_bool=false`、
`gate_performs_ci_rerun_bool=false`、`gate_reads_private_input_bool=false`。

## Claim boundary

N10ET 是 public-only、aggregate-buckets-only、design/decision-only。所有
execution、rerun、retrieval、recompute、candidate generation、tuning、promotion、
runtime/default、method-winner、downstream/scaled retrieval、raw diagnostic
publication、selector/reranker、provider/model network、network-run、gold-for-policy
字段均为 `false`。`ci_rerun_bool=false`、`retrieval_recompute_bool=false`、
`promotion_claim_bool=false`、`candidate_generation_bool=false`、
`n10er_execution_authorized_bool=false`、`n10er_re_run_authorized_bool=false`。HAAE-R0
non-identity booleans（`haae_r0_not_bea_v1_a_bool`、`haae_r0_not_selector_only_bool`、
`haae_r0_not_selector_reranker_execution_bool`、`haae_r0_not_p5_bool`、
`haae_r0_not_runtime_default_promotion_bool`）全部为 `true`。

## Stop/go

N10ET **只**授权 **BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
Route Design / Schema Preflight** 交接（public-only，design-only，不执行）：
`haae_r0_design_only_schema_preflight_authorized_bool=true`，
`haae_r0_execution_authorized_bool=false`。它**不**授权：N10ET re-run、N10ES
re-run/audit、任何 execution、rerun、retrieval、recompute、candidate generation、
threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware
promotion、runtime/default changes、method-winner claims、downstream/scaled
retrieval、raw diagnostic publication、CI variant execution、selector/reranker、
BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为
`false`。

已关闭 N10E 分支的详细事实来源是
[`current-research-conclusions.md`](current-research-conclusions.md)，以及 per-phase
N10EO/N10EP/N10EQ/N10ER/N10ES docs。

## Workflow

- Design/decision helper：`eval/bea_v1_n10et_public_safety_probe_design_decision.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out`。它只读取 N10ES + N10ER
  public reports 与 public docs，不进行任何 execution/rerun/recompute/candidate
  generation。

## Artifact

- Helper：`eval/bea_v1_n10et_public_safety_probe_design_decision.py`
- Report：`artifacts/bea_v1_n10et_public_safety_probe_design_decision/bea_v1_n10et_public_safety_probe_design_decision_report.json`
