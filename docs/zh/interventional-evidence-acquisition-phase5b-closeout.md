# Interventional Evidence Acquisition Phase 5B Closeout

日期：2026-07-07

Status: `phase5b_public_repo_formal_validation_complete_no_claim`

Phase 5B 已完成 frozen public-repo formal validation。12 个 public repos 已 clone/lock 到 ignored `runs/` 下；public tasks 先在没有 labels 的情况下生成；120 个 hard tasks 只使用 public `task_bucket` 选择；labels 在 task freeze 后生成，并按 frozen `test_id` 过滤。

Runner 执行了 120 个 hard public tasks × 7 个 frozen labels。Private rows 只保留在 ignored `runs/` 下。Public report 仅包含 aggregate 信息：[`phase5b_public_repo_formal_validation_report.json`](../../artifacts/phase5b_public_repo_formal_validation/phase5b_public_repo_formal_validation_report.json)。

Result buckets：task count `count_hundred_to_task_cap`，repo count `count_target_repo_range`，row count `count_task_cap_to_row_cap`，best fixed local/acquisition `count_21_to_50`，acquisition rate `rate_25_to_50pct`，stop/abstain success `count_0`。

Interpretation：这是 frozen protocol 下的 nonzero local evidence-acquisition signal。它不是 method winner、lift、product、default、runtime、provider、remote-model 或 training claim。Candidate-found alone 不是 evidence；counted success 必须满足 current-source read/materialization/hash/currentness/task tie。下一步是在任何新 empirical phase 前写 closeout/no-claim summary。
