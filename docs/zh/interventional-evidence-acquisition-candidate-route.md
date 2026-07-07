# Interventional Evidence Acquisition 候选路线

日期：2026-07-07

Status: `candidate_route_phase1_methodology_repair_preflight_no_private_write`

Authorization: `methodology_repair_preflight_only_no_confirmed_private_capture`

Route relation: `new_candidate_route_not_reopening_closed_v2_lines`

本文记录 interventional evidence acquisition 的 Phase 0 候选路线设计，以及后续最小 Phase 1 local private pilot。它不是 OpenLocus v3 branding，也不授权 provider/network work、training、runtime/default changes 或 method-winner claims。

## 边界

该候选路线不重启 HAAE-A2/v2 trace-driven policy、RPM-D2/model scaling、FRK repair、LDI/static support、provider/network、runtime/default 或 method-winner routes。既有关闭结论仍是权威上下文；参见 [`current-route-closure.md`](./current-route-closure.md)、[`state-action-trace-v2-bootstrap.md`](./state-action-trace-v2-bootstrap.md) 和 [`openlocus-v2-rpm-d1-learning-smoke.md`](./openlocus-v2-rpm-d1-learning-smoke.md)，此处不重复旧路线细节。

Phase 1 private pilot output 仍需要显式 `--confirm-private-output`；未提供该 flag 时，runner 不得写入 private rows。该 pilot 不授权 provider/LLM plumbing、runtime/default changes、CI gates、model changes、training、source scans 或 README changes。

## Phase 1 local private pilot status

最小 local pilot runner 为 `eval/interventional_evidence_acquisition_phase1_local_episode_runner.py`。此前一次 confirmed low-resource local run 已在提供 `--confirm-private-output` 后，只向 ignored `runs/` storage 写入 private rows。当前 public aggregate report `artifacts/interventional_evidence_acquisition_phase1_local_episode_runner/interventional_evidence_acquisition_phase1_local_episode_runner_report.json` 已作为 methodology-repair `phase1_preflight` dry run 重新生成，未写入 private rows。

该 report 仅包含 aggregate 信息：private row contents、task text、paths、ranges、hashes、snippets、provider payloads 和 per-episode details 均不公开。未授权或执行 provider/network actions，未授权 training 或 runtime/default change，不提出 method-winner claim；下一步授权动作仍为 `stop/request next explicit decision`。

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
