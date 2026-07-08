# Interventional Evidence Acquisition Phase 6A Strategy-Selection Screen Protocol Freeze

日期：2026-07-07

Status: `phase6a_strategy_selection_screen_protocol_freeze_no_claim`

Authorization: `design_only_no_execution`

## 范围

Phase 6A 冻结 possible later Phase 6B tiny strategy-selection screen protocol。它只是 design-only：不读取 ignored Phase 5B rows、不读取 source、不创建 tasks 或 repositories、不拟合 model，也不执行 screen。

## 冻结的 Phase 6B screen 形态

- Input source：只使用 existing ignored Phase 5B rows，且必须等 Phase 6A 已提交并通过 CI，并在现有低资源、无结论声明约束下显式进入 Phase 6B 边界后才能读取。
- Scale：tiny repo-heldout screen。
- Labels：精确复用 Phase 5B 的同 7 个 frozen labels：
  1. `bm25_then_read_top1`
  2. `bm25_then_read_next_unique_file`
  3. `symbol_regex_then_read_top1`
  4. `symbol_regex_then_read_next_unique_file`
  5. `read_related_test_when_available`
  6. `stop`
  7. `abstain`
- Split：repo-heldout，fit/check slices 之间没有 repository overlap。
- Implementation：stdlib-only tiny screen，只使用 pre-action aggregate/action fields。
- Baselines：action-only table、shuffled repo-heldout control、fixed-label controls。

## Evidence 与 public reporting boundary

Phase 6B 如后续在现有低资源、无结论声明约束下被显式进入，只能发布 aggregate buckets。不得公开 raw row contents、raw task IDs、paths、ranges、hashes、snippets、run directories、manifests、per-repo details、per-task details 或 singleton buckets。

任何 future screen 都只是 no-claim stability check，用于判断 tiny stdlib-only policy shape 是否值得作为 research machinery 保留。它不是 release、readiness、promotion 或 deployment claim。

## Hard stops

如发生 Phase 6A private/source read、新 task/repo creation、Phase 6A model fit、Phase 6A execution、slices 之间 repo overlap、label drift、public private leak、singleton public bucket、`stop`/`abstain` 非零 success、post-outcome tuning，或新增 remote/provider work，则在 future Phase 6B attempt 前或执行中 stop。

## 当前状态

Phase 6A 已作为 design-only protocol freeze 完成。Phase 6B runner 或 screen work 只能在 Phase 6A 已提交并通过 CI，并在现有低资源、无结论声明约束下显式进入 Phase 6B 边界后继续。
