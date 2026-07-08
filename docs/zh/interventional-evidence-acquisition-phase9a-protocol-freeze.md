# Interventional Evidence Acquisition Phase 9A Protocol Freeze

日期：2026-07-09

Status: `phase9a_protocol_freeze_no_execution_no_claim`

Authorization: `protocol_freeze_only_docs_report_no_execution_no_claim`

Public report: [`phase9a_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase9a_protocol_freeze_no_execution_no_claim/phase9a_protocol_freeze_no_execution_no_claim_report.json)

## 范围

Phase 9A 仅是 protocol-freeze-only public documentation 与 aggregate public report。它不是 Phase 8B 的 continuation、repair、completion 或 direct execution。它只使用已经公开的 Phase 8B/8C aggregate facts 作为动机：Phase 8B 在 frozen cap 下 did not pass into scoring eligibility，Phase 8C 在 public closeout 后停止 current Phase 8 construction attempt。

Phase 9A 未发生 private reads、ignored `runs/` reads、manifest reads、Phase 8B private registry 或 pool reads、Phase 8B accepted/rejected repository inspection、repository fetch/clone、source reads、task generation、candidate registry population、candidate pool construction、data collection、row/outcome scoring、labels、evidence-success evaluation、model fitting、provider 或 LLM calls、runtime/default/product changes、direct Phase 9 execution，也未 repair Phase 8B accepted-repository count。

## Frozen clean-room source-universe rule

Future Phase 9B source-list construction 必须是 clean-room。Phase 9B source list 必须在不读取 Phase 8B private pool、manifests、registry、logs、provenance、accepted candidates、rejected candidates、near misses 或任何其他 Phase 8B private material 的情况下生成。

因为 Phase 9A 不能读取 Phase 8B private registry，所以它不声称任何 reuse 已 checked safe。相反，frozen anti-laundering rule 排除 reuse 所有 Phase 8B private material。

## Predeclared acquisition recipe

Future Phase 9B 只能在该 frozen recipe 下使用 neutral public acquisition channels。Channel order 在任何 inspection 前固定为：

1. `public_language_registry_top_projects_index`；
2. `public_ecosystem_topic_index`；
3. `public_package_metadata_dependents_index`。

Manual named seed repositories、private candidate sources 与 prior-phase candidate sources 都被禁止。

每个 channel 内部的 ordering 是 deterministic，并按以下 public metadata keys 排序：normalized public project identity ascending、stable public-metadata rank ascending、default-branch name ascending、channel-local index ascending。Seed label `phase9a_clean_room_public_seed_v1` 只是 version label；randomness、random shuffle 与 post-hoc resampling 都被禁止。

Frozen quotas 为：accepted-source target 12、later audit pass 的 minimum accepted sources 8、total candidate inspection cap 48、per-channel inspection cap 16、initial per-channel quota 16。Eligibility 必须在 scoring 前、只基于 public metadata/materialization facts 决定：public accessibility without authentication、source archive materializable before scoring、declared or publicly auditable license、default branch or equivalent revision resolvable、in-scope language/file mix detectable from public metadata，以及不是 private/prior-phase/manual named seed material。

Replacement 是 deterministic：unavailable 或 ineligible source 用同一个 frozen channel stream 中下一个尚未 inspected 的 item 替换；如果该 stream exhausted，则按 frozen channel order round-robin 到下一个 channel。Replacement 必须发生在任何 scoring、labels 或 outcomes 之前，并且不得使用 performance、outcome、evidence-success 或 Phase 8B private feedback。Performance-based replacement 被禁止。

## Identity normalization before inspection

Future Phase 9B 必须在 source inspection 前 normalize public project identity、deduplicate candidate identities，并在 publicly available 时检查 public fork/mirror equivalence。这些 identity checks 只使用 public metadata，并且必须发生在 inspection 或 availability decisions 之前。

## Availability-first gate

Availability 是 scoring 前的 gate，不是 scoring result。Future Phase 9B 必须在 scoring 前检查 access、license/materialization feasibility 与 availability。Unavailable sources 必须按 frozen replacement rules 在 scoring 前替换。

## Privacy contract

Public output 保持 aggregate-only。不得公开 repository names、URLs、owners、commits、paths、hashes、snippets、task IDs、row IDs、manifest paths、run directories、singleton buckets 或 per-repository/per-task facts。

## Hard stops

如果发生或需要以下任一情况，protocol 必须停止：

- 任何读取 Phase 8B private material 的尝试；
- identity normalization 未在 inspection 前完成；
- availability gate 未在 scoring 前完成；
- ordering、quota 或 replacement-rule drift；
- public reporting 需要 exact private 或 source identifiers；
- later audit passes 前发生任何 scoring。

## Future Phase 9B boundary

Phase 9B 只能在该 frozen protocol 下 construct 与 audit candidate sources。Scoring 在 later audit passes 且另行授权前仍被禁止。Phase 9A 本身不授权 direct Phase 9 execution，也不提出 method、product、performance、training、provider、model、scoring、outcome、evidence-success、runtime、default 或 deployment claim。
