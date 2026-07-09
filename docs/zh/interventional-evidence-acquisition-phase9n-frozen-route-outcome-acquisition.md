# Interventional Evidence Acquisition Phase 9N 冻结路由 outcome-observable 获取（仅 availability）

日期：2026-07-09

状态：`phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability_no_scoring_no_adjudication_no_claim`

授权：仅执行 Phase 9M 冻结的 outcome-observable 获取路由；private outputs 只在 ignored `runs/` 之下；公开仅 aggregate availability report；无 scoring、无 adjudication、无 gold labels、无 evidence_success、无 result labels、无 claim

公开报告：[`phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim_report.json`](../../artifacts/phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim/phase9n_frozen_route_outcome_acquisition_no_scoring_no_claim_report.json)

## 范围

Phase 9N 只执行由 Phase 9M outcome-observable 获取路由协议冻结的单一路由。只有一条固定路由；无 fallback、无 retry、无 trying-routes-until-one-works、无 route-order drift。Phase 9N 在 ignored `runs/` 之下读取 Phase 9H private materialized sources（实际 source 内容），在 ignored `runs/` 之下读取 Phase 9J private annotation-input rows（仅作为 routing/precondition metadata，NOT benchmark truth），只从 Phase 9H materialized sources 进行 deterministic manual extraction（无 LLM、无 provider、无 model inference 或 judgment），只在 ignored `runs/` 之下生成 private outcome-observable packets/manifests，并只发布 aggregate/bucketed public availability report。

Phase 9N 不进行 scoring、adjudication、gold labels、benchmark labels、evidence_success、correctness、precision/recall、pass/fail、result labels、provider/LLM/model/network/fetch/clone/source refresh、model fitting/training、runtime/default/product changes，也不提出 method/product/performance/provider/model claim。Phase 9N 不读取 Phase 9L private outcome packets。Phase 9N 不将 Phase 9J annotation-input rows 作为 benchmark truth（仅 routing/precondition metadata）。Phase 9N 中不存在 scoring denominator。

Phase 9N gate 于 Phase 9M remote commit `0b0356b43d98edad0a3483132bdfae12ed520bb9`、CI run `28983935272`、CI success、Phase 9M status `phase9m_outcome_observable_acquisition_route_protocol_freeze_no_execution_no_scoring_no_adjudication_no_claim` 以及 Phase 9M protocol freeze。Phase 9L remote commit `c815a77d4dea3b77efe5dae0abe06006045294e9`、CI run `28983185765`、Phase 9L status `phase9l_outcome_acquisition_executed_unavailable_only_no_scoring_no_adjudication_no_claim`、Phase 9K remote commit `233a16e6672b05b87b09be5b920f8fc9dd72e274`、CI run `28981994749` 以及 Phase 9K status `phase9k_outcome_scoring_protocol_freeze_no_claim` 作为 secondary gate references 从 Phase 9M 公开报告 carry forward。Phase 9H、Phase 9I、Phase 9J、Phase 9G 与 Phase 9F 作为 bucketed inherited provenance carry forward，其精确 remote commit/CI run 值刻意不在 Phase 9N report/docs 中公开。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。Execution 需要全部十六个显式 confirmations。

## 冻结路由执行

冻结路由是单一固定 deterministic route（无 fallback、无 retry、无 LLM、无 provider）。closed route vocabulary（authorized private inputs、extraction procedure、observable definition、invalid/unavailable criteria、replacement rule、stop rule、route-order/fallback rule）与 Phase 9M 公开报告的 frozen lists 进行 set-equality 验证。

- **Deterministic manual extraction：** outcome observable 是来自 authorized Phase 9H materialized source 的 directly-readable、source-grounded fact。expected evidence form 是 `file_path_and_line_range_only_no_snippet_stored`：materialized source file 存在于 candidate path、可读、且 line range [start, end] 在文件行数内有效。不存储 snippet。
- **Acquisition states：** `acquired`（文件存在、可读、line range 有效、evidence form 匹配）；`unavailable`（文件 absent/unreadable 或 line range 超出文件行数）；`invalid`（observable malformed、not source-grounded、ambiguous 或超出 whitelisted evidence form — 需要 replacement，仅 next deterministic candidate）。
- **Deterministic ordering：** candidate 按 `candidate_order_index_private` 升序处理。每个 Phase 9H row 通过 `candidate_order_index_private` 与其 Phase 9J annotation-input row 匹配。无随机 shuffle。
- **无 provider/LLM/model：** outcome-observable 获取中无 LLM、无 provider calls、无 model inference 或 judgment。

## Availability buckets

公开报告只发布 availability buckets。Buckets 为 `bucket_zero` 或 `bucket_nonzero_redacted` — 无 exact counts、无 per-source/per-task facts、无 singleton buckets。

- `attempted_bucket`：outcome-observable 获取尝试数（bucketed）。
- `acquired_valid_bucket`：acquired-and-valid outcome observables 数（bucketed）。
- `unavailable_bucket`：unavailable outcomes 数（bucketed）。
- `invalid_rejected_bucket`：invalid-rejected outcomes 数（bucketed）。
- `replacement_needed_bucket`：需要 replacement 的 outcomes 数（bucketed）。
- `distinct_sources_bucket`：有 outcome packets 的 distinct sources 数（bucketed）。

Unavailable 与 invalid outcomes 不被计为 failure、success 或 partial。Phase 9N 中不存在 scoring denominator。

## Phase 9O gate

Phase 9O scoring protocol/denominator freeze 只有在 `acquired_valid_bucket` 非零时才可被考虑。Scoring 与 adjudication 在 Phase 9N 中保持 false。Phase 9O 需要单独的 frozen boundary。

## Privacy

- 公开仅 aggregate/bucketed。
- 除 whitelisted Phase 9M、Phase 9L 与 Phase 9K gate refs 外，无 repo/source/url/owner/commit。
- 无 path/snippet/row/task/manifest/run locations。
- 无 per-source 或 per-task facts。
- 无 singleton buckets。

## No-claim boundary

Phase 9N 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success、annotation-truth、adjudication 或 correctness claim。Outcome acquisition 不是 scoring、不是 adjudication、不是 evidence_success、不是 method success、不是 benchmark success、不是 product readiness。Phase 9N 不是 product readiness。

Conservative recommendation：`phase9n_executes_frozen_route_availability_only_acquisition_state_not_scoring_not_adjudication_not_evidence_success_future_scoring_and_adjudication_require_separate_frozen_boundary_no_method_product_claim`。
