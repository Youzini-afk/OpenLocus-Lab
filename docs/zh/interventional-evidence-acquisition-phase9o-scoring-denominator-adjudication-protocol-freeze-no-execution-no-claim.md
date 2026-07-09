# Interventional Evidence Acquisition Phase 9O Scoring/Denominator/Adjudication 协议冻结（无 execution，无 claim）

日期：2026-07-09

状态：`phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_private_read_no_scoring_no_claim`

授权：仅 docs/report/validator 协议冻结；结构性冻结 scoring-denominator eligibility、inclusion/exclusion、scoring-metric 定义、adjudication 协议、missing/invalid/unavailable 处理、privacy/publication 边界以及 future Phase 9P gate（非数值化）；无 execution、无 private reads、无 scoring、无 adjudication、无 denominator 计算、无 claim

公开报告：[`phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim/phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_claim_report.json)

## 范围

Phase 9O 仅为 docs/report/validator。它不 fetch、clone、read 或 materialize 任何 repository 或 source，不读取 ignored `runs/`、private candidate pools/registries/manifests、Phase 9H private materialized sources、Phase 9J private annotation-input rows/manifests、Phase 9L private outcome-acquisition packets/manifests 或 Phase 9N private outcome-observable packets/manifests，不执行任何 scoring route 或 adjudication method，不计算任何 scoring denominator 或 metric，也不进行 scoring、adjudication 或生成 gold/benchmark labels、evidence_success、result labels、annotation-truth、correctness 或 scoring/evaluation rows。它不提出 method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success/annotation-truth/adjudication/correctness claim。

Phase 9O 仅结构性冻结协议。不计算 denominator；不评估 metric；不执行 adjudication。Scoring-metric 定义是 future definitions，不是已执行的 metrics。Phase 9N `acquired_valid_bucket` 公开事实是 availability，不是 scoring success。

## Gate references

Phase 9O gate 于 Phase 9N remote commit `282a5037a106da55b6df67a33c42bb3ad7142836`、CI run `28985320043`、CI success、Phase 9N status `phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability_no_scoring_no_adjudication_no_claim`、Phase 9N 公开事实 `acquired_valid_bucket` = `bucket_nonzero_redacted` 以及 Phase 9N `phase9o_gate` 事实（phase9o 需要单独的 frozen boundary；只有在 acquired_valid bucket 非零时才可考虑 scoring protocol；Phase 9N 中 scoring/adjudication 保持 false）。Phase 9M、Phase 9L、Phase 9K、Phase 9H、Phase 9I、Phase 9J、Phase 9G 与 Phase 9F 作为 bucketed inherited provenance carry forward，其精确 remote commit/CI run 值刻意不在 Phase 9O report/docs 中公开（更严格的 privacy）。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。

## 冻结协议（结构性，非数值化）

- **Denominator eligibility rule：** future Phase 9P denominator 是在 Phase 9P execution 时满足 pre-frozen predicates 的 Phase 9N packets 的 private 集合：由单一 Phase 9M frozen route 在 Phase 9N gated run 期间生成；acquisition state 为 acquired；validity state 为 valid；expected evidence form 匹配 whitelist；source-grounding checks 通过；packet schema 验证通过；not unavailable/invalid/replacement-needed/malformed/duplicate/outside route/cap/order constraints。
- **Inclusion/exclusion rule：** 仅 include eligible valid acquired packets；在 scoring 前 exclude unavailable、invalid、replacement-needed、schema-invalid、duplicate 以及 out-of-route/cap/order packets。
- **Scoring metric definitions：** 一个仅包含 availability-to-score protocol metrics 的小型 closed list（denominator_bucket、scored_bucket、adjudicated_bucket、invalid_excluded_bucket、unavailable_excluded_bucket、correctness_bucket），均为 bucket-only future aggregate 定义，未执行。无 exact counts/rates，无 winner/effect/lift 语言。Correctness 与 adjudication metrics 明确为 future definitions，未执行。
- **Adjudication protocol：** 针对冻结 outcome observable packet 的 deterministic、source-grounded adjudication；无 LLM/provider/model；无 Phase 9J rows as truth；无 Phase 9L unavailable packets。
- **Missing/invalid/unavailable handling：** 非 failure/success/partial；在 scoring 前 excluded；仅 bucketed aggregate。
- **Privacy/publication boundary：** 公开仅 buckets；无 exact counts/observables/paths/snippets/line ranges/source/task/row/packet IDs/run locations。
- **Future Phase 9P gate：** 只有在 Phase 9O committed/CI green 后才可执行 scoring，仅 frozen rules，private outputs ignored，公开仅 aggregate buckets。

所有 closed lists（denominator eligibility predicates、inclusion/exclusion rules、scoring metric definitions、adjudication rules、missing/invalid/unavailable handling rules、privacy/publication rules、future Phase 9P gate rules、no-p-hacking guardrails）均由 validator 进行 set-equality 验证。Vocabulary drift（missing/extra/reworded members）被拒绝。

## No-execution boundary

所有 execution booleans 均为 false：scoring、adjudication、denominator computation、private Phase 9N packet reads、private Phase 9L packet reads、ignored `runs/` reads、provider/LLM、result/gold/evidence_success/correctness、model fitting、network fetch/clone/source refresh、runtime/default/product changes、Phase 9J rows as benchmark truth、Phase 9L packets scoreable。

## Privacy

- 公开仅 aggregate/bucketed。
- 除 whitelisted Phase 9N gate refs 外，无 repo/source/url/owner/commit。
- 无 paths/snippets/line ranges/row/task/packet IDs/manifest/run locations。
- 无 per-source、per-task 或 per-packet facts。
- 无 singleton buckets。
- Phase 9O 中不读取 Phase 9N 或 Phase 9L private packets。

## No-claim boundary

Phase 9O 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success、annotation-truth、adjudication 或 correctness claim。协议冻结不是 scoring/adjudication 的 execution，也不是 evidence/method/product success。Correctness/adjudication metrics 是 future definitions，未执行。

Conservative recommendation：`phase9o_freezes_scoring_denominator_adjudication_protocol_only_no_execution_no_private_read_no_scoring_no_claim_phase9p_may_execute_scoring_only_under_separate_frozen_boundary_no_method_product_claim`。
