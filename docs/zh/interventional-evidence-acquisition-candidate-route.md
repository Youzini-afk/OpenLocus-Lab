# Interventional Evidence Acquisition 候选路线

日期：2026-07-07

Status: `phase5b_public_repo_formal_validation_canary_complete_no_claim`

Authorization: `runner_canary_only_formal_validation_not_run`

Route relation: `new_candidate_route_not_reopening_closed_v2_lines`

本文记录 interventional evidence acquisition 的 Phase 0 候选路线设计，以及后续最小 Phase 1 local private pilot。它不是 OpenLocus v3 branding，也不授权 provider/network work、training、runtime/default changes 或 method-winner claims。

最新 checkpoint：Phase 5B runner canary。Runner 为 `eval/interventional_evidence_acquisition_phase5b_public_repo_formal_validation.py`；public aggregate canary report 为 `artifacts/phase5b_public_repo_formal_validation/phase5b_public_repo_formal_validation_report.json`。Status 为 `phase5b_public_repo_formal_validation_canary_complete_no_claim`。这不是 100-150 task formal validation。

## Phase 5B runner canary status

该 runner 使用安全的 two-step 形态：ingest 已冻结的 public task manifest 和 repo-lock，只为 scoring rows ingest private labels，精确执行 7 个 frozen local labels，并且 counted evidence 必须满足 current-source materialization/hash/currentness/task tie。Private rows 需要 `--confirm-private-output`，并保留在 ignored `runs/` 下。

Tiny local canary 已通过，并且只在 confirmation 后写入 ignored private canary rows。Runner 本身不 fetch repositories，也不生成 formal task set；这些仍是 future formal run 前的 external frozen hooks。100-150 task formal validation 尚未运行，也不提出 method/product/default/runtime claim。

## Phase 5A public-repo protocol freeze status

Phase 5A 冻结 possible Phase 5B public-repo validation：target 120 个 hard tasks，valid range 100-150，hard max 150，7 个 exact labels，max 1050 private rows，target 10-12 repos 且 hard max 16，并且在 execution 前冻结 repository URLs/SHAs/strata/replacement rules。

Future Phase 5B 允许的 network 只限 frozen URLs/SHAs 的 public GitHub repo fetch。禁止 LLM/provider/search API/remote model calls、training、runtime/default changes、新 retrieval families、staged runs 和 post-outcome tuning。Candidate-found alone 不是 evidence；counted success 需要 current-source read、materialization、hash/currentness verification 和 task tie。Public reporting 仍为 aggregate-only 和 no-claim。

## Phase 2 small fair local comparison status

同一 script 现在支持 `--run-phase2-comparison --confirm-private-output --phase2-private-manifest <ignored-local-path>`。它使用 ignored private manifest 中的 hard current-source tasks，对既有 7 个 micro-policy/control labels 做 paired local comparison。Private rows 保留在 ignored `runs/`；public output 只包含 aggregate 信息。

该 screen 比较 fixed-label buckets，并记录 best fixed local baselines。Best label 被视为 baseline，不是 winner。Counted success 需要 real current-source read、path/range/content/hash/currentness/range match、non-empty content 和 task-target tie。Candidate-found 不是 evidence。`stop` 和 `abstain` 仍保持 controls。

## Phase 3 independent local holdout validation status

同一 script 现在支持 `--run-phase3-holdout --confirm-private-output --phase3-private-manifest <ignored-local-path>`。它使用 fresh ignored private manifest 和同样 7 个 labels，验证 Phase 2 fixed-label comparison protocol 在 holdout slice 上仍能正常运行。Private rows 保留在 ignored `runs/`；public output 只包含 aggregate 信息。

Phase 3 screen 检查 protocol validity、control behavior、EvidenceCore materialization，以及 nontrivial best fixed acquisition baseline。它不选择 method，也不推广任何 product/default behavior。

## Phase 3B public replication closeout status

Phase 3B 记录 Phase 2 和 Phase 3 复现了 protocol-level bucket pattern：no-claim positive screens、best fixed acquisition/local baseline buckets `count_21_to_50`、controls `count_0`，以及 intact EvidenceCore/private-public boundaries。这将 small local comparison protocol 作为 research asset 保留。

