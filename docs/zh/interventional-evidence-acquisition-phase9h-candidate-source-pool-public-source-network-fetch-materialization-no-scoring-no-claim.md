# Interventional Evidence Acquisition Phase 9H Candidate Source-Pool Public-Source Network-Fetch Materialization

日期：2026-07-09

Status：`phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`

Authorization：candidate source-pool public-source network-fetch materialization only，under the frozen Phase 9G candidate-source-pool network-fetch protocol

Public report：[`phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim_report.json)

## Scope

Phase 9H 是 bounded candidate source-pool public-source network-fetch materialization runner only。它 gate 于 frozen Phase 9G candidate-source-pool network-fetch protocol 及其 public gate references：Phase 9G remote commit `130b6732`、CI run `28974306775`、CI success 以及 status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`。Phase 9F public gate references（remote commit `c091b742`、CI run `28973602930`、CI success、Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim`）也被 carry forward。Local same-tree git commits 不被读取或比较；supplied confirmation 值只与 frozen public gate constants 比对。

Execution 需要全部 nine 个 explicit confirmations：`--confirm-phase9g-commit 130b6732`、`--confirm-phase9g-ci 28974306775`、`--confirm-public-source-network-fetch`、`--confirm-ignored-runs-workspace`、`--confirm-allow-public-github-api-transport`、`--confirm-no-private-or-local-fallback`、`--confirm-no-labels-outcomes-scoring-evidence-success`、`--confirm-no-provider-llm-model-default-runtime-change` 以及 `--confirm-aggregate-public-report-only`。Dry self-test 与 report validation 不 fetch/clone、不 hit network、不读取 ignored `runs/`、不读取 private candidate pools、不读取 materialized sources。

## Transport boundary

Phase 9H 只使用 unauthenticated public GitHub API transport，在 aggregate transport bucket 中 declared。Allowed：unauthenticated public GitHub REST/API metadata fetch、tree/content fetch 以及 public raw content fetch。Forbidden：hidden GitHub API fallback、authenticated API/tokens/credentials/auth prompts、private repos、使用 API 绕过 privacy/currentness/license/default-branch checks、transport comparison claims。如果 API rate limits 需要 auth，Phase 9H stop repair/no-claim。Redirect ambiguity 执行 fail-closed：redirects 只跟随到已知 public GitHub hosts。不使用 credentials、auth prompts、private hosts 或 local fallback。

## Materialization boundary

Phase 9H 可以通过 unauthenticated public GitHub API transport 将 public-only source repositories fetch 到 ignored `runs/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim/...` workspace only，不进入 tracked artifacts。Private candidate source pools、manifests 与 materialization rows 只留在 ignored `runs/` 之下。Public-source inputs 不嵌入 tracked source/docs/report；candidate source identities 如果有，只从 ignored `runs/` 之下的 private candidate pool 读取或创建。

Task candidates 是 inventory/readiness rows only。它们是 evidence-finding、file-localizable、code-task-shaped。它们不是 benchmark labels、outcomes、gold rows、success rows 或 evidence-success evaluations。Materialization 本身不是 evidence success。Readiness 仅指 source-materialization readiness。它不是 evidence success、method success、benchmark success、scoring success 或 product readiness。

## Deterministic construction rules

Candidate construction 使用 deterministic source order，不使用 random shuffle。Replacements 只在 labels/outcomes/scoring 之前发生：先考虑同一 source 的下一个 deterministic candidate，然后如需再考虑下一个 source。Replacement 不使用 performance、evidence、model 或 downstream feedback。

Phase 9G caps 保持 exact：max source candidates considered 16、target accepted materialized candidate bucket 48-72、hard candidate/materialization attempt cap 96、per-source accepted candidate cap 8、minimum accepted distinct public sources 8、per-source transport attempts initial attempt + one fixed retry only。在 observing success/failure 之后不发生 dynamic cap changes。如果 diversity 在 caps 之后低于 minimum，Phase 9H 必须 stop 或 repair 而非 pass。在接受任何 candidate 之前需要的 private materialization checks 包括 public access、license/access/default-branch/currentness/hash/reread checks 以及 file-localizable evidence-finding task shape。

## Public result

Public report 是 aggregate-only。它包含 schema_version、phase、status、Phase 9F 与 Phase 9G gate references、confirmation summary、candidate-source-pool schema summary、transport summary bucketed only、materialization summary bucketed only、source diversity summary bucketed only、retry/timeout/failure buckets aggregate only、privacy summary、no-claim boundary all false、forbidden execution boundary all false、validation summary 以及 conservative recommendation。

当前 public status 为 `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`。Public aggregate buckets 显示 constructed inventory `bucket_target_48_to_72`、materialized references `bucket_target_48_to_72`、observed distinct sources `bucket_minimum_met_low`、transport attempt `bucket_minimum_met_low`、transport success `bucket_minimum_met_low`、retry attempt `bucket_minimum_met_low`、timeout failure `bucket_zero`、rate-limit stop no-auth false 以及 redirect ambiguity fail-closed false。这是 source-materialization readiness only，不是任何 evidence-acquisition method 成功或失败的 evidence。

Phase 9H 不在 tracked source 中嵌入任何 remote source URL 或 repo name。在 confirmed execution 期间，使用 unauthenticated public GitHub search API discovery 在 ignored `runs/` 之下创建了 private candidate source pool；source identities 只在 ignored `runs/` 之下保持 private。使用 unauthenticated public GitHub API transport（trees API + raw content fetch）将 source files materialize 到 ignored `runs/` workspace only。Private manifests/materialization rows 只留在 ignored `runs/` 之下；public report 是 aggregate-only。Public report 不包含 exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts 与 singleton buckets。Public report 中唯一的 commit/CI 值是 Phase 9F 与 Phase 9G public gate references。

## No-claim boundary

Phase 9H 不执行 strategy scoring、labels、outcomes、evidence-success evaluation、model fitting/training、provider/LLM calls、runtime/default/product changes，也不提出 method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claim。不发生 provider/LLM/model/default/runtime change。

Task rows 保持 candidate inventory only。它们不是 labels、outcomes、gold、success 或 evidence_success。Materialization 本身不是 evidence_success。Future strategy scoring 需要另一个 frozen boundary。
