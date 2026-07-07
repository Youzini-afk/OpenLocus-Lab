# Interventional Evidence Acquisition Phase 4C Frozen Fresh-Holdout Protocol

日期：2026-07-07

Phase: `phase4c_frozen_fresh_holdout_protocol_design_only`

Status: `phase4c_frozen_fresh_holdout_protocol_design_only_no_execution`

本文只是 design。它不读取 private rows、不创建 manifests、不为新 evidence 读取 source、不收集 data、不训练或拟合 model、不改变 CI、不改变 runtime/default behavior、不新增 retrieval families，也不提出 method claim。

## 为什么需要它

Phase 4B 只是在既有 ignored Phase 2/3 private rows 上做了一个 small local screen。它没有证明 working model、method victory、lift、product readiness 或 default change。

下一个真实检查必须使用 fresh hard current-source tasks，且这些 tasks 不能来自 Phase 2、Phase 3 或 Phase 4B。Phase 4C 在任何执行前冻结 future holdout protocol，避免后续 Phase 4D 在同一批 private rows 上调参。

## Frozen basis

- Code/protocol basis commit：`6626075`。
- 只允许既有 7 个 labels：
  - `bm25_then_read_top1`
  - `bm25_then_read_next_unique_file`
  - `symbol_regex_then_read_top1`
  - `symbol_regex_then_read_next_unique_file`
  - `read_related_test_when_available`
  - `stop`
  - `abstain`
- Feature set 只允许：
  - `action_label`
  - `task_family_bucket`
  - `availability_bucket`
  - `budget_bucket`
- Screen method：stdlib-only smoothed categorical table，deterministic。
- 不使用 sklearn、numpy、torch、provider、network、LLM，也不创建 reusable model artifact。
- Fit source 必须是预先声明的 Phase 2 training rows，或另一个单独冻结的 source。
- 不得在 fresh holdout rows 上 fit 或 tune。
- Thresholds、control buckets、status values 和 validation rules 必须在读取 holdout rows 前固定。

## Future Phase 4D shape

- Target：12 个 fresh hard current-source tasks。
- Hard max：16 tasks。
- Fixed labels/actions：同上 7 个 labels。
- Private row cap：112 rows。
- Private manifest 和 private rows：只能在 ignored `runs/` 下。
- 如果 private check 可行，必须拒绝复用 Phase 2/3/4B tasks。

## Future public report fields

如果未来 Phase 4D 被单独授权，public output 只能包含 aggregate fields：

- coarse task 和 row buckets；
- screen bucket；
- shuffled/control buckets；
- evidence materialization pass bucket；
- overlap check bucket；
- privacy validation；
- conservative recommendation。

Public output 不得包含 private rows、task text、task IDs、exact paths、ranges、hashes、snippets、run directories、manifests、labels、prompts、responses 或 provider payloads。不得出现 exact `count_1` values。

## Future statuses

未来 Phase 4D statuses 只允许：

- `stop_no_learning_claim`
- `repair_holdout_contract_no_claim`
- `fresh_holdout_screen_positive_no_claim`

## Phase 4D result 被接受前必须验证

- 没有 `runs/` files staged。
- 如果 private check 可行，必须拒绝与 Phase 2/3 private tasks、paths、ranges 重叠。
- 读取 holdout rows 后，不得改变 feature、threshold 或 table。
- Evidence success 需要 real current-source read，加 private path/range/hash/currentness/range match 和 task tie。
- Candidate-found alone 不是 evidence。
- `stop` 和 `abstain` success 保持 `count_0`。
- Public report 必须拒绝 private references、exact `count_1` 和 claim terms。
- Public privacy audit 和 CI 在 public closeout 前必须为 green。

## Forbidden

- 不做 RPM-D2/model scaling。
- 不使用 LLM/provider/network。
- 不改变 runtime/default。
- 不新增 retrieval family。
- 不创建 reusable model artifact。
- 不在 holdout rows 上 training。
- 不在 holdout 后 tuning。
- 不提出 winner、lift、product、default 或 method claim。
- 不公开 private refs 或 raw rows。

## Phase 4C outcome

Phase 4C 只冻结 possible future Phase 4D 的设计。它本身不授权 Phase 4D 执行。

## Phase 4D execution note

Phase 4D 后续已按该 frozen protocol 作为 standalone local screen 运行。Public report：[`phase4d_frozen_fresh_holdout_report.json`](../../artifacts/phase4d_frozen_fresh_holdout/phase4d_frozen_fresh_holdout_report.json)。Status 为 `fresh_holdout_screen_positive_no_claim`。

Phase 4D result 仍是 no-claim。它使用 ignored private input/output，只发布 aggregate buckets，不创建 reusable model artifact，也不支持 winner、lift、product、default、provider/network 或 runtime claims。

## Phase 4E closeout pointer

Phase 4E 只使用 public Phase 4B/4C/4D reports/docs 来关闭这一 small-check sequence。参见 [`interventional-evidence-acquisition-phase4e-closeout.md`](./interventional-evidence-acquisition-phase4e-closeout.md)。它将路线保留为 research candidate，但在这里停止以避免 result-shopping；任何下一步 empirical work 都需要单独的 larger validation decision 或 independent replication protocol。