Phase 3B 不证明哪个 method 最好，也不支持 lift、signal、runtime/default、product、provider/network 或 training claims。如果有 Phase 4，应先从 design-only action-outcome learning precheck 开始；在写出 feature、label、leakage 和 split rules 前，不进行 model training。

## Phase 4 learning precheck design status

Phase 4 写下 possible future action-outcome learning precheck 的 feature、label、leakage 和 split contract。Allowed future features 必须是 pre-action 且 non-leaky；forbidden features 包括 actual success labels、target paths/ranges/hashes/content、post-action reads、snippets、gold labels 和 provider payloads。

这不是 training authorization。Stop/go outcomes 仅限 `stop_no_learning_claim`、`repair_feature_contract_no_claim` 或 `learning_precheck_ready_no_training`。

## Phase 4A feature/leakage/class-balance precheck status

Phase 4A 检查 pre-action feature contract 是否足够 non-leaky，能否作为 future learning precheck input 保留。它拒绝 evidence-success-as-feature、target path/range/hash/content features、post-action read/currentness/materialization fields、leak-shaped public strings 和 exact singleton public buckets。它报告 `feature_balance_precheck_ready_no_training`，这不是 training、scoring、ranking 或 predictive-performance evidence。

## Phase 4B tiny local learning screen status

Phase 4B 在既有 ignored Phase 2/3 private rows 上运行 stdlib-only deterministic heldout bucket screen。它只使用 allowed pre-action categorical features，检查 negative controls，拒绝 ignored `runs/` 之外的 private inputs，并输出 aggregate-only public report。它不创建 reusable model artifact，也不提出 method/default claim。

## Phase 4C frozen fresh-holdout protocol design status

Phase 4C 只是 design-only。它在任何 execution 前冻结 possible future Phase 4D fresh-holdout protocol：target 12 个 fresh hard current-source tasks，hard max 16 tasks，7 个 fixed labels，max 112 private rows，只使用 ignored `runs/`，固定 features 为 `action_label`/`task_family_bucket`/`availability_bucket`/`budget_bucket`，使用 deterministic stdlib-only smoothed categorical table，并且不在 holdout rows 上 fit/tune。

Future Phase 4D statuses 仅限 `stop_no_learning_claim`、`repair_holdout_contract_no_claim` 或 `fresh_holdout_screen_positive_no_claim`。该 design 禁止 RPM-D2/model scaling、LLM/provider/network、runtime/default changes、新 retrieval families、reusable model artifacts、在 holdout rows 上 training、holdout 后 tuning、winner/lift/product/default claims，以及公开 private refs 或 rows。

## Phase 4D frozen fresh-holdout screen status

Phase 4D 作为 standalone local script `eval/interventional_evidence_acquisition_phase4d_frozen_fresh_holdout.py` 运行。它要求 Phase 4C public gate，使用 fresh ignored private manifest，只从 frozen Phase 2 private training rows fit，并且不在 holdout rows 上 fit/tune。Private manifest 和 private rows 保留在 ignored `runs/phase4d_frozen_fresh_holdout/...`；public output 仅为 aggregate-only。

Public status 为 `fresh_holdout_screen_positive_no_claim`。这只是 screen result；不是 method selection，不是 reusable model artifact，也不是 runtime/default/product claim。

## Phase 4E closeout status

Phase 4E 只是 public closeout。它不读取 private rows，不创建 manifests，不为新 evidence 读取 source，不收集 data，也不改变 scripts 或 CI。

该 closeout 记录这一路径：Phase 4B 运行 tiny local screen，Phase 4C 在 fresh check 前冻结规则，Phase 4D 在 fresh ignored private holdout rows 上运行 frozen rules。路线仍值得作为 research candidate 保留，但正确的下一状态是停止。继续做更多 small checks 会有 result-shopping 风险；任何下一步 empirical work 都需要单独的 larger validation decision 或 independent replication protocol。

## 边界

