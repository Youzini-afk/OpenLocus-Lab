# Interventional Evidence Acquisition Phase 6B Repo-Heldout Strategy Screen

Date: 2026-07-07

Status: `strategy_selection_screen_positive_no_claim`

Authorization: `confirmed_private_input_local_screen_only`

## Scope

Phase 6B ran the frozen Phase 6A tiny stdlib-only repo-heldout screen. It used existing ignored Phase 5B private rows only after `--confirm-private-input`. It did not fetch repositories, read source, create tasks, call providers or remote services, change release settings, or write a reusable artifact.

## Screen shape

- Input: latest ignored Phase 5B private rows.
- Split: repo-heldout grouped folds.
- Labels: the same seven frozen Phase 5B labels.
- Feature shape: `action_label` only.
- Controls: fixed-label control, shuffled-target control, and zero-success requirement for `stop`/`abstain`.
- Public output: aggregate buckets only.

## Aggregate public result

Public report: [`phase6b_repo_heldout_strategy_selection_screen_report.json`](../../artifacts/phase6b_repo_heldout_strategy_selection_screen/phase6b_repo_heldout_strategy_selection_screen_report.json).

Key buckets: task count `bucket_hundred_to_task_cap`, repo group count `bucket_six_to_twenty`, private row count `bucket_task_cap_to_row_cap`, main screen success `bucket_twenty_one_to_fifty`, main screen rate `rate_quarter_to_half`, fixed-label control success `bucket_twenty_one_to_fifty`, shuffled-target control success `bucket_nonzero_to_five`, shuffled-control comparison `above_shuffled_control_over_twenty`, and stop/abstain success `bucket_zero`.

Interpretation: this is an action-label-only positive no-claim stability screen for the frozen research route. It does not identify a winning method, estimate lift, authorize release behavior, deployment behavior, remote-provider work, new data collection, or further empirical work without a separately frozen next boundary.
