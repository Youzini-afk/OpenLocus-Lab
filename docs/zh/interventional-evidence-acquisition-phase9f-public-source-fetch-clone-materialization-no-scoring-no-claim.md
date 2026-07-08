# Interventional Evidence Acquisition Phase 9F Public Source Fetch/Clone Materialization

日期：2026-07-09

Status：`phase9f_public_source_fetch_clone_materialization_repair_no_claim`

Authorization：public source fetch/clone materialization only，在 frozen Phase 9E protocol 之下

Public report：[`phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim_report.json)

## Scope

Phase 9F 只是 bounded public source fetch/clone materialization runner。它 gate 于 frozen Phase 9E protocol 及其 public gate references：Phase 9E remote commit `7f4ad8a`、CI run `28972733319`、CI success，以及 status `phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim`。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。

Execution 需要全部六个显式 confirmations：`--confirm-phase9e-commit 7f4ad8a`、`--confirm-phase9e-ci 28972733319`、`--confirm-public-source-fetch-clone`、`--confirm-ignored-runs-workspace`、`--confirm-no-labels-outcomes-scoring-evidence-success`，以及 `--confirm-no-provider-llm-model-default-runtime-change`。Dry self-test 与 report validation 不 fetch/clone、不读取 ignored `runs/`、不读取 private candidate pools。

## Materialization boundary

Phase 9F 只能将 public-only source repositories fetch/clone 进入 ignored `runs/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim/...` workspace，绝不进入 tracked artifacts。Private candidate source pools、manifests 与 materialization rows 只保留在 ignored `runs/` 之下。Public-source inputs 不嵌入 tracked source/docs/report；candidate source URLs（若有）只从 ignored `runs/` 下的 private candidate pool 读取。

Task candidates 只是 inventory。它们是 evidence-finding、file-localizable code-task candidates。它们不是 benchmark labels、outcomes、gold rows、success rows 或 evidence-success evaluations。Materialization 本身不是 evidence success。

## Deterministic construction rules

Candidate construction 使用 deterministic source order，不使用 random shuffle。Replacement 只在 labels/outcomes/scoring 之前发生：先考虑同一 source 的下一个 deterministic candidate，如需再考虑下一个 source。Replacement 不使用 performance、evidence、model 或 downstream feedback。

Phase 9E caps 保持不变：target task-candidate bucket 48-72，hard cap 最多 96，per-source cap 最多 8，minimum distinct sources 至少 8。如果 caps 之后 diversity 低于 minimum，Phase 9F 必须 stop 或 repair 而不是 pass。在接受任何 candidate 之前需要的 private materialization checks 包括 public access、license/access/default-branch/currentness/hash/reread checks，以及 file-localizable evidence-finding task shape。

## Public result

Public report 仅 aggregate-only。它包含 schema_version、phase、status、Phase 9E gate references、confirmation summary、materialization summary、source diversity summary、privacy summary、validation summary、no-claim boundary、forbidden execution boundary，以及 conservative recommendation。

当前 public status 为 `phase9f_public_source_fetch_clone_materialization_repair_no_claim`。Public aggregate buckets 显示 constructed inventory `bucket_zero`、materialized references `bucket_zero`、observed distinct sources `bucket_zero`，并且 source-reference currentness reread 在私有侧不可用。这是 failed materialization attempt/checkpoint，不是 pass。

Phase 9F 没有在 tracked source 中嵌入任何 remote source URL。ignored `runs/` 下没有可用的 private candidate source pool，并且 public fetch/clone 无法在 caps 之下 materialize 任何 source，因此 materialization 在 caps 之后保持为零。Zero-materialization repair state 被保留而不是 in-place 修复。在 observed materialization failure 之后没有发生 in-place tuning/cap 或 source selection。这只是 source-materialization readiness failure，不是任何 evidence-acquisition method 成功或失败的证据。

Private manifests 只保留在 ignored `runs/` 之下；public report 不包含 exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts，也不包含 exact singleton buckets。Public report 中唯一的 commit/CI 值是 Phase 9E public gate references（`7f4ad8a`、`28972733319`）。

## No-claim boundary

Phase 9F 不执行 strategy scoring、labels、outcomes、evidence-success evaluation、model fitting/training、provider/LLM calls、runtime/default/product changes，也不提出 method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claim。未发生 provider/LLM/model/default/runtime change。

Task rows（若未来 boundary 将其 materialize）仍只是 candidate inventory。它们不是 labels、outcomes、gold rows、success rows 或 evidence_success。Materialization 本身不是 evidence_success。Future strategy scoring 需要另一个 frozen boundary。