该候选路线不重启 HAAE-A2/v2 trace-driven policy、RPM-D2/model scaling、FRK repair、LDI/static support、provider/network、runtime/default 或 method-winner routes。既有关闭结论仍是权威上下文；参见 [`current-route-closure.md`](./current-route-closure.md)、[`state-action-trace-v2-bootstrap.md`](./state-action-trace-v2-bootstrap.md) 和 [`openlocus-v2-rpm-d1-learning-smoke.md`](./openlocus-v2-rpm-d1-learning-smoke.md)，此处不重复旧路线细节。

Phase 1 private pilot output 仍需要显式 `--confirm-private-output`；未提供该 flag 时，runner 不得写入 private rows。该 pilot 不授权 provider/LLM plumbing、runtime/default changes、CI gates、model changes、training、source scans 或 README changes。

## Phase 1 local private pilot status

最小 local pilot runner 为 `eval/interventional_evidence_acquisition_phase1_local_episode_runner.py`。此前一次 confirmed low-resource local run 已在提供 `--confirm-private-output` 后，只向 ignored `runs/` storage 写入 private rows。当前 public aggregate report `artifacts/interventional_evidence_acquisition_phase1_local_episode_runner/interventional_evidence_acquisition_phase1_local_episode_runner_report.json` 已作为 methodology-repair `phase1_preflight` dry run 重新生成，未写入 private rows。

该 report 仅包含 aggregate 信息：private row contents、task text、paths、ranges、hashes、snippets、provider payloads 和 per-episode details 均不公开。未授权或执行 provider/network actions，未授权 training 或 runtime/default change，不提出 method-winner claim；下一步授权动作仍为 `stop/request next explicit decision`。

## Hard-source preflight status

Hard-source preflight script 为 `eval/interventional_evidence_acquisition_phase1_hard_source_preflight.py`。它生成了 `artifacts/interventional_evidence_acquisition_phase1_hard_source_preflight/interventional_evidence_acquisition_phase1_hard_source_preflight_report.json`，status 为 `phase1_hard_source_preflight_no_private_rows`。

这不是 confirmed private capture。它检查 32 个 synthetic/local hard task shapes、8 个 family buckets，并且只公开 balance、structural availability、candidate ambiguity、baseline non-saturation、EvidenceCore summary 和 privacy summary 的 aggregate buckets。它不写入 private rows，也不授权 provider/network work、training、runtime/default changes、新 retrieval families、method-winner claims 或 route reopening。

## Hard-source private pilot status

同一 script 现在支持 explicit `--confirm-private-output` mode。一次 confirmed local private pilot 只向 ignored `runs/` storage 写入 private rows，并把同一个 public report 更新为 status `phase1_hard_source_private_pilot_complete_no_claim`。

Public report 仍然只包含 aggregate 信息：task/action/family count buckets、candidate-found buckets、materialized buckets、evidence-success buckets、baseline/non-saturation buckets、privacy summary 和 no-claim attestations。Retrieval-only actions 可以找到 candidates，但没有 current-source materialization 时不计为 evidence success。不授权 provider/network work、training、runtime/default changes、新 retrieval families、method-winner claims 或 route reopening。

## Private-row aggregate screen status

同一 script 现在支持 `--aggregate-private-rows`。它在本地读取已有的 ignored hard-source private rows，并写出 `artifacts/interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen/interventional_evidence_acquisition_phase1_hard_source_private_row_aggregate_screen_report.json`，status 为 `phase1_hard_source_private_row_aggregate_screen_no_claim`。

该 screen 是 public aggregate-only diagnostic。它只公开 row/action/family coverage、candidate-found、materialized、evidence-success、materialized-but-not-success、baseline/randomized screen 和 conservative recommendation `maybe_expand_with_new_explicit_decision` 的 buckets。它不公开 raw rows、private paths、symbols、queries、ranges、snippets、hashes、run paths、prompts、responses、provider payloads 或 labels，也不提出 method-winner 或 signal claim。

## Phase 1B micro-policy status

同一 script 现在支持 `--run-phase1b-micro-policy --confirm-private-output`。它在既有 hard synthetic task source 上运行 tiny local micro-policy collection，并且只向 ignored `runs/` 写入 private rows。Public report 为 `artifacts/interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection/interventional_evidence_acquisition_phase1b_micro_policy_tiny_collection_report.json`，status 为 `phase1b_micro_policy_tiny_collection_synthetic_preflight_no_real_evidencecore_no_claim`。

