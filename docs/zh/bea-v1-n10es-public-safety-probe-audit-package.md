# BEA-v1-N10ES Public Safety Probe Audit/Package

日期：2026-06-30

BEA-v1-N10ES 是 **public safety probe audit/package** —— 对 BEA-v1-N10ER
bounded public CI score/guard safety probe 结果的 public-only、不执行任何操作的
审计。它**只**读取 N10ER public aggregate report（+ N10ER
evaluator/workflow，仅用于 schema/status 校验，绝不执行——不 rerun/recompute）
以及 git metadata（记录 N10ER 结果的 `c8fd353` checkpoint 与 CI run
`28457213423`）。它**不**进行任何 CI rerun、retrieval、recompute、clone、build
或 search，不读取 private directories、CI raw logs、repo clones、raw
candidates/orders/labels/paths/queries/tasks/repos、per-task diagnostics 或
N10EO private rerun data。

## 结果

```text
status: n10es_public_safety_probe_audit_package_complete_n10et_authorized
self-test: 31 / 31
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
clone/build/search: false
n10er source locked: true
next allowed phase: BEA-v1-N10ET Public Safety Probe Design/Decision
```

## N10ER source lock

N10ES 从 N10ER public report 与 git metadata 锁定 N10ER 结果：

```text
n10er checkpoint: c8fd353（记录 N10ER 结果的 git commit）
n10er CI run: 28457213423（head 2e7894e）
n10er status: n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10eq checkpoint: 7963831（上游，来自 N10ER source lock）
n10ep checkpoint: 0a54b49（上游，来自 N10ER source lock）
n10eo checkpoint: 6f8eeda（上游）
n10er report scan: pass
n10er stop/go n10es_audit_authorized: true
source_locked: true
```

## Metric audit（从 N10ER public report 重新表达；不 recompute）

N10ES 重新表达 N10ER aggregate metrics 并确认每一项与锁定值匹配——不 recompute
任何东西：

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

所有 metric audit 的 `metric_match_bool=true`；每条 metric record 的
`recomputed_bool=false`。

## Interpretation

```text
interpretation_bucket: valid_research_negative
risk_bucket_sufficient: true（task_count=26 >= 5）
signal_reproduced: false
signal_not_reproduced: true
ci_failure: false
not_ci_failure: true
```

risk bucket 足够大（`task_count=26`），但 bucket 内 full/guard/diffaware 都丢失
`0` 个 baseline top-10 hits，`guard_would_preserve_full_loss_count=0`，所以
low-novelty + strong-baseline full-displacement / guard-preservation safety
signal 未复现。这是**有效 research negative，不是 CI failure**。N10ER workflow
只在 contract/privacy/build/clone 失败时失败，不在有效的 no-signal 或
inconclusive research 结果上失败。

## Pass/fail gates（13，仅审计）

1. `n10er_public_source_locked` —— N10ER public report 已锁定，status 与所有锁定 aggregates 匹配。
2. `n10er_metric_audit_no_recompute` —— metrics 从 public report 重新表达；不 recompute。
3. `n10es_no_threshold_tuning` —— frozen threshold 不变。
4. `n10es_no_method_winner_claim` —— 不 promotion guard/full/diffaware。
5. `n10es_no_runtime_default_change` —— 审计保持 public/eval-only。
6. `n10es_no_promotion_or_frozen_rule_change` —— 不 promotion，不改 rule。
7. `n10es_no_ci_rerun_retrieval_recompute` —— 不 CI rerun、retrieval、recompute。
8. `n10es_no_private_input_read` —— 不读取 private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos 或 per-task diagnostics。
9. `n10es_interpretation_consistent_with_locked_aggregates` —— 解释由锁定 aggregates 推出。
10. `n10er_stop_go_next_phase_match_gate` —— N10ER 明确 handoff 到 N10ES。
11. `docs_readback_match_gate` —— EN/ZH N10ER docs 与锁定结果一致。
12. `readme_readback_match_gate` —— README 与锁定结果一致。
13. `current_conclusions_match_gate` —— EN/ZH current conclusions 与锁定结果一致。

所有 gate 都是 aggregate-only，`gate_uses_gold_for_policy_bool=false`、
`gate_performs_ci_rerun_bool=false`、`gate_reads_private_input_bool=false`。

## Claim boundary

N10ES 是 public-only、aggregate-buckets-only、design/decision-only。所有
execution、rerun、retrieval、recompute、tuning、promotion、runtime/default、
method-winner、downstream/scaled retrieval、raw diagnostic publication、
selector/reranker、provider/model network、network-run、gold-for-policy 字段均为
`false`。`ci_rerun_bool=false`、`retrieval_recompute_bool=false`、
`promotion_claim_bool=false`、`n10er_execution_authorized_bool=false`、
`n10er_re_run_authorized_bool=false`。

## Stop/go

N10ES **只**授权 **BEA-v1-N10ET Public Safety Probe Design/Decision**
交接（public-only，design/decision-only）：
`n10et_design_decision_authorized_bool=true`。它**不**授权：N10ES re-run、任何
execution、rerun、retrieval、recompute、threshold tuning、新 policy experiments、
frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、
method-winner claims、downstream/scaled retrieval、raw diagnostic publication、
CI variant execution、selector/reranker、provider/model network 或 network
runs。所有这类 stop/go 字段均为 `false`。

## Workflow

- 审计 helper：`eval/bea_v1_n10es_public_safety_probe_audit_package.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out`。它只读取 N10ER public
  report JSON，不进行任何 execution/rerun/recompute。

## Artifact

- Helper: `eval/bea_v1_n10es_public_safety_probe_audit_package.py`
- Report: `artifacts/bea_v1_n10es_public_safety_probe_audit_package/bea_v1_n10es_public_safety_probe_audit_package_report.json`
