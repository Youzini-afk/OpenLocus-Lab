# Interventional Evidence Acquisition Phase 9G Candidate Source-Pool Network-Fetch Protocol Freeze

日期：2026-07-09

Status：`phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization：docs/report/validator-only protocol freeze

Public report：[`phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim/phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9G 是 docs/report/validator-only protocol freeze。它在 Phase 9F public-source fetch/clone materialization repair/no-claim checkpoint 之后冻结 future candidate-source-pool schema 与 future Phase 9H network-fetch implementation contract。它不 fetch、clone、read 或 materialize 任何 repository 或 source。它不读取 ignored `runs/` 或 private candidate pools/registries/manifests。它不生成 task rows、labels、outcomes、scoring rows 或 evidence_success。它不提出 method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim。

Phase 9G gate 于 Phase 9F remote commit `c091b742`、CI run `28973602930`、CI success 以及 Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim`。它记录 Phase 9F 是 repair/no-claim，且 NOT proof public fetch/clone 或 materialization works：Phase 9F 观察到 zero buckets 与 `public_source_fetch_clone_executed=false`。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。Future execution 在 Phase 9G contract 下需要 Phase 9G commit 与 CI green。

## Frozen candidate-source-pool schema

Frozen future candidate-source-pool schema 要求：

- Bounded public source pool only。
- License、access、default-branch 与 currentness fields。
- Deterministic source order field。
- Retry/timeout/failure bucket fields。
- Clone target mapping 只在 ignored `runs/` 之下。
- No credentials、auth-prompt、private-host 或 local-fallback fields。
- No repo name、URL、owner、commit、path、hash、snippet、row ID、run-dir、per-source 或 per-task fields。

## Frozen Phase 9H network-fetch implementation contract

Frozen future Phase 9H contract 要求：

- Public-only HTTPS 或 git fetch/clone，仅在显式 confirmation 下进行。
- Fetch/clone 只进入 ignored `runs/` workspace，不进入 tracked artifacts。
- No credentials、auth prompts、private hosts 或 local fallback。
- Deterministic source order，不使用 random shuffle。
- Bounded public source pool only。
- Fail closed on redirect ambiguity。
- Fail closed on auth prompt。
- Fail closed on private host。
- Fail closed on missing license、access 或 default branch。
- Fail closed on hash 或 currentness mismatch。
- Fail closed on inaccessible source。
- Retry/timeout/failure buckets 仅 aggregate-only。
- Clone target mapping 只在 ignored `runs/` 之下。
- License/access/default-branch/currentness fields 在任何 acceptance 之前。
- Privacy redaction rules 仅 aggregate-only。
- Aggregate public report only：不包含 repo names、URLs、owners、commits、paths、snippets、hashes、row IDs、run dirs 或 singleton buckets。
- Task-candidate target bucket 48-72，hard cap 最多 96，per-source cap 最多 8，minimum distinct sources 至少 8。
- Stop 或 repair 如果 zero materialization 在 caps 之后发生。
- Stop 或 repair 如果 source diversity 在 caps 之后低于 minimum。
- No replacement 或 tuning 基于 labels、outcomes、evidence_success、model 或 downstream-performance feedback。
- Task types 仅限于 evidence-finding file-localizable code tasks。
- Provider/LLM tasks forbidden。
- 不公开 unit per-source 或 per-task reporting。
- No hidden GitHub API substitute，除非 future protocol 显式 allow 或 forbid。
- Future strategy scoring 需要另一个 frozen boundary。

## No-claim boundary

Phase 9G 不提出 method、product、performance、training、provider、model、runtime、default、scoring、outcome 或 evidence-success claim。Frozen contract 仅 aggregate-bucketed。Public output 不包含 repo names、source names、URLs、owners、commits、hashes、paths、snippets、task IDs、row IDs、manifest locations、run locations、per-source facts、per-task facts 或 singleton buckets。Phase 9G 不暗示 fetch/clone、materialization 或任何 evidence-acquisition method works；Phase 9F repair/no-claim 不是 fetch/clone 或 materialization 成功的 proof。