Phase 1B 只使用 7 个 local micro-policy/control labels：`bm25_then_read_top1`、`bm25_then_read_next_unique_file`、`symbol_regex_then_read_top1`、`symbol_regex_then_read_next_unique_file`、`read_related_test_when_available`、`stop` 和 `abstain`。Standalone retrieval 不是 Phase 1B top-level policy。由于当前 source 仍是模拟 materialization，而不是读取真实 current files/ranges/content，因此这只是 synthetic preflight，不是真实 EvidenceCore evidence。Public output 只包含 synthetic success labels 的 buckets，recommendation 为 `maybe_expand_with_new_explicit_decision`，且不提出 method-winner 或 signal claim。

## Phase 1C real current-source feasibility status

同一 script 现在支持 `--run-phase1c-real-source --confirm-private-output --phase1c-private-manifest <ignored-local-path>`。它在 8 个 current repository-file tasks 上运行 tiny local feasibility pilot，并覆盖全部 7 个既有 Phase 1B micro-policy/control labels；exact task paths/ranges 从 ignored private manifest 读取。Private rows 位于 ignored `runs/`；public report 为 `artifacts/interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot/interventional_evidence_acquisition_phase1c_tiny_real_current_source_pilot_report.json`，status 为 `phase1c_tiny_real_current_source_pilot_evidencecore_feasibility_no_claim`。

这只检查 local micro-policy framework 是否能安全执行 real current-source materialization。Counted success 需要 private path/range/content bytes、SHA-256、re-read/currentness match 和 range/content match。Public output 只包含 aggregate buckets，recommendation 为 `maybe_expand_with_new_explicit_decision`。它不提出 method-winner、lift 或 signal claim，也不改变 provider/network、training/model、runtime/default 或 retrieval-family 边界。

## Phase 1D real-source coverage robustness status

同一 script 现在支持 `--run-phase1d-real-source --confirm-private-output --phase1d-private-manifest <ignored-local-path>`。它在最多 16 个 current repository-file tasks 上运行 modest local robustness pilot，并覆盖全部 7 个既有 micro-policy/control labels；exact task paths/ranges 从 ignored private manifest 读取。Private rows 位于 ignored `runs/`；public report 为 `artifacts/interventional_evidence_acquisition_phase1d_real_source_coverage_robustness/interventional_evidence_acquisition_phase1d_real_source_coverage_robustness_report.json`，status 为 `phase1d_real_source_coverage_robustness_no_claim`。

这只测试 coverage robustness，不是 policy efficacy。Counted success 需要 real current-source materialization，以及 private hash 和 currentness checks。Public output 只包含 aggregate buckets，recommendation 为 `maybe_expand_with_new_explicit_decision`；它不提出 method-winner、lift 或 signal claim。

## Phase 1E cross-phase diagnostic status

同一 script 现在支持 `--run-phase1e-diagnostic --confirm-private-input`。它在本地读取既有 ignored Phase 1C 和 Phase 1D private rows，并写出 `artifacts/phase1e_cross_phase_private_row_diagnostic_screen/phase1e_cross_phase_private_row_diagnostic_screen_report.json`，status 为 `phase1e_cross_phase_private_row_diagnostic_no_claim`。

Phase 1E 不收集新 rows，也不读取新 source。它是 aggregate-only diagnostic：input coverage、EvidenceCore consistency、failure modes、policy-label coverage 和 coarse phase comparison。它不提出 policy efficacy、method-winner、signal 或 lift claim。

## 候选问题

在 hard product-workflow episodes 上，使用极小的本地 randomized intervention 来选择既有 evidence-acquisition actions，是否比 passive trace review 更能产生清晰的 workflow evidence，同时保持 EvidenceCore 与 privacy invariants？

目标 evidence 是决策质量，而不是 branding：受控 action choice 是否能更快找到 current、可 rematerialize 的 evidence。

## Phase 1 local pilot 形态

Phase 1 已按 private randomized local pilot 运行：

