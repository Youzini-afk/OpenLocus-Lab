# Interventional Evidence Acquisition Phase 6B Repo-Heldout Strategy Screen

日期：2026-07-07

Status: `strategy_selection_screen_positive_no_claim`

Authorization: `confirmed_private_input_local_screen_only`

## 范围

Phase 6B 按 Phase 6A 冻结边界运行 tiny stdlib-only repo-heldout screen。它只在 `--confirm-private-input` 后读取 existing ignored Phase 5B private rows。它没有 fetch repositories、读取 source、创建 tasks、调用 providers 或 remote services、改变 release settings，也没有写 reusable artifact。

## Screen 形态

- Input：latest ignored Phase 5B private rows。
- Split：repo-heldout grouped folds。
- Labels：同 7 个 frozen Phase 5B labels。
- Feature shape：只使用 `action_label`。
- Controls：fixed-label control、shuffled-target control，以及 `stop`/`abstain` zero-success requirement。
- Public output：仅 aggregate buckets。

## Aggregate public result

Public report：[`phase6b_repo_heldout_strategy_selection_screen_report.json`](../../artifacts/phase6b_repo_heldout_strategy_selection_screen/phase6b_repo_heldout_strategy_selection_screen_report.json)。

Key buckets：task count `bucket_hundred_to_task_cap`，repo group count `bucket_six_to_twenty`，private row count `bucket_task_cap_to_row_cap`，main screen success `bucket_twenty_one_to_fifty`，main screen rate `rate_quarter_to_half`，fixed-label control success `bucket_twenty_one_to_fifty`，shuffled-target control success `bucket_nonzero_to_five`，shuffled-control comparison `above_shuffled_control_over_twenty`，stop/abstain success `bucket_zero`。

Interpretation：这是 frozen research route 的 action-label-only positive no-claim stability screen。它不识别 winning method、不估计 lift、不授权 release behavior、deployment behavior、remote-provider work、新 data collection，也不授权没有另行冻结边界的后续 empirical work。
