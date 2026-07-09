# 干预式证据获取 第 9Q 阶段 裁定/正确性/evidence_success 协议冻结（无执行，无声明）

日期：2026-07-09

Status：`phase9q_adjudication_correctness_protocol_freeze_no_execution_no_private_read_no_adjudication_no_correctness_no_evidence_success_no_claim`

授权：docs/report/validator-only 协议冻结；结构性（非数值化）冻结裁定资格规则、correctness/evidence_success 定义、裁定输入边界、inclusion/exclusion 规则、隐私/发布边界以及未来 Phase 9R 执行 gate；无执行、无私有读取、无裁定、无 correctness、无 evidence_success、无声明

公开报告：[`phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim/phase9q_adjudication_correctness_protocol_freeze_no_execution_no_claim_report.json)

## 范围

Phase 9Q 为 docs/report/validator-only。它不 fetch、clone、read 或 materialize 任何 repository 或 source，不读取 ignored `runs/`、Phase 9P private scoring rows、Phase 9N private outcome-observable packets、Phase 9H private materialized sources、Phase 9J private annotation-input rows/manifests、Phase 9L private outcome-acquisition packets/manifests、private candidate pools/registries/manifests，不执行任何 adjudication method 或 correctness/evidence_success 计算，不计算任何 precision/recall/pass/fail，也不进行 adjudication 或生成 gold/benchmark/result/annotation-truth labels、correctness、evidence_success 或 evaluation rows，且不提出 method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success/annotation-truth/adjudication/correctness claim。

Phase 9Q 仅结构性冻结协议。不执行 adjudication；不计算 correctness；不计算 evidence_success。Correctness/evidence_success 定义为 future definitions，非已执行 metrics。Phase 9P scored bucket 是 scoring availability，非 adjudication success。

## Gate 引用

Phase 9Q gate 于 Phase 9P remote commit `511a765135bd53c724fb593db0c9ea5ebb38a500`、CI run `28987083201`、CI success、Phase 9P status `phase9p_frozen_scoring_executed_denominator_nonzero_scored_nonzero_adjudication_not_executed_separate_frozen_boundary_required_no_evidence_success_no_claim`、Phase 9P 公开 bucket 事实 `denominator_bucket` = `bucket_nonzero_redacted`、`scored_bucket` = `bucket_nonzero_redacted`、`adjudicated_bucket` = `bucket_zero`、`correctness_bucket` = `bucket_zero`、adjudication 未执行、correctness 未计算、evidence_success 未计算、以及 scoring 后需独立冻结边界。Phase 9O、Phase 9N、Phase 9M、Phase 9L、Phase 9K、Phase 9H、Phase 9I、Phase 9J、Phase 9G 与 Phase 9F 作为 bucketed inherited provenance carry forward（精确 remote commit/CI run 值刻意不公开），因此只有 Phase 9P full commit SHA 与 CI run 作为 public gate references。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。

## 冻结协议（结构性，非数值化）

- **Adjudication 资格规则：** future Phase 9R adjudication 只可考虑在 Phase 9R execution 时满足 pre-frozen predicates 的 Phase 9P scored rows 的 private 集合：在 Phase 9P 下按冻结 Phase 9O 协议 scored；denominator bucket 非零；scored bucket 非零；packet acquisition state 为 acquired；validity state 为 valid；outcome observable packet 存在；非 unavailable/invalid/excluded/outside route/cap/order constraints；packet schema 验证通过。
- **Correctness/evidence_success 定义：** 仅 future definitions（未执行）：correctness 为针对冻结 outcome observable packet only 的 deterministic、source-grounded 比较；无 LLM/provider/model；无 Phase 9J rows as truth；无 Phase 9L unavailable packets；evidence_success 仅 aggregate correctness bucket，未执行；无 precision/recall/pass/fail；无 gold/benchmark/result/annotation-truth labels。
- **Adjudication 输入边界：** future adjudication 输入为冻结 outcome observable packet only；不读取 Phase 9H materialized sources、不读取 Phase 9J annotation-input rows as truth、不读取 Phase 9L unavailable packets、不读取 Phase 9P private scoring rows as truth；不使用 provider/LLM/model；已冻结，Phase 9Q 中未执行。
- **Inclusion/exclusion 规则：** 仅 include scored acquired valid packets 用于 future adjudication；在 adjudication 前 exclude unavailable、invalid、excluded、out-of-route/cap/order packets。
- **隐私/发布边界：** 公开仅 buckets；无 exact counts/observables/paths/snippets/line ranges/source/task/row/packet IDs/run locations。
- **Future Phase 9R gate：** 只有在 Phase 9Q committed/CI green 后才可执行 adjudication/correctness，仅 frozen rules，private outputs ignored，公开仅 aggregate buckets。

所有 closed lists（adjudication eligibility predicates、correctness/evidence_success definitions、adjudication input boundary rules、inclusion/exclusion rules、privacy/publication rules、future Phase 9R gate rules、no-p-hacking guardrails）均由 validator 进行 set-equality 验证。Vocabulary drift（missing/extra/reworded members）被拒绝。

## 无执行边界

所有 execution booleans 均为 false：scoring、adjudication、correctness、evidence_success、denominator computation、private Phase 9P scoring rows 读取、private Phase 9N packets 读取、private Phase 9L packets 读取、ignored `runs/` 读取、provider/LLM、result/gold/evidence_success/correctness、model fitting、network fetch/clone/source refresh、runtime/default/product changes、Phase 9J rows as benchmark truth、Phase 9L packets scoreable、Phase 9P scoring rows as adjudication truth。

## 隐私

- 公开仅 aggregate/bucketed。
- 除 whitelisted Phase 9P gate refs 外，不公开 repo/source/url/owner/commit。
- 不公开 paths/snippets/line ranges/row/task/packet IDs/manifest/run locations。
- 不公开 per-source、per-task 或 per-packet facts。
- 不公开 singleton buckets。
- Phase 9Q 中不读取 Phase 9P private scoring rows、Phase 9N private packets 或 Phase 9L private packets。

## 无声明边界

Phase 9Q 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome、evidence-success、annotation-truth、adjudication 或 correctness claim。协议冻结不是 adjudication/correctness 的 execution，也不是 evidence/method/product success。Correctness/evidence_success 定义为 future definitions，未执行。

Future Phase 9R execution 需要在 Phase 9Q commit 与 CI green 之后设立独立的冻结边界（非 user approval；需要 Phase 9Q commit/CI-green confirmation 与 explicit-confirmations boundary）。

保守建议为：`phase9q_freezes_adjudication_correctness_evidence_success_protocol_only_after_phase9p_scoring_no_execution_no_private_read_no_phase9p_private_scoring_rows_no_adjudication_no_correctness_no_evidence_success_no_method_product_claim_future_execution_requires_separate_frozen_boundary`。