- 24-40 个 hard product-workflow episodes。
- 最多 7 个既有 local actions：`retrieve_bm25`、`retrieve_symbol_regex`、`read_top1`、`read_next_unique_file`、`read_related_test`、`stop`、`abstain`。
- 不使用 LLM/provider/network actions。
- 不做 model training 或 model scaling。
- 不新增 retrieval channel families。
- 不改变 runtime/default。
- 不提出 method-winner、scale、default 或 product-readiness claim。

## Private row schema

Confirmed run 使用的小型 fail-closed private row shape 包括：

- `schema_version`：固定 candidate schema id。
- `episode_id`、`step_index`、`randomization_block_id`：private identifiers。
- `task_bucket`：粗粒度 product-workflow task family，不记录 raw prompt text。
- `state`：label-blind pre-action fields，例如 remaining budget bucket、seen file count bucket、candidate count bucket、ambiguity bucket、evidence coverage bucket。
- `action`：上述 7 个 local actions 之一。
- `randomization`：eligible action set、assignment policy id、probability bucket；seed/reference 保持 private。
- `observation`：cost bucket、file/read result bucket、abstain/stop marker、failure-safe reason bucket。
- `evidence_core`：private source path、range、content/currentness check result、rematerialization status。
- `outcome`：post-action success/failure-safe label 与 reason bucket，只能在 action 之后或 offline review 后填写。
- `privacy`：用于确认 prompt/response/snippet/gold/provider/path/range/hash/reference containment 的 private-only markers。

Private rows 保留在 ignored `runs/` storage 下，不是 public artifacts。

## Aggregate-only public report shape

Public report 只包含 aggregate/sanitized 信息，例如：

- route/status/authorization fields；
- episode-count 与 step-count buckets；
- action coverage 与 randomization health buckets；
- EvidenceCore rematerialization pass/fail buckets；
- 按 action family 聚合的 success/failure-safe buckets；
- stop/abstain 与 budget buckets；
- privacy scan summary；
- 不含 private rows 的 stop/go recommendation。

Public report 不得包含 private traces、prompts、responses、snippets、gold labels、provider payloads、exact paths、exact ranges、hashes、private refs、raw task text、raw row values 或 per-episode details。

## EvidenceCore 与 privacy invariants

- Counted evidence 必须 rematerialize current source path/range/content/currentness。
- Candidate evidence 在通过 currentness 与 content checks 前不是 fact。
- Public outputs 只能是 aggregate/sanitized。
- Private traces、prompts、responses、snippets、gold、provider payloads、exact paths、exact ranges、hashes 和 private refs 必须保持 private。
- State/action fields 必须保持 label-blind；labels/outcomes 只能 post-action 或 offline-only。

## Phase 0 -> Phase 1 decision record

Phase 1 只在满足以下条件后运行：

1. 单独的 explicit route decision 点名该 candidate route，并授权 tiny private pilot。
2. Episode source 被限制为 24-40 个 hard product-workflow episodes。
3. Action set 仍限制为上述 7 个既有 local actions。
4. 在任何 capture 前接受 private row schema 与 aggregate-only report contract。
5. 从第一行开始要求 EvidenceCore rematerialization 与 privacy checks。
6. 该 decision 明确保留本文列出的全部 closed-route boundaries。

## Phase 1 stop/go status

Phase 1 已作为 no-claim pilot 完成。除非后续另有单独 decision，否则必须 stop，因为 public report 明确不提出 signal 或 method-winner claim。未来若要继续，需要同时满足：

1. Private rows schema-valid，且 state/action fields 无 label leakage。
2. EvidenceCore rematerialization 达到预先声明的最低要求，足以支撑 counted evidence。
3. Public/private privacy boundary 无 failure。
4. Randomization health 达到预先声明的检查要求，足以支撑 tiny pilot 的 aggregate comparison。
5. 预先声明的 aggregate stop/go thresholds 被满足，包括 practical aggregate signal，表明 randomized existing-local-action choice 在相同 7-action、same-budget setup 下，相比 best fixed local-action baseline 改善 hard product-workflow evidence acquisition，而不只是优于 stop/abstain。

即使全部通过，唯一可能的后续动作仍是另一个 explicit route decision。Phase 1 不会授权 runtime/default changes、provider/network work、training、new retrieval families 或 method-winner claims。
